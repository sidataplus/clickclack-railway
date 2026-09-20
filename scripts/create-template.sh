#!/bin/sh
# Snapshot a linked live project into an UNPUBLISHED Railway template draft.
# The draft may inherit real credentials. Sanitize in the composer before publish.
set -eu
cd "$(dirname "$0")/.."
command -v railway >/dev/null 2>&1 || { echo 'Railway CLI is required.' >&2; exit 1; }
umask 077
mkdir -p .local
if [ -e .local/template-create.json ]; then
  echo 'Existing template-create.json found; inspect it instead of creating duplicate drafts.' >&2
  exit 1
fi
# noclobber protects any existing local result. Do not print potentially sensitive JSON.
set -C
railway templates create --json > .local/template-create.json
printf '%s\n' 'Draft response saved privately in .local/template-create.json.'   'Open its template in Railway; replace copied email/password with per-deployment inputs.'   'Do NOT publish until a sanitized draft passes docs/ACCEPTANCE.md.'
