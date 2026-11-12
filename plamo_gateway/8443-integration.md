# PLaMo on existing Japanese API HTTPS 8443 — draft integration

**Feature branch only. Do not merge, restart, or modify production without a staged compatibility test.**

## Why 8443 rather than 8445

iPhone on Wi-Fi successfully reaches the existing `kanu-rustdesk.synology.me:8443` Japanese API, while the standalone `8445` cannot be reached via the public DNS address. The Windows Hosts override forces the domain to `192.168.1.4`, which does not apply on iOS. No iPhone settings or router port-forward/DNS changes are required for this plan.

## Intended flow

`GitHub Pages -> HTTPS 8443 -> current FastAPI app (Docker) -> /api/v1/translate/plamo -> mounted Unix socket /run/plamo-gateway/gateway.sock -> NAS-host Gateway -> Windows LAN 192.168.1.13:18789 -> model`

**Critical network boundary fixed in draft:** Container `127.0.0.1` is not the NAS-host loopback. The draft FastAPI router uses a Unix-domain socket instead of trying to dial `127.0.0.1:18790`. The NAS Gateway retains its existing loopback HTTP listener for LAN 8445 tests and gains an opt-in `PLAMO_UNIX_SOCKET` listener. No new TCP listener is opened.

Supabase login token is read in-memory from the existing translator Cloud Sync client and sent in the Authorization header. The FastAPI route never validates an unsigned JWT by itself: the existing NAS loopback Gateway validates the token remotely with Supabase, checks the allowlisted UUID and applies the per-UID quota.

## Files staged in PR #14

- `plamo_gateway/gateway.py`: optional Unix-domain socket listener on the NAS host, configured only by `PLAMO_UNIX_SOCKET=/volume2/docker/japanese-api/plamo-gateway-run/gateway.sock`. The socket parent directory is private; the file is `0600`. Existing localhost `18790` behavior is retained.
- `plamo_gateway/japanese_api_router.py`: isolated FastAPI `APIRouter` with one POST translation path and OPTIONS route. It enforces a strict JSON schema/size and a conservative pre-auth, in-memory rate/concurrency cap before proxying to the local Gateway.
- `plamo_gateway/test_japanese_api_router.py`: mocked route-level tests. Must run **inside the Japanese API runtime environment**, not only NAS system Python 3.8.
- `translator-plamo-config.js`: points to `https://kanu-rustdesk.synology.me:8443/api/v1/translate/plamo` on **staging branch only**. Published GitHub Pages `main` is unchanged.
- `translator-cloud-sync.js` and `translator-plamo-client.js`: reuse existing Supabase session; no private keys in frontend.

## Predeployment gates (mandatory)

1. Inspect actual NAS `/volume2/docker/japanese-api/app/main.py` and `compose.yaml`. The source does **not** currently live in this GitHub repository, so the router has **NOT** yet been mounted in FastAPI. Confirm the code is built into container vs mounted, the app import path, Python version and dependency versions.
2. Run syntax, 11 HTTP mock tests including actual AF_UNIX transfer, in a temporary container using the actual Japanese API image, `--network none`, no restart/change of production. The original 10 tests passed on 2026-11-12. The new UDS test is pending.
3. Before attempting to enable Unix sockets on the NAS Gateway, back up the exact running `gateway.py` and record its process launch/environment without exposing secrets. The existing Gateway must be gracefully stopped/restarted under a controlled maintenance step to add the Unix listener; avoid two concurrent processes on port 18790.
4. Create the private NAS directory `/volume2/docker/japanese-api/plamo-gateway-run/` mode 0700. Bind mount it into **Japanese API container** as `/run/plamo-gateway:ro` in Compose. Since Docker is using `build: .`, add the router file to the app tree before building the new image. Do not open new NAS LAN ports.
5. Ensure the NAS Gateway restarts with the opt-in `PLAMO_UNIX_SOCKET` environment setting and confirm that the real mounted UDS works from the test image before activating the route.
6. Inspect CORS middleware order/configuration: preflight OPTIONS must allow Origin `https://kanuli.github.io`, methods POST, and headers Authorization, Content-Type. Ensure no secrets/tokens are logged.
7. Before touching production: take a timestamped backup of original `main.py`, Compose configuration, existing image ID, and router file (if any), and prepare a rollback that only restores changed files.
8. Stage the addition using FastAPI `app.include_router(router)` after app initialization, without changing existing vocabulary/audio/conjugation routes. Ensure the new `/api/v1/translate/plamo` does not collide with an existing route.
9. Only with authorized maintenance window, deploy the isolated router, restart/recreate only `japanese-api` if required by its current installation method, then verify all existing GET health, status, voices, vocabulary/audio endpoints.
10. Test HTTPS 8443: no token=401, bad Origin=403, bad token=401, allowed CORS preflight, real signed-in account JA→zh-hant/en, approved 30/15min per-UID limits, failure fallback MyMemory.
11. Verify *actual* network-layer abusive traffic controls. The outer FastAPI in-memory pre-auth quotas and the NAS Gateway per-UID quotas are additional layers, **not a robust multi-process distributed rate limiter**; do not claim independent Nginx rate limiting without checking effective config. Consider reverse-proxy edge-rate limiting for full public internet exposure.
12. Confirm that a remote user on mobile data can reach the *existing* 8443 URL (previously proven) and that PLaMo access is only granted to the allowlisted Supabase account.
13. Only merge into main after all security, regressions and quality checks pass. MyMemory remains the default and fallback.

## Guardrails

- Do not modify iPhone, iPad, NordVPN, RAX70 DNS/DHCP/port forwards or Windows Hosts.
- Do not expose `18790` or `18789` to WAN. Keep existing 8445 LAN-only setup untouched until later cleanup is authorized.
- Do not edit DSM-generated `server.ReverseProxy.conf` directly.
- Do not copy account access tokens into chat, source control, files, logs, curl command arguments, or shell history.
- Stop before production deploy if actual `compose.yaml` indicates an image-only code path not covered by the patch.

## Current status

The above files are **staged only** in draft PR #14. We have prior independent evidence that the NAS standalone Gateway authenticates the signed-in Supabase user and translates both languages. We do *not* yet have an 8443 live route or iPhone PLaMo translation test.
