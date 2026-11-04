#!/usr/bin/env bash
# reanchor: repoint the DOCX marker at HEAD without changing the document.
#
# Needed when history was rewritten (rebase, amend, squash, force-push) and the
# old marker no longer names a commit. Safe because it uploads nothing unless
# the DOCX body already equals thesis.typ.
source "$(dirname "$0")/lib.sh"

require_target
shared_exists || die "no shared document at $(remote_label). Run: make init"

prepare_work
extract_review

read -r ins dels comments <<<"$(review_state "$WORK")"
if [[ "$ins" -ne 0 || "$dels" -ne 0 ]]; then
  die "the DOCX has $ins pending insertion(s) and $dels deletion(s).
Resolve the review first: make pull"
fi

if [[ -n "$(git status --porcelain -- thesis.typ)" ]]; then
  die "thesis.typ has uncommitted changes. Commit before re-anchoring."
fi

old="$(tag_get "$WORK")"
head="$(git rev-parse --short HEAD)"

note "Old marker: ${old:-(none)}"
note "New marker: $head"

if [[ "$old" == "$head" ]]; then
  note "Already anchored."
  exit 0
fi

if ! python3 "$ROOT/scripts/compare.py" thesis.typ "$REVIEW/accepted.md"; then
  die "the DOCX body and thesis.typ disagree. Re-anchoring would claim they match.
Sync the content first: make push"
fi

tag_set "$WORK" "$head"
note "Uploading ..."
upload_shared "$WORK"
mark_uploaded

note
note "Re-anchored: ${old:-none} -> $head"
