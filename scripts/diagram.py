#!/usr/bin/env python3
"""Render the diagrams of `thesis.typ` and embed them in the review DOCX.

Word cannot draw Typst figures or mermaid diagrams, so a diagram crosses the
sync boundary as a picture. Typst renders it to SVG; the DOCX gets that SVG
plus a PNG fallback in the same drawing (Word renders `asvg:svgBlip`, older
readers fall back to the PNG).

    diagram.py render --index 0
        .sync/fig/diagram-0.svg, .sync/fig/diagram-0.png

    diagram.py insert .sync/work.docx --after 0DE69351 --index 0
        Inserts the picture after that paragraph with the SVG + PNG pair.

`insert` edits the package directly: docx-mcp's `insert_image` writes a minimal
`w:drawing` without the parts Word requires (`wp:docPr`, `pic:spPr`), so the
SVG has to be added here anyway. Run it after docx-mcp has saved and closed
the document.

Diagrams are numbered by their order of appearance in `thesis.typ`, so
`--index` is stable as long as diagrams are not reordered.
"""

from __future__ import annotations

import argparse
import re
import secrets
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THESIS = ROOT / "thesis.typ"
CACHE = ROOT / ".sync" / "fig"
DEFAULT_IMPORT = '#import "@preview/merman:0.5.0": mermaid'

EMU_PER_PT = 12700
EMU_PER_CM = 360000

SVG_EXT_URI = "{96DAC541-7B7A-43D3-8B79-37D633B846F1}"
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_PIC = "http://schemas.openxmlformats.org/drawingml/2006/picture"
NS_ASVG = "http://schemas.microsoft.com/office/drawing/2016/SVG/main"

# Top-level Typst calls that draw something. They may span several lines and
# contain blank lines (mermaid source), so they are scanned as one block.
FIGURE_CALLS = ("mermaid", "figure", "image")


class DiagramError(RuntimeError):
    pass


# --------------------------------------------------------------------------
# Typst source
# --------------------------------------------------------------------------

def _scan_call(text: str, start: int) -> int:
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
    raise DiagramError("unbalanced parentheses in a figure call")


def figure_calls(source: str) -> list[tuple[int, int, str]]:
    """Return `(start, end, text)` for each top-level figure call."""
    calls: list[tuple[int, int, str]] = []
    pos = 0
    for line in source.splitlines(keepends=True):
        stripped = line.lstrip()
        match = re.match(r"#(" + "|".join(FIGURE_CALLS) + r")\s*\(", stripped)
        if match:
            start = pos + len(line) - len(stripped)
            end = _scan_call(source, start)
            calls.append((start, end, source[start:end]))
        pos += len(line)
    return calls


def mermaid_import(source: str) -> str:
    for line in source.splitlines():
        if line.lstrip().startswith("#import") and "mermaid" in line:
            return line.strip()
    return DEFAULT_IMPORT


# --------------------------------------------------------------------------
# render
# --------------------------------------------------------------------------

def render(index: int, outdir: Path) -> tuple[Path, Path]:
    source = THESIS.read_text(encoding="utf8")
    calls = figure_calls(source)
    if not calls:
        raise DiagramError("thesis.typ contains no #mermaid/#figure/#image call")
    if index >= len(calls):
        raise DiagramError(
            f"thesis.typ has {len(calls)} figure(s); there is no index {index}"
        )

    outdir.mkdir(parents=True, exist_ok=True)
    typ = outdir / f"diagram-{index}.typ"
    svg = outdir / f"diagram-{index}.svg"
    png = outdir / f"diagram-{index}.png"

    typ.write_text(
        f"{mermaid_import(source)}\n"
        "#set page(width: auto, height: auto, margin: 0pt)\n"
        f"{calls[index][2]}\n",
        encoding="utf8",
    )

    for args in (
        ["compile", "--format", "svg", str(typ), str(svg)],
        ["compile", "--format", "png", "--ppi", "300", str(typ), str(png)],
    ):
        try:
            subprocess.run(["typst", *args], check=True, cwd=ROOT)
        except FileNotFoundError as exc:  # pragma: no cover - env error
            raise DiagramError("typst not found; run inside nix develop") from exc
        except subprocess.CalledProcessError as exc:
            raise DiagramError(f"typst failed for diagram {index}") from exc

    return svg, png


# --------------------------------------------------------------------------
# DOCX package editing
# --------------------------------------------------------------------------

