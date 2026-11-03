#!/usr/bin/env bash
# pull, step 1: fetch the shared DOCX and extract the supervisor's review.
# Step 2 (make pull-finish) runs after the agent applied the suggestions.
source "$(dirname "$0")/lib.sh"

require_target
shared_exists || die "no shared document at $(remote_label). Run: make init"

note "Downloading $(remote_label) ..."
prepare_work

note "Extracting comments and tracked changes ..."
extract_review
date -Iseconds > "$ROOT/.sync/last-pull.txt"

read -r ins dels comments <<<"$(review_state "$WORK")"
base="$(tag_get "$WORK")"

note
note "Document marker: ${base:-(none)}"
note "Tracked changes:  $ins insertion(s), $dels deletion(s)"
note "Comments:         $comments"

if [[ "$ins" -eq 0 && "$dels" -eq 0 && "$comments" -eq 0 ]]; then
  note
  note "Nothing to review."
  note "The DOCX content compared against thesis.typ:"
  note
  python3 "$ROOT/scripts/compare.py" thesis.typ "$REVIEW/accepted.md" || true
  note
  note "If that lists differences, the DOCX is behind thesis.typ: run make push."
  exit 0
fi

note
note "Review material:"
note "  review/comments.md   comments"
note "  review/tracked.md    tracked-change view"
note "  review/accepted.md   accepted-text view"
note
note "Next (agent):"
note "  1. apply every suggestion and comment to thesis.typ"
note "  2. accept the tracked changes in .sync/work.docx; keep all comments"
note "  3. make pull-finish"
