// Public cloud-sync configuration for 日本語語音・翻譯.
// Supabase project URL and publishable/anon key are safe to expose in a browser app
// only when Row Level Security (RLS) is enabled with the policies in
// supabase/translation-sync.sql.
//
// Leave blank to configure from the page itself. Values entered in the page are
// stored only in that browser. Once a shared project is ready, these two public
// values can be committed here so every device only needs to sign in.
window.JP_TRANSLATOR_CLOUD_CONFIG = Object.freeze({
  url: '',
  anonKey: ''
});
