#!/bin/sh
set -eu
node --check wordlist-conjugation.js
node --check wordlist-conjugation-ui.js
node --check wordlist.js
node wordlist-conjugation.test.js
node wordlist-conjugation.playwright.js
