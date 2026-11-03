#!/usr/bin/env bash
# Show thesis.typ changes since the last successful DOCX upload.
source "$(dirname "$0")/lib.sh"

if [[ ! -f "$ROOT/.sync/last-synced-thesis.typ" ]]; then
  echo "No sync snapshot yet. The first 'make upload' creates it."
  exit 0
fi

if cmp -s "$ROOT/.sync/last-synced-thesis.typ" "$ROOT/thesis.typ"; then
  echo "No local Typst changes since the last upload."
  exit 0
fi

diff -u "$ROOT/.sync/last-synced-thesis.typ" "$ROOT/thesis.typ" || true
