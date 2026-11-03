#!/usr/bin/env bash
# Declare that the current thesis.typ matches the current OneDrive DOCX.
# Use after switching machines, when the shared DOCX is known to correspond to
# the current git checkout. This does not upload anything.
source "$(dirname "$0")/lib.sh"

require_configured_target

if ! shared_exists; then
  echo "No shared Word document found at:"
  echo "  $REMOTE_DOCX"
  echo "Check THESIS_REMOTE / THESIS_DOCX_NAME in .env."
  exit 1
fi

download_shared "$ROOT/.sync/review.docx"
cp "$ROOT/thesis.typ" "$ROOT/.sync/last-synced-thesis.typ"
sha "$ROOT/thesis.typ" > "$ROOT/.sync/last-synced-thesis.sha256"
sha "$ROOT/.sync/review.docx" > "$ROOT/.sync/last-pulled.sha256"
date -Iseconds > "$ROOT/.sync/last-adopt.txt"

echo "Adopted current thesis.typ as matching the shared DOCX."
echo "This did not upload or modify the DOCX."
