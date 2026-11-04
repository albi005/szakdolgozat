# Szakdolgozat

Typst source of the thesis. `thesis.typ` is the content source of truth.

The Word review copy is a persistent document in OneDrive:

```text
onedrive:/Szakdolgozat - Ragány-Németh Albert GL6IFB.docx
```

The supervisor reviews it with **Track Changes / Suggesting** and comments.
The DOCX is never generated from Typst and never edited by hand: its body is
`thesis.typ` plus the boilerplate that only exists in Word plus whatever
suggestions are still pending.

## Setup

```sh
nix develop
make init        # OneDrive login (browser) + reachability check
```

## The three flows

| Flow | Command | Direction |
|---|---|---|
| init | `make init` | OneDrive login |
| pull | `make pull` → agent → `make pull-finish` | supervisor suggestions → `thesis.typ` |
| push | `make push` → agent → `make push-finish` | `thesis.typ` → DOCX + `git push` |
| reanchor | `make reanchor` | repoint the marker after history was rewritten |
| status | `make status` | read-only, downloads the DOCX |
| pdf | `make pdf` | `typst compile` to `thesis.pdf` |

`pull` and `push` are split in two because an agent (this one) does the content
work in between. `make pull` prepares `review/`; `make pull-finish` verifies
and publishes. Same for push, with `review/pending.md` as the worklist.

```sh
make pull          # download + extract comments/tracked changes
                   # ... apply to thesis.typ, accept changes in the DOCX ...
make pull-finish   # gate, commit, stamp, upload

make push          # download + worklist of missing blocks
                   # ... apply them to the DOCX ...
make push-finish   # gate, git push, stamp, upload
```

## How sync state is tracked

The DOCX carries its own marker: a custom document property `ThesisSyncBase`
in `docProps/custom.xml`, holding the commit whose `thesis.typ` content the
document body reflects. Because it is inside the file, "the DOCX was updated"
and "the DOCX says it was updated" are a single write — OneDrive cannot split
them, and there is no sidecar state to fall out of date.

`make status` therefore reduces to arithmetic:

```
Marker:   80459d0
HEAD:     80459d0
Commits:  0 touching thesis.typ since the marker
```

There is no local sync baseline. `.sync/` and `review/` are caches; deleting
them loses nothing.

## The gate

Nothing is uploaded unless the DOCX body and `thesis.typ` agree:

```sh
python3 scripts/compare.py thesis.typ review/accepted.md
```

The comparison is word-level and exact. It ignores markup, typography (smart
quotes, dashes, `\~`), list numbering and the boilerplate sections it is told
to ignore (title page, `Összefoglaló`, `Abstract`, `Irodalomjegyzék`,
`Függelék`, declarations, ToC). A section present on only one side is a
difference unless it matches the allowlist. A Word code listing — one `Kód`
paragraph per line — is merged back into a fenced block by
`scripts/docx_md.lua` before comparing.

This is what replaces the old "mark as synced and hope" step: a forgotten
paragraph blocks the upload instead of silently disappearing.

A diagram is compared as one `image` block: it must be present on both sides in
the same position, but the picture itself is not compared. `scripts/diagram.py`
renders the `#mermaid`/`#figure` call to a PNG with Typst and embeds it in the
DOCX. (Not SVG: Word drops the SVG Typst emits, which nests the mermaid render
as a base64 data URI — typst/typst#7040.)

## Failure modes

| Symptom | Meaning |
|---|---|
| `423 Locked` | the DOCX is open in Word; close it and retry |
| `marker is not a commit in this repository` | the DOCX was synced elsewhere |
| `history was rewritten since <sha>` | run `make reanchor`; it gates before touching the marker |
| `pending insertion(s)` on `make push` | supervisor edits are unresolved; `make pull` first |
| `thesis.typ has uncommitted changes` | commit before `push-finish` |
| gate FAIL | the DOCX is missing or has extra blocks; see `review/pending.md` |

`make push` and `make pull` reuse an already prepared `.sync/work.docx` when the
remote has not changed, so a retry after a failed finish step keeps the agent's
edits.

## Repo contents

- `thesis.typ` — thesis content
- `scripts/` — sync tooling (`compare.py` gate, `docx_tag.py` marker,
  `docx_md.lua` pandoc filter for Word code listings, `diagram.py` renders
  figures to SVG and embeds them in the DOCX)
- `AGENTS.md` — the agent procedure for the three flows
- `opencode.json` — `docx-mcp` configuration
- `flake.nix` — pinned `nixpkgs-unstable` dev shell
- `.env` — OneDrive target (not sensitive)

The DOCX is deliberately not in git. Its history lives in OneDrive, and its
sync marker lives inside it.
