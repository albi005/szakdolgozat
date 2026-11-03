#!/usr/bin/env python3
"""Report the review state of a .docx: tracked insertions, deletions, comments.

    docx_state.py FILE          -> "INS DEL COMMENTS"
    docx_state.py --json FILE   -> {"insertions": n, "deletions": n, "comments": n}
"""

from __future__ import annotations

import json
import sys
import zipfile


def count(zf: zipfile.ZipFile, part: str, needle: str) -> int:
    try:
        raw = zf.read(part)
    except KeyError:
        return 0
    return raw.count(needle)


def main(argv: list[str]) -> int:
    as_json = False
    args = argv[1:]
    if args and args[0] == "--json":
        as_json = True
        args = args[1:]
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2

    with zipfile.ZipFile(args[0]) as zf:
        state = {
            "insertions": count(zf, "word/document.xml", b"<w:ins "),
            "deletions": count(zf, "word/document.xml", b"<w:del "),
            "comments": count(zf, "word/comments.xml", b"<w:comment "),
        }

    if as_json:
        print(json.dumps(state))
    else:
        print(f"{state['insertions']} {state['deletions']} {state['comments']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
