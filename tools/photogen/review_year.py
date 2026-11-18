#!/usr/bin/env python3
"""Vision-check every Framing C year photo against its caption.

One Gemini call per image. The key is loaded the same way as photogen
(GEMINI_API_KEY or WILLIAM_GEMINI_KEY_FILE), and it is never printed. Results land in a JSON file
so a stopped run can resume. A true flag means that check failed.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

PHOTOGEN_DIR = Path(__file__).resolve().parent
if str(PHOTOGEN_DIR) not in sys.path:
    sys.path.insert(0, str(PHOTOGEN_DIR))

import photogen  # noqa: E402

CHECKS = (
    "lettering",
    "uncalled_hand",
    "modern_object",
    "forbidden_face",
    "aged_or_painted",
    "wrong_subject",
)

# Conservative token prices so a vision pass cannot quietly walk past the
# image budget. Real flash prices are lower than this ceiling.
VISION_INPUT_PER_1M = 5.0
VISION_OUTPUT_PER_1M = 20.0


def list_models(api_key: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    page_token = ""
    while True:
        url = "https://generativelanguage.googleapis.com/v1beta/models?pageSize=100"
        if page_token:
            url += f"&pageToken={page_token}"
        req = urllib.request.Request(url, headers={"x-goog-api-key": api_key})
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        found.extend(payload.get("models") or [])
        page_token = payload.get("nextPageToken") or ""
        if not page_token:
            return found


def choose_flash_model(models: list[dict[str, Any]]) -> str:
    """A stable flash model that can take an image and return text. Not an image generator."""
    skip = ("imagen", "nano-banana", "embedding", "tts", "aqa", "live", "robotics", "image")
    candidates: list[str] = []
    for model in models:
        name = str(model.get("name") or "")
        methods = model.get("supportedGenerationMethods") or []
        if "generateContent" not in methods:
            continue
        low = name.lower()
        if "flash" not in low:
            continue
        if any(token in low for token in skip):
            continue
        if any(token in low for token in ("preview", "exp", "experimental", "lite")):
            continue
        candidates.append(name)
    if not candidates:
        raise photogen.PhotogenError("No stable Gemini flash model available for vision review.")

    def sort_key(name: str) -> tuple[float, ...]:
        nums = [float(part) for part in re.findall(r"\d+(?:\.\d+)?", name)]
        return tuple(nums or [0.0])

    candidates.sort(key=sort_key)
    return candidates[-1]


def _review_prompt(caption: str, title: str) -> str:
    return (
        "Check this photograph against the caption and the failure list. "
        "Reply with one JSON object and no other text. "
        "Each field is true only when the image fails that check.\n"
        '{"lettering":false,"uncalled_hand":false,"modern_object":false,'
        '"forbidden_face":false,"aged_or_painted":false,"wrong_subject":false,"notes":""}\n'
        "lettering: readable English words, shop signs, banners, play titles, or a printed title. "
        "Illegible ink, smudged black-letter, and scribbles that are not English words are not lettering.\n"
        "uncalled_hand: a hand is visible even though the caption does not put that hand in the picture. "
        "A hand the caption names is not a failure.\n"
        "modern_object: an object that did not exist in England in 1595, including glass street lamps, "
        "cast-iron downpipes, a modern skyline, plastic, electric light, a wristwatch, or a printed tattoo.\n"
        "forbidden_face: a face looking into the lens, the photographer's face or reflection, "
        "or a face the caption says not to show. A person seen from behind, face turned away, is allowed.\n"
        "aged_or_painted: sepia, an antique filter, film grain, a vignette, or a painting rather than a photograph.\n"
        "wrong_subject: the scene is a different subject from the caption.\n"
        f"Title: {title}\nCaption:\n{caption}"
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


def review_one(
    api_key: str,
    model: str,
    image_path: Path,
    caption: str,
    title: str,
) -> dict[str, Any]:
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    body = {
        "contents": [
            {
                "parts": [
                    {"text": _review_prompt(caption, title)},
                    {"inlineData": {"mimeType": "image/jpeg", "data": encoded}},
                ]
            }
        ],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        err = photogen.redact_secret(exc.read().decode("utf-8", errors="replace"), api_key)
        # Some models reject responseMimeType. Retry once without it.
        if exc.code == 400 and "responseMimeType" in body["generationConfig"]:
            body["generationConfig"].pop("responseMimeType")
            req = urllib.request.Request(
                url,
                data=json.dumps(body).encode("utf-8"),
                headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        else:
            raise photogen.PhotogenError(f"Vision HTTP {exc.code}: {err[:500]}") from None
    text = ""
    for cand in data.get("candidates") or []:
        for part in (cand.get("content") or {}).get("parts") or []:
            if part.get("text"):
                text += part["text"]
    usage = data.get("usageMetadata") or {}
    prompt_tokens = int(usage.get("promptTokenCount") or 0)
    output_tokens = int(usage.get("candidatesTokenCount") or 0)
    cost = (prompt_tokens * VISION_INPUT_PER_1M + output_tokens * VISION_OUTPUT_PER_1M) / 1_000_000
    verdict = _parse_verdict(text)
    verdict["prompt_tokens"] = prompt_tokens
    verdict["output_tokens"] = output_tokens
    verdict["cost_usd_ceiling"] = round(cost, 6)
    return verdict


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Vision-check Framing C year photos.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--spent-usd", type=float, default=0.0, help="Image-generation dollars already spent.")
    parser.add_argument("--budget-usd", type=float, default=30.0)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args(argv)

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    prior: dict[str, Any] = {}
    if args.out.is_file():
        prior = json.loads(args.out.read_text(encoding="utf-8"))
    done = {item["number"]: item for item in prior.get("items") or []}
    api_key = photogen.load_api_key()
    model = prior.get("model") or choose_flash_model(list_models(api_key))
    print(f"vision model: {model}", flush=True)

    pending = []
    for item in manifest.get("items") or []:
        if int(item["number"]) in done:
            continue
        image = args.manifest.parent / item["image_rel_path"]
        seg = item.get("source_segment") or {}
        pending.append((item, image, seg.get("photo_text") or item.get("subject_prompt") or "", seg.get("title") or ""))

    spent = float(args.spent_usd) + sum(float(item.get("cost_usd_ceiling") or 0) for item in done.values())

    def _save() -> None:
        items = [done[n] for n in sorted(done)]
        body = {
            "model": model,
            "pricing_ceiling_per_1m_usd": {
                "input": VISION_INPUT_PER_1M,
                "output": VISION_OUTPUT_PER_1M,
            },
            "items": items,
            "reviewed": len(items),
            "failed": sum(1 for item in items if item.get("failed")),
            "vision_cost_ceiling_usd": round(sum(float(item.get("cost_usd_ceiling") or 0) for item in items), 6),
        }
        args.out.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")

    if pending:
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            futures = {
                pool.submit(review_one, api_key, model, image, caption, title): item
                for item, image, caption, title in pending
            }
            for fut in as_completed(futures):
                item = futures[fut]
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
                    "code": item.get("code"),
                    "image_rel_path": item.get("image_rel_path"),
                    "title": (item.get("source_segment") or {}).get("title"),
                    "date": (item.get("source_segment") or {}).get("date"),
                    **verdict,
                }
                done[int(item["number"])] = record
                _save()
                mark = "FAIL" if verdict["failed"] else "ok"
                print(
                    f"[{len(done):03d}] #{item['number']:03d} {mark} ceiling=${spent:.4f} {record['title']}",
                    flush=True,
                )
                if spent > args.budget_usd:
                    pool.shutdown(wait=False, cancel_futures=True)
                    print(
                        f"STOP vision: ceiling ${spent:.2f} would pass ${args.budget_usd:.2f}",
                        flush=True,
                    )
                    return 2
    else:
        _save()
    failed = sum(1 for item in done.values() if item.get("failed"))
    print(f"reviewed={len(done)} failed={failed} vision_ceiling=${sum(float(i.get('cost_usd_ceiling') or 0) for i in done.values()):.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
