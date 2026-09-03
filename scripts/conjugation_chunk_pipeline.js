#!/usr/bin/env node
'use strict';
var A = require('./conjugation_chunk_a.js');
var SUPERTonic_VOICES = A.SUPERTonic_VOICES;
var AIVIS_VOICES = A.AIVIS_VOICES;
var PROVIDERS = A.PROVIDERS;
var sha256 = A.sha256;
var padChunk = A.padChunk;
var loadJson = A.loadJson;
var writeJson = A.writeJson;
var loadInventory = A.loadInventory;
var chunkReadings = A.chunkReadings;
var freezeHashOf = A.freezeHashOf;
var assertFrozen = A.assertFrozen;
var assetName = A.assetName;
var releaseTagFor = A.releaseTagFor;
var emptyStatus = A.emptyStatus;
var ensureVoice = A.ensureVoice;
var getChunkRecord = A.getChunkRecord;
var isChunkComplete = A.isChunkComplete;
var legacyReadingMap = A.legacyReadingMap;
var planChunk = A.planChunk;
var generatorCatalog = A.generatorCatalog;
var skipCheck = A.skipCheck;
var validateTar = A.validateTar;

function markComplete(status, provider, voice, invVersion, chunk, rec) {
  var slot = ensureVoice(status, provider, voice, invVersion);
  rec.status = 'complete';
  rec.chunk = chunk;
  rec.timestamp = rec.timestamp || new Date().toISOString();
  slot.chunks[String(chunk)] = rec;
  recomputeVoice(slot, status.chunkCount || Object.keys(slot.chunks).length);
  status.updatedAt = rec.timestamp;
  return status;
}

function markFailed(status, provider, voice, invVersion, chunk, rec) {
  var slot = ensureVoice(status, provider, voice, invVersion);
  rec.status = 'failed';
  rec.chunk = chunk;
  rec.timestamp = rec.timestamp || new Date().toISOString();
  rec.retry = (rec.retry || 0);
  slot.chunks[String(chunk)] = rec;
  recomputeVoice(slot, status.chunkCount);
  status.updatedAt = rec.timestamp;
  return status;
}

function recomputeVoice(slot, chunkCount) {
  var complete = 0, generated = 0, reused = 0;
  Object.keys(slot.chunks).forEach(function (k) {
    var c = slot.chunks[k];
    if (isChunkComplete(c)) {
      complete++;
      generated += Number(c.generatedCount || 0);
      reused += Number(c.reusedCount || 0);
    }
  });
  slot.generatedReadings = generated;
  slot.reusedReadings = reused;
  slot.coverageComplete = chunkCount > 0 && complete === chunkCount;
}

function missingChunks(status, provider, voice, invVersion, chunkCount, releaseAssets) {
  var missing = [];
  for (var i = 0; i < chunkCount; i++) {
    var rec = getChunkRecord(status, provider, voice, invVersion, i);
    var name = assetName(provider, voice, invVersion, i);
    var onRelease = Array.isArray(releaseAssets) && releaseAssets.indexOf(name) >= 0;
    if (isChunkComplete(rec) && (rec.reused || onRelease || rec.githubAvailable)) continue;
    missing.push(i);
  }
  return missing;
}

function expectedVoices(provider, speakerKeys) {
  if (provider === 'supertonic3') return SUPERTonic_VOICES.slice();
  if (provider === 'aivis') return AIVIS_VOICES.slice();
  if (provider === 'voicevox') return speakerKeys && speakerKeys.length ? speakerKeys.slice() : [];
  return [];
}

