#!/usr/bin/env node
'use strict';
/**
 * Small-batch conjugation audio pipeline helpers.
 * Workers consume a frozen inventory. Finalizers read durable status + release
 * metadata, never Actions artifacts.
 */
var fs = require('fs');
var path = require('path');
var crypto = require('crypto');
var zlib = require('zlib');
var { spawnSync } = require('child_process');

var SUPERTonic_VOICES = ['F1','F2','F3','F4','F5','M1','M2','M3','M4','M5'];
var AIVIS_VOICES = ['a01','a02','a03','a04'];
var PROVIDERS = ['supertonic3','voicevox','aivis'];

function sha256(buf) {
  return crypto.createHash('sha256').update(buf).digest('hex');
}
function padChunk(n) {
  return String(n).padStart(3, '0');
}
function loadJson(p) {
  if (!p) return null;
  if (!fs.existsSync(p)) return null;
  var raw = fs.readFileSync(p);
  if (String(p).endsWith('.gz')) raw = zlib.gunzipSync(raw);
  return JSON.parse(raw.toString('utf8'));
}
function writeJson(p, obj, pretty) {
  fs.mkdirSync(path.dirname(p), { recursive: true });
  var text = pretty ? JSON.stringify(obj, null, 2) + '\n' : JSON.stringify(obj);
  fs.writeFileSync(p, text);
}

function loadInventory(file) {
  var inv = loadJson(file);
  if (!inv || !Array.isArray(inv.readings)) throw new Error('invalid inventory: ' + file);
  if (!inv.inventoryVersion) throw new Error('inventory missing version');
  if (!inv.freezeHash) throw new Error('inventory missing freezeHash');
  if (!inv.chunkSize) throw new Error('inventory missing chunkSize');
  inv.chunkCount = inv.chunkCount || Math.ceil(inv.readings.length / inv.chunkSize);
  inv.publicBundleCount = inv.publicBundleCount || 20;
  return inv;
}

function chunkReadings(inv, chunk) {
  var size = inv.chunkSize;
  var start = chunk * size;
  return inv.readings.slice(start, start + size);
}

function chunkIndexForReading(inv, reading) {
  for (var i = 0; i < inv.readings.length; i++) {
    if (inv.readings[i][1] === reading) return Math.floor(i / inv.chunkSize);
  }
  return -1;
}

function freezeHashOf(inv) {
  var canonical = inv.readings.map(function (x) { return x[0] + '\t' + x[1]; }).join('\n');
  var ver = String(inv.inventoryVersion);
  // Smoke freeze omits chunkSize (see build_conjugation_reading_inventory.js).
  if (inv.smoke || ver.indexOf('smoke') === 0) {
    return sha256(Buffer.from(ver + '\n' + canonical));
  }
  return sha256(Buffer.from(ver + '\n' + inv.chunkSize + '\n' + canonical));
}

function assertFrozen(inv) {
  var h = freezeHashOf(inv);
  if (h !== inv.freezeHash) throw new Error('inventory freezeHash mismatch');
  return h;
}

function assetName(provider, voice, invVersion, chunk) {
  var ver = String(invVersion).replace(/[^a-zA-Z0-9._-]/g, '');
  return provider + '-' + voice + '-inv' + ver + '-chunk' + padChunk(chunk) + '.tar';
}

function releaseTagFor(invVersion) {
  if (String(invVersion).indexOf('smoke') === 0) return 'word-conj-chunks-smoke';
  return 'word-conj-chunks-v1';
}

function emptyStatus(inv) {
  return {
    schemaVersion: 1,
    inventoryVersion: inv.inventoryVersion,
    inventoryFreezeHash: inv.freezeHash,
    chunkSize: inv.chunkSize,
    chunkCount: inv.chunkCount,
    publicBundleCount: inv.publicBundleCount,
    uniqueReadingCount: inv.uniqueReadingCount || inv.readings.length,
    updatedAt: null,
    note: 'Checkpoint. One failure must never require restarting previously successful units. Generation chunks are not public runtime shards.',
    providers: {
      supertonic3: {},
      voicevox: {},
      aivis: {}
    }
  };
}

