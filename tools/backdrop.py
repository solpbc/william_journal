#!/usr/bin/env python3
"""Mechanical backdrop generator for the William Shakespeare 1595/2025 journal.

Generates the non-LLM spine of the journal tree:
1. `config/journal.json` (identity, timezone, setup; NO thinking provider or lane).
2. `entities/<id>/entity.json` for all 71 world § 3 cast slugs + 16 facet entities
   (`william_shakespeare` has `is_principal: true`).
3. `facets/<facet>/` (`company`, `writing`, `household`, `stratford`) with `facet.json`,
   `activities/activities.jsonl`, and `entities/<id>/{entity.json,observations.jsonl}`
   from `content/facets.md`.
4. All 794 calendar notes (`chronicle/<day>/calendar/<seg>/calendar_<sha256>.jsonl`)
   from `calendar/merged/calendar.json`, clamped to
   `2025-01-01` when `created < 2025-01-01` so no chronicle day precedes 2025.
5. `chronicle/<day>/import.apple_health/060000_300/body.jsonl` from world § 7.8 and
   `dayplan.md` (with deterministic per-date seeded draws for banded values).
6. `chronicle/<day>/phone/<seg>/location.jsonl` from world § 7.9, § 4 coordinates,
   and `dayplan.md`.
7. `streams/<name>.json` and `<segment>/stream.json` chronological chains for every
   stream (`calendar`, `obsidian`, `screenshots`, `import.apple_health`, `phone`),
   validated against the pinned `solstone-journal` contract bundle before writing.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import random
import re
import shutil
import sys
from typing import Any
from zoneinfo import ZoneInfo

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from contracts import (  # type: ignore[import-not-found]
        DEFAULT_SOLSTONE_REPO,
        ContractRegistry,
        validate_body_rows,
        validate_calendar_file_bytes,
        validate_location_lines,
        validate_stream_record,
    )
    from world_data import (  # type: ignore[import-not-found]
        CANON_CAST,
        CANON_PLACES,
        FACET_DEFINITIONS,
        FACET_EXTRA_ENTITIES,
        CastEntity,
        generate_body_metrics_for_day,
        resolve_day_type_key,
    )
else:
    from .contracts import (
        DEFAULT_SOLSTONE_REPO,
        ContractRegistry,
        validate_body_rows,
        validate_calendar_file_bytes,
        validate_location_lines,
        validate_stream_record,
    )
    from .world_data import (
        CANON_CAST,
        CANON_PLACES,
        FACET_DEFINITIONS,
        FACET_EXTRA_ENTITIES,
        CastEntity,
        generate_body_metrics_for_day,
        resolve_day_type_key,
    )


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CALENDAR_JSON = PROJECT_ROOT / "calendar" / "merged" / "calendar.json"
DEFAULT_DAYPLAN_MD = PROJECT_ROOT / "content" / "weeks" / "2025-03-09" / "dayplan.md"
DEFAULT_DAYPLANS_WEEKS_DIR = PROJECT_ROOT / "content" / "dayplans" / "weeks"
DEFAULT_OUTPUT_JOURNAL = PROJECT_ROOT / "build" / "journal"

LONDON_TZ = ZoneInfo("Europe/London")
SETUP_COMPLETED_AT_MS = 1735689600000  # 2025-01-01T00:00:00Z
PACKED_DAYS = {
    "2025-08-10": "2025-08-10",
    "2025-10-22": "2025-10-19",
    "2025-12-30": "2025-12-28",
}

SOURCE_NAMES = {
    "talk": "gathered talk",
    "calls": "a voice at a distance",
    "memos": "working speech",
    "obsidian": "commonplace book and papers",
    "desk": "the page before him",
    "screenshots": "a still",
    "phone": "the day's walk",
}

ALL_ENTITIES: tuple[CastEntity, ...] = (*CANON_CAST, *FACET_EXTRA_ENTITIES)
CAST_BY_SLUG: dict[str, CastEntity] = {ent.slug: ent for ent in ALL_ENTITIES}


@dataclass(frozen=True)
class PlaceStop:
    """One place stop or waypoint on a day's itinerary."""

    place_slug: str
    start_time: time
    end_time: time
    is_waypoint: bool = False
    transit_mode_before: str = "walk"


@dataclass(frozen=True)
class DayPlanRow:
    """Parsed row from `dayplan.md` (or synthesized full-year day plan)."""

    date_iso: str
    day_type_label: str
    explicit_steps: int | None
    stops: list[PlaceStop]
    raw_places: str
    sources: str


