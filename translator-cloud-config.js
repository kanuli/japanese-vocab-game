// Public cloud-sync configuration for 日本語語音・翻譯.
//
// Passkey-first authentication is handled by translator-cloud-sync.js using
// Supabase Auth + WebAuthn. The Project URL and publishable/anon key are safe
// to expose in this browser app only when Row Level Security (RLS) is enabled
// with the policies in supabase/translation-sync.sql.
//
// IMPORTANT:
// - Never place a Supabase service-role / secret key in this repository.
// - Google/Azure translation secrets belong only in Supabase Edge Function Secrets.
// - Enable Authentication -> Passkeys in Supabase and configure the WebAuthn
//   RP ID / allowed origin for the actual website hostname/origin.
// - See supabase/passkey-setup.md for the one-time setup.
window.JP_TRANSLATOR_CLOUD_CONFIG = Object.freeze({
  url: 'https://qrznpvldluxxjbxdzeml.supabase.co',
  anonKey: 'sb_publishable_4lYT4c8o7fT7PbadkvJ4aA_KJT3pbTz'
});

// Keep the translation engine separate from the existing voice/history code.
// It rebinds only the Translate action after the page finishes loading.
(()=>{
  const s=document.createElement('script');
  s.src='./translator-translation-router.js?v=20260919v1';
  s.async=true;
  document.head.appendChild(s);
})();
