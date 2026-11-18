#!/usr/bin/env python3
"""Contact sheet and install map for the packed-day desk frames.

install.json matches photos/year/install.json: by_segment, keyed
`<day>/<segment_key>`, paths relative to the william-journal project root.
A frame that failed vision review twice is left out. Nothing is copied into
the journal build.
"""

from __future__ import annotations

import argparse
import html
import json
from collections import OrderedDict
from pathlib import Path
from typing import Any

PHOTOGEN_DIR = Path(__file__).resolve().parent
import sys

if str(PHOTOGEN_DIR) not in sys.path:
    sys.path.insert(0, str(PHOTOGEN_DIR))

import year_sheet  # noqa: E402

PROMPTS = PHOTOGEN_DIR / "prompts_pages.json"


def _current_titles() -> dict[str, str]:
    """Segment headings as the day files read now.

    A later plain-words pass renamed the headings after the first images
    were made. The manifest keeps the heading from generation time. The
    sheet shows the current one.
    """
    if not PROMPTS.is_file():
        return {}
    data = json.loads(PROMPTS.read_text(encoding="utf-8"))
    titles: dict[str, str] = {}
    for shot in data.get("shots") or []:
        titles[f"{shot.get('date')}/{shot.get('segment_key')}"] = str(shot.get("title") or "")
    return titles


def _passed_items(manifest: dict[str, Any], review_path: Path | None) -> list[dict[str, Any]]:
    failed: set[int] = set()
    if review_path is not None and review_path.is_file():
        review = json.loads(review_path.read_text(encoding="utf-8"))
        for item in review.get("items") or []:
            if item.get("failed"):
                failed.add(int(item["number"]))
    kept = []
    for item in year_sheet._items(manifest):
        if int(item["number"]) in failed:
            continue
        kept.append(item)
    return kept


def render_contact_sheet(items: list[dict[str, Any]]) -> str:
    titles = _current_titles()
    groups: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for item in items:
        seg = item.get("source_segment") or {}
        groups.setdefault(str(seg.get("date") or ""), []).append(item)
    parts = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>William journal, desk frames</title>",
        "<style>",
        "body{margin:0;background:#161410;color:#f4efe6;font:16px/1.45 Georgia,serif}",
        "header,main{max-width:1100px;margin:0 auto;padding:24px 16px}",
        "h1{font-weight:500;font-size:28px;margin:0 0 8px}",
        "p.note{color:#c8bfb0;margin:0}",
        "h2{font-weight:500;font-size:20px;margin:32px 0 12px;border-bottom:1px solid #3a342c;padding-bottom:6px}",
        "figure{margin:0 0 28px;background:#221e19}",
        "img{width:100%;height:auto;display:block}",
        "figcaption{padding:10px 12px 14px}",
        ".meta{color:#d9c7a2;font-size:14px;letter-spacing:.02em}",
        "figcaption p{margin:6px 0 0}",
        "</style>",
        "</head>",
        "<body>",
        "<header>",
        "<h1>William journal, 1595. The packed days, desk frames.</h1>",
        f"<p class='note'>{len(items)} pages that passed review, grouped by day. A frame that failed twice is not on this sheet.</p>",
        "</header>",
        "<main>",
    ]
    for day, group in groups.items():
        parts.append(f"<h2>{html.escape(day)}</h2>")
        for item in group:
            seg = item.get("source_segment") or {}
            number = int(item["number"])
            key = f"{seg.get('date')}/{seg.get('segment_key')}"
            title = titles.get(key) or str(seg.get("title") or "")
            when = str(seg.get("time") or "")
            src = html.escape(str(item.get("image_rel_path") or ""), quote=True)
            parts.append("<figure>")
            parts.append(f'<img src="{src}" alt="{html.escape(title, quote=True)}">')
            parts.append("<figcaption>")
            parts.append(
                f'<div class="meta">{number}. {html.escape(day)} {html.escape(when)} — {html.escape(title)}</div>'
            )
            parts.append("</figcaption></figure>")
    parts.append("</main></body></html>\n")
    return "\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write the desk-frame contact sheet and install map.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--html", type=Path, required=True)
    parser.add_argument("--install", type=Path, required=True)
    parser.add_argument("--review", type=Path, default=None)
    parser.add_argument("--photos-rel", default="photos/pages")
    args = parser.parse_args(argv)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    items = _passed_items(manifest, args.review)
    thinned = dict(manifest)
    thinned["items"] = items
    args.html.write_text(render_contact_sheet(items), encoding="utf-8")
    mapped = year_sheet.write_install_map(thinned, args.install, photos_rel=args.photos_rel)
    print(f"sheet {args.html} images={len(items)}")
    print(f"install {args.install} segments={len(mapped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
