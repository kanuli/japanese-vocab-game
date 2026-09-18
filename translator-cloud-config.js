// Public cloud-sync configuration for 日本語語音・翻譯.
//
// Passkey-first authentication is handled by translator-cloud-sync.js using
// Supabase Auth + WebAuthn. The Project URL and publishable/anon key are safe
// to expose in this browser app only when Row Level Security (RLS) is enabled
// with the policies in supabase/translation-sync.sql.
//
// IMPORTANT:
// - Never place a Supabase service-role / secret key in this repository.
// - Enable Authentication -> Passkeys in Supabase and configure the WebAuthn
//   RP ID / allowed origin for the actual website hostname/origin.
// - See supabase/passkey-setup.md for the one-time setup.
//
// Leave blank to configure from the page itself. Once a shared Supabase project
// is ready, these two public values can be committed here so every device only
// needs Passkey authentication for normal use.
window.JP_TRANSLATOR_CLOUD_CONFIG = Object.freeze({
  url: '',
  anonKey: ''
});
