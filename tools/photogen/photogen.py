#!/usr/bin/env python3
"""Photo generation tool for the william journal (tools/photogen/).

Reads a prompt set JSON, calls the latest Google Gemini image generation model
(`gemini-nano-banana-2.1`) via the Gemini REST API (`v1beta/models/...:generateContent`)
using the Gemini API key from `GEMINI_API_KEY`, or from a key file named by
`--key-file` or `WILLIAM_GEMINI_KEY_FILE`,
writes generated images + `manifest.json` + a static side-by-side HTML review page
(`index.html`). Never prints, logs, or commits the API key.
"""

from __future__ import annotations

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import html
import io
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
from typing import Any
import urllib.error
import urllib.request

try:
    from PIL import Image
except ModuleNotFoundError:
    if "/usr/lib/python3/dist-packages" not in sys.path:
        sys.path.append("/usr/lib/python3/dist-packages")
    from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROMPT_SET_PATH = Path(__file__).resolve().parent / "prompts_sample_round.json"
DEFAULT_MODEL = "gemini-nano-banana-2.1"
API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

# Published Paid-Tier pricing for gemini-nano-banana-2.1 (checked 2026-11-17 at
# https://ai.google.dev/gemini-api/docs/pricing.md.txt):
# - Input price: $1.50 per 1M tokens (text/image/video)
# - Output price (text and thinking): $7.50 per 1M tokens
# - Output price (images): $30.00 per 1M tokens (1,120 tokens per 1K image = $0.0336)
PRICING_PER_1M_USD = {
    "input_usd": 1.50,
    "image_output_usd": 30.00,
    "text_thinking_output_usd": 7.50,
}

MODEL_VERIFICATION = {
    "model_id": DEFAULT_MODEL,
    "display_name": "Nano Banana 2.1 (Gemini Nano Banana 2.1)",
    "checked_date": "2026-11-17",
    "how_checked": (
        "Verified on 2026-11-17 against (1) Google's official Gemini API documentation at "
        "https://ai.google.dev/gemini-api/docs/image-generation.md.txt, "
        "https://ai.google.dev/gemini-api/docs/models/gemini-nano-banana-2.1.md.txt "
        "(latest update October 2026; primary recommended image generation model, superseding "
        "gemini-3.1-flash-image [Feb 2026], gemini-3.1-flash-lite-image [Jun 2026], "
        "gemini-3-pro-image [Nov 2025], deprecated gemini-2.5-flash-image, and shut-down Imagen endpoints), "
        "and (2) live GET https://generativelanguage.googleapis.com/v1beta/models with the agy-hub-sessions key."
    ),
}


class PhotogenError(RuntimeError):
    """Raised when key loading, budget enforcement, or API generation fails."""


def load_api_key(key_file: Path | None = None) -> str:
    """Read the Gemini API key at runtime.

    Order: an explicit key file, then `GEMINI_API_KEY`, then the file named by
    `WILLIAM_GEMINI_KEY_FILE`. A key file holds the bare key, or a markdown line
    `**key:** <key>`. Never logs or prints the key value.
    """
    if key_file is None:
        if env_key := os.environ.get("GEMINI_API_KEY", "").strip():
            return env_key
        if env_file := os.environ.get("WILLIAM_GEMINI_KEY_FILE", "").strip():
            key_file = Path(env_file)
        else:
            raise PhotogenError("No Gemini API key: set GEMINI_API_KEY or pass --key-file")
    if not key_file.is_file():
        raise PhotogenError(f"Key file not found: {key_file}")
    content = key_file.read_text(encoding="utf-8")
    match = re.search(r"\*\*key:\*\*\s*(\S+)", content)
    if match:
        key = match.group(1).strip()
    elif len(content.split()) == 1:
        key = content.strip()
    else:
        raise PhotogenError(f"Could not parse '**key:**' line in {key_file}")
    if not key:
        raise PhotogenError(f"Empty key parsed from {key_file}")
    return key


def redact_secret(text: str, secret: str) -> str:
    """Ensure the secret never appears in any error message or log string."""
    if not secret or not text:
        return text
    return text.replace(secret, "[REDACTED_API_KEY]")


def compose_prompt(subject_prompt: str, framing_instruction: str) -> str:
    """Combine a shot's 1595 subject prompt with a 2025-phone style framing instruction."""
    return f"{subject_prompt.strip()}\n\nCamera and style framing: {framing_instruction.strip()}"


def compute_usage_and_cost(usage_metadata: dict[str, Any]) -> dict[str, Any]:
    """Extract token breakdown from Gemini usageMetadata and compute exact USD cost."""
    prompt_tokens = int(usage_metadata.get("promptTokenCount", 0))
    candidates_tokens = int(usage_metadata.get("candidatesTokenCount", 0))
    thoughts_tokens = int(usage_metadata.get("thoughtsTokenCount", 0))
    total_tokens = int(
        usage_metadata.get("totalTokenCount", prompt_tokens + candidates_tokens + thoughts_tokens)
    )

    image_output_tokens = 0
    for detail in usage_metadata.get("candidatesTokensDetails", []):
        if str(detail.get("modality", "")).upper() == "IMAGE":
            image_output_tokens += int(detail.get("tokenCount", 0))
    if image_output_tokens == 0 and candidates_tokens > 0:
        image_output_tokens = 1120 if candidates_tokens >= 1120 else candidates_tokens

    non_image_candidate_tokens = max(0, candidates_tokens - image_output_tokens)
    text_and_thinking_tokens = non_image_candidate_tokens + thoughts_tokens

    cost_usd = (
        prompt_tokens * PRICING_PER_1M_USD["input_usd"]
        + image_output_tokens * PRICING_PER_1M_USD["image_output_usd"]
        + text_and_thinking_tokens * PRICING_PER_1M_USD["text_thinking_output_usd"]
    ) / 1_000_000.0

    return {
        "prompt_tokens": prompt_tokens,
        "image_output_tokens": image_output_tokens,
        "text_and_thinking_output_tokens": text_and_thinking_tokens,
        "thoughts_tokens": thoughts_tokens,
        "candidates_tokens": candidates_tokens,
        "total_tokens": total_tokens,
        "cost_usd": round(cost_usd, 6),
    }


