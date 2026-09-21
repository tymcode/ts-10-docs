#!/usr/bin/env python3
"""Rebuild screen JSON in displays-manifest/08-09a-programs.json from print.html bezels."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from convert_bezel_figures import figure_to_screen, pressed_buttons, alt_from_screen  # noqa: E402

FIGURE_RE = re.compile(
    r'(<figure class="vfd-unit[^"]*">[\s\S]*?vfd-bezel[\s\S]*?</figure>)',
    re.I,
)


def section_figures(print_html: str, start_id: str, end_id: str) -> list[str]:
    chunk = print_html.split(f'id="{start_id}"', 1)[1].split(f'id="{end_id}"', 1)[0]
    return FIGURE_RE.findall(chunk)


def main() -> None:
    manifest_path = ROOT / "displays-manifest" / "08-09a-programs.json"
    manifest = json.loads(manifest_path.read_text())
    print_html = (ROOT / "print.html").read_text()
    figures = section_figures(
        print_html,
        "section-8-understanding-programs",
        "section-9-program-parameters-lfo-envelopes-pitch-filters",
    ) + section_figures(
        print_html,
        "section-9-program-parameters-lfo-envelopes-pitch-filters",
        "section-9-program-parameters-wave-hyper-wave-editors",
    )
    if len(figures) != len(manifest["outputs"]):
        raise SystemExit(f"Figure count {len(figures)} != manifest {len(manifest['outputs'])}")
    for fig, entry in zip(figures, manifest["outputs"]):
        screen = figure_to_screen(fig)
        entry["screen"] = screen
        entry["buttonStates"] = pressed_buttons(fig)
        if screen.get("rowJustify"):
            entry["rowJustify"] = screen["rowJustify"]
        elif "rowJustify" in entry:
            del entry["rowJustify"]
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Updated {len(figures)} manifest entries from print.html")


if __name__ == "__main__":
    main()
