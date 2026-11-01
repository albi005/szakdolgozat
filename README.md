# Szakdolgozat

Typst source for the thesis. `thesis.typ` is the content source of truth.

The Word review copy is a persistent document in OneDrive:

```text
onedrive:/Szakdolgozat - Ragány-Németh Albert GL6IFB.docx
```

The supervisor reviews it with **Track Changes / Suggesting** and comments.
The DOCX is never regenerated from Typst. Comments stay in the document.

## Setup

```sh
nix develop
```

If OneDrive is not configured yet:

```sh
make rclone-config
```

Then check:

```sh
make status
```

## Review workflow

```sh
make pull
```

Extracts the DOCX and writes review material to `review/`:

- `comments.md` — comments and tracked changes
- `tracked.md` — tracked-change view
- `accepted.md` — accepted-text view

Then apply suggestions to `thesis.typ`, accept them in `.sync/review.docx`
with docx-mcp, and upload:

```sh
make upload
```

See `AGENTS.md` for the full agent procedure.

## Commands

```sh
make pull
make upload
make status
make pdf
make rclone-config
```

## Repo contents

- `thesis.typ` — thesis content
- `scripts/` — review sync helpers
- `AGENTS.md` — instructions for the syncing agent
- `opencode.json` — docx-mcp configuration
- `flake.nix` — pinned `nixpkgs-unstable` dev shell
- `.env` — OneDrive target (not sensitive)

The DOCX is deliberately not in git. Its history lives in OneDrive.
