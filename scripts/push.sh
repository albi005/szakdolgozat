#!/usr/bin/env bash
# push, step 1: fetch the DOCX, read its sync marker, and write the worklist
# of thesis.typ changes the DOCX is missing.
# Step 2 (make push-finish) runs after the agent applied the worklist.
source "$(dirname "$0")/lib.sh"

require_target
shared_exists || die "no shared document at $(remote_label). Run: make init"

note "Downloading $(remote_label) ..."
prepare_work
extract_review

read -r ins dels comments <<<"$(review_state "$WORK")"
if [[ "$ins" -ne 0 || "$dels" -ne 0 ]]; then
  die "the DOCX has $ins pending insertion(s) and $dels deletion(s).
Resolve them first: make pull"
fi

base="$(tag_get "$WORK")"
head="$(git rev-parse --short HEAD)"

commits=""
if [[ -n "$base" ]]; then
  git cat-file -e "${base}^{commit}" 2>/dev/null ||
    die "the DOCX marker ($base) is not a commit in this repository.
History was rewritten, or the DOCX was synced elsewhere. If the content already
matches, re-anchor the marker: make reanchor"
  git merge-base --is-ancestor "$base" HEAD ||
    die "history was rewritten since $base (rebase/amend/squash).
The marker no longer identifies an ancestor of HEAD. If the content already
matches, re-anchor the marker: make reanchor"
  commits="$(git log --oneline "$base..HEAD" -- thesis.typ)"
else
  note "No sync marker in the DOCX: converging from its current content."
fi

{
  echo "# Pending sync: thesis.typ -> DOCX"
  echo
  echo "Base:   ${base:-(none)}"
  echo "Head:   $head"
  echo
  echo "## Commits touching thesis.typ since the base"
  echo
  if [[ -n "$commits" ]]; then
    echo "$commits" | sed 's/^/    /'
  else
    echo "    (none)"
  fi
  echo
  echo "## Differences the DOCX is missing"
  echo
  python3 "$ROOT/scripts/compare.py" thesis.typ "$REVIEW/accepted.md" || true
} > "$REVIEW/pending.md"

if python3 "$ROOT/scripts/compare.py" thesis.typ "$REVIEW/accepted.md" >/dev/null; then
  note
  note "The DOCX already matches thesis.typ — no content changes to apply."
  if [[ -n "$base" && "$base" != "$head" ]] && [[ -n "$commits" ]]; then
    note "The marker is $base but HEAD is $head."
    note "Run 'make push-finish' to advance the marker and push git."
  elif [[ -n "$base" && "$base" != "$head" ]]; then
    note "The marker ($base) is behind HEAD ($head) only in commits that do"
    note "not touch thesis.typ; nothing to sync."
  fi
  exit 0
fi

note
cat "$REVIEW/pending.md"
note
note "Worklist written to review/pending.md"
note
note "Next (agent):"
note "  1. apply each difference to .sync/work.docx (tracked=False)"
note "  2. make push-finish"
