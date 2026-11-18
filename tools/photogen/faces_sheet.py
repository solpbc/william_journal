#!/usr/bin/env python3
"""Crop passing faces to 256-pixel squares and write the contact sheet.

install.json maps a person-entity slug to photos/faces/images/<slug>.jpg.
A face that failed vision review, or that is the later of a near-duplicate
pair, stays out of that map. The photogen source files keep their long names.
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

from PIL import Image

PHOTOGEN_DIR = Path(__file__).resolve().parent
PROJECT = PHOTOGEN_DIR.parents[1]


def _section_age(world_text: str) -> str:
    parts = [part.strip() for part in world_text.split(" · ")]
    if len(parts) >= 2:
        return parts[1]
    return ""


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def crop_square(src: Path, dest: Path, width: int = 256, quality: int = 92) -> None:
    with Image.open(src) as image:
        rgb = image.convert("RGB")
        side = min(rgb.size)
        left = (rgb.width - side) // 2
        top = (rgb.height - side) // 2
        square = rgb.crop((left, top, left + side, top + side))
        square = square.resize((width, width), Image.Resampling.LANCZOS)
        dest.parent.mkdir(parents=True, exist_ok=True)
        square.save(dest, format="JPEG", quality=quality, optimize=True)
    with Image.open(dest) as check:
        check.verify()
    with Image.open(dest) as check:
        if check.format != "JPEG" or check.width != width:
            raise ValueError(f"{dest.name} is not a {width}-pixel-wide JPEG")


def failing_slugs(review: dict[str, Any]) -> dict[str, str]:
    """slug -> reason. The later slug of a duplicate pair is the one left out."""
    reasons: dict[str, str] = {}
    for item in review.get("items") or []:
        if not item.get("failed"):
            continue
        flags = [name for name in (
            "lettering", "modern_object", "looking_at_lens", "wrong_age_or_sex",
            "aged_or_painted", "second_person",
        ) if item.get(name)]
        note = str(item.get("notes") or "")
        reason = ", ".join(flags) if flags else "review error"
        if note:
            reason = f"{reason}: {note}"
        reasons[str(item["shot_id"])] = reason
    pairs = ((review.get("duplicates") or {}).get("pairs") or [])
    order = {str(item["shot_id"]): int(item["number"]) for item in review.get("items") or []}
    for pair in pairs:
        a, b = str(pair["a"]), str(pair["b"])
        later = b if order.get(b, 0) >= order.get(a, 0) else a
        if later not in reasons:
            reasons[later] = f"near-duplicate of {a if later == b else b}: {pair.get('notes') or ''}".strip()
    return reasons


def render_sheet(cards: list[dict[str, str]], left_out: list[dict[str, str]], spend_line: str) -> str:
    parts = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>William journal, person faces</title>",
        "<style>",
        "body{margin:0;background:#161410;color:#f4efe6;font:16px/1.45 Georgia,serif}",
        "header,main{max-width:1200px;margin:0 auto;padding:24px 16px}",
        "h1{font-weight:500;font-size:28px;margin:0 0 8px}",
        "p.note{color:#c8bfb0;margin:0 0 8px}",
        "h2{font-weight:500;font-size:20px;margin:28px 0 12px}",
        ".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px}",
        "figure{margin:0;background:#221e19}",
        "img{width:100%;height:auto;display:block}",
        "figcaption{padding:8px 10px 12px}",
        ".name{font-size:16px}",
        ".meta{color:#d9c7a2;font-size:13px;margin-top:2px}",
        ".who{margin:6px 0 0;color:#f4efe6}",
        "</style>",
        "</head>",
        "<body>",
        "<header>",
        "<h1>Person faces, 1595</h1>",
        f"<p class='note'>{len(cards)} faces installed. {len(left_out)} left out.</p>",
        f"<p class='note'>{html.escape(spend_line)}</p>",
        "</header>",
        "<main>",
        "<div class='grid'>",
    ]
    for card in cards:
        parts.append("<figure>")
        parts.append(f'<img src="{html.escape(card["src"], quote=True)}" alt="{html.escape(card["name"], quote=True)}">')
        parts.append("<figcaption>")
        parts.append(f'<div class="name">{html.escape(card["name"])}</div>')
        parts.append(
            f'<div class="meta">{html.escape(card["slug"])} · § 3 age {html.escape(card["age"])}</div>'
        )
        parts.append(f'<p class="who">{html.escape(card["who"])}</p>')
        parts.append("</figcaption></figure>")
    parts.append("</div>")
    if left_out:
        parts.append("<h2>Left out</h2>")
        parts.append("<div class='grid'>")
        for card in left_out:
            parts.append("<figure>")
            if card.get("src"):
                parts.append(
                    f'<img src="{html.escape(card["src"], quote=True)}" alt="{html.escape(card["name"], quote=True)}">'
                )
            parts.append("<figcaption>")
            parts.append(f'<div class="name">{html.escape(card["name"])}</div>')
            parts.append(f'<div class="meta">{html.escape(card["slug"])}</div>')
            parts.append(f'<p class="who">{html.escape(card["why"])}</p>')
            parts.append("</figcaption></figure>")
        parts.append("</div>")
    parts.append("</main></body></html>\n")
    return "\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Crop passing faces and write install.json.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--prompts", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--faces-dir", type=Path, default=PROJECT / "photos" / "faces")
    parser.add_argument("--spend-line", default="")
    args = parser.parse_args(argv)

    manifest = _load(args.manifest)
    shots = {str(shot["id"]): shot for shot in _load(args.prompts).get("shots") or []}
    review = _load(args.review)
    reasons = failing_slugs(review)
    images = args.faces_dir / "images"
    by_entity: dict[str, str] = {}
    cards: list[dict[str, str]] = []
    left_out: list[dict[str, str]] = []

    for item in sorted(manifest.get("items") or [], key=lambda row: int(row["number"])):
        slug = str(item["shot_id"])
        shot = shots[slug]
        name = str(shot.get("title") or slug)
        if slug in reasons:
            left_out.append({
                "slug": slug,
                "name": name,
                "src": str(item.get("image_rel_path") or ""),
                "why": reasons[slug],
            })
            continue
        src = args.faces_dir / str(item["image_rel_path"])
        dest = images / f"{slug}.jpg"
        crop_square(src, dest)
        rel = f"photos/faces/images/{slug}.jpg"
        by_entity[slug] = rel
        cards.append({
            "src": f"images/{slug}.jpg",
            "name": name,
            "slug": slug,
            "age": _section_age(str(shot.get("world_text") or "")),
            "who": str(shot.get("face_who") or ""),
        })

    install_path = args.faces_dir / "install.json"
    install_path.write_text(
        json.dumps({"by_entity": by_entity}, indent=2) + "\n",
        encoding="utf-8",
    )
    sheet = render_sheet(cards, left_out, args.spend_line)
    (args.faces_dir / "index.html").write_text(sheet, encoding="utf-8")
    print(f"installed={len(by_entity)} left_out={len(left_out)}")
    for row in left_out:
        print(f"left out {row['slug']}: {row['why']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
