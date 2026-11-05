#!/usr/bin/env python3
"""Compare `thesis.typ` with the accepted text of the review DOCX.

This is the sync gate. The DOCX is never edited by hand, so its body must equal
`thesis.typ` apart from the boilerplate that intentionally lives only in the
DOCX (title page, declarations, ToC, bibliography, appendix).

    compare.py thesis.typ accepted.md           # report, exit 1 on difference
    compare.py --allow-missing introduction ... # extra allowlisted headings

Output is a worklist: every difference is a block the agent must apply to the
DOCX (or to thesis.typ, during a pull).
"""

from __future__ import annotations

import difflib
import re
import sys
import unicodedata

# Sections that exist only in the DOCX by design. Matched against the heading
# text, case-insensitively, as a prefix-anchored regex.
DEFAULT_ALLOWLIST = [
    r"tartalomjegyz[ée]k",
    r"[öo]sszefoglal[óo]",
    r"abstract",
    r"irodalomjegyz[ée]k",
    r"f[üu]ggel[ée]k",
    r"nyilatkozat .*",
    r"hallgat[óo]i nyilatkozat",
    r"feladatki[íi]r[áa]s",
]


class Block:
    __slots__ = ("kind", "level", "text")

    def __init__(self, kind: str, text: str, level: int = 0) -> None:
        self.kind = kind
        self.level = level
        self.text = text

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Block({self.kind!r}, {self.level}, {self.text[:40]!r})"


class Section:
    __slots__ = ("level", "title", "blocks")

    def __init__(self, level: int, title: str) -> None:
        self.level = level
        self.title = title
        self.blocks: list[Block] = []


# --------------------------------------------------------------------------
# normalization
# --------------------------------------------------------------------------

_TRANSLATE = str.maketrans(
    {
        "\u00a0": " ",
        "\u2018": "'",
        "\u2019": "'",
        "\u201a": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u201e": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u2026": "...",
    }
)


def normalize(text: str) -> str:
    """Reduce typst/markdown markup and typography to comparable plain words.

    Deliberately only touches *markup*, never words: if this is too strict the
    gate blocks an upload and a human looks at it. Too lenient would let a real
    difference through, so every rule here must be lossless for word content.
    """
    text = unicodedata.normalize("NFC", text).translate(_TRANSLATE)
    text = re.sub(r"\\([^\w\s])", r"\1", text)
    # Inline raw code with a language tag: ```cs foo()``` -> foo(). Typst keeps
    # the backticks in the source but renders only the code, so the delimiters
    # and the language are markup, not words. Must run before the single-tick
    # rule below, which would otherwise strip the ticks one pair at a time.
    text = re.sub(r"```[A-Za-z0-9_+.-]*[ \t]+([^`\n]*?)```", r"\1", text)
    text = re.sub(r"```([^`\n]*?)```", r"\1", text)  # inline raw, no language
    text = re.sub(r"```[^\n]*", "", text)  # stray fence info strings
    text = re.sub(r"`([^`]*)`", r"\1", text)  # inline code
    text = re.sub(r"\*\*|__", "", text)  # strong
    text = re.sub(r"(?<![\w*])\*(?!\s)(.*?)(?<!\s)\*(?![\w*])", r"\1", text)
    text = re.sub(r"(?<![\w_])_(?!\s)(.*?)(?<!\s)_(?![\w_])", r"\1", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)(\{[^}]*\})?", r"\1", text)  # images
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # links
    text = re.sub(r"\[\^[^\]]*\]", "", text)  # footnote refs
    text = re.sub(r"\{[#.][^}]*\}", "", text)  # pandoc attributes
    text = re.sub(r"^\s*[:]{3,}.*$", "", text, flags=re.M)  # fenced divs
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def heading_title(raw: str) -> str:
    raw = re.sub(r"\{[^}]*\}\s*$", "", raw)
    return normalize(raw)


# --------------------------------------------------------------------------
# parsers
# --------------------------------------------------------------------------

TYPST_HEADING = re.compile(r"^(=+)\s+(.*\S)\s*$")
MD_HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")

# Typst calls that draw something. Word stores a drawing as an image, so both
# surfaces contribute one `image` block; the picture itself is not compared.
TYPST_FIGURE = re.compile(r"^#(mermaid|figure|image)\s*\(")
# Top-level directives that configure the document instead of contributing text.
TYPST_DIRECTIVE = re.compile(r"^#(import|include|set|show|let|bibliography)\b")
MD_IMAGE = re.compile(r"^!\[[^\]]*\]\([^)]*\)(\{[^}]*\})?$")


def typst_call_end(text: str, start: int) -> int:
    """Return the index just past the balanced `(...)` of a call at `start`."""
    i = text.index("(", start)
    depth = 0
    quote: str | None = None
    while i < len(text):
        ch = text[i]
        if quote is not None:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return len(text)


