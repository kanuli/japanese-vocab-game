/* PLaMo 3 Translate browser adapter. No model or secret is embedded in GitHub Pages. */
(() => {
  'use strict';
  function endpoint() {
    const input = String(window.JapanesePlamoConfig?.endpoint || '').trim();
    if (!input) return '';
    try {
      const url = new URL(input);
      if (url.protocol !== 'https:' || url.username || url.password ||
          url.search || url.hash || !url.pathname.endsWith('/api/v1/translate/plamo')) return '';
      return url.href;
    } catch (_) { return ''; }
  }
  async function translate(text, targetLang) {
    const url = endpoint();
    if (!url) throw new Error('PLaMo endpoint is not configured');
    if (targetLang !== 'zh-hant' && targetLang !== 'en') throw new Error('Unsupported target language');
    if (typeof text !== 'string' || !text.trim() || text.length > 1800) throw new Error('Invalid text');
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 90000);
    try {
      const response = await fetch(url, {
        method: 'POST', mode: 'cors', credentials: 'omit', cache: 'no-store',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_lang: 'ja', target_lang: targetLang, text: text.trim() }),
        signal: controller.signal
      });
      if (!response.ok) throw new Error('PLaMo HTTP ' + response.status);
      const payload = await response.json();
      if (typeof payload.translation !== 'string' || !payload.translation.trim())
        throw new Error('Empty PLaMo translation');
      return payload.translation.trim();
    } finally {
      clearTimeout(timer);
    }
  }
  window.JapanesePlamoTranslator = Object.freeze({
    available: () => Boolean(endpoint()),
    translate
  });
})();
