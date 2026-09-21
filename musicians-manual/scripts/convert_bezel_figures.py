#!/usr/bin/env python3
"""Convert vfd-bezel figures in chapter HTML to exported display SVGs + img tags."""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POS = {"tl": "top-1", "tc": "top-2", "tr": "top-3", "bl": "bottom-1", "bc": "bottom-2", "br": "bottom-3"}


def strip_tags(fragment: str) -> str:
    text = re.sub(r"<br\s*/?>", " ", fragment, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).replace("\xa0", " ").strip()


def cell_text_and_underline(inner: str, whole_selected: bool) -> tuple[str, int | None, int | None]:
    plain = strip_tags(inner)
    if whole_selected:
        return plain, 0, len(plain) if plain else None
    m = re.search(r'<span class="selected">([^<]*)</span>', inner, re.I)
    if not m:
        return plain, None, None
    before = strip_tags(re.sub(r'<span class="selected">[^<]*</span>', "", inner, flags=re.I))
    sel = m.group(1).upper()
    # Reconstruct plain with selected segment
    full = strip_tags(inner.replace("<span class=\"selected\">", "").replace("</span>", ""))
    idx = full.find(sel)
    if idx < 0:
        idx = full.find(m.group(1))
    if idx < 0:
        return plain, None, None
    return full, idx, len(sel)


def parse_rows(table_html: str) -> tuple[bool, list[list[dict]]]:
    has_page = "page-col" in table_html
    tbody = re.search(r"<tbody[^>]*>([\s\S]*?)</tbody>", table_html, re.I)
    if not tbody:
        return has_page, []
    rows: list[list[dict]] = []
    for tr in re.finditer(r"<tr[^>]*>([\s\S]*?)</tr>", tbody.group(1), re.I):
        cells = []
        for td in re.finditer(r"<td([^>]*)>([\s\S]*?)</td>", tr.group(1), re.I):
            attrs, inner = td.group(1), td.group(2)
            colspan = 1
            cm = re.search(r'colspan="(\d+)"', attrs, re.I)
            if cm:
                colspan = int(cm.group(1))
            is_page = "page-label" in attrs
            whole_sel = "selected" in attrs and "page-label" not in attrs
            text, u0, ulen = cell_text_and_underline(inner, whole_sel)
            cells.append(
                {
                    "text": text,
                    "colspan": colspan,
                    "page_label": is_page,
                    "underline_start": u0,
                    "underline_len": ulen,
                }
            )
        if cells:
            rows.append(cells)
    return has_page, rows


def pressed_buttons(fig_html: str) -> dict[str, str]:
    states = {}
    for m in re.finditer(
        r'<button[^>]*class="[^"]*soft-btn[^"]*pressed[^"]*"[^>]*data-pos="(tl|tc|tr|bl|bc|br)"',
        fig_html,
        re.I,
    ):
        states[POS[m.group(1)]] = "pressed"
    return states


def parse_callouts(fig_html: str, has_page: bool) -> list[dict]:
    callouts: list[dict] = []
    for side in ("top", "bottom"):
        block = re.search(rf'<div class="vfd-callouts {side}[^"]*">([\s\S]*?)</div>', fig_html, re.I)
        if not block:
            continue
        parts = re.findall(r"<div[^>]*>([\s\S]*?)</div>", block.group(1), re.I)
        # first div may be page-spacer
        texts = [strip_tags(p) for p in parts if strip_tags(p)]
        if not has_page:
            ids = ["top-1", "top-2", "top-3"] if side == "top" else ["bottom-1", "bottom-2", "bottom-3"]
        else:
            ids = ["top-1", "top-2", "top-3"] if side == "top" else ["bottom-1", "bottom-2", "bottom-3"]
        idx = 0
        for text in texts:
            if idx >= len(ids):
                break
            bid = ids[idx]
            idx += 1
            callouts.append(
                {
                    "id": f"callout-{len(callouts)+1}",
                    "side": side,
                    "text": text,
                    "target": {"type": "string", "id": bid, "start": 0, "length": 1},
                }
            )
    return callouts


