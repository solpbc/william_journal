# SPDX-License-Identifier: CC-BY-NC-4.0
# Copyright (c) 2026 sol pbc

"""Mechanical converter from FORMAT.md content files to solstone-journal artifacts."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import sys
import time as time_mod
from typing import Any
import zlib

from zoneinfo import ZoneInfo

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from backdrop import (  # type: ignore[import-not-found]
        ALL_ENTITIES,
        CAST_BY_SLUG,
        DEFAULT_CALENDAR_JSON,
        LONDON_TZ,
        PROJECT_ROOT,
        SETUP_COMPLETED_AT_MS,
        _deterministic_cid,
        generate_backdrop,
        write_calendar_backdrop,
        write_device_descriptions,
    )
    from contracts import (  # type: ignore[import-not-found]
        DEFAULT_SOLSTONE_REPO,
        ContractRegistry,
        judge_weekly_reflection,
        validate_stream_record,
    )
    from stamp import stamp_journal_tree  # type: ignore[import-not-found]
    from world_data import (  # type: ignore[import-not-found]
        CANON_CAST,
        CANON_PLACES,
        FACET_DEFINITIONS,
        FACET_EXTRA_ENTITIES,
    )
else:
    from .backdrop import (
        ALL_ENTITIES,
        CAST_BY_SLUG,
        DEFAULT_CALENDAR_JSON,
        LONDON_TZ,
        PROJECT_ROOT,
        SETUP_COMPLETED_AT_MS,
        _deterministic_cid,
        generate_backdrop,
        write_calendar_backdrop,
        write_device_descriptions,
    )
    from .contracts import (
        DEFAULT_SOLSTONE_REPO,
        ContractRegistry,
        judge_weekly_reflection,
        validate_stream_record,
    )
    from .stamp import stamp_journal_tree
    from .world_data import CANON_CAST, CANON_PLACES, FACET_DEFINITIONS, FACET_EXTRA_ENTITIES

CAST_ONLY_BY_SLUG = {ent.slug: ent for ent in CANON_CAST}
FACET_ENTITIES_BY_SLUG = {ent.slug: ent for ent in FACET_EXTRA_ENTITIES}
PLACES_BY_SLUG = CANON_PLACES
VALID_FACETS = frozenset(FACET_DEFINITIONS.keys())
JOURNAL_YEAR_START = date(2025, 1, 1)

CALENDAR_EVENTS_BY_ID: dict[str, dict[str, Any]] = {}
if DEFAULT_CALENDAR_JSON.is_file():
    for _cal_ev in json.loads(DEFAULT_CALENDAR_JSON.read_text(encoding="utf-8")).get("events", []):
        if isinstance(_cal_ev, dict) and "id" in _cal_ev:
            CALENDAR_EVENTS_BY_ID[_cal_ev["id"]] = _cal_ev


def _validate_calendar_ids(calendar_ids: list[str], day_iso: str, label: str) -> None:
    """Validate `- calendar:` IDs against `calendar/merged/calendar.json`, matching `content/lint.py`."""
    if not CALENDAR_EVENTS_BY_ID:
        return
    for cid in calendar_ids:
        if cid not in CALENDAR_EVENTS_BY_ID:
            raise ContentFormatError(f"{label}: calendar id {cid} does not exist")
        ev = CALENDAR_EVENTS_BY_ID[cid]
        if ev.get("date") != day_iso and not ev.get("end_date") and not ev.get("rrule"):
            raise ContentFormatError(f"{label}: {cid} is dated {ev.get('date')}")


def london_offset_str(d: date) -> str:
    dt = datetime(d.year, d.month, d.day, 12, 0, 0, tzinfo=LONDON_TZ)
    off = dt.strftime("%z")
    return f"{off[:3]}:{off[3:]}"


def to_epoch_ms(iso_str: str) -> int:
    dt = datetime.fromisoformat(iso_str)
    return int(dt.timestamp() * 1000)


STREAM_CONFIG_BY_KIND: dict[str, tuple[str, str, str | None]] = {
    "meeting": ("talk", "observer", "microphone"),
    "call": ("calls", "observer", "call"),
    "memo": ("memos", "observer", "voice_memo"),
    "note": ("obsidian", "observer", "obsidian"),
    "frame": ("desk", "observer", "screen"),
    "photo": ("import.image", "observer", None),
}

VALID_CONTENT_TYPES = {
    "meeting",
    "coding",
    "browsing",
    "email",
    "messaging",
    "ai_conversation",
    "writing",
    "reading",
    "video",
    "media",
    "gaming",
    "social",
    "planning",
    "productivity",
    "terminal",
    "design",
    "music",
    "idle",
}

VALID_DENSITIES = {"active", "low_change", "idle"}
VALID_RELATION_KINDS = {
    "works-with",
    "works-at",
    "reports-to",
    "family-of",
    "knows",
    "uses",
    "created",
    "other",
}


class ContentFormatError(ValueError):
    """Raised when a FORMAT.md file is missing a required judgment value or violates format rules."""


@dataclass(frozen=True)
class TranscriptLine:
    offset_sec: int
    speaker: str | None
    text: str
    is_stage_direction: bool = False


@dataclass(frozen=True)
class FrameItem:
    offset_sec: int
    label: str
    visual: str
    text: str


@dataclass(frozen=True)
class MentionedItem:
    name: str
    entity_type: str  # Company | Project | Tool


@dataclass(frozen=True)
class RelationItem:
    from_slug: str
    to_slug: str
    kind: str
    note: str
    quote: str | None


@dataclass
class SegmentSpec:
    day_iso: str
    start_hhmm: str
    duration_min: int
    kind: str
    heading_title: str
    place: str
    facet: str
    content_type: str
    density: str
    surface: str | None
    people: list[tuple[str, str]]  # (slug, raw_role)
    entries: list[str]
    calendar_ids: list[str]
    transcript_lines: list[TranscriptLine] = field(default_factory=list)
    page_text: str = ""
    frames: list[FrameItem] = field(default_factory=list)
    photo_text: str = ""
    sense_summary: str = ""
    sense_topics: list[str] = field(default_factory=list)
    sense_quotes: list[tuple[str, str]] = field(default_factory=list)
    also_mentioned: list[MentionedItem] = field(default_factory=list)
    activity_title: str = ""
    activity_story: str = ""
    participation: dict[str, str] = field(default_factory=dict)
    relations: list[RelationItem] = field(default_factory=list)
    # FORMAT.md "Continuing an activity": the heading time of the segment that
    # opens this segment's activity. A continuation has no Activity of its own.
    continues: str | None = None
    head: "SegmentSpec | None" = None

    @property
    def activity_head(self) -> "SegmentSpec":
        """The segment whose activity this segment belongs to (itself, unless it continues one)."""
        return self.head if self.head is not None else self

    @property
    def day_key(self) -> str:
        return self.day_iso.replace("-", "")

    @property
    def duration_sec(self) -> int:
        return self.duration_min * 60

    @property
    def segment_key(self) -> str:
        clock = self._clock_hhmmss()
        # A phone photo uses the importer's id (`HHMMSS_0`). Other kinds keep
        # the duration suffix the rest of the journal already uses.
        if self.kind == "photo":
            return f"{clock}_0"
        return f"{clock}_{self.duration_sec}"

    @property
    def legacy_screenshot_key(self) -> str:
        """The old screenshots-segment id, used only to find bytes already on disk."""
        return f"{self._clock_hhmmss()}_{self.duration_sec}"

    def _clock_hhmmss(self) -> str:
        hh, mm = self.start_hhmm.split(":")
        return f"{int(hh):02d}{int(mm):02d}00"

    @property
    def stream_name(self) -> str:
        return STREAM_CONFIG_BY_KIND[self.kind][0]

    @property
    def activity_id(self) -> str:
        return f"{self.kind}_{self.segment_key}"


@dataclass
class DaySpec:
    day_iso: str
    wakes: str
    sleeps: str
    day_type: str
    calendar_ids: list[str]
    entries: list[str]
    pulse_title: str
    pulse_one_sentence: str
    pulse_details: str
    briefing_coverage: str
    briefing_bullets: list[str]
    segments: list[SegmentSpec]

    @property
    def day_key(self) -> str:
        return self.day_iso.replace("-", "")


@dataclass
class WeekSpec:
    sunday_iso: str
    reflection_markdown: str
    memories: list[tuple[str, str]]  # (day_iso, text)
    said: list[tuple[str, str, str, str, str]]  # (day_iso, hhmm, kind, speaker_slug, quote)
    observations: list[tuple[str, str, str]]  # (entity_slug, day_iso, text)


def _strip_html_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def _entity_display_name(slug: str) -> str:
    if slug.startswith("(") and slug.endswith(")"):
        return slug[1:-1].strip()
    if slug in CAST_BY_SLUG:
        return CAST_BY_SLUG[slug].name
    if slug in FACET_ENTITIES_BY_SLUG:
        return FACET_ENTITIES_BY_SLUG[slug].name
    return slug


def _parse_mmss(mmss: str, label: str) -> int:
    m = re.fullmatch(r"(\d{2}):(\d{2})", mmss.strip())
    if not m:
        raise ContentFormatError(f"{label}: invalid timestamp [{mmss!r}], expected [MM:SS]")
    return int(m.group(1)) * 60 + int(m.group(2))


PHOTO_INSTALL_MANIFEST = PROJECT_ROOT / "photos" / "year" / "install.json"
PAGE_INSTALL_MANIFEST = PROJECT_ROOT / "photos" / "pages" / "install.json"
AUDIO_INSTALL_MANIFEST = PROJECT_ROOT / "audio" / "install.json"
PHOTO_JPEG = "original.jpg"
LEGACY_PHOTO_JPEG = "screenshot_screen.jpg"
PAGE_JPEG = "page_screen.jpg"
AUDIO_FLAC = "audio.flac"
_REAL_PHOTO_MIN_BYTES = 2000
_REAL_AUDIO_MIN_BYTES = 1024
# `triage.rs` RULESET_VERSION at the pinned journal. `image_default` is the
# manual-image fallback and stores kind `photos` (`rules.rs`).
PHOTO_IMPORT_KIND = {
    "kind": "photos",
    "reasons": ["image_default"],
    "ruleset_version": 5,
}
_JPEG_SOF_MARKERS = {
    0xC0, 0xC1, 0xC2, 0xC3,
    0xC5, 0xC6, 0xC7,
    0xC9, 0xCA, 0xCB,
    0xCD, 0xCE, 0xCF,
}


def _load_photo_install_map(manifest_path: Path | None = None) -> dict[str, Path]:
    """Map `YYYY-MM-DD/<segment_key>` to a committed JPEG, if the year manifest exists."""
    path = manifest_path if manifest_path is not None else PHOTO_INSTALL_MANIFEST
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    mapped: dict[str, Path] = {}
    for key, rel in (payload.get("by_segment") or {}).items():
        if not isinstance(key, str) or not isinstance(rel, str):
            continue
        source = Path(rel)
        if not source.is_absolute():
            source = PROJECT_ROOT / rel
        mapped[key] = source
    return mapped


def _is_real_photo_bytes(data: bytes, placeholder: bytes) -> bool:
    return (
        data.startswith(b"\xff\xd8")
        and data.endswith(b"\xff\xd9")
        and len(data) >= _REAL_PHOTO_MIN_BYTES
        and data != placeholder
    )


def _photo_byte_candidates(day_dir: Path, seg: SegmentSpec) -> list[Path]:
    """Where a still may already be, newest layout first.

    The first reconvert still finds the JPEG under the old screenshots segment.
    """
    if seg.kind == "photo":
        return [
            day_dir / "import.image" / seg.segment_key / PHOTO_JPEG,
            day_dir / "screenshots" / seg.legacy_screenshot_key / LEGACY_PHOTO_JPEG,
        ]
    return [day_dir / seg.stream_name / seg.segment_key / PAGE_JPEG]


def _preserved_photo_bytes(day_dir: Path, day_spec: DaySpec) -> dict[tuple[str, str], bytes]:
    """Real JPEGs already on disk for this day, keyed by stream and segment.

    A convert removes the day's stream directories before rewriting them, so the
    bytes have to be read first or a re-convert blanks every photo.
    """
    preserved: dict[tuple[str, str], bytes] = {}
    for seg in day_spec.segments:
        if seg.kind not in ("photo", "frame"):
            continue
        seed = f"{seg.day_iso}:{seg.segment_key}:{seg.heading_title}"
        placeholder = _make_minimal_jpeg(seed)
        for jpg in _photo_byte_candidates(day_dir, seg):
            if not jpg.is_file():
                continue
            data = jpg.read_bytes()
            if _is_real_photo_bytes(data, placeholder):
                preserved[seg.stream_name, seg.segment_key] = data
                break
    return preserved


def _is_real_audio_bytes(data: bytes) -> bool:
    return data.startswith(b"fLaC") and len(data) >= _REAL_AUDIO_MIN_BYTES


def _load_audio_install_timings(manifest_path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Map `YYYYMMDD/<stream>/<segment_key>` to aligned duration/turn timings from `audio/install.json`."""
    path = manifest_path if manifest_path is not None else AUDIO_INSTALL_MANIFEST
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    by_seg = payload.get("by_segment")
    if not isinstance(by_seg, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for key, entry in by_seg.items():
        if isinstance(key, str) and isinstance(entry, dict) and isinstance(entry.get("turns"), list):
            out[key] = {
                "duration": float(entry["duration_s"]),
                "turns": {
                    int(t["sentence_id"]): {
                        "start": str(t["start"]),
                        "timing": {
                            "start": float(t["timing"]["start"]),
                            "end": float(t["timing"]["end"]),
                        },
                    }
                    for t in entry["turns"]
                    if isinstance(t, dict) and "sentence_id" in t and "timing" in t
                },
            }
    return out


def _read_audio_jsonl_timings(jsonl_path: Path) -> dict[str, Any] | None:
    if not jsonl_path.is_file():
        return None
    lines = [json.loads(ln) for ln in jsonl_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if len(lines) < 2 or not isinstance(lines[0], dict) or "duration" not in lines[0]:
        return None
    turns: dict[int, dict[str, Any]] = {}
    for rec in lines[1:]:
        if isinstance(rec, dict) and "sentence_id" in rec and "timing" in rec and "start" in rec:
            turns[int(rec["sentence_id"])] = {
                "start": str(rec["start"]),
                "timing": {
                    "start": float(rec["timing"]["start"]),
                    "end": float(rec["timing"]["end"]),
                },
            }
    return {"duration": float(lines[0]["duration"]), "turns": turns}


def _preserved_audio_state(
    day_dir: Path, day_spec: DaySpec
) -> dict[tuple[str, str], tuple[bytes, dict[str, Any] | None]]:
    """Real `audio.flac` bytes and aligned `audio.jsonl` timings already on disk for this day.

    A convert removes the day's stream directories before rewriting them, so real audio
    and its aligned per-turn timings must be read first or a re-convert wipes them.
    """
    preserved: dict[tuple[str, str], tuple[bytes, dict[str, Any] | None]] = {}
    for seg in day_spec.segments:
        if seg.kind not in ("meeting", "call", "memo"):
            continue
        seg_dir = day_dir / seg.stream_name / seg.segment_key
        flac_path = seg_dir / AUDIO_FLAC
        if not flac_path.is_file():
            continue
        data = flac_path.read_bytes()
        if _is_real_audio_bytes(data):
            preserved[seg.stream_name, seg.segment_key] = (
                data,
                _read_audio_jsonl_timings(seg_dir / "audio.jsonl"),
            )
    return preserved


def photo_jpeg_bytes(
    seg: SegmentSpec,
    dest_path: Path,
    manifest_path: Path | None = None,
    preserved: bytes | None = None,
) -> bytes:
    """Bytes to store as a photo or page segment's still.

    A real JPEG already at `dest_path`, or one captured before the day's stream
    directories were removed, is kept. Otherwise the corresponding install
    manifest is consulted. A photo with neither gets the deterministic 1x1 placeholder.
    A page with neither stays text-only and returns empty bytes.
    """
    seed = f"{seg.day_iso}:{seg.segment_key}:{seg.heading_title}"
    placeholder = _make_minimal_jpeg(seed)
    if dest_path.is_file():
        existing = dest_path.read_bytes()
        if _is_real_photo_bytes(existing, placeholder):
            return existing
    if preserved is not None and _is_real_photo_bytes(preserved, placeholder):
        return preserved
    if manifest_path is None and seg.kind == "frame":
        manifest_path = PAGE_INSTALL_MANIFEST
    install_map = _load_photo_install_map(manifest_path)
    keys = [f"{seg.day_iso}/{seg.segment_key}"]
    if seg.kind == "photo":
        legacy_key = f"{seg.day_iso}/{seg.legacy_screenshot_key}"
        if legacy_key not in keys:
            keys.append(legacy_key)
    for key in keys:
        source = install_map.get(key)
        if source is not None and source.is_file():
            incoming = source.read_bytes()
            if _is_real_photo_bytes(incoming, placeholder):
                return incoming
    return placeholder if seg.kind == "photo" else b""


def _make_minimal_jpeg(seed_text: str) -> bytes:
    """Return a valid, deterministic 1x1 baseline JPEG image so ImageReader reads dimensions."""
    # Standard minimal valid 1x1 baseline YCbCr JPEG bytes; last scan byte varied deterministically if needed
    base = bytes.fromhex(
        "ffd8ffe000104a46494600010101006000600000"
        "ffdb004300"
        "080606070605080707070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c1c2837292c30313434341f27393d38323c2e333432"
        "ffc0000b080001000101011100"
        "ffc4001f0000010501010101010100000000000000000102030405060708090a0b"
        "ffc400b5100002010303020403050504040000017d01020300041105122131410613516107227114328191a1082342b1c11552d1f02433627282090a161718191a25262728292a3435363738393a434445464748494a535455565758595a636465666768696a737475767778797a838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2f3f4f5f6f7f8f9fa"
        "ffda0008010100003f00fbf5ffd9"
    )
    # Embed a deterministic COM (0xFFFE) comment segment right before EOI so each photo has distinct bytes
    comment_bytes = seed_text.encode("utf-8")[:120]
    length = len(comment_bytes) + 2
    com_seg = b"\xff\xfe" + struct.pack(">H", length) + comment_bytes
    return base[:-2] + com_seg + b"\xff\xd9"


def london_offset_seconds_at(day_iso: str, hhmm: str) -> int:
    """Europe/London offset at that civil time, so the BST changeover hour is right."""
    hh, mm = [int(part) for part in hhmm.split(":")]
    year, month, day = [int(part) for part in day_iso.split("-")]
    dt = datetime(year, month, day, hh, mm, tzinfo=LONDON_TZ)
    offset = dt.utcoffset()
    if offset is None:
        raise ContentFormatError(f"{day_iso} {hhmm}: Europe/London has no offset")
    return int(offset.total_seconds())


def _jpeg_dimensions(data: bytes) -> tuple[int, int]:
    """Width and height from a JPEG SOF marker. No Pillow dependency at convert time."""
    if not data.startswith(b"\xff\xd8"):
        raise ContentFormatError("photo bytes are not a JPEG")
    index = 2
    limit = len(data)
    while index + 8 < limit:
        if data[index] != 0xFF:
            index += 1
            continue
        while index < limit and data[index] == 0xFF:
            index += 1
        if index >= limit:
            break
        marker = data[index]
        index += 1
        if marker in (0xD8, 0xD9, 0x01) or 0xD0 <= marker <= 0xD7:
            continue
        if index + 2 > limit:
            break
        length = int.from_bytes(data[index:index + 2], "big")
        if marker in _JPEG_SOF_MARKERS:
            if index + 7 > limit:
                break
            height = int.from_bytes(data[index + 3:index + 5], "big")
            width = int.from_bytes(data[index + 5:index + 7], "big")
            if width < 1 or height < 1:
                break
            return width, height
        if marker == 0xDA or length < 2:
            break
        index += length
    raise ContentFormatError("photo JPEG has no readable dimensions")


def _literal_markdown(text: str) -> str:
    """Match `solstone_core_format::markdown::literal_text` so a description renders as written."""
    out: list[str] = []
    for ch in text:
        if ch == "&":
            out.append("&amp;")
        elif ch == "<":
            out.append("&lt;")
        elif ch == ">":
            out.append("&gt;")
        elif ch.isascii() and not ch.isalnum() and not ch.isspace():
            out.append("\\")
            out.append(ch)
        else:
            out.append(ch)
    return "".join(out)


def _image_transcript(title: str, width: int, height: int, day_iso: str, description: str) -> str:
    """The importer's `render_image_markdown` for a described JPEG with no owner caption."""
    lines = [
        f"# {title}",
        "",
        "**Type:** Image",
        "**Format:** JPEG",
        f"**Dimensions:** {width}×{height}",
        f"**Date:** {day_iso}",
        "",
        "---",
        "",
        "> [image description — model-derived]",
    ]
    for line in description.split("\n"):
        lines.append(">" if line == "" else f"> {_literal_markdown(line)}")
    return "\n".join(lines).rstrip() + "\n"


def _write_photo_import_record(
    journal_dir: Path,
    seg: SegmentSpec,
    jpeg: bytes,
    file_mtime_sec: float,
) -> None:
    """Import-page record for one phone photo.

    `image_content_items` lists a photo only when `manifest.json` says
    `source_type: image` and `imported.json` carries a `segments` array.
    The publication shape is `solstone.import.publication.v2`.
    """
    hh, mm = [int(part) for part in seg.start_hhmm.split(":")]
    import_id = f"{seg.day_key}_{hh:02d}{mm:02d}00"
    import_dir = journal_dir / "imports" / import_id
    import_dir.mkdir(parents=True, exist_ok=True)
    transcript_rel = f"chronicle/{seg.day_key}/import.image/{seg.segment_key}/image_transcript.md"
    manifest = {
        "import_id": import_id,
        "source_type": "image",
        "source_hash": hashlib.sha256(jpeg).hexdigest(),
        "entry_count": 1,
        "days_affected": [seg.day_key],
        "files_created": [transcript_rel],
        "imported_at": f"{seg.day_iso}T{hh:02d}:{mm:02d}:00.000000",
        "imported_via": "mobile_share",
        "link_id": None,
        "observer_handle": None,
    }
    published = {
        "schema": "solstone.import.publication.v2",
        "status": "success",
        "segments": [
            {
                "day": seg.day_key,
                "segment": seg.segment_key,
                "stream": "import.image",
                "outcome": {
                    "status": "bound",
                    "prev_day": None,
                    "prev_segment": None,
                    "seq": 1,
                },
            }
        ],
        "indexing": {"queued": [], "declined": [], "errored": []},
        "day_markers": [{"day": seg.day_key, "outcome": {"status": "touched"}}],
    }
    for name, payload in (("manifest.json", manifest), ("imported.json", published)):
        path = import_dir / name
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        os.utime(path, (file_mtime_sec, file_mtime_sec))


def parse_day_markdown(path: Path) -> DaySpec:
    """Parse a day markdown file in `FORMAT.md` shape, failing loudly on missing fields."""
    raw = _strip_html_comments(path.read_text(encoding="utf-8"))
    stem = path.stem
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", stem):
        raise ContentFormatError(f"{path}: filename stem {stem!r} must be YYYY-MM-DD")

    # Split by H2 sections (`## ...`)
    lines = raw.splitlines()
    if not lines:
        raise ContentFormatError(f"{path}: file is empty")

    h2_indices: list[int] = [i for i, line in enumerate(lines) if line.startswith("## ")]
    if len(h2_indices) < 2:
        raise ContentFormatError(f"{path}: missing required '## Pulse' and '## Briefing for tomorrow morning' sections")

    header_lines = lines[: h2_indices[0]]
    wakes = ""
    sleeps = ""
    day_type = ""
    calendar_ids: list[str] = []
    entries: list[str] = []

    for hl in header_lines:
        s = hl.strip()
        if s.startswith("- wakes:"):
            m = re.match(r"^- wakes:\s*([a-z0-9_]+)\s*·\s*sleeps:\s*([a-z0-9_]+)\s*$", s)
            if not m:
                raise ContentFormatError(f"{path}: invalid wakes/sleeps line {s!r}")
            wakes, sleeps = m.group(1), m.group(2)
        elif s.startswith("- day type:"):
            day_type = s[len("- day type:") :].strip()
        elif s.startswith("- calendar:"):
            val = s[len("- calendar:") :].strip()
            calendar_ids = [] if val.lower() == "none" else [x.strip() for x in val.split(",") if x.strip()]
        elif s.startswith("- entries:"):
            val = s[len("- entries:") :].strip()
            entries = [] if val.lower() == "none" else [x.strip() for x in val.split(",") if x.strip()]

    if not wakes or not sleeps:
        raise ContentFormatError(f"{path}: missing '- wakes: <place> · sleeps: <place>' in day header")
    if wakes not in PLACES_BY_SLUG or sleeps not in PLACES_BY_SLUG:
        raise ContentFormatError(f"{path}: unknown wakes/sleeps place ({wakes!r}, {sleeps!r})")
    if not day_type:
        raise ContentFormatError(f"{path}: missing '- day type:' in day header")
    _validate_calendar_ids(calendar_ids, stem, str(path))

    pulse_title = ""
    pulse_one_sentence = ""
    pulse_details = ""
    briefing_coverage = ""
    briefing_bullets: list[str] = []
    segments: list[SegmentSpec] = []

    for idx_pos, start_idx in enumerate(h2_indices):
        end_idx = h2_indices[idx_pos + 1] if idx_pos + 1 < len(h2_indices) else len(lines)
        sec_heading = lines[start_idx][3:].strip()
        sec_body = lines[start_idx + 1 : end_idx]

        if sec_heading == "Pulse":
            for bl in sec_body:
                s = bl.strip()
                if s.startswith("- title:"):
                    pulse_title = s[len("- title:") :].strip()
                elif s.startswith("- one sentence:"):
                    pulse_one_sentence = s[len("- one sentence:") :].strip()
                elif s.startswith("- details:"):
                    pulse_details = s[len("- details:") :].strip()
        elif sec_heading == "Briefing for tomorrow morning":
            for bl in sec_body:
                s = bl.strip()
                if not s or (s.startswith("*") and s.endswith("*")):
                    continue
                if s.startswith("- coverage:"):
                    briefing_coverage = s[len("- coverage:") :].strip()
                elif s.startswith("- "):
                    bullet = s[2:].strip()
                    if bullet:
                        briefing_bullets.append(bullet)
        else:
            segments.append(_parse_segment_section(path, stem, sec_heading, sec_body))

    if not pulse_title or not pulse_one_sentence or not pulse_details:
        raise ContentFormatError(f"{path}: '## Pulse' requires non-empty title, one sentence, and details")
    if not briefing_coverage or not briefing_bullets:
        raise ContentFormatError(
            f"{path}: '## Briefing for tomorrow morning' requires non-empty coverage and at least one bullet"
        )
    if not segments:
        raise ContentFormatError(f"{path}: day file has no segments")
    _resolve_continuations(path, segments)
    assign_cross_midnight(path, segments)

    return DaySpec(
        day_iso=stem,
        wakes=wakes,
        sleeps=sleeps,
        day_type=day_type,
        calendar_ids=calendar_ids,
        entries=entries,
        pulse_title=pulse_title,
        pulse_one_sentence=pulse_one_sentence,
        pulse_details=pulse_details,
        briefing_coverage=briefing_coverage,
        briefing_bullets=briefing_bullets,
        segments=segments,
    )


def _parse_segment_section(
    path: Path,
    day_iso: str,
    heading: str,
    body_lines: list[str],
) -> SegmentSpec:
    label = f"{path.name} [{heading}]"
    m = re.match(r"^(\d{2}:\d{2})\s*·\s*(\d+)\s*min\s*·\s*([a-z]+)\s*·\s*(.+)$", heading)
    if not m:
        raise ContentFormatError(
            f"{label}: segment heading must match 'HH:MM · <N> min · <kind> · <title>'"
        )
    start_hhmm, dur_str, kind, heading_title = (
        m.group(1),
        m.group(2),
        m.group(3).strip(),
        m.group(4).strip(),
    )
    duration_min = int(dur_str)
    if duration_min <= 0:
        raise ContentFormatError(f"{label}: duration must be > 0 min")
    if kind not in STREAM_CONFIG_BY_KIND:
        raise ContentFormatError(f"{label}: unsupported segment kind {kind!r}")

    h3_indices = [i for i, line in enumerate(body_lines) if line.startswith("### ")]
    if not h3_indices:
        raise ContentFormatError(f"{label}: segment has no '### ' subsections")

    meta_lines = body_lines[: h3_indices[0]]
    meta: dict[str, str] = {}
    for ml in meta_lines:
        s = ml.strip()
        if not s:
            continue
        if not s.startswith("- ") or ":" not in s:
            raise ContentFormatError(f"{label}: invalid metadata line {s!r}")
        k, v = s[2:].split(":", 1)
        meta[k.strip()] = v.strip()

    for req_meta in ("place", "facet", "kind", "content type", "density", "people", "entries", "calendar"):
        if req_meta not in meta or not meta[req_meta]:
            raise ContentFormatError(f"{label}: missing required segment field '- {req_meta}:'")

    if meta["kind"] != kind:
        raise ContentFormatError(f"{label}: heading kind {kind!r} != metadata kind {meta['kind']!r}")
    place = meta["place"]
    if place not in PLACES_BY_SLUG:
        raise ContentFormatError(f"{label}: unknown place slug {place!r}")
    facet = meta["facet"]
    if facet not in VALID_FACETS:
        raise ContentFormatError(f"{label}: invalid facet {facet!r}, must be one of {VALID_FACETS}")
    content_type = meta["content type"]
    if content_type not in VALID_CONTENT_TYPES:
        if content_type == "conversation":
            content_type = "meeting" if kind in ("meeting", "call") else "social"
        elif content_type in ("work", "business", "rehearsal"):
            content_type = "meeting" if kind in ("meeting", "call") else "productivity"
        elif content_type in ("household", "meal"):
            content_type = "social" if kind in ("meeting", "call") else "productivity"
        elif content_type == "errand":
            content_type = "planning" if kind == "note" else "productivity"
        elif content_type in ("monologue", "note"):
            content_type = "writing" if facet == "writing" else "planning"
        else:
            raise ContentFormatError(f"{label}: invalid content type {content_type!r}")
    density = meta["density"]
    if density not in VALID_DENSITIES:
        raise ContentFormatError(f"{label}: invalid density {density!r}")
    continues = meta.get("continues")
    if continues is not None and not re.fullmatch(r"\d{2}:\d{2}", continues):
        raise ContentFormatError(f"{label}: '- continues:' must be a heading time HH:MM, got {continues!r}")
    surface = meta.get("surface")
    if kind == "frame" and not surface:
        raise ContentFormatError(f"{label}: frame segment requires '- surface: <tag>'")

    people: list[tuple[str, str]] = []
    if meta["people"].lower() != "none":
        for raw_p in meta["people"].split(","):
            raw_p = raw_p.strip()
            if not raw_p:
                continue
            pm = re.match(r"^([a-z0-9_]+)(?:\s*\(([^)]+)\))?$", raw_p)
            if not pm:
                raise ContentFormatError(f"{label}: invalid people entry {raw_p!r}")
            p_slug = pm.group(1)
            p_role = (pm.group(2) or "attendee").strip()
            if p_slug not in CAST_BY_SLUG and p_slug not in FACET_ENTITIES_BY_SLUG:
                raise ContentFormatError(f"{label}: unknown person/entity slug {p_slug!r} in people")
            people.append((p_slug, p_role))

    # Ensure principal is always represented in people if not explicitly listed
    if not any(p_slug == "william_shakespeare" for p_slug, _ in people):
        people.insert(0, ("william_shakespeare", "attendee"))

    entries = [] if meta["entries"].lower() == "none" else [x.strip() for x in meta["entries"].split(",") if x.strip()]
    cal_ids = (
        [] if meta["calendar"].lower() == "none" else [x.strip() for x in meta["calendar"].split(",") if x.strip()]
    )
    _validate_calendar_ids(cal_ids, day_iso, label)

    spec = SegmentSpec(
        day_iso=day_iso,
        start_hhmm=start_hhmm,
        duration_min=duration_min,
        kind=kind,
        heading_title=heading_title,
        place=place,
        facet=facet,
        content_type=content_type,
        density=density,
        surface=surface,
        people=people,
        entries=entries,
        calendar_ids=cal_ids,
        continues=continues,
    )

    seen_h3: set[str] = set()
    for idx_pos, h3_start in enumerate(h3_indices):
        h3_end = h3_indices[idx_pos + 1] if idx_pos + 1 < len(h3_indices) else len(body_lines)
        h3_name = body_lines[h3_start][4:].strip()
        h3_body = body_lines[h3_start + 1 : h3_end]
        seen_h3.add(h3_name)

        if h3_name == "Transcript":
            spec.transcript_lines = _parse_transcript_lines(h3_body, label)
        elif h3_name == "Page":
            spec.page_text = _parse_page_text(h3_body, label)
        elif h3_name == "Frames":
            spec.frames = _parse_frames(h3_body, label)
        elif h3_name == "Photo":
            spec.photo_text = "\n".join(line.strip() for line in h3_body if line.strip()).strip()
            if not spec.photo_text:
                raise ContentFormatError(f"{label}: '### Photo' section is empty")
        elif h3_name == "Sense":
            _parse_sense_section(spec, h3_body, label)
        elif h3_name == "Activity":
            if spec.continues is not None:
                raise ContentFormatError(
                    f"{label}: a continuation segment has no '### Activity' (its head carries it)"
                )
            _parse_activity_section(spec, h3_body, label)
        else:
            raise ContentFormatError(f"{label}: unexpected subsection '### {h3_name}'")

    expected_body_h3 = {
        "meeting": "Transcript",
        "call": "Transcript",
        "memo": "Transcript",
        "note": "Page",
        "frame": "Frames",
        "photo": "Photo",
    }[kind]
    required_h3 = (expected_body_h3, "Sense") if spec.continues is not None else (expected_body_h3, "Sense", "Activity")
    for req_h3 in required_h3:
        if req_h3 not in seen_h3:
            raise ContentFormatError(f"{label}: missing required subsection '### {req_h3}'")

    if spec.content_type == "idle":
        spec.content_type = classify_idle_segment(spec)
    return spec


def classify_idle_segment(seg: SegmentSpec) -> str:
    """Correct an idle label only when the authored segment supplies an activity."""
    if seg.kind == "photo":
        return "media"
    if seg.kind in ("meeting", "call"):
        return "social" if seg.facet in ("household", "stratford") else "meeting"
    if seg.density == "idle":
        return "idle"
    if seg.kind == "memo" and any(line.speaker for line in seg.transcript_lines):
        return "planning"
    if seg.kind == "frame" and seg.surface == "almanac":
        return "reading"
    if seg.kind == "frame" and seg.surface == "draft" and any(frame.text for frame in seg.frames):
        return "writing"
    return "idle"


_CARRY_JUMP_MIN = 6 * 60


def _hhmm_minutes(hhmm: str) -> int:
    hour, minute = hhmm.split(":")
    return int(hour) * 60 + int(minute)


def assign_cross_midnight(path: Path, segments: list[SegmentSpec]) -> None:
    """Move a post-midnight run onto the next calendar day.

    A day file is one waking day. When a heading jumps backwards by more than
    six hours, that heading and every heading after it happened after midnight.
    They belong to the next morning. The file date is the base, so the run
    moves one day rather than one day per jump. A continuation cannot split
    from its head.
    """
    if len(segments) < 2:
        return
    carry_from: int | None = None
    previous = _hhmm_minutes(segments[0].start_hhmm)
    for index, seg in enumerate(segments[1:], start=1):
        current = _hhmm_minutes(seg.start_hhmm)
        if current < previous - _CARRY_JUMP_MIN:
            carry_from = index
            break
        previous = current
    if carry_from is None:
        return
    next_day = (date.fromisoformat(path.stem) + timedelta(days=1)).isoformat()
    for seg in segments[carry_from:]:
        seg.day_iso = next_day
    for seg in segments:
        if seg.head is not None and seg.day_iso != seg.head.day_iso:
            raise ContentFormatError(
                f"{path.name} [{seg.start_hhmm} {seg.kind}]: continues across midnight "
                f"({seg.head.day_iso} {seg.head.start_hhmm} -> {seg.day_iso} {seg.start_hhmm})"
            )


def _previous_day_markdown(content_dir: Path, prev_iso: str) -> Path | None:
    """The previous morning's day file, including Saturday's file from the prior week."""
    direct = content_dir / f"{prev_iso}.md"
    if direct.is_file():
        return direct
    week_dir = content_dir.parent
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", week_dir.name):
        return None
    prev_date = date.fromisoformat(prev_iso)
    prev_sunday = prev_date - timedelta(days=(prev_date.weekday() + 1) % 7)
    candidate = week_dir.parent / prev_sunday.isoformat() / content_dir.name / f"{prev_iso}.md"
    if candidate.is_file():
        return candidate
    return None


def _previous_day_spec(
    content_dir: Path,
    day_iso: str,
    specs_by_iso: dict[str, DaySpec],
) -> DaySpec | None:
    prev_iso = (date.fromisoformat(day_iso) - timedelta(days=1)).isoformat()
    if prev_iso in specs_by_iso:
        return specs_by_iso[prev_iso]
    prev_path = _previous_day_markdown(content_dir, prev_iso)
    if prev_path is None:
        return None
    return parse_day_markdown(prev_path)


def _segments_to_write(
    day_spec: DaySpec,
    content_dir: Path,
    specs_by_iso: dict[str, DaySpec],
) -> list[SegmentSpec]:
    """Segments that land on this calendar day: this file's own, plus the previous file's carry.

    A carried run is not written while converting the file it was authored in.
    Sunday's conversion reads Saturday's markdown itself, so week order does not matter.
    """
    own = [seg for seg in day_spec.segments if seg.day_iso == day_spec.day_iso]
    prev_spec = _previous_day_spec(content_dir, day_spec.day_iso, specs_by_iso)
    carried = []
    if prev_spec is not None:
        carried = [seg for seg in prev_spec.segments if seg.day_iso == day_spec.day_iso]
    if not carried:
        return own
    return sorted([*carried, *own], key=lambda seg: seg.start_hhmm)


def _resolve_continuations(path: Path, segments: list[SegmentSpec]) -> None:
    """Point each continuation at its head: the earlier same-kind segment it names that day.

    The head must itself open an activity (a continuation never names another
    continuation) and sit earlier in the day file, as `content/lint.py` checks.
    """
    heads: dict[tuple[str, str], SegmentSpec] = {}
    for seg in segments:
        if seg.continues is None:
            heads.setdefault((seg.start_hhmm, seg.kind), seg)
            continue
        label = f"{path.name} [{seg.start_hhmm} {seg.kind}]"
        head = heads.get((seg.continues, seg.kind))
        if head is None:
            raise ContentFormatError(
                f"{label}: continues: {seg.continues} names no earlier {seg.kind} segment that opens an activity"
            )
        seg.head = head


def _parse_transcript_lines(lines: list[str], label: str) -> list[TranscriptLine]:
    result: list[TranscriptLine] = []
    for raw in lines:
        s = raw.strip()
        if not s:
            continue
        m = re.match(r"^\[(\d{2}:\d{2})\]\s*(.+)$", s)
        if not m:
            raise ContentFormatError(f"{label}: invalid transcript line {s!r}")
        offset_sec = _parse_mmss(m.group(1), label)
        rest = m.group(2).strip()
        # Check if stage direction `(...)` with no `: ` outside parens
        if rest.startswith("(") and rest.endswith(")") and "): " not in rest:
            result.append(
                TranscriptLine(
                    offset_sec=offset_sec,
                    speaker=None,
                    text=rest,
                    is_stage_direction=True,
                )
            )
            continue
        # Unnamed walk-on `[MM:SS] (the clerk): words` or slug `[MM:SS] slug: words`
        if rest.startswith("(") and "): " in rest:
            walk_on, spoken = rest.split("): ", 1)
            speaker_str = walk_on + ")"
            result.append(
                TranscriptLine(
                    offset_sec=offset_sec,
                    speaker=speaker_str,
                    text=spoken.strip(),
                    is_stage_direction=False,
                )
            )
            continue
        if ":" not in rest:
            raise ContentFormatError(f"{label}: transcript line missing speaker colon: {s!r}")
        speaker_slug, spoken = rest.split(":", 1)
        speaker_slug = speaker_slug.strip()
        spoken = spoken.strip()
        if speaker_slug not in CAST_BY_SLUG and speaker_slug not in FACET_ENTITIES_BY_SLUG:
            raise ContentFormatError(f"{label}: unknown speaker slug {speaker_slug!r}")
        if not spoken:
            raise ContentFormatError(f"{label}: empty spoken text for {speaker_slug!r}")
        result.append(
            TranscriptLine(
                offset_sec=offset_sec,
                speaker=speaker_slug,
                text=spoken,
                is_stage_direction=False,
            )
        )
    if not result:
        raise ContentFormatError(f"{label}: '### Transcript' has no lines")
    return result


def _parse_page_text(lines: list[str], label: str) -> str:
    raw = "\n".join(lines).strip()
    if not raw:
        raise ContentFormatError(f"{label}: '### Page' is empty")
    fence_match = re.search(r"```[^\n]*\n(.*?)```", raw, flags=re.DOTALL)
    if fence_match:
        page = fence_match.group(1).rstrip()
    else:
        page = raw
    if not page.strip():
        raise ContentFormatError(f"{label}: '### Page' has no content")
    return page + "\n"


def _parse_frames(lines: list[str], label: str) -> list[FrameItem]:
    frames: list[FrameItem] = []
    cur_offset: int | None = None
    cur_label = ""
    cur_visual = ""
    cur_text = ""
    cur_field: str | None = None

    def flush_current() -> None:
        nonlocal cur_offset, cur_label, cur_visual, cur_text, cur_field
        if cur_offset is not None:
            if not cur_visual:
                raise ContentFormatError(f"{label}: frame [{cur_label}] missing 'visual:' line")
            frames.append(
                FrameItem(
                    offset_sec=cur_offset,
                    label=cur_label,
                    visual=cur_visual.strip(),
                    text=cur_text.strip(),
                )
            )
        cur_offset = None
        cur_label = ""
        cur_visual = ""
        cur_text = ""
        cur_field = None

    for raw in lines:
        s = raw.strip()
        if not s:
            continue
        m = re.match(r"^\[(\d{2}:\d{2})\]\s*(.+)$", s)
        if m:
            flush_current()
            cur_offset = _parse_mmss(m.group(1), label)
            cur_label = m.group(2).strip()
        elif s.startswith("visual:"):
            cur_visual = s[len("visual:") :].strip()
            cur_field = "visual"
        elif s.startswith("text:"):
            cur_text = s[len("text:") :].strip()
            cur_field = "text"
        elif cur_field == "text":
            cur_text = (cur_text + "\n" + s).strip()
        elif cur_field == "visual":
            cur_visual = (cur_visual + " " + s).strip()
        else:
            raise ContentFormatError(f"{label}: unexpected line in '### Frames': {s!r}")

    flush_current()
    if not frames:
        raise ContentFormatError(f"{label}: '### Frames' has no frame entries")
    return frames


def _parse_sense_section(spec: SegmentSpec, lines: list[str], label: str) -> None:
    mode: str | None = None
    has_quotes_field = False
    has_mentioned_field = False

    for raw in lines:
        if not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        s = raw.strip()
        if indent == 0 and s.startswith("- "):
            if ":" not in s:
                raise ContentFormatError(f"{label}: invalid Sense line {s!r}")
            k, v = s[2:].split(":", 1)
            k = k.strip()
            v = v.strip()
            mode = None
            if k == "summary":
                spec.sense_summary = v
            elif k == "topics":
                spec.sense_topics = [t.strip() for t in v.split(",") if t.strip()]
            elif k == "quotes":
                has_quotes_field = True
                if v.lower() == "none":
                    spec.sense_quotes = []
                elif v:
                    spec.sense_quotes.extend(_parse_quote_bullet(q, label) for q in _split_inline_quotes(v))
                else:
                    mode = "quotes"
            elif k == "also mentioned":
                has_mentioned_field = True
                if v.lower() == "none":
                    spec.also_mentioned = []
                elif v:
                    spec.also_mentioned = _parse_also_mentioned(v, label)
                else:
                    mode = "mentioned"
            else:
                raise ContentFormatError(f"{label}: unknown Sense key {k!r}")
        elif indent > 0 and s.startswith("- "):
            item = s[2:].strip()
            if mode == "quotes":
                if item.lower() != "none":
                    spec.sense_quotes.append(_parse_quote_bullet(item, label))
            elif mode == "mentioned":
                if item.lower() != "none":
                    spec.also_mentioned.extend(_parse_also_mentioned(item, label))
            else:
                raise ContentFormatError(f"{label}: unexpected nested bullet {s!r} in Sense")
        else:
            raise ContentFormatError(f"{label}: unparseable Sense line {s!r}")

    if not spec.sense_summary:
        raise ContentFormatError(f"{label}: Sense missing non-empty '- summary:'")
    if not spec.sense_topics:
        raise ContentFormatError(f"{label}: Sense missing non-empty '- topics:'")


def _split_inline_quotes(value: str) -> list[str]:
    """Split `slug: text; slug: text` on one line into its quotes.

    A split happens only where `; ` is followed by a known cast or entity slug
    and a colon, so a semicolon inside a quoted line stays in the line.
    """
    parts: list[str] = []
    start = 0
    for m in re.finditer(r";\s+(?=([a-z0-9_]+):\s)", value):
        if m.group(1) in CAST_BY_SLUG or m.group(1) in FACET_ENTITIES_BY_SLUG:
            parts.append(value[start : m.start()])
            start = m.end()
    parts.append(value[start:])
    return [p.strip() for p in parts if p.strip()]


def _parse_quote_bullet(item: str, label: str) -> tuple[str, str]:
    if ":" not in item:
        raise ContentFormatError(f"{label}: quote item must be 'speaker: text', got {item!r}")
    spk, txt = item.split(":", 1)
    spk = spk.strip()
    txt = txt.strip()
    if len(txt) >= 2 and txt[0] == '"' and txt[-1] == '"':
        txt = txt[1:-1].strip()
    if not spk or not txt:
        raise ContentFormatError(f"{label}: empty speaker or quote text in {item!r}")
    return (spk, txt)


_ALSO_MENTIONED_TYPE_MAP: dict[str, str] = {
    "Company": "Company",
    "Project": "Project",
    "Tool": "Tool",
    "Text": "Project",
    "Book": "Project",
    "Work": "Project",
    "Place": "Project",
    "Person": "Person",
}


def _parse_also_mentioned(raw_val: str, label: str) -> list[MentionedItem]:
    if raw_val.strip().lower() == "none":
        return []
    raw_stripped = raw_val.strip()
    items: list[MentionedItem] = []
    parts = [p.strip() for p in re.split(r"\)\s*[,;]\s*", raw_stripped) if p.strip()]
    for part in parts:
        m_dot = re.match(r"^(.+?)\s*·\s*([A-Za-z]+)$", part)
        if m_dot:
            name = m_dot.group(1).strip().lstrip(",").strip()
            raw_type = m_dot.group(2).strip()
        else:
            if not part.endswith(")"):
                part = part + ")"
            m = re.match(r"^(.+)\s*\(([^()]+)\)$", part)
            if not m:
                raise ContentFormatError(
                    f"{label}: invalid 'also mentioned' item {part!r}; expected '<name> (Company|Project|Tool)'"
                )
            name = m.group(1).strip().lstrip(",").strip()
            raw_type = m.group(2).strip()
        mapped_type = _ALSO_MENTIONED_TYPE_MAP.get(raw_type)
        if not name or not mapped_type:
            raise ContentFormatError(
                f"{label}: invalid 'also mentioned' item {part!r}; expected '<name> (Company|Project|Tool)'"
            )
        items.append(MentionedItem(name=name, entity_type=mapped_type))
    return items


def _parse_activity_section(spec: SegmentSpec, lines: list[str], label: str) -> None:
    mode: str | None = None
    has_participation_field = False
    has_relations_field = False

    for raw in lines:
        if not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        s = raw.strip()
        if indent == 0 and s.startswith("- "):
            if ":" not in s:
                raise ContentFormatError(f"{label}: invalid Activity line {s!r}")
            k, v = s[2:].split(":", 1)
            k = k.strip()
            v = v.strip()
            mode = None
            if k == "title":
                spec.activity_title = v
            elif k == "story":
                spec.activity_story = v
            elif k == "participation":
                has_participation_field = True
                mode = "participation"
                if v and v.lower() != "none":
                    p_slug, p_desc = _parse_participation_bullet(v, label)
                    if not p_slug.startswith("("):
                        spec.participation[p_slug] = p_desc
            elif k == "relations":
                has_relations_field = True
                if v.lower() == "none":
                    pass
                elif v:
                    spec.relations.append(_parse_relation_bullet(v, label))
                else:
                    mode = "relations"
            else:
                raise ContentFormatError(f"{label}: unknown Activity key {k!r}")
        elif indent > 0 and s.startswith("- "):
            item = s[2:].strip()
            if mode == "participation":
                if item.lower() != "none":
                    p_slug, p_desc = _parse_participation_bullet(item, label)
                    if not p_slug.startswith("("):
                        spec.participation[p_slug] = p_desc
            elif mode == "relations":
                if item.lower() != "none":
                    spec.relations.append(_parse_relation_bullet(item, label))
            else:
                raise ContentFormatError(f"{label}: unexpected nested bullet {s!r} in Activity")
        else:
            raise ContentFormatError(f"{label}: unparseable Activity line {s!r}")

    if not spec.activity_title:
        raise ContentFormatError(f"{label}: Activity missing non-empty '- title:'")
    if not spec.activity_story:
        raise ContentFormatError(f"{label}: Activity missing non-empty '- story:'")
    non_owner_people = [slug for slug, _ in spec.people if slug != "william_shakespeare"]
    if non_owner_people and not spec.participation:
        raise ContentFormatError(f"{label}: Activity missing participation entries for {non_owner_people}")


def _parse_participation_bullet(item: str, label: str) -> tuple[str, str]:
    if ":" not in item:
        raise ContentFormatError(f"{label}: participation item must be 'slug: description', got {item!r}")
    slug, desc = item.split(":", 1)
    slug = slug.strip()
    desc = desc.strip()
    if not (slug.startswith("(") and slug.endswith(")")):
        if slug not in CAST_BY_SLUG and slug not in FACET_ENTITIES_BY_SLUG:
            raise ContentFormatError(f"{label}: unknown entity slug {slug!r} in participation")
    if not desc:
        raise ContentFormatError(f"{label}: empty participation description for {slug!r}")
    return (slug, desc)


_RELATION_KIND_MAP: dict[str, str] = {
    "goes home to": "family-of",
}


def _parse_relation_bullet(item: str, label: str) -> RelationItem:
    parts = [p.strip() for p in item.split("·")]
    if len(parts) < 3:
        raise ContentFormatError(
            f"{label}: relation must match 'from → to · kind · note [· quote]', got {item!r}"
        )
    arrow_part = parts[0]
    if "→" in arrow_part:
        from_slug, to_slug = [x.strip() for x in arrow_part.split("→", 1)]
    elif "->" in arrow_part:
        from_slug, to_slug = [x.strip() for x in arrow_part.split("->", 1)]
    else:
        raise ContentFormatError(f"{label}: relation missing '→' in {item!r}")

    kind = _RELATION_KIND_MAP.get(parts[1].strip(), parts[1].strip())
    if kind not in VALID_RELATION_KINDS:
        raise ContentFormatError(f"{label}: invalid relation kind {kind!r}")
    note = parts[2].strip()
    if not note:
        raise ContentFormatError(f"{label}: empty relation note in {item!r}")
    quote: str | None = None
    if len(parts) >= 4:
        q = " · ".join(parts[3:]).strip()
        if len(q) >= 2 and q[0] == '"' and q[-1] == '"':
            q = q[1:-1].strip()
        if q.lower() not in ("", "none"):
            quote = q
    return RelationItem(
        from_slug=from_slug,
        to_slug=to_slug,
        kind=kind,
        note=note,
        quote=quote,
    )


def parse_week_markdown(path: Path) -> WeekSpec:
    """Parse `week.md` in `FORMAT.md` shape, failing loudly on missing sections or bad items."""
    raw = _strip_html_comments(path.read_text(encoding="utf-8"))
    lines = raw.splitlines()
    if not lines:
        raise ContentFormatError(f"{path}: week.md is empty")

    # Find H1 `# Week of Sun 9 Mar 2025`
    sunday_iso = ""
    for line in lines:
        s = line.strip()
        if s.startswith("# Week of "):
            rest = s[len("# Week of ") :].strip()
            try:
                dt = datetime.strptime(rest, "%a %d %b %Y").date()
            except ValueError as err:
                raise ContentFormatError(f"{path}: cannot parse week header date {rest!r}") from err
            if dt == JOURNAL_YEAR_START and dt.weekday() != 6:
                # The year's edge week (`# Week of Wed 1 Jan 2025`) starts mid-week. Its
                # reflection is keyed to the Sunday before, with the pre-year days as
                # empty slots, mirroring the 28 Dec week's span past 31 Dec.
                dt = dt - timedelta(days=(dt.weekday() + 1) % 7)
            sunday_iso = dt.isoformat()
            break
    if not sunday_iso:
        raise ContentFormatError(f"{path}: missing '# Week of Sun D Mon YYYY' heading")

    h2_indices = [i for i, line in enumerate(lines) if line.startswith("## ")]
    sections: dict[str, list[str]] = {}
    for idx_pos, start_idx in enumerate(h2_indices):
        end_idx = h2_indices[idx_pos + 1] if idx_pos + 1 < len(h2_indices) else len(lines)
        sec_name = lines[start_idx][3:].strip()
        sections[sec_name] = lines[start_idx + 1 : end_idx]

    for req_sec in ("Reflection", "Memories", "Said", "Observations"):
        if req_sec not in sections:
            raise ContentFormatError(f"{path}: missing required '## {req_sec}' section")

    reflection_paragraphs = [
        line.strip()
        for line in sections["Reflection"]
        if line.strip() and not (line.strip().startswith("*") and line.strip().endswith("*"))
    ]
    if not reflection_paragraphs:
        raise ContentFormatError(f"{path}: '## Reflection' is empty")
    reflection_md = "\n\n".join(reflection_paragraphs)

    memories: list[tuple[str, str]] = []
    for line in sections["Memories"]:
        s = line.strip()
        if not s or (s.startswith("*") and s.endswith("*")):
            continue
        if not s.startswith("- "):
            raise ContentFormatError(f"{path}: invalid Memories line {s!r}")
        m = re.match(r"^-\s*(\d{4}-\d{2}-\d{2}):\s*(.+)$", s)
        if not m:
            raise ContentFormatError(f"{path}: memory line must match '- YYYY-MM-DD: text', got {s!r}")
        memories.append((m.group(1), m.group(2).strip()))
    if not memories:
        raise ContentFormatError(f"{path}: '## Memories' has no entries")

    said: list[tuple[str, str, str, str, str]] = []
    for line in sections["Said"]:
        s = line.strip()
        if not s or (s.startswith("*") and s.endswith("*")):
            continue
        m = re.match(
            r'^-\s*(\d{4}-\d{2}-\d{2})\s*·\s*(\d{2}:\d{2})\s+([a-z]+)\s*·\s*([a-z0-9_]+|\([^)]+\)|[a-zA-Z0-9_ ]+?):\s*"?(.+?)"?\s*$',
            s,
        )
        if not m:
            raise ContentFormatError(
                f"{path}: Said line must match '- YYYY-MM-DD · HH:MM <kind> · <slug>: \"<quote>\"', got {s!r}"
            )
        # The journal shows Said as "said by you": William's own words only (content/lint.py's rule).
        if m.group(4) != "william_shakespeare":
            raise ContentFormatError(
                f"{path}: Said line speaker {m.group(4)!r} is not william_shakespeare "
                f"(the journal shows Said as \"said by you\"), got {s!r}"
            )
        said.append((m.group(1), m.group(2), m.group(3), m.group(4), m.group(5).strip()))
    if not said:
        raise ContentFormatError(f"{path}: '## Said' has no entries")

    saturday_iso = (date.fromisoformat(sunday_iso) + timedelta(days=6)).isoformat()
    cast_prefix_pairs: list[tuple[str, str]] = []
    for ent in CANON_CAST:
        for alias in (ent.name, *ent.aka):
            cast_prefix_pairs.append((alias, ent.slug))
    cast_prefix_pairs.sort(key=lambda x: -len(x[0]))

    observations: list[tuple[str, str, str]] = []
    for line in sections["Observations"]:
        s = line.strip()
        if not s or (s.startswith("*") and s.endswith("*")):
            continue
        m = re.match(r"^-\s*([a-z0-9_]+)\s*·\s*(\d{4}-\d{2}-\d{2}):\s*(.+)$", s)
        if m:
            slug = m.group(1)
            if slug not in CAST_BY_SLUG and slug not in FACET_ENTITIES_BY_SLUG:
                raise ContentFormatError(f"{path}: unknown entity slug {slug!r} in Observations")
            observations.append((slug, m.group(2), m.group(3).strip()))
            continue
        m_nodate = re.match(r"^-\s*([a-z0-9_]+):\s*(.+)$", s)
        if m_nodate:
            slug = m_nodate.group(1)
            if slug not in CAST_BY_SLUG and slug not in FACET_ENTITIES_BY_SLUG:
                raise ContentFormatError(f"{path}: unknown entity slug {slug!r} in Observations")
            observations.append((slug, saturday_iso, m_nodate.group(2).strip()))
            continue
        if not s.startswith("- "):
            matched_slug: str | None = None
            for alias, c_slug in cast_prefix_pairs:
                if re.match(rf"^{re.escape(alias)}\b", s):
                    matched_slug = c_slug
                    break
            if matched_slug is not None:
                observations.append((matched_slug, saturday_iso, s))
            continue
        raise ContentFormatError(
            f"{path}: Observation line must match '- <slug> · YYYY-MM-DD: <text>', got {s!r}"
        )
    if not observations:
        raise ContentFormatError(f"{path}: '## Observations' has no entries")

    return WeekSpec(
        sunday_iso=sunday_iso,
        reflection_markdown=reflection_md,
        memories=memories,
        said=said,
        observations=observations,
    )


def _normalize_schema_role(raw_role: str) -> str:
    if raw_role in ("attendee", "caller"):
        return "attendee"
    return "mentioned"


def _normalize_activity_role(raw_role: str) -> str:
    if raw_role in ("attendee", "caller"):
        return "attendee"
    if raw_role in ("heard", "mentioned", "visible"):
        return raw_role
    return "mentioned"


def _source_for_kind(kind: str, role: str) -> str:
    if kind in ("meeting", "call", "memo"):
        return "speaker_label" if role == "attendee" else "transcript"
    if kind in ("frame", "photo"):
        return "screen"
    return "transcript"


def _segment_level(seg: SegmentSpec) -> str:
    """The sense facet level a segment's density maps to."""
    return "high" if seg.density == "active" else "medium"


def _level_value(level: str) -> float:
    """`level_value` in `solstone-core-system/src/activity_state.rs`: the stored number for a level."""
    return {"high": 1.0, "low": 0.25}.get(level, 0.5)


def build_sense_and_projections(
    seg: SegmentSpec,
    predecessor_seg_key: str | None,
    timestamp_rfc3339: str,
    registry: ContractRegistry,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Build `talents/sense.json` and its 7 projections (`write_sense_and_change` parity)."""
    entities: list[dict[str, Any]] = []
    speakers: list[str] = []

    for slug, raw_role in seg.people:
        role = _normalize_schema_role(raw_role)
        src = _source_for_kind(seg.kind, role)
        ctx = seg.participation.get(slug) or f"{raw_role} in {seg.heading_title}"
        entities.append(
            {
                "type": "Person",
                "name": _entity_display_name(slug),
                "role": role,
                "source": src,
                "context": ctx,
                "level": "high" if role == "attendee" else "medium",
            }
        )

    if seg.kind in ("meeting", "call", "memo"):
        seen_spk: set[str] = set()
        for tl in seg.transcript_lines:
            if tl.speaker and not tl.speaker.startswith("(") and tl.speaker not in seen_spk:
                seen_spk.add(tl.speaker)
                speakers.append(_entity_display_name(tl.speaker))

    for m_item in seg.also_mentioned:
        entities.append(
            {
                "type": m_item.entity_type,
                "name": m_item.name,
                "role": "mentioned",
                "source": _source_for_kind(seg.kind, "mentioned"),
                "context": f"Mentioned in {seg.heading_title}",
                "level": "medium",
            }
        )

    entities = entities[:40]
    speakers = speakers[:16]
    topics = seg.sense_topics[:12]
    quotes = [{"speaker": spk, "text": txt} for spk, txt in seg.sense_quotes]

    sense_obj: dict[str, Any] = {
        "density": seg.density,
        "content_type": seg.content_type,
        "activity_summary": seg.sense_summary,
        "entities": entities,
        "facets": [
            {
                "facet": seg.facet,
                "activity": seg.activity_head.activity_title,
                "level": _segment_level(seg),
            }
        ],
        "speculative_facet": None,
        "meeting_detected": seg.kind in ("meeting", "call"),
        "speakers": speakers,
        "recommend": {
            "screen_record": False,
            "speaker_attribution": False,
        },
        "topics": topics,
        "quotes": quotes,
    }
    registry.validate_talent_output("sense", sense_obj, f"{seg.day_key}/{seg.segment_key}/sense.json")

    projections: dict[str, str] = {}
    projections["activity.md"] = sense_obj["activity_summary"] + "\n"
    projections["facets.json"] = json.dumps(sense_obj["facets"], indent=2) + "\n"
    projections["density.json"] = (
        json.dumps(
            {
                "classification": sense_obj["density"],
                "timestamp": timestamp_rfc3339,
            },
            indent=2,
        )
        + "\n"
    )
    if entities:
        sense_md_lines = ["# Sense Entities", ""]
        for ent in entities:
            sense_md_lines.append(
                f"- {ent['type']} — {ent['name']} (role={ent['role']}, source={ent['source']}) — {ent['context']}"
            )
        projections["sense.md"] = "\n".join(sense_md_lines) + "\n"

    if sense_obj["meeting_detected"]:
        projections["speakers.json"] = json.dumps(speakers, indent=2) + "\n"

    projections["change.json"] = (
        json.dumps(
            {
                "change_class": "substantive",
                "predecessor": predecessor_seg_key,
                "timestamp": timestamp_rfc3339,
            },
            indent=2,
        )
        + "\n"
    )

    if topics or quotes:
        topic_lines: list[str] = []
        if topics:
            topic_lines.append("## Topics")
            for t in topics:
                topic_lines.append(f"- {t}")
        if quotes:
            if topic_lines:
                topic_lines.append("")
            topic_lines.append("## Quotes")
            for q in quotes:
                topic_lines.append(f"- {q['speaker']}: {q['text']}")
        projections["topics.md"] = "\n".join(topic_lines) + "\n"

    return sense_obj, projections


def _write_segment_files(
    journal_dir: Path,
    seg: SegmentSpec,
    predecessor_by_stream: dict[str, str | None],
    registry: ContractRegistry,
    file_mtime_sec: float,
    receipt_ts_ms: int,
    preserved_photos: dict[tuple[str, str], bytes] | None = None,
    preserved_audio: dict[tuple[str, str], tuple[bytes, dict[str, Any] | None]] | None = None,
    audio_install_timings: dict[str, dict[str, Any]] | None = None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[dict[str, Any]]]:
    """Write one segment's files, sense projections, and health receipts; return activity and entity rows.

    A continuation segment returns no activity record: `_join_continuation`
    adds it to its head's record instead.
    """
    day_dir = journal_dir / "chronicle" / seg.day_key
    seg_dir = day_dir / seg.stream_name / seg.segment_key
    talents_dir = seg_dir / "talents"
    talents_dir.mkdir(parents=True, exist_ok=True)

    hh, mm = [int(x) for x in seg.start_hhmm.split(":")]
    seg_start_dt = datetime.combine(date.fromisoformat(seg.day_iso), time(hh, mm, 0))
    seg_end_dt = seg_start_dt + timedelta(seconds=seg.duration_sec)
    seg_end_iso = f"{seg_end_dt.strftime('%Y-%m-%dT%H:%M:%S')}{london_offset_str(date.fromisoformat(seg.day_iso))}"
    seg_end_utc = datetime.fromtimestamp(to_epoch_ms(seg_end_iso) / 1000.0, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    seg_end_ms = to_epoch_ms(seg_end_iso)

    written_paths: list[Path] = []

    # 1. Modality extract files
    if seg.kind in ("meeting", "call", "memo"):
        audio_lines: list[dict[str, Any]] = [
            {
                "backend": "whisper",
                "duration": float(seg.duration_sec),
                "model": "large-v3",
                "observer": seg.stream_name,
                "raw": "audio.flac",
            }
        ]
        speaker_labels: list[dict[str, Any]] = []
        sentence_id = 0
        effective_lines = [tl for tl in seg.transcript_lines if not tl.is_stage_direction]
        if not effective_lines:
            effective_lines = list(seg.transcript_lines)
        for idx, tl in enumerate(effective_lines):
            next_offset = (
                effective_lines[idx + 1].offset_sec
                if idx + 1 < len(effective_lines)
                else max(tl.offset_sec + 6, min(seg.duration_sec, tl.offset_sec + 10))
            )
            end_offset = max(tl.offset_sec + 1, next_offset)
            wall_dt = seg_start_dt + timedelta(seconds=tl.offset_sec)
            wall_clock = wall_dt.strftime("%H:%M:%S")
            sentence_id += 1
            rec: dict[str, Any] = {
                "sentence_id": sentence_id,
                "start": wall_clock,
                "text": tl.text,
                "timing": {
                    "end": float(end_offset),
                    "start": float(tl.offset_sec),
                },
            }
            if tl.speaker is not None:
                rec["speaker"] = tl.speaker
            audio_lines.append(rec)
            if tl.speaker and (tl.speaker in CAST_BY_SLUG or tl.speaker in FACET_ENTITIES_BY_SLUG):
                speaker_labels.append(
                    {
                        "sentence_id": sentence_id,
                        "speaker": tl.speaker,
                        "method": "user_assigned",
                        "confidence": "high",
                    }
                )
        kept_audio = (preserved_audio or {}).get((seg.stream_name, seg.segment_key))
        if kept_audio is not None:
            audio_bytes, kept_timings = kept_audio
            flac_path = seg_dir / AUDIO_FLAC
            flac_path.write_bytes(audio_bytes)
            written_paths.append(flac_path)
            seg_rel = f"{seg.day_key}/{seg.stream_name}/{seg.segment_key}"
            timing_overlay = kept_timings
            if timing_overlay is None or len(timing_overlay.get("turns") or {}) != len(effective_lines):
                cand = (audio_install_timings or {}).get(seg_rel)
                if cand is not None and len(cand.get("turns") or {}) == len(effective_lines):
                    timing_overlay = cand
            if timing_overlay is not None and len(timing_overlay.get("turns") or {}) == len(effective_lines):
                audio_lines[0]["duration"] = float(timing_overlay["duration"])
                turns_map = timing_overlay["turns"]
                for rec in audio_lines[1:]:
                    ov = turns_map.get(int(rec["sentence_id"]))
                    if ov is not None:
                        rec["start"] = ov["start"]
                        rec["timing"] = {
                            "end": float(ov["timing"]["end"]),
                            "start": float(ov["timing"]["start"]),
                        }
        registry.validate_headered_jsonl("audio-jsonl", audio_lines, f"{seg.day_key}/{seg.segment_key}/audio.jsonl")
        audio_path = seg_dir / "audio.jsonl"
        audio_path.write_text(
            "".join(json.dumps(line, sort_keys=True) + "\n" for line in audio_lines),
            encoding="utf-8",
        )
        written_paths.append(audio_path)

        labels_path = talents_dir / "speaker_labels.json"
        labels_path.write_text(
            json.dumps({"labels": speaker_labels}, indent=2) + "\n",
            encoding="utf-8",
        )
        written_paths.append(labels_path)

    elif seg.kind == "note":
        note_path = seg_dir / "note_transcript.md"
        note_path.write_text(seg.page_text, encoding="utf-8")
        written_paths.append(note_path)

    elif seg.kind == "frame":
        jpg_path = seg_dir / PAGE_JPEG
        kept = (preserved_photos or {}).get((seg.stream_name, seg.segment_key))
        jpeg = photo_jpeg_bytes(seg, jpg_path, preserved=kept)
        if jpeg:
            jpg_path.write_bytes(jpeg)
            written_paths.append(jpg_path)
        screen_lines: list[dict[str, Any]] = [
            {
                "observer": seg.stream_name,
                "qualified_count": len(seg.frames),
                "raw": "screen.mp4",
            }
        ]
        md_blocks: list[str] = []
        narratives: list[str] = []
        for idx, fr in enumerate(seg.frames, start=1):
            frame = {
                "analysis": {
                    "primary": seg.content_type,
                    "visual_description": fr.visual,
                },
                "content": {},
                "frame_id": idx,
                "timestamp": float(fr.offset_sec),
            }
            # A segment's page is one still. Attach it to the first beat so
            # later descriptions do not each show the same image again.
            if jpeg and idx == 1:
                frame["raw"] = PAGE_JPEG
            screen_lines.append(frame)
            narratives.append(fr.visual)
            mm, ss = divmod(fr.offset_sec, 60)
            block = f"## {mm:02d}:{ss:02d} · {fr.label}\n"
            if fr.text:
                block += f"\n{fr.text}\n"
            md_blocks.append(block)

        registry.validate_headered_jsonl("screen-jsonl", screen_lines, f"{seg.day_key}/{seg.segment_key}/screen.jsonl")
        screen_jsonl_path = seg_dir / "screen.jsonl"
        screen_jsonl_path.write_text(
            "".join(json.dumps(line, sort_keys=True) + "\n" for line in screen_lines),
            encoding="utf-8",
        )
        written_paths.append(screen_jsonl_path)

        screen_text_path = talents_dir / "screen_text.md"
        screen_text_path.write_text("\n".join(md_blocks), encoding="utf-8")
        written_paths.append(screen_text_path)

        screen_entities: list[dict[str, str]] = []
        for slug, raw_role in seg.people:
            screen_entities.append(
                {
                    "type": "Person",
                    "name": _entity_display_name(slug),
                    "role": _normalize_schema_role(raw_role),
                    "context": seg.participation.get(slug) or f"Visible/present in {seg.heading_title}",
                }
            )
        for m_item in seg.also_mentioned:
            screen_entities.append(
                {
                    "type": m_item.entity_type,
                    "name": m_item.name,
                    "role": "mentioned",
                    "context": f"Shown on {seg.surface or 'surface'} in {seg.heading_title}",
                }
            )
        screen_talent_obj = {
            "narrative": " ".join(narratives),
            "entities": screen_entities[:30],
        }
        registry.validate_talent_output("screen", screen_talent_obj, f"{seg.day_key}/{seg.segment_key}/screen.json")
        screen_json_path = talents_dir / "screen.json"
        screen_json_path.write_text(json.dumps(screen_talent_obj, indent=2) + "\n", encoding="utf-8")
        written_paths.append(screen_json_path)

    elif seg.kind == "photo":
        jpg_path = seg_dir / PHOTO_JPEG
        kept = (preserved_photos or {}).get((seg.stream_name, seg.segment_key))
        jpeg = photo_jpeg_bytes(seg, jpg_path, preserved=kept)
        jpg_path.write_bytes(jpeg)
        written_paths.append(jpg_path)
        width, height = _jpeg_dimensions(jpeg)
        offset = london_offset_seconds_at(seg.day_iso, seg.start_hhmm)
        meta_path = seg_dir / "image_meta.json"
        # Field order matches `write_image_meta`. No caption, filename, or tz:
        # the importer stores tz only when it has one, and this path never does.
        meta_path.write_text(
            json.dumps(
                {"schema": 1, "time_source": "capture", "utc_offset_seconds": offset},
                separators=(",", ":"),
            )
            + "\n",
            encoding="utf-8",
        )
        written_paths.append(meta_path)
        transcript_path = seg_dir / "image_transcript.md"
        transcript_path.write_text(
            _image_transcript(seg.heading_title, width, height, seg.day_iso, seg.photo_text),
            encoding="utf-8",
        )
        written_paths.append(transcript_path)
        kind_path = seg_dir / "import_kind.json"
        kind_path.write_text(
            json.dumps(PHOTO_IMPORT_KIND, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        written_paths.append(kind_path)
        _write_photo_import_record(journal_dir, seg, jpeg, file_mtime_sec)

    # 2. Sense + 7 projections
    pred_seg = predecessor_by_stream.get(seg.stream_name)
    sense_obj, projections = build_sense_and_projections(seg, pred_seg, seg_end_utc, registry)
    predecessor_by_stream[seg.stream_name] = seg.segment_key

    sense_path = talents_dir / "sense.json"
    sense_path.write_text(json.dumps(sense_obj, indent=2) + "\n", encoding="utf-8")
    written_paths.append(sense_path)

    for proj_name, proj_content in projections.items():
        proj_path = talents_dir / proj_name
        proj_path.write_text(proj_content, encoding="utf-8")
        written_paths.append(proj_path)

    # 3. Documents talent output (required on every thought segment)
    if seg.kind in ("note", "frame"):
        docs_obj: dict[str, Any] = {
            "overview": seg.sense_summary[:3000],
            "parties": [
                {
                    "name": _entity_display_name(slug)[:256],
                    "role": raw_role[:512],
                    "formal_term": _entity_display_name(slug)[:256],
                    "appointment_tier": "not_applicable",
                    "context": (seg.participation.get(slug) or seg.activity_head.activity_title)[:1000],
                }
                for slug, raw_role in seg.people[:10]
            ],
            "key_provisions": [
                {
                    "type": "other",
                    "text": t[:1500],
                    "applies_to": "William Shakespeare",
                }
                for t in seg.sense_topics[:5]
            ],
            "assets": [
                {
                    "name": m.name[:512],
                    "asset_type": "other",
                    "disposition": seg.activity_head.activity_title[:1500],
                }
                for m in seg.also_mentioned[:5]
            ],
            "conditions": [],
            "important_dates": [
                {
                    "date": seg.day_iso,
                    "meaning": seg.heading_title[:1000],
                }
            ],
            "summary": seg.activity_head.activity_title[:3000],
        }
    else:
        docs_obj = {
            "overview": "",
            "parties": [],
            "key_provisions": [],
            "assets": [],
            "conditions": [],
            "important_dates": [],
            "summary": "",
        }
    registry.validate_talent_output("documents", docs_obj, f"{seg.day_key}/{seg.segment_key}/documents.json")
    docs_path = talents_dir / "documents.json"
    docs_path.write_text(json.dumps(docs_obj, indent=2) + "\n", encoding="utf-8")
    written_paths.append(docs_path)

    # Set segment file mtimes strictly before receipt_ts_ms so segment_thinking_is_current is True
    for wp in written_paths:
        os.utime(wp, (file_mtime_sec, file_mtime_sec))

    # 4. Health receipt lines for this segment
    receipts: list[dict[str, Any]] = [
        {
            "ts": receipt_ts_ms,
            "event": "sense.complete",
            "mode": "segment",
            "day": seg.day_key,
            "stream": seg.stream_name,
            "segment": seg.segment_key,
            "density": seg.density,
        },
        {
            "ts": receipt_ts_ms + 1,
            "event": "sense.change_detect",
            "mode": "segment",
            "day": seg.day_key,
            "stream": seg.stream_name,
            "segment": seg.segment_key,
            "change_class": "substantive",
        },
        {
            "ts": receipt_ts_ms + 2,
            "event": "talent.complete",
            "mode": "segment",
            "day": seg.day_key,
            "stream": seg.stream_name,
            "segment": seg.segment_key,
            "name": "documents",
        },
    ]
    if seg.kind == "frame":
        receipts.append(
            {
                "ts": receipt_ts_ms + 3,
                "event": "talent.complete",
                "mode": "segment",
                "day": seg.day_key,
                "stream": seg.stream_name,
                "segment": seg.segment_key,
                "name": "screen",
            }
        )

    # 5. Build Activity Record + Validate Story and Participation schemas
    if seg.head is not None:
        detected_entities = [
            {
                "id": slug,
                "name": _entity_display_name(slug),
                "type": FACET_ENTITIES_BY_SLUG[slug].entity_type if slug in FACET_ENTITIES_BY_SLUG else "Person",
                "description": f"Active in {seg.head.activity_title}",
                "last_seen": seg.day_key,
            }
            for slug in dict.fromkeys(slug for slug, _ in seg.people)
        ]
        return None, detected_entities, receipts

    story_relations = [
        {
            "from": _entity_display_name(r.from_slug),
            "to": _entity_display_name(r.to_slug),
            "kind": r.kind,
            "note": r.note[:300],
            "quote": r.quote[:400] if r.quote is not None else None,
        }
        for r in seg.relations[:12]
    ]
    story_obj: dict[str, Any] = {
        "body": seg.activity_story[:4000],
        "topics": [t[:48].rstrip() for t in seg.sense_topics[:10]],
        "confidence": 0.95,
        "relations": story_relations,
    }
    registry.validate_talent_output("story", story_obj, f"{seg.day_key}/{seg.activity_id}/story")

    schema_participation_items: list[dict[str, Any]] = []
    activity_participation_items: list[dict[str, Any]] = []
    seen_part_slugs: set[str] = set()

    for slug, raw_role in seg.people:
        seen_part_slugs.add(slug)
        ctx = seg.participation.get(slug) or f"{raw_role} in {seg.heading_title}"
        schema_role = _normalize_schema_role(raw_role)
        act_role = _normalize_activity_role(raw_role)
        src = _source_for_kind(seg.kind, schema_role)
        schema_participation_items.append(
            {
                "name": _entity_display_name(slug),
                "role": schema_role,
                "source": src,
                "confidence": 0.95,
                "context": ctx,
                "entity_id": None,
            }
        )
        activity_participation_items.append(
            {
                "name": _entity_display_name(slug),
                "role": act_role,
                "source": src,
                "confidence": 0.95,
                "context": ctx,
                "entity_id": slug,
            }
        )

    for slug, ctx in seg.participation.items():
        if slug not in seen_part_slugs:
            seen_part_slugs.add(slug)
            src = _source_for_kind(seg.kind, "mentioned")
            schema_participation_items.append(
                {
                    "name": _entity_display_name(slug),
                    "role": "mentioned",
                    "source": src,
                    "confidence": 0.9,
                    "context": ctx,
                    "entity_id": None,
                }
            )
            activity_participation_items.append(
                {
                    "name": _entity_display_name(slug),
                    "role": "mentioned",
                    "source": src,
                    "confidence": 0.9,
                    "context": ctx,
                    "entity_id": slug,
                }
            )

    participation_envelope = {
        "participation": schema_participation_items,
        "participation_confidence": 0.95,
    }
    registry.validate_talent_output(
        "participation", participation_envelope, f"{seg.day_key}/{seg.activity_id}/participation"
    )

    activity_record: dict[str, Any] = {
        "id": seg.activity_id,
        "activity": seg.content_type,
        "title": seg.activity_title,
        "description": seg.heading_title,
        "details": "",  # owner-only: non-empty reads as "corrected by you" (facets-web activities/view.rs:421-428)
        "facet": seg.facet,
        "day": seg.day_key,
        "stream": seg.stream_name,
        "segments": [seg.segment_key],
        # The product stores the last tracked segment's level as a number under
        # this key (`activity_state.rs`, `completed`); `_join_continuation` moves it.
        "level_avg": _level_value(_segment_level(seg)),
        "created_at": seg_end_ms,
        "updated_at": seg_end_ms,
        "story": story_obj,
        "participation": activity_participation_items,
        "relations": story_relations,
    }

    # 6. Daily detected entities for this facet
    detected_entities: list[dict[str, Any]] = []
    for slug in seen_part_slugs:
        ent_type = "Person"
        if slug in FACET_ENTITIES_BY_SLUG:
            ent_type = FACET_ENTITIES_BY_SLUG[slug].entity_type
        detected_entities.append(
            {
                "id": slug,
                "name": _entity_display_name(slug),
                "type": ent_type,
                "description": seg.participation.get(slug) or f"Active in {seg.activity_title}",
                "last_seen": seg.day_key,
            }
        )

    return activity_record, detected_entities, receipts


def _segment_end_ms(seg: SegmentSpec) -> int:
    hh, mm = [int(x) for x in seg.start_hhmm.split(":")]
    end_dt = datetime.combine(date.fromisoformat(seg.day_iso), time(hh, mm, 0)) + timedelta(seconds=seg.duration_sec)
    return to_epoch_ms(f"{end_dt.strftime('%Y-%m-%dT%H:%M:%S')}{london_offset_str(date.fromisoformat(seg.day_iso))}")


def _join_continuation(record: dict[str, Any], run: list[SegmentSpec], registry: ContractRegistry) -> None:
    """Fold a head's continuations into its activity record (FORMAT.md, "Continuing an activity").

    The editor's rules : the head's facet and content type govern; people
    are the union, the head's authored entries kept as written; the level is the
    product's over the run. `segments` is in time order, because the product
    reads the span from its first and last entries (`activity_time_range`).
    """
    head = run[0]
    for seg in run[1:]:
        if seg.stream_name != head.stream_name:
            raise ContentFormatError(
                f"{seg.day_iso} {seg.start_hhmm} {seg.kind}: a continuation must share its head's stream "
                f"({seg.stream_name!r} != {head.stream_name!r})"
            )
    ordered = sorted(run, key=lambda s: s.segment_key)
    record["segments"] = [s.segment_key for s in ordered]
    # `completed` in activity_state.rs keeps the last tracked segment's level.
    record["level_avg"] = _level_value(_segment_level(ordered[-1]))
    record["created_at"] = record["updated_at"] = _segment_end_ms(ordered[-1])

    seen = {item["entity_id"] for item in record["participation"]}
    joined: list[dict[str, Any]] = []
    for seg in run[1:]:
        for slug, raw_role in seg.people:
            if slug in seen:
                continue
            seen.add(slug)
            joined.append(
                {
                    "name": _entity_display_name(slug),
                    "role": _normalize_activity_role(raw_role),
                    "source": _source_for_kind(seg.kind, _normalize_schema_role(raw_role)),
                    "confidence": 0.95,
                    "context": f"{raw_role} in {seg.heading_title}",
                    "entity_id": slug,
                }
            )
    if joined:
        record["participation"].extend(joined)
        envelope = {
            "participation": [
                {**item, "role": "attendee" if item["role"] == "attendee" else "mentioned", "entity_id": None}
                for item in record["participation"]
            ],
            "participation_confidence": 0.95,
        }
        registry.validate_talent_output("participation", envelope, f"{head.day_key}/{head.activity_id}/participation")


def rebuild_stream_chains(journal_dir: Path, registry: ContractRegistry, file_mtime_sec: float | None = None) -> None:
    """Rebuild `<segment>/stream.json` and `streams/<name>.json` across all streams in chronological order."""
    chronicle_dir = journal_dir / "chronicle"
    if not chronicle_dir.is_dir():
        return

    # Known stream metadata
    stream_meta: dict[str, tuple[str, str | None, str | None]] = {
        "calendar": ("observer", "calendar", None),
        "obsidian": ("observer", "obsidian", None),
        "import.image": ("observer", None, None),
        "import.text": ("import", None, None),
        "import.document": ("import", None, None),
        "import.evernote": ("import", "evernote", None),
        "import.apple_health": ("observer", "import.apple_health", None),
        "phone": ("observer", None, "ios"),
        "talk": ("observer", "microphone", None),
        "calls": ("observer", "call", None),
        "memos": ("observer", "voice_memo", None),
        "desk": ("observer", "screen", None),
    }

    segments_by_stream: dict[str, list[tuple[str, str]]] = {k: [] for k in stream_meta}
    for day_dir in sorted(chronicle_dir.iterdir()):
        if not day_dir.is_dir() or not re.fullmatch(r"\d{8}", day_dir.name):
            continue
        day_key = day_dir.name
        for stream_dir in sorted(day_dir.iterdir()):
            if not stream_dir.is_dir() or stream_dir.name == "talents" or stream_dir.name == "health":
                continue
            stream_name = stream_dir.name
            if stream_name not in segments_by_stream:
                segments_by_stream[stream_name] = []
                stream_meta[stream_name] = ("observer", None, None)
            for seg_dir in sorted(stream_dir.iterdir()):
                if not seg_dir.is_dir():
                    continue
                segments_by_stream[stream_name].append((day_key, seg_dir.name))

    streams_root = journal_dir / "streams"
    streams_root.mkdir(parents=True, exist_ok=True)

    for stream_name, seg_list in sorted(segments_by_stream.items()):
        kind, source, platform = stream_meta[stream_name]
        seg_list.sort(key=lambda x: (x[0], x[1]))

        prev_day: str | None = None
        prev_seg: str | None = None
        seq = 0

        for idx, (day_key, seg_key) in enumerate(seg_list, start=1):
            seq = idx
            seg_json_obj = {
                "stream": stream_name,
                "prev_day": prev_day,
                "prev_segment": prev_seg,
                "seq": seq,
            }
            label = f"chronicle/{day_key}/{stream_name}/{seg_key}/stream.json"
            registry.validate_bundle_json("stream-json", seg_json_obj, label)
            seg_json_path = chronicle_dir / day_key / stream_name / seg_key / "stream.json"
            raw_bytes = (
                json.dumps(seg_json_obj, separators=(",", ":"), ensure_ascii=False) + "\n"
            ).encode("utf-8")
            seg_json_path.write_bytes(raw_bytes)
            if file_mtime_sec is not None:
                os.utime(seg_json_path, (file_mtime_sec, file_mtime_sec))
            prev_day = day_key
            prev_seg = seg_key

        # Always keep the 5 backdrop stream records; also write any active speech/screen stream records
        if seq == 0 and stream_name not in (
            "calendar",
            "obsidian",
            "import.apple_health",
            "phone",
        ):
            continue

        stream_record: dict[str, Any] = {
            "name": stream_name,
            "kind": kind,
            "host": None,
            "platform": platform,
            "created_at": SETUP_COMPLETED_AT_MS,
            "last_day": prev_day,
            "last_segment": prev_seg,
            "seq": max(1, seq),
            "cid": _deterministic_cid(stream_name),
        }
        if source is not None:
            stream_record["source"] = source
        validate_stream_record(stream_record, f"streams/{stream_name}.json")
        (streams_root / f"{stream_name}.json").write_text(
            json.dumps(stream_record, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    # Photos left the screenshots stream. Drop the empty record so the journal
    # does not keep advertising a source that has no segments.
    if not segments_by_stream.get("screenshots"):
        stale_screenshots = streams_root / "screenshots.json"
        if stale_screenshots.is_file():
            stale_screenshots.unlink()

    write_device_descriptions(journal_dir)


def convert_content_to_journal(
    content_dir: Path,
    journal_dir: Path,
    solstone_repo: Path | None = None,
) -> dict[str, Any]:
    """Convert all day files (`YYYY-MM-DD.md`) and `week.md` in `content_dir` into `journal_dir`."""
    registry = ContractRegistry(solstone_repo) if solstone_repo else ContractRegistry()

    day_files = sorted(
        p for p in content_dir.glob("*.md") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.stem)
    )
    if not day_files:
        raise ContentFormatError(f"No YYYY-MM-DD.md day files found in {content_dir}")

    day_specs = [parse_day_markdown(p) for p in day_files]
    specs_by_iso = {spec.day_iso: spec for spec in day_specs}
    week_file = content_dir / "week.md"
    week_spec = parse_week_markdown(week_file) if week_file.is_file() else None

    all_activities_by_day: dict[str, list[dict[str, Any]]] = {}
    total_segments = 0
    first_day_mtime_sec: float | None = None

    for day_spec in day_specs:
        day_date = date.fromisoformat(day_spec.day_iso)
        base_receipt_ts_ms = to_epoch_ms(
            f"{day_spec.day_iso}T23:55:00{london_offset_str(day_date)}"
        )
        file_mtime_sec = (base_receipt_ts_ms / 1000.0) - 300.0
        if first_day_mtime_sec is None:
            first_day_mtime_sec = file_mtime_sec

        day_dir = journal_dir / "chronicle" / day_spec.day_key
        day_talents_dir = day_dir / "talents"
        day_health_dir = day_dir / "health"
        day_talents_dir.mkdir(parents=True, exist_ok=True)
        day_health_dir.mkdir(parents=True, exist_ok=True)

        # Read real photos and audio before the stream directories are removed. A re-convert
        # would otherwise replace photos with the 1x1 placeholder and wipe real audio/timings.
        preserved_photos = _preserved_photo_bytes(day_dir, day_spec)
        preserved_audio = _preserved_audio_state(day_dir, day_spec)
        audio_install_timings = _load_audio_install_timings() if preserved_audio else {}
        written_segments = _segments_to_write(day_spec, content_dir, specs_by_iso)

        # Clean any pre-existing content stream directories and receipt files for this day
        for stream_name, _, _ in STREAM_CONFIG_BY_KIND.values():
            stream_dir = day_dir / stream_name
            if stream_dir.is_dir():
                shutil.rmtree(stream_dir)
        # The photo stream name changed. Remove the old directory or the day
        # still holds the picture as a screen segment.
        legacy_screenshots = day_dir / "screenshots"
        if legacy_screenshots.is_dir():
            shutil.rmtree(legacy_screenshots)
        for old_receipt in day_health_dir.glob("*_segment.jsonl"):
            old_receipt.unlink()

        # 1. Pulse (`chronicle/<YYYYMMDD>/talents/pulse.jsonl`)
        pulse_schema_obj = {
            "title": day_spec.pulse_title,
            "one_sentence": day_spec.pulse_one_sentence,
            "full_details": day_spec.pulse_details,
            "needs_you": [],
        }
        registry.validate_talent_output("pulse", pulse_schema_obj, f"{day_spec.day_key}/pulse.jsonl")
        day_end_iso = (
            f"{day_spec.day_iso}T22:00:00{london_offset_str(date.fromisoformat(day_spec.day_iso))}"
        )
        pulse_disk_obj = {
            **pulse_schema_obj,
            "ts": to_epoch_ms(day_end_iso),
        }
        (day_talents_dir / "pulse.jsonl").write_text(
            json.dumps(pulse_disk_obj, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        # 2. Morning Briefing (`chronicle/<YYYYMMDD>/talents/morning_briefing.json`, shown on D+1)
        next_day = date.fromisoformat(day_spec.day_iso) + timedelta(days=1)
        briefing_obj = {
            "metadata": {
                "generated": f"{next_day.isoformat()}T06:00:00Z",
                "model": "william-journal-generator",
                "sources": {
                    "segments": len(written_segments),
                },
                "gaps": [],
                "coverage_preamble": day_spec.briefing_coverage,
            },
            "yesterday": day_spec.briefing_bullets[:8],
            "needs_attention": [],
        }
        registry.validate_talent_output(
            "morning_briefing", briefing_obj, f"{day_spec.day_key}/morning_briefing.json"
        )
        (day_talents_dir / "morning_briefing.json").write_text(
            json.dumps(briefing_obj, indent=2) + "\n",
            encoding="utf-8",
        )

        # 3. Segments
        predecessor_by_stream: dict[str, str | None] = {}
        activities_by_facet: dict[str, list[dict[str, Any]]] = {}
        entities_by_facet: dict[str, dict[str, dict[str, Any]]] = {}
        day_receipts: list[dict[str, Any]] = []

        records_by_head: dict[int, dict[str, Any]] = {}
        runs: dict[int, list[SegmentSpec]] = {}
        for seg_idx, seg in enumerate(written_segments):
            total_segments += 1
            act_rec, det_entities, seg_receipts = _write_segment_files(
                journal_dir=journal_dir,
                seg=seg,
                predecessor_by_stream=predecessor_by_stream,
                registry=registry,
                file_mtime_sec=file_mtime_sec,
                receipt_ts_ms=base_receipt_ts_ms + seg_idx * 10,
                preserved_photos=preserved_photos,
                preserved_audio=preserved_audio,
                audio_install_timings=audio_install_timings,
            )
            runs.setdefault(id(seg.activity_head), []).append(seg)
            if act_rec is not None:
                records_by_head[id(seg)] = act_rec
                activities_by_facet.setdefault(seg.facet, []).append(act_rec)
                all_activities_by_day.setdefault(seg.day_iso, []).append(act_rec)
            day_receipts.extend(seg_receipts)

            facet_ent_map = entities_by_facet.setdefault(seg.facet, {})
            for de in det_entities:
                if act_rec is None:
                    # A continuation adds people; it never overwrites an authored description.
                    facet_ent_map.setdefault(de["id"], de)
                else:
                    facet_ent_map[de["id"]] = de

        for head_id, run in runs.items():
            if len(run) > 1:
                _join_continuation(records_by_head[head_id], run, registry)

        # Clean any pre-existing facet activity/entity files for this day before writing
        if (journal_dir / "facets").is_dir():
            for stale_f in (journal_dir / "facets").glob(f"*/activities/{day_spec.day_key}.jsonl"):
                stale_f.unlink()
            for stale_f in (journal_dir / "facets").glob(f"*/entities/{day_spec.day_key}.jsonl"):
                stale_f.unlink()

        # Write `facets/<facet>/activities/<YYYYMMDD>.jsonl` and `facets/<facet>/entities/<YYYYMMDD>.jsonl`
        for facet_name, act_list in sorted(activities_by_facet.items()):
            act_dir = journal_dir / "facets" / facet_name / "activities"
            act_dir.mkdir(parents=True, exist_ok=True)
            (act_dir / f"{day_spec.day_key}.jsonl").write_text(
                "".join(json.dumps(r, sort_keys=True) + "\n" for r in act_list),
                encoding="utf-8",
            )

        for facet_name, ent_map in sorted(entities_by_facet.items()):
            ent_dir = journal_dir / "facets" / facet_name / "entities"
            ent_dir.mkdir(parents=True, exist_ok=True)
            sorted_ents = [ent_map[k] for k in sorted(ent_map)]
            (ent_dir / f"{day_spec.day_key}.jsonl").write_text(
                "".join(json.dumps(e, sort_keys=True) + "\n" for e in sorted_ents),
                encoding="utf-8",
            )

        # Write health receipts file for this day
        receipt_file = day_health_dir / f"{base_receipt_ts_ms}_segment.jsonl"
        receipt_file.write_text(
            "".join(json.dumps(r, sort_keys=True) + "\n" for r in day_receipts),
            encoding="utf-8",
        )

    # Rebuild stream chains before stamping deterministic mtimes
    rebuild_stream_chains(
        journal_dir,
        registry,
        file_mtime_sec=first_day_mtime_sec if first_day_mtime_sec is not None else time_mod.time(),
    )

    # 4. Week outputs (`reflections/weekly/<Sunday_YYYYMMDD>.json` & `.md`, and `observations.jsonl`)
    if week_spec is not None:
        _write_week_outputs(journal_dir, week_spec, all_activities_by_day)

    stamp_summary = stamp_journal_tree(journal_dir)

    return {
        "days_converted": len(day_specs),
        "segments_converted": total_segments,
        "week_converted": week_spec.sunday_iso if week_spec else None,
        "stamp": stamp_summary,
    }


def _is_baseline_observation(line: str) -> bool:
    """A backdrop observation (`source_day` 20250101 with an `id`), never a week's own."""
    obj = json.loads(line)
    return obj.get("source_day") == JOURNAL_YEAR_START.strftime("%Y%m%d") and "id" in obj


def _write_week_outputs(
    journal_dir: Path,
    week_spec: WeekSpec,
    all_activities_by_day: dict[str, list[dict[str, Any]]],
) -> None:
    sunday_date = date.fromisoformat(week_spec.sunday_iso)
    saturday_date = sunday_date + timedelta(days=6)
    sunday_key = sunday_date.strftime("%Y%m%d")
    saturday_key = saturday_date.strftime("%Y%m%d")

    memories_by_day_key: dict[str, dict[str, Any]] = {}
    memories_list: list[dict[str, Any]] = []

    for idx, (day_iso, mem_text) in enumerate(week_spec.memories):
        day_key = day_iso.replace("-", "")
        mem_id = f"m-{day_key}-{idx}"
        mem_key = f"mem_{day_key}_{idx}"
        day_acts = all_activities_by_day.get(day_iso, [])
        refs = [
            f"sol://facets/{act['facet']}/activities/{day_key}#{act['id']}"
            for act in day_acts[:3]
        ]
        mem_obj = {
            "id": mem_id,
            "key": mem_key,
            "day": day_key,
            "text": mem_text,
            "source": {
                "kind": "briefing",
                "uri": f"sol://chronicle/{day_key}/talents/morning_briefing",
                "briefing_day": day_key,
                "refs": refs,
            },
        }
        memories_list.append(mem_obj)
        if day_key not in memories_by_day_key:
            memories_by_day_key[day_key] = mem_obj

    days_list: list[dict[str, Any]] = []
    for i in range(7):
        d_key = (sunday_date + timedelta(days=i)).strftime("%Y%m%d")
        if d_key in memories_by_day_key:
            days_list.append(
                {
                    "day": d_key,
                    "state": "memory",
                    "memory_id": memories_by_day_key[d_key]["id"],
                }
            )
        else:
            days_list.append(
                {
                    "day": d_key,
                    "state": "nothing_shared",
                }
            )

    said_list: list[dict[str, Any]] = []
    for idx, (day_iso, hhmm, kind, speaker_slug, quote_text) in enumerate(week_spec.said):
        day_key = day_iso.replace("-", "")
        day_acts = all_activities_by_day.get(day_iso, [])
        hhmm_compact = hhmm.replace(":", "") + "00"
        matched_act: dict[str, Any] | None = None
        for act in day_acts:
            if act["id"].startswith(f"{kind}_{hhmm_compact}_"):
                matched_act = act
                break
        if matched_act is None:
            # Never fall back to another activity: a wrong citation must fail loudly.
            raise ContentFormatError(
                f"week.md Said item references {day_iso} {hhmm} {kind}, but no activity opens at that time"
            )
        uri = f"sol://facets/{matched_act['facet']}/activities/{day_key}#{matched_act['id']}"
        said_list.append(
            {
                "id": f"s-{day_key}-{idx}",
                "key": f"said_{day_key}_{idx}",
                "day": day_key,
                "quote": quote_text,
                "source": {
                    "kind": "activity",
                    "uri": uri,
                },
            }
        )

    weekly_json_obj = {
        "version": 1,
        "week": {
            "start": sunday_key,
            "end": saturday_key,
        },
        "generated_at": f"{saturday_date.isoformat()}T22:00:00Z",
        "days": days_list,
        "memories": memories_list,
        "said": said_list,
    }
    weekly_json_str = json.dumps(weekly_json_obj, indent=2) + "\n"
    weekly_md_str = f"# Week of {sunday_date.strftime('%b %d, %Y')}\n\n{week_spec.reflection_markdown}\n"

    judge_weekly_reflection(weekly_md_str, weekly_json_str, sunday_key)

    weekly_dir = journal_dir / "reflections" / "weekly"
    weekly_dir.mkdir(parents=True, exist_ok=True)
    (weekly_dir / f"{sunday_key}.json").write_text(weekly_json_str, encoding="utf-8")
    (weekly_dir / f"{sunday_key}.md").write_text(weekly_md_str, encoding="utf-8")

    # Write `observations.jsonl` on each person's facet entity directory
    week_day_keys = {(sunday_date + timedelta(days=i)).strftime("%Y%m%d") for i in range(7)}
    if (journal_dir / "facets").is_dir():
        for existing_obs_file in sorted((journal_dir / "facets").glob("*/entities/*/observations.jsonl")):
            raw_lines = [
                ln for ln in existing_obs_file.read_text(encoding="utf-8").splitlines() if ln.strip()
            ]
            kept_lines = [
                ln
                for ln in raw_lines
                if json.loads(ln).get("source_day") not in week_day_keys or _is_baseline_observation(ln)
            ]
            if len(kept_lines) != len(raw_lines):
                existing_obs_file.write_text(
                    ("\n".join(kept_lines) + "\n") if kept_lines else "",
                    encoding="utf-8",
                )

    obs_by_entity: dict[str, list[dict[str, Any]]] = {}
    for slug, day_iso, obs_text in week_spec.observations:
        day_key = day_iso.replace("-", "")
        obs_ms = to_epoch_ms(f"{day_iso}T21:00:00{london_offset_str(date.fromisoformat(day_iso))}")
        obs_by_entity.setdefault(slug, []).append(
            {
                "content": obs_text,
                "observed_at": obs_ms,
                "source_day": day_key,
            }
        )

    for slug, obs_rows in sorted(obs_by_entity.items()):
        # Determine target facets for this entity
        if slug in CAST_BY_SLUG:
            target_facets = list(CAST_BY_SLUG[slug].facets)
        elif slug in FACET_ENTITIES_BY_SLUG:
            target_facets = list(FACET_ENTITIES_BY_SLUG[slug].facets)
        else:
            target_facets = ["company"]

        for facet_name in target_facets:
            ent_subdir = journal_dir / "facets" / facet_name / "entities" / slug
            ent_subdir.mkdir(parents=True, exist_ok=True)
            root_ent = journal_dir / "entities" / slug / "entity.json"
            target_ent = ent_subdir / "entity.json"
            if root_ent.is_file() and not target_ent.is_file():
                target_ent.write_bytes(root_ent.read_bytes())
            obs_file = ent_subdir / "observations.jsonl"
            existing_lines: list[str] = []
            if obs_file.is_file():
                existing_lines = [ln for ln in obs_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
            baseline_lines: list[str] = []
            week_obs_map: dict[tuple[str, str], dict[str, Any]] = {}
            for ln in existing_lines:
                obj = json.loads(ln)
                if _is_baseline_observation(ln):
                    baseline_lines.append(ln)
                else:
                    week_obs_map[(str(obj.get("source_day", "")), str(obj.get("content", "")))] = obj
            for row in obs_rows:
                week_obs_map[(str(row["source_day"]), str(row["content"]))] = row
            sorted_week_obs = sorted(
                week_obs_map.values(),
                key=lambda r: (str(r.get("source_day", "")), int(r.get("observed_at", 0)), str(r.get("content", ""))),
            )
            out_lines = baseline_lines + [json.dumps(r, sort_keys=True) for r in sorted_week_obs]
            obs_file.write_text("\n".join(out_lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Convert FORMAT.md content files into a William journal tree.")
    parser.add_argument(
        "--week",
        type=str,
        default="2025-03-09",
        help="Week folder name(s) under content/weeks/<week>/, comma-separated (default: 2025-03-09).",
    )
    parser.add_argument(
        "--content",
        type=Path,
        default=None,
        help="Directory containing YYYY-MM-DD.md day files and optional week.md (defaults to content/weeks/<week>/merged).",
    )
    parser.add_argument(
        "--journal",
        type=Path,
        default=None,
        help="Target journal directory (defaults to build/journal).",
    )
    parser.add_argument(
        "--dayplan",
        type=Path,
        default=None,
        help="Optional dayplan.md path when generating backdrop (defaults to full 365-day year plan).",
    )
    parser.add_argument(
        "--calendar",
        type=Path,
        default=DEFAULT_CALENDAR_JSON,
        help="Path to merged calendar.json when generating backdrop.",
    )
    parser.add_argument(
        "--with-backdrop",
        action="store_true",
        help="Generate (or refresh) the backdrop from dayplan.md and calendar.json before converting content.",
    )
    parser.add_argument(
        "--refresh-calendar",
        action="store_true",
        help="Regenerate only the calendar notes in the target journal before converting content.",
    )
    parser.add_argument(
        "--solstone-repo",
        type=Path,
        default=None,
        help="Path to solstone-journal repository for schema validation.",
    )
    args = parser.parse_args(argv)
    journal_dir = (
        args.journal
        if args.journal is not None
        else PROJECT_ROOT / "build" / "journal"
    )
    dayplan_md = args.dayplan
    solstone_repo = args.solstone_repo if args.solstone_repo is not None else DEFAULT_SOLSTONE_REPO

    backdrop_summary: dict[str, Any] | None = None
    if args.with_backdrop or not (journal_dir / "config" / "journal.json").is_file():
        backdrop_summary = generate_backdrop(
            output_journal=journal_dir,
            calendar_json=args.calendar,
            dayplan_md=dayplan_md,
            solstone_repo=solstone_repo,
        )
    elif args.refresh_calendar:
        registry = ContractRegistry(solstone_repo) if solstone_repo else ContractRegistry()
        backdrop_summary = write_calendar_backdrop(
            journal_root=journal_dir,
            calendar_json_path=args.calendar,
            registry=registry,
        )

    if args.content is not None:
        summary = convert_content_to_journal(args.content, journal_dir, solstone_repo)
        if backdrop_summary is not None:
            summary["backdrop"] = backdrop_summary
        print(json.dumps(summary, indent=2))
        return 0

    weeks = [w.strip() for w in args.week.split(",") if w.strip()]
    if len(weeks) == 1:
        content_dir = PROJECT_ROOT / "content" / "weeks" / weeks[0] / "merged"
        summary = convert_content_to_journal(content_dir, journal_dir, solstone_repo)
        if backdrop_summary is not None:
            summary["backdrop"] = backdrop_summary
        print(json.dumps(summary, indent=2))
        return 0

    week_summaries: dict[str, Any] = {}
    for w in weeks:
        content_dir = PROJECT_ROOT / "content" / "weeks" / w / "merged"
        week_summaries[w] = convert_content_to_journal(content_dir, journal_dir, solstone_repo)
    out_obj: dict[str, Any] = {"weeks": week_summaries}
    if backdrop_summary is not None:
        out_obj["backdrop"] = backdrop_summary
    print(json.dumps(out_obj, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
