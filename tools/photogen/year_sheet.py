#!/usr/bin/env python3
"""Contact sheet and journal install for the Framing C year photos.

The sheet is a static HTML page grouped by date. Image paths are relative
`images/*.jpg` files beside the page. install.json maps each photo segment to
the committed JPEG so a fresh convert can copy it back in.
"""

from __future__ import annotations

import argparse
import html
import json
import shutil
from collections import OrderedDict
from pathlib import Path
from typing import Any

PHOTOGEN_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PHOTOGEN_DIR.parents[1]


def _items(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(manifest.get("items") or [], key=lambda item: int(item["number"]))


def write_install_map(manifest: dict[str, Any], dest: Path, photos_rel: str = "photos/year") -> dict[str, str]:
    by_segment: dict[str, str] = {}
    for item in _items(manifest):
        seg = item.get("source_segment") or {}
        day = seg.get("date") or ""
        key = seg.get("segment_key") or ""
        if not day or not key:
            continue
        rel = item.get("image_rel_path") or ""
        by_segment[f"{day}/{key}"] = f"{photos_rel}/{rel}"
    dest.write_text(
        json.dumps({"by_segment": by_segment}, indent=2) + "\n",
        encoding="utf-8",
    )
    return by_segment


def install_into_journal(manifest: dict[str, Any], photos_dir: Path, journal_dir: Path) -> int:
    """Copy each downscaled JPEG over the journal placeholder. Returns how many were copied."""
    copied = 0
    for item in _items(manifest):
        seg = item.get("source_segment") or {}
        rel = seg.get("journal_rel") or ""
        image_rel = item.get("image_rel_path") or ""
        if not rel or not image_rel:
            raise SystemExit(f"manifest item {item.get('number')} is missing journal_rel or image_rel_path")
        src = photos_dir / image_rel
        dest = journal_dir / rel / "original.jpg"
        if not src.is_file():
            raise SystemExit(f"missing generated image {src}")
        if not dest.parent.is_dir():
            raise SystemExit(f"missing journal segment dir {dest.parent}")
        shutil.copyfile(src, dest)
        copied += 1
    return copied


def render_contact_sheet(manifest: dict[str, Any]) -> str:
    groups: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for item in _items(manifest):
        seg = item.get("source_segment") or {}
        groups.setdefault(str(seg.get("date") or ""), []).append(item)
    parts = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>William journal, Framing C</title>",
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
        "figcaption p{margin:6px 0 0;white-space:pre-wrap}",
        "</style>",
        "</head>",
        "<body>",
        "<header>",
        "<h1>William journal, 1595. Framing C.</h1>",
        f"<p class='note'>{len(_items(manifest))} photographs, one for each photo segment, in the order of the year.</p>",
        "</header>",
        "<main>",
    ]
    for day, items in groups.items():
        parts.append(f"<h2>{html.escape(day)}</h2>")
        for item in items:
            seg = item.get("source_segment") or {}
            number = int(item["number"])
            title = str(seg.get("title") or "")
            when = str(seg.get("time") or "")
            caption = str(seg.get("photo_text") or "")
            src = html.escape(str(item.get("image_rel_path") or ""), quote=True)
            parts.append("<figure>")
            parts.append(f'<img src="{src}" alt="{html.escape(title, quote=True)}">')
            parts.append("<figcaption>")
            parts.append(
                f'<div class="meta">{number}. {html.escape(day)} {html.escape(when)} — {html.escape(title)}</div>'
            )
            parts.append(f"<p>{html.escape(caption)}</p>")
            parts.append("</figcaption></figure>")
    parts.append("</main></body></html>\n")
    return "\n".join(parts)


def write_contact_sheet(manifest: dict[str, Any], dest: Path) -> None:
    dest.write_text(render_contact_sheet(manifest), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write the year contact sheet and install map.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--html", type=Path, required=True)
    parser.add_argument("--install", type=Path, required=True)
    parser.add_argument("--journal", type=Path, default=None)
    args = parser.parse_args(argv)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    write_contact_sheet(manifest, args.html)
    mapped = write_install_map(manifest, args.install)
    print(f"sheet {args.html}")
    print(f"install {args.install} segments={len(mapped)}")
    if args.journal is not None:
        copied = install_into_journal(manifest, args.manifest.parent, args.journal)
        print(f"copied {copied} into {args.journal}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
