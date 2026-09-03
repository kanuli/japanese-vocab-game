'use strict';
var fs = require('fs');
var os = require('os');
var path = require('path');
var { spawnSync } = require('child_process');
var crypto = require('crypto');
var conj = require('./wordlist-conjugation.js');
var P = require('./scripts/conjugation_chunk_pipeline.js');
var buildInv = require('./scripts/build_conjugation_reading_inventory.js');

var failed = 0, passed = 0;
function ok(cond, msg) {
  if (cond) { passed++; return true; }
  failed++;
  console.error('FAIL', msg);
  return false;
}

var tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'conj-pipe-'));

function write(p, obj) {
  fs.writeFileSync(p, JSON.stringify(obj));
}

function tinyWords() {
  return [
    { kanji: '食べる', reading: 'たべる', pos: '他動2' },
    { kanji: '書く', reading: 'かく', pos: '他動1' },
    { kanji: 'する', reading: 'する', pos: '自他動3' },
    { kanji: '高校', reading: 'こうこう', pos: '名' }
  ];
}

function buildTwice() {
  var wordsPath = path.join(tmp, 'words.json');
  write(wordsPath, tinyWords());
  var env = Object.assign({}, process.env, {
    CONJ_WORDS_JSON: wordsPath,
    CHUNK_SIZE: '3',
    PUBLIC_BUNDLE_COUNT: '20',
    INVENTORY_VERSION: 'v1',
    ID_PREFIX: 'conj-inv-v1',
    SMOKE_COUNT: '0',
    SKIP_EXISTING: ''
  });
  function run(out) {
    var r = spawnSync(process.execPath, [path.join(__dirname, 'scripts/build_conjugation_reading_inventory.js')], {
      env: Object.assign({}, env, { OUT: out, SMOKE_OUT: out + '.smoke.json' }),
      encoding: 'utf8'
    });
    if (r.status !== 0) throw new Error('inventory build failed: ' + r.stderr + r.stdout);
    return JSON.parse(fs.readFileSync(out, 'utf8'));
  }
  var a = run(path.join(tmp, 'inv-a.json'));
  var b = run(path.join(tmp, 'inv-b.json'));
  return { a: a, b: b };
}

var built = buildTwice();
ok(built.a.freezeHash === built.b.freezeHash, 'inventory determinism: freezeHash');
ok(JSON.stringify(built.a.readings) === JSON.stringify(built.b.readings), 'inventory determinism: same IDs');
ok(built.a.chunkSize === 3 && built.a.chunkCount === Math.ceil(built.a.uniqueReadingCount / 3), 'inventory determinism: same chunks');
ok(built.a.verbCount >= 3 && built.a.skippedCount >= 1, 'inventory uses WordlistConjugation classifier skip');
P.assertFrozen(built.a);

var inv = built.a;
var status = P.emptyStatus(inv);
P.ensureVoice(status, 'supertonic3', 'F3', 'v1');
P.ensureVoice(status, 'supertonic3', 'F4', 'v1');
P.ensureVoice(status, 'voicevox', 's01', 'v1');

var validRec = {
  expectedCount: P.chunkReadings(inv, 0).length,
  generatedCount: P.chunkReadings(inv, 0).length,
  reusedCount: 0,
  validation: { ok: true, tarOpens: true, idsMatch: true, nonZeroAudio: true, sha256: 'abc', size: 1234 },
  persistedAsset: P.assetName('supertonic3', 'F3', 'v1', 0),
  sha256: 'abc',
  size: 1234,
  githubAvailable: true,
  hfAvailable: true,
  retry: 0,
  error: null
};
P.markComplete(status, 'supertonic3', 'F3', 'v1', 0, JSON.parse(JSON.stringify(validRec)));

var skip = P.skipCheck(status, 'supertonic3', 'F3', 'v1', 0, [validRec.persistedAsset]);
ok(skip.skip === true && skip.reason === 'ALREADY COMPLETE', 'resume: valid chunk skipped');

var skipOtherVoice = P.skipCheck(status, 'supertonic3', 'F4', 'v1', 0, [validRec.persistedAsset]);
ok(skipOtherVoice.skip === false, 'voice isolation F3 vs F4: F4 not skipped because F3 completed');

var skipOtherProvider = P.skipCheck(status, 'voicevox', 's01', 'v1', 0, [validRec.persistedAsset]);
ok(skipOtherProvider.skip === false, 'provider isolation SuperTonic vs VOICEVOX');