def _deterministic_cid(stream_name: str) -> str:
    digest = hashlib.sha256(f"william-journal:stream:{stream_name}".encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def write_device_descriptions(journal_root: Path) -> None:
    """Write descriptive metadata for the synthetic stream CIDs without pairing anything."""
    descriptions = {}
    for stream, label in SOURCE_NAMES.items():
        if not (journal_root / "streams" / f"{stream}.json").is_file():
            continue
        reported = None
        if stream == "screenshots":
            # The world gives the stills a modern phone camera (§ 2.9).
            reported = dict(name=None, platform=None, device_type="phone",
                            app_id=None, app_version=None)
        descriptions[_deterministic_cid(stream)] = {
            "protocol_version": 1,
            "revision": 1,
            "reported": reported,
            "owner_label": label,
            "updated_at": "2025-01-01T00:00:00Z",
        }
    _write_json_pretty(journal_root / "link" / "client-descriptions.json", descriptions)


def _write_json_pretty(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


def _write_json_compact(path: Path, payload: Any, sort_keys: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, sort_keys=sort_keys, separators=(",", ":"), ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


def write_journal_config(journal_root: Path) -> None:
    """Write `config/journal.json` with NO thinking provider or lane."""
    config = {
        "identity": {
            "name": "William Shakespeare",
            "preferred": "Will",
            "timezone": "Europe/London",
        },
        "timezone": "Europe/London",
        "setup": {
            "completed_at": SETUP_COMPLETED_AT_MS,
        },
    }
    _write_json_pretty(journal_root / "config" / "journal.json", config)


def write_entities_and_facets(journal_root: Path) -> dict[str, int]:
    """Write all `entities/<id>/entity.json` and `facets/<facet>/` files."""
    entity_count = 0

    for ent in sorted(ALL_ENTITIES, key=lambda e: e.slug):
        entity_obj: dict[str, Any] = {
            "id": ent.slug,
            "name": ent.name,
            "type": ent.entity_type,
            "aka": list(ent.aka),
            "description": ent.description,
            "created_at": SETUP_COMPLETED_AT_MS,
        }
        if ent.is_principal:
            entity_obj["is_principal"] = True
        _write_json_pretty(journal_root / "entities" / ent.slug / "entity.json", entity_obj)
        entity_count += 1

    principal_facet_roles = {
        "company": "Sharer, player, and poet in the Lord Chamberlain's Men.",
        "writing": "Poet and playwright at the table in Bishopsgate and New Place.",
        "household": "Lodger at Mistress Ansell's house in St Helen's parish, Bishopsgate.",
        "stratford": "Husband to Anne, father to Susanna, Hamnet, and Judith, son to John and Mary in Henley Street.",
    }

    facet_link_count = 0
    for facet_slug, fdef in sorted(FACET_DEFINITIONS.items()):
        facet_dir = journal_root / "facets" / facet_slug
        facet_json = {
            "title": fdef["title"],
            "description": fdef["description"],
            "color": fdef["color"],
            "emoji": fdef["emoji"],
            "muted": False,
        }
        _write_json_pretty(facet_dir / "facet.json", facet_json)

        act_lines = []
        for act in fdef["activities"]:
            act_lines.append(
                json.dumps(
                    {
                        "id": act["id"],
                        "name": act["name"],
                        "description": act["description"],
                        "priority": act.get("priority", "medium"),
                    },
                    ensure_ascii=False,
                )
            )
        act_path = facet_dir / "activities" / "activities.jsonl"
        act_path.parent.mkdir(parents=True, exist_ok=True)
        act_path.write_text("\n".join(act_lines) + "\n", encoding="utf-8")

        for ent in sorted(ALL_ENTITIES, key=lambda e: e.slug):
            if facet_slug not in ent.facets:
                continue
            desc = principal_facet_roles[facet_slug] if ent.is_principal else ent.description
            rel_obj = {
                "entity_id": ent.slug,
                "description": desc,
                "attached_at": SETUP_COMPLETED_AT_MS,
                "updated_at": SETUP_COMPLETED_AT_MS,
                "last_seen": "20250309",
            }
            ent_dir = facet_dir / "entities" / ent.slug
            _write_json_pretty(ent_dir / "entity.json", rel_obj)

            obs_texts = list(ent.observations) if ent.observations else [desc]
            obs_lines = []
            for obs_idx, obs_text in enumerate(obs_texts, start=1):
                obs_lines.append(
                    json.dumps(
                        {
                            "id": obs_idx,
                            "content": obs_text,
                            "source_day": "20250101",
                            "observed_at": SETUP_COMPLETED_AT_MS,
                        },
                        ensure_ascii=False,
                    )
                )
            (ent_dir / "observations.jsonl").write_text("\n".join(obs_lines) + "\n", encoding="utf-8")
            facet_link_count += 1

    return {
        "entities": entity_count,
        "facets": len(FACET_DEFINITIONS),
        "facet_entity_links": facet_link_count,
    }


def write_stream_chain(
    journal_root: Path,
    stream_name: str,
    segments: list[tuple[str, str]],
    source: str | None,
    registry: ContractRegistry,
    kind: str = "observer",
    platform: str | None = None,
) -> None:
    """Write `<segment>/stream.json` chain and `streams/<stream_name>.json`."""
    sorted_segments = sorted(set(segments))
    prev_day: str | None = None
    prev_seg: str | None = None

    for seq_idx, (day_key, seg_key) in enumerate(sorted_segments, start=1):
        marker = {
            "stream": stream_name,
            "prev_day": prev_day,
            "prev_segment": prev_seg,
            "seq": seq_idx,
        }
        label = f"chronicle/{day_key}/{stream_name}/{seg_key}/stream.json"
        registry.validate_bundle_json("stream-json", marker, label)
        marker_path = journal_root / "chronicle" / day_key / stream_name / seg_key / "stream.json"
        _write_json_compact(marker_path, marker)
        prev_day = day_key
        prev_seg = seg_key

    record: dict[str, Any] = {
        "name": stream_name,
        "kind": kind,
        "host": None,
        "platform": platform,
        "created_at": SETUP_COMPLETED_AT_MS,
        "last_day": prev_day,
        "last_segment": prev_seg,
        "seq": max(1, len(sorted_segments)),
        "cid": _deterministic_cid(stream_name),
    }
    if source is not None:
        record["source"] = source

    validate_stream_record(record, f"streams/{stream_name}.json")
    _write_json_pretty(journal_root / "streams" / f"{stream_name}.json", record)


def write_calendar_backdrop(
    journal_root: Path,
    calendar_json_path: Path,
    registry: ContractRegistry,
) -> dict[str, int]:
    """Write all calendar notes into `chronicle/<day>/calendar/<seg>/calendar_<sha256>.jsonl`."""
    chronicle_root = journal_root / "chronicle"
    if chronicle_root.is_dir():
        for day_dir in sorted(chronicle_root.iterdir()):
            if not day_dir.is_dir():
                continue
            cal_dir = day_dir / "calendar"
            if cal_dir.is_dir():
                shutil.rmtree(cal_dir)
            if not any(day_dir.iterdir()):
                day_dir.rmdir()

    payload = json.loads(calendar_json_path.read_text(encoding="utf-8"))
    events = payload["events"] if isinstance(payload, dict) else payload

    segments_written: set[tuple[str, str]] = set()
    files_written = 0

    def note_moment(naive_raw: str) -> tuple[str, str, str]:
        """The day, five-minute segment and `changed_at` a note recorded at `naive_raw` is stored under."""
        naive = datetime.fromisoformat(naive_raw)
        if naive.year < 2025:
            return "20250101", "070000_300", "2025-01-01T07:00:00+00:00"
        local_dt = naive.replace(tzinfo=LONDON_TZ)
        minute_bucket = (local_dt.minute // 5) * 5
        return local_dt.strftime("%Y%m%d"), f"{local_dt.hour:02d}{minute_bucket:02d}00_300", local_dt.isoformat()

    def write_note(note_obj: dict[str, Any], day_key: str, seg_key: str) -> None:
        nonlocal files_written
        raw_line = (json.dumps(note_obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode(
            "utf-8"
        )
        sha_hex = hashlib.sha256(raw_line).hexdigest()
        filename = f"calendar_{sha_hex}.jsonl"
        validate_calendar_file_bytes(filename, raw_line, day_key, seg_key)
        out_path = journal_root / "chronicle" / day_key / "calendar" / seg_key / filename
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(raw_line)
        segments_written.add((day_key, seg_key))
        files_written += 1

    for ev in events:
        status = ev.get("status", "confirmed")
        if status not in ("confirmed", "cancelled"):
            raise ValueError(f"{ev['id']}: unknown calendar status {status!r}")
        if status == "cancelled" and not ev.get("modified"):
            raise ValueError(f"{ev['id']}: a cancelled event needs the 'modified' time it was struck")
        day_key, seg_key, changed_at = note_moment(ev["created"])

        all_day = bool(ev.get("all_day", False))
        ev_date = date.fromisoformat(ev["date"])
        if all_day:
            start_str = ev["date"]
            end_date_raw = ev.get("end_date") or ev["date"]
            end_inclusive = date.fromisoformat(end_date_raw)
            # `calendar.rs:675-680` treats `When::Date` `end` as exclusive when > start
            end_str: str | None = (end_inclusive + timedelta(days=1)).isoformat()
            time_zone_val: str | None = None
        else:
            sh, sm = (int(p) for p in ev["start"].split(":"))
            eh, em = (int(p) for p in ev["end"].split(":"))
            start_dt = datetime(ev_date.year, ev_date.month, ev_date.day, sh, sm, 0, tzinfo=LONDON_TZ)
            end_day = ev_date + timedelta(days=1) if (eh, em) < (sh, sm) else ev_date
            end_dt = datetime(end_day.year, end_day.month, end_day.day, eh, em, 0, tzinfo=LONDON_TZ)
            start_str = start_dt.isoformat()
            end_str = end_dt.isoformat()
            time_zone_val = "Europe/London"

        attendees_list = []
        for slug in ev.get("attendees") or []:
            if slug in CAST_BY_SLUG:
                attendees_list.append({"name": CAST_BY_SLUG[slug].name, "email": None})
            else:
                attendees_list.append({"name": slug.replace("_", " ").title(), "email": None})

        location_label: str | None = ev.get("location")
        if not location_label:
            pslug = ev.get("place_slug")
            if pslug and pslug in CANON_PLACES:
                location_label = CANON_PLACES[pslug].name

        note_obj = {
            "all_day": all_day,
            "attendees": attendees_list,
            "calendar": ev.get("calendar") or "The year's book",
            "change": "added",
            "changed_at": changed_at,
            "end": end_str,
            "event": ev["id"],
            "location": location_label,
            "notes": ev.get("description") or ev.get("notes") or None,
            "occurrence": None,
            "organizer": None,
            "repeats": ev.get("rrule") or None,
            "start": start_str,
            "time_zone": time_zone_val,
            "title": ev.get("title") or ev["summary"],
            "url": None,
            "v": 1,
        }
        write_note(note_obj, day_key, seg_key)

        if status == "cancelled":
            # A struck event: the calendar removed it at `modified`. A removal carries no
            # schedule (`calendar.rs` reads none), so the journal stops listing the event
            # and keeps the note as "Calendar event removed" at that moment.
            removed_day, removed_seg, removed_at = note_moment(ev["modified"])
            removed_obj = {
                **{key: None for key in note_obj},
                "attendees": [],
                "calendar": note_obj["calendar"],
                "change": "removed",
                "changed_at": removed_at,
                "event": ev["id"],
                "title": note_obj["title"],
                "v": 1,
            }
            write_note(removed_obj, removed_day, removed_seg)

    write_stream_chain(
        journal_root=journal_root,
        stream_name="calendar",
        segments=sorted(segments_written),
        source="calendar",
        registry=registry,
        kind="observer",
    )

    return {
        "events": files_written,
        "segments": len(segments_written),
    }


_MONTH_MAP = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}


def _parse_hhmm(text: str) -> time:
    hh, mm = text.strip().split(":")
    return time(int(hh), int(mm))


def parse_places_column(places_str: str) -> list[PlaceStop]:
    """Parse a `dayplan.md` 'Places, in order' string into ordered `PlaceStop` items."""
    if places_str.strip().lower() in ("", "gap", "unplaced", "none"):
        return []
    parts = [p.strip() for p in places_str.split("·") if p.strip()]
    stops: list[PlaceStop] = []
    pending_mode = "walk"

    for part in parts:
        slug_match = re.search(r"`([a-z0-9_]+)`", part)
        if not slug_match:
            if "wherry" in part.lower() or "boat" in part.lower():
                pending_mode = "wherry"
            else:
                pending_mode = "walk"
            if "past midnight" in part.lower() and "ludgate" in part.lower():
                stops.append(
                    PlaceStop(
                        place_slug="pauls_churchyard",
                        start_time=time(23, 55),
                        end_time=time(23, 59),
                        is_waypoint=True,
                        transit_mode_before=pending_mode,
                    )
                )
                pending_mode = "walk"
            continue

        place_slug = slug_match.group(1)
        if place_slug not in CANON_PLACES:
            raise ValueError(f"Unknown place slug {place_slug!r} in dayplan clause {part!r}")
        is_route_track = CANON_PLACES[place_slug].lat is None or CANON_PLACES[place_slug].lon is None

        mode_for_this = "wherry" if "wherry" in part.lower() else pending_mode
        pending_mode = "walk"

        after_slug = part[slug_match.end() :].strip()
        after_slug_clean = re.sub(r"\([^)]*\)", "", after_slug)
        if is_route_track:
            span_match = re.search(r"(\d{2}:\d{2})\s*[–-]\s*(\d{2}:\d{2})", after_slug_clean)
            if span_match:
                stops.append(
                    PlaceStop(
                        place_slug=place_slug,
                        start_time=_parse_hhmm(span_match.group(1)),
                        end_time=_parse_hhmm(span_match.group(2)),
                        is_waypoint=True,
                        transit_mode_before=mode_for_this,
                    )
                )
            continue
        if "all day" in after_slug_clean:
            stops.append(
                PlaceStop(
                    place_slug=place_slug,
                    start_time=time(0, 0),
                    end_time=time(23, 55),
                    is_waypoint=False,
                    transit_mode_before=mode_for_this,
                )
            )
            continue

        to_match = re.search(r"\bto\s+(\d{2}:\d{2})\b", after_slug_clean)
        from_match = re.search(r"\bfrom\s+(\d{2}:\d{2})\b", after_slug_clean)
        span_match = re.search(r"(\d{2}:\d{2})\s*[–-]\s*(\d{2}:\d{2})", after_slug_clean)

        if from_match and to_match and not span_match:
            stops.append(
                PlaceStop(
                    place_slug=place_slug,
                    start_time=_parse_hhmm(from_match.group(1)),
                    end_time=_parse_hhmm(to_match.group(1)),
                    is_waypoint=False,
                    transit_mode_before=mode_for_this,
                )
            )
            continue

        if to_match and not span_match:
            stops.append(
                PlaceStop(
                    place_slug=place_slug,
                    start_time=time(0, 0),
                    end_time=_parse_hhmm(to_match.group(1)),
                    is_waypoint=False,
                    transit_mode_before=mode_for_this,
                )
            )
            continue

        if from_match:
            stops.append(
                PlaceStop(
                    place_slug=place_slug,
                    start_time=_parse_hhmm(from_match.group(1)),
                    end_time=time(23, 55),
                    is_waypoint=False,
                    transit_mode_before=mode_for_this,
                )
            )
            continue

        if span_match:
            stops.append(
                PlaceStop(
                    place_slug=place_slug,
                    start_time=_parse_hhmm(span_match.group(1)),
                    end_time=_parse_hhmm(span_match.group(2)),
                    is_waypoint=False,
                    transit_mode_before=mode_for_this,
                )
            )
            continue

        point_match = re.search(r"\b(\d{2}:\d{2})\b", after_slug_clean)
        if point_match:
            pt = _parse_hhmm(point_match.group(1))
            dt_end = (datetime.combine(date(2025, 1, 1), pt) + timedelta(minutes=5)).time()
            stops.append(
                PlaceStop(
                    place_slug=place_slug,
                    start_time=pt,
                    end_time=dt_end,
                    is_waypoint=True,
                    transit_mode_before=mode_for_this,
                )
            )
            continue

        raise ValueError(f"Could not parse time span for {place_slug!r} in clause {part!r}")

    return stops


def parse_dayplan_markdown(dayplan_path: Path, year: int = 2025) -> list[DayPlanRow]:
    """Parse `content/weeks/<week>/dayplan.md`."""
    rows: list[DayPlanRow] = []
    text = dayplan_path.read_text(encoding="utf-8")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 5:
            continue
        date_cell, day_type_cell, steps_cell, places_cell, sources_cell = cells[:5]
        if date_cell.lower() == "date" or set(date_cell) <= {"-", " "}:
            continue
        m = re.search(r"(\d{1,2})\s+([A-Za-z]{3})", date_cell)
        if not m:
            raise ValueError(f"Cannot parse date cell {date_cell!r} in {dayplan_path}")
        day_num = int(m.group(1))
        month_num = _MONTH_MAP[m.group(2).title()]
        date_iso = date(year, month_num, day_num).isoformat()

        steps_clean = steps_cell.strip()
        if steps_clean.lower().startswith("band"):
            explicit_steps = None
        else:
            num_m = re.search(r"([\d,]+)", steps_clean)
            if not num_m:
                raise ValueError(f"Cannot parse steps cell {steps_cell!r} on {date_iso}")
            explicit_steps = int(num_m.group(1).replace(",", ""))

        stops = parse_places_column(places_cell)
        rows.append(
            DayPlanRow(
                date_iso=date_iso,
                day_type_label=day_type_cell,
                explicit_steps=explicit_steps,
                stops=stops,
                raw_places=places_cell,
                sources=sources_cell,
            )
        )
    return rows


def load_year_dayplan_rows(
    dayplans_weeks_dir: Path = DEFAULT_DAYPLANS_WEEKS_DIR,
    march_hand_dayplan_md: Path = DEFAULT_DAYPLAN_MD,
) -> list[DayPlanRow]:
    """Load all 365 day plan rows from `content/dayplans/weeks/*.md`, governed on 9–15 Mar by the hand plan."""
    rows_by_date: dict[str, DayPlanRow] = {}
    for wk_file in sorted(dayplans_weeks_dir.glob("*.md")):
        for row in parse_dayplan_markdown(wk_file):
            rows_by_date[row.date_iso] = row
    if march_hand_dayplan_md.is_file():
        for row in parse_dayplan_markdown(march_hand_dayplan_md):
            rows_by_date[row.date_iso] = row
    return [rows_by_date[d] for d in sorted(rows_by_date)]


def _packed_segments(date_iso: str):
    week = PACKED_DAYS.get(date_iso)
    if week is None:
        return []
    # Use the same segment parser as conversion, after backdrop has loaded.
    if __package__ in (None, ""):
        from converter import parse_day_markdown
    else:
        from .converter import parse_day_markdown
    path = PROJECT_ROOT / "content" / "weeks" / week / "merged" / f"{date_iso}.md"
    return parse_day_markdown(path).segments


def _body_sleep_window(day: date, metrics: dict[str, Any]) -> tuple[datetime, datetime]:
    wake = datetime.combine(day, _parse_hhmm(metrics["wake_time"]), tzinfo=LONDON_TZ)
    bed = wake - timedelta(minutes=metrics["sleep_min"])
    for seg in _packed_segments(day.isoformat()):
        start = datetime.combine(day, _parse_hhmm(seg.start_hhmm), tzinfo=LONDON_TZ)
        if bed <= start < wake:
            wake = start
    previous_day = day - timedelta(days=1)
    for seg in _packed_segments(previous_day.isoformat()):
        start = datetime.combine(previous_day, _parse_hhmm(seg.start_hhmm), tzinfo=LONDON_TZ)
        if start.hour >= 18:
            bed = max(bed, start + timedelta(seconds=seg.duration_sec))
    return bed, wake


def _heart_rate_rows(
    day: date,
    metrics: dict[str, Any],
    day_type: str,
    stops: list[PlaceStop],
    bed: datetime,
    wake: datetime,
    next_bed: datetime,
) -> list[dict[str, Any]]:
    """Five-minute waking samples and half-hour sleep samples, on a UTC clock."""
    def local_clock(at: time) -> datetime:
        return datetime.combine(day, at, tzinfo=LONDON_TZ)

    cutoff = local_clock(time.min) + timedelta(days=1)
    rest, typical, peak = (metrics[key] for key in ("rhr_bpm", "hr_avg_bpm", "hr_max_bpm"))
    spans: list[tuple[datetime, datetime, int]] = []
    for previous, following in zip(stops, stops[1:]):
        p = CANON_PLACES[previous.place_slug]
        q = CANON_PLACES[following.place_slug]
        start = local_clock(previous.start_time if previous.is_waypoint else previous.end_time)
        end = local_clock(following.start_time)
        if previous.place_slug == following.place_slug or end <= start:
            continue
        if day_type == "Foot road day":
            target = peak - 16
        elif day_type in ("Riding day", "Boat day") or following.transit_mode_before == "wherry":
            target = typical + 10
        else:
            target = max(typical + 13, peak - 25)
            if p.lat is not None and p.lon is not None and q.lat is not None and q.lon is not None:
                mins = max(5, round(distance_m(p.lat, p.lon, q.lat, q.lon) / 72))
                start = max(start, end - timedelta(minutes=mins))
        spans.append((start, end, target))

    for stop in stops:
        start, end = local_clock(stop.start_time), local_clock(stop.end_time)
        if day_type in ("Playing day", "Court day") and start.hour >= 13 and stop.place_slug in (
            "the_theatre", "cross_keys_inn", "richmond_palace", "whitehall_palace",
        ):
            spans.append((start, end, peak - 6))
        elif day_type == "Rehearsal-heavy day" and stop.place_slug in ("the_theatre", "cross_keys_inn"):
            spans.append((start, end, peak - 17))
        elif day_type == "Rose day" and stop.place_slug == "the_rose":
            spans.append((start, end, typical + 3))

    for seg in _packed_segments(day.isoformat()):
        start = local_clock(_parse_hhmm(seg.start_hhmm))
        end = start + timedelta(seconds=seg.duration_sec)
        motion = (seg.heading_title + " " + seg.sense_summary).lower()
        if re.search(r"(?:walk(?:s|ed|ing)?|on foot|up the (?:path|lane|lime walk)|along the hedge)", motion):
            target = max(typical + 13, peak - 25)
        elif seg.kind in ("frame", "note"):
            target = rest + 6 if seg.surface != "stage" else typical + 3
        elif seg.kind == "meeting":
            target = typical
        else:
            continue
        spans.append((start, end, target))
    # One calm sedentary evening in the world is explicitly a high-rate interval.
    if day.isoformat() == "2025-06-29":
        spans.append((local_clock(time(21, 30)), local_clock(time(23, 15)), peak - 6))

    rng = random.Random(f"william-journal:heart-rate:{day.isoformat()}")
    output = []
    bed_utc = bed.astimezone(timezone.utc)
    wake_utc = wake.astimezone(timezone.utc)
    next_bed_utc = next_bed.astimezone(timezone.utc)
    end_utc = cutoff.astimezone(timezone.utc)
    at = local_clock(time.min).astimezone(timezone.utc)
    while at < end_utc:
        local = at.astimezone(LONDON_TZ)
        asleep = bed_utc <= at < wake_utc or at >= next_bed_utc
        if asleep:
            target = metrics["hr_min_bpm"] + 2
        else:
            active = [rate for start, end, rate in spans if start <= local < end]
            target = max(active, default=rest + 8)
        rate = min(peak, max(metrics["hr_min_bpm"], target + rng.randint(-4, 4)))
        output.append({
            "at": local.isoformat(timespec="seconds"),
            "by": "the day's count",
            "id": f"hr-{day:%Y%m%d}-{len(output):03d}",
            "kind": "reading",
            "label": "heart rate",
            "source": "apple_health",
            "type": "HKQuantityTypeIdentifierHeartRate",
            "unit": "count/min",
            "v": 1,
            "value": str(rate),
        })
        # Anchor each waking series at the recorded wake, and its first sleep
        # sample at bedtime even when the interval is off the five-minute grid.
        interval = timedelta(minutes=30 if asleep else 5)
        next_boundary = min(
            (edge for edge in (bed_utc, wake_utc, next_bed_utc) if edge > at),
            default=end_utc,
        )
        at = min(at + interval, next_boundary)
    return output


def build_body_rows_for_day(
    date_iso: str,
    day_type_key: str,
    explicit_steps: int | None = None,
    *,
    stops: list[PlaceStop] | None = None,
    next_day_type: str | None = None,
) -> list[dict[str, Any]]:
    """Build `body-records.schema.json` compliant rows for a day's `body.jsonl`."""
    metrics = generate_body_metrics_for_day(
        date_str=date_iso,
        day_type_key=day_type_key,
        explicit_steps=explicit_steps,
    )
    day_date = date.fromisoformat(date_iso)
    day_compact = day_date.strftime("%Y%m%d")
    next_date = day_date + timedelta(days=1)

    bed_local, wake_local = _body_sleep_window(day_date, metrics)
    next_metrics = generate_body_metrics_for_day(next_date.isoformat(), next_day_type or day_type_key)
    next_bed, _ = _body_sleep_window(next_date, next_metrics)
    day_start_local = datetime.combine(day_date, time.min, tzinfo=LONDON_TZ)
    day_end_local = datetime.combine(next_date, time.min, tzinfo=LONDON_TZ)

    sleep_id = f"experience-sleep-{day_compact}"
    rows: list[dict[str, Any]] = [
        {
            "assembled": (
                "assembled from this source's adjacent sleep stage intervals 30 minutes "
                "or less apart, not a session Apple Health reported"
            ),
            "by": "the day's count",
            "end": wake_local.isoformat(),
            "experience": "sleep",
            "id": sleep_id,
            "kind": "experience",
            "label": "night",
            "source": "apple_health",
            "start": bed_local.isoformat(),
            "type": "HKCategoryTypeIdentifierSleepAnalysis",
            "v": 1,
        }
    ]

    stage_cursor = bed_local.astimezone(timezone.utc)
    wake_utc = wake_local.astimezone(timezone.utc)
    stage_specs = [
        ("deep", int(metrics["deep_min"]), "HKCategoryValueSleepAnalysisAsleepDeep", "asleep deep"),
        ("core", int(metrics["core_min"]), "HKCategoryValueSleepAnalysisAsleepCore", "asleep core"),
        ("rem", int(metrics["rem_min"]), "HKCategoryValueSleepAnalysisAsleepREM", "asleep rem"),
        ("awake", int(metrics["awake_min"]), "HKCategoryValueSleepAnalysisAwake", "awake"),
    ]
    available = round((wake_utc - stage_cursor).total_seconds() / 60)
    planned = sum(mins for _, mins, _, _ in stage_specs)
    for index, (stage_slug, mins, hk_type, label) in enumerate(stage_specs):
        mins = round(mins * available / planned)
        if index == len(stage_specs) - 1:
            mins = round((wake_utc - stage_cursor).total_seconds() / 60)
        if mins <= 0:
            continue
        stage_end = stage_cursor + timedelta(minutes=mins)
        rows.append(
            {
                "by": "the day's count",
                "end": stage_end.astimezone(LONDON_TZ).isoformat(),
                "id": f"stage-{stage_slug}-{day_compact}",
                "kind": "stage",
                "label": label,
                "of": sleep_id,
                "source": "apple_health",
                "start": stage_cursor.astimezone(LONDON_TZ).isoformat(),
                "type": hk_type,
                "v": 1,
            }
        )
        stage_cursor = stage_end

    rows.extend(
        [
            {
                "by": "the day's count",
                "end": day_end_local.isoformat(),
                "id": f"count-steps-{day_compact}",
                "kind": "count",
                "label": "step count",
                "source": "apple_health",
                "start": day_start_local.isoformat(),
                "type": "HKQuantityTypeIdentifierStepCount",
                "unit": "count",
                "v": 1,
                "value": str(metrics["steps"]),
            },
            {
                "by": "the day's count",
                "end": day_end_local.isoformat(),
                "id": f"count-distance-{day_compact}",
                "kind": "count",
                "label": "distance walking running",
                "source": "apple_health",
                "start": day_start_local.isoformat(),
                "type": "HKQuantityTypeIdentifierDistanceWalkingRunning",
                "unit": "km",
                "v": 1,
                "value": f"{metrics['distance_km']:.2f}",
            },
            {
                "by": "the day's count",
                "end": day_end_local.isoformat(),
                "id": f"count-energy-{day_compact}",
                "kind": "count",
                "label": "active energy burned",
                "source": "apple_health",
                "start": day_start_local.isoformat(),
                "type": "HKQuantityTypeIdentifierActiveEnergyBurned",
                "unit": "kcal",
                "v": 1,
                "value": str(metrics["active_energy_kcal"]),
            },
            {
                "at": wake_local.isoformat(),
                "by": "the day's count",
                "id": f"reading-rhr-{day_compact}",
                "kind": "reading",
                "label": "resting heart rate",
                "source": "apple_health",
                "type": "HKQuantityTypeIdentifierRestingHeartRate",
                "unit": "count/min",
                "v": 1,
                "value": str(metrics["rhr_bpm"]),
            },
            {
                "at": wake_local.isoformat(),
                "by": "the day's count",
                "id": f"reading-hrv-{day_compact}",
                "kind": "reading",
                "label": "heart rate variability sdnn",
                "source": "apple_health",
                "type": "HKQuantityTypeIdentifierHeartRateVariabilitySDNN",
                "unit": "ms",
                "v": 1,
                "value": str(metrics["hrv_ms"]),
            },
        ]
    )
    rows.extend(_heart_rate_rows(day_date, metrics, day_type_key, stops or [], bed_local, wake_local, next_bed))

    def _row_sort_key(r: dict[str, Any]) -> tuple[int, str]:
        begins = r.get("at") or r.get("start")
        assert isinstance(begins, str)
        dt = datetime.fromisoformat(begins)
        return (int(dt.timestamp() * 1000), r["id"])

    rows.sort(key=_row_sort_key)
    return rows


def _bearing_degrees(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlon)
    brng = math.degrees(math.atan2(y, x))
    return round((brng + 360.0) % 360.0, 1)


def build_location_segments_for_day(
    date_iso: str,
    stops: list[PlaceStop],
    prev_last_stop: PlaceStop | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Build `<seg_key> -> [header, fixes..., visits...]` for a day's `phone` stream."""
    day_date = date.fromisoformat(date_iso)
    fixes_by_seg: dict[str, list[dict[str, Any]]] = {}
    visits_by_seg: dict[str, list[dict[str, Any]]] = {}

    def _seg_for_local(dt_local: datetime) -> str:
        bucket_min = (dt_local.minute // 5) * 5
        return f"{dt_local.hour:02d}{bucket_min:02d}00_300"

    def _utc_z(dt_local: datetime) -> str:
        return dt_local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _add_fix(
        dt_local: datetime,
        lat: float,
        lon: float,
        stationary: bool,
        h_acc: float = 10.0,
        speed: float | None = None,
        course: float | None = None,
    ) -> None:
        seg = _seg_for_local(dt_local)
        fixes_by_seg.setdefault(seg, []).append(
            {
                "alt": None,
                "course": course,
                "h_acc": h_acc,
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "schema": "solstone.location.fix/1",
                "speed": speed,
                "stationary": stationary,
                "t": _utc_z(dt_local),
                "v_acc": None,
            }
        )

    def _add_visit(dt_start_local: datetime, dt_end_local: datetime, lat: float, lon: float) -> None:
        seg = _seg_for_local(dt_start_local)
        visits_by_seg.setdefault(seg, []).append(
            {
                "arrival": _utc_z(dt_start_local),
                "departure": _utc_z(dt_end_local),
                "h_acc": 12,
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "schema": "solstone.location.visit/1",
            }
        )

    for idx, stop in enumerate(stops):
        place = CANON_PLACES[stop.place_slug]
        start_local = datetime.combine(day_date, stop.start_time, tzinfo=LONDON_TZ)
        end_local = datetime.combine(day_date, stop.end_time, tzinfo=LONDON_TZ)

        if place.lat is None or place.lon is None:
            prev_concrete = next(
                (s for s in reversed(stops[:idx]) if CANON_PLACES[s.place_slug].lat is not None),
                prev_last_stop,
            )
            next_concrete = next(
                (s for s in stops[idx + 1 :] if CANON_PLACES[s.place_slug].lat is not None),
                None,
            )
            if (
                prev_concrete is not None
                and next_concrete is not None
                and CANON_PLACES[prev_concrete.place_slug].lat is not None
                and CANON_PLACES[next_concrete.place_slug].lat is not None
            ):
                p_place = CANON_PLACES[prev_concrete.place_slug]
                n_place = CANON_PLACES[next_concrete.place_slug]
                assert p_place.lat is not None and p_place.lon is not None
                assert n_place.lat is not None and n_place.lon is not None
                prev_lat, prev_lon = float(p_place.lat), float(p_place.lon)
                next_lat, next_lon = float(n_place.lat), float(n_place.lon)
                t0 = (
                    datetime.combine(day_date, prev_concrete.end_time, tzinfo=LONDON_TZ)
                    if prev_concrete in stops[:idx]
                    else datetime.combine(day_date, time(0, 0), tzinfo=LONDON_TZ)
                )
                t1 = datetime.combine(day_date, next_concrete.start_time, tzinfo=LONDON_TZ)
                total_secs = max(1.0, (t1 - t0).total_seconds())
                span_secs = max(0.0, (end_local - start_local).total_seconds())
                if date_iso == "2025-08-21" and stop.place_slug == "oxford_road":
                    sample_dts = [
                        start_local,
                        datetime.combine(day_date, time(12, 30), tzinfo=LONDON_TZ),
                        datetime.combine(day_date, time(15, 20), tzinfo=LONDON_TZ),
                        datetime.combine(day_date, time(16, 40), tzinfo=LONDON_TZ),
                        end_local,
                    ]
                elif span_secs > 600:
                    sample_dts = [
                        start_local,
                        start_local + timedelta(seconds=int(span_secs / 3)),
                        start_local + timedelta(seconds=int(2 * span_secs / 3)),
                        end_local,
                    ]
                else:
                    sample_dts = [start_local, end_local]
                speed_mps = 2.2 if stop.transit_mode_before == "wherry" else 1.35
                course_deg = _bearing_degrees(prev_lat, prev_lon, next_lat, next_lon)
                for sample_dt in sample_dts:
                    frac = min(1.0, max(0.0, (sample_dt - t0).total_seconds() / total_secs))
                    interp_lat = prev_lat + (next_lat - prev_lat) * frac
                    interp_lon = prev_lon + (next_lon - prev_lon) * frac
                    _add_fix(
                        sample_dt,
                        interp_lat,
                        interp_lon,
                        stationary=False,
                        h_acc=12.0,
                        speed=speed_mps,
                        course=course_deg,
                    )
            continue

        assert place.lat is not None and place.lon is not None
        lat, lon = float(place.lat), float(place.lon)

        if idx == 0 and stop.start_time > time(0, 0) and prev_last_stop is not None:
            prev_place = CANON_PLACES[prev_last_stop.place_slug]
            if prev_place.lat is not None and prev_place.lon is not None:
                prev_lat, prev_lon = float(prev_place.lat), float(prev_place.lon)
                prev_end_local = datetime.combine(day_date, time(0, 0), tzinfo=LONDON_TZ)
                gap_secs = (start_local - prev_end_local).total_seconds()
                if gap_secs > (0 if date_iso in PACKED_DAYS else 120) and (prev_lat != lat or prev_lon != lon):
                    steps_count = min(4, max(2, int(gap_secs // 300)))
                    speed_mps = 2.2 if stop.transit_mode_before == "wherry" else 1.35
                    course_deg = _bearing_degrees(prev_lat, prev_lon, lat, lon)
                    for step_i in range(1, steps_count):
                        frac = step_i / steps_count
                        interp_dt = prev_end_local + timedelta(seconds=int(gap_secs * frac))
                        interp_lat = prev_lat + (lat - prev_lat) * frac
                        interp_lon = prev_lon + (lon - prev_lon) * frac
                        _add_fix(
                            interp_dt,
                            interp_lat,
                            interp_lon,
                            stationary=False,
                            h_acc=12.0,
                            speed=speed_mps,
                            course=course_deg,
                        )
        elif idx > 0 and CANON_PLACES[stops[idx - 1].place_slug].lat is not None:
            prev_stop = stops[idx - 1]
            prev_place = CANON_PLACES[prev_stop.place_slug]
            assert prev_place.lat is not None and prev_place.lon is not None
            prev_lat, prev_lon = float(prev_place.lat), float(prev_place.lon)
            prev_end_local = datetime.combine(day_date, prev_stop.end_time, tzinfo=LONDON_TZ)
            gap_secs = (start_local - prev_end_local).total_seconds()
            if gap_secs > (0 if date_iso in PACKED_DAYS else 120) and (prev_lat != lat or prev_lon != lon):
                steps_count = min(4, max(2, int(gap_secs // 300)))
                speed_mps = 2.2 if stop.transit_mode_before == "wherry" else 1.35
                course_deg = _bearing_degrees(prev_lat, prev_lon, lat, lon)
                for step_i in range(1, steps_count):
                    frac = step_i / steps_count
                    interp_dt = prev_end_local + timedelta(seconds=int(gap_secs * frac))
                    interp_lat = prev_lat + (lat - prev_lat) * frac
                    interp_lon = prev_lon + (lon - prev_lon) * frac
                    _add_fix(
                        interp_dt,
                        interp_lat,
                        interp_lon,
                        stationary=False,
                        h_acc=12.0,
                        speed=speed_mps,
                        course=course_deg,
                    )

        if stop.is_waypoint:
            _add_fix(start_local, lat, lon, stationary=False, h_acc=10.0, speed=0.5, course=None)
        else:
            _add_visit(start_local, end_local, lat, lon)
            if date_iso in PACKED_DAYS:
                # The reported visit carries this dwell. Redundant fix clusters
                # appear as separate area-only reading runs beside it.
                continue
            # Emit 4 stationary fixes across 300s at arrival (satisfying stay.rs:
            # STAY_MIN_READINGS = 3, STAY_MIN_SECONDS = 300, STAY_MAX_GAP_SECONDS = 300)
            # plus a departure fix at `end_local`.
            for offset_sec in (0, 120, 240, 300):
                fix_dt = start_local + timedelta(seconds=offset_sec)
                if fix_dt <= end_local:
                    _add_fix(fix_dt, lat, lon, stationary=True, h_acc=10.0)
            if end_local > start_local + timedelta(seconds=300):
                _add_fix(end_local, lat, lon, stationary=True, h_acc=10.0)

    all_segs = sorted(set(fixes_by_seg.keys()) | set(visits_by_seg.keys()))
    result: dict[str, list[dict[str, Any]]] = {}
    for seg in all_segs:
        seg_fixes = sorted(fixes_by_seg.get(seg, []), key=lambda x: x["t"])
        seg_visits = visits_by_seg.get(seg, [])
        header = {
            "accuracy": "full",
            "fix_count": len(seg_fixes),
            "gap": False,
            "kind": "location",
            "platform": "ios",
            "schema": "solstone.location.segment/1",
            "source": "location",
            "tier": "balanced",
        }
        result[seg] = [header, *seg_fixes, *seg_visits]

    return result


def write_body_and_location_from_dayplan(
    journal_root: Path,
    dayplan_rows: list[DayPlanRow],
    registry: ContractRegistry,
) -> dict[str, int]:
    """Write `body.jsonl` and `location.jsonl` for every day in `dayplan_rows`."""
    body_segments: list[tuple[str, str]] = []
    phone_segments: list[tuple[str, str]] = []
    body_rows_total = 0
    location_fixes_total = 0
    placed_days = 0
    gap_days = 0
    prev_last_stop: PlaceStop | None = None

    day_types = {
        p.date_iso: resolve_day_type_key(p.day_type_label, p.date_iso) for p in dayplan_rows
    }
    for plan in dayplan_rows:
        day_key = plan.date_iso.replace("-", "")
        day_type_key = day_types[plan.date_iso]
        next_day = date.fromisoformat(plan.date_iso) + timedelta(days=1)
        day_dir = journal_root / "chronicle" / day_key

        ah_dir = day_dir / "import.apple_health"
        if ah_dir.is_dir():
            shutil.rmtree(ah_dir)
        ph_dir = day_dir / "phone"
        if ph_dir.is_dir():
            shutil.rmtree(ph_dir)

        body_seg = "060000_300"
        rows = build_body_rows_for_day(
            date_iso=plan.date_iso,
            day_type_key=day_type_key,
            explicit_steps=plan.explicit_steps,
            stops=plan.stops,
            next_day_type=day_types.get(next_day.isoformat()),
        )
        body_label = f"chronicle/{day_key}/import.apple_health/{body_seg}/body.jsonl"
        validate_body_rows(rows, body_label, registry=registry)
        body_path = day_dir / "import.apple_health" / body_seg / "body.jsonl"
        body_path.parent.mkdir(parents=True, exist_ok=True)
        body_text = "".join(
            json.dumps(r, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n" for r in rows
        )
        body_path.write_text(body_text, encoding="utf-8")
        body_segments.append((day_key, body_seg))
        body_rows_total += len(rows)

        if not plan.stops:
            gap_days += 1
            prev_last_stop = None
            continue

        placed_days += 1
        loc_by_seg = build_location_segments_for_day(
            plan.date_iso, plan.stops, prev_last_stop=prev_last_stop
        )
        prev_last_stop = plan.stops[-1]
        for loc_seg, lines in sorted(loc_by_seg.items()):
            loc_label = f"chronicle/{day_key}/phone/{loc_seg}/location.jsonl"
            validate_location_lines(lines, loc_label)
            loc_path = day_dir / "phone" / loc_seg / "location.jsonl"
            loc_path.parent.mkdir(parents=True, exist_ok=True)
            loc_text = "".join(
                json.dumps(line, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
                for line in lines
            )
            loc_path.write_text(loc_text, encoding="utf-8")
            phone_segments.append((day_key, loc_seg))
            location_fixes_total += lines[0]["fix_count"]

    write_stream_chain(
        journal_root=journal_root,
        stream_name="import.apple_health",
        segments=body_segments,
        source="import.apple_health",
        registry=registry,
        kind="observer",
    )
    write_stream_chain(
        journal_root=journal_root,
        stream_name="phone",
        segments=phone_segments,
        source=None,
        registry=registry,
        kind="observer",
        platform="ios",
    )

    for stream_name, source_name in (("obsidian", "obsidian"), ("screenshots", "screenshots")):
        existing_segs: list[tuple[str, str]] = []
        chron_root = journal_root / "chronicle"
        if chron_root.is_dir():
            for d_dir in sorted(chron_root.iterdir()):
                s_dir = d_dir / stream_name
                if s_dir.is_dir():
                    for seg_d in sorted(s_dir.iterdir()):
                        if seg_d.is_dir():
                            existing_segs.append((d_dir.name, seg_d.name))
        if existing_segs:
            write_stream_chain(
                journal_root=journal_root,
                stream_name=stream_name,
                segments=existing_segs,
                source=source_name,
                registry=registry,
                kind="observer",
            )
        else:
            record = {
                "name": stream_name,
                "kind": "observer",
                "host": None,
                "platform": None,
                "created_at": SETUP_COMPLETED_AT_MS,
                "last_day": None,
                "last_segment": None,
                "seq": 1,
                "cid": _deterministic_cid(stream_name),
                "source": source_name,
            }
            validate_stream_record(record, f"streams/{stream_name}.json")
            _write_json_pretty(journal_root / "streams" / f"{stream_name}.json", record)

    return {
        "days": len(dayplan_rows),
        "placed_days": placed_days,
        "gap_days": gap_days,
        "body_segments": len(body_segments),
        "body_rows": body_rows_total,
        "phone_segments": len(phone_segments),
        "location_fixes": location_fixes_total,
    }


PLACE_RADIUS_M = 50.0
PLACE_SPACING_M = 100.0
NEAREST_CANON_PLACE_MAX_M = 100.0


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres matching `solstone-core-location/src/places.rs:439-456`."""
    earth_radius_m = 6_371_000.0
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * (math.sin(dlon / 2.0) ** 2)
    )
    return 2.0 * earth_radius_m * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


def _seed_place_id(day: str, device: str, start: str | None, lat: float, lon: float) -> str:
    """Compute the 12-hex-char place id matching `solstone-core-location/src/places.rs:458-466`."""
    start_str = f"Some({int(datetime.fromisoformat(start).timestamp())})" if start else "None"
    payload = f"{day}|{device}|{start_str}|{lat:.6f}|{lon:.6f}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def derive_and_name_places(journal_root: Path) -> dict[str, Any]:
    """Derive 50 m stay clusters across `chronicle/*/phone/*/location.jsonl` matching
    `solstone-core-location/src/places.rs` (`recompute_holding`) and assign each derived
    place the display name of the nearest `world/world.md` § 4 place within 100 m
    (with `alias: "home"` on the cluster holding `ansell_house`).
    """
    stays: list[dict[str, Any]] = []
    chronicle_dir = journal_root / "chronicle"
    if chronicle_dir.is_dir():
        for day_dir in sorted(chronicle_dir.iterdir()):
            if not day_dir.is_dir():
                continue
            day = day_dir.name
            phone_dir = day_dir / "phone"
            if not phone_dir.is_dir():
                continue
            day_visits: list[dict[str, Any]] = []
            for seg_dir in sorted(phone_dir.iterdir()):
                loc_file = seg_dir / "location.jsonl"
                if not loc_file.is_file():
                    continue
                for line in loc_file.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    if rec.get("schema") == "solstone.location.visit/1":
                        day_visits.append(
                            {
                                "day": day,
                                "device": "stream:phone",
                                "start": rec.get("arrival"),
                                "end": rec.get("departure"),
                                "latitude": float(rec["lat"]),
                                "longitude": float(rec["lon"]),
                                "margin_m": float(rec["h_acc"]),
                            }
                        )
            day_visits.sort(key=lambda v: v["start"] or "")
            stays.extend(day_visits)

    eligible = [s for s in stays if s["margin_m"] <= PLACE_RADIUS_M]
    used: set[int] = set()
    candidates: list[dict[str, Any]] = []

    def distance(a: dict[str, Any], b: dict[str, Any]) -> float:
        return distance_m(a["latitude"], a["longitude"], b["latitude"], b["longitude"])

    for seed_index, seed in enumerate(eligible):
        if seed_index in used:
            continue
        group = [seed_index]
        for index in range(seed_index + 1, len(eligible)):
            if index not in used and all(
                distance(eligible[index], eligible[member]) <= PLACE_RADIUS_M for member in group
            ):
                group.append(index)
        days = sorted({eligible[index]["day"] for index in group})
        if len(days) < 2:
            continue
        lat = sum(eligible[index]["latitude"] for index in group) / len(group)
        lon = sum(eligible[index]["longitude"] for index in group) / len(group)
        if any(distance_m(c["latitude"], c["longitude"], lat, lon) <= PLACE_SPACING_M for c in candidates):
            continue
        used.update(group)
        pid = _seed_place_id(
            seed["day"], seed["device"], seed["start"], seed["latitude"], seed["longitude"]
        )
        candidates.append({"id": pid, "latitude": lat, "longitude": lon, "days": days})

    ansell = CANON_PLACES["ansell_house"]
    assert ansell.lat is not None and ansell.lon is not None

    places_rows: list[dict[str, Any]] = []
    matched_details: list[dict[str, Any]] = []
    unmatched_places: list[dict[str, Any]] = []

    for cand in candidates:
        clat = cand["latitude"]
        clon = cand["longitude"]
        holds_ansell = (
            distance_m(clat, clon, float(ansell.lat), float(ansell.lon)) <= PLACE_RADIUS_M
        )

        best_slug: str | None = None
        best_name: str | None = None
        best_dist = float("inf")
        within_50m: list[str] = []
        for slug, cp in CANON_PLACES.items():
            if cp.lat is None or cp.lon is None:
                continue
            d_m = distance_m(clat, clon, float(cp.lat), float(cp.lon))
            if d_m <= PLACE_RADIUS_M:
                within_50m.append(slug)
            if d_m < best_dist:
                best_dist = d_m
                best_slug = slug
                best_name = cp.name

        if holds_ansell:
            chosen_slug = "ansell_house"
            chosen_name: str | None = ansell.name
            chosen_alias: str | None = "home"
        elif best_dist <= NEAREST_CANON_PLACE_MAX_M and best_name is not None:
            chosen_slug = best_slug
            chosen_name = best_name
            chosen_alias = None
        else:
            chosen_slug = None
            chosen_name = None
            chosen_alias = None
            unmatched_places.append(
                {
                    "id": cand["id"],
                    "latitude": clat,
                    "longitude": clon,
                    "days_count": len(cand["days"]),
                    "nearest_slug": best_slug,
                    "nearest_distance_m": round(best_dist, 2),
                }
            )

        places_rows.append(
            {
                "id": cand["id"],
                "latitude": clat,
                "longitude": clon,
                "name": chosen_name,
                "alias": chosen_alias,
                "hidden": False,
                "days": cand["days"],
            }
        )
        matched_details.append(
            {
                "id": cand["id"],
                "slug": chosen_slug,
                "name": chosen_name,
                "alias": chosen_alias,
                "distance_m": round(best_dist, 2),
                "days_count": len(cand["days"]),
                "canon_places_within_50m": within_50m,
            }
        )

    # Sort identically to `solstone-core-location/src/places.rs:429-435`:
    # `right.days.len().cmp(&left.days.len()).then_with(|| left.id.cmp(&right.id))`
    places_rows.sort(key=lambda p: (-len(p["days"]), p["id"]))
    matched_details.sort(key=lambda p: (-p["days_count"], p["id"]))

    return {
        "store": {
            "version": 1,
            "places": places_rows,
        },
        "derived_count": len(places_rows),
        "named_count": sum(1 for p in places_rows if p["name"] is not None),
        "unmatched_places": unmatched_places,
        "matched_details": matched_details,
    }


def write_places_store(journal_root: Path) -> dict[str, Any]:
    """Write `solstone/apps/map/places.json` for `journal_root`."""
    res = derive_and_name_places(journal_root)
    places_path = journal_root / "solstone" / "apps" / "map" / "places.json"
    _write_json_pretty(places_path, res["store"])
    return {
        "places_path": str(places_path),
        "derived_count": res["derived_count"],
        "named_count": res["named_count"],
        "unmatched_count": len(res["unmatched_places"]),
        "unmatched_places": res["unmatched_places"],
    }


def refresh_body_and_places(
    journal_root: Path = DEFAULT_OUTPUT_JOURNAL,
    solstone_repo: Path = DEFAULT_SOLSTONE_REPO,
    only_days: set[str] | None = None,
) -> dict[str, Any]:
    """Refresh all 365 days' `body.jsonl` (`import.apple_health`), `phone/*/location.jsonl`,
    and `solstone/apps/map/places.json` in `journal_root` without modifying converted week segments.
    """
    registry = ContractRegistry(solstone_repo=solstone_repo)
    dayplan_rows = load_year_dayplan_rows()
    body_segments: list[tuple[str, str]] = []
    phone_segments: list[tuple[str, str]] = []
    body_rows_total = 0
    location_fixes_total = 0
    prev_last_stop: PlaceStop | None = None

    day_types = {
        p.date_iso: resolve_day_type_key(p.day_type_label, p.date_iso) for p in dayplan_rows
    }
    for plan in dayplan_rows:
        day_key = plan.date_iso.replace("-", "")
        day_type_key = day_types[plan.date_iso]
        next_day = date.fromisoformat(plan.date_iso) + timedelta(days=1)
        day_dir = journal_root / "chronicle" / day_key
        ah_dir = day_dir / "import.apple_health"
        ph_dir = day_dir / "phone"

        if only_days is not None and plan.date_iso not in only_days:
            if ah_dir.is_dir():
                for seg_dir in sorted(ah_dir.iterdir()):
                    if seg_dir.is_dir() and (seg_dir / "body.jsonl").is_file():
                        body_segments.append((day_key, seg_dir.name))
            if ph_dir.is_dir():
                for seg_dir in sorted(ph_dir.iterdir()):
                    if seg_dir.is_dir() and (seg_dir / "location.jsonl").is_file():
                        phone_segments.append((day_key, seg_dir.name))
            prev_last_stop = plan.stops[-1] if plan.stops else None
            continue

        if ah_dir.is_dir():
            shutil.rmtree(ah_dir)
        if ph_dir.is_dir():
            shutil.rmtree(ph_dir)

        body_seg = "060000_300"
        rows = build_body_rows_for_day(
            date_iso=plan.date_iso,
            day_type_key=day_type_key,
            explicit_steps=plan.explicit_steps,
            stops=plan.stops,
            next_day_type=day_types.get(next_day.isoformat()),
        )
        body_label = f"chronicle/{day_key}/import.apple_health/{body_seg}/body.jsonl"
        validate_body_rows(rows, body_label, registry=registry)
        body_path = day_dir / "import.apple_health" / body_seg / "body.jsonl"
        body_path.parent.mkdir(parents=True, exist_ok=True)
        body_text = "".join(
            json.dumps(r, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
            for r in rows
        )
        body_path.write_text(body_text, encoding="utf-8")
        body_segments.append((day_key, body_seg))
        body_rows_total += len(rows)

        if not plan.stops:
            prev_last_stop = None
            continue

        loc_by_seg = build_location_segments_for_day(
            plan.date_iso, plan.stops, prev_last_stop=prev_last_stop
        )
        prev_last_stop = plan.stops[-1]
        for loc_seg, lines in sorted(loc_by_seg.items()):
            loc_label = f"chronicle/{day_key}/phone/{loc_seg}/location.jsonl"
            validate_location_lines(lines, loc_label)
            loc_path = day_dir / "phone" / loc_seg / "location.jsonl"
            loc_path.parent.mkdir(parents=True, exist_ok=True)
            loc_text = "".join(
                json.dumps(line, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
                for line in lines
            )
            loc_path.write_text(loc_text, encoding="utf-8")
            phone_segments.append((day_key, loc_seg))
            location_fixes_total += lines[0]["fix_count"]

    write_stream_chain(
        journal_root=journal_root,
        stream_name="import.apple_health",
        segments=body_segments,
        source="import.apple_health",
        registry=registry,
        kind="observer",
    )
    write_stream_chain(
        journal_root=journal_root,
        stream_name="phone",
        segments=phone_segments,
        source=None,
        registry=registry,
        kind="observer",
        platform="ios",
    )
    write_device_descriptions(journal_root)
    places_summary = write_places_store(journal_root)
    return {
        "days": len(dayplan_rows),
        "body_segments": len(body_segments),
        "body_rows": body_rows_total,
        "phone_segments": len(phone_segments),
        "location_fixes": location_fixes_total,
        "places": places_summary,
    }


def generate_backdrop(
    output_journal: Path = DEFAULT_OUTPUT_JOURNAL,
    calendar_json: Path = DEFAULT_CALENDAR_JSON,
    dayplan_md: Path | None = None,
    solstone_repo: Path = DEFAULT_SOLSTONE_REPO,
) -> dict[str, Any]:
    """Run the full backdrop generator into `output_journal`."""
    registry = ContractRegistry(solstone_repo=solstone_repo)
    output_journal.mkdir(parents=True, exist_ok=True)

    write_journal_config(output_journal)
    ent_stats = write_entities_and_facets(output_journal)
    cal_stats = write_calendar_backdrop(output_journal, calendar_json, registry)
    if dayplan_md is None:
        dayplan_rows = load_year_dayplan_rows()
    elif dayplan_md.is_dir():
        dayplan_rows = load_year_dayplan_rows(dayplans_weeks_dir=dayplan_md)
    else:
        dayplan_rows = parse_dayplan_markdown(dayplan_md)
    body_loc_stats = write_body_and_location_from_dayplan(output_journal, dayplan_rows, registry)
    write_device_descriptions(output_journal)
    places_stats = write_places_store(output_journal)

    return {
        "output_journal": str(output_journal),
        "entities_and_facets": ent_stats,
        "calendar": cal_stats,
        "body_and_location": body_loc_stats,
        "places": places_stats,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the William journal backdrop tree.")
    parser.add_argument(
        "--week",
        type=str,
        default="2025-03-09",
        help="Optional week folder name (retained for CLI compatibility).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_JOURNAL,
        help="Destination journal root directory (defaults to build/journal).",
    )
    parser.add_argument(
        "--calendar",
        type=Path,
        default=DEFAULT_CALENDAR_JSON,
        help="Path to merged calendar.json.",
    )
    parser.add_argument(
        "--dayplan",
        type=Path,
        default=None,
        help="Optional single dayplan.md or weeks directory (defaults to full 365-day year plan).",
    )
    parser.add_argument(
        "--solstone-repo",
        type=Path,
        default=DEFAULT_SOLSTONE_REPO,
        help="Path to pinned solstone-journal checkout.",
    )
    parser.add_argument(
        "--refresh-body-and-places",
        action="store_true",
        help="Refresh all 365 days' body.jsonl and solstone/apps/map/places.json in --output without touching converted weeks.",
    )
    parser.add_argument(
        "--days",
        type=str,
        default=None,
        help="Comma-separated YYYY-MM-DD dates to refresh with --refresh-body-and-places.",
    )
    args = parser.parse_args(argv)
    if args.refresh_body_and_places:
        only_days = {d.strip() for d in args.days.split(",") if d.strip()} if args.days else None
        summary = refresh_body_and_places(
            journal_root=args.output,
            solstone_repo=args.solstone_repo,
            only_days=only_days,
        )
    else:
        summary = generate_backdrop(
            output_journal=args.output,
            calendar_json=args.calendar,
            dayplan_md=args.dayplan,
            solstone_repo=args.solstone_repo,
        )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