def _next_image_number(names: list[str]) -> int:
    numbers = [int(m.group(1)) for n in names if (m := re.search(r"image(\d+)\.", n))]
    return max(numbers, default=0) + 1


def _next_rid(rels: str) -> tuple[str, int]:
    numbers = [int(n) for n in re.findall(r'Id="rId(\d+)"', rels)]
    nxt = max(numbers, default=0) + 1
    return f"rId{nxt}", nxt + 1


def _unique_para_id(xml: str) -> str:
    while True:
        candidate = f"{secrets.randbelow(0x80000000):08X}"
        if candidate not in xml:
            return candidate


def _paragraph_end(xml: str, start: int) -> int:
    """Index just past the `</w:p>` matching the paragraph that starts at start."""
    depth = 0
    for match in re.finditer(r"<w:p(?:\s[^>]*)?>|</w:p>", xml[start:]):
        if match.group(0).startswith("</"):
            depth -= 1
            if depth == 0:
                return start + match.end()
        else:
            depth += 1
    raise DiagramError("unterminated paragraph in document.xml")


def _drawing_paragraph(
    *,
    para_id: str,
    cx: int,
    cy: int,
    doc_pr_id: int,
    png_rid: str,
    svg_rid: str,
    name: str,
    alt: str,
) -> str:
    name = _xml_escape(name)
    alt = _xml_escape(alt)
    return (
        f'<w:p w14:paraId="{para_id}" w14:textId="77777777">'
        '<w:pPr><w:jc w:val="center"/><w:rPr><w:noProof/></w:rPr></w:pPr>'
        "<w:r><w:drawing>"
        '<wp:inline distT="0" distB="0" distL="0" distR="0">'
        f'<wp:extent cx="{cx}" cy="{cy}"/>'
        '<wp:effectExtent l="0" t="0" r="0" b="0"/>'
        f'<wp:docPr id="{doc_pr_id}" name="{name}" descr="{alt}"/>'
        "<wp:cNvGraphicFramePr>"
        f'<a:graphicFrameLocks xmlns:a="{NS_A}" noChangeAspect="1"/>'
        "</wp:cNvGraphicFramePr>"
        f'<a:graphic xmlns:a="{NS_A}">'
        f'<a:graphicData uri="{NS_PIC}">'
        f'<pic:pic xmlns:pic="{NS_PIC}">'
        f'<pic:nvPicPr><pic:cNvPr id="0" name="{name}" descr="{alt}"/>'
        '<pic:cNvPicPr><a:picLocks noChangeAspect="1" noChangeArrowheads="1"/>'
        "</pic:cNvPicPr></pic:nvPicPr>"
        "<pic:blipFill>"
        f'<a:blip r:embed="{png_rid}"><a:extLst>'
        f'<a:ext uri="{SVG_EXT_URI}">'
        f'<asvg:svgBlip xmlns:asvg="{NS_ASVG}" r:embed="{svg_rid}"/>'
        "</a:ext></a:extLst></a:blip>"
        "<a:srcRect/><a:stretch><a:fillRect/></a:stretch>"
        "</pic:blipFill>"
        "<pic:spPr>"
        f'<a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
        "</pic:spPr>"
        "</pic:pic></a:graphicData></a:graphic>"
        "</wp:inline></w:drawing></w:r></w:p>"
    )