function ensureVoice(status, provider, voice, invVersion) {
  status.providers = status.providers || {};
  status.providers[provider] = status.providers[provider] || {};
  status.providers[provider][voice] = status.providers[provider][voice] || {};
  var slot = status.providers[provider][voice][invVersion] || {
    coverageComplete: false,
    expectedReadings: status.uniqueReadingCount || 0,
    generatedReadings: 0,
    reusedReadings: 0,
    chunks: {}
  };
  status.providers[provider][voice][invVersion] = slot;
  slot.chunks = slot.chunks || {};
  return slot;
}

function getChunkRecord(status, provider, voice, invVersion, chunk) {
  var slot = status && status.providers && status.providers[provider] &&
    status.providers[provider][voice] && status.providers[provider][voice][invVersion];
  if (!slot || !slot.chunks) return null;
  return slot.chunks[String(chunk)] || null;
}

function isChunkComplete(rec) {
  if (!rec) return false;
  if (rec.status !== 'complete') return false;
  if (rec.reused === true && rec.validation && rec.validation.ok) return true;
  if (!rec.validation || rec.validation.ok !== true) return false;
  if (!rec.persistedAsset) return false;
  if (rec.githubAvailable !== true) return false;
  return true;
}

function legacyReadingMap(catalog) {
  var out = Object.create(null);
  if (!catalog || !catalog.words) return out;
  Object.keys(catalog.words).forEach(function (k) {
    var r = String(k).split('|')[0];
    var e = catalog.words[k];
    out[r] = {
      key: k,
      id: Array.isArray(e) ? e[0] : e,
      shard: Array.isArray(e) ? e[1] : 0,
      source: 'word-supertonic3-conj-v1'
    };
  });
  return out;
}

function planChunk(inv, chunk, opts) {
  opts = opts || {};
  var rows = chunkReadings(inv, chunk);
  var legacy = opts.legacyMap || Object.create(null);
  var voice = opts.voice || '';
  var reuseOnlyFor = opts.reuseVoice || 'F3';
  var items = [];
  var reused = [];
  var skippedValid = [];
  var isSmoke = !!(inv.smoke || String(inv.inventoryVersion || '').indexOf('smoke') === 0);
  for (var i = 0; i < rows.length; i++) {
    var id = rows[i][0], reading = rows[i][1], written = rows[i][2];
    // Smoke must synthesize new clips; never reuse published F3 v1 by reading only.
    var reuse = !opts.disableReuse && !isSmoke && (voice === reuseOnlyFor || opts.reuseAnyVoice) && legacy[reading];
    if (reuse && opts.provider === 'supertonic3') {
      reused.push({ id: id, reading: reading, written: written, legacy: legacy[reading] });
      continue;
    }
    items.push({
      id: id,
      key: reading + '|' + written,
      reading: reading,
      written: written,
      shard: 0
    });
  }
  return {
    chunk: chunk,
    expected: rows.length,
    toGenerate: items,
    reused: reused,
    skippedValid: skippedValid,
    allReused: items.length === 0 && reused.length === rows.length && rows.length > 0
  };
}

function generatorCatalog(inv, chunk, plan) {
  var items = (plan.toGenerate || []).map(function (x) {
    return {
      id: x.id,
      key: x.key,
      reading: x.reading,
      written: x.written,
      shard: 0
    };
  });
  return {
    version: 1,
    status: 'catalog',
    engine: 'conj-chunk',
    inventoryVersion: inv.inventoryVersion,
    freezeHash: inv.freezeHash,
    chunk: chunk,
    // generate_word_supertonic_shard.py requires SHARD in range(shardCount).
    // One generation window is always shard 0 when there is anything to synthesize.
    shardCount: items.length ? 1 : 0,
    wordCount: items.length,
    items: items,
    words: items.reduce(function (o, x) { o[x.key] = [x.id, 0]; return o; }, {})
  };
}