def expand_row(cells: list[dict]) -> list[dict]:
    out: list[dict] = []
    for c in cells:
        for _ in range(c["colspan"]):
            out.append(c)
    return out


PAGE_COL_WIDTH = 5
PARAM_WIDTHS = (12, 12, 11)
NO_PAGE_WIDTHS = (13, 13, 14)


def cell_plain(text: str) -> str:
    t = text.strip()
    return "" if not t else t


def format_has_page_row(cells: list[dict]) -> str:
    if not cells:
        return " " * 40
    if cells[0]["page_label"]:
        page = cell_plain(cells[0]["text"])[:PAGE_COL_WIDTH].ljust(PAGE_COL_WIDTH)
        data = cells[1:]
    else:
        page = " " * PAGE_COL_WIDTH
        data = cells

    slot = 0
    parts: list[str] = []
    for cell in data:
        if slot >= 3:
            break
        text = cell_plain(cell["text"])
        span = cell["colspan"]
        if span >= 3:
            w = sum(PARAM_WIDTHS)
            return (page + text[:w].ljust(w))[:40].ljust(40)
        if span == 2:
            w = PARAM_WIDTHS[0] + PARAM_WIDTHS[1]
            return (page + text[:w].ljust(w) + " " * PARAM_WIDTHS[2])[:40].ljust(40)
        w = PARAM_WIDTHS[slot]
        parts.append(text[:w].ljust(w))
        slot += 1
    while len(parts) < 3:
        parts.append(" " * PARAM_WIDTHS[len(parts)])
    return (page + "".join(parts))[:40].ljust(40)


def format_no_page_row(cells: list[dict]) -> str:
    slot = 0
    parts: list[str] = []
    for cell in cells:
        if slot >= 3:
            break
        text = cell_plain(cell["text"])
        span = cell["colspan"]
        if span >= 3:
            return text[:40].ljust(40)
        if span == 2:
            w = NO_PAGE_WIDTHS[0] + NO_PAGE_WIDTHS[1]
            return (text[:w].ljust(w) + " " * NO_PAGE_WIDTHS[2])[:40].ljust(40)
        w = NO_PAGE_WIDTHS[slot]
        parts.append(text[:w].ljust(w))
        slot += 1
    while len(parts) < 3:
        parts.append(" " * NO_PAGE_WIDTHS[len(parts)])
    return "".join(parts)[:40].ljust(40)


def format_table_row(cells: list[dict], has_page: bool) -> str:
    return format_has_page_row(cells) if has_page else format_no_page_row(cells)


def raw_effects_for_rows(rows: list[list[dict]], lines: list[str], has_page: bool) -> list[dict]:
    effects: list[dict] = []
    for ri, row in enumerate(rows[:2]):
        line = lines[ri]
        col = 0
        if has_page and row and row[0]["page_label"]:
            col = PAGE_COL_WIDTH
            data = row[1:]
        else:
            data = row
        slot = 0
        for cell in data:
            if slot >= 3:
                break
            text = cell_plain(cell["text"])
            span = cell["colspan"]
            if span >= 3:
                width = sum(PARAM_WIDTHS) if has_page else 40 - col
            elif span == 2:
                width = (PARAM_WIDTHS[0] + PARAM_WIDTHS[1]) if has_page else NO_PAGE_WIDTHS[0] + NO_PAGE_WIDTHS[1]
            else:
                width = (PARAM_WIDTHS[slot] if has_page else NO_PAGE_WIDTHS[slot])
            if cell["underline_start"] is not None and cell["underline_len"] and text:
                effects.append(
                    {
                        "target": {
                            "type": "range",
                            "row": ri,
                            "start": col + cell["underline_start"],
                            "length": cell["underline_len"],
                        },
                        "underline": True,
                    }
                )
            col += width
            slot += span
    return effects


