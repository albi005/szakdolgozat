#!/usr/bin/env bash
# Single-terminal editing session: typst watch + sioyek + helix.
#
#   make dev
#
# Starts the watcher and the reader in the background, then runs helix in the
# foreground. Quitting helix stops both.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

for tool in typst hx sioyek; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Missing '$tool'. Run inside 'nix develop' (sioyek may need to be installed)." >&2
    exit 1
  fi
done

LOG="$ROOT/.sync/typst-watch.log"
mkdir -p "$ROOT/.sync"

watch_pid=""
reader_pid=""

cleanup() {
  trap - EXIT INT TERM
  [[ -n "$watch_pid" ]] && kill "$watch_pid" 2>/dev/null || true
  [[ -n "$reader_pid" ]] && kill "$reader_pid" 2>/dev/null || true
  wait 2>/dev/null || true
  echo "Stopped typst watch and sioyek."
}
trap cleanup EXIT INT TERM

# Compiler output goes to a file: a background writer on the tty would fight
# helix for the alternate screen. Tail it with: tail -f .sync/typst-watch.log
typst watch thesis.typ thesis.pdf >"$LOG" 2>&1 &
watch_pid=$!

# Open the reader only once a PDF exists (fresh checkout, first compile).
for _ in $(seq 1 200); do
  if [[ -f thesis.pdf ]]; then break; fi
  sleep 0.1
done

sioyek thesis.pdf >/dev/null 2>&1 &
reader_pid=$!

hx thesis.typ
