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

`make upload` copies `.sync/review.docx` to OneDrive. It also stores the
current `thesis.typ` as `.sync/last-synced-thesis.typ`, so future syncs know
exactly what changed.

See `AGENTS.md` for the full agent procedure.

## Push

There are two separate “push” operations:

```sh
make upload     # upload the edited DOCX to OneDrive
git push        # push the Typst/scripts to GitHub
```

`make upload` does not push to GitHub. `git push` does not touch OneDrive.

## How the local diff is found

Git commits are irrelevant for DOCX sync. The comparison uses a text snapshot
of `thesis.typ` from the last successful `make upload`:

```text
.sync/last-synced-thesis.typ
```

Show the local changes since that upload:

```sh
make diff
```

This works even if you have already committed your Typst changes.

## Commands

```sh
make pull
make upload
make status
make diff
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
