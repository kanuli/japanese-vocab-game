#!/bin/sh
set -eu
node --check wordlist-conjugation.js
node --check wordlist-conjugation-ui.js
node --check wordlist.js
node --check wordaudio-multivoice.js
node --check wordaudio-delta-voices.js
node wordlist-conjugation.test.js
node wordlist-conjugation-catalog.test.js
node scripts/audit_conjugation_hosted_catalogs.js
node wordlist-conjugation.playwright.js
node wordlist-conjugation-hosted.playwright.js
