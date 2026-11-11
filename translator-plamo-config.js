/* DRAFT PR ONLY. Route remains unavailable until the NAS Japanese API
 * explicitly mounts plamo_gateway/japanese_api_router.py on HTTPS 8443
 * and end-to-end tests pass. Never put Supabase service secrets here.
 * Do not merge this change into published GitHub Pages prematurely. */
window.JapanesePlamoConfig = Object.freeze({
  endpoint: "https://kanu-rustdesk.synology.me:8443/api/v1/translate/plamo"
});