function finalizeReport(inv, status, provider, opts) {
  opts = opts || {};
  var assets = opts.releaseAssets || [];
  var voices = opts.voices || expectedVoices(provider, opts.speakerKeys);
  var invVersion = opts.inventoryVersion || inv.inventoryVersion;
  var chunkCount = inv.chunkCount;
  var rows = [];
  voices.forEach(function (voice) {
    var missing = missingChunks(status, provider, voice, invVersion, chunkCount, assets);
    var slot = status.providers && status.providers[provider] && status.providers[provider][voice] &&
      status.providers[provider][voice][invVersion];
    var complete = missing.length === 0 && chunkCount > 0;
    rows.push({
      voice: voice,
      coverageComplete: complete,
      status: complete ? 'COMPLETE' : 'NOT COMPLETE',
      expectedChunks: chunkCount,
      missingChunks: missing,
      missingChunkIds: missing.map(padChunk),
      reusedReadings: slot && slot.reusedReadings || 0,
      generatedReadings: slot && slot.generatedReadings || 0,
      expectedReadings: inv.uniqueReadingCount || inv.readings.length,
      advertise100: complete,
      publishRuntimeCatalog: complete || !!(opts.allowHonestPartial && slot && (slot.generatedReadings || slot.reusedReadings)),
      honestPartial: !complete && !!(slot && (slot.generatedReadings || slot.reusedReadings) && opts.allowHonestPartial)
    });
  });
  var allComplete = rows.length > 0 && rows.every(function (r) { return r.coverageComplete; });
  return {
    provider: provider,
    inventoryVersion: invVersion,
    freezeHash: inv.freezeHash,
    uniqueReadingCount: inv.uniqueReadingCount || inv.readings.length,
    chunkSize: inv.chunkSize,
    chunkCount: chunkCount,
    publicBundleCount: inv.publicBundleCount,
    usedActionsArtifacts: false,
    source: 'durable-status+release-metadata',
    coverageComplete: allComplete,
    status: allComplete ? 'COMPLETE' : 'NOT COMPLETE',
    voices: rows,
    note: allComplete
      ? 'All voices have complete chunk coverage.'
      : 'NOT COMPLETE. Missing chunk IDs are listed per voice. Do not advertise 100% hosted coverage. Keep previous valid lookup; incomplete is a miss then documented fallback.'
  };
}

function mapLegacyF3(status, inv, catalog) {
  var slot = ensureVoice(status, 'supertonic3', 'F3', inv.inventoryVersion);
  var map = legacyReadingMap(catalog);
  var count = Object.keys(map).length;
  slot.legacyReuse = {
    releaseTag: 'word-supertonic3-conj-v1',
    catalog: 'word-supertonic3-conj-catalog.json',
    voice: 'F3',
    readingCount: count,
    publicShardCount: Number(catalog && catalog.shardCount) || 8,
    note: 'reading×voice mapped via catalog words map; do not regenerate valid F3 clips'
  };
  slot.reusedReadings = count;
  slot.expectedReadings = inv.uniqueReadingCount || inv.readings.length;
  slot.coverageComplete = false;
  slot.coverageNote = 'Partial F3 v1 (' + count + ' of ' + slot.expectedReadings + '). Not 100% hosted.';
  return status;
}

function applyPartialFailure(status, provider, voice, invVersion, okChunk, failChunk, okRec, failRec) {
  markComplete(status, provider, voice, invVersion, okChunk, okRec);
  markFailed(status, provider, voice, invVersion, failChunk, failRec);
  var kept = getChunkRecord(status, provider, voice, invVersion, okChunk);
  var failed = getChunkRecord(status, provider, voice, invVersion, failChunk);
  return { keptComplete: isChunkComplete(kept), failedNotComplete: !isChunkComplete(failed) };
}

function parseArgs(argv) {
  var cmd = argv[2] || 'help';
  var opts = { _: [] };
  for (var i = 3; i < argv.length; i++) {
    var a = argv[i];
    if (a.indexOf('--') === 0) {
      var k = a.slice(2);
      var v = argv[i + 1];
      if (!v || v.indexOf('--') === 0) { opts[k] = true; }
      else { opts[k] = v; i++; }
    } else opts._.push(a);
  }
  opts.cmd = cmd;
  return opts;
}

