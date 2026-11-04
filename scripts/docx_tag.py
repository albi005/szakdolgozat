#!/usr/bin/env python3
"""Read/write the sync-base marker embedded in the .docx package.

The marker lives in `docProps/custom.xml`, so "the DOCX contains commit X" and
"the DOCX says it contains commit X" are the same bytes. That makes the marker
travel atomically with the document through OneDrive.

Usage:
    docx_tag.py get FILE
    docx_tag.py set FILE VALUE

`get` prints the marker (empty string if absent). `set` rewrites the package in
place, preserving every other part.

IMPORTANT: `[Content_Types].xml` and `_rels/.rels` are edited as text, never
round-tripped through an XML library. ElementTree rewrites the default
namespace as an `ns0:` prefix, and OPC readers that look elements up by
qualified name then find nothing — Word Online reports the package as corrupt.
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
import zipfile
from xml.etree import ElementTree as ET

PROP_NAME = "ThesisSyncBase"

CT_PART = "[Content_Types].xml"
REL_PART = "_rels/.rels"
CUSTOM_PART = "docProps/custom.xml"

CUSTOM_CT = "application/vnd.openxmlformats-officedocument.custom-properties+xml"
CUSTOM_REL = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties"
)
CP_NS = "http://schemas.openxmlformats.org/officeDocument/2006/custom-properties"
VT_NS = "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"
FMTID = "{D5CDD505-2E9C-101B-9397-08002B2CF9AE}"

ET.register_namespace("", CP_NS)
ET.register_namespace("vt", VT_NS)


def q(ns: str, tag: str) -> str:
    return f"{{{ns}}}{tag}"


def read_parts(path: str) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as zf:
        return {item.filename: zf.read(item.filename) for item in zf.infolist()}


def write_parts(path: str, parts: dict[str, bytes]) -> None:
    """Rewrite the package, keeping the original entry order and compression."""
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)), suffix=".docx")
    os.close(fd)
    try:
        with zipfile.ZipFile(path) as src:
            info = src.infolist()
            order = [item.filename for item in info]
            compress = {item.filename: item.compress_type for item in info}
        for name in parts:
            if name not in order:
                order.append(name)
                compress[name] = zipfile.ZIP_DEFLATED
        with zipfile.ZipFile(tmp, "w") as dst:
            for name in order:
                dst.writestr(name, parts[name], compress_type=compress[name])
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def insert_before_close(text: str, local_name: str, fragment: str) -> str:
    """Insert `fragment` just before the closing tag of `local_name`.

    Works for both `<Types>` and `<ns0:Types>`, and leaves every other byte of
    the part untouched.
    """
    match = re.search(rf"</(?:[A-Za-z_][\w.-]*:)?{local_name}\s*>", text)
    if match is None:
        raise ValueError(f"no closing {local_name} tag found")
    return text[: match.start()] + fragment + text[match.start() :]


def get_marker(path: str) -> str:
    with zipfile.ZipFile(path) as zf:
        try:
            raw = zf.read(CUSTOM_PART)
        except KeyError:
            return ""
    for prop in ET.fromstring(raw).findall(q(CP_NS, "property")):
        if prop.get("name") != PROP_NAME:
            continue
        for child in prop:
            return (child.text or "").strip()
    return ""


def build_custom_xml(parts: dict[str, bytes], value: str) -> bytes:
    """Return custom.xml with our property set and every other property kept."""
    if CUSTOM_PART in parts:
        root = ET.fromstring(parts[CUSTOM_PART])
        for prop in list(root.findall(q(CP_NS, "property"))):
            if prop.get("name") == PROP_NAME:
                root.remove(prop)
    else:
        root = ET.Element(q(CP_NS, "Properties"))

    used = {p.get("pid") for p in root.findall(q(CP_NS, "property"))}
    pid = 2
    while str(pid) in used:
        pid += 1

    prop = ET.SubElement(root, q(CP_NS, "property"))
    prop.set("fmtid", FMTID)
    prop.set("pid", str(pid))
    prop.set("name", PROP_NAME)
    ET.SubElement(prop, q(VT_NS, "lpwstr")).text = value

    body = ET.tostring(root, encoding="unicode")
    # Word writes a standalone declaration; match it.
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n' + body
    ).encode("utf-8")


def set_marker(path: str, value: str) -> None:
    parts = read_parts(path)

    parts[CUSTOM_PART] = build_custom_xml(parts, value)

    ct = parts[CT_PART].decode("utf-8")
    if 'PartName="/docProps/custom.xml"' not in ct:
        ct = insert_before_close(
            ct,
            "Types",
            f'<Override PartName="/{CUSTOM_PART}" ContentType="{CUSTOM_CT}"/>',
        )
        parts[CT_PART] = ct.encode("utf-8")

    rels = parts[REL_PART].decode("utf-8")
    if 'Target="docProps/custom.xml"' not in rels:
        ids = set(re.findall(r'Id="([^"]+)"', rels))
        rid, n = "rIdSyncBase", 1
        while rid in ids:
            n += 1
            rid = f"rIdSyncBase{n}"
        rels = insert_before_close(
            rels,
            "Relationships",
            f'<Relationship Id="{rid}" Type="{CUSTOM_REL}" Target="{CUSTOM_PART}"/>',
        )
        parts[REL_PART] = rels.encode("utf-8")

    write_parts(path, parts)


def main(argv: list[str]) -> int:
    if len(argv) == 3 and argv[1] == "get":
        print(get_marker(argv[2]))
        return 0
    if len(argv) == 4 and argv[1] == "set":
        set_marker(argv[2], argv[3])
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
