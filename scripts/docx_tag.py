#!/usr/bin/env python3
"""Read/write the sync-base marker embedded in the .docx package.

The marker lives in `docProps/custom.xml`, so "the DOCX contains commit X" and
"the DOCX says it contains commit X" are the same bytes. That makes the marker
travel atomically with the document through OneDrive.

Usage:
    docx_tag.py get FILE
    docx_tag.py set FILE VALUE

`get` prints the marker (empty string if absent). `set` rewrites the package in
place, preserving every other part and every other custom property.
"""

from __future__ import annotations

import os
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
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CP_NS = "http://schemas.openxmlformats.org/officeDocument/2006/custom-properties"
VT_NS = "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"

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


def get_marker(path: str) -> str:
    with zipfile.ZipFile(path) as zf:
        try:
            raw = zf.read(CUSTOM_PART)
        except KeyError:
            return ""
    root = ET.fromstring(raw)
    for prop in root.findall(q(CP_NS, "property")):
        if prop.get("name") != PROP_NAME:
            continue
        for child in prop:
            return (child.text or "").strip()
    return ""


def set_marker(path: str, value: str) -> None:
    parts = read_parts(path)

    # 1. custom.xml — update or create our property, keep the others.
    if CUSTOM_PART in parts:
        root = ET.fromstring(parts[CUSTOM_PART])
        for prop in list(root.findall(q(CP_NS, "property"))):
            if prop.get("name") == PROP_NAME:
                root.remove(prop)
    else:
        root = ET.Element(q(CP_NS, "Properties"))

    props = list(root.findall(q(CP_NS, "property")))
    used_pids = {p.get("pid") for p in props}
    pid = 2
    while str(pid) in used_pids:
        pid += 1

    prop = ET.SubElement(root, q(CP_NS, "property"))
    prop.set("fmtid", "{D5CDD505-2E9C-101B-9397-08002B2CF9AE}")
    prop.set("pid", str(pid))
    prop.set("name", PROP_NAME)
    ET.SubElement(prop, q(VT_NS, "lpwstr")).text = value

    parts[CUSTOM_PART] = ET.tostring(root, encoding="UTF-8", xml_declaration=True)

    # 2. [Content_Types].xml — register the part.
    ct = ET.fromstring(parts[CT_PART])
    target = "/" + CUSTOM_PART
    if not any(
        el.get("PartName") == target for el in ct.findall(q(CT_NS, "Override"))
    ):
        override = ET.SubElement(ct, q(CT_NS, "Override"))
        override.set("PartName", target)
        override.set("ContentType", CUSTOM_CT)
    parts[CT_PART] = ET.tostring(ct, encoding="UTF-8", xml_declaration=True)

    # 3. _rels/.rels — point at the part.
    rels = ET.fromstring(parts[REL_PART])
    if not any(
        el.get("Type") == CUSTOM_REL
        for el in rels.findall(q(REL_NS, "Relationship"))
    ):
        ids = {el.get("Id") for el in rels.findall(q(REL_NS, "Relationship"))}
        rid, n = "rIdSyncBase", 1
        while rid in ids:
            n += 1
            rid = f"rIdSyncBase{n}"
        rel = ET.SubElement(rels, q(REL_NS, "Relationship"))
        rel.set("Id", rid)
        rel.set("Type", CUSTOM_REL)
        rel.set("Target", CUSTOM_PART)
    parts[REL_PART] = ET.tostring(rels, encoding="UTF-8", xml_declaration=True)

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
