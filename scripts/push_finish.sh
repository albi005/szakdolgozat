#!/usr/bin/env bash
# push, step 2: verify, record the marker, push git, upload.
# Runs after the agent applied review/pending.md to .sync/work.docx.
source "$(dirname "$0")/lib.sh"

require_target
[[ -f "$WORK" ]] || die "no .sync/work.docx — run: make push"

extract_review
read -r ins dels comments <<<"$(review_state "$WORK")"
if [[ "$ins" -ne 0 || "$dels" -ne 0 ]]; then
  die "the DOCX has $ins insertion(s) and $dels deletion(s) after the edits.
Author edits must be recorded with tracked=False, not as revisions."
fi

if [[ -n "$(git status --porcelain -- thesis.typ)" ]]; then
  die "thesis.typ has uncommitted changes. Commit first: the marker records a commit."
fi

if ! git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
  die "the current branch has no upstream. Set one with: git push -u origin HEAD"
fi

note "Gate: comparing the DOCX body with thesis.typ ..."
python3 "$ROOT/scripts/compare.py" thesis.typ "$REVIEW/accepted.md" || die \
  "the DOCX body and thesis.typ disagree. Nothing was pushed or uploaded."

head="$(git rev-parse --short HEAD)"
note "Pushing git ($head) ..."
git push

tag_set "$WORK" "$head"
note "Uploading ..."
upload_shared "$WORK"
sha "$WORK" > "$ROOT/.sync/last-seen.sha256"
date -Iseconds > "$ROOT/.sync/last-upload.txt"

note
note "Synced. Marker: $head   comments kept: $comments"
