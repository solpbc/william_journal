#!/usr/bin/env python3
"""Build the Framing C prompt set for every photo segment in the william journal.

One entry per `### Photo` segment under `content/weeks/*/merged/2025-*.md`.
The subject is the segment caption, plus the world's § 7.7 shot line and § 8.6
specimen when this photo is one of those numbered shots. Framing C and the
sample round's guards are applied to every entry.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = TOOLS_DIR.parent
PHOTOGEN_DIR = Path(__file__).resolve().parent
WORLD_PATH = PROJECT_ROOT / "world" / "world.md"
CONTENT_WEEKS = PROJECT_ROOT / "content" / "weeks"
SAMPLE_PROMPTS = PHOTOGEN_DIR / "prompts_sample_round.json"
OUT_PATH = PHOTOGEN_DIR / "prompts_year.json"

if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import converter  # noqa: E402

MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

GUARDS = (
    "Guards from the sample round: no added signs or legible lettering anywhere "
    "(no play titles, shop signs, banners, book titles, or printed words; any writing "
    "is illegible cursive or smudged black-letter only). Do not show the photographer's "
    "hand, arm, or anything he is carrying unless the subject text explicitly puts his "
    "own hand in the frame; if it does, that hand only, with no face and no reflection. "
    "No modern background details: no skyline blocks, no glass street lamps, no "
    "cast-iron downpipes, no tattoo-like smudges. Clean bare skin. Nothing aged, sepia, "
    "grained, vignetted, or painted."
)

PERIOD_TAIL = (
    "England in 1595 only: timber, lime plaster, wool, linen, leather, iron, tallow, "
    "thatch, mud, and hand-made objects. Nobody poses or looks into the lens. Light is "
    "only sun, fog, candle, rushlight, cresset, or fire. Do not show a child's death, "
    "a funeral, or grief for a son. This is a 2025 phone picture of that year, not a painting."
)


def _section(world: str, start: str, end: str) -> str:
    body = world.split(start, 1)[1]
    return body.split(end, 1)[0]


def _iso_from_world_date(cell: str) -> str:
    match = re.search(r"(\d{1,2})\s+([A-Za-z]{3})", cell.strip())
    if not match:
        raise ValueError(f"Cannot read a § 7.7 date from {cell!r}")
    month = MONTHS[match.group(2).lower()]
    return f"2025-{month:02d}-{int(match.group(1)):02d}"


def parse_shot_list(world: str) -> list[dict[str, str]]:
    """Return § 7.7 rows. The closing-shot line (no number) is not a row."""
    section = _section(world, "### 7.7 Photo shot list", "### 7.8")
    rows: list[dict[str, str]] = []
    for line in section.splitlines():
        match = re.match(
            r"^\| (\d+) \| ([^|]+?) \| ([^|]+?) \| `([^`]+)` \| (.+?) \|$",
            line.strip(),
        )
        if not match:
            continue
        rows.append(
            {
                "number": match.group(1),
                "date": _iso_from_world_date(match.group(2)),
                "entry": match.group(3).strip(),
                "place": match.group(4).strip(),
                "shot": match.group(5).strip(),
            }
        )
    return rows


def _blockquote(chunk: str) -> str:
    lines = []
    for line in chunk.splitlines():
        if line.startswith("> "):
            lines.append(line[2:].strip())
        elif line.startswith(">"):
            lines.append(line[1:].strip())
    return "\n".join(lines).strip()


def _split_frames(body: str) -> list[tuple[str, str]]:
    if not re.search(r"Frame \d+", body):
        return [("specimen", body)]
    parts = re.split(r"\*?Frame (\d+)\.?\*?\s*", body)
    frames: list[tuple[str, str]] = []
    preamble = parts[0].strip()
    iterator = iter(parts[1:])
    for number, text in zip(iterator, iterator):
        joined = f"{preamble} {text}".strip() if preamble else text.strip()
        frames.append((f"frame {number}", joined))
    return frames or [("specimen", body)]


def parse_specimens(world: str) -> list[dict[str, str]]:
    """Return § 8.6 prompt blocks, split when one entry has two frames."""
    section = _section(world, "### 8.6 Photo prompts", "\n## 9.")
    specimens: list[dict[str, str]] = []
    for chunk in re.split(r"\n(?=\*\*Photo )", section):
        header_match = re.match(r"\*\*Photo ([^*]+)\*\*", chunk.strip())
        if not header_match:
            continue
        header = header_match.group(1)
        entry_match = re.search(r"`([A-Z][A-Za-z0-9]*)`", header)
        date_match = re.search(r"(20\d\d-\d\d-\d\d)", header)
        if not entry_match or not date_match:
            continue
        places = re.findall(r"`([a-z][a-z0-9_]*)`", header)
        body = _blockquote(chunk)
        if not body:
            continue
        frames = _split_frames(body)
        for index, (label, text) in enumerate(frames):
            place = places[index] if index < len(places) else (places[0] if len(places) == 1 else "")
            specimens.append(
                {
                    "label": f"Photo {header.split('·')[0].strip()} {label}".strip(),
                    "entry": entry_match.group(1),
                    "date": date_match.group(1),
                    "place": place,
                    "text": text,
                }
            )
    return specimens


def _hand_scan_text(text: str) -> str:
    """Caption text used to decide whether a person's hand is in the frame.

    Drops negated sentences ("No lantern in his hand"), a hand that has already
    left, the frame's left-hand edge, and phrases where "hand" means handwriting.
    """
    cleaned = re.sub(r"left hand's edge|right-hand\b", " ", text, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"in \w+'s hand\b|\w+'s hand and the\b|italic hands\b",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    parts = re.split(r"(?<=[.!?])\s+", cleaned.strip())
    kept: list[str] = []
    for part in parts:
        sentence = part.strip()
        if re.match(r"(?i)no\b", sentence):
            continue
        if re.search(r"(?i)hand has left|hands have left|put a hand on", sentence):
            continue
        kept.append(sentence)
    return " ".join(kept)


def caption_mentions_handwriting(text: str) -> bool:
    return bool(
        re.search(
            r"in \w+'s hand\b|\w+'s hand and the\b|italic hands\b|secretary,\s*chancery",
            text,
            re.IGNORECASE,
        )
    )


def caption_wants_own_hand(text: str) -> bool:
    """True when the caption puts the photographer's own hand in the frame.

    Other people's hands (Nick's, Heminges's, a boy's) do not count. "Left hand's
    edge" is the edge of the frame, not a hand. A sentence that begins with "No"
    does not put a hand in.
    """
    return bool(
        re.search(
            r"(your own hand|his own hand|your hand|in his palm|his palm|"
            r"his (?:inked |ink-stained )?forefinger|your fingers|"
            r"ink (?:is )?on the (?:right )?forefinger|\bright forefinger\b|"
            r"the hand in the foreground|\bhis right hand\b|\bhis two hands\b|"
            r"\bin his hand\b|no one else's hands|a hand at the edge|"
            r"the pen still in the hand|only the paper, the stroke, and the hand|"
            r"\ba right hand\b|\bthe right hand\b|a pair of hands holds)",
            _hand_scan_text(text),
            re.IGNORECASE,
        )
    )


def caption_names_a_hand(text: str) -> bool:
    """True when the caption mentions a person's hand that may belong to someone else."""
    return bool(re.search(r"\b(?:hands?|palm|forefinger|fingers)\b", _hand_scan_text(text), re.IGNORECASE))