def _xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _save(zip_path: Path, entries: dict[str, bytes]) -> None:
    tmp = zip_path.with_suffix(zip_path.suffix + ".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
        for name, data in entries.items():
            out.writestr(name, data)
    shutil.move(tmp, zip_path)


def insert(
    docx: Path,
    *,
    after: str | None,
    anchor: str | None,
    index: int,
    alt: str,
    max_width_cm: float,
    max_height_cm: float,
) -> dict:
    svg, png = render(index, CACHE)

    with zipfile.ZipFile(docx) as zf:
        entries = {name: zf.read(name) for name in zf.namelist()}

    document = entries["word/document.xml"].decode("utf8")
    rels = entries["word/_rels/document.xml.rels"].decode("utf8")
    types = entries["[Content_Types].xml"].decode("utf8")

    if after:
        marker = f'w14:paraId="{after.upper()}"'
        start = document.find("<w:p")
        while start != -1:
            head_end = document.find(">", start)
            if marker in document[start:head_end]:
                break
            start = document.find("<w:p", start + 1)
        if start == -1:
            raise DiagramError(f"no paragraph with paraId {after}")
    elif anchor:
        needle = _xml_escape(anchor)
        pos = document.find(needle)
        if pos == -1:
            raise DiagramError(f"anchor text not found: {anchor!r}")
        start = document.rfind("<w:p", 0, pos)
        if start == -1:
            raise DiagramError("anchor text is not inside a paragraph")
    else:
        raise DiagramError("pass --after PARAID or --anchor TEXT")

    end = _paragraph_end(document, start)

    width_pt, height_pt = _svg_size(svg)
    scale = min(
        max_width_cm * EMU_PER_CM / (width_pt * EMU_PER_PT),
        max_height_cm * EMU_PER_CM / (height_pt * EMU_PER_PT),
    )
    cx = round(width_pt * EMU_PER_PT * scale)
    cy = round(height_pt * EMU_PER_PT * scale)

    next_image = _next_image_number(list(entries))
    svg_name = f"image{next_image}.svg"
    png_name = f"image{next_image}.png"
    entries[f"word/media/{svg_name}"] = svg.read_bytes()
    entries[f"word/media/{png_name}"] = png.read_bytes()

    png_rid, svg_rid_num = _next_rid(rels)
    svg_rid = f"rId{svg_rid_num}"
    rel_type = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
    rels = rels.replace(
        "</Relationships>",
        f'<Relationship Id="{png_rid}" Type="{rel_type}" Target="media/{png_name}"/>'
        f'<Relationship Id="{svg_rid}" Type="{rel_type}" Target="media/{svg_name}"/>'
        "</Relationships>",
    )
    entries["word/_rels/document.xml.rels"] = rels.encode("utf8")

    if not re.search(r'<Default[^>]*Extension="svg"', types):
        types = types.replace(
            "</Types>",
            '<Default Extension="svg" ContentType="image/svg+xml"/></Types>',
        )
        entries["[Content_Types].xml"] = types.encode("utf8")

    doc_pr_ids = [int(n) for n in re.findall(r'<wp:docPr id="(\d+)"', document)]
    doc_pr_id = max(doc_pr_ids, default=0) + 1
    para_id = _unique_para_id(document)

    paragraph = _drawing_paragraph(
        para_id=para_id,
        cx=cx,
        cy=cy,
        doc_pr_id=doc_pr_id,
        png_rid=png_rid,
        svg_rid=svg_rid,
        name=f"Ábra {index + 1}",
        alt=alt,
    )
    document = document[:end] + paragraph + document[end:]
    entries["word/document.xml"] = document.encode("utf8")

    _save(docx, entries)
    return {
        "para_id": para_id,
        "svg": f"word/media/{svg_name}",
        "png": f"word/media/{png_name}",
        "width_cm": round(cx / EMU_PER_CM, 2),
        "height_cm": round(cy / EMU_PER_CM, 2),
    }


def _svg_size(svg: Path) -> tuple[float, float]:
    head = svg.read_text(encoding="utf8")[:2000]
    width = re.search(r'\bwidth="([\d.]+)pt"', head)
    height = re.search(r'\bheight="([\d.]+)pt"', head)
    if not width or not height:
        raise DiagramError(f"cannot read the size of {svg}")
    return float(width.group(1)), float(height.group(1))


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_render = sub.add_parser("render", help="render a diagram to SVG and PNG")
    p_render.add_argument("--index", type=int, default=0)
    p_render.add_argument("--outdir", type=Path, default=CACHE)

    p_insert = sub.add_parser("insert", help="embed a diagram in the DOCX")
    p_insert.add_argument("docx", type=Path)
    p_insert.add_argument("--index", type=int, default=0)
    p_insert.add_argument("--after", help="paraId of the paragraph to insert after")
    p_insert.add_argument("--anchor", help="text of the paragraph to insert after")
    p_insert.add_argument("--alt", default="", help="image alt text")
    p_insert.add_argument("--max-width", type=float, default=12.0, help="cm")
    p_insert.add_argument("--max-height", type=float, default=18.0, help="cm")

    args = parser.parse_args(argv)

    try:
        if args.command == "render":
            svg, png = render(args.index, args.outdir)
            print(f"{svg}\n{png}")
        else:
            result = insert(
                args.docx,
                after=args.after,
                anchor=args.anchor,
                index=args.index,
                alt=args.alt,
                max_width_cm=args.max_width,
                max_height_cm=args.max_height,
            )
            for key, value in result.items():
                print(f"{key}: {value}")
    except DiagramError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