def parse_typst(text: str) -> list[Block]:
    blocks: list[Block] = []
    para: list[str] = []
    code: list[str] | None = None
    in_block_comment = False

    def flush() -> None:
        nonlocal para
        joined = normalize(" ".join(para))
        if joined:
            blocks.append(Block("para", joined))
        para = []

    offset = 0
    length = len(text)
    while offset < length:
        newline = text.find("\n", offset)
        next_offset = length if newline == -1 else newline + 1
        line = text[offset:newline if newline != -1 else length]
        stripped = line.strip()

        if code is not None:
            if stripped.startswith("```"):
                blocks.append(Block("code", normalize("\n".join(code))))
                code = None
            else:
                code.append(line)
            offset = next_offset
            continue

        if in_block_comment:
            if "*/" in line:
                in_block_comment = False
            offset = next_offset
            continue

        if stripped.startswith("```"):
            flush()
            code = []
            offset = next_offset
            continue
        if stripped.startswith("//"):
            offset = next_offset
            continue
        if stripped.startswith("/*"):
            flush()
            in_block_comment = "*/" not in stripped
            offset = next_offset
            continue
        if not stripped:
            flush()
            offset = next_offset
            continue

        m = TYPST_HEADING.match(line)
        if m:
            flush()
            blocks.append(Block("heading", heading_title(m.group(2)), len(m.group(1))))
            offset = next_offset
            continue

        if TYPST_DIRECTIVE.match(stripped):
            flush()
            offset = next_offset
            continue

        if TYPST_FIGURE.match(stripped):
            # A diagram spans several lines (mermaid source included); consume
            # the whole call so its body is not read as prose.
            flush()
            start = offset + len(line) - len(line.lstrip())
            end = typst_call_end(text, start)
            blocks.append(Block("image", ""))
            offset = end
            continue

        para.append(stripped)
        offset = next_offset

    if code is not None:
        blocks.append(Block("code", normalize("\n".join(code))))
    flush()
    return blocks


def parse_markdown(text: str) -> list[Block]:
    blocks: list[Block] = []
    para: list[str] = []
    code: list[str] | None = None
    table: list[str] | None = None

    def flush() -> None:
        nonlocal para
        raw = " ".join(para).strip()
        if raw:
            if MD_IMAGE.match(raw):
                # A figure in the DOCX. Its content is a picture: compare its
                # presence and position, not its pixels.
                blocks.append(Block("image", ""))
            else:
                joined = normalize(raw)
                if joined:
                    blocks.append(Block("para", joined))
        para = []

    def flush_table() -> None:
        nonlocal table
        if table:
            cells = [re.sub(r"^[+|=\-\s]+|[+|=\-\s]+$", "", row) for row in table]
            joined = normalize(" ".join(cells))
            if joined:
                blocks.append(Block("table", joined))
        table = None

    for line in text.splitlines():
        if code is not None:
            if line.strip().startswith("```") or line.strip().startswith("~~~"):
                blocks.append(Block("code", normalize("\n".join(code))))
                code = None
            else:
                code.append(line)
            continue

        stripped = line.strip()

        if stripped.startswith("```") or stripped.startswith("~~~"):
            flush()
            flush_table()
            code = []
            continue

        if stripped and set(stripped) <= set("+-=| ") and ("|" in stripped or "+" in stripped):
            flush()
            table = (table or []) + [stripped]
            continue
        if stripped.startswith("|"):
            flush()
            table = (table or []) + [stripped]
            continue
        flush_table()

        if not stripped:
            flush()
            continue

        m = MD_HEADING.match(line)
        if m:
            flush()
            blocks.append(Block("heading", heading_title(m.group(2)), len(m.group(1))))
            continue

        para.append(stripped)

    flush_table()
    if code is not None:
        blocks.append(Block("code", normalize("\n".join(code))))
    flush()
    return blocks


# --------------------------------------------------------------------------
# sections
# --------------------------------------------------------------------------

def is_allowlisted(title: str, patterns: list[str]) -> bool:
    return any(re.match(p, title, re.IGNORECASE) for p in patterns)


def drop_allowlisted(blocks: list[Block], patterns: list[str]) -> list[Block]:
    kept: list[Block] = []
    ignored_level: int | None = None
    for block in blocks:
        if block.kind == "heading":
            if ignored_level is not None and block.level <= ignored_level:
                ignored_level = None
            if is_allowlisted(block.text, patterns):
                ignored_level = block.level
                continue
        if ignored_level is None:
            kept.append(block)
    return kept


def sectionize(blocks: list[Block], keep_preamble: bool) -> list[Section]:
    sections = [Section(0, "")]
    for block in blocks:
        if block.kind == "heading":
            sections.append(Section(block.level, block.text))
        else:
            sections[-1].blocks.append(block)
    return [s for s in sections if s.title or (keep_preamble and s.blocks)]


