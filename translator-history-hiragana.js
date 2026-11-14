/* Hiragana readings for Japanese translation history only.
 * Uses this site's existing Japanese kuromoji tokenizer and local IPA dictionary.
 * Nothing is sent to an external phonetic service; user text is rendered via
 * textContent, never innerHTML, and no history/sync schema is changed.
 */
(() => {
  'use strict';

  const cache = new Map();
  let tokenizer = null;
  let initPromise = null;

  function toHiragana(value) {
    return String(value || '').replace(/[\u30a1-\u30f6]/g, ch =>
      String.fromCharCode(ch.charCodeAt(0) - 0x60));
  }
  function kanjiPresent(s) {
    return /[\u3400-\u9fff\uF900-\uFAFF々〆ヶ]/u.test(s);
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
      console.warn('Translation history hiragana dictionary unavailable:', err?.message || err);
      initPromise = null;
      return null;
    });
    return initPromise;
  }

  function composeReading(value, t) {
    const output = t.tokenize(value).map(token => {
      const surface = String(token.surface_form || '');
      const reading = token.reading && token.reading !== '*' ?
        String(token.reading) : surface;
      // Keep punctuation/latin text intact and convert Japanese readings.
      return toHiragana(reading);
    }).join('');
    return output || '';
  }

  async function fill(node, source) {
    if (!node) return;
    const text = String(source || '');
    const id = (Number(node.dataset.readingSerial || 0) + 1);
    node.dataset.readingSerial = String(id);
    if (!text.trim()) { node.textContent = ''; return; }
    if (!kanjiPresent(text)) {
      node.textContent = 'ひらがな：' + toHiragana(text);
      return;
    }
    let reading = cache.get(text);
    if (!reading) {
      node.textContent = 'ひらがな：讀音載入中…';
      const t = await init();
      if (node.dataset.readingSerial !== String(id)) return;
      if (!t) {
        node.textContent = 'ひらがな：讀音暫時無法生成';
        return;
      }
      try {
        reading = composeReading(text, t);
        if (!reading) throw new Error('No reading');
        if (cache.size >= 200) cache.clear();
        cache.set(text, reading);
      } catch (err) {
        console.warn('Translation history hiragana conversion failed:', err?.message || err);
        node.textContent = 'ひらがな：讀音暫時無法生成';
        return;
      }
    }
    if (node.dataset.readingSerial === String(id)) {
      node.textContent = 'ひらがな：' + reading;
    }
  }

  function fillExisting() {
    document.querySelectorAll('#historyList .history-item').forEach(item => {
      const jp = item.querySelector('.history-jp');
      const kana = item.querySelector('.history-hiragana');
      if (jp && kana) fill(kana, jp.textContent);
    });
  }

  window.TranslatorHistoryHiragana = Object.freeze({ fill, fillExisting });
  if (document.readyState === 'loading')
    document.addEventListener('DOMContentLoaded', fillExisting, {once: true});
  else fillExisting();
})();
