# PLaMo 3 Translate 2B — staging integration

Status: **CODE PREPARED / NOT DEPLOYED / NOT VERIFIED AGAINST A REAL MODEL**.

This branch adds an optional PLaMo translation source to `translator.html` and a separate local Python bridge. It does **not** alter the NAS, Windows PC, production GitHub Pages, MyMemory service, or translation history schema.

## Architecture

```
PC / iPhone / iPad browser (GitHub Pages)
  -> configured HTTPS reverse proxy (not yet installed)
     -> plamo_bridge/bridge.py :8788 (loopback/private IP)
        -> llama-server :8000 (loopback)
           -> pfnet/plamo-3-translate-2b-Q4_K_M.gguf
```

The model runs on the host, **not on each device**. Mobile devices need no downloaded model. The server machine must remain available while translations are requested.

The site defaults to **MyMemory**. The PLaMo option is **disabled** until `translator-plamo-config.js` contains a valid HTTPS endpoint ending in `/api/v1/translate/plamo`. If a configured PLaMo API fails, the page labels the fallback and retries with MyMemory. This is deliberately not enabled on production yet.

## Local PC setup (later, when at home)

1. Install a current GPU-enabled llama.cpp containing `llama-server`; verify that `llama-server --help` works. Follow the [official PFN GGUF model card](https://huggingface.co/pfnet/plamo-3-translate-2b-GGUF) rather than an unverified model source.
2. Download the official Q4_K_M file (~1.81 GB):

```powershell
py -m pip install -U huggingface_hub
hf download pfnet/plamo-3-translate-2b-GGUF plamo-3-translate-2b-Q4_K_M.gguf --local-dir plamo-model
```

3. In a dedicated terminal in the model folder start the upstream server:

```powershell
llama-server -m plamo-3-translate-2b-Q4_K_M.gguf -c 16384 --host 127.0.0.1 --port 8000 --alias plamo-3-translate --jinja --no-prefill-assistant
```

4. In a second terminal from this repository start the bridge:

```powershell
py plamo_bridge/bridge.py
```

5. In a third terminal (or with a REST client) verify locally:

```powershell
Invoke-RestMethod http://127.0.0.1:8788/healthz

$payload = @{
  text = '大学教授は自分の研究をするとともに、学生たちを育てなければならない。'
  source_lang = 'ja'
  target_lang = 'zh-hant'
} | ConvertTo-Json
Invoke-RestMethod -Uri 'http://127.0.0.1:8788/api/v1/translate/plamo' -Method Post -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($payload))
```

`/healthz` checks the bridge process only; it deliberately returns `model: not_checked`, not a misleading readiness signal.

## Before enabling access from any browser

**DO NOT publish port 8000 or 8788 directly to the internet.** The sample bridge is a local backend and is **not** a complete public security boundary. An Origin/CORS check cannot authenticate requests; non-browser clients can spoof or omit Origin.

Deploy a protected HTTPS reverse proxy that forwards **only** `POST /api/v1/translate/plamo` to the bridge. Enforce TLS, access control as appropriate, request-size and per-IP quotas, concurrency limits and logs that omit submitted text. Do not proxy arbitrary LLM routes or add API credentials to public JavaScript. Consider the existing NAS authentication/network configuration before exposure.

If the model and API run on a Windows PC but the existing reverse proxy runs on the NAS, use a separately designed protected tunnel/private network. Do not widen Windows firewall exposure simply to make the demo work. By default the bridge binds to 127.0.0.1; an explicitly selected private LAN IP can be configured via `PLAMO_BIND_HOST` after a security review. Wildcard and public binds are rejected.

Once the protected endpoint works on HTTPS **and** CORS preflight permits `https://kanuli.github.io`, place only its public URL in:

```javascript
window.JapanesePlamoConfig = Object.freeze({
  endpoint: 'https://YOUR-TRUSTED-ENDPOINT/api/v1/translate/plamo'
});
```

Do not place any secret in that file. Enable the PLaMo UI through the configuration (it is automatically disabled when the endpoint is empty). Verify both `ja -> zh-hant` and `ja -> en` from Windows, iPhone and iPad.

## Offline tests

From repository root:

```powershell
py -m unittest discover -s plamo_bridge -p "test_*.py" -v
```

These tests mock the model API and check request validation, CORS, output shape and health semantics. **Passing them is not evidence of translation accuracy or connectivity to the 1.81 GB model.**

## Acceptance gate before merging / switching the default

- Actual model launches without memory/resource conflict or unwanted Windows desktop interference.
- Real model translations for Japanese→Traditional Chinese and English work through HTTPS on PC and iPhone.
- Compare at least 50 real source sentences against the existing MyMemory outputs with blind review (grammar, omissions, traditional characters, jargon, fluency).
- Confirm model license obligations, uptime, latency, privacy, and rate limiting.
- Retain MyMemory as a clearly labeled fallback.
- Explicit approval before setting PLaMo as default or changing production NAS.

Official source: [Preferred Networks PLaMo 3 Translate GGUF](https://huggingface.co/pfnet/plamo-3-translate-2b-GGUF); model is under **PLaMo Community License**, separate from the license of any browser extension.