function main(argv) {
  var opts = parseArgs(argv);
  var cmd = opts.cmd;
  if (cmd === 'help' || cmd === '--help') {
    process.stdout.write('conjugation_chunk_pipeline.js slice|skip-check|validate|update-status|finalize-report|asset-name\n');
    return 0;
  }
  if (cmd === 'asset-name') {
    process.stdout.write(assetName(opts.provider, opts.voice, opts.inventory_version || opts.version, parseInt(opts.chunk, 10)) + '\n');
    return 0;
  }
  if (cmd === 'slice') {
    var inv = loadInventory(opts.inventory);
    assertFrozen(inv);
    var chunk = parseInt(opts.chunk, 10);
    var legacy = opts['legacy-catalog'] ? legacyReadingMap(loadJson(opts['legacy-catalog'])) : Object.create(null);
    var plan = planChunk(inv, chunk, {
      provider: opts.provider,
      voice: opts.voice,
      legacyMap: legacy
    });
    var cat = generatorCatalog(inv, chunk, plan);
    writeJson(opts.out, cat);
    writeJson(opts.plan || (opts.out + '.plan.json'), plan, true);
    process.stdout.write(JSON.stringify({
      chunk: chunk,
      expected: plan.expected,
      toGenerate: plan.toGenerate.length,
      reused: plan.reused.length,
      allReused: plan.allReused
    }) + '\n');
    return 0;
  }
  if (cmd === 'skip-check') {
    var status = loadJson(opts.status) || {};
    var assets = [];
    if (opts['release-assets']) {
      var raw = fs.readFileSync(opts['release-assets'], 'utf8').trim();
      assets = raw ? raw.split(/\s+/) : [];
    }
    var res = skipCheck(status, opts.provider, opts.voice, opts.inventory_version, parseInt(opts.chunk, 10), assets);
    process.stdout.write(JSON.stringify(res) + '\n');
    return res.skip ? 0 : 10;
  }
  if (cmd === 'validate') {
    var cat = loadJson(opts.catalog);
    var ids = (cat.items || []).map(function (x) { return x.id; });
    var report = validateTar(opts.tar, ids, { skipDecode: !!opts['skip-decode'] });
    if (opts.out) writeJson(opts.out, report, true);
    process.stdout.write(JSON.stringify(report) + '\n');
    return report.ok ? 0 : 1;
  }
  if (cmd === 'update-status') {
    var st = loadJson(opts.status) || emptyStatus(loadInventory(opts.inventory));
    var rec = loadJson(opts.record);
    var ch = parseInt(opts.chunk, 10);
    if (opts.failed) markFailed(st, opts.provider, opts.voice, opts.inventory_version, ch, rec);
    else markComplete(st, opts.provider, opts.voice, opts.inventory_version, ch, rec);
    writeJson(opts.out || opts.status, st, true);
    return 0;
  }
  if (cmd === 'finalize-report') {
    var inv2 = loadInventory(opts.inventory);
    var st2 = loadJson(opts.status) || emptyStatus(inv2);
    var assets2 = [];
    if (opts['release-assets']) {
      var raw2 = fs.readFileSync(opts['release-assets'], 'utf8').trim();
      try { assets2 = JSON.parse(raw2); }
      catch (e) { assets2 = raw2 ? raw2.split(/\s+/) : []; }
    }
    var speakers = opts.speakers ? String(opts.speakers).split(',') : [];
    var report = finalizeReport(inv2, st2, opts.provider, {
      releaseAssets: assets2,
      speakerKeys: speakers,
      voices: opts.voice ? [opts.voice] : undefined,
      inventoryVersion: opts.inventory_version || inv2.inventoryVersion,
      allowHonestPartial: opts['honest-partial'] !== 'false'
    });
    if (opts.out) writeJson(opts.out, report, true);
    process.stdout.write(JSON.stringify(report, null, 2) + '\n');
    return 0;
  }
  throw new Error('unknown command ' + cmd);
}

module.exports = {
  SUPERTonic_VOICES: SUPERTonic_VOICES,
  AIVIS_VOICES: AIVIS_VOICES,
  PROVIDERS: PROVIDERS,
  sha256: sha256,
  padChunk: padChunk,
  loadJson: loadJson,
  writeJson: writeJson,
  loadInventory: loadInventory,
  chunkReadings: chunkReadings,
  freezeHashOf: freezeHashOf,
  assertFrozen: assertFrozen,
  assetName: assetName,
  releaseTagFor: releaseTagFor,
  emptyStatus: emptyStatus,
  ensureVoice: ensureVoice,
  getChunkRecord: getChunkRecord,
  isChunkComplete: isChunkComplete,
  legacyReadingMap: legacyReadingMap,
  planChunk: planChunk,
  generatorCatalog: generatorCatalog,
  skipCheck: skipCheck,
  validateTar: validateTar,
  markComplete: markComplete,
  markFailed: markFailed,
  missingChunks: missingChunks,
  expectedVoices: expectedVoices,
  finalizeReport: finalizeReport,
  mapLegacyF3: mapLegacyF3,
  applyPartialFailure: applyPartialFailure
};

if (require.main === module) {
  try { process.exit(main(process.argv) || 0); }
  catch (e) { console.error(e.stack || e); process.exit(1); }
}
