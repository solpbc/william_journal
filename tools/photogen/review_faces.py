#!/usr/bin/env python3
"""Vision-check person faces against § 3 and against the rest of the set.

One Gemini call per face, then one call on a labeled contact grid for
near-duplicates. The key is loaded the same way as photogen (GEMINI_API_KEY
or WILLIAM_GEMINI_KEY_FILE), and it is never printed. Results land in a JSON file so a
stopped run can resume. A true flag means that check failed.

This does not edit review_year.py. That script checks a photo against its
segment. A face is checked against the person's sex, age and look.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

PHOTOGEN_DIR = Path(__file__).resolve().parent
if str(PHOTOGEN_DIR) not in sys.path:
    sys.path.insert(0, str(PHOTOGEN_DIR))

import photogen  # noqa: E402
import review_year  # noqa: E402

CHECKS = (
    "lettering",
    "modern_object",
    "looking_at_lens",
    "wrong_age_or_sex",
    "aged_or_painted",
    "second_person",
)

# Resemblance inside a group is allowed. A face that could be swapped for
# another person, including inside a group, is still a near-duplicate.
KIN_GROUPS = (
    "Henley Street household: anne_shakespeare, bartholomew_hathaway, edmund_shakespeare, gilbert_shakespeare, hamnet_shakespeare, joan_shakespeare, john_shakespeare, judith_shakespeare, mary_shakespeare, richard_shakespeare, susanna_shakespeare",
    "Burbage: james_burbage (64), richard_burbage (27), cuthbert_burbage (30, clean-shaven)",
    "Shakespeare twins of ten: hamnet_shakespeare is a boy, judith_shakespeare is a girl",
    "Sadler: hamnet_sadler, judith_sadler",
    "Field: richard_field, jacqueline_field",
    "Hoby: edward_hoby, margaret_hoby",
)


def _review_prompt(name: str, sex: str, age: int, who: str, subject: str) -> str:
    return (
        "Check this one photograph of a person in England in 1595. "
        "Reply with one JSON object and no other text. "
        "Each field is true only when the image clearly fails that check. "
        "A doubt is false.\n"
        '{"lettering":false,"modern_object":false,"looking_at_lens":false,'
        '"wrong_age_or_sex":false,"aged_or_painted":false,"second_person":false,"notes":""}\n'
        "lettering: readable words, shop signs, banners, titles, or a printed title. "
        "Illegible ink and smudged marks are not lettering.\n"
        "modern_object: glasses, a zip, a modern haircut, modern makeup, plastic, "
        "electric light, a wristwatch, or any object that did not exist in England in 1595.\n"
        "looking_at_lens: the eyes meet the camera. A three-quarter or profile face "
        "whose gaze is on work or on someone outside the frame is not a failure.\n"
        "wrong_age_or_sex: the person is clearly the wrong sex, or clearly the wrong "
        "life-stage for the age given (a child of ten shown as an adult, a man of sixty "
        "shown as about thirty, a girl shown as a boy). A few years either way is not a failure.\n"
        "aged_or_painted: sepia, an antique filter, a vignette used as a style, or a painting. "
        "A colour photograph with warm candlelight is not sepia.\n"
        "second_person: a second person's face is clearly visible. A blurred shoulder, "
        "or a figure whose face is not shown, is not a second person.\n"
        f"Name: {name}\nSex: {sex}\nAge in 1595: {age}\nWho they are: {who}\n"
        f"What was asked:\n{subject}"
    )


def _parse_verdict(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("no JSON object in vision response")
    payload = json.loads(match.group(0))
    verdict = {name: bool(payload.get(name)) for name in CHECKS}
    verdict["notes"] = str(payload.get("notes") or "")[:400]
    verdict["failed"] = any(verdict[name] for name in CHECKS)
    return verdict


def _post_json(api_key: str, model: str, parts: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    body: dict[str, Any] = {
        "contents": [{"parts": parts}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent"
    last_error = ""
    for attempt in range(4):
        data_bytes = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            err = photogen.redact_secret(exc.read().decode("utf-8", errors="replace"), api_key)
            last_error = f"Vision HTTP {exc.code}: {err[:500]}"
            if exc.code == 400 and "responseMimeType" in body.get("generationConfig", {}):
                body["generationConfig"].pop("responseMimeType", None)
                continue
            if exc.code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(2 * (attempt + 1))
                continue
            raise photogen.PhotogenError(last_error) from None
        except urllib.error.URLError as exc:
            last_error = photogen.redact_secret(str(exc), api_key)
            if attempt < 3:
                time.sleep(2 * (attempt + 1))
                continue
            raise photogen.PhotogenError(f"Vision request failed: {last_error[:500]}") from None
    else:
        raise photogen.PhotogenError(last_error or "Vision request failed")

    text = ""
    for cand in data.get("candidates") or []:
        for part in (cand.get("content") or {}).get("parts") or []:
            if part.get("text"):
                text += part["text"]
    usage = data.get("usageMetadata") or {}
    return text, usage


def _cost(usage: dict[str, Any]) -> tuple[int, int, float]:
    prompt_tokens = int(usage.get("promptTokenCount") or 0)
    output_tokens = int(usage.get("candidatesTokenCount") or 0)
    cost = (
        prompt_tokens * review_year.VISION_INPUT_PER_1M
        + output_tokens * review_year.VISION_OUTPUT_PER_1M
    ) / 1_000_000
    return prompt_tokens, output_tokens, round(cost, 6)


def review_one(
    api_key: str,
    model: str,
    image_path: Path,
    name: str,
    sex: str,
    age: int,
    who: str,
    subject: str,
) -> dict[str, Any]:
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    text, usage = _post_json(
        api_key,
        model,
        [
            {"text": _review_prompt(name, sex, age, who, subject)},
            {"inlineData": {"mimeType": "image/jpeg", "data": encoded}},
        ],
    )
    prompt_tokens, output_tokens, cost = _cost(usage)
    verdict = _parse_verdict(text)
    verdict["prompt_tokens"] = prompt_tokens
    verdict["output_tokens"] = output_tokens
    verdict["cost_usd_ceiling"] = cost
    return verdict


def _font(size: int) -> ImageFont.ImageFont:
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ):
        if Path(path).is_file():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def build_montage(entries: list[dict[str, Any]], dest: Path, cols: int = 8) -> None:
    """One labeled grid. entries need slug and image_path."""
    thumb = 180
    label_h = 28
    rows = (len(entries) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb, rows * (thumb + label_h)), (22, 20, 16))
    draw = ImageDraw.Draw(sheet)
    font = _font(11)
    for index, entry in enumerate(entries):
        col = index % cols
        row = index // cols
        x = col * thumb
        y = row * (thumb + label_h)
        with Image.open(entry["image_path"]) as im:
            tile = im.convert("RGB")
            side = min(tile.size)
            left = (tile.width - side) // 2
            top = (tile.height - side) // 2
            tile = tile.crop((left, top, left + side, top + side))
            tile = tile.resize((thumb, thumb), Image.Resampling.LANCZOS)
        sheet.paste(tile, (x, y))
        draw.text((x + 3, y + thumb + 4), entry["slug"][:22], fill=(244, 239, 230), font=font)
    dest.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(dest, format="JPEG", quality=85, optimize=True)


def _duplicate_prompt(entries: list[dict[str, Any]]) -> str:
    lines = [
        "These photographs are supposed to be different people in 1595. "
        "Reply with one JSON object and no other text.\n"
        '{"pairs":[{"a":"slug","b":"slug","notes":""}]}\n'
        "List a pair only when the two faces could be the same person: the same face reused. "
        "Family resemblance is allowed inside a kin group when the two still read as different people "
        "(different age, beard, or sex). An empty pairs list is the right answer when nobody is reused.\n"
        "Kin groups:",
        *KIN_GROUPS,
        "People, in grid order, left to right, top to bottom:",
    ]
    for entry in entries:
        lines.append(f"- {entry['slug']}: {entry['sex']} of {entry['age']}, {entry['who']}")
    return "\n".join(lines)


def review_duplicates(
    api_key: str,
    model: str,
    entries: list[dict[str, Any]],
    montage_path: Path,
) -> dict[str, Any]:
    build_montage(entries, montage_path)
    encoded = base64.b64encode(montage_path.read_bytes()).decode("ascii")
    text, usage = _post_json(
        api_key,
        model,
        [
            {"text": _duplicate_prompt(entries)},
            {"inlineData": {"mimeType": "image/jpeg", "data": encoded}},
        ],
    )
    prompt_tokens, output_tokens, cost = _cost(usage)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("no JSON object in duplicate response")
    payload = json.loads(match.group(0))
    known = {entry["slug"] for entry in entries}
    pairs = []
    for pair in payload.get("pairs") or []:
        a = str(pair.get("a") or "")
        b = str(pair.get("b") or "")
        if a in known and b in known and a != b:
            pairs.append({"a": a, "b": b, "notes": str(pair.get("notes") or "")[:300]})
    return {
        "pairs": pairs,
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "cost_usd_ceiling": cost,
        "montage": str(montage_path),
    }


def _shots_by_id(prompts: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(shot["id"]): shot for shot in prompts.get("shots") or []}


def _body(model: str, done: dict[int, dict[str, Any]], duplicates: dict[str, Any] | None) -> dict[str, Any]:
    items = [done[n] for n in sorted(done)]
    return {
        "model": model,
        "pricing_ceiling_per_1m_usd": {
            "input": review_year.VISION_INPUT_PER_1M,
            "output": review_year.VISION_OUTPUT_PER_1M,
        },
        "items": items,
        "reviewed": len(items),
        "failed": sum(1 for item in items if item.get("failed")),
        "duplicates": duplicates,
        "vision_cost_ceiling_usd": round(
            sum(float(item.get("cost_usd_ceiling") or 0) for item in items)
            + float((duplicates or {}).get("cost_usd_ceiling") or 0),
            6,
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Vision-check william journal person faces.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--prompts", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--montage", type=Path, default=Path("/tmp/william-face-montage.jpg"))
    parser.add_argument("--spent-usd", type=float, default=0.0, help="Dollars already spent on this job.")
    parser.add_argument("--budget-usd", type=float, default=8.0, help="Whole-job cap, including --spent-usd.")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--skip-duplicates", action="store_true")
    args = parser.parse_args(argv)

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    shots = _shots_by_id(json.loads(args.prompts.read_text(encoding="utf-8")))
    prior: dict[str, Any] = {}
    if args.out.is_file():
        prior = json.loads(args.out.read_text(encoding="utf-8"))
    done = {int(item["number"]): item for item in prior.get("items") or []}
    api_key = photogen.load_api_key()
    model = prior.get("model") or review_year.choose_flash_model(review_year.list_models(api_key))
    print(f"vision model: {model}", flush=True)

    pending = []
    for item in manifest.get("items") or []:
        if int(item["number"]) in done:
            continue
        shot = shots.get(str(item.get("shot_id") or ""))
        if shot is None:
            raise photogen.PhotogenError(f"No prompt for shot {item.get('shot_id')}")
        image = args.manifest.parent / item["image_rel_path"]
        pending.append((item, image, shot))

    duplicates = prior.get("duplicates")
    spent = float(args.spent_usd) + sum(float(item.get("cost_usd_ceiling") or 0) for item in done.values())
    if duplicates:
        spent += float(duplicates.get("cost_usd_ceiling") or 0)

    def _save() -> None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(_body(model, done, duplicates), indent=2) + "\n",
            encoding="utf-8",
        )

    if pending:
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            futures = {
                pool.submit(
                    review_one,
                    api_key,
                    model,
                    image,
                    str(shot.get("title") or shot["id"]),
                    str(shot.get("face_sex") or ""),
                    int(shot.get("face_age") or 0),
                    str(shot.get("face_who") or ""),
                    str(shot.get("subject_prompt") or ""),
                ): (item, shot)
                for item, image, shot in pending
            }
            for fut in as_completed(futures):
                item, shot = futures[fut]
                try:
                    verdict = fut.result()
                except Exception as exc:
                    safe = photogen.redact_secret(str(exc), api_key)[:400]
                    verdict = {name: False for name in CHECKS}
                    verdict.update(
                        {
                            "notes": f"review error: {safe}",
                            "failed": True,
                            "prompt_tokens": 0,
                            "output_tokens": 0,
                            "cost_usd_ceiling": 0.0,
                        }
                    )
                spent += float(verdict["cost_usd_ceiling"])
                record = {
                    "number": item["number"],
                    "shot_id": item.get("shot_id"),
                    "code": item.get("code"),
                    "image_rel_path": item.get("image_rel_path"),
                    "name": shot.get("title"),
                    "sex": shot.get("face_sex"),
                    "age": shot.get("face_age"),
                    **verdict,
                }
                done[int(item["number"])] = record
                _save()
                mark = "FAIL" if verdict["failed"] else "ok"
                print(
                    f"[{len(done):03d}] #{item['number']:03d} {mark} ceiling=${spent:.4f} {record['shot_id']}",
                    flush=True,
                )
                if spent > args.budget_usd:
                    pool.shutdown(wait=False, cancel_futures=True)
                    print(f"STOP vision: ceiling ${spent:.2f} would pass ${args.budget_usd:.2f}", flush=True)
                    return 2
    else:
        _save()

    if not args.skip_duplicates and duplicates is None and len(done) == len(manifest.get("items") or []):
        entries = []
        for item in sorted(manifest.get("items") or [], key=lambda row: int(row["number"])):
            shot = shots[str(item["shot_id"])]
            record = done[int(item["number"])]
            if record.get("failed"):
                continue
            entries.append(
                {
                    "slug": str(item["shot_id"]),
                    "sex": str(shot.get("face_sex") or ""),
                    "age": int(shot.get("face_age") or 0),
                    "who": str(shot.get("face_who") or ""),
                    "image_path": args.manifest.parent / item["image_rel_path"],
                }
            )
        try:
            duplicates = review_duplicates(api_key, model, entries, args.montage)
        except Exception as exc:
            safe = photogen.redact_secret(str(exc), api_key)[:400]
            print(f"duplicate pass error: {safe}", flush=True)
            return 1
        spent += float(duplicates["cost_usd_ceiling"])
        _save()
        print(
            f"duplicates={len(duplicates['pairs'])} ceiling=${spent:.4f}",
            flush=True,
        )
        if spent > args.budget_usd:
            print(f"STOP vision: ceiling ${spent:.2f} would pass ${args.budget_usd:.2f}", flush=True)
            return 2

    failed = sum(1 for item in done.values() if item.get("failed"))
    print(
        f"reviewed={len(done)} failed={failed} "
        f"vision_ceiling=${sum(float(i.get('cost_usd_ceiling') or 0) for i in done.values()):.4f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