def call_gemini_image_api(
    *,
    api_key: str,
    model: str,
    prompt: str,
    parameters: dict[str, Any],
    timeout_sec: int = 120,
    max_retries: int = 2,
) -> tuple[bytes, str, dict[str, Any]]:
    """Call Gemini generateContent for image generation and return (image_bytes, mime_type, usage_dict)."""
    url = f"{API_BASE_URL}/models/{model}:generateContent"
    gen_config: dict[str, Any] = {
        "responseModalities": parameters.get("responseModalities", ["IMAGE"]),
        "imageConfig": {
            "aspectRatio": parameters.get("aspectRatio", "4:3"),
            "imageSize": parameters.get("imageSize", "1K"),
        },
    }
    if "seed" in parameters and parameters["seed"] is not None:
        gen_config["seed"] = int(parameters["seed"])
    if "thinkingLevel" in parameters and parameters["thinkingLevel"]:
        gen_config["thinkingConfig"] = {"thinkingLevel": str(parameters["thinkingLevel"])}

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": gen_config,
    }
    body_bytes = json.dumps(payload).encode("utf-8")

    last_err: Exception | None = None
    for attempt in range(max_retries + 1):
        req = urllib.request.Request(
            url,
            data=body_bytes,
            headers={
                "x-goog-api-key": api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                raw_resp = resp.read().decode("utf-8")
                data = json.loads(raw_resp)
            break
        except urllib.error.HTTPError as exc:
            err_body = ""
            try:
                err_body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                err_body = str(exc)
            safe_body = redact_secret(err_body, api_key)
            # Retry only on transient 5xx if not a quota/tier failure
            if exc.code in (500, 502, 503, 504) and attempt < max_retries:
                time.sleep(2.0 * (attempt + 1))
                last_err = PhotogenError(f"HTTP {exc.code} from {model}: {safe_body}")
                continue
            raise PhotogenError(
                f"Gemini API HTTP {exc.code} on model '{model}': {safe_body}"
            ) from None
        except Exception as exc:
            safe_msg = redact_secret(str(exc), api_key)
            if attempt < max_retries:
                time.sleep(2.0 * (attempt + 1))
                last_err = PhotogenError(f"Request error on '{model}': {safe_msg}")
                continue
            raise PhotogenError(f"Request error on '{model}': {safe_msg}") from None
    else:
        raise last_err or PhotogenError("Unknown API failure")

    usage = compute_usage_and_cost(data.get("usageMetadata", {}))
    for cand in data.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                mime_type = inline.get("mimeType") or inline.get("mime_type") or "image/jpeg"
                img_bytes = base64.b64decode(inline["data"])
                return img_bytes, mime_type, usage

    safe_dump = redact_secret(json.dumps(data)[:800], api_key)
    raise PhotogenError(f"No inlineData image returned by '{model}'. Response: {safe_dump}")


def build_jobs_from_prompt_set(prompt_set: dict[str, Any], model_override: str | None = None) -> list[dict[str, Any]]:
    """Expand shots x framings into an ordered list of numbered generation jobs (1..N)."""
    model = model_override or prompt_set.get("default_model") or DEFAULT_MODEL
    default_params = dict(prompt_set.get("default_parameters") or {})
    framings = prompt_set.get("framings") or []
    shots = prompt_set.get("shots") or []
    if not framings or not shots:
        raise PhotogenError("Prompt set must contain non-empty 'framings' and 'shots' lists.")

    jobs: list[dict[str, Any]] = []
    num = 0
    for shot in shots:
        shot_idx = int(shot["shot_index"])
        shot_id = str(shot.get("id") or f"S{shot_idx:02d}")
        for framing in framings:
            num += 1
            f_id = str(framing["id"])
            f_slug = str(framing.get("slug") or f_id.lower())
            code = f"{shot_id}-{f_id}"
            filename = f"{num:02d}_{shot_id}_{f_id}_{shot['date']}_{shot['place']}.jpg"
            params = dict(default_params)
            if "parameters" in shot:
                params.update(shot["parameters"])
            if "parameters" in framing:
                params.update(framing["parameters"])
            full_prompt = compose_prompt(shot["subject_prompt"], framing["instruction"])
            jobs.append(
                {
                    "number": num,
                    "code": code,
                    "shot_index": shot_idx,
                    "shot_id": shot_id,
                    "framing_id": f_id,
                    "framing_slug": f_slug,
                    "framing_name": framing["name"],
                    "framing_short_label": framing.get("short_label", framing["name"]),
                    "framing_instruction": framing["instruction"],
                    "source_segment": {
                        "date": shot["date"],
                        "time": shot["time"],
                        "title": shot["title"],
                        "place": shot["place"],
                        "region": shot.get("region", ""),
                        "setting": shot.get("setting", ""),
                        "season": shot.get("season", ""),
                        "lighting": shot.get("lighting", ""),
                        "category": shot.get("category", ""),
                        "people_present": bool(shot.get("people_present", False)),
                        "entries": shot.get("entries", ""),
                        "shot_list_ref": shot.get("shot_list_ref", ""),
                        "day_file": shot["day_file"],
                        "photo_text": shot["photo_text"],
                        "world_text": shot.get("world_text", ""),
                        "segment_key": shot.get("segment_key", ""),
                        "day_key": shot.get("day_key", ""),
                        "journal_rel": shot.get("journal_rel", ""),
                    },
                    "subject_prompt": shot["subject_prompt"],
                    "full_prompt": full_prompt,
                    "model": model,
                    "parameters": params,
                    "seed": params.get("seed"),
                    "image_rel_path": f"images/{filename}",
                }
            )
    return jobs


def inspect_image_bytes(img_bytes: bytes) -> tuple[int, int]:
    """Return (width, height) of an encoded image."""
    with Image.open(io.BytesIO(img_bytes)) as im:
        return im.size


def downscale_image_file(
    src_path: Path,
    dst_path: Path,
    max_width: int = 1200,
    jpeg_quality: int = 84,
) -> tuple[int, int, int]:
    """Write a compressed/downscaled JPEG copy and return (width, height, byte_len)."""
    with Image.open(src_path) as im:
        rgb = im.convert("RGB")
        w, h = rgb.size
        if w > max_width:
            new_h = int(round(h * (max_width / float(w))))
            rgb = rgb.resize((max_width, new_h), Image.Resampling.LANCZOS)
            w, h = rgb.size
        buf = io.BytesIO()
        rgb.save(buf, format="JPEG", quality=jpeg_quality, optimize=True)
        out_bytes = buf.getvalue()
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    dst_path.write_bytes(out_bytes)
    return w, h, len(out_bytes)


def enforce_repo_size_limit(
    output_dir: Path,
    items: list[dict[str, Any]],
    max_repo_mb: float = 50.0,
    originals_root: Path | None = None,
    jpeg_quality: int = 84,
    max_width: int = 1200,
) -> dict[str, Any]:
    """If generated images exceed max_repo_mb, preserve full-res originals in /var/tmp and downscale committed copies."""
    total_raw_bytes = sum(int(item["bytes"]) for item in items)
    threshold_bytes = int(max_repo_mb * 1024 * 1024)
    if total_raw_bytes <= threshold_bytes:
        return {
            "downscaled": False,
            "committed_bytes": total_raw_bytes,
            "originals_bytes": total_raw_bytes,
            "originals_dir": None,
        }

    run_name = output_dir.name
    orig_dir = originals_root or Path(f"/var/tmp/william-photogen-{run_name}")
    orig_images_dir = orig_dir / "images"
    orig_images_dir.mkdir(parents=True, exist_ok=True)

    # Write a /var/tmp/.sweep-protect.<entry> sidecar so scratch cleanup keeps the originals
    protect_file = orig_dir.parent / f".sweep-protect.{orig_dir.name}"
    protect_file.write_text(
        f"Hold full-resolution originals for william-journal photogen run {run_name}. "
        f"The committed copies are the downscaled JPEGs; this directory is cited by that run's manifest.json. "
        f"Release when those copies no longer point here.\n",
        encoding="utf-8",
    )

    committed_total = 0
    for item in items:
        rel_path = item["image_rel_path"]
        repo_img_path = output_dir / rel_path
        orig_img_path = orig_dir / rel_path
        orig_img_path.parent.mkdir(parents=True, exist_ok=True)
        if not orig_img_path.exists():
            shutil.copy2(repo_img_path, orig_img_path)
        orig_w, orig_h = item["width"], item["height"]
        orig_b = orig_img_path.stat().st_size

        new_w, new_h, new_b = downscale_image_file(
            orig_img_path,
            repo_img_path,
            max_width=max_width,
            jpeg_quality=jpeg_quality,
        )
        item["original_path"] = str(orig_img_path)
        item["original_width"] = orig_w
        item["original_height"] = orig_h
        item["original_bytes"] = orig_b
        item["width"] = new_w
        item["height"] = new_h
        item["bytes"] = new_b
        committed_total += new_b

    return {
        "downscaled": True,
        "committed_bytes": committed_total,
        "originals_bytes": total_raw_bytes,
        "originals_dir": str(orig_dir),
    }


def render_review_html(manifest: dict[str, Any], output_dir: Path) -> Path:
    """Generate the self-contained static HTML review page at output_dir / index.html."""
    items = manifest["items"]
    framings = manifest["framings"]
    shots_map: dict[int, list[dict[str, Any]]] = {}
    for item in items:
        shots_map.setdefault(int(item["shot_index"]), []).append(item)

    for s_idx in shots_map:
        shots_map[s_idx].sort(key=lambda x: x["number"])

    total_images = manifest["total_images"]
    total_shots = len(shots_map)
    total_cost = manifest["total_cost_usd"]
    committed_mb = manifest["committed_bytes"] / (1024 * 1024)
    originals_mb = manifest.get("originals_bytes", manifest["committed_bytes"]) / (1024 * 1024)
    downscaled = manifest.get("downscaled", False)
    originals_dir = manifest.get("originals_dir")

    framing_cards_html = []
    for f in framings:
        framing_cards_html.append(
            f"""
            <div class="framing-spec-card">
              <div class="framing-spec-header">
                <span class="framing-badge framing-{html.escape(f['id'])}">Framing {html.escape(f['id'])}</span>
                <strong>{html.escape(f['name'])}</strong>
              </div>
              <p class="framing-spec-text">{html.escape(f['instruction'])}</p>
            </div>
            """
        )

    shot_sections_html = []
    w_val, h_val = 1200, 896
    for s_idx in sorted(shots_map.keys()):
        group = shots_map[s_idx]
        first = group[0]
        seg = first["source_segment"]
        shot_id = first["shot_id"]
        people_tag = "people" if seg["people_present"] else "no-people"
        people_label = "People" if seg["people_present"] else "No people"
        region_slug = seg["region"].split("(")[0].strip().lower().replace(" ", "-")
        season_slug = seg["season"].lower()
        setting_slug = seg["setting"].lower()

        cards_html = []
        for item in group:
            num = item["number"]
            code = item["code"]
            f_id = item["framing_id"]
            f_label = item["framing_short_label"]
            img_rel = item["image_rel_path"]
            cost_val = item["cost_usd"]
            kb_val = item["bytes"] / 1024.0
            w_val, h_val = item["width"], item["height"]
            tokens_val = item["usage"]["total_tokens"]
            full_prompt_escaped = html.escape(item["full_prompt"])
            caption_js = html.escape(
                f"#{num} ({code}) · {seg['date']} {seg['time']} · {seg['place']} · {seg['title']} — {f_label}"
            )

            cards_html.append(
                f"""
                <div class="sample-card" id="img-{num}">
                  <div class="sample-card-top">
                    <div class="cite-badges">
                      <a href="#img-{num}" class="cite-number" title="Cite this image in feedback">#{num}</a>
                      <span class="cite-code">{html.escape(code)}</span>
                    </div>
                    <span class="framing-pill framing-{html.escape(f_id)}">{html.escape(f_label)}</span>
                  </div>
                  <div class="image-frame" data-src="{html.escape(img_rel, quote=True)}" data-caption="{caption_js}" onclick="openLightboxFromEl(this)">
                    <img src="{html.escape(img_rel)}" alt="#{num} {html.escape(seg['title'])} ({html.escape(f_label)})" loading="lazy" width="{w_val}" height="{h_val}">
                    <span class="zoom-hint">Click to enlarge ({w_val}&times;{h_val})</span>
                  </div>
                  <div class="sample-meta-row">
                    <span>seed <code>{item['seed']}</code></span>
                    <span>{tokens_val:,} tok</span>
                    <span>${cost_val:.4f}</span>
                    <span>{kb_val:.0f} KB</span>
                  </div>
                  <details class="prompt-details">
                    <summary>Full prompt &amp; style framing sent to model</summary>
                    <pre class="prompt-pre">{full_prompt_escaped}</pre>
                  </details>
                </div>
                """
            )

        nums_range = f"#{group[0]['number']}&ndash;#{group[-1]['number']}"
        shot_sections_html.append(
            f"""
            <section class="shot-group" id="shot-{s_idx}"
                     data-region="{html.escape(region_slug)}"
                     data-season="{html.escape(season_slug)}"
                     data-setting="{html.escape(setting_slug)}"
                     data-people="{html.escape(people_tag)}">
              <div class="shot-header">
                <div class="shot-title-row">
                  <span class="shot-index-badge">Shot {s_idx} of {total_shots} ({nums_range})</span>
                  <h2>{html.escape(seg['title'])}</h2>
                  <span class="shot-coords">
                    <code>{html.escape(seg['date'])} {html.escape(seg['time'])}</code> &middot;
                    <code>{html.escape(seg['place'])}</code> &middot;
                    <code>{html.escape(seg['entries'])}</code> ({html.escape(seg['shot_list_ref'])})
                  </span>
                </div>
                <div class="shot-tags">
                  <span class="tag tag-region">{html.escape(seg['region'])}</span>
                  <span class="tag tag-season">{html.escape(seg['season'])}</span>
                  <span class="tag tag-setting">{html.escape(seg['setting'].capitalize())}</span>
                  <span class="tag tag-lighting">{html.escape(seg['lighting'])}</span>
                  <span class="tag tag-category">{html.escape(seg['category'])}</span>
                  <span class="tag tag-people">{html.escape(people_label)}</span>
                </div>
              </div>

              <div class="source-box">
                <div class="source-col">
                  <div class="source-label">Day file <code>### Photo</code> caption (<code>{html.escape(seg['day_file'])}</code>)</div>
                  <blockquote class="source-quote">{html.escape(seg['photo_text'])}</blockquote>
                </div>
                <div class="source-col">
                  <div class="source-label">1595 subject prompt (before style framing A / B / C)</div>
                  <p class="subject-prompt-text">{html.escape(first['subject_prompt'])}</p>
                </div>
              </div>

              <div class="comparison-grid">
                {''.join(cards_html)}
              </div>
            </section>
            """
        )

    storage_note = (
        f"{committed_mb:.1f} MB committed ({w_val}&times;{h_val} JPEGs); "
        f"untouched originals ({originals_mb:.1f} MB) in <code>{html.escape(str(originals_dir))}</code>"
        if downscaled and originals_dir
        else f"{committed_mb:.1f} MB committed in repo"
    )

    page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>The William Journal (1595 / 2025) · Photo Sample Round Review</title>
  <style>
    :root {{
      --bg: #111315;
      --panel: #191c20;
      --panel-alt: #20242a;
      --border: #2d323b;
      --text: #eceff4;
      --muted: #9aa3b2;
      --accent: #d8a657;
      --framing-a: #5e9eff;
      --framing-b: #c084fc;
      --framing-c: #34d399;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif;
      line-height: 1.5;
    }}
    .container {{
      max-width: 1560px;
      margin: 0 auto;
      padding: 28px 24px 64px;
    }}
    header.page-header {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 24px 28px;
      margin-bottom: 20px;
    }}
    header.page-header h1 {{
      margin: 0 0 8px;
      font-size: 1.65rem;
      font-weight: 650;
      letter-spacing: -0.02em;
    }}
    .subtitle {{
      color: var(--muted);
      margin: 0 0 18px;
      font-size: 0.98rem;
    }}
    .stats-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 12px;
      margin-bottom: 20px;
    }}
    .stat-box {{
      background: var(--panel-alt);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 10px 14px;
    }}
    .stat-label {{
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--muted);
    }}
    .stat-value {{
      font-size: 0.98rem;
      font-weight: 600;
      margin-top: 2px;
    }}
    .framings-overview {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 14px;
      margin-top: 14px;
    }}
    @media (max-width: 980px) {{
      .framings-overview {{ grid-template-columns: 1fr; }}
    }}
    .framing-spec-card {{
      background: var(--panel-alt);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px 14px;
    }}
    .framing-spec-header {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 6px;
      font-size: 0.9rem;
    }}
    .framing-spec-text {{
      margin: 0;
      font-size: 0.8rem;
      color: var(--muted);
    }}
    .framing-badge, .framing-pill {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 0.75rem;
      font-weight: 650;
      letter-spacing: 0.02em;
    }}
    .framing-A {{ background: rgba(94, 158, 255, 0.16); color: var(--framing-a); border: 1px solid rgba(94, 158, 255, 0.35); }}
    .framing-B {{ background: rgba(192, 132, 252, 0.16); color: var(--framing-b); border: 1px solid rgba(192, 132, 252, 0.35); }}
    .framing-C {{ background: rgba(52, 211, 153, 0.16); color: var(--framing-c); border: 1px solid rgba(52, 211, 153, 0.35); }}

    .toolbar {{
      position: sticky;
      top: 0;
      z-index: 20;
      background: rgba(25, 28, 32, 0.95);
      backdrop-filter: blur(8px);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 12px 16px;
      margin-bottom: 24px;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }}
    .filter-group {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 6px;
    }}
    .filter-label {{
      font-size: 0.78rem;
      color: var(--muted);
      margin-right: 4px;
      font-weight: 600;
    }}
    button.filter-btn, button.action-btn {{
      background: var(--panel-alt);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 5px 10px;
      font-size: 0.8rem;
      cursor: pointer;
    }}
    button.filter-btn.active {{
      background: var(--accent);
      color: #111315;
      border-color: var(--accent);
      font-weight: 600;
    }}
    button.action-btn:hover, button.filter-btn:hover {{
      border-color: var(--accent);
    }}

    section.shot-group {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 20px 22px;
      margin-bottom: 26px;
    }}
    .shot-header {{
      display: flex;
      flex-wrap: wrap;
      align-items: baseline;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 12px;
      padding-bottom: 10px;
      border-bottom: 1px solid var(--border);
    }}
    .shot-title-row {{
      display: flex;
      flex-wrap: wrap;
      align-items: baseline;
      gap: 12px;
    }}
    .shot-index-badge {{
      background: rgba(216, 166, 87, 0.16);
      color: var(--accent);
      border: 1px solid rgba(216, 166, 87, 0.4);
      border-radius: 6px;
      padding: 2px 9px;
      font-size: 0.78rem;
      font-weight: 650;
    }}
    .shot-title-row h2 {{
      margin: 0;
      font-size: 1.25rem;
      font-weight: 650;
    }}
    .shot-coords {{
      font-size: 0.85rem;
      color: var(--muted);
    }}
    .shot-tags {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}
    .tag {{
      background: var(--panel-alt);
      border: 1px solid var(--border);
      border-radius: 5px;
      padding: 2px 8px;
      font-size: 0.74rem;
      color: var(--muted);
    }}

    .source-box {{
      display: grid;
      grid-template-columns: 1fr 1.25fr;
      gap: 14px;
      background: var(--panel-alt);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px 16px;
      margin-bottom: 16px;
    }}
    @media (max-width: 900px) {{
      .source-box {{ grid-template-columns: 1fr; }}
    }}
    .source-label {{
      font-size: 0.74rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--muted);
      margin-bottom: 4px;
    }}
    .source-quote {{
      margin: 0;
      font-size: 0.92rem;
      color: var(--text);
      border-left: 3px solid var(--accent);
      padding-left: 10px;
    }}
    .subject-prompt-text {{
      margin: 0;
      font-size: 0.83rem;
      color: #cfd6e2;
    }}

    .comparison-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
    }}
    @media (max-width: 1024px) {{
      .comparison-grid {{ grid-template-columns: 1fr; }}
    }}
    .sample-card {{
      background: var(--panel-alt);
      border: 1px solid var(--border);
      border-radius: 10px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }}
    .sample-card-top {{
      padding: 10px 12px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid var(--border);
    }}
    .cite-badges {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    a.cite-number {{
      background: var(--accent);
      color: #111315;
      font-weight: 750;
      font-size: 0.92rem;
      padding: 2px 9px;
      border-radius: 6px;
      text-decoration: none;
    }}
    .cite-code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 0.8rem;
      color: var(--muted);
    }}
    .image-frame {{
      position: relative;
      cursor: zoom-in;
      background: #0b0c0e;
      aspect-ratio: 4 / 3;
      overflow: hidden;
    }}
    .image-frame img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
      transition: transform 0.18s ease;
    }}
    .image-frame:hover img {{
      transform: scale(1.015);
    }}
    .zoom-hint {{
      position: absolute;
      right: 8px;
      bottom: 8px;
      background: rgba(0, 0, 0, 0.72);
      color: #fff;
      font-size: 0.7rem;
      padding: 2px 7px;
      border-radius: 4px;
      opacity: 0;
      transition: opacity 0.15s ease;
    }}
    .image-frame:hover .zoom-hint {{
      opacity: 1;
    }}
    .sample-meta-row {{
      display: flex;
      justify-content: space-between;
      padding: 7px 12px;
      font-size: 0.75rem;
      color: var(--muted);
      border-top: 1px solid var(--border);
      background: rgba(0, 0, 0, 0.18);
    }}
    details.prompt-details {{
      padding: 8px 12px;
      border-top: 1px solid var(--border);
      font-size: 0.78rem;
    }}
    details.prompt-details summary {{
      cursor: pointer;
      color: var(--muted);
      user-select: none;
    }}
    pre.prompt-pre {{
      white-space: pre-wrap;
      word-break: break-word;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 0.74rem;
      color: #d5dce6;
      background: #121417;
      padding: 10px;
      border-radius: 6px;
      margin: 8px 0 2px;
      max-height: 220px;
      overflow-y: auto;
    }}

    /* Lightbox modal */
    #lightbox {{
      display: none;
      position: fixed;
      inset: 0;
      z-index: 100;
      background: rgba(8, 9, 12, 0.92);
      align-items: center;
      justify-content: center;
      flex-direction: column;
      padding: 24px;
    }}
    #lightbox.open {{
      display: flex;
    }}
    #lightbox img {{
      max-width: 92vw;
      max-height: 82vh;
      border-radius: 8px;
      border: 1px solid var(--border);
      box-shadow: 0 18px 50px rgba(0, 0, 0, 0.7);
    }}
    #lightbox-caption {{
      margin-top: 12px;
      font-size: 0.95rem;
      color: var(--text);
      text-align: center;
    }}
    #lightbox-close {{
      position: absolute;
      top: 18px;
      right: 24px;
      background: var(--panel-alt);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 6px 12px;
      font-size: 0.85rem;
      cursor: pointer;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header class="page-header">
      <h1>The William Journal (1595 / 2025) &middot; Photo Sample Round Review</h1>
      <p class="subtitle">
        20 varied scenes from the accepted 1595 year across 3 alternative 2025-phone style framings (<strong>{total_images} images</strong>, cited as <code>#1</code>&ndash;<code>#{total_images}</code> or <code>S01-A</code>&ndash;<code>S20-C</code>).
        Authentic 1595 England in front of the lens; 2025 phone camera clarity, color, and framing with zero artificial aging.
      </p>

      <div class="stats-grid">
        <div class="stat-box">
          <div class="stat-label">Model (Checked {html.escape(manifest['model_verification']['checked_date'])})</div>
          <div class="stat-value"><code>{html.escape(manifest['model'])}</code> (Nano Banana 2.1)</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">Samples &amp; Aspect</div>
          <div class="stat-value">{total_images} images ({total_shots} shots &times; 3 framings, 4:3)</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">Total API Cost</div>
          <div class="stat-value">${total_cost:.2f} USD (${total_cost / max(1, total_images):.4f} / image)</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">Size on Disk</div>
          <div class="stat-value">{storage_note}</div>
        </div>
      </div>

      <div class="framings-overview">
        {''.join(framing_cards_html)}
      </div>
    </header>

    <div class="toolbar">
      <div class="filter-group">
        <span class="filter-label">Filter shots:</span>
        <button class="filter-btn active" onclick="filterShots('all', this)">All ({total_shots})</button>
        <button class="filter-btn" onclick="filterShots('region:london', this)">London</button>
        <button class="filter-btn" onclick="filterShots('region:stratford', this)">Stratford</button>
        <button class="filter-btn" onclick="filterShots('region:the-road', this)">The Road</button>
        <button class="filter-btn" onclick="filterShots('region:court', this)">Court</button>
        <button class="filter-btn" onclick="filterShots('setting:inside', this)">Inside</button>
        <button class="filter-btn" onclick="filterShots('setting:outside', this)">Outside</button>
        <button class="filter-btn" onclick="filterShots('season:winter', this)">Winter</button>
        <button class="filter-btn" onclick="filterShots('season:spring', this)">Spring</button>
        <button class="filter-btn" onclick="filterShots('season:summer', this)">Summer</button>
        <button class="filter-btn" onclick="filterShots('season:autumn', this)">Autumn</button>
        <button class="filter-btn" onclick="filterShots('people:people', this)">People</button>
        <button class="filter-btn" onclick="filterShots('people:no-people', this)">No people</button>
      </div>
      <div class="filter-group">
        <button class="action-btn" onclick="toggleAllPrompts(true)">Expand all prompts</button>
        <button class="action-btn" onclick="toggleAllPrompts(false)">Collapse all prompts</button>
      </div>
    </div>

    <main id="shots-container">
      {''.join(shot_sections_html)}
    </main>
  </div>

  <div id="lightbox" onclick="closeLightbox(event)">
    <button id="lightbox-close" onclick="closeLightbox(event)">Close (Esc)</button>
    <img id="lightbox-img" src="" alt="">
    <div id="lightbox-caption"></div>
  </div>

  <script>
    function filterShots(criteria, btn) {{
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      if (btn) btn.classList.add('active');
      const sections = document.querySelectorAll('section.shot-group');
      sections.forEach(sec => {{
        if (criteria === 'all') {{
          sec.style.display = '';
          return;
        }}
        const [attr, val] = criteria.split(':');
        const actual = sec.getAttribute('data-' + attr) || '';
        sec.style.display = actual.includes(val) ? '' : 'none';
      }});
    }}

    function toggleAllPrompts(openState) {{
      document.querySelectorAll('details.prompt-details').forEach(d => {{
        d.open = openState;
      }});
    }}

    function openLightboxFromEl(el) {{
      if (!el) return;
      const src = el.getAttribute('data-src') || '';
      const caption = el.getAttribute('data-caption') || '';
      const lb = document.getElementById('lightbox');
      document.getElementById('lightbox-img').src = src;
      document.getElementById('lightbox-caption').textContent = caption;
      lb.classList.add('open');
    }}

    function closeLightbox(e) {{
      if (e && e.target && e.target.id === 'lightbox-img') return;
      const lb = document.getElementById('lightbox');
      lb.classList.remove('open');
      document.getElementById('lightbox-img').src = '';
    }}

    document.addEventListener('keydown', e => {{
      if (e.key === 'Escape') closeLightbox();
    }});
  </script>
</body>
</html>
"""
    index_path = output_dir / "index.html"
    clean_html = "\n".join(line.rstrip() for line in page_html.splitlines()) + "\n"
    index_path.write_text(clean_html, encoding="utf-8")
    return index_path


def run_photogen(
    *,
    prompt_set_path: Path,
    output_dir: Path,
    key_file: Path | None = None,
    model_override: str | None = None,
    max_images: int = 60,
    budget_usd: float = 25.0,
    max_repo_mb: float = 50.0,
    workers: int = 4,
    overwrite: bool = False,
    render_only: bool = False,
) -> dict[str, Any]:
    """Execute a photogen sample run, writing images, manifest.json, and index.html."""
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"

    if render_only:
        if not manifest_path.is_file():
            raise PhotogenError(f"Cannot --render-only; manifest not found at {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        render_review_html(manifest, output_dir)
        return manifest

    prompt_set = json.loads(prompt_set_path.read_text(encoding="utf-8"))
    jobs = build_jobs_from_prompt_set(prompt_set, model_override=model_override)
    if len(jobs) > max_images:
        raise PhotogenError(
            f"Prompt set expands to {len(jobs)} images, exceeding --max-images={max_images}."
        )

    api_key = load_api_key(key_file)

    existing_by_num: dict[int, dict[str, Any]] = {}
    # Money already paid into this output directory. It survives deleted,
    # regenerated and overwritten images, so --budget-usd caps real spend.
    # A manifest written before `spent_usd` existed falls back to its
    # keepers' total, which undercounts anything deleted before then.
    prior_spent = 0.0
    if manifest_path.is_file():
        try:
            old_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            old_manifest = {}
        prior_spent = float(old_manifest.get("spent_usd", old_manifest.get("total_cost_usd", 0.0)) or 0.0)
        if not overwrite:
            try:
                for item in old_manifest.get("items", []):
                    img_file = output_dir / item["image_rel_path"]
                    if img_file.is_file() and img_file.stat().st_size > 0:
                        existing_by_num[int(item["number"])] = item
            except Exception:
                existing_by_num = {}

    results_by_num: dict[int, dict[str, Any]] = dict(existing_by_num)
    pending_jobs = [j for j in jobs if j["number"] not in results_by_num]

    # Estimate upper-bound cost before starting (~$0.05/image for 1K Nano Banana 2.1)
    est_cost = prior_spent + len(pending_jobs) * 0.05
    if est_cost > budget_usd:
        raise PhotogenError(
            f"Estimated cost ${est_cost:.2f} (${prior_spent:.2f} already spent in this output directory "
            f"+ {len(pending_jobs)} images to generate) exceeds budget cap ${budget_usd:.2f}"
        )

    def _run_one(job: dict[str, Any]) -> dict[str, Any]:
        img_bytes, mime_type, usage = call_gemini_image_api(
            api_key=api_key,
            model=job["model"],
            prompt=job["full_prompt"],
            parameters=job["parameters"],
        )
        img_path = output_dir / job["image_rel_path"]
        img_path.parent.mkdir(parents=True, exist_ok=True)
        img_path.write_bytes(img_bytes)
        w, h = inspect_image_bytes(img_bytes)
        return {
            "number": job["number"],
            "code": job["code"],
            "shot_index": job["shot_index"],
            "shot_id": job["shot_id"],
            "framing_id": job["framing_id"],
            "framing_slug": job["framing_slug"],
            "framing_name": job["framing_name"],
            "framing_short_label": job["framing_short_label"],
            "framing_instruction": job["framing_instruction"],
            "source_segment": job["source_segment"],
            "subject_prompt": job["subject_prompt"],
            "full_prompt": job["full_prompt"],
            "model": job["model"],
            "parameters": job["parameters"],
            "seed": job["seed"],
            "mime_type": mime_type,
            "usage": usage,
            "cost_usd": usage["cost_usd"],
            "image_rel_path": job["image_rel_path"],
            "width": w,
            "height": h,
            "bytes": len(img_bytes),
        }

    def _persist(items: list[dict[str, Any]], size_info: dict[str, Any] | None = None) -> dict[str, Any]:
        info = size_info or {
            "downscaled": False,
            "committed_bytes": sum(int(it.get("bytes", 0)) for it in items),
            "originals_bytes": sum(int(it.get("bytes", 0)) for it in items),
            "originals_dir": None,
        }
        manifest_body: dict[str, Any] = {
            "schema_version": 1,
            "run_id": output_dir.name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "model": jobs[0]["model"] if jobs else DEFAULT_MODEL,
            "model_verification": MODEL_VERIFICATION,
            "pricing_per_1m_tokens_usd": PRICING_PER_1M_USD,
            "parameters": prompt_set.get("default_parameters", {}),
            "total_images": len(items),
            "total_shots": len(prompt_set.get("shots", [])),
            "total_framings": len(prompt_set.get("framings", [])),
            "total_cost_usd": round(sum(float(it.get("cost_usd", 0.0)) for it in items), 6),
            "spent_usd": round(running_cost, 6),
            "downscaled": info["downscaled"],
            "committed_bytes": info["committed_bytes"],
            "originals_bytes": info["originals_bytes"],
            "originals_dir": info["originals_dir"],
            "framings": prompt_set.get("framings", []),
            "items": items,
            "complete": len(items) == len(jobs),
        }
        manifest_path.write_text(json.dumps(manifest_body, indent=2) + "\n", encoding="utf-8")
        return manifest_body

    running_cost = prior_spent

    if pending_jobs:
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            future_to_job = {pool.submit(_run_one, job): job for job in pending_jobs}
            for fut in as_completed(future_to_job):
                job = future_to_job[fut]
                item_res = fut.result()
                running_cost += float(item_res["cost_usd"])
                results_by_num[job["number"]] = item_res
                ordered_now = [results_by_num[j["number"]] for j in jobs if j["number"] in results_by_num]
                _persist(ordered_now)
                print(
                    f"[{len(results_by_num):02d}/{len(jobs):02d}] #{item_res['number']:02d} "
                    f"{item_res['code']} ({item_res['source_segment']['date']} {item_res['source_segment']['place']}) "
                    f"-> {item_res['width']}x{item_res['height']} ({item_res['bytes'] // 1024} KB, ${item_res['cost_usd']:.4f}) "
                    f"running=${running_cost:.4f}",
                    flush=True,
                )
                if running_cost > budget_usd:
                    pool.shutdown(wait=False, cancel_futures=True)
                    raise PhotogenError(
                        f"Spend in this output directory ${running_cost:.4f} exceeded budget limit ${budget_usd:.2f}; stopping."
                    )

    ordered_items = [results_by_num[j["number"]] for j in jobs]
    size_info = enforce_repo_size_limit(
        output_dir=output_dir,
        items=ordered_items,
        max_repo_mb=max_repo_mb,
    )
    manifest = _persist(ordered_items, size_info)
    render_review_html(manifest, output_dir)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate sample photos and a static HTML review page for the william journal."
    )
    parser.add_argument(
        "--prompts",
        type=Path,
        default=DEFAULT_PROMPT_SET_PATH,
        help="Path to prompt set JSON (default: tools/photogen/prompts_sample_round.json)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output directory for generated images, manifest.json, and index.html (e.g. photos/samples/261117-round1)",
    )
    parser.add_argument(
        "--key-file",
        type=Path,
        default=None,
        help="File holding the Gemini API key (default: GEMINI_API_KEY, then WILLIAM_GEMINI_KEY_FILE)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help=f"Override Gemini image model ID (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--max-images",
        type=int,
        default=60,
        help="Hard cap on total images generated in one run (default: 60)",
    )
    parser.add_argument(
        "--budget-usd",
        type=float,
        default=25.0,
        help="Hard cap in USD on everything spent in this --out directory, across runs; deleted or regenerated images still count (manifest `spent_usd`; default: 25.0)",
    )
    parser.add_argument(
        "--max-repo-mb",
        type=float,
        default=50.0,
        help="Downscale committed images and move untouched originals to /var/tmp if raw bytes exceed this MB limit (default: 50.0)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Concurrent API requests (default: 4)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Regenerate all images even if already present in --out",
    )
    parser.add_argument(
        "--render-only",
        action="store_true",
        help="Re-render index.html from an existing manifest.json without calling the API",
    )
    args = parser.parse_args(argv)

    try:
        manifest = run_photogen(
            prompt_set_path=args.prompts,
            output_dir=args.out,
            key_file=args.key_file,
            model_override=args.model,
            max_images=args.max_images,
            budget_usd=args.budget_usd,
            max_repo_mb=args.max_repo_mb,
            workers=args.workers,
            overwrite=args.overwrite,
            render_only=args.render_only,
        )
    except PhotogenError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(
        f"Done: {manifest['total_images']} images | cost=${manifest['total_cost_usd']:.4f} | "
        f"committed={manifest['committed_bytes'] / (1024 * 1024):.2f} MB | "
        f"review={args.out / 'index.html'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
