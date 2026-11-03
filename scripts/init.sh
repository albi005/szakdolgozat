#!/usr/bin/env bash
# init: authenticate with OneDrive and verify the review document is reachable.
source "$(dirname "$0")/lib.sh"

remote_name="${THESIS_REMOTE%%:*}"
configured=no
if rclone listremotes 2>/dev/null | grep -qx "$remote_name:"; then
  configured=yes
fi

if [[ "$configured" == no ]]; then
  note "rclone remote '$remote_name' is not configured."
  note
  note "Create it now: name '$remote_name', storage 'onedrive',"
  note "then authenticate in the browser."
  note
  rclone config
else
  note "Re-authenticating '$remote_name' (a browser window will be needed)."
  rclone config reconnect "$remote_name:" || die "reconnect failed"
fi

if ! rclone listremotes 2>/dev/null | grep -qx "$remote_name:"; then
  die "rclone remote '$remote_name' still missing after init."
fi

if ! rclone lsf "$REMOTE_DOCX" >/dev/null 2>&1; then
  die "the review document is not reachable:
  $(remote_label)
Check THESIS_REMOTE / THESIS_DOCX_NAME in .env."
fi

note
note "OK — $(remote_label) is reachable."
note "Next: make pull  (supervisor suggestions -> thesis.typ)"
note "      make push  (thesis.typ -> DOCX)"
