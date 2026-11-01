#!/usr/bin/env bash
# Download the shared DOCX and extract suggestions/comments for manual review.
# This does NOT modify thesis.typ or the DOCX.
source "$(dirname "$0")/lib.sh"

require_configured_target

if ! shared_exists; then
  echo "No shared Word document found at:"
  echo "  $REMOTE_DOCX"
  echo "Check THESIS_REMOTE / THESIS_DOCX_NAME in .env."
  exit 1
fi

mkdir -p "$ROOT/.sync" "$ROOT/review"

echo "Downloading review copy ..."
download_shared "$ROOT/.sync/review.docx"

echo "Extracting suggestions and comments ..."
pandoc "$ROOT/.sync/review.docx" --track-changes=accept \
  -t markdown --wrap=none -o "$ROOT/review/accepted.md"
pandoc "$ROOT/.sync/review.docx" --track-changes=all \
  -t markdown --wrap=none -o "$ROOT/review/tracked.md"
pandoc "$ROOT/.sync/review.docx" --track-changes=all \
  -t json -o "$ROOT/.sync/review.json"
python3 "$ROOT/scripts/extract_review.py" \
  "$ROOT/.sync/review.json" "$ROOT/review/comments.md"

sha "$ROOT/.sync/review.docx" > "$ROOT/.sync/last-pulled.sha256"
date -Iseconds > "$ROOT/.sync/last-pull.txt"

echo
echo "Review extracted to:"
echo "  review/comments.md   comments + tracked changes"
echo "  review/tracked.md    tracked-change view"
echo "  review/accepted.md   accepted text view"
echo
echo "Next: apply the accepted suggestions to thesis.typ, accept them in the"
echo "DOCX with docx-mcp, and upload the same DOCX."
