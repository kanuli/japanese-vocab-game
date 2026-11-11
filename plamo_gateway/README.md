# PLaMo NAS HTTPS Gateway — staging

**Status: code only. Not installed, started, publicly exposed, or production-authorized.**

The Synology NAS uses Python 3.8.15. This gateway uses only Python 3.8 standard-library modules and does not need Docker, pip, sudo, or a new visible Windows terminal.

Topology:
- GitHub Pages frontend (staging branch): bearer session token from existing Supabase login.
- NAS HTTPS reverse proxy **to be configured later**.
- NAS private gateway `127.0.0.1:18790`.
- Existing Windows LAN bridge `192.168.1.13:18789`, restricted in Windows Firewall to NAS `192.168.1.4`.
- PLaMo model remains bound to PC loopback `127.0.0.1:8000`.

## Security gates

1. **Do not publish NAS port 18790.** The Python gateway listens on NAS loopback only; it is not a TLS server. Do not open router port forwarding or run it on `0.0.0.0`.
2. Requests to the translation route require `Authorization: Bearer <Supabase access token>` from the existing signed-in browser session.
3. The gateway calls Supabase `GET /auth/v1/user` over HTTPS to validate that token and retrieve the authenticated user ID. A user-supplied ID in the request body is never trusted.
4. Only explicitly allowlisted Supabase account UUIDs can translate. If configuration is absent, the service fails to start.
5. Per-UID quota is 30 translations per rolling 15-minute window per running gateway process; concurrency is capped at two. These are *supplementary* guards, **not enough as the only internet-facing rate limit**. Configure per-IP request rate, connection cap, max request body, timeout and TLS on the outer reverse proxy.
6. `Origin` is restricted to `https://kanuli.github.io` for browser CORS, but CORS alone is not access control. Bearer token verification is mandatory.
7. No user translation text or bearer tokens are logged. Avoid debug logging of request bodies at reverse proxy.
8. The upstream Windows PC is a fixed private IP; no user-provided URLs are accepted.
9. HTTPS route placement on the Synology DSM-managed reverse proxy has not been determined; do **not** edit generated `server.ReverseProxy.conf` or restart Nginx without a separate rollback and backup procedure.
10. A proxy design must preserve existing HTTPS 8443 Japanese API, 443 and 8444 routes without regressions.

## Offline staging tests (safe now)

```sh
python3 -m unittest discover -s ~/plamo-gateway-staging -p 'test_*.py' -v
```

No credentials or model are required for these offline tests. They use mocked authentication and translation.

## Environment for future private deployment

Use a protected local NAS configuration file (NOT GitHub and NOT pasted into chat):

```text
PLAMO_SUPABASE_URL=https://YOUR-PROJECT.supabase.co
PLAMO_SUPABASE_PUBLISHABLE_KEY=<public publishable or anon key>
PLAMO_ALLOWED_USER_IDS=<comma-separated allowlisted Supabase user UUID(s)>
PLAMO_GATEWAY_PORT=18790
```

`PLAMO_SUPABASE_PUBLISHABLE_KEY` is **not** a service-role key. Never store a service-role key in public frontend code. The trusted HTTPS Supabase endpoint verifies each user access token. When not configured, the gateway refuses to start. A new account's UID can be obtained after signing into Supabase; never paste bearer tokens to ChatGPT.

To verify configuration without revealing values, run `python3 -m py_compile gateway.py` first, then offline tests. Only after authentication settings, HTTPS proxy access controls, and authorization are validated should the private service be started and tested.

## Frontend staging work

On feature branch `feature/plamo3-translate-staging-20261110`:
- `translator-cloud-sync.js` exposes an in-memory method returning the existing Supabase access token; it does not log the token or embed any new secret.
- `translator-plamo-client.js` sends the bearer token only to its configured HTTPS translation endpoint.
- `translator-plamo-config.js` remains **empty** (PLaMo disabled) until the HTTPS gateway is securely available.
- `translator.html` keeps MyMemory as default and as fallback.

The public website is **not changed**. The existing PLaMo Windows and NAS LAN connection tests remain valid but **do not** prove that a protected public endpoint is ready.