def _drop_viewer_hand_sentences(text: str) -> str:
    kept: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
        if re.search(r"own hand|viewer'?s hand|holds a .*basket|basket handle", sentence, re.IGNORECASE):
            continue
        kept.append(sentence)
    return " ".join(kept).strip()


def sanitize_world_text(text: str, caption: str) -> str:
    if caption_wants_own_hand(caption):
        return text.strip()
    return _drop_viewer_hand_sentences(text)


def _token_set(text: str) -> set[str]:
    return {tok for tok in re.findall(r"[a-z]{4,}", text.lower())}


def _jaccard(a: str, b: str) -> float:
    left, right = _token_set(a), _token_set(b)
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def match_shot_list(
    segments: list[dict[str, Any]], rows: list[dict[str, str]]
) -> dict[str, dict[str, str]]:
    """Assign each § 7.7 row to at most one segment. Keyed by segment id."""
    candidates: list[tuple[float, str, str]] = []
    by_number = {row["number"]: row for row in rows}
    for seg in segments:
        for row in rows:
            if row["date"] != seg["date"] or row["entry"] not in seg["entries"]:
                continue
            score = _jaccard(row["shot"], seg["photo_text"])
            if row["place"] == seg["place"]:
                score += 0.35
            candidates.append((score, seg["id"], row["number"]))
    candidates.sort(key=lambda item: item[0], reverse=True)
    used_seg: set[str] = set()
    used_row: set[str] = set()
    assigned: dict[str, dict[str, str]] = {}
    for _score, seg_id, number in candidates:
        if seg_id in used_seg or number in used_row:
            continue
        used_seg.add(seg_id)
        used_row.add(number)
        assigned[seg_id] = by_number[number]
    # A row whose content photo carries a different entry id still belongs to
    # that photo when the date and place name exactly one unassigned segment.
    # 29 Dec W108 is tagged M056 on the latch photo; the shot sentence is that picture.
    for row in rows:
        if row["number"] in used_row:
            continue
        hits = [
            seg
            for seg in segments
            if seg["date"] == row["date"] and seg["place"] == row["place"] and seg["id"] not in used_seg
        ]
        if len(hits) != 1:
            continue
        used_seg.add(hits[0]["id"])
        used_row.add(row["number"])
        assigned[hits[0]["id"]] = row
    return assigned


