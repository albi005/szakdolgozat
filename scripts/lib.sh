#!/usr/bin/env bash
# Shared helpers for the thesis DOCX sync.
#
# Three flows: init (log in), pull (supervisor -> typst), push (typst -> DOCX).
# The sync marker lives inside the DOCX itself, so "the DOCX contains commit X"
# and "the DOCX says it contains commit X" are one write.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

for tool in git pandoc python3 rclone typst; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Missing '$tool'. Run the commands inside 'nix develop'." >&2
    exit 1
  fi
done

if [[ -f "$ROOT/.env" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.env"
fi

THESIS_DOCX_NAME="${THESIS_DOCX_NAME:-Szakdolgozat - Ragány-Németh Albert GL6IFB.docx}"
THESIS_REMOTE="${THESIS_REMOTE:-onedrive:}"

if [[ "$THESIS_REMOTE" == *: ]]; then
  REMOTE_DOCX="${THESIS_REMOTE}${THESIS_DOCX_NAME}"
else
  REMOTE_DOCX="${THESIS_REMOTE%/}/$THESIS_DOCX_NAME"
fi

WORK="$ROOT/.sync/work.docx"
REVIEW="$ROOT/review"
mkdir -p "$ROOT/.sync" "$REVIEW"

die() {
  printf '\n\033[1;31merror:\033[0m %s\n' "$*" >&2
  exit 1
}

note() {
  printf '%s\n' "$*"
}

require_target() {
  local remote_name="${THESIS_REMOTE%%:*}"
  if ! rclone listremotes 2>/dev/null | grep -qx "$remote_name:"; then
    die "rclone remote '$remote_name' is not configured. Run: make init"
  fi
}

shared_exists() {
  rclone lsf "$REMOTE_DOCX" >/dev/null 2>&1
}

download_shared() {
  rclone copyto "$REMOTE_DOCX" "$1" >/dev/null
}

upload_shared() {
  rclone copyto "$1" "$REMOTE_DOCX" >/dev/null
}

sha() {
  sha256sum "$1" | cut -d' ' -f1
}

# Sync marker: the commit whose thesis.typ content the DOCX body reflects.
tag_get() {
  python3 "$ROOT/scripts/docx_tag.py" get "$1"
}

tag_set() {
  python3 "$ROOT/scripts/docx_tag.py" set "$1" "$2"
}

# "insertions deletions comments" for a DOCX.
review_state() {
  python3 "$ROOT/scripts/docx_state.py" "$1"
}

# Regenerate the pandoc views of .sync/work.docx.
extract_review() {
  pandoc "$WORK" --track-changes=accept -t markdown --wrap=none \
    -o "$REVIEW/accepted.md"
  pandoc "$WORK" --track-changes=all -t markdown --wrap=none \
    -o "$REVIEW/tracked.md"
  pandoc "$WORK" --track-changes=all -t json -o "$ROOT/.sync/review.json"
  python3 "$ROOT/scripts/extract_review.py" \
    "$ROOT/.sync/review.json" "$REVIEW/comments.md"
}

# The name of the remote file, for messages.
remote_label() {
  printf '%s' "$REMOTE_DOCX"
}
