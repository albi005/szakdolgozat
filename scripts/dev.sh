#!/usr/bin/env bash
# Editing session: helix here, typst watch in its own terminal window, sioyek
# alongside. The watcher window can be moved to another Hyprland workspace.
#
#   make dev
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

for tool in typst hx sioyek; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Missing '$tool'. Run inside 'nix develop' (sioyek may need to be installed)." >&2
    exit 1
  fi
done

# The reader needs a PDF to open; build once on a fresh checkout before the
# watcher takes over. sioyek reloads the file on its own afterwards.
if [[ ! -f thesis.pdf ]]; then
  typst compile thesis.typ thesis.pdf
fi

READER_PID=""
WATCH_PID=""

cleanup() {
  trap - EXIT INT TERM
  # The watcher terminal owns the typst process; closing it stops the watch.
  [[ -n "$WATCH_PID" ]] && kill "$WATCH_PID" 2>/dev/null || true
  [[ -n "$READER_PID" ]] && kill "$READER_PID" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# typst watch in a terminal window of its own, titled so it is easy to spot in
# the Hyprland window list. Window class "typst-watch" is set for a window rule.
TERM_BIN="${TERMINAL:-alacritty}"
if command -v "$TERM_BIN" >/dev/null 2>&1; then
  case "$(basename "$TERM_BIN")" in
  kitty)
    "$TERM_BIN" --title "typst watch" --class typst-watch typst watch thesis.typ thesis.pdf &
    ;;
  foot)
    "$TERM_BIN" -T "typst watch" -a typst-watch -e typst watch thesis.typ thesis.pdf &
    ;;
  wezterm)
    "$TERM_BIN" start --class typst-watch -- typst watch thesis.typ thesis.pdf &
    ;;
  *)
    "$TERM_BIN" --title "typst watch" --class typst-watch -e typst watch thesis.typ thesis.pdf &
    ;;
  esac
  WATCH_PID=$!
else
  # No terminal emulator: keep the watcher out of the way in a log file.
  LOG="$ROOT/.sync/typst-watch.log"
  mkdir -p "$ROOT/.sync"
  echo "No terminal emulator (\$TERMINAL=$TERM_BIN); logging to $LOG" >&2
  typst watch thesis.typ thesis.pdf >"$LOG" 2>&1 &
  WATCH_PID=$!
fi

sioyek thesis.pdf >/dev/null 2>&1 &
READER_PID=$!

hx thesis.typ
