#!/usr/bin/env bash
# status: read-only report of where the DOCX and thesis.typ stand.
source "$(dirname "$0")/lib.sh"

require_target
shared_exists || die "no shared document at $(remote_label). Run: make init"

tmp="$ROOT/.sync/status.docx"
download_shared "$tmp"
read -r ins dels comments <<<"$(review_state "$tmp")"
base="$(tag_get "$tmp")"
head="$(git rev-parse --short HEAD)"

note "Target:      $(remote_label)"
note "Marker:      ${base:-(none)}"
note "HEAD:        $head"

if [[ -f "$ROOT/.sync/last-seen.sha256" ]]; then
  if [[ "$(sha "$tmp")" == "$(cat "$ROOT/.sync/last-seen.sha256")" ]]; then
    note "Remote:      unchanged since the last download"
  else
    note "Remote:      CHANGED since the last download (run make pull)"
  fi
else
  note "Remote:      not seen on this machine yet"
fi

note "Review:      $ins insertion(s), $dels deletion(s), $comments comment(s)"

if [[ "$ins" -ne 0 || "$dels" -ne 0 || "$comments" -ne 0 ]]; then
  note "Next:        make pull  (supervisor suggestions are pending)"
else
  pandoc "$tmp" --track-changes=accept -t markdown --wrap=none \
    -o "$ROOT/.sync/status-accepted.md"
  if python3 "$ROOT/scripts/compare.py" thesis.typ \
    "$ROOT/.sync/status-accepted.md" >"$ROOT/.sync/status-gate.txt"; then
    note "Gate:        OK — the DOCX body matches thesis.typ"
  else
    note "Gate:        DIFFERS — $(head -1 "$ROOT/.sync/status-gate.txt")"
    note "Next:        make push"
  fi

  if [[ -n "$base" ]]; then
    count="$(git log --oneline "$base..$head" -- thesis.typ 2>/dev/null | wc -l)"
    note "Commits:     $count touching thesis.typ since the marker"
    if [[ "$count" -eq 0 && "$base" != "$head" ]]; then
      note "             (HEAD is ahead only in commits that do not touch thesis.typ)"
    fi
  else
    note "Commits:     no marker, so 'make push' converges from the DOCX content"
  fi
fi

rm -f "$tmp"
note
note "Git status:"
git status --short
