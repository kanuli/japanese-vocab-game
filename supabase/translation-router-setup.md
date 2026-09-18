# Free multi-provider translation router setup

The website translation order is:

1. Google Cloud Translation NMT (Supabase Edge Function; monthly safety cap: 480,000 source characters)
2. Azure Translator (Supabase Edge Function; monthly safety cap: 1,950,000 source characters)
3. Chrome built-in Translator API (desktop Chrome, on-device)
4. MyMemory (last-resort public fallback)

The safety caps are intentionally below the advertised free monthly allowances. Google/Azure keys must never be committed to GitHub or placed in browser JavaScript.

## 1. Create quota table/function

Open Supabase Dashboard -> SQL Editor and run the complete contents of:

`supabase/translation-router.sql`

## 2. Add provider secrets

Open Supabase Dashboard -> Edge Functions -> Secrets and add only the providers you have configured:

- `GOOGLE_TRANSLATE_API_KEY`
- `AZURE_TRANSLATOR_KEY`
- `AZURE_TRANSLATOR_REGION`
- Optional: `AZURE_TRANSLATOR_ENDPOINT` (defaults to `https://api.cognitive.microsofttranslator.com`)
- Optional: `TRANSLATOR_ALLOWED_ORIGINS` for additional production origins, comma-separated.

Do not add Google/Azure keys to `translator-cloud-config.js`.

## 3. Deploy the Edge Function

Deploy `supabase/functions/translate-router/index.ts` as the `translate-router` function.

The repository also contains `supabase/config.toml` with `verify_jwt = false`; the function itself validates the browser publishable key using `@supabase/server`.

## 4. Test

Open `translator.html` and translate:

`大学教授は自分の研究をするとともに、学生たちを育てなければならない。`

The status line reports which provider produced the result.

Also regression-test:

- `高いからといって、品質がいいわけではない。`
- `雨が降るに伴って、気温も下がった。`
- `難しいものの、やってみる価値はある。`
- `彼が犯人に違いない。`
- `先生とともに会場へ向かった。`

## Cost-control behavior

The Edge Function reserves characters atomically before calling a cloud provider. When a safety cap would be exceeded, that provider is skipped. The browser then moves to the next provider. If quota tracking is unavailable, paid cloud providers fail closed and the browser falls back to Chrome/MyMemory instead of risking untracked usage.
