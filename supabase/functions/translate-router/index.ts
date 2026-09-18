import { createSupabaseContext } from 'npm:@supabase/server'

type TranslateRequest = {
  text?: string
  source?: string
  target?: string
}

const GOOGLE_MONTHLY_LIMIT = 480_000
const AZURE_MONTHLY_LIMIT = 1_950_000
const MAX_INPUT_CHARS = 20_000

function allowedOrigin(origin: string | null) {
  if (!origin) return true
  if (origin === 'https://kanuli.github.io') return true
  if (/^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(origin)) return true
  const extra = (Deno.env.get('TRANSLATOR_ALLOWED_ORIGINS') || '')
    .split(',')
    .map((v) => v.trim())
    .filter(Boolean)
  return extra.includes(origin)
}

function corsHeaders(origin: string | null) {
  const headers: Record<string, string> = {
    'Access-Control-Allow-Headers': 'apikey, authorization, x-client-info, content-type',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Vary': 'Origin',
  }
  if (origin && allowedOrigin(origin)) headers['Access-Control-Allow-Origin'] = origin
  return headers
}

function json(body: unknown, status: number, origin: string | null) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders(origin), 'Content-Type': 'application/json; charset=utf-8' },
  })
}

function codePointLength(text: string) {
  return Array.from(text).length
}

function monthKey() {
  return new Date().toISOString().slice(0, 7)
}

function normalizeTarget(target: string) {
  if (target === 'zh-TW' || target === 'zh-Hant') return 'zh-TW'
  if (target === 'en') return 'en'
  return null
}

function decodeEntities(text: string) {
  return text
    .replace(/&#(\d+);/g, (_m, n) => String.fromCodePoint(Number(n)))
    .replace(/&#x([0-9a-f]+);/gi, (_m, n) => String.fromCodePoint(parseInt(n, 16)))
    .replace(/&quot;/g, '"')
    .replace(/&#39;|&apos;/g, "'")
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&')
}

async function reserveQuota(
  supabaseAdmin: any,
  provider: string,
  chars: number,
  limit: number,
) {
  const { data, error } = await supabaseAdmin.rpc('reserve_translation_quota', {
    p_provider: provider,
    p_period: monthKey(),
    p_chars: chars,
    p_limit: limit,
  })
  if (error) {
    console.error(`quota reservation failed for ${provider}`, error)
    return false
  }
  return data === true
}

async function translateGoogle(text: string, target: string) {
  const key = Deno.env.get('GOOGLE_TRANSLATE_API_KEY')
  if (!key) throw new Error('GOOGLE_TRANSLATE_API_KEY is not configured')
  const response = await fetch(
    `https://translation.googleapis.com/language/translate/v2?key=${encodeURIComponent(key)}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ q: text, source: 'ja', target, format: 'text' }),
    },
  )
  const data = await response.json().catch(() => null)
  if (!response.ok) throw new Error(data?.error?.message || `Google HTTP ${response.status}`)
  const translated = data?.data?.translations?.[0]?.translatedText
  if (!translated) throw new Error('Google returned an empty translation')
  return decodeEntities(String(translated)).trim()
}

async function translateAzure(text: string, target: string) {
  const key = Deno.env.get('AZURE_TRANSLATOR_KEY')
  if (!key) throw new Error('AZURE_TRANSLATOR_KEY is not configured')
  const region = Deno.env.get('AZURE_TRANSLATOR_REGION') || ''
  const endpoint = (Deno.env.get('AZURE_TRANSLATOR_ENDPOINT') || 'https://api.cognitive.microsofttranslator.com')
    .replace(/\/$/, '')
  const azureTarget = target === 'zh-TW' ? 'zh-Hant' : target
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'Ocp-Apim-Subscription-Key': key,
    'X-ClientTraceId': crypto.randomUUID(),
  }
  if (region) headers['Ocp-Apim-Subscription-Region'] = region
  const response = await fetch(
    `${endpoint}/translate?api-version=3.0&from=ja&to=${encodeURIComponent(azureTarget)}`,
    {
      method: 'POST',
      headers,
      body: JSON.stringify([{ Text: text }]),
    },
  )
  const data = await response.json().catch(() => null)
  if (!response.ok) throw new Error(data?.error?.message || `Azure HTTP ${response.status}`)
  const translated = data?.[0]?.translations?.[0]?.text
  if (!translated) throw new Error('Azure returned an empty translation')
  return String(translated).trim()
}

export default {
  async fetch(req: Request) {
    const origin = req.headers.get('Origin')
    if (req.method === 'OPTIONS') {
      if (!allowedOrigin(origin)) return json({ error: 'origin_not_allowed' }, 403, origin)
      return new Response('ok', { headers: corsHeaders(origin) })
    }
    if (req.method !== 'POST') return json({ error: 'method_not_allowed' }, 405, origin)
    if (!allowedOrigin(origin)) return json({ error: 'origin_not_allowed' }, 403, origin)

    const { data: ctx, error: authError } = await createSupabaseContext(req, { auth: 'publishable' })
    if (authError || !ctx) {
      return json({ error: 'unauthorized', message: authError?.message || 'Invalid publishable key' }, authError?.status || 401, origin)
    }

    let body: TranslateRequest
    try {
      body = await req.json()
    } catch {
      return json({ error: 'invalid_json' }, 400, origin)
    }

    const text = String(body.text || '').trim()
    const source = String(body.source || 'ja')
    const target = normalizeTarget(String(body.target || ''))
    if (!text) return json({ error: 'empty_text' }, 400, origin)
    if (source !== 'ja') return json({ error: 'unsupported_source', message: 'Only Japanese source text is accepted.' }, 400, origin)
    if (!target) return json({ error: 'unsupported_target', message: 'Only zh-TW/zh-Hant and en are accepted.' }, 400, origin)

    const chars = codePointLength(text)
    if (chars > MAX_INPUT_CHARS) return json({ error: 'input_too_long' }, 413, origin)

    const attempts: Array<{ provider: string; error: string }> = []

    if (Deno.env.get('GOOGLE_TRANSLATE_API_KEY')) {
      const reserved = await reserveQuota(ctx.supabaseAdmin, 'google-nmt', chars, GOOGLE_MONTHLY_LIMIT)
      if (reserved) {
        try {
          const translation = await translateGoogle(text, target)
          return json({ translation, provider: 'google-nmt', source: 'ja', target }, 200, origin)
        } catch (error) {
          attempts.push({ provider: 'google-nmt', error: error instanceof Error ? error.message : String(error) })
        }
      } else attempts.push({ provider: 'google-nmt', error: 'monthly free-safety limit reached or quota tracking unavailable' })
    }

    if (Deno.env.get('AZURE_TRANSLATOR_KEY')) {
      const reserved = await reserveQuota(ctx.supabaseAdmin, 'azure-translator', chars, AZURE_MONTHLY_LIMIT)
      if (reserved) {
        try {
          const translation = await translateAzure(text, target)
          return json({ translation, provider: 'azure-translator', source: 'ja', target }, 200, origin)
        } catch (error) {
          attempts.push({ provider: 'azure-translator', error: error instanceof Error ? error.message : String(error) })
        }
      } else attempts.push({ provider: 'azure-translator', error: 'monthly free-safety limit reached or quota tracking unavailable' })
    }

    return json(
      {
        error: 'no_cloud_provider_available',
        message: 'Free cloud providers are unavailable or at their configured safety limits. Client should use Chrome Translator/MyMemory fallback.',
        attempts,
      },
      503,
      origin,
    )
  },
}
