#!/usr/bin/env python3
"""Rebuild print.html from chapter pages listed in contents.html."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "print.html"
SKIP_PAGES = {"tips.html", "search.html", "print.html"}
SKIP_SCRIPTS = {"js/search.js", "js/search-index.js"}

HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ENSONIQ TS-10/TS-12 Musician’s Manual</title>
  <link rel="stylesheet" href="css/manual.css">
</head>
<body class="print-book">
<p class="print-toolbar"><button type="button" onclick="window.print()">Print / Save as PDF</button></p>
"""

FOOT = """</body>
</html>
"""

ARTICLE_OPEN = re.compile(r"<article\b([^>]*)>", re.I)
HREF_RE = re.compile(r'href="([^"]+)"')
SCRIPT_RE = re.compile(r'<script\b[^>]*\ssrc="([^"]+)"[^>]*>\s*</script>', re.I)
CLASS_RE = re.compile(r'\bclass="([^"]*)"', re.I)


def extract_article(html: str, path: Path) -> tuple[str, str]:
    match = ARTICLE_OPEN.search(html)
    if not match:
        raise SystemExit(f"No <article> in {path.name}")
    start = match.end()
    depth = 1
    pos = start
    open_tag = re.compile(r"<article\b", re.I)
    close_tag = re.compile(r"</article>", re.I)
    while depth:
        nxt_open = open_tag.search(html, pos)
        nxt_close = close_tag.search(html, pos)
        if not nxt_close:
            raise SystemExit(f"Unclosed <article> in {path.name}")
        if nxt_open and nxt_open.start() < nxt_close.start():
            depth += 1
            pos = nxt_open.end()
        else:
            depth -= 1
            if depth == 0:
                inner = html[start : nxt_close.start()]
                classes = CLASS_RE.search(match.group(1))
                return (classes.group(1) if classes else "manual"), inner
            pos = nxt_close.end()
    raise SystemExit(f"Unclosed <article> in {path.name}")


def print_classes(source_classes: str) -> str:
    tokens = [t for t in source_classes.split() if t != "print-section"]
    if "manual" not in tokens:
        tokens.insert(0, "manual")
    return " ".join(["print-section"] + tokens)


def toc_files(contents_html: str) -> list[str]:
    nav = re.search(r'<nav class="toc-page">(.*?)</nav>', contents_html, re.S)
    if not nav:
        raise SystemExit("No toc-page nav in contents.html")
    files: list[str] = []
    seen: set[str] = set()
    for href in HREF_RE.findall(nav.group(1)):
        name = href.split("#", 1)[0]
        if name in SKIP_PAGES or name in seen:
            continue
        seen.add(name)
        files.append(name)
    return files


def page_scripts(html: str) -> list[str]:
    out = []
    for src in SCRIPT_RE.findall(html):
        if src not in SKIP_SCRIPTS and src not in out:
            out.append(src)
    return out


def wrap_article(classes: str, inner: str) -> str:
    return f'<article class="{print_classes(classes)}">{inner}</article>\n'


def main() -> int:
    cover_html = (ROOT / "index.html").read_text()
    contents_html = (ROOT / "contents.html").read_text()

    parts = [HEAD]
    scripts: list[str] = []

    cover_cls, cover_inner = extract_article(cover_html, ROOT / "index.html")
    parts.append(wrap_article(cover_cls, cover_inner))

    contents_cls, contents_inner = extract_article(contents_html, ROOT / "contents.html")
    parts.append(wrap_article(contents_cls, contents_inner))

    for name in toc_files(contents_html):
        path = ROOT / name
        if not path.is_file():
            raise SystemExit(f"Missing chapter {name}")
        html = path.read_text()
        cls, inner = extract_article(html, path)
        parts.append(wrap_article(cls, inner))
        for src in page_scripts(html):
            if src not in scripts:
                scripts.append(src)

    for src in scripts:
        parts.append(f'<script src="{src}"></script>\n')
    parts.append(FOOT)

    OUT.write_text("".join(parts))
    print(f"Wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