def button_strings_for_row(cells: list[dict], side: str) -> list[tuple[str, dict]]:
    ids = ["top-1", "top-2", "top-3"] if side == "top" else ["bottom-1", "bottom-2", "bottom-3"]
    if cells and cells[0]["page_label"]:
        data = cells[1:]
    else:
        data = cells
    out: list[tuple[str, dict]] = []
    slot = 0
    for cell in data:
        if slot >= 3:
            break
        text = cell_plain(cell["text"])
        if text:
            out.append((ids[slot], cell))
        slot += cell["colspan"]
    return out


def semantic_row_lengths(screen: dict) -> tuple[list[int], list[int]]:
    top: list[int] = []
    bottom: list[int] = []
    if screen.get("pageHeader"):
        top.append(len(cell_plain(screen["pageHeader"])))
    if screen.get("pageFooter"):
        bottom.append(len(cell_plain(screen["pageFooter"])))
    for item in screen.get("buttonStrings") or []:
        n = len(item["text"])
        if item["button"].startswith("top-"):
            top.append(n)
        else:
            bottom.append(n)
    return top, bottom


def semantic_packs(screen: dict) -> bool:
    for lengths in semantic_row_lengths(screen):
        if not lengths:
            continue
        if sum(lengths) + len(lengths) - 1 > 40:
            return False
    for item in screen.get("buttonStrings") or []:
        if len(item["text"]) > 40:
            return False
    return True


def build_semantic_screen(has_page: bool, rows: list[list[dict]]) -> dict:
    screen: dict = {"rowJustify": {"row0": "left", "row1": "left"}}
    effects: list[dict] = []
    if not has_page or not rows:
        return screen
    r0, r1 = rows[0], rows[1] if len(rows) > 1 else []
    if r0 and r0[0]["page_label"] and cell_plain(r0[0]["text"]):
        screen["pageHeader"] = cell_plain(r0[0]["text"])
    if r1 and r1[0]["page_label"] and cell_plain(r1[0]["text"]):
        screen["pageFooter"] = cell_plain(r1[0]["text"])
    button_strings = []
    for bid, cell in button_strings_for_row(r0, "top"):
        text = cell_plain(cell["text"])
        button_strings.append({"id": bid, "button": bid, "text": text})
        if cell["underline_start"] is not None and cell["underline_len"]:
            effects.append(
                {
                    "target": {
                        "type": "string",
                        "id": bid,
                        "start": cell["underline_start"],
                        "length": cell["underline_len"],
                    },
                    "underline": True,
                }
            )
    for bid, cell in button_strings_for_row(r1, "bottom"):
        text = cell_plain(cell["text"])
        button_strings.append({"id": bid, "button": bid, "text": text})
        if cell["underline_start"] is not None and cell["underline_len"]:
            effects.append(
                {
                    "target": {
                        "type": "string",
                        "id": bid,
                        "start": cell["underline_start"],
                        "length": cell["underline_len"],
                    },
                    "underline": True,
                }
            )
    if button_strings:
        screen["buttonStrings"] = button_strings
    if effects:
        screen["effects"] = effects
    return screen


def build_raw_screen(has_page: bool, rows: list[list[dict]]) -> dict:
    lines = [format_table_row(row, has_page) for row in rows[:2]]
    while len(lines) < 2:
        lines.append(" " * 40)
    screen: dict = {"rowJustify": {"row0": "left", "row1": "left"}, "rows": lines[:2]}
    effects = raw_effects_for_rows(rows, lines, has_page)
    if effects:
        screen["effects"] = effects
    return screen


def figure_to_screen(fig_html: str) -> dict:
    table = re.search(r"<div class=\"vfd-bezel\">([\s\S]*?)</div>", fig_html, re.I)
    if not table:
        raise ValueError("no bezel")
    has_page = "has-page" in fig_html or "page-col" in table.group(1)
    _, rows = parse_rows(table.group(1))
    if not rows:
        return {"rowJustify": {"row0": "left", "row1": "left"}, "rows": [" " * 40, " " * 40]}

    use_semantic = has_page and rows and len(expand_row(rows[0])) >= 4
    if use_semantic:
        screen = build_semantic_screen(has_page, rows)
        if not semantic_packs(screen):
            screen = build_raw_screen(has_page, rows)
    else:
        screen = build_raw_screen(has_page, rows)

    callouts = parse_callouts(fig_html, has_page)
    if callouts:
        screen["callouts"] = callouts

    return screen


