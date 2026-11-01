#!/usr/bin/env bash
# Upload the edited .sync/review.docx back to OneDrive and mark it as seen.
source "$(dirname "$0")/lib.sh"

require_configured_target

if [[ ! -f "$ROOT/.sync/review.docx" ]]; then
  echo "No .sync/review.docx found. Run 'make pull' first."
  exit 1
fi

echo "Uploading the edited DOCX ..."
upload_shared "$ROOT/.sync/review.docx"

sha "$ROOT/.sync/review.docx" > "$ROOT/.sync/last-pulled.sha256"
sha "$ROOT/thesis.typ" > "$ROOT/.sync/last-synced-thesis.sha256"
date -Iseconds > "$ROOT/.sync/last-upload.txt"

echo "Uploaded:"
echo "  $REMOTE_DOCX"
