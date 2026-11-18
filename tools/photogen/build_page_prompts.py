#!/usr/bin/env python3
"""One Framing C prompt per desk-frame segment on the three packed days.

A frame segment is the page he is reading or writing. The three days are
10 Aug, 22 Oct and 30 Dec 2025 (1595 in the world). Each segment holds several
timed frames. This builder picks the one a viewer would take as the segment's
picture, and writes a prompt that shows that page from his eye.

The page's own words never enter the prompt. Secretary handwriting, or the
print a bill, almanac or book would carry, is texture: too small, soft or
angled to read.
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
SAMPLE_PROMPTS = PHOTOGEN_DIR / "prompts_sample_round.json"
OUT_PATH = PHOTOGEN_DIR / "prompts_pages.json"

if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import converter  # noqa: E402

DAY_FILES = (
    "content/weeks/2025-08-10/merged/2025-08-10.md",
    "content/weeks/2025-10-19/merged/2025-10-22.md",
    "content/weeks/2025-12-28/merged/2025-12-30.md",
)

# Print, not secretary handwriting. The request's count: bill 5, almanac 5, book 2.
PRINTED = {"bill", "almanac", "book"}

# Name the material, not a script the model will letter onto the page.
# The first pass wrote "Elizabethan Secretary handwriting" and "Penny Almanac"
# because those phrases were in the prompt.
SCRIPT = {
    "draft": (
        "Foul paper, a quill, and iron-gall ink. Any marks are out-of-focus loops and blots. "
        "Not printed type."
    ),
    "tables": (
        "One small erasable leaf in a stiff pocket writing-tables, marked with a plain brass point. "
        "The marks are faint or rubbed, and out of focus. Not a modern pen, and not printed type."
    ),
    "letter": (
        "A single letter sheet. Quill and iron-gall ink, out-of-focus loops and blots. Not printed type."
    ),
    "part": (
        "A long narrow parchment strip with one long rule. Ink is out-of-focus loops and blots. "
        "Not printed type."
    ),
    "ledger": (
        "A ruled account book. Any figure is an ink smudge, not a numeral. Marks are out of focus. "
        "Not printed type."
    ),
    "bill": (
        "A sheet nailed to a wooden post. The print is broken black shapes, too soft to read. "
        "No heading. Not modern type."
    ),
    "almanac": (
        "A small cheap printed booklet. The print is broken black shapes, too soft to read, "
        "with a few ink blots in the margin. No heading. If the scene says it is shut, "
        "the cover has no words."
    ),
    "book": (
        "A printed book lying open. The type is old and too soft to read. "
        "Any mark of his is an ink blot. No heading."
    ),
}

CROPS = (
    "Close, from his eyes looking down, about a forearm from the page. The sheet fills the frame and the writing is soft.",
    "A little farther back: the page and a margin of wood around it, still from his eyes looking down.",
    "He has leaned in. The near corner of the sheet is closer than the far corner, and the far lines dissolve.",
    "Along the sheet from the near edge, so the lines run away from the lens and cannot be read.",
    "He has straightened. More of the board is in frame, the page smaller, the writing only a texture.",
)

BILL_CROPS = (
    "He stands close to the post. The bill fills the frame. The type is too soft to read.",
    "A half-step closer. Nail-heads, cockled paper, frost or weather on the wood. The type is still not readable.",
    "He has stepped back. The bill is smaller, the street is in the frame, and the words are gone.",
)

SHIFT = (
    "The page is the brightest thing in the frame.",
    "A little more of the board is in shadow than a moment ago.",
    "The light has moved a hand's breadth across the sheet.",
    "The near edge of the paper is brighter than the far edge.",
)

# (date, HH:MM) -> timed-frame index, where the score picked a door or a wide room
# and another timed frame is the page.
# First vision pass failed these shot indexes on lettering, a modern object,
# an extra hand, or the wrong scene. The seed shift makes the second picture
# a different draw. Passing shots keep 159500 + index.
REGEN_SEED = {
    1, 4, 5, 6, 10, 11, 12, 13, 16, 18, 19, 26, 27, 31, 32, 33, 34, 36, 37,
    39, 42, 46, 50, 51, 52, 53, 56, 58, 59, 61, 63, 64, 72, 74, 75,
}

OVERRIDES: dict[tuple[str, str], int] = {
    ("2025-08-10", "08:49"): 0,
    ("2025-12-30", "11:36"): 0,
    ("2025-12-30", "15:30"): 0,
}

# Names and titles the picture must not spell. The scene keeps the object.
SCRUB = (
    (
        "The Chaucer open on the desk at the Knight's Tale",
        "The printed book lies open on the desk",
    ),
    (
        "The two young men at the window are further on, and he does not turn to them.",
        "The page is not turned.",
    ),
    ("Humphrey's secretary hand sets", "Another man's right hand, face out of frame, sets"),
    ("Humphrey's hand", "Another man's hand"),
    ("onto York's strip", "onto the first parchment strip"),
    ("York's roll", "the first roll"),
    ("the Queen's entrance", "the next entrance"),
    ("the Queen's roll", "the third roll"),
    ("at the Knight's Tale", "at an old printed tale"),
    ("Knight's Tale", "an old printed tale"),
    ("the shut Chaucer", "the printed book, shut"),
    ("The Chaucer", "The printed book"),
    ("the Chaucer", "the printed book"),
    ("Chaucer", "the printed book"),
    ("Curtain Close", "the lane"),
    ("a Masters of Defence prize", "a fencing prize"),
    ("St Helen's", "the close"),
    ("Gib is", "The cat is"),
    ("Gib", "the cat"),
    ("The penny almanac", "The small printed booklet"),
    ("the penny almanac", "the small printed booklet"),
    ("The almanac closed", "The booklet is shut"),
    ("The printed month", "The printed leaf"),
    ("the printed month", "the printed leaf"),
    ("One title, large.", "The largest shapes are too soft to read."),
    ("The pen is poised.", "The pen lies on the sheet. No hand is in the frame."),
    (
        "sets the full closing words onto the first parchment strip, repeats them at the head of the next entrance, and sets the small winter sign",
        "sets ink on the first parchment strip, repeats a blot at the head of the next strip, and sets a small mark",
    ),
)

PAGE_NOUNS = (
    "sheet", "leaf", "page", "bill", "book", "roll", "tables", "almanac",
    "letter", "paper", "parchment", "folio",
)

STOP = {
    "that", "with", "from", "this", "have", "been", "were", "them", "they",
    "your", "into", "over", "under", "still", "where", "what", "when", "then",
    "than", "only", "does", "hand", "face", "page", "sheet", "leaf", "line",
    "lines", "paper", "same", "back", "down", "left", "does",
}


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in STOP}


def _jaccard(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _hhmm(offset_sec: int) -> str:
    return f"{offset_sec // 60:02d}:{offset_sec % 60:02d}"


def _clock(hhmm: str) -> float:
    hour, minute = hhmm.split(":")
    return int(hour) + int(minute) / 60.0


def light_clause(date: str, hhmm: str, place: str, run_index: int) -> str:
    """Daylight or flame for this hour, plus a small shift so a run does not repeat."""
    month = int(date[5:7])
    t = _clock(hhmm)
    shift = SHIFT[run_index % len(SHIFT)]
    if place == "fields_printing_house":
        base = "Firelight only, from a small sea-coal fire. Shadows stay deep. No daylight, and no candle unless the scene names one."
    elif place in ("bishopsgate", "the_curtain"):
        if month == 12:
            base = "Out of doors on a December afternoon. Thin cold daylight, frost on the wood, mud in the street. No lantern is lit."
        else:
            base = "Out of doors in late October. Thin daylight, a wooden post, no candle and no lantern."
    elif place == "the_theatre":
        base = "Inside the tiring-house. Cool daylight from the yard door, no candle. The pine trestle is the brightest plane."
    elif month == 12 and t < 8:
        base = "Before full day at the end of December. One tallow candle, and a grey frost-light in the west panes. Most of the room is dark."
    elif month == 12 and t < 15:
        base = "A low December sun through small panes, pale and cold. No candle."
    elif month == 12 and t < 17:
        base = "The December light is leaving the desk. The panes are grey. No candle is lit yet."
    elif month == 12:
        base = "After dark. One tallow candle close to the page. The rest of the chamber is dark. No daylight left."
    elif month == 10 and t < 9:
        base = "A grey October morning through the west window. No sun on the page, and no candle."
    elif month == 10 and t < 17:
        base = "Thin October daylight, cool, through small panes. No candle."
    elif month == 10:
        base = "After dark in October. One short tallow candle. Deep shadow past the page."
    elif place == "henley_street" and t < 9:
        base = "An August morning under the apple trees, on the orchard bench. Dappled sun, cool shade on the paper, dew still in the shade. No candle."
    else:
        base = "An August morning indoors, soft daylight from a casement. No candle."
    return f"{base} {shift}"


def crop_clause(surface: str, run_index: int) -> str:
    if surface == "bill":
        return BILL_CROPS[run_index % len(BILL_CROPS)]
    return CROPS[run_index % len(CROPS)]


def where_clause(date: str, place: str, surface: str) -> str:
    month = int(date[5:7])
    if place == "henley_street" and surface == "draft":
        return "Stratford-upon-Avon, an August morning, the orchard bench behind the house in Henley Street: a plank with a knot-hole, an inkhorn, quills, a stone used to weight the sheets."
    if place == "henley_street":
        return "Stratford-upon-Avon, an August morning, the hall of the house in Henley Street, a plain oak table."
    if place == "the_theatre":
        return "The Theatre in Shoreditch, an October day, the players' side: a pine trestle, parchment, a lead weight."
    if place == "the_curtain":
        return "Outside the Curtain playhouse, Shoreditch, an October day."
    if place == "bishopsgate":
        return "Bishopsgate Street, London, a December afternoon."
    if place == "fields_printing_house":
        return "A printer's house in London, a December evening: an oak settle, a small fire, pewter cups."
    if month == 10:
        return "His lodging chamber above a Bishopsgate close, London, an October day. Timber, lime plaster, a trestle desk, a west window."
    return "His lodging chamber above a Bishopsgate close, London, the last days of December. Timber, lime plaster, a trestle desk, frost on the west panes."


def scrub_visual(visual: str) -> str:
    """Drop his body from the scene, and any name the picture would try to spell."""
    if "Masters of Defence" in visual:
        return "A damp black-letter bill nailed to the outer gatepost. The type is a texture. No face."
    text = visual.strip()
    for old, new in SCRUB:
        text = text.replace(old, new)
    text = re.sub(r"^Walking .+? he pauses by ", "", text)
    kept: list[str] = []
    for sentence in re.split(r"(?<=\.)\s+", text):
        if re.match(r"(He|She) ", sentence):
            continue
        kept.append(sentence.strip())
    cleaned = " ".join(s for s in kept if s).strip()
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned or text


def pick_frame(seg: converter.SegmentSpec, prev_visual: str, prev_index: int) -> tuple[int, converter.FrameItem, str]:
    forced = OVERRIDES.get((seg.day_iso, seg.start_hhmm))
    if forced is not None:
        frame = seg.frames[forced]
        return forced, frame, "named picture for this segment"
    sense = _tokens(f"{seg.heading_title} {seg.sense_summary}")
    best: tuple[float, int] | None = None
    for index, frame in enumerate(seg.frames):
        vis = f"{frame.label} {frame.visual}"
        score = 2.0 * len(sense & _tokens(vis))
        score += min(len(frame.visual), 220) / 120.0
        if any(noun in frame.visual.lower() for noun in PAGE_NOUNS):
            score += 3.0
        if frame.label.lower().startswith("the same"):
            score -= 0.5
        if len(seg.frames) > 1 and index == prev_index:
            score -= 1.25
        if prev_visual and _jaccard(frame.visual, prev_visual) > 0.45:
            score -= 2.5
        if best is None or score > best[0]:
            best = (score, index)
    assert best is not None
    index = best[1]
    return index, seg.frames[index], "the timed frame that carries this segment's picture"


def subject_prompt(seg: converter.SegmentSpec, frame: converter.FrameItem, run_index: int) -> str:
    script = SCRIPT[seg.surface or ""]
    scene = scrub_visual(frame.visual)
    blocks = [
        "What his eye holds: the page he is reading or writing, from about 5 ft 7 in, not a portrait and not a view of the room for its own sake.",
        where_clause(seg.day_iso, seg.place, seg.surface or ""),
        light_clause(seg.day_iso, seg.start_hhmm, seg.place, run_index),
        crop_clause(seg.surface or "", run_index),
        f"Scene: {scene}",
        script,
        (
            "Any mark is out of focus: loops and blots only. "
            "No glyph a person could read, no heading, no numeral, "
            "not on the page, not on a sheet nailed up, not on a spine, not in a margin."
        ),
        "Do not draw the man whose eyes these are. Show only what is in front of him.",
        (
            "A person's hand or thumb appears only if the scene names one. "
            "If it names one, show only that one hand, with no face and no reflection. "
            "Do not add a second hand. "
            "If the scene says the hand has left, or that no hand is there, show none. "
            "Never his face, never a mirror, never his reflection, never his shadow. "
            "Nobody looks into the lens."
        ),
        (
            "Where the scene says the leaf is blank, shut, or closed, that part stays empty."
            if re.search(r"\b(blank|shut|closed)\b", scene, re.I)
            else "Filled pages stay filled only with out-of-focus blots."
        ),
        (
            "Oak, pine, lime plaster, wool, linen, parchment, tallow, iron. "
            "Light is only sun, frost-light, candle, or fire. "
            "This is a phone picture of that year, not a painting and not an aged photograph."
        ),
    ]
    return "\n\n".join(blocks)


def framing_c() -> tuple[dict[str, Any], dict[str, Any]]:
    sample = json.loads(SAMPLE_PROMPTS.read_text(encoding="utf-8"))
    framing = next(item for item in sample["framings"] if item["id"] == "C")
    built = dict(framing)
    # The year prompts append the sample-round guards. Keep the same lens.
    year = json.loads((PHOTOGEN_DIR / "prompts_year.json").read_text(encoding="utf-8"))
    year_framing = next(item for item in year["framings"] if item["id"] == "C")
    # The year digits were lettered onto a page in the first pass.
    built["instruction"] = year_framing["instruction"].replace("1595", "that year")
    return built, sample["default_parameters"]


def collect() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rel in DAY_FILES:
        path = PROJECT_ROOT / rel
        day = converter.parse_day_markdown(path)
        for seg in day.segments:
            if seg.kind != "frame":
                continue
            if seg.surface not in SCRIPT:
                raise SystemExit(f"unexpected surface {seg.surface} on {seg.day_iso} {seg.start_hhmm}")
            rows.append(
                {
                    "seg": seg,
                    "day_file": rel,
                    "day_type": day.day_type,
                }
            )
    rows.sort(key=lambda item: (item["seg"].day_iso, item["seg"].start_hhmm, item["seg"].segment_key))
    return rows


def build_prompt_set() -> dict[str, Any]:
    framing, parameters = framing_c()
    rows = collect()
    shots = []
    prev_key: tuple[str, str, str] | None = None
    prev_visual = ""
    prev_index = -1
    run_index = 0
    leaked: list[str] = []
    for n, row in enumerate(rows, start=1):
        seg: converter.SegmentSpec = row["seg"]
        group = (seg.day_iso, seg.surface or "", seg.place)
        if group != prev_key:
            run_index = 0
            prev_visual = ""
            prev_index = -1
        index, frame, why = pick_frame(seg, prev_visual, prev_index)
        prompt = subject_prompt(seg, frame, run_index)
        for other in seg.frames:
            chunk = other.text.strip()
            if len(chunk) >= 16 and chunk in prompt:
                leaked.append(f"{seg.day_iso} {seg.start_hhmm}: {chunk[:40]}")
        shots.append(
            {
                "shot_index": n,
                "id": f"f{n:03d}",
                "date": seg.day_iso,
                "time": seg.start_hhmm,
                "title": seg.heading_title,
                "place": seg.place,
                "surface": seg.surface,
                "segment_key": seg.segment_key,
                "day_key": seg.day_key,
                "journal_rel": f"chronicle/{seg.day_key}/desk/{seg.segment_key}",
                "entries": ", ".join(seg.entries),
                "day_file": row["day_file"],
                "day_type": row["day_type"],
                "duration_min": seg.duration_min,
                "timed_frames": len(seg.frames),
                "chosen_frame": {
                    "index": index,
                    "offset": _hhmm(frame.offset_sec),
                    "label": frame.label,
                    "why": why,
                },
                "photo_text": prompt,
                "people_present": bool(re.search(r"\b(hand|thumb|finger)\b", frame.visual, re.I)),
                "subject_prompt": prompt,
                "parameters": {"seed": 159500 + n + (1000 if n in REGEN_SEED else 0)},
            }
        )
        prev_key = group
        prev_visual = frame.visual
        prev_index = index
        run_index += 1
    if leaked:
        raise SystemExit("page words leaked into a prompt:\n" + "\n".join(leaked))
    printed = sum(1 for shot in shots if shot["surface"] in PRINTED)
    by_surface: dict[str, int] = {}
    for shot in shots:
        by_surface[shot["surface"]] = by_surface.get(shot["surface"], 0) + 1
    return {
        "schema_version": 1,
        "description": (
            "One Framing C image for each desk-frame segment on the william journal's "
            "three packed days (2025-08-10, 2025-10-22, 2025-12-30). "
            "Each shot names the timed frame chosen as that segment's picture. "
            "Framing C was chosen on 2026-11-17."
        ),
        "default_model": "gemini-nano-banana-2.1",
        "default_parameters": parameters,
        "framings": [framing],
        "shots": shots,
        "_counts": {
            "segments": len(shots),
            "printed": printed,
            "by_surface": by_surface,
            "by_day": {
                day: sum(1 for shot in shots if shot["date"] == day)
                for day in ("2025-08-10", "2025-10-22", "2025-12-30")
            },
        },
    }


def write_prompt_set(path: Path = OUT_PATH) -> dict[str, Any]:
    prompt_set = build_prompt_set()
    counts = prompt_set.pop("_counts")
    path.write_text(json.dumps(prompt_set, indent=2) + "\n", encoding="utf-8")
    prompt_set["_counts"] = counts
    return prompt_set


def main() -> int:
    prompt_set = write_prompt_set()
    counts = prompt_set["_counts"]
    print(
        f"segments={counts['segments']} printed={counts['printed']} "
        f"days={counts['by_day']} surfaces={counts['by_surface']}"
    )
    print(f"wrote {OUT_PATH}")
    for shot in prompt_set["shots"]:
        chosen = shot["chosen_frame"]
        print(
            f"{shot['shot_index']:02d} {shot['date']} {shot['time']} {shot['surface']:8} "
            f"f{chosen['index']}/{shot['timed_frames']} +{chosen['offset']} {chosen['label']}"
        )
    expected = {"2025-08-10": 6, "2025-10-22": 32, "2025-12-30": 37}
    if counts["by_day"] != expected or counts["segments"] != 75 or counts["printed"] != 12:
        return 1
    if counts["by_surface"].get("bill") != 5 or counts["by_surface"].get("almanac") != 5 or counts["by_surface"].get("book") != 2:
        return 1
    keys = [f"{shot['date']}/{shot['segment_key']}" for shot in prompt_set["shots"]]
    if len(keys) != len(set(keys)):
        print("duplicate segment keys", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