def match_specimens(
    segments: list[dict[str, Any]], specimens: list[dict[str, str]]
) -> dict[str, dict[str, str]]:
    """Assign each § 8.6 frame to at most one segment. Keyed by segment id."""
    assigned: dict[str, dict[str, str]] = {}
    used: set[int] = set()
    for seg in segments:
        cands = [
            (index, spec)
            for index, spec in enumerate(specimens)
            if spec["date"] == seg["date"] and spec["entry"] in seg["entries"] and index not in used
        ]
        if not cands:
            continue
        place_hits = [(index, spec) for index, spec in cands if spec["place"] and spec["place"] == seg["place"]]
        pool = place_hits or cands
        best_index, best = max(pool, key=lambda item: _jaccard(item[1]["text"], seg["photo_text"]))
        used.add(best_index)
        assigned[seg["id"]] = best
    return assigned


def collect_segments() -> list[dict[str, Any]]:
    files = sorted(CONTENT_WEEKS.glob("*/merged/2025-*.md"))
    segments: list[dict[str, Any]] = []
    for path in files:
        day = converter.parse_day_markdown(path)
        for seg in day.segments:
            if seg.kind != "photo":
                continue
            day_key = seg.day_key
            rel_day = path.relative_to(PROJECT_ROOT).as_posix()
            journal_rel = f"chronicle/{day_key}/import.image/{seg.segment_key}"
            segments.append(
                {
                    "id": f"{seg.day_iso}/{seg.segment_key}",
                    "date": seg.day_iso,
                    "time": seg.start_hhmm,
                    "title": seg.heading_title,
                    "place": seg.place,
                    "entries": list(seg.entries),
                    "photo_text": seg.photo_text,
                    "segment_key": seg.segment_key,
                    "day_key": day_key,
                    "day_file": rel_day,
                    "journal_rel": journal_rel,
                }
            )
    segments.sort(key=lambda item: (item["date"], item["time"], item["segment_key"]))
    return segments


def _subject_prompt(seg: dict[str, Any], shot: dict[str, str] | None, specimen: dict[str, str] | None) -> str:
    blocks = [seg["photo_text"].strip()]
    if shot:
        line = sanitize_world_text(shot["shot"], seg["photo_text"])
        if line:
            blocks.append(f"World shot list § 7.7 #{shot['number']} ({shot['entry']}): {line}")
    if specimen:
        line = sanitize_world_text(specimen["text"], seg["photo_text"])
        if line:
            blocks.append(f"World specimen § 8.6 {specimen['label']} ({specimen['entry']}): {line}")
    rules = [PERIOD_TAIL]
    if caption_wants_own_hand(seg["photo_text"]):
        rules.append(
            "His own hand is in the frame, as the caption says. No face, no mirror, and no reflection."
        )
    elif caption_names_a_hand(seg["photo_text"]):
        rules.append(
            "Keep only the hands the caption names. Do not add the photographer's own hand, arm, "
            "or shadow, and do not add a hand the caption does not name."
        )
    else:
        rules.append(
            "The photographer is not in the picture: no hand of his, no shadow of him, no reflection, "
            "and nothing carried into the frame that the caption does not name."
        )
    if re.search(r"no face", seg["photo_text"], re.IGNORECASE):
        rules.append("Where the caption says no face, show no face.")
    if re.search(r"\blady\b", seg["photo_text"], re.IGNORECASE):
        rules.append("Do not identify the unnamed lady, and do not show her face.")
    if re.search(r"letter|black-letter|proclamation|playbill|title|ink|written|page|book", seg["photo_text"], re.IGNORECASE):
        rules.append("Any writing in the frame is illegible. Do not render readable English words.")
    if caption_mentions_handwriting(seg["photo_text"]):
        rules.append("Where the caption says hand and means handwriting or a signature, do not draw a person's hand for that word.")
    blocks.append(" ".join(rules))
    return "\n\n".join(blocks)


