# Agent instructions: DOCX review sync

This repository contains the Typst source of the thesis. The shared Word
document is the persistent review surface and lives in OneDrive.

- `thesis.typ` is the only content source of truth.
- The shared DOCX must never be regenerated from Typst.
- The supervisor uses **Track Changes / Suggesting** and comments only.
- The supervisor’s comments must remain in the DOCX.
- Formatting/title-page boilerplate is intentionally not in this repo.

Run tools inside the Nix dev shell:

```sh
nix develop
```

## Environment

- OneDrive target: `.env` → `THESIS_REMOTE` + `THESIS_DOCX_NAME`
- rclone remote: `onedrive`
- Word editing: `docx-mcp` tools (configured in `opencode.json`)
- Download/extract: `make pull`
- Upload the edited review copy: `make upload`
- Check state: `make status`
- Build PDF: `make pdf`

Do not upload while the DOCX is open in Word/Word Online. OneDrive returns
`423 Locked`.

## A. Supervisor review → thesis.typ

1. Check state:

   ```sh
   make status
   ```

2. Download and extract:

   ```sh
   make pull
   ```

   This creates:

   - `.sync/review.docx` — the DOCX to edit and upload
   - `review/comments.md` — comments + tracked insertions/deletions
   - `review/tracked.md` — tracked-change view
   - `review/accepted.md` — accepted-text view

3. Read `review/comments.md` and `review/tracked.md`.

4. Apply the accepted suggestions to `thesis.typ`. Preserve the existing
   content and wording unless the suggestion explicitly changes it. Do not
   re-add boilerplate.

5. Accept the supervisor’s tracked changes in the DOCX with docx-mcp:

   - `open_document({ path: ".sync/review.docx" })`
   - `get_tracked_changes()`
   - `get_comments()` — verify comments are present
   - `accept_changes()` or `accept_change({ change_id })` for each suggestion
   - `audit_document()`
   - `save_document({ path: ".sync/review.docx" })`
   - `close_document()`

   Accepting changes must not remove comments. If a comment is anchored to a
   paragraph that would be deleted, do not delete the paragraph blindly:
   re-anchor the comment to the nearest surviving paragraph first.

6. Upload the same DOCX:

   ```sh
   make upload
   ```

7. Commit the Typst changes:

   ```sh
   git add thesis.typ
   git commit -m "Apply supervisor review"
   ```

Do not push unless explicitly asked.

## B. Local thesis.typ edits → DOCX

1. Check whether local Typst changes are already in the DOCX:

   ```sh
   make status
   ```

   `Typst state: local changes not yet applied to the DOCX` means a sync is
   needed.

2. Download the current DOCX:

   ```sh
   make pull
   ```

3. Compare the current `thesis.typ` with the downloaded DOCX. Use
   `review/accepted.md` and `git diff`.

4. Apply only the changed blocks to `.sync/review.docx` with docx-mcp:

   - `open_document({ path: ".sync/review.docx" })`
   - `search_text()` / `get_headings()` / `get_paragraph()` to locate content
   - `update_paragraph()` for replacements
   - `insert_paragraph()` / `delete_paragraph()` for structural changes
   - `modify_cell()` / `add_table_row()` for tables
   - `insert_image()` for images
   - use `tracked=False` for the author’s own edits so the document looks
     directly edited
   - `audit_document()`
   - `save_document({ path: ".sync/review.docx" })`
   - `close_document()`

5. Upload:

   ```sh
   make upload
   ```

6. Commit `thesis.typ` if it is not already committed.

## Rules

- Never rebuild the DOCX from Typst.
- Never regenerate the DOCX and replace the OneDrive file.
- Never delete `review/comments.md` before the comments have been addressed.
- Keep comments in the DOCX; they are the supervisor’s review history.
- If a comment’s anchored text is gone, attach the comment to the nearest
  surviving paragraph and mention this in the final summary.
- If `make upload` fails with `423 Locked`, stop and ask the user to close the
  document in Word.
- Keep `thesis.typ` free of title-page, declaration, and other boilerplate.
- Commit locally; do not push to GitHub unless asked.
