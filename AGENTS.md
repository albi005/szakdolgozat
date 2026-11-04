# Agent instructions: DOCX sync

`thesis.typ` is the only content source of truth. The shared Word document in
OneDrive is a derived review surface:

```
DOCX body  ==  thesis.typ  +  boilerplate that lives only in the DOCX
                            +  pending supervisor suggestions
```

Nobody edits the DOCX by hand. The supervisor only adds Track Changes and
comments; the author only edits `thesis.typ`.

Run everything inside the Nix dev shell:

```sh
nix develop
```

## The three flows

| Flow | Command | What it does |
|---|---|---|
| init | `make init` | rclone/OneDrive login, verify the document is reachable |
| pull | `make pull` … `make pull-finish` | supervisor suggestions → `thesis.typ`, then accept them in the DOCX |
| push | `make push` … `make push-finish` | `thesis.typ` changes → DOCX, plus `git push` |

`pull` and `push` each have two phases because the agent does the content work
between them. Phase 1 writes the material into `review/`; phase 2 verifies and
publishes.

## State

- `thesis.typ` — the only thing worth keeping.
- `.sync/work.docx` — scratch copy; safe to delete at any time.
- `.sync/work.base` — remote hash the scratch copy was made from. A retry of
  phase 2 reuses the scratch copy instead of re-downloading.
- `review/` — generated views; safe to delete at any time.
- **The sync marker lives inside the DOCX**, in `docProps/custom.xml` as
  `ThesisSyncBase`. It names the commit whose `thesis.typ` content the DOCX
  body reflects. Markers are never stored on the side, so the claim and the
  document cannot disagree.

## The gate

Before anything is uploaded, both phases run:

```sh
python3 scripts/compare.py thesis.typ review/accepted.md
```

It compares the DOCX body with `thesis.typ` word by word, ignoring markup,
smart quotes, list numbering and the boilerplate sections listed in
`DEFAULT_ALLOWLIST`. Any difference means **do not upload**. If the gate is too
strict, fix the normalization rule or the allowlist in `scripts/compare.py` —
never bypass the gate.

## Flow: pull (supervisor → thesis.typ)

```sh
make pull
```

Downloads the DOCX and writes:

- `review/comments.md` — comments (empty section if none)
- `review/tracked.md` — tracked-change view
- `review/accepted.md` — accepted-text view

If there is nothing to review, `make pull` stops here and reports whether the
DOCX already matches `thesis.typ`. Then:

1. Read `review/comments.md` and `review/tracked.md`.
2. Apply every suggestion and comment to `thesis.typ`. Keep existing wording
   unless the suggestion explicitly changes it. Do not add boilerplate.
3. Accept the tracked changes in the DOCX:

   ```
   open_document({ path: ".sync/work.docx" })
   get_tracked_changes()
   get_comments()          # must still list the supervisor's comments
   accept_changes()
   audit_document()
   save_document({})       # writes back to .sync/work.docx
   close_document()
   ```

   Accepting must not remove comments. If a comment is anchored to a paragraph
   that is being deleted, re-anchor it to the nearest surviving paragraph and
   say so in the summary.

4. Publish:

   ```sh
   make pull-finish
   ```

   This gates, commits `thesis.typ`, stamps the marker, and uploads. It does
   **not** push to GitHub.

## Flow: push (thesis.typ → DOCX)

```sh
make push
```

Downloads the DOCX, reads its marker, and writes a worklist to
`review/pending.md`:

- the commits touching `thesis.typ` since the marker,
- the exact blocks the DOCX is missing.

`make push` refuses when the DOCX has unresolved tracked changes (run `pull`
first), or when the marker no longer names an ancestor of `HEAD` (history was
rewritten). In the second case the content is usually still in sync, and only
the marker is stale:

```sh
make reanchor
```

`make reanchor` uploads nothing unless the gate passes, so it can never claim a
match that does not exist. Never edit the marker by hand.

Then:

1. Read `review/pending.md`.
2. Apply each difference to `.sync/work.docx` with docx-mcp, `tracked=False`:

   ```
   open_document({ path: ".sync/work.docx" })
   search_text() / get_headings() / get_paragraph()
   replace_text(..., tracked=False)
   insert_paragraph() / delete_paragraph()
   insert_code_block()
   modify_cell() / add_table_row()
   insert_image()
   audit_document()
   save_document({})
   close_document()
   ```

   `audit_document()` reports a pre-existing inconsistent table in the
   template's declaration page; that is not caused by a push.

3. Publish:

   ```sh
   make push-finish
   ```

   Gates, then runs `git push`, then stamps the marker and uploads. Git goes
   first on purpose: if the upload fails, the repository is consistent and the
   next `push` recomputes the same worklist.

`thesis.typ` must be committed before `push-finish`; the marker records a
commit, not a working tree.

## Commit messages

Commits whose primary content the agent wrote — tooling, scripts, and docs
describing that infrastructure — carry a trailer naming the assistant:

```
Assisted-by: OpenCode:deepseek-flash
```

Use `git commit --trailer "Assisted-by: OpenCode:deepseek-flash"`.

## Rules

- Never regenerate the DOCX from Typst, and never replace it wholesale.
- Never delete or edit the supervisor's comments.
- Never upload when the gate fails.
- If `rclone` returns `423 Locked`, stop and ask the user to close the document
  in Word.
- Never edit the marker by hand. After a rebase, amend or squash, run
  `make reanchor`; it only proceeds when the DOCX already matches `thesis.typ`.
- Keep `thesis.typ` free of title page, declarations, ToC, bibliography and
  appendix boilerplate; those live only in the DOCX.
- Label a commit with `Assisted-by: OpenCode:deepseek-flash` only when the agent
  wrote its primary content — infrastructure, tooling, docs. Sync commits (the
  supervisor's suggestions applied to `thesis.typ`) are not labelled.
- `make pdf` builds `thesis.pdf`; it is unrelated to the DOCX.