def framing_c() -> tuple[dict[str, Any], dict[str, Any]]:
    sample = json.loads(SAMPLE_PROMPTS.read_text(encoding="utf-8"))
    framing = next(item for item in sample["framings"] if item["id"] == "C")
    built = dict(framing)
    built["instruction"] = f"{framing['instruction']} {GUARDS}"
    return built, sample["default_parameters"]


def build_prompt_set() -> dict[str, Any]:
    world = WORLD_PATH.read_text(encoding="utf-8")
    segments = collect_segments()
    rows = parse_shot_list(world)
    specimens = parse_specimens(world)
    shot_by_seg = match_shot_list(segments, rows)
    spec_by_seg = match_specimens(segments, specimens)
    framing, parameters = framing_c()
    shots = []
    for index, seg in enumerate(segments, start=1):
        shot = shot_by_seg.get(seg["id"])
        specimen = spec_by_seg.get(seg["id"])
        world_bits = []
        if shot:
            world_bits.append(f"§ 7.7 #{shot['number']} ({shot['entry']}): {shot['shot']}")
        if specimen:
            world_bits.append(f"§ 8.6 {specimen['label']} ({specimen['entry']})")
        shots.append(
            {
                "shot_index": index,
                "id": f"p{index:03d}",
                "date": seg["date"],
                "time": seg["time"],
                "title": seg["title"],
                "place": seg["place"],
                "segment_key": seg["segment_key"],
                "day_key": seg["day_key"],
                "journal_rel": seg["journal_rel"],
                "entries": ", ".join(seg["entries"]),
                "shot_list_ref": " · ".join(world_bits),
                "day_file": seg["day_file"],
                "photo_text": seg["photo_text"],
                "world_text": "\n\n".join(world_bits),
                "people_present": "no people" not in seg["photo_text"].lower(),
                "subject_prompt": _subject_prompt(seg, shot, specimen),
            }
        )
    return {
        "schema_version": 1,
        "description": (
            "All photo segments of the 1595/2025 william journal, one Framing C image each. "
            "Framing C was chosen on 2026-11-17."
        ),
        "default_model": "gemini-nano-banana-2.1",
        "default_parameters": parameters,
        "framings": [framing],
        "shots": shots,
        "_match_report": {
            "segments": len(segments),
            "shot_list_rows": len(rows),
            "shot_list_matched": len(shot_by_seg),
            "specimens": len(specimens),
            "specimens_matched": len(spec_by_seg),
            "unmatched_shot_rows": [
                f"#{row['number']} {row['date']} {row['entry']} {row['place']}"
                for row in rows
                if row["number"] not in {item["number"] for item in shot_by_seg.values()}
            ],
            "segments_without_shot_row": [
                seg["id"] for seg in segments if seg["id"] not in shot_by_seg
            ],
        },
    }


def write_prompt_set(path: Path = OUT_PATH) -> dict[str, Any]:
    prompt_set = build_prompt_set()
    report = prompt_set.pop("_match_report")
    path.write_text(json.dumps(prompt_set, indent=2) + "\n", encoding="utf-8")
    prompt_set["_match_report"] = report
    return prompt_set


def main() -> int:
    prompt_set = write_prompt_set()
    report = prompt_set["_match_report"]
    print(
        f"segments={report['segments']} shot_rows={report['shot_list_rows']} "
        f"shot_matched={report['shot_list_matched']} specimens={report['specimens']} "
        f"specimens_matched={report['specimens_matched']}"
    )
    print(f"wrote {OUT_PATH}")
    if report["unmatched_shot_rows"]:
        print("unmatched § 7.7 rows:")
        for line in report["unmatched_shot_rows"]:
            print(f"  {line}")
    print(f"segments without a § 7.7 row: {len(report['segments_without_shot_row'])}")
    journal = PROJECT_ROOT / "build" / "journal"
    missing = [
        shot["journal_rel"]
        for shot in prompt_set["shots"]
        if not (journal / shot["journal_rel"]).is_dir()
    ]
    print(f"segment dirs missing from build/journal: {len(missing)}")
    for rel in missing[:20]:
        print(f"  {rel}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