def slug_from_context(before: str, index: int) -> str:
    for pat in (
        r'id="([^"]+)"[^>]*class="[^"]*algo',
        r'id="([^"]+)"[^>]*class="param-name',
        r'id="([^"]+)"[^>]*class="[^"]*page-name',
        r'<h[234][^>]*id="([^"]+)"',
    ):
        hits = re.findall(pat, before, re.I)
        if hits:
            return hits[-1][:48]
    return f"figure-{index:02d}"


def alt_from_screen(screen: dict) -> str:
    if "rows" in screen:
        text = " ".join(r.strip() for r in screen["rows"])
    else:
        bits = []
        if screen.get("pageHeader"):
            bits.append(screen["pageHeader"])
        for s in screen.get("buttonStrings") or []:
            bits.append(s.get("text", ""))
        if screen.get("pageFooter"):
            bits.append(screen["pageFooter"])
        text = "  ".join(bits)
    text = re.sub(r"\s+", " ", text).strip()
    return f"VFD: {text[:200]}"


def convert_file(html_path: Path, out_dir: Path, manifest: list[dict]) -> None:
    text = html_path.read_text()
    chapter = html_path.stem  # 08-programs
    folder = out_dir / chapter.replace("-", "-")  # images/displays/08-programs
    if chapter.startswith("09-program-params-a"):
        folder = out_dir / "09-program-params-a"
    elif chapter.startswith("08-"):
        folder = out_dir / "08-programs"

    pattern = re.compile(r"(<figure class=\"vfd-unit[^\"]*\">)([\s\S]*?)(</figure>)", re.I)
    index = 0
    parts: list[str] = []
    last = 0

    for m in pattern.finditer(text):
        fig_open, body, fig_close = m.group(1), m.group(2), m.group(3)
        if "images/displays" in body and "vfd-bezel" not in body:
            continue
        if "vfd-bezel" not in body:
            continue
        index += 1
        before = text[max(0, m.start() - 4000) : m.start()]
        slug = slug_from_context(before, index)
        safe = re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-") or f"figure-{index:02d}"
        filename = f"{index:02d}-{safe}.svg"
        filepath = folder / filename

        fig_html = fig_open + body + fig_close
        screen = figure_to_screen(fig_html)
        button_states = pressed_buttons(fig_html)
        has_page = "has-page" in fig_open

        manifest.append(
            {
                "file": str(filepath),
                "name": safe,
                "screen": screen,
                "buttonStates": button_states,
                **({"rowJustify": screen.get("rowJustify")} if screen.get("rowJustify") else {}),
            }
        )

        rel = filepath.relative_to(ROOT)
        alt = html.escape(alt_from_screen(screen), quote=True)
        cls = fig_open.replace("<figure ", "").replace(">", "").strip()
        replacement = f'<figure {cls}>\n      <img src="{rel.as_posix()}" alt="{alt}">\n    </figure>'
        parts.append(text[last:m.start()])
        parts.append(replacement)
        last = m.end()

    parts.append(text[last:])
    html_path.write_text("".join(parts))
    print(f"{html_path.name}: converted {index} figure(s) -> {folder.relative_to(ROOT)}")


def main() -> None:
    targets = sys.argv[1:] or ["08-programs.html", "09-program-params-a.html"]
    out_dir = ROOT / "images" / "displays"
    manifest: list[dict] = []
    for name in targets:
        path = ROOT / name
        if not path.exists():
            raise SystemExit(f"Missing {path}")
        convert_file(path, out_dir, manifest)
    manifest_path = ROOT / "displays-manifest" / "08-09a-programs.json"
    manifest_path.write_text(json.dumps({"outputs": manifest}, indent=2) + "\n")
    print(f"Wrote manifest {manifest_path} ({len(manifest)} outputs)")


if __name__ == "__main__":
    main()