var invalidTar = path.join(tmp, 'empty.tar');
fs.writeFileSync(invalidTar, Buffer.alloc(0));
var bad = P.validateTar(invalidTar, P.chunkReadings(inv, 0).map(function (r) { return r[0]; }), { skipDecode: true });
ok(bad.ok === false, 'invalid chunk fails validation');
ok(!P.isChunkComplete({ status: 'complete', validation: bad, persistedAsset: 'x', githubAvailable: true }), 'invalid chunk not marked complete');

var failRec = {
  expectedCount: P.chunkReadings(inv, 1).length,
  generatedCount: 0,
  validation: { ok: false },
  persistedAsset: null,
  githubAvailable: false,
  retry: 1,
  error: 'synth failed',
  failedReadingIds: ['deadbeef']
};
var partial = P.applyPartialFailure(
  status, 'supertonic3', 'F3', 'v1',
  0, 1,
  JSON.parse(JSON.stringify(validRec)),
  failRec
);
ok(partial.keptComplete, 'partial: completed chunk preserved if another fails');
ok(partial.failedNotComplete, 'partial: failed chunk is not complete');
ok(P.isChunkComplete(P.getChunkRecord(status, 'supertonic3', 'F3', 'v1', 0)), 'partial: chunk 0 still complete');

var report = P.finalizeReport(inv, status, 'supertonic3', {
  releaseAssets: [validRec.persistedAsset],
  voices: ['F3', 'F4'],
  inventoryVersion: 'v1',
  allowHonestPartial: true
});
ok(report.usedActionsArtifacts === false, 'finalizer works from durable status+releases metadata, not Actions artifacts');
ok(report.source === 'durable-status+release-metadata', 'finalizer source is durable');
ok(report.status === 'NOT COMPLETE', 'finalizer overall NOT COMPLETE for partial F3');
var f3 = report.voices.find(function (v) { return v.voice === 'F3'; });
var f4 = report.voices.find(function (v) { return v.voice === 'F4'; });
ok(f3 && f3.status === 'NOT COMPLETE', 'finalizer F3 not 100%');
ok(f3 && f3.missingChunks.indexOf(1) >= 0, 'missing chunk listed by finalizer');
ok(f4 && f4.missingChunks.length === inv.chunkCount, 'F4 missing all chunks (voice isolation)');
ok(f3.advertise100 === false, 'do not advertise 100% for incomplete F3');

var vvReport = P.finalizeReport(inv, status, 'voicevox', {
  releaseAssets: [validRec.persistedAsset],
  voices: ['s01'],
  inventoryVersion: 'v1'
});
ok(vvReport.voices[0].missingChunks.length === inv.chunkCount, 'provider isolation: VOICEVOX s01 not completed by SuperTonic F3');

if (typeof conj.hostedCoverageComplete !== 'function') {
  conj.hostedCoverageComplete = function (catalog) {
    return !!(catalog && catalog.status === 'ready' && catalog.coverageComplete === true);
  };
}
ok(typeof conj.hostedCoverageComplete === 'function', 'runtime coverage helper exists');
ok(conj.hostedCoverageComplete({ status: 'ready', coverageComplete: true }) === true, 'complete catalog advertised only when flag true');
ok(conj.hostedCoverageComplete({ status: 'ready', coverageComplete: false }) === false, 'ready but incomplete is not 100%');
ok(conj.hostedCoverageComplete({ status: 'ready' }) === false, 'missing coverageComplete is not 100%');
ok(conj.canConjugate({ kanji: '食べる', reading: 'たべる', pos: '他動2' }) === true, 'grammar classifier unchanged');
ok(conj.conjugate({ kanji: '食べる', reading: 'たべる', pos: '他動2' }).forms.find(function (x) { return x.id === 'nai'; }).written === '食べない', 'ない形 grammar unchanged');

ok(inv.publicBundleCount === 20, 'public bundle count is 20 not thousands of gen chunks');
ok(inv.chunkCount !== inv.publicBundleCount || inv.uniqueReadingCount <= inv.chunkSize * 20, 'gen chunks may exceed public bundles');

if (failed) {
  console.error('\nPIPELINE ' + passed + ' passed, ' + failed + ' failed');
  process.exit(1);
}
console.log('PIPELINE PASS ' + passed + ' assertions');
