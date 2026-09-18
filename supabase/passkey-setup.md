# 日本語語音・翻譯 — Passkey cloud sync setup

The translator uses Supabase Auth + WebAuthn Passkeys for cross-device history sync.

## 1. Create the sync table

Run `supabase/translation-sync.sql` once in the Supabase SQL editor.

## 2. Enable Passkeys

In Supabase Dashboard:

- Authentication → Passkeys → Enable Passkey authentication
- Relying Party display name: `Japanese Learning`
- Relying Party ID: use the hostname that serves the site. For the default GitHub Pages deployment this is normally `kanuli.github.io`.
- Allowed origin: use the exact HTTPS origin that serves the site. For the default GitHub Pages deployment this is normally `https://kanuli.github.io`.

Do not include `/japanese-vocab-game/` in the RP ID or origin; WebAuthn binds to the origin/hostname, not the path.

If a custom domain is added later, update these settings before enrolling production passkeys. Changing RP ID makes previously enrolled passkeys unusable.

## 3. Configure Auth URL redirects

Add the deployed translator URL to Supabase Authentication URL configuration / redirect allow list, for example:

`https://kanuli.github.io/japanese-vocab-game/translator.html`

This is only needed for the one-time Email magic-link bootstrap / recovery flow. Normal sign-in is Passkey-first and does not ask for Email.

## 4. Add the public project settings

Put the Supabase Project URL and Publishable/anon key into `translator-cloud-config.js`.

These values are public browser configuration, not a service-role secret. Never put a Supabase service-role / secret key into this repository.

## 5. First enrollment

1. Open 日本語語音・翻譯.
2. Open `☁️ 跨裝置同步`.
3. Use `首次設定 / 備援` and send the Email magic link once.
4. Open the magic link and return to the translator.
5. Press `➕ 建立 Passkey`.
6. Save it using Apple Passwords, Windows Hello, or another WebAuthn password manager/authenticator.

## 6. Normal use on another device

Open the same translator page and press `🔑 Passkey 登入`. No Email or username is required for normal Passkey authentication. Translation history is then merged/synchronized with the cloud state.

## Security

`translation_sync_state` uses Row Level Security. Authenticated users may only select/insert/update/delete the row whose `user_id` matches `auth.uid()`.
