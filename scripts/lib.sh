#!/usr/bin/env bash
# Shared helpers for the suggestions-only DOCX review loop.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

for tool in pandoc typst python3 rclone; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Missing '$tool'. Run the commands inside 'nix develop'."
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

mkdir -p "$ROOT/.sync"

require_configured_target() {
  local remote_name="${THESIS_REMOTE%%:*}"
  if ! rclone listremotes 2>/dev/null | grep -qx "$remote_name:"; then
    echo "rclone remote '$remote_name' is not configured."
    echo
    echo "Set it up with:"
    echo "  make rclone-config"
    echo
    echo "Then check it with:"
    echo "  rclone lsd $remote_name:"
    exit 1
  fi
}

shared_exists() {
  rclone lsf "$REMOTE_DOCX" >/dev/null 2>&1
}

download_shared() {
  local dest="$1"
  rclone copyto "$REMOTE_DOCX" "$dest" >/dev/null
}

upload_shared() {
  local src="$1"
  rclone copyto "$src" "$REMOTE_DOCX" >/dev/null
}

sha() {
  sha256sum "$1" | cut -d' ' -f1
}
