(function (root) {
  'use strict';

  var FORMS = [
    ['dict', '辭書形（原形）'],
    ['masu', 'ます形'],
    ['nai', 'ない形'],
    ['ta', 'た形'],
    ['te', 'て形'],
    ['potential', '可能形'],
    ['volitional', '意向形（意志形）'],
    ['imperative', '命令形'],
    ['prohibitive', '禁止形'],
    ['ba', '條件形（ば形）'],
    ['passive', '受身形（被動形）'],
    ['causative', '使役形'],
    ['causativePassive', '使役被動形']
  ];

  var GODAN_ROW = {
    'う': { i: 'い', a: 'わ', e: 'え', o: 'お', te: 'って', ta: 'った' },
    'く': { i: 'き', a: 'か', e: 'け', o: 'こ', te: 'いて', ta: 'いた' },
    'ぐ': { i: 'ぎ', a: 'が', e: 'げ', o: 'ご', te: 'いで', ta: 'いだ' },
    'す': { i: 'し', a: 'さ', e: 'せ', o: 'そ', te: 'して', ta: 'した' },
    'つ': { i: 'ち', a: 'た', e: 'て', o: 'と', te: 'って', ta: 'った' },
    'ぬ': { i: 'に', a: 'な', e: 'ね', o: 'の', te: 'んで', ta: 'んだ' },
    'ぶ': { i: 'び', a: 'ば', e: 'べ', o: 'ぼ', te: 'んで', ta: 'んだ' },
    'む': { i: 'み', a: 'ま', e: 'め', o: 'も', te: 'んで', ta: 'んだ' },
    'る': { i: 'り', a: 'ら', e: 'れ', o: 'ろ', te: 'って', ta: 'った' }
  };

  var GODAN_RU = {
    '帰る': 1, 'かえる': 1, '切る': 1, 'きる': 1, '知る': 1, 'しる': 1,
    '入る': 1, 'はいる': 1, '走る': 1, 'はしる': 1, '減る': 1, 'へる': 1,
    '要る': 1, '嘗る': 1, 'しゃべる': 1, '焦る': 1, 'あせる': 1,
    '限る': 1, 'かぎる': 1, '蹴る': 1, 'ける': 1, '滑る': 1, 'すべる': 1,
    '握る': 1, 'にぎる': 1, '参る': 1, 'まいる': 1, '交じる': 1, 'まじる': 1,
    '混じる': 1, '捻る': 1, 'ひねる': 1, '遮る': 1, 'さえぎる': 1,
    '罵る': 1, 'ののしる': 1, '湿る': 1, 'しめる': 1, '茂る': 1, 'しげる': 1,
    '散る': 1, 'ちる': 1, '練る': 1, 'ねる': 1, '照る': 1, 'てる': 1,
    '渋る': 1, 'しぶる': 1, '煎る': 1,
    '取る': 1, 'とる': 1, '撮る': 1, '採る': 1, '捕る': 1,
    '売る': 1, 'うる': 1, '折る': 1, 'おる': 1, '掘る': 1, 'ほる': 1,
    '彫る': 1, '頼る': 1, 'たよる': 1, '乗る': 1, 'のる': 1,
    '振る': 1, 'ふる': 1, '降る': 1, '詰まる': 1,
    '終わる': 1, 'おわる': 1, '当たる': 1, 'あたる': 1, '座る': 1, 'すわる': 1,
    '作る': 1, 'つくる': 1, '送る': 1, 'おくる': 1, '怒る': 1, 'おこる': 1,
    '戻る': 1, 'もどる': 1, '寄る': 1, 'よる': 1,
    '登る': 1, 'のぼる': 1, '上る': 1, '昇る': 1,
    '塗る': 1, 'ぬる': 1
  };

  var ICHIDAN_HINTS = {
    '食べる': 1, 'たべる': 1, '見る': 1, 'みる': 1, '起きる': 1, 'おきる': 1,
    '寝る': 1, 'ねる': 1, '教える': 1, 'おしえる': 1, '考える': 1, 'かんがえる': 1,
    '出る': 1, 'でる': 1, '入れる': 1, 'いれる': 1, '開ける': 1, 'あける': 1,
    '閉める': 1, 'しめる': 1, '始める': 1, 'はじめる': 1, '続ける': 1, 'つづける': 1,
    '生きる': 1, 'いきる': 1, '信じる': 1, 'しんじる': 1, '感じる': 1, 'かんじる': 1,
    'できる': 1, '出来る': 1, '借りる': 1, 'かりる': 1, '足りる': 1, 'たりる': 1,
    '降りる': 1, 'おりる': 1, '落ちる': 1, 'おちる': 1, '浴びる': 1, 'あびる': 1
  };

  function hira(s) {
    return String(s || '').replace(/[ァ-ヶ]/g, function (c) {
      return String.fromCharCode(c.charCodeAt(0) - 96);
    });
  }
  function posText(w) { return String((w && (w.pos || w.VocabPoS || w.partOfSpeech || w.type)) || ''); }
  function writtenOf(w) { return String((w && (w.kanji || w.displayWord || w.reading)) || ''); }
  function readingOf(w) { return hira(String((w && w.reading) || writtenOf(w))); }
  function isNonVerbPos(pos) {
    if (!pos) return false;
    if (/動詞|verb/i.test(pos)) return false;
    return /(名詞|副詞|助詞|接続詞|連体詞|感動詞|代名詞|数詞|noun|adverb|particle|conjunction|adjective|形容詞)/i.test(pos);
  }
  function classify(w) {
    var written = writtenOf(w), reading = readingOf(w), pos = posText(w);
    var form = written || reading, kana = reading || hira(form);
    if (isNonVerbPos(pos)) return null;
    if (form === 'ある' || kana === 'ある' || form === '有る' || form === '在る') return { type: 'aru', written: written || 'ある', reading: 'ある' };
    if (form === 'ない' || kana === 'ない') return null;
    if (form === '来る' || kana === 'くる' || form === 'くる') return { type: 'kuru', written: written || '来る', reading: 'くる' };
    if (form === 'する' || kana === 'する') return { type: 'suru', stem: '', kanaStem: '', written: 'する', reading: 'する' };
    if (/する$/.test(form) || /する$/.test(kana)) return { type: 'suru', stem: form.replace(/する$/, ''), kanaStem: kana.replace(/する$/, ''), written: written || form, reading: kana };
    var last = kana.slice(-1);
    var forcedIchidan = /一段|ichidan|ru[- ]?verb|上一段|下一段/i.test(pos);
    var forcedGodan = /五段|godan|u[- ]?verb/i.test(pos);
    var looksVerb = /動詞|verb/i.test(pos) || forcedIchidan || forcedGodan || last === 'る' || last in GODAN_ROW;
    if (!looksVerb) return null;
    if (form === '行く' || kana === 'いく' || form === 'いく' || kana === 'ゆく') return { type: 'iku', written: written || '行く', reading: kana === 'ゆく' ? 'ゆく' : 'いく' };
    if (last === 'る') {
      var isGodanRu = !!(GODAN_RU[form] || GODAN_RU[kana]);
      var isIchidanHint = !!(ICHIDAN_HINTS[form] || ICHIDAN_HINTS[kana]);
      var pre = kana.slice(-2, -1);
      var vowelRu = /[いえけげせぜてでねへべぺめれきぎしじちぢにひびぴみり]$/.test(pre);
      var ichidan = forcedIchidan || isIchidanHint || (!forcedGodan && !isGodanRu && vowelRu);
      if (forcedGodan || isGodanRu) ichidan = false;
      if (ichidan) return { type: 'ichidan', written: written || form, reading: kana };
      return { type: 'godan', ending: 'る', written: written || form, reading: kana };
    }
    if (last in GODAN_ROW) {
      if (forcedIchidan) return null;
      return { type: 'godan', ending: last, written: written || form, reading: kana };
    }
    return null;
  }
  function pair(written, reading) { return { written: written, reading: hira(reading || written) }; }
  function applyEnding(info, kanaEnding, writtenEnding) {
    var w = info.written, r = info.reading, we = writtenEnding == null ? kanaEnding : writtenEnding;
    if (info.type === 'ichidan') return pair(w.slice(0, -1) + we, r.slice(0, -1) + kanaEnding);
    if (info.type === 'godan' || info.type === 'iku') {
      var stemW = /[うくぐすつぬぶむる]$/.test(w) ? w.slice(0, -1) : w.slice(0, -1);
      return pair(stemW + we, r.slice(0, -1) + kanaEnding);
    }
    if (info.type === 'suru') return pair(info.stem + we, info.kanaStem + kanaEnding);
    if (info.type === 'kuru') {
      var map = { 'きます': '来ます', 'こない': '来ない', 'きた': '来た', 'きて': '来て', 'こられる': '来られる', 'こよう': '来よう', 'こい': '来い', 'くるな': '来るな', 'くれば': '来れば', 'こさせる': '来させる', 'こさせられる': '来させられる', 'くる': '来る' };
      var kanji = map[kanaEnding] || ('来' + we);
      if (w === 'くる') kanji = kanaEnding;
      return pair(kanji, kanaEnding);
    }
    return pair(we, kanaEnding);
  }
  function conjugate(w) {
    var info = classify(w); if (!info) return null;
    var out = {}; out.dict = pair(info.written, info.reading);
    if (info.type === 'ichidan') {
      out.masu = applyEnding(info, 'ます'); out.nai = applyEnding(info, 'ない'); out.ta = applyEnding(info, 'た'); out.te = applyEnding(info, 'て');
      out.potential = applyEnding(info, 'られる'); out.volitional = applyEnding(info, 'よう'); out.imperative = applyEnding(info, 'ろ');
      out.prohibitive = pair(info.written + 'な', info.reading + 'な'); out.ba = applyEnding(info, 'れば');
      out.passive = applyEnding(info, 'られる'); out.causative = applyEnding(info, 'させる'); out.causativePassive = applyEnding(info, 'させられる');
      return out;
    }
    if (info.type === 'godan') {
      var row = GODAN_ROW[info.ending]; if (!row) return null;
      out.masu = applyEnding(info, row.i + 'ます'); out.nai = applyEnding(info, row.a + 'ない');
      out.ta = applyEnding(info, row.ta); out.te = applyEnding(info, row.te);
      out.potential = applyEnding(info, row.e + 'る'); out.volitional = applyEnding(info, row.o + 'う');
      out.imperative = applyEnding(info, row.e); out.prohibitive = pair(info.written + 'な', info.reading + 'な');
      out.ba = applyEnding(info, row.e + 'ば'); out.passive = applyEnding(info, row.a + 'れる');
      out.causative = applyEnding(info, row.a + 'せる'); out.causativePassive = applyEnding(info, row.a + 'せられる');
      return out;
    }
    if (info.type === 'iku') {
      var g = { type: 'godan', ending: 'く', written: info.written, reading: info.reading }, r = GODAN_ROW['く'];
      out.masu = applyEnding(g, r.i + 'ます'); out.nai = applyEnding(g, r.a + 'ない');
      out.ta = applyEnding(g, 'った'); out.te = applyEnding(g, 'って');
      out.potential = applyEnding(g, r.e + 'る'); out.volitional = applyEnding(g, r.o + 'う');
      out.imperative = applyEnding(g, r.e); out.prohibitive = pair(info.written + 'な', info.reading + 'な');
      out.ba = applyEnding(g, r.e + 'ば'); out.passive = applyEnding(g, r.a + 'れる');
      out.causative = applyEnding(g, r.a + 'せる'); out.causativePassive = applyEnding(g, r.a + 'せられる');
      return out;
    }
    if (info.type === 'suru') {
      function s(k) { return pair(info.stem + k, info.kanaStem + k); }
      out.masu = s('します'); out.nai = s('しない'); out.ta = s('した'); out.te = s('して');
      out.potential = s('できる'); out.volitional = s('しよう'); out.imperative = s('しろ');
      out.prohibitive = s('するな'); out.ba = s('すれば'); out.passive = s('される');
      out.causative = s('させる'); out.causativePassive = s('させられる');
      return out;
    }
    if (info.type === 'kuru') {
      function k(x) { return applyEnding(info, x); }
      out.masu = k('きます'); out.nai = k('こない'); out.ta = k('きた'); out.te = k('きて');
      out.potential = k('こられる'); out.volitional = k('こよう'); out.imperative = k('こい');
      out.prohibitive = k('くるな'); out.ba = k('くれば'); out.passive = k('こられる');
      out.causative = k('こさせる'); out.causativePassive = k('こさせられる');
      return out;
    }
    if (info.type === 'aru') {
      out.masu = pair('あります', 'あります'); out.nai = pair('ない', 'ない');
      out.ta = pair('あった', 'あった'); out.te = pair('あって', 'あって');
      out.potential = null; out.volitional = pair('あろう', 'あろう'); out.imperative = pair('あれ', 'あれ');
      out.prohibitive = pair('あるな', 'あるな'); out.ba = pair('あれば', 'あれば');
      out.passive = null; out.causative = null; out.causativePassive = null;
      return out;
    }
    return null;
  }
  function canConjugate(w) { return !!classify(w); }
  var overlay, dialog, lastFocus, savedScroll, scrollEl, audioBusy = false;
  function qs(id) { return document.getElementById(id); }
  function ensureDom() {
    if (overlay) return;
    overlay = document.createElement('div');
    overlay.id = 'conjOverlay'; overlay.className = 'conj-overlay'; overlay.setAttribute('hidden', '');
    overlay.innerHTML = '<div class="conj-dialog" role="dialog" aria-modal="true" aria-labelledby="conjTitle" tabindex="-1"><div class="conj-sheet-handle" aria-hidden="true"></div><div class="conj-head"><h2 id="conjTitle">動詞活用</h2><button type="button" class="conj-close" aria-label="關閉">×</button></div><p class="conj-sub" id="conjSub"></p><div class="conj-list" id="conjList"></div></div>';
    document.body.appendChild(overlay);
    dialog = overlay.querySelector('.conj-dialog');
    overlay.addEventListener('click', function (e) { if (e.target === overlay) close(); });
    overlay.querySelector('.conj-close').addEventListener('click', close);
    document.addEventListener('keydown', function (e) {
      if (!overlay.classList.contains('is-open')) return;
      if (e.key === 'Escape') { e.preventDefault(); close(); }
      if (e.key === 'Tab') trap(e);
    });
  }
  function trap(e) {
    var nodes = dialog.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'), list = [];
    for (var i = 0; i < nodes.length; i++) if (!nodes[i].disabled) list.push(nodes[i]);
    if (!list.length) return;
    var first = list[0], last = list[list.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }
  function open(w, btn) {
    ensureDom();
    var forms = conjugate(w); if (!forms) return;
    lastFocus = btn || document.activeElement;
    scrollEl = document.querySelector('.table-wrap');
    savedScroll = scrollEl ? scrollEl.scrollTop : 0;
    var written = writtenOf(w), reading = readingOf(w);
    qs('conjSub').textContent = written + (reading && reading !== hira(written) ? '｜' + reading : '') + (w.meaning ? '｜' + w.meaning : '');
    var html = '';
    FORMS.forEach(function (pairForm) {
      var key = pairForm[0], label = pairForm[1], item = forms[key];
      if (!item) { html += '<div class="conj-row conj-row-na"><div class="conj-label">' + label + '</div><div class="conj-value">—</div></div>'; return; }
      html += '<div class="conj-row"><div class="conj-label">' + label + '</div><div class="conj-value"><span class="conj-written">' + esc(item.written) + '</span>' +
        (item.reading && item.reading !== hira(item.written) ? '<span class="conj-reading">' + esc(item.reading) + '</span>' : '') +
        '<button type="button" class="btn conj-audio-btn" data-speak="' + esc(item.reading || item.written) + '" aria-label="播放 ' + esc(item.written) + '">🔊</button></div></div>';
    });
    qs('conjList').innerHTML = html;
    qs('conjList').querySelectorAll('.conj-audio-btn').forEach(function (b) {
      b.addEventListener('click', function (ev) { ev.preventDefault(); ev.stopPropagation(); speak(b.getAttribute('data-speak'), w, b); });
    });
    overlay.hidden = false; overlay.classList.add('is-open'); overlay.setAttribute('aria-hidden', 'false'); dialog.focus();
  }
  function close() {
    if (!overlay) return;
    overlay.classList.remove('is-open'); overlay.hidden = true; overlay.setAttribute('aria-hidden', 'true');
    if (scrollEl) scrollEl.scrollTop = savedScroll || 0;
    if (lastFocus && lastFocus.focus) try { lastFocus.focus(); } catch (e) {}
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; });
  }
  async function speak(text, w, btn) {
    var WA = root.WA; if (!WA || !WA.speak || audioBusy) return;
    audioBusy = true; if (btn) btn.disabled = true;
    try { await WA.speak(text, { reading: text, kanji: '', displayWord: text }); } catch (e) {}
    audioBusy = false; if (btn) btn.disabled = false;
  }
  var api = { canConjugate: canConjugate, conjugate: conjugate, classify: classify, open: open, close: close, FORMS: FORMS };
  root.WordlistConjugation = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
