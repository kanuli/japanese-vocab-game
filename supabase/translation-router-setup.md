# Free no-card translation router setup

The website translation order is:

1. Gemini API Free Tier via Google AI Studio (Supabase Edge Function; grammar-aware primary engine)
2. Chrome built-in Translator API (on-device browser fallback)
3. MyMemory (last-resort public fallback)

This setup is designed for users who do **not** want to enter credit-card information. Do not enable Google Cloud Billing and do not upgrade the Gemini project to a paid tier.

## 1. Create quota table/function

Open Supabase Dashboard -> SQL Editor and run the complete contents of:

`supabase/translation-router.sql`

The router currently applies a site-side safety cap of 100,000 source characters per UTC day. This cap is only to reduce abuse of the public website; it is not a Google billing limit.

## 2. Create a Gemini Free API key

Open Google AI Studio and use a Free Tier project. New users can create/copy an API key without enabling paid billing.

Do **not** click `Set up billing` and do **not** add a payment method.

## 3. Add the Supabase secret

Open Supabase Dashboard -> Edge Functions -> Secrets and add:

- `GEMINI_API_KEY` = your Google AI Studio Gemini API key

Optional:

- `TRANSLATOR_ALLOWED_ORIGINS` = additional website origins, comma-separated.

Never add `GEMINI_API_KEY` to GitHub, `translator-cloud-config.js`, or browser JavaScript.

## 4. Deploy the Edge Function

Deploy `supabase/functions/translate-router/index.ts` as the `translate-router` function.

The repository contains `supabase/config.toml` with `verify_jwt = false`. The function accepts only the configured website origin(s), stores the Gemini key server-side, and uses the database quota guard.

The function tries free Gemini models in this order:

1. `gemini-3.5-flash`
2. `gemini-3.1-flash-lite`

If the Gemini Free Tier is unavailable, rate-limited, or reaches the site's safety cap, the browser automatically falls back to Chrome Translator and then MyMemory.

## 5. Test grammar-sensitive translation

Open `translator.html` and translate:

`大学教授は自分の研究をするとともに、学生たちを育てなければならない。`

The status line reports which provider produced the result.

Also regression-test:

- `高いからといって、品質がいいわけではない。`
- `雨が降るに伴って、気温も下がった。`
- `難しいものの、やってみる価値はある。`
- `彼が犯人に違いない。`
- `先生とともに会場へ向かった。`

## Zero-cost behavior

No paid cloud translation provider is required. If Gemini Free returns a quota/rate-limit error, the site does not upgrade or charge anything; it moves to free browser/public fallbacks instead.