def label(section: Section) -> str:
    return section.title or "(document start)"


# --------------------------------------------------------------------------
# comparison
# --------------------------------------------------------------------------

def block_key(block: Block) -> str:
    # Compare words, not Word styles: a code block and a shaded paragraph with
    # the same text are the same content.
    return block.text


def compare(
    thesis: list[Block], docx: list[Block], patterns: list[str]
) -> list[str]:
    """Return a markdown worklist; an empty list means the surfaces agree."""
    thesis_sections = sectionize(thesis, keep_preamble=True)
    docx_sections = sectionize(drop_allowlisted(docx, patterns), keep_preamble=False)

    out: list[str] = []

    t_titles = [label(s) for s in thesis_sections]
    d_titles = [label(s) for s in docx_sections]
    matcher = difflib.SequenceMatcher(a=t_titles, b=d_titles, autojunk=False)

    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            for t_sec, d_sec in zip(thesis_sections[i1:i2], docx_sections[j1:j2]):
                out += compare_blocks(t_sec, d_sec)
        elif op == "delete":
            for t_sec in thesis_sections[i1:i2]:
                out.append(
                    f"- **missing in DOCX**: section `{label(t_sec)}` "
                    f"(level {t_sec.level}) — insert heading and {len(t_sec.blocks)} block(s)"
                )
        elif op == "insert":
            for d_sec in docx_sections[j1:j2]:
                out.append(
                    f"- **extra in DOCX**: section `{label(d_sec)}` "
                    f"(level {d_sec.level}) — remove, or add it to thesis.typ"
                )
        else:
            for t_sec in thesis_sections[i1:i2]:
                out.append(
                    f"- **missing in DOCX**: section `{label(t_sec)}` "
                    f"(level {t_sec.level}) — insert heading and {len(t_sec.blocks)} block(s)"
                )
            for d_sec in docx_sections[j1:j2]:
                out.append(
                    f"- **extra in DOCX**: section `{label(d_sec)}` "
                    f"(level {d_sec.level}) — remove, or add it to thesis.typ"
                )
    return out


def compare_blocks(t_sec: Section, d_sec: Section) -> list[str]:
    if t_sec.level != d_sec.level:
        return [
            f"- **heading level differs** in `{label(t_sec)}`: "
            f"thesis {t_sec.level}, DOCX {d_sec.level}"
        ]

    t_keys = [block_key(b) for b in t_sec.blocks]
    d_keys = [block_key(b) for b in d_sec.blocks]
    if t_keys == d_keys:
        return []

    out: list[str] = []
    matcher = difflib.SequenceMatcher(a=t_keys, b=d_keys, autojunk=False)
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            continue
        where = f"`{label(t_sec)}`"
        if op == "replace":
            for t_b, d_b in zip(t_sec.blocks[i1:i2], d_sec.blocks[j1:j2]):
                out.append(f"- **change** in {where}")
                out.append(f"  - DOCX: {quote(d_b.text)}")
                out.append(f"  - thesis: {quote(t_b.text)}")
            for t_b in t_sec.blocks[i1 + (j2 - j1) : i2]:
                out.append(f"- **insert into DOCX** in {where}: {quote(t_b.text)}")
            for d_b in d_sec.blocks[j1 + (i2 - i1) : j2]:
                out.append(f"- **delete from DOCX** in {where}: {quote(d_b.text)}")
        elif op == "delete":
            for t_b in t_sec.blocks[i1:i2]:
                out.append(f"- **insert into DOCX** in {where}: {quote(t_b.text)}")
        elif op == "insert":
            for d_b in d_sec.blocks[j1:j2]:
                out.append(f"- **delete from DOCX** in {where}: {quote(d_b.text)}")
    return out


def quote(text: str) -> str:
    if len(text) > 240:
        text = text[:237] + "..."
    return "«" + text + "»"


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    args = argv[1:]
    patterns = list(DEFAULT_ALLOWLIST)
    extra: list[str] = []
    while args and args[0].startswith("--"):
        flag = args.pop(0)
        if flag == "--allow":
            extra.append(args.pop(0))
        elif flag in ("-h", "--help"):
            print(__doc__)
            return 0
        else:
            print(f"unknown option: {flag}", file=sys.stderr)
            return 2

    if len(args) != 2:
        print(__doc__, file=sys.stderr)
        return 2

    thesis_path, docx_md_path = args
    patterns += extra

    with open(thesis_path, encoding="utf8") as fh:
        thesis = parse_typst(fh.read())
    with open(docx_md_path, encoding="utf8") as fh:
        docx = parse_markdown(fh.read())

    problems = compare(thesis, docx, patterns)

    if not problems:
        print("gate: OK — the DOCX body matches thesis.typ")
        return 0

    count = sum(1 for line in problems if line.startswith("- "))
    print(f"gate: FAIL — {count} difference(s)")
    for line in problems:
        print(line)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
