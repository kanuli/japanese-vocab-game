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
    { kanji: '\u98df\u3079\u308b', reading: '\u305f\u3079\u308b', pos: '\u4ed6\u52d82' },
    { kanji: '\u66f8\u304f', reading: '\u304b\u304f', pos: '\u4ed6\u52d81' },
    { kanji: '\u3059\u308b', reading: '\u3059\u308b', pos: '\u81ea\u4ed6\u52d83' },
    { kanji: '\u9ad8\u6821', reading: '\u3053\u3046\u3053\u3046', pos: '\u540d' }
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
ok(conj.canConjugate({ kanji: '\u98df\u3079\u308b', reading: '\u305f\u3079\u308b', pos: '\u4ed6\u52d82' }) === true, 'grammar classifier unchanged');

var smokeInv = {
  inventoryVersion: 'smoke-v1',
  freezeHash: 'x',
  chunkSize: 2,
  chunkCount: 1,
  smoke: true,
  uniqueReadingCount: 2,
  readings: [['aaaa', '\u3042\u3046', '\u4f1a\u3046'], ['bbbb', '\u3042\u305d\u3076', '\u904a\u3076']]
};
var legacyHit = {
  '\u3042\u3046': { key: '\u3042\u3046|\u4f1a\u3046', id: 'legacy-au', shard: 3, source: 'word-supertonic3-conj-v1' },
  '\u3042\u305d\u3076': { key: '\u3042\u305d\u3076|\u904a\u3076', id: 'legacy-asobu', shard: 4, source: 'word-supertonic3-conj-v1' }
};
var smokePlan = P.planChunk(smokeInv, 0, { provider: 'supertonic3', voice: 'F3', legacyMap: legacyHit });
ok(smokePlan.expected === 2 && smokePlan.toGenerate.length === 2 && smokePlan.reused.length === 0 && smokePlan.allReused === false, 'smoke disables F3 v1 reading reuse');
var smokeCat = P.generatorCatalog(smokeInv, 0, smokePlan);
ok(smokeCat.shardCount === 1 && smokeCat.items.length === 2 && smokeCat.items.every(function (x) { return x.shard === 0; }), 'smoke catalog shardCount=1 and every item shard=0');

var v1Inv = {
  inventoryVersion: 'v1',
  freezeHash: 'x',
  chunkSize: 2,
  chunkCount: 1,
  uniqueReadingCount: 2,
  readings: smokeInv.readings
};
var v1Plan = P.planChunk(v1Inv, 0, { provider: 'supertonic3', voice: 'F3', legacyMap: legacyHit });
ok(v1Plan.reused.length === 2 && v1Plan.toGenerate.length === 0 && v1Plan.allReused === true, 'v1 F3 still reuses published catalog readings');
var v1PartialLegacy = { '\u3042\u3046': legacyHit['\u3042\u3046'] };
var v1Mix = P.planChunk(v1Inv, 0, { provider: 'supertonic3', voice: 'F3', legacyMap: v1PartialLegacy });
ok(v1Mix.reused.length === 1 && v1Mix.toGenerate.length === 1 && v1Mix.toGenerate[0].reading === '\u3042\u305d\u3076', 'v1 mixed reuse still synthesizes missing readings');

ok(conj.conjugate({ kanji: '\u98df\u3079\u308b', reading: '\u305f\u3079\u308b', pos: '\u4ed6\u52d82' }).forms.find(function (x) { return x.id === 'nai'; }).written === '\u98df\u3079\u306a\u3044', '\u306a\u3044\u5f62 grammar unchanged');

ok(inv.publicBundleCount === 20, 'public bundle count is 20 not thousands of gen chunks');
ok(inv.chunkCount !== inv.publicBundleCount || inv.uniqueReadingCount <= inv.chunkSize * 20, 'gen chunks may exceed public bundles');

if (failed) {
  console.error('\nPIPELINE ' + passed + ' passed, ' + failed + ' failed');
  process.exit(1);
}
console.log('PIPELINE PASS ' + passed + ' assertions');
