#!/usr/bin/env bash
# pull, step 2: verify, record the marker, upload, commit.
# Runs after the agent applied the suggestions to thesis.typ and accepted them
# in the DOCX. Nothing is uploaded unless the two surfaces agree.
source "$(dirname "$0")/lib.sh"

require_target
[[ -f "$WORK" ]] || die "no .sync/work.docx — run: make pull"

extract_review
read -r ins dels comments <<<"$(review_state "$WORK")"

if [[ "$ins" -ne 0 || "$dels" -ne 0 ]]; then
  die "the DOCX still has $ins insertion(s) and $dels deletion(s).
Accept the tracked changes first (docx-mcp: accept_changes). Comments stay."
fi

note "Gate: comparing the DOCX body with thesis.typ ..."
python3 "$ROOT/scripts/compare.py" thesis.typ "$REVIEW/accepted.md" || die \
  "the DOCX body and thesis.typ disagree. Nothing was uploaded."

if [[ -n "$(git status --porcelain -- thesis.typ)" ]]; then
  note "Committing thesis.typ ..."
  git add thesis.typ
  git commit -m "Apply supervisor review" \
    --trailer "Assisted-by: OpenCode:deepseek-flash" \
    --quiet -- thesis.typ
else
  note "thesis.typ is unchanged; nothing to commit."
fi

head="$(git rev-parse --short HEAD)"
tag_set "$WORK" "$head"

note "Uploading ..."
upload_shared "$WORK"
mark_uploaded
date -Iseconds > "$ROOT/.sync/last-upload.txt"

note
note "Synced. Marker: $head   comments kept: $comments"
note "Git: $(git log -1 --format='%h %s') (not pushed)"
