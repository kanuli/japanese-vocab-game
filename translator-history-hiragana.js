/* Japanese hiragana ruby for translation history.
 * Uses the existing offline kuromoji.js + ./dict, and safe DOM textContent.
 * No translations sent to an external service; no history data migration.
 */
(() => {
  'use strict';

  let tokenizer = null;
  let initPromise = null;
  const cache = new Map();
  const kanji = /[\u3400-\u9fff\uF900-\uFAFF々〆ヶ]/u;
  const kanaSuffix = /[ぁ-ゖァ-ヺー]/u;

  function toHiragana(value) {
    return String(value || '').replace(/[\u30a1-\u30f6]/g, ch =>
      String.fromCharCode(ch.charCodeAt(0) - 0x60));
  }
  function init() {
    if (tokenizer) return Promise.resolve(tokenizer);
    if (initPromise) return initPromise;
    if (!window.kuromoji?.builder) return Promise.resolve(null);
    initPromise = new Promise((resolve, reject) => {
      window.kuromoji.builder({dicPath: './dict/'}).build((err, result) => {
        if (err) reject(err);
        else { tokenizer = result; resolve(result); }
      });
    }).catch(err => {
      console.warn('Translation history ruby dictionary unavailable:', err?.message || err);
      initPromise = null;
      return null;
    });
    return initPromise;
  }
  function appendToken(fragment, token) {
    const surface = String(token.surface_form || '');
    const reading = token.reading && token.reading !== '*' ?
      toHiragana(token.reading) : '';
    if (!reading || !kanji.test(surface)) {
      fragment.appendChild(document.createTextNode(surface));
      return;
    }

    // Give the reading only above the kanji, leaving trailing okurigana below.
    // E.g. 食べる -> <ruby>食<rt>た</rt></ruby>べる
    let stemEnd = surface.length;
    while (stemEnd > 0 && kanaSuffix.test(surface[stemEnd - 1])) stemEnd--;
    const stem = surface.slice(0, stemEnd);
    const suffix = surface.slice(stemEnd);
    const hiraSuffix = toHiragana(suffix);
    let rubyBase = surface, rubyReading = reading, literalSuffix = '';
    if (stem && suffix && reading.endsWith(hiraSuffix)) {
      const candidate = reading.slice(0, -hiraSuffix.length);
      if (candidate) {
        rubyBase = stem;
        rubyReading = candidate;
        literalSuffix = suffix;
      }
    }

    const ruby = document.createElement('ruby');
    ruby.appendChild(document.createTextNode(rubyBase));
    const rt = document.createElement('rt');
    rt.textContent = rubyReading;
    ruby.appendChild(rt);
    fragment.appendChild(ruby);
    if (literalSuffix) fragment.appendChild(document.createTextNode(literalSuffix));
  }

  async function fill(element, source) {
    if (!element) return;
    const text = String(source || '');
    const serial = String((Number(element.dataset.rubySerial) || 0) + 1);
    element.dataset.rubySerial = serial;
    element.textContent = text; // useful even when tokenization unavailable
    if (!text || !kanji.test(text)) return;

    let tokens = cache.get(text);
    if (!tokens) {
      const t = await init();
      if (element.dataset.rubySerial !== serial) return;
      if (!t) return;
      try { tokens = t.tokenize(text); }
      catch (err) {
        console.warn('Translation history ruby failed:', err?.message || err);
        return; // keep unmodified Japanese
      }
      if (cache.size >= 200) cache.clear();
      cache.set(text, tokens);
    }
    if (element.dataset.rubySerial !== serial) return;
    const fragment = document.createDocumentFragment();
    for (const token of tokens) appendToken(fragment, token);
    element.replaceChildren(fragment);
  }

  function fillExisting() {
    document.querySelectorAll('#historyList .history-item .history-jp').forEach(
      element => fill(element, element.textContent));
  }

  window.TranslatorHistoryHiragana = Object.freeze({fill, fillExisting});
  if (document.readyState === 'loading')
    document.addEventListener('DOMContentLoaded', fillExisting, {once: true});
  else fillExisting();
})();
