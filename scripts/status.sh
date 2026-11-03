#!/usr/bin/env bash
# Show whether the shared DOCX has changed since the last pull.
source "$(dirname "$0")/lib.sh"

require_configured_target

echo "Target:      $REMOTE_DOCX"

if shared_exists; then
  echo "Shared file: present"
  download_shared "$ROOT/.sync/status.docx"
  current="$(sha "$ROOT/.sync/status.docx")"
  if [[ -f "$ROOT/.sync/last-pulled.sha256" ]]; then
    if [[ "$current" == "$(cat "$ROOT/.sync/last-pulled.sha256")" ]]; then
      echo "Review state: no new changes since last pull"
    else
      echo "Review state: new suggestions/comments available (run make pull)"
    fi
  else
    echo "Review state: not pulled yet (run make pull)"
  fi
  rm -f "$ROOT/.sync/status.docx"
else
  echo "Shared file: MISSING"
fi

if [[ -f "$ROOT/.sync/last-pull.txt" ]]; then
  echo "Last pull:   $(cat "$ROOT/.sync/last-pull.txt")"
fi
if [[ -f "$ROOT/.sync/last-upload.txt" ]]; then
  echo "Last upload: $(cat "$ROOT/.sync/last-upload.txt")"
fi

if [[ -f "$ROOT/.sync/last-synced-thesis.typ" ]]; then
  if cmp -s "$ROOT/.sync/last-synced-thesis.typ" "$ROOT/thesis.typ"; then
    echo "Typst state: in sync with the last upload"
  else
    echo "Typst state: local changes not yet applied to the DOCX (run make diff)"
  fi
else
  echo "Typst state: no sync snapshot yet"
fi

echo
echo "Git status:"
git status --short
