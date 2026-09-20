#!/bin/sh
# Deliberately requires a human acknowledgement of the release checklist.
set -eu
cd "$(dirname "$0")/.."
[ "$#" -eq 1 ] || { echo 'Usage: scripts/publish-template.sh ACTUAL_TEMPLATE_ID' >&2; exit 1; }
case "$1" in *[!a-zA-Z0-9_-]*|'') echo 'Invalid template identifier' >&2; exit 1;; esac
[ "${CC_PUBLISH_CHECKLIST_PASSED:-}" = "yes" ] || {
  echo 'Complete docs/ACCEPTANCE.md, then set CC_PUBLISH_CHECKLIST_PASSED=yes.' >&2
  exit 1
}
exec railway templates publish "$1" --category Bots   --description 'Self-hosted chat for humans and AI agents, with SQLite and password-first setup.'   --readme-file template/marketplace.md
