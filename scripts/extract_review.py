#!/usr/bin/env python3
"""Turn Pandoc's `--track-changes=all` JSON into a readable review report.

Word comments become `comment-start` / `comment-end` spans in Pandoc's AST.
Tracked insertions and deletions become `insertion` / `deletion` spans.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def text_of(node) -> str:
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(text_of(item) for item in node)
    if not isinstance(node, dict):
        return ""

    t = node.get("t")
    c = node.get("c")

    if t == "Str":
        return c
    if t in ("Space", "SoftBreak", "LineBreak"):
        return " "
    if t == "Code":
        return f"`{c[1]}`"
    if t == "Math":
        return c[1]
    if t == "RawInline":
        return c[1]
    if t == "Quoted":
        return "„" + text_of(c[1]) + "”"
    if t == "Link":
        return text_of(c[1])
    if t == "Image":
        return "[kép]"
    if t in (
        "Emph",
        "Strong",
        "Strikeout",
        "Superscript",
        "Subscript",
        "SmallCaps",
        "Underline",
        "Span",
    ):
        return text_of(c[1] if t == "Span" else c)
    if t == "Note":
        return " " + text_of(c) + " "
    return ""


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


class Collector:
    def __init__(self) -> None:
        self.comments: list[dict[str, str]] = []
        self.open_comments: list[dict[str, str]] = []
        self.insertions: list[dict[str, str]] = []
        self.deletions: list[dict[str, str]] = []
        self.recent: list[str] = []

    def add_text(self, s: str) -> None:
        for comment in self.open_comments:
            comment["context"].append(s)
        self.recent.append(s)
        if len(self.recent) > 2000:
            self.recent = self.recent[-1000:]

    def context(self) -> str:
        return norm("".join(self.recent))[-300:]

    def walk(self, node) -> None:
        if node is None:
            return
        if isinstance(node, list):
            for item in node:
                self.walk(item)
            return
        if not isinstance(node, dict):
            return

        t = node.get("t")
        c = node.get("c")

        if t == "Span":
            attrs, content = c
            classes = attrs[1] or []
            meta = {k: v for k, v in (attrs[2] or [])}

            if "comment-start" in classes:
                self.open_comments.append(
                    {
                        "id": meta.get("id", ""),
                        "author": meta.get("author", ""),
                        "date": meta.get("date", ""),
                        "comment": norm(text_of(content)),
                        "context": [],
                    }
                )
                return

            if "comment-end" in classes:
                if self.open_comments:
                    self.comments.append(self.open_comments.pop())
                return

            if "insertion" in classes:
                self.insertions.append(
                    {"text": norm(text_of(content)), "context": self.context()}
                )
                self.add_text(" " + text_of(content) + " ")
                return

            if "deletion" in classes:
                self.deletions.append(
                    {"text": norm(text_of(content)), "context": self.context()}
                )
                self.add_text(" " + text_of(content) + " ")
                return

            self.walk(content)
            return

        if t in ("Str", "Space", "SoftBreak", "LineBreak", "Code", "Math", "RawInline"):
            self.add_text(text_of(node))
            return

        if t == "Image":
            self.add_text("[kép]")
            return

        if t == "Link":
            self.walk(c[1])
            return

        if t == "Note":
            self.walk(c)
            return

        if t in ("Para", "Plain", "Header"):
            self.add_text(" ")
            self.walk(c)
            self.add_text(" ")
            return

        # Generic recursion: covers lists, tables, etc.
        self.walk(c)


def bullet_list(items: list[dict[str, str]], kind: str) -> list[str]:
    if not items:
        return []
    lines = [f"## {kind} ({len(items)})", ""]
    for item in items:
        text = item["text"] or "(üres)"
        lines.append(f"- **{text}**")
        if item["context"]:
            lines.append(f"  - Kontextus: …{item['context']}…")
    lines.append("")
    return lines


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(f"usage: {sys.argv[0]} REVIEW.json OUTPUT.md")

    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf8"))
    collector = Collector()
    collector.walk(data.get("blocks", []))

    comments = collector.comments
    insertions = collector.insertions
    deletions = collector.deletions

    out = ["# Review report", ""]

    if comments:
        out += [f"## Comments ({len(comments)})", ""]
        for i, comment in enumerate(comments, 1):
            out += [
                f"### {i}. {comment['author'] or 'Névtelen'}",
                "",
                f"**Dátum:** {comment['date'] or 'ismeretlen'}",
                "",
                f"**Megjegyzés:** {comment['comment']}",
                "",
            ]
            context = norm("".join(comment["context"]))
            if context:
                out += [f"> {context}", ""]
            out += ["- [ ] Megoldva", ""]
    else:
        out += ["## Comments", "", "Nincs megjegyzés.", ""]

    out += bullet_list(insertions, "Tracked insertions")
    out += bullet_list(deletions, "Tracked deletions")

    if not comments and not insertions and not deletions:
        out += ["Nincs javaslat vagy megjegyzés.", ""]

    Path(sys.argv[2]).write_text("\n".join(out), encoding="utf8")


if __name__ == "__main__":
    main()
