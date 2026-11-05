# Agent notes

Practical findings from previous syncs. Read this before starting a sync and
append anything new you had to work out, so the next sync does not rediscover
it. Rules that are part of the workflow live in `AGENTS.md`; this file only
collects gotchas.

## docx-mcp

- **Edits are in memory until `save_document()`.** Reading `.sync/work.docx`
  from disk with python/zipfile shows the state before the current session's
  edits. Inspect through `get_paragraph()`/`search_text()`, or save to a
  temporary path (`.sync/work.tmp.docx`) and read that.
- **`replace_text()` is unreliable in the middle of a paragraph.** In this
  document a mid-paragraph replacement left the original run untouched and
  appended the new text at the end of the paragraph
  (`...commonly used pages.(JS) `). It behaved correctly only when the matched
  text was at the end of the paragraph. Use
  `delete_text(tracked=False)` + `insert_text(position=<text to insert after>,
  tracked=False)` instead, then verify the visible text with `get_paragraph()`.
- `insert_paragraph()` returns the new `paraId`; pass it as the next
  `after_para_id` to build a chain of paragraphs.
- XML escaping (`<TModule>`, `C#`) and `xml:space="preserve"` for leading
  spaces in `Kd` lines are handled by `insert_paragraph()`.
- `save_document()` keeps numbered backups (`.sync/work.docx.bakN`); `close_document()`
  is required before `scripts/diagram.py insert`.
- `audit_document()` reports the template's declaration table
  (`Table 2 has inconsistent column counts`). That is pre-existing; it is not
  caused by a push.

## Gate (`scripts/compare.py`)

- `normalize()` must remove markup without removing words. **Inline raw code
  with a language tag is valid Typst**: `` ```cs WebApplicationBuilder.AddModule<TModule>()``` ``.
  The old rule `re.sub(r"```[^\n]*", "")` deleted everything from the ticks to
  the end of the line, silently truncating the paragraph, so the DOCX could
  never match. Balanced triple-backtick spans are now consumed first; keep that
  order, before the single-backtick inline-code rule.
- When the gate reports a difference in text that looks identical, dump the
  parsed blocks (`parse_typst`/`parse_markdown` + `sectionize`) instead of
  guessing. A normalization bug is fixed in `compare.py`, never bypassed.

## Code listings

- One paragraph per source line, style `Kd`. Never `insert_code_block()`.
- `thesis.typ` may also contain **inline** raw code with a language tag
  (`` ```cs ...``` ``). That is inline, not a fence: it becomes plain text in
  the DOCX paragraph, exactly like single-backtick inline code.

## Diagrams

- Diagrams are numbered by their order of appearance (`#mermaid`/`#figure`) in
  `thesis.typ`: `render --index N`, then `insert ... --index N`.
- `scripts/diagram.py insert` places the picture paragraph **immediately after**
  the anchor paragraph. To put a picture between two paragraphs, insert the
  following paragraph first and anchor on the paragraph that precedes the
  picture.
- Alt text follows the language/style of the existing picture (Hungarian in
  this document), and the picture gets no caption that `thesis.typ` lacks.

## Flow

- To check before committing: regenerate the views
  (`source scripts/lib.sh; extract_review`) and run
  `python3 scripts/compare.py thesis.typ review/accepted.md`. `push-finish`
  also requires `review_state "$WORK"` to report `0 0 0`.
- `push.sh` exits 0 with "no content changes" when the body already matches but
  the marker is behind `HEAD`; run `make push-finish` anyway to advance the
  marker and upload.
- The marker (`docProps/custom.xml` → `ThesisSyncBase`) records `HEAD`, so
  `thesis.typ` must be committed before `push-finish`.