function skipCheck(status, provider, voice, invVersion, chunk, releaseAssets) {
  var rec = getChunkRecord(status, provider, voice, invVersion, chunk);
  if (isChunkComplete(rec)) {
    var name = rec.persistedAsset || assetName(provider, voice, invVersion, chunk);
    if (rec.reused) {
      return { skip: true, reason: 'ALREADY COMPLETE', reused: true, record: rec };
    }
    if (!releaseAssets || releaseAssets.indexOf(name) >= 0 || rec.githubAvailable) {
      return { skip: true, reason: 'ALREADY COMPLETE', record: rec };
    }
  }
  return { skip: false, reason: 'NEED GENERATE', record: rec };
}

function validateTar(tarPath, expectedIds, opts) {
  opts = opts || {};
  var report = {
    ok: false,
    tar: tarPath,
    expectedCount: expectedIds.length,
    memberCount: 0,
    idsMatch: false,
    tarOpens: false,
    sha256: null,
    size: 0,
    nonZeroAudio: false,
    sampleDecode: opts.skipDecode ? 'skipped' : false,
    errors: []
  };
  if (!tarPath || !fs.existsSync(tarPath)) {
    report.errors.push('missing tar');
    return report;
  }
  var st = fs.statSync(tarPath);
  report.size = st.size;
  if (st.size < 1) report.errors.push('zero-size tar');
  report.sha256 = sha256(fs.readFileSync(tarPath));
  var listed = spawnSync('tar', ['-tf', tarPath], { encoding: 'utf8' });
  if (listed.status !== 0) {
    report.errors.push('tar did not open: ' + (listed.stderr || listed.status));
    return report;
  }
  report.tarOpens = true;
  var names = listed.stdout.split('\n').map(function (s) { return s.trim(); }).filter(Boolean);
  var stems = names.map(function (n) { return path.basename(n).replace(/\.mp3$/,''); });
  report.memberCount = stems.length;
  var expected = expectedIds.slice().sort();
  var got = stems.slice().sort();
  report.idsMatch = JSON.stringify(expected) === JSON.stringify(got);
  if (!report.idsMatch) report.errors.push('IDs mismatch expected ' + expected.length + ' got ' + got.length);

  var tv = spawnSync('tar', ['-tvf', tarPath], { encoding: 'utf8' });
  var zero = false;
  if (tv.status === 0) {
    tv.stdout.split('\n').forEach(function (line) {
      if (!line.trim()) return;
      var parts = line.trim().split(/\s+/);
      var size = parseInt(parts[2], 10);
      if (!isFinite(size) || size < 400) zero = true;
    });
  }
  report.nonZeroAudio = !zero && stems.length > 0;
  if (!report.nonZeroAudio) report.errors.push('zero or tiny audio member');

  if (!opts.skipDecode && report.tarOpens && stems.length) {
    var tmp = opts.decodeDir || path.join(path.dirname(tarPath), '.decode-sample');
    fs.mkdirSync(tmp, { recursive: true });
    var sample = names[0];
    var ex = spawnSync('tar', ['-xf', tarPath, '-C', tmp, sample], { encoding: 'utf8' });
    if (ex.status !== 0) {
      report.errors.push('sample extract failed');
    } else {
      var mp3 = path.join(tmp, sample);
      var ff = spawnSync('ffmpeg', ['-hide_banner','-loglevel','error','-i', mp3, '-f','null','-'], { encoding: 'utf8' });
      if (ff.status === 0) report.sampleDecode = true;
      else {
        report.sampleDecode = false;
        report.errors.push('sample decode failed');
      }
    }
  } else if (opts.skipDecode) {
    report.sampleDecode = 'skipped';
  }

  report.ok = report.tarOpens && report.idsMatch && report.nonZeroAudio && report.errors.length === 0 &&
    (report.sampleDecode === true || report.sampleDecode === 'skipped');
  return report;
}

module.exports = {
  SUPERTonic_VOICES, AIVIS_VOICES, PROVIDERS, sha256, padChunk, loadJson, writeJson,
  loadInventory, chunkReadings, freezeHashOf, assertFrozen, assetName, releaseTagFor,
  emptyStatus, ensureVoice, getChunkRecord, isChunkComplete, legacyReadingMap,
  planChunk, generatorCatalog, skipCheck, validateTar
};
