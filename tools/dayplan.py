#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Copyright (c) 2026 sol pbc

"""Deterministic 365-day plan generator for the William Shakespeare 1595/2025 journal.

Derives a day plan for every day of 2025 from the canon:
1. `content/threads/merged/where-he-is.md` and `world/world.md` § 7.9 (where he wakes
   and sleeps across all 365 nights, the road stages, the 12 Jun–18 Jul river ban,
   and the 13 Jun–5 Jul 600 m fear radius).
2. `world/world.md` § 6 (376 dated entries with time, place, and body/route notes).
3. `calendar/merged/calendar.json` (795 raw events expanded via `rrule` and `exdates`
   to 874 instances across 349 days, filtered by the presence rule to the 496 instances
   that record William's physical presence).
4. `world/world.md` § 7.8 (day types, step bands, seasonal parameters, special days,
   illnesses, and road distances) and § 7.9 (London walk times and dwell patterns).
5. Written default rules where the canon is silent.

Writes:
- `content/dayplans/2025.json`: structured rules, counts, disagreements, March 9–15
  comparison against `content/weeks/2025-03-09/dayplan.md`, and all 365 day records.
- `content/dayplans/weeks/<Sunday_YYYY-MM-DD>.md`: 53 Sunday-to-Saturday weekly markdown
  tables in the shape of `content/weeks/2025-03-09/dayplan.md`.
- `content/dayplans/index.md`: human-readable summary of rules, counts, disagreements,
  March comparison, and index links to all 53 weekly files.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
import hashlib
import json
from pathlib import Path
import random
import re
import sys
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from backdrop import DayPlanRow, PlaceStop, parse_dayplan_markdown, parse_places_column  # type: ignore[import-not-found]
    from world_data import CANON_PLACES, DAY_TYPE_STEP_BANDS, resolve_day_type_key, season_body_params, sleeping_place_for_night  # type: ignore[import-not-found]
else:
    from .backdrop import DayPlanRow, PlaceStop, parse_dayplan_markdown, parse_places_column
    from .world_data import CANON_PLACES, DAY_TYPE_STEP_BANDS, resolve_day_type_key, season_body_params, sleeping_place_for_night


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORLD_MD = PROJECT_ROOT / "world" / "world.md"
DEFAULT_CALENDAR_JSON = PROJECT_ROOT / "calendar" / "merged" / "calendar.json"
DEFAULT_WHERE_HE_IS_MD = PROJECT_ROOT / "content" / "threads" / "merged" / "where-he-is.md"
DEFAULT_MARCH_DAYPLAN_MD = PROJECT_ROOT / "content" / "weeks" / "2025-03-09" / "dayplan.md"
DEFAULT_DAYPLANS_DIR = PROJECT_ROOT / "content" / "dayplans"

# Walk time in minutes from the day's home base (ansell_house, henley_street, or the_feathers_richmond)
# derived from world/world.md § 7.9 ("London distances on foot" and "Dwell patterns").
WALK_MIN_FROM_HOME: dict[str, int] = {
    "ansell_house": 0,
    "st_helens_church": 2,
    "crosby_place": 3,
    "bull_inn": 5,
    "split_hazel": 5,
    "bishopsgate": 5,
    "bedlam": 8,
    "cross_keys_inn": 10,
    "leadenhall": 8,
    "tower_hill": 15,
    "old_swan_stairs": 15,
    "the_curtain": 18,
    "pauls_churchyard": 20,
    "the_theatre": 20,
    "burbage_house_holywell": 20,
    "the_jackdaw": 20,
    "st_leonards_shoreditch": 22,
    "finsbury_fields": 15,
    "the_bell_carter_lane": 20,
    "fields_printing_house": 25,
    "st_johns_clerkenwell": 30,
    "smithfield": 25,
    "southampton_house": 35,
    "grays_inn": 35,
    "somerset_house": 35,
    "london_bridge": 18,
    "the_rose": 30,
    "southwark_market": 25,
    "paris_garden_swan": 35,
    "whitehall_palace": 50,
    "whitehall_tiltyard": 50,
    "canon_row": 50,
    "westminster_hall": 50,
    # Stratford (§ 7.9 "Stratford day")
    "henley_street": 0,
    "high_cross_market": 5,
    "stratford_fire_ground": 5,
    "guild_chapel_school": 8,
    "new_place": 8,
    "clopton_bridge": 12,
    "holy_trinity": 12,
    "hewlands_shottery": 25,
    # Richmond (§ 7.9 "Richmond, 24–29 December")
    "the_feathers_richmond": 0,
    "richmond_palace": 5,
}

# Default dwell in minutes for a § 6 point-in-time entry when no end time is stated (§ 7.9)
DEFAULT_DWELL_MIN: dict[str, int] = {
    "st_helens_church": 120,
    "holy_trinity": 120,
    "pauls_churchyard": 60,
    "fields_printing_house": 60,
    "the_bell_carter_lane": 40,
    "st_johns_clerkenwell": 60,
    "leadenhall": 45,
    "finsbury_fields": 60,
    "bishopsgate": 30,
    "crosby_place": 30,
    "bull_inn": 90,
    "split_hazel": 90,
    "the_jackdaw": 75,
    "burbage_house_holywell": 90,
    "the_theatre": 120,
    "cross_keys_inn": 120,
    "the_rose": 150,
    "paris_garden_swan": 60,
    "old_swan_stairs": 30,
    "tower_hill": 45,
    "westminster_hall": 90,
    "whitehall_palace": 90,
    "whitehall_tiltyard": 120,
    "canon_row": 180,
    "somerset_house": 60,
    "southampton_house": 30,
    "grays_inn": 90,
    "smithfield": 120,
    "the_curtain": 60,
    "st_leonards_shoreditch": 60,
    "high_cross_market": 90,
    "stratford_fire_ground": 60,
    "guild_chapel_school": 60,
    "new_place": 45,
    "clopton_bridge": 30,
    "hewlands_shottery": 90,
    "richmond_palace": 150,
}

# Explicit daily step counts fixed by world/world.md § 7.8 ("Special days" and "The long roads")
# and § 6 dated entry body lines.
EXPLICIT_STEPS_BY_DATE: dict[str, tuple[int, str]] = {
    "2025-01-13": (2900, "W005"),
    "2025-01-15": (3100, "S006, § 7.8"),
    "2025-01-17": (9400, "S007, § 7.8"),
    "2025-01-18": (900, "G006, § 7.8"),
    "2025-01-19": (1400, "W006"),
    "2025-01-22": (5400, "W111"),
    "2025-01-29": (9800, "W113"),
    "2025-02-09": (8700, "W011"),
    "2025-02-14": (11800, "S016, § 7.8"),
    "2025-02-20": (10900, "W015, § 7.8"),
    "2025-02-21": (2700, "S019, § 7.8"),
    "2025-03-04": (9900, "S022"),
    "2025-03-08": (6800, "W019"),
    "2025-03-10": (8200, "W118"),
    "2025-03-15": (9600, "W119, § 7.8"),
    "2025-03-17": (10400, "W021"),
    "2025-03-21": (7400, "W023"),
    "2025-03-26": (5900, "S030a"),
    "2025-03-27": (6400, "S030b"),
    "2025-03-28": (5100, "S030c"),
    "2025-03-30": (7200, "W027"),
    "2025-04-03": (9800, "W028"),
    "2025-04-08": (4800, "W032a"),
    "2025-04-10": (5600, "W032c"),
    "2025-04-20": (5200, "S035, § 7.8"),
    "2025-04-21": (11600, "S036"),
    "2025-04-24": (10800, "W126"),
    "2025-05-15": (14100, "W130"),
    "2025-05-16": (9000, "G037"),
    "2025-05-17": (3300, "W042, § 7.8"),
    "2025-05-20": (12600, "W043, § 7.8"),
    "2025-05-25": (8900, "W045"),
    "2025-06-03": (5800, "S053"),
    "2025-06-09": (11200, "S056"),
    "2025-06-13": (3900, "S059a, § 7.8"),
    "2025-06-16": (8100, "S061"),
    "2025-06-29": (2100, "S069, § 7.8"),
    "2025-07-01": (9700, "W300"),
    "2025-07-06": (4100, "W301"),
    "2025-07-10": (12800, "W056"),
    "2025-07-12": (11900, "S071"),
    "2025-07-17": (14300, "W304"),
    "2025-07-21": (15600, "S074"),
    "2025-07-22": (8200, "G053"),
    "2025-07-24": (1400, "S077, § 7.8"),
    "2025-07-25": (13100, "W308"),
    "2025-07-27": (3600, "W060"),
    "2025-07-28": (58500, "W061, § 7.8"),
    "2025-07-29": (60700, "W062, § 7.8"),
    "2025-07-30": (46000, "W063, § 7.8"),
    "2025-07-31": (44000, "W064, § 7.8"),
    "2025-08-01": (3100, "S079"),
    "2025-08-02": (5200, "W330"),
    "2025-08-03": (6400, "W065"),
    "2025-08-04": (1900, "G058"),
    "2025-08-05": (10800, "S080"),
    "2025-08-07": (9600, "W066"),
    "2025-08-08": (7300, "W331"),
    "2025-08-09": (8800, "W067, § 7.8"),
    "2025-08-10": (7800, "G060"),
    "2025-08-12": (9200, "W069, § 7.8"),
    "2025-08-13": (400, "W332, § 7.8"),
    "2025-08-14": (700, "W070, § 7.8"),
    "2025-08-15": (950, "§ 7.8 400–1,200 band"),
    "2025-08-16": (2900, "W071"),
    "2025-08-17": (4100, "W072"),
    "2025-08-18": (30000, "W073a, § 7.8"),
    "2025-08-19": (43500, "W073b, § 7.8"),
    "2025-08-20": (66500, "W073c, § 7.8"),
    "2025-08-21": (60500, "W073d, § 7.8"),
    "2025-08-22": (6800, "W075"),
    "2025-08-24": (14200, "S082, § 7.8"),
    "2025-08-25": (11900, "S083"),
    "2025-08-27": (7200, "W076, § 7.8"),
    "2025-08-29": (12300, "S085"),
    "2025-08-31": (4400, "W077"),
    "2025-09-03": (3800, "W333"),
    "2025-09-04": (11400, "S084"),
    "2025-09-06": (10600, "W078"),
    "2025-09-07": (8900, "W079"),
    "2025-09-09": (10200, "W080"),
    "2025-09-11": (13300, "W334"),
    "2025-09-14": (5600, "W336"),
    "2025-09-20": (11100, "W083"),
    "2025-09-22": (12400, "S090"),
    "2025-09-27": (9400, "G073"),
    "2025-09-28": (2300, "W339"),
    "2025-09-30": (6300, "W340"),
    "2025-10-02": (12900, "W085, § 7.8"),
    "2025-10-14": (1900, "W089, § 7.8"),
    "2025-10-15": (1400, "W404"),
    "2025-10-16": (2100, "§ 7.8 1,200–2,800 band"),
    "2025-10-18": (6400, "S099"),
    "2025-10-23": (13300, "W406"),
    "2025-11-06": (11400, "W409"),
    "2025-11-08": (9900, "W092"),
    "2025-11-17": (15800, "S106, § 7.8"),
    "2025-11-23": (2600, "M046"),
    "2025-11-28": (11900, "S108"),
    "2025-12-06": (13400, "W100, § 7.8"),
    "2025-12-09": (16900, "S112b, § 7.8"),
    "2025-12-17": (9800, "G095"),
    "2025-12-21": (7300, "S113"),
    "2025-12-22": (6900, "W106"),
    "2025-12-24": (6200, "W107, § 7.8"),
    "2025-12-25": (4800, "S114, § 7.8"),
    "2025-12-26": (7500, "S115a, § 7.8"),
    "2025-12-27": (8200, "S115b, § 7.8"),
    "2025-12-28": (7900, "S115c, § 7.8"),
    "2025-12-29": (5400, "W108, § 7.8"),
}

_HDR_RE = re.compile(
    r"^\*\*(?P<id>[A-Z]+\d+[a-z]?) · (?P<date>\d{4}-\d{2}-\d{2}) \((?P<wd>[A-Za-z]{3})\) · "
    r"(?P<time>\d{2}:\d{2}(?:[0-9:–, ]|and)*?) · (?P<place>[a-z0-9_]+) · (?P<title>.+?)\*\*\s*$"
)

_WD_MAP = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}


def _hm_to_min(hm: str) -> int:
    h, m = hm.strip().split(":")
    return int(h) * 60 + int(m)


def _min_to_hm(total_min: int) -> str:
    clamped = max(0, min(23 * 60 + 55, total_min))
    return f"{clamped // 60:02d}:{clamped % 60:02d}"


def parse_world_sec6_entries(world_md_path: Path = DEFAULT_WORLD_MD) -> list[dict[str, Any]]:
    """Parse all 376 dated entries in `world/world.md` § 6."""
    lines = world_md_path.read_text(encoding="utf-8").splitlines()
    entries: list[dict[str, Any]] = []
    in_sec6 = False
    cur: dict[str, Any] | None = None

    for line_no, line in enumerate(lines, 1):
        if line.startswith("## 6. "):
            in_sec6 = True
        elif line.startswith("## 7. "):
            if cur is not None:
                entries.append(cur)
                cur = None
            break
        if not in_sec6:
            continue
        m = _HDR_RE.match(line)
        if m:
            if cur is not None:
                entries.append(cur)
            cur = {
                "line": line_no,
                "header": line.strip(),
                "id": m.group("id"),
                "date": m.group("date"),
                "weekday": m.group("wd"),
                "time": m.group("time").strip(),
                "place_slug": m.group("place").strip(),
                "title": m.group("title").strip(),
                "body_lines": [],
            }
        elif cur is not None:
            if line.startswith("### ") or line.startswith("#### Week "):
                entries.append(cur)
                cur = None
            else:
                cur["body_lines"].append(line)

    for e in entries:
        e["body"] = "\n".join(e.pop("body_lines")).strip()
    return entries


def expand_calendar_events(calendar_json_path: Path = DEFAULT_CALENDAR_JSON) -> list[dict[str, Any]]:
    """Load `calendar.json` (795 raw events) and expand `rrule` events with `exdates` (874 instances)."""
    payload = json.loads(calendar_json_path.read_text(encoding="utf-8"))
    raw_events = payload["events"] if isinstance(payload, dict) else payload
    expanded: list[dict[str, Any]] = []

    for ev in raw_events:
        rrule = ev.get("rrule")
        if not rrule:
            item = dict(ev)
            item["instance_date"] = ev["date"]
            item["is_expanded"] = False
            expanded.append(item)
            continue

        parts = dict(p.split("=") for p in rrule.split(";"))
        byday = _WD_MAP[parts["BYDAY"]]
        until_str = parts["UNTIL"][:8]
        until_date = date(int(until_str[:4]), int(until_str[4:6]), int(until_str[6:8]))
        cur_d = date.fromisoformat(ev["date"])
        exdates = set(ev.get("exdates") or [])
        while cur_d <= until_date:
            d_str = cur_d.isoformat()
            if cur_d.weekday() == byday and d_str not in exdates:
                item = dict(ev)
                item["instance_date"] = d_str
                item["is_expanded"] = d_str != ev["date"]
                expanded.append(item)
            cur_d += timedelta(days=1)

    return expanded


def is_presence_calendar_event(ev: dict[str, Any]) -> tuple[bool, str]:
    """Apply the written presence rule from `status`, `all_day`, `place_slug`, `layer`, `why`, `organizer`, `attendees`, and `title`."""
    if ev.get("status") != "confirmed":
        return False, "cancelled (status != confirmed)"
    if ev.get("all_day"):
        return False, "all-day banner/span (all_day == true)"
    if not ev.get("place_slug"):
        return False, "no place_slug on event"

    layer = ev.get("layer")
    attendees = ev.get("attendees") or []
    organizer = ev.get("organizer")
    title = ev.get("title") or ""

    if layer == "rival_bill":
        if "william_shakespeare" in attendees:
            return True, "rival_bill with william_shakespeare in attendees ('He means to stand in the yard, and does')"
        return False, "rival_bill without william_shakespeare in attendees ('The bill, not an attendance. He reads it and does not go.')"

    if layer == "money":
        if organizer == "william_shakespeare" or "william_shakespeare" in attendees:
            return True, "money event with william_shakespeare as organizer/attendee"
        return False, "money charge with organizer dorcas_ansell and attendees null ('Firing and washing, vj d.')"

    if layer == "company_play":
        if "(I play)" in title:
            return True, "company_play with '(I play)' in title"
        return False, "company_play stock bill without '(I play)' (William not cast; world § 7.1 'with (I play) on about four days in six')"

    return True, f"confirmed timed {layer} event with place_slug"


@dataclass(frozen=True)
class VisitSpan:
    place_slug: str
    start_min: int
    end_min: int
    source_tag: str
    is_waypoint: bool = False
    prefix_note: str | None = None
    suffix_note: str | None = None


# Curated multi-stop / road / special overrides where Rank 1 (`where-he-is.md`) or Rank 2 (§ 6 prose + § 7.9 routes)
# specifies the exact sequence of canonical § 4 stops across the day.
def _road_and_special_day_itineraries() -> dict[str, dict[str, Any]]:
    return {
        # Jan 4: W001 overrides cal-0009 (11:00–11:30 bishopsgate) -> crosby_place 11:00–11:30; cal-0012 Reckoning 16:45–18:00
        "2025-01-04": {
            "day_type": "Writing day at the lodging",
            "places_in_order": (
                "`ansell_house` to 10:55 · `crosby_place` 11:00–11:30 (W001) · `ansell_house` 11:35–16:35 "
                "· `cross_keys_inn` 16:45–18:00 (cal-0012) · `ansell_house` from 18:10"
            ),
            "sources": "§ 6 W001; cal-0012 (W001 overrides cal-0009)",
        },
        # Jan 18: G006 worst day of the cold, stays abed, Cowley plays Egeon (overrides cal-0012 Reckoning)
        "2025-01-18": {
            "day_type": "Household and rest",
            "places_in_order": "`ansell_house` all day (G006, abed with fever; Cowley plays Egeon)",
            "sources": "§ 6 G006; § 7.8 Special days (overrides cal-0012)",
        },
        # Jan 19: W006 abed with cold, cal-0045 cancelled
        "2025-01-19": {
            "day_type": "Household and rest",
            "places_in_order": "`ansell_house` all day (W006, abed; cal-0045 cancelled)",
            "sources": "§ 6 W006; cal-0045 (cancelled)",
        },
        # Jan 23: S008a walk west with Bryan to westminster_hall 10:00 (cal-0057), back east for S008b at cross_keys_inn 14:00 (overrides cal-0056 Rehearsal)
        "2025-01-23": {
            "day_type": "Playing day",
            "places_in_order": (
                "`ansell_house` to 09:05 · `westminster_hall` 10:00–11:30 (S008a, cal-0057) "
                "· `cross_keys_inn` 14:00–16:30 (S008b, cal-0058) · `ansell_house` from 16:45"
            ),
            "sources": "§ 6 S008a, S008b; cal-0057, cal-0058 (S008a overrides cal-0056)",
        },
        # Feb 25: G013 at the_theatre 10:00–12:00 (overrides cal-0138 Rehearsal at cross_keys_inn)
        "2025-02-25": {
            "day_type": "Playing day",
            "places_in_order": (
                "`ansell_house` to 09:40 · `the_theatre` 10:00–12:00 (G013, cal-0139) "
                "· `cross_keys_inn` 14:00–16:30 (cal-0140) · `ansell_house` from 16:45"
            ),
            "sources": "§ 6 G013; cal-0139, cal-0140 (G013 overrides cal-0138)",
        },
        # Mar 4: S022 Shrove Tuesday last play at cross_keys_inn 14:00–18:00 (overrides cal-0162 Evening prayer)
        "2025-03-04": {
            "day_type": "Playing day",
            "places_in_order": (
                "`ansell_house` to 08:50 · `cross_keys_inn` 09:00–11:00 (cal-0159) · `ansell_house` 11:15–13:45 "
                "· `cross_keys_inn` 14:00–18:00 (S022, cal-0160) · `ansell_house` from 18:20"
            ),
            "sources": "§ 6 S022; cal-0159, cal-0160 (S022 overrides cal-0162)",
        },
        # Mar 15: W119 + S027 warrant day by wherry to whitehall_palace, walk to burbage_house_holywell
        "2025-03-15": {
            "day_type": "Boat day",
            "places_in_order": (
                "`ansell_house` to 07:15 · `old_swan_stairs` 07:30 · by wherry to `whitehall_palace` 08:15–10:30 (W119) "
                "· on foot by the Strand and Holborn · `burbage_house_holywell` 11:30–13:30 (S027, cal-0177) · `ansell_house` from 13:50"
            ),
            "sources": "§ 6 W119, S027; § 7.9 'The warrant, 15 March'; cal-0177",
        },
        # Lent ride out (26–28 Mar)
        "2025-03-26": {
            "day_type": "Riding day",
            "places_in_order": (
                "`ansell_house` to 05:30 · `bull_inn` 05:40–06:15 (S030a, cal-0186) · `uxbridge` 10:00–10:45 (S030a, cal-0187) "
                "· `beaconsfield` 13:00 (S030a) · `high_wycombe` from 15:30 (S030a, cal-0188)"
            ),
            "sources": "where-he-is.md; § 6 S030a; § 7.8, § 7.9; cal-0186, cal-0187, cal-0188",
        },
        "2025-03-27": {
            "day_type": "Riding day",
            "places_in_order": (
                "`high_wycombe` to 05:30 (S030b, cal-0189) · `oxford` 17:45–19:15 (S030b, W025, cal-0190) "
                "· `woodstock` from 20:40 (W025, cal-0191)"
            ),
            "sources": "where-he-is.md; § 6 S030b, W025; § 7.8, § 7.9; cal-0189, cal-0190, cal-0191",
        },
        "2025-03-28": {
            "day_type": "Riding day",
            "places_in_order": (
                "`woodstock` to 05:30 (S030c, cal-0192) · `chipping_norton` 10:00–10:45 (S030c, cal-0193) "
                "· `shipston_on_stour` 14:30 (S030c) · `clopton_bridge` 18:10–18:25 (W026, cal-0194) "
                "· `henley_street` from 18:30 (W026, cal-0195)"
            ),
            "sources": "where-he-is.md; § 6 S030c, W026; § 7.8, § 7.9; cal-0192, cal-0193, cal-0194, cal-0195",
        },
        # Lent ride back (8–10 Apr)
        "2025-04-08": {
            "day_type": "Riding day",
            "places_in_order": (
                "`henley_street` to 05:30 (W032a, cal-0204) · `clopton_bridge` 05:40 (W032a) "
                "· `shipston_on_stour` 09:30–10:00 (W032a, cal-0205) · `chipping_norton` 12:00–12:30 (W032a) "
                "· `woodstock` from 17:30 (W032a, cal-0206)"
            ),
            "sources": "where-he-is.md; § 6 W032a; § 7.8, § 7.9; cal-0204, cal-0205, cal-0206",
        },
        "2025-04-09": {
            "day_type": "Riding day",
            "places_in_order": (
                "`woodstock` to 07:30 (cal-0207) · `oxford` 11:00 (W032b, passing without stopping) "
                "· `beaconsfield` 16:30 (§ 4.5) · `high_wycombe` from 18:00 (W032b, cal-0209)"
            ),
            "sources": "where-he-is.md; § 6 W032b; § 4.5, § 7.8; cal-0207, cal-0209 (W032b overrides cal-0208)",
        },
        "2025-04-10": {
            "day_type": "Riding day",
            "places_in_order": (
                "`high_wycombe` to 05:30 (W032c, cal-0210) · `beaconsfield` 07:00 (§ 4.5) "
                "· `uxbridge` 11:00–12:00 (cal-0211) · `bull_inn` 15:00–15:30 (W032c, cal-0212) · `ansell_house` from 15:35 (W032c)"
            ),
            "sources": "where-he-is.md; § 6 W032c; § 4.5, § 7.8; cal-0210, cal-0211, cal-0212",
        },
        # May 20: G039 at ansell_house in the morning (overrides cal-0303 Rehearsal), then over london_bridge to the_rose (W043, cal-0305)
        "2025-05-20": {
            "day_type": "Rose day",
            "places_in_order": (
                "`ansell_house` to 13:15 (G039) · `london_bridge` 13:35 (W043) · `the_rose` 14:00–16:45 (W043, cal-0305) "
                "· `london_bridge` 17:00 · `ansell_house` from 17:20"
            ),
            "sources": "§ 6 G039, W043; § 7.8 Special days, § 7.9; cal-0305 (G039 overrides cal-0303)",
        },
        # May 24: W131 at the_jackdaw 17:30 after Reckoning
        "2025-05-24": {
            "day_type": "Playing day",
            "places_in_order": (
                "`ansell_house` to 13:40 · `the_theatre` 14:00–17:25 (cal-0314, cal-0247) "
                "· `the_jackdaw` 17:30–19:00 (W131) · `ansell_house` from 19:20"
            ),
            "sources": "§ 6 W131; cal-0314, cal-0247",
        },
        # Jun 5: W134 at the_theatre 12:50–16:30, then carrier at the_bell_carter_lane after the play (overrides cal-0343 11:30–13:00)
        "2025-06-05": {
            "day_type": "Playing day",
            "places_in_order": (
                "`ansell_house` to 08:40 · `the_theatre` 09:00–11:00 (cal-0342) · `ansell_house` 11:20–12:30 "
                "· `the_theatre` 12:50–16:30 (W134, cal-0344) · `the_bell_carter_lane` 17:15–17:45 (§ 7.9 Carrier day) "
                "· `ansell_house` from 18:05"
            ),
            "sources": "§ 6 W134; § 7.9 Carrier day; cal-0342, cal-0344 (W134 overrides cal-0343)",
        },
        # Jun 10: S094 writing the deposing 03:50–11:00 at ansell_house ("Not cast... He does not walk once", overrides cal-0355 Rehearsal)
        "2025-06-10": {
            "day_type": "Writing day at the lodging",
            "places_in_order": "`ansell_house` all day (S094, writing the deposing; not cast in Shrew)",
            "sources": "§ 6 S094 (overrides cal-0355)",
        },
        # Jun 17: W137 call at 08:10 and G045 at ansell_house 09:00 (overrides cal-0371 Rehearsal)
        "2025-06-17": {
            "day_type": "Playing day",
            "places_in_order": (
                "`ansell_house` to 13:40 (W137, G045) · `the_theatre` 14:00–16:30 (cal-0372) · `ansell_house` from 16:50"
            ),
            "sources": "§ 6 W137, G045; cal-0372 (G045 overrides cal-0371)",
        },
        # Jun 26: where-he-is.md 600 m fear radius + S066 ("William does not walk that far this week; he sends the canvas and a line by Heminges's man", overrides cal-0398 at the_bell_carter_lane)
        "2025-06-26": {
            "day_type": "Playing day",
            "places_in_order": (
                "`ansell_house` to 08:40 · `the_theatre` 09:00–11:00 (cal-0397) · `ansell_house` 11:20–13:40 "
                "· `the_theatre` 14:00–17:30 (cal-0399, S066) · `ansell_house` from 17:50"
            ),
            "sources": "where-he-is.md; § 6 S066; § 7.9 Carrier day; cal-0397, cal-0399 (where-he-is.md & S066 override cal-0398)",
        },
        # Jul 8: G049 at ansell_house 08:00–11:00 (overrides cal-0419 Rehearsal)
        "2025-07-08": {
            "day_type": "Playing day",
            "places_in_order": (
                "`ansell_house` to 13:40 (G049) · `the_theatre` 14:00–16:30 (cal-0420) · `ansell_house` from 16:50"
            ),
            "sources": "§ 6 G049; cal-0420 (G049 overrides cal-0419)",
        },
        # Jul 12: cal-0247 Reckoning at the_theatre, G051 supper at split_hazel 17:30, S071 walk to old_swan_stairs 19:00–21:40
        "2025-07-12": {
            "day_type": "Rehearsal-heavy day",
            "places_in_order": (
                "`ansell_house` to 16:25 · `the_theatre` 16:45–17:20 (cal-0247) "
                "· `split_hazel` 17:35–18:45 (G051) · `old_swan_stairs` 19:00–21:40 (S071) · `ansell_house` from 21:55"
            ),
            "sources": "§ 6 G051, S071; cal-0247",
        },
        # Jul 17: W058 at the_theatre 12:20, play cal-0435 14:00–16:30, W304 carrier at the_bell_carter_lane 17:40 (overrides cal-0434 11:30–13:00)
        "2025-07-17": {
            "day_type": "Playing day",
            "places_in_order": (
                "`ansell_house` to 08:40 · `the_theatre` 09:00–11:00 (cal-0433) · `ansell_house` 11:20–12:00 "
                "· `the_theatre` 12:20–16:30 (W058, cal-0435) · `the_bell_carter_lane` 17:40–18:20 (W304) "
                "· `ansell_house` from 18:40"
            ),
            "sources": "§ 6 W058, W304; cal-0433, cal-0435 (W058 & W304 override cal-0434)",
        },
        # Jul 19: Play + Reckoning at the_theatre, then old_swan_stairs by wherry to paris_garden_swan (W059, cal-0438)
        "2025-07-19": {
            "day_type": "Boat day",
            "places_in_order": (
                "`ansell_house` to 13:40 · `the_theatre` 14:00–17:15 (cal-0437, cal-0247) · `old_swan_stairs` 17:35–18:30 (cal-0438) "
                "· by wherry to `paris_garden_swan` 18:40–19:20 (W059) · by wherry to `old_swan_stairs` 19:30 · `ansell_house` from 19:45"
            ),
            "sources": "where-he-is.md; § 6 W059; cal-0437, cal-0247, cal-0438",
        },
        # Summer walk out (28–31 Jul)
        "2025-07-28": {
            "day_type": "Foot road day",
            "places_in_order": (
                "`ansell_house` to 04:10 (W061, cal-0452) · `uxbridge` 11:00–12:00 (W061, cal-0453) "
                "· `chalfont_st_giles` from 18:40 (W061, cal-0454)"
            ),
            "sources": "where-he-is.md; § 6 W061; § 7.8, § 7.9; cal-0452, cal-0453, cal-0454",
        },
        "2025-07-29": {
            "day_type": "Foot road day",
            "places_in_order": "`chalfont_st_giles` to 03:50 (W062) · `grendon_underwood` from 19:40 (W062, cal-0455)",
            "sources": "where-he-is.md; § 6 W062; § 7.8, § 7.9; cal-0455",
        },
        "2025-07-30": {
            "day_type": "Foot road day",
            "places_in_order": "`grendon_underwood` to 04:20 (W063) · `banbury` from 17:30 (W063, cal-0456)",
            "sources": "where-he-is.md; § 6 W063; § 7.8, § 7.9; cal-0456",
        },
        "2025-07-31": {
            "day_type": "Foot road day",
            "places_in_order": (
                "`banbury` to 04:30 (W064, cal-0457) · `clopton_bridge` 17:00–17:20 (W064, cal-0458) "
                "· `henley_street` from 17:30 (W064, cal-0459)"
            ),
            "sources": "where-he-is.md; § 6 W064; § 7.8, § 7.9; cal-0457, cal-0458, cal-0459",
        },
        # Aug 13–15: laid up flat on his back at henley_street (W332, G061, W070)
        "2025-08-13": {
            "day_type": "Stratford ordinary day",
            "places_in_order": "`henley_street` all day (W332, G061, laid up flat with strained back)",
            "sources": "where-he-is.md; § 6 W332, G061; § 7.8 Special days",
        },
        "2025-08-14": {
            "day_type": "Stratford ordinary day",
            "places_in_order": "`henley_street` all day (W070, laid up flat on market day)",
            "sources": "where-he-is.md; § 6 W070; § 7.8 Special days",
        },
        "2025-08-15": {
            "day_type": "Stratford ordinary day",
            "places_in_order": "`henley_street` all day (§ 7.8, laid up with strained back)",
            "sources": "where-he-is.md; § 7.8 Special days (13–15 Aug flat)",
        },
        # Summer walk back with Hobbins's packhorses (18–21 Aug)
        "2025-08-18": {
            "day_type": "Foot road day",
            "places_in_order": (
                "`henley_street` to 05:40 (W073a) · `clopton_bridge` 06:00 (W073a) "
                "· `shipston_on_stour` 10:00–10:30 (W073a, § 4.5) · `chipping_norton` from 18:00 (W073a, cal-0473)"
            ),
            "sources": "where-he-is.md; § 6 W073a; § 4.5, § 7.8; cal-0473",
        },
        "2025-08-19": {
            "day_type": "Foot road day",
            "places_in_order": (
                "`chipping_norton` to 05:30 (W073b) · `woodstock` 12:00 (W073b, § 4.5) "
                "· `oxford` from 18:20 (W073b, cal-0474)"
            ),
            "sources": "where-he-is.md; § 6 W073b; § 4.5, § 7.8; cal-0474",
        },
        "2025-08-20": {
            "day_type": "Foot road day",
            "places_in_order": (
                "`oxford` to 04:45 (W073c) · `high_wycombe` 17:00 (W073c, § 4.5) "
                "· `beaconsfield` from 19:30 (W073c, cal-0475)"
            ),
            "sources": "where-he-is.md; § 6 W073c; § 4.5, § 7.8; cal-0475",
        },
        "2025-08-21": {
            "day_type": "Foot road day",
            "places_in_order": (
                "`beaconsfield` to 04:30 (W073d) · `uxbridge` 10:00 (W073d, cal-0476) "
                "· `the_bell_carter_lane` from 18:10 (W073d, W074, cal-0477)"
            ),
            "sources": "where-he-is.md; § 6 W073d, W074; § 4.5, § 7.8; cal-0476, cal-0477",
        },
        "2025-08-22": {
            "day_type": "Household and rest",
            "places_in_order": (
                "`the_bell_carter_lane` to 07:45 (W075) · `ansell_house` from 08:00 (W075, cal-0478, M030 at 19:30)"
            ),
            "sources": "where-he-is.md; § 6 W075, M030; cal-0478",
        },
        # Aug 28: G068 seated at ansell_house 08:00–11:30 ("because the back will allow nothing else after yesterday", overrides cal-0489 Rehearsal)
        "2025-08-28": {
            "day_type": "Playing day",
            "places_in_order": (
                "`ansell_house` to 13:40 (G068) · `the_theatre` 14:00–16:30 (cal-0490) · `ansell_house` from 16:50"
            ),
            "sources": "§ 6 G068; cal-0490 (G068 overrides cal-0489)",
        },
        # Sep 18: W082 at pauls_churchyard 10:00 (overrides cal-0535 Rehearsal and merges with cal-0536 12:15–12:45)
        "2025-09-18": {
            "day_type": "Writing day at the lodging",
            "places_in_order": (
                "`ansell_house` to 09:40 · `pauls_churchyard` 10:00–12:45 (W082, cal-0536) · `ansell_house` from 13:05"
            ),
            "sources": "§ 6 W082; cal-0536 (W082 overrides cal-0535)",
        },
        # Sep 23: S091 writing morning at ansell_house 10:40 (overrides cal-0546 Rehearsal)
        "2025-09-23": {
            "day_type": "Playing day",
            "places_in_order": (
                "`ansell_house` to 13:40 (S091) · `the_theatre` 14:00–16:30 (cal-0547) · `ansell_house` from 16:50"
            ),
            "sources": "§ 6 S091; cal-0547 (S091 overrides cal-0546)",
        },
        # Oct 1: G075 at fields_printing_house 09:00–10:00 (overrides cal-0568 Rehearsal), W400 at ansell_house 19:30
        "2025-10-01": {
            "day_type": "Playing day",
            "places_in_order": (
                "`ansell_house` to 08:35 · `fields_printing_house` 09:00–10:00 (G075) · `ansell_house` 10:25–13:40 "
                "· `the_theatre` 14:00–16:30 (cal-0569) · `ansell_house` from 16:50, with Gilbert at 19:30 (W400)"
            ),
            "sources": "§ 6 G075, W400; cal-0569 (G075 overrides cal-0568)",
        },
        # Oct 2: S095a at bishopsgate 08:40, cal-0570 Rehearsal, W085 Richard II first played 13:00–16:50 at the_theatre (W400 states Gilbert carries the 60s to the Bell, overriding cal-0571)
        "2025-10-02": {
            "day_type": "Playing day",
            "places_in_order": (
                "`ansell_house` to 08:35 · `bishopsgate` 08:40–08:45 (S095a) · `the_theatre` 09:00–11:00 (cal-0570) "
                "· `ansell_house` 11:20–12:40 · `the_theatre` 13:00–16:50 (W085, cal-0572) · `ansell_house` from 17:10"
            ),
            "sources": "§ 6 S095a, W085, W400; cal-0570, cal-0572 (W400 & W085 override cal-0571)",
        },
        # Oct 13–16: tooth abscess and extraction recovery (G077, W403, M038, W089, W404)
        "2025-10-13": {
            "day_type": "Household and rest",
            "places_in_order": "`ansell_house` all day (G077, W403; Cowley takes his part)",
            "sources": "§ 6 G077, W403; § 7.8",
        },
        "2025-10-14": {
            "day_type": "Household and rest",
            "places_in_order": (
                "`ansell_house` to 09:55 (M038) · `bishopsgate` 10:00–10:30 (W089) · `ansell_house` from 10:35 (W089)"
            ),
            "sources": "§ 6 M038, W089; § 7.8 Special days",
        },
        "2025-10-15": {
            "day_type": "Household and rest",
            "places_in_order": "`ansell_house` all day (W404, recovering after tooth drawing)",
            "sources": "§ 6 W404; § 7.8",
        },
        "2025-10-16": {
            "day_type": "Household and rest",
            "places_in_order": "`ansell_house` all day (W404, S099; Pope plays Gaunt for him)",
            "sources": "§ 6 W404, S099; § 5.2, § 7.8 (overrides cal-0604)",
        },
        # Oct 18: S099 walks up to Shoreditch for the reckoning only, back by 17:10, then Evening prayer cal-0612
        "2025-10-18": {
            "day_type": "Household and rest",
            "places_in_order": (
                "`ansell_house` to 15:40 · `the_theatre` 16:00–16:50 (S099, cal-0247) · `ansell_house` 17:10–18:10 (S099) "
                "· `st_helens_church` 18:15–19:00 (cal-0612) · `ansell_house` from 19:05"
            ),
            "sources": "§ 6 S099; cal-0247, cal-0612",
        },
        # Nov 1: S102a All Saints morning prayer + play + reckoning + Evening prayer
        "2025-11-01": {
            "day_type": "Playing day",
            "places_in_order": (
                "`ansell_house` to 08:55 · `st_helens_church` 09:00–11:00 (S102a) · `ansell_house` 11:05–13:40 "
                "· `the_theatre` 14:00–18:00 (cal-0648, cal-0247) · `st_helens_church` 18:15–19:00 (S102a, cal-0650) "
                "· `ansell_house` from 19:05"
            ),
            "sources": "§ 6 S102a; cal-0648, cal-0247, cal-0650",
        },
        # Nov 11: W093 writing at ansell_house 06:30–10:15, S105 Leadenhall 10:30–11:45 (overrides cal-0668 06:30–08:45 and cal-0669 Rehearsal)
        "2025-11-11": {
            "day_type": "Playing day",
            "places_in_order": (
                "`ansell_house` to 10:20 (W093) · `leadenhall` 10:30–11:45 (S105, cal-0668) · `ansell_house` 11:55–13:40 "
                "· `the_theatre` 14:00–16:30 (cal-0670) · `st_helens_church` 17:00–17:45 (cal-0671) · `ansell_house` from 17:50"
            ),
            "sources": "§ 6 W093, S105; cal-0668, cal-0670, cal-0671 (W093 & S105 override cal-0669)",
        },
        # Nov 17: S106 Accession Day at whitehall_tiltyard 09:30–17:30 (overrides cal-0686 Evening prayer), bonfire at bishopsgate 20:00
        "2025-11-17": {
            "day_type": "Household and rest",
            "places_in_order": (
                "`ansell_house` to 08:30 · `pauls_churchyard` 08:50 (S106) · `whitehall_tiltyard` 09:30–17:30 (S106, cal-0684) "
                "· `ansell_house` 18:25–19:55 · `bishopsgate` 20:00–20:30 (S106) · `ansell_house` from 20:35"
            ),
            "sources": "§ 6 S106; § 7.8 Special days; cal-0684 (S106 overrides cal-0686)",
        },
        # Nov 22: W413 call at 08:00 + Play + Reckoning + W097 at the_jackdaw 17:30–20:30
        "2025-11-22": {
            "day_type": "Playing day",
            "places_in_order": (
                "`ansell_house` to 13:40 (W413 at 08:00) · `the_theatre` 14:00–17:25 (cal-0699, cal-0247) "
                "· `the_jackdaw` 17:30–20:30 (W097, cal-0701) · `ansell_house` from 20:50"
            ),
            "sources": "§ 6 W413, W097; cal-0699, cal-0247, cal-0701",
        },
        # Dec 1: S111 at pauls_churchyard 10:45 (leaving rehearsal cal-0722 early), then afternoon play cal-0723 at the_theatre
        "2025-12-01": {
            "day_type": "Playing day",
            "places_in_order": (
                "`ansell_house` to 08:40 · `the_theatre` 09:00–10:20 (cal-0722) "
                "· `pauls_churchyard` 10:45–11:45 (S111) · `ansell_house` 12:00–13:40 "
                "· `the_theatre` 14:00–16:30 (cal-0723) · `ansell_house` from 16:50"
            ),
            "sources": "§ 6 S111; cal-0722, cal-0723",
        },
        # Dec 9: cal-0743 morning rehearsal + S112a/b afternoon play at the_theatre, then by water from old_swan_stairs to canon_row, walk home at midnight
        "2025-12-09": {
            "day_type": "Playing day",
            "places_in_order": (
                "`ansell_house` to 08:40 · `the_theatre` 09:00–11:00 (cal-0743) · `ansell_house` 11:20–13:40 "
                "· `the_theatre` 14:00–16:15 (S112a, cal-0744) · `ansell_house` 16:35–16:50 (S112a) "
                "· `old_swan_stairs` 17:05 (S112a) · by wherry to `canon_row` 17:30–23:00 (S112a, cal-0745) "
                "· on foot by the Strand: `somerset_house` 23:45 (S112b, § 7.7 shot 91) "
                "· on by Fleet Street, Ludgate and Cheapside past midnight (S112b; the editor, 2026-11-16: the world's times govern)"
            ),
            "sources": "§ 6 S112a, S112b; § 7.8 Special days, § 7.9 'Court night, 9 December'; cal-0743, cal-0744, cal-0745",
        },
        # Dec 21: S113 St Thomas + cal-0768 church + cal-0769 Fields dinner + cal-0770 dole
        "2025-12-21": {
            "day_type": "Household and rest",
            "places_in_order": (
                "`ansell_house` to 08:25 (S113) · `st_helens_church` 08:30–10:30 (S113, cal-0768) · `ansell_house` 10:35–12:05 "
                "· `fields_printing_house` 12:30–14:30 (S113, cal-0769) · `ansell_house` from 15:30 (S113, cal-0770)"
            ),
            "sources": "§ 6 S113; cal-0768, cal-0769, cal-0770",
        },
        # Dec 22: W106 rent paid at 11:30, M053 old_swan_stairs 12:15, W106/cal-0772 Errors at the_theatre 14:00–16:30
        "2025-12-22": {
            "day_type": "Playing day",
            "places_in_order": (
                "`ansell_house` to 12:00 (W106, cal-0771) · `old_swan_stairs` 12:15–13:00 (M053) "
                "· `the_theatre` 14:00–16:30 (W106, M053, cal-0772) · `ansell_house` from 16:50 (W106)"
            ),
            "sources": "§ 6 W106, M053; cal-0771, cal-0772",
        },
        # Dec 24: W107 upriver by tilt-boat from old_swan_stairs to the_feathers_richmond
        "2025-12-24": {
            "day_type": "Boat day",
            "places_in_order": (
                "`ansell_house` to 06:45 (W107) · `old_swan_stairs` 07:00–11:00 (W107, cal-0776) "
                "· by wherry to `the_feathers_richmond` from 15:30 (W107, cal-0777)"
            ),
            "sources": "where-he-is.md; § 6 W107; § 7.8, § 7.9; cal-0776, cal-0777",
        },
        # Dec 26: S115a St Stephen's night at richmond_palace
        "2025-12-26": {
            "day_type": "Court day",
            "places_in_order": (
                "`the_feathers_richmond` to 09:50 · `richmond_palace` 10:00–11:30 (S115a) "
                "· `the_feathers_richmond` 11:40–17:20 · `richmond_palace` 17:30–23:50 (S115a, cal-0782) "
                "· `the_feathers_richmond` from 23:55"
            ),
            "sources": "where-he-is.md; § 6 S115a; § 7.8 Special days; cal-0782 (cal-0779 cancelled)",
        },
        # Dec 27: S115b St John's night at richmond_palace (21:00–00:20, carries past midnight into 28 Dec)
        "2025-12-27": {
            "day_type": "Court day",
            "places_in_order": (
                "`the_feathers_richmond` to 20:50 "
                "· `richmond_palace` from 21:00 past midnight (S115b, cal-0785)"
            ),
            "sources": "where-he-is.md; § 6 S115b; § 7.8 Special days; cal-0785",
        },
        # Dec 28: S115c Innocents' night at richmond_palace
        "2025-12-28": {
            "day_type": "Court day",
            "places_in_order": (
                "`the_feathers_richmond` to 20:50 (cal-0786 at 09:00–11:00) "
                "· `richmond_palace` 21:00–23:45 (S115c, cal-0787) · `the_feathers_richmond` from 23:50"
            ),
            "sources": "where-he-is.md; § 6 S115c; § 7.8 Special days; cal-0786, cal-0787",
        },
        # Dec 29: W108 downriver by tilt-boat to old_swan_stairs + M056 spiced ale at bull_inn (overrides cal-0790 13:00–14:00 ansell_house)
        "2025-12-29": {
            "day_type": "Boat day",
            "places_in_order": (
                "`the_feathers_richmond` to 09:00 (W108, cal-0789) · by wherry to `old_swan_stairs` 14:00 (W108) "
                "· `bull_inn` 14:30–16:00 (M056, cal-0792) · `ansell_house` from 16:05 (M056)"
            ),
            "sources": "where-he-is.md; § 6 W108, M056; § 7.8, § 7.9; cal-0789, cal-0792 (W108 & M056 override cal-0790)",
        },
    }


def _extract_cross_midnight_carry(entry: dict[str, Any]) -> dict[str, Any] | None:
    """If `entry` has a quoted `HH:MM–HH:MM` time range that crosses 24:00, return its overnight carry spec."""
    t_str = entry["time"].strip()
    for part in re.split(r"\s*(?:,|and)\s*", t_str):
        part_s = part.strip()
        if "–" not in part_s:
            continue
        a, b = part_s.split("–", 1)
        s_min = _hm_to_min(a)
        e_min = _hm_to_min(b)
        if e_min < s_min:
            bed_match = re.search(r"\bbed\s+(\d{2}:\d{2})\b", entry.get("body", ""))
            if bed_match:
                bed_hm = bed_match.group(1)
            else:
                next_d = date.fromisoformat(entry["date"]) + timedelta(days=1)
                bed_hm = str(season_body_params(next_d)["bed_time"])
            is_walk_home = "walk" in entry.get("title", "").lower() or "on foot" in entry.get("body", "").lower()
            return {
                "id": entry["id"],
                "date": entry["date"],
                "place_slug": entry["place_slug"],
                "start_hm": a.strip(),
                "end_hm": b.strip(),
                "bed_hm": bed_hm,
                "is_walk_home": is_walk_home,
            }
    return None


def _apply_overnight_carry_to_next_day(
    places_in_order: str,
    home: str,
    carry: dict[str, Any],
) -> str:
    """Carry a cross-midnight entry from day D into the start of day D+1."""
    eid = carry["id"]
    end_hm = carry["end_hm"]
    bed_hm = carry["bed_hm"]
    entry_place = carry["place_slug"]

    parts = [p.strip() for p in places_in_order.split("·") if p.strip()]
    if not parts:
        return places_in_order

    first_part = parts[0]
    m_to = re.match(rf"^`{re.escape(home)}`\s+to\s+(\d{{2}}:\d{{2}})(.*)$", first_part)
    m_all = re.match(rf"^`{re.escape(home)}`\s+all\s+day(.*)$", first_part)

    if entry_place != home:
        walk_min = WALK_MIN_FROM_HOME.get(entry_place, 15)
        arrive_hm = _min_to_hm(_hm_to_min(end_hm) + walk_min)
        if m_to:
            dep_hm, suffix = m_to.group(1), m_to.group(2)
            parts[0] = (
                f"`{entry_place}` to {end_hm} ({eid}) "
                f"· `{home}` from {arrive_hm} ({eid}, bed {bed_hm}) to {dep_hm}{suffix}"
            )
            return " · ".join(parts)
        if m_all:
            suffix = m_all.group(1)
            parts[0] = (
                f"`{entry_place}` to {end_hm} ({eid}) "
                f"· `{home}` from {arrive_hm} ({eid}, bed {bed_hm}){suffix}"
            )
            return " · ".join(parts)
        return places_in_order

    if carry["is_walk_home"]:
        if m_to:
            dep_hm, suffix = m_to.group(1), m_to.group(2)
            parts[0] = f"`{home}` from {end_hm} ({eid}, bed {bed_hm}) to {dep_hm}{suffix}"
            return " · ".join(parts)
        if m_all:
            suffix = m_all.group(1)
            parts[0] = f"`{home}` from {end_hm} ({eid}, bed {bed_hm}){suffix}"
            return " · ".join(parts)
        return places_in_order

    # Stationary at home across midnight (e.g., W042, W067, W092)
    if m_to:
        dep_hm, suffix = m_to.group(1), m_to.group(2).strip()
        if suffix:
            parts[0] = f"`{home}` to {dep_hm} ({eid} to {end_hm}, bed {bed_hm}; {suffix.strip('()')})"
        else:
            parts[0] = f"`{home}` to {dep_hm} ({eid} to {end_hm}, bed {bed_hm})"
        return " · ".join(parts)
    if m_all:
        suffix = m_all.group(1).strip()
        if suffix:
            parts[0] = f"`{home}` all day ({eid} to {end_hm}, bed {bed_hm}; {suffix.strip('()')})"
        else:
            parts[0] = f"`{home}` all day ({eid} to {end_hm}, bed {bed_hm})"
        return " · ".join(parts)
    return places_in_order


def _parse_entry_interval(entry: dict[str, Any]) -> tuple[int, int]:
    """Parse a § 6 entry's `time` field into `(start_min, end_min)`."""
    t_str = entry["time"].strip()
    place = entry["place_slug"]
    # Take the first span if `and` or `,` is present (curated overrides handle multi-place/multi-time days)
    first_part = re.split(r"\s*(?:,|and)\s*", t_str)[0].strip()
    if "–" in first_part:
        a, b = first_part.split("–", 1)
        s_min = _hm_to_min(a)
        e_min = _hm_to_min(b)
        if e_min <= s_min:
            e_min = 24 * 60
        return s_min, e_min
    s_min = _hm_to_min(first_part)
    dwell = DEFAULT_DWELL_MIN.get(place, 60)
    e_min = min(23 * 60 + 40, s_min + dwell)
    return s_min, e_min


def _build_day_itinerary_general(
    d: date,
    wakes: str,
    sleeps: str,
    s6_entries: list[dict[str, Any]],
    cal_events: list[dict[str, Any]],
) -> tuple[str, str, str]:
    """Derive `(day_type, places_in_order, sources)` for a standard London/Stratford/Richmond day."""
    d_str = d.isoformat()
    home = sleeps  # On all non-curated days, wakes == sleeps

    # Collect intervals at away-from-home places and notes at home
    raw_visits: list[tuple[int, int, str, list[str]]] = []
    home_notes: list[tuple[int, str, str]] = []  # (start_min, id, time_str)
    all_source_ids: list[str] = []

    has_i_play = False
    has_rehearsal = False
    has_rose = False

    for e in s6_entries:
        all_source_ids.append(f"§ 6 {e['id']}")
        p = e["place_slug"]
        s_min, e_min = _parse_entry_interval(e)
        if p == "the_rose":
            has_rose = True
        if p == home:
            home_notes.append((s_min, e["id"], e["time"]))
        else:
            raw_visits.append((s_min, e_min, p, [e["id"]]))

    for c in cal_events:
        cid = c["id"]
        layer = c.get("layer")
        p = c["place_slug"]
        s_min = _hm_to_min(c["start"])
        e_min = _hm_to_min(c["end"])
        if e_min <= s_min:
            e_min = 23 * 60 + 45

        if layer == "company_play" and "(I play)" in (c.get("title") or ""):
            has_i_play = True
        elif layer == "rehearsal":
            has_rehearsal = True
        elif layer == "rival_bill" and p == "the_rose":
            has_rose = True

        # Carrier Thursday rule (§ 7.9 "Carrier day: Home -> the_bell_carter_lane after the play"):
        # If there is an afternoon play on a carrier Thursday and `cal` has Carrier at 11:30–13:00,
        # check if a § 6 entry already placed `the_bell_carter_lane`; if not, and there is a play,
        # move the visit to after the play (17:15–17:55) per § 7.9 ("Carrier day: Home -> the_bell_carter_lane after the play").
        if layer == "carrier" and p == "the_bell_carter_lane":
            if any(rv[2] == "the_bell_carter_lane" for rv in raw_visits):
                all_source_ids.append(cid)
                continue
            if has_i_play or any(ev.get("layer") == "company_play" and "(I play)" in (ev.get("title") or "") for ev in cal_events):
                s_min, e_min = 17 * 60 + 15, 17 * 60 + 55

        all_source_ids.append(cid)
        if p == home:
            home_notes.append((s_min, cid, f"{c['start']}–{c['end']}"))
        else:
            raw_visits.append((s_min, e_min, p, [cid]))

    # Sort and merge overlapping or adjacent visits at the same place, and resolve overlaps between different places
    # (Rank 2 § 6 entries were added before Rank 3 calendar events).
    raw_visits.sort(key=lambda x: (x[0], x[1]))
    merged_visits: list[list[Any]] = []
    for s_min, e_min, p, tags in raw_visits:
        if not merged_visits:
            merged_visits.append([s_min, e_min, p, list(tags)])
            continue
        prev = merged_visits[-1]
        prev_s, prev_e, prev_p, prev_tags = prev
        if p == prev_p and s_min <= prev_e + 20:
            prev[0] = min(prev_s, s_min)
            prev[1] = max(prev_e, e_min)
            for t in tags:
                if t not in prev_tags:
                    prev_tags.append(t)
        elif s_min < prev_e + 10:
            # Different places overlapping or within 10 min: adjust boundary so there is a walk gap
            mid = max(prev_s + 20, min(s_min, prev_e - 10))
            prev[1] = mid
            new_s = mid + 10
            if e_min <= new_s:
                e_min = new_s + 30
            merged_visits.append([new_s, e_min, p, list(tags)])
        else:
            merged_visits.append([s_min, e_min, p, list(tags)])

    # Classify day_type (§ 7.8)
    if home == "henley_street":
        day_type = "Stratford ordinary day"
    elif home == "the_feathers_richmond":
        day_type = "Household and rest"
    elif has_rose:
        day_type = "Rose day"
    elif has_i_play:
        day_type = "Playing day"
    elif has_rehearsal or any(
        v[2] in ("cross_keys_inn", "the_theatre")
        and any(
            k in " ".join(e["title"].lower() + " " + e["body"].lower() for e in s6_entries)
            for k in ("rehearsal", "parts", "reading", "con", "baskets", "stage")
        )
        for v in merged_visits
    ):
        day_type = "Rehearsal-heavy day"
    elif d.weekday() == 6:  # Sunday in London
        day_type = "Household and rest"
    elif d_str == "2025-02-21":  # Southwell's execution day (S019, resting 66 with no exertion)
        day_type = "Household and rest"
    else:
        day_type = "Writing day at the lodging"

    # Format `places_in_order`
    if not merged_visits:
        if home_notes:
            note_tags = ", ".join(f"{hid} at {ht}" for _, hid, ht in home_notes)
            places_str = f"`{home}` all day ({note_tags})"
        else:
            places_str = f"`{home}` all day"
    else:
        clauses: list[str] = []
        first_s, first_e, first_p, _ = merged_visits[0]
        walk_out = WALK_MIN_FROM_HOME.get(first_p, 15)
        depart_home = max(0, first_s - walk_out)
        clauses.append(f"`{home}` to {_min_to_hm(depart_home)}")

        for idx, (s_min, e_min, p, tags) in enumerate(merged_visits):
            if idx > 0:
                prev_s, prev_e, prev_p, _ = merged_visits[idx - 1]
                gap = s_min - prev_e
                walk_home = WALK_MIN_FROM_HOME.get(prev_p, 15) + WALK_MIN_FROM_HOME.get(p, 15)
                # If gap is long enough (>= 60 min and >= walk_home + 20 min), he returns to home base in between
                if gap >= max(60, walk_home + 20):
                    h_arr = prev_e + WALK_MIN_FROM_HOME.get(prev_p, 15)
                    h_dep = s_min - WALK_MIN_FROM_HOME.get(p, 15)
                    if h_dep > h_arr:
                        clauses.append(f"`{home}` {_min_to_hm(h_arr)}–{_min_to_hm(h_dep)}")

            tag_str = ", ".join(tags)
            if e_min >= 24 * 60:
                clauses.append(f"`{p}` from {_min_to_hm(s_min)} past midnight ({tag_str})")
            else:
                clauses.append(f"`{p}` {_min_to_hm(s_min)}–{_min_to_hm(e_min)} ({tag_str})")

        last_s, last_e, last_p, _ = merged_visits[-1]
        if last_e < 24 * 60:
            walk_back = WALK_MIN_FROM_HOME.get(last_p, 15)
            arrive_home = min(23 * 60 + 50, last_e + walk_back)
            late_home_notes = [ f"{hid} at {ht}" for hm_min, hid, ht in home_notes if hm_min >= arrive_home - 30 ]
            if late_home_notes:
                clauses.append(f"`{home}` from {_min_to_hm(arrive_home)} ({', '.join(late_home_notes)})")
            else:
                clauses.append(f"`{home}` from {_min_to_hm(arrive_home)}")

        places_str = " · ".join(clauses)

    # Deduplicate sources while preserving order
    seen_src: set[str] = set()
    dedup_src: list[str] = []
    if home != "ansell_house" or ("2025-06-12" <= d_str <= "2025-07-18"):
        dedup_src.append("where-he-is.md")
        seen_src.add("where-he-is.md")
    for s in all_source_ids:
        if s not in seen_src:
            dedup_src.append(s)
            seen_src.add(s)
    sources_str = "; ".join(dedup_src) if dedup_src else "no entry (§ 7.8 / § 7.9 default)"

    return day_type, places_str, sources_str


def build_rules_spec() -> dict[str, Any]:
    """Return the structured specification of written presence, precedence, day-type, and default rules."""
    return {
        "precedence_ranks": [
            {
                "rank": 1,
                "source": "content/threads/merged/where-he-is.md (and world/world.md § 7.9 365-night table)",
                "rule": (
                    "Defines where William sleeps each night and his geographic bounds across the 365 nights of 2025: "
                    "`ansell_house` in St Helen's Bishopsgate for 317 nights, `henley_street` in Stratford for 28 nights "
                    "(Mar 28–Apr 7 and Jul 31–Aug 17), `the_feathers_richmond` for 5 nights (Dec 24–28), and 15 road/carrier "
                    "nights across 4 journeys (Mar 26–27, Apr 8–9, Jul 28–30, Aug 18–21). "
                    "During the riot-season curfew (Jun 12–Jul 18), `where-he-is.md` forbids crossing the river (`lat < 51.5085`) "
                    "and from Jun 13–Jul 5 restricts him to the 600 m triangle (`ansell_house` – `the_theatre` – `st_helens_church`)."
                ),
            },
            {
                "rank": 2,
                "source": "world/world.md § 6 (376 dated narrative entries across 307 distinct days)",
                "rule": (
                    "Each dated entry header (`**ID · YYYY-MM-DD (Day) · HH:MM · place_slug · Title**`) "
                    "and its prose body give William's concrete location, activity, step count (where stated), "
                    "and companions. When a § 6 entry places him at home (`ansell_house` or `henley_street`), at a "
                    "tavern, at Paul's, at Field's shop, or on the road during a time window that overlaps a "
                    "calendar event elsewhere, Rank 2 overrides Rank 3."
                ),
            },
            {
                "rank": 3,
                "source": "calendar/merged/calendar.json (795 raw events -> 874 expanded instances across 349 days)",
                "rule": (
                    "Timed confirmed calendar events with a `place_slug` that pass the written presence rule "
                    "(derived from `layer`, `why`, and `attendees`) place William at `place_slug` for `[start, end]` "
                    "unless overridden by Rank 1 (`where-he-is.md`) or Rank 2 (§ 6)."
                ),
            },
            {
                "rank": 4,
                "source": "world/world.md § 7.8 & § 7.9 written defaults",
                "rule": (
                    "Where Rank 1–3 record no movement outside the overnight base (`ansell_house` in London, "
                    "`henley_street` in Stratford, or `the_feathers_richmond` in Richmond), William remains at his "
                    "overnight base (`all day`), and the backdrop generator emits stationary home fixes (`§ 7.9`: "
                    "'When he is at `ansell_house` writing, the dot sits in Bishopsgate for six hours'). If an "
                    "unplaced away stretch has no canonical coordinates, no location fixes are emitted "
                    "('Missing data beats teleporting', § 7.9)."
                ),
            },
        ],
        "calendar_presence_rules": {
            "total_raw_events": 795,
            "total_expanded_instances": 874,
            "presence_recording_instances": 496,
            "excluded_instances": 378,
            "rules_by_category": [
                {
                    "condition": "status != 'confirmed'",
                    "decision": "exclude (3 instances: cal-0045 on 2025-01-19, cal-0407 on 2025-06-30, cal-0779 on 2025-12-26)",
                    "why": "Cancelled events (`status: 'cancelled'`) carry `why` explaining that the planned gathering or supper did not take place.",
                },
                {
                    "condition": "all_day == true or place_slug is null",
                    "decision": "exclude from direct place stops (72 all-day banners + 7 null-place timed notices)",
                    "why": (
                        "All-day events mark seasonal spans, law terms, fairs, or journeys whose day-by-day stops "
                        "are carried by timed events and `where-he-is.md`. Four timed `No play` notices have no "
                        "`place_slug`; the other three null-place timed events (`cal-0468` Aug 10 Sadlers' dinner, "
                        "`cal-0591` Oct 10 Yaxley, `cal-0599` Oct 14 Yaxley) are placed by their corresponding "
                        "§ 6 entries (`W068`, `W402`, `W089`)."
                    ),
                },
                {
                    "condition": "layer == 'rival_bill'",
                    "decision": "include ONLY when 'william_shakespeare' in attendees (4 included: cal-0115, cal-0305, cal-0493, cal-0718; 205 excluded)",
                    "why": (
                        "world.md § 7.1 ('Henslowe's Rose bill, copied from the posts down Bishopsgate so William "
                        "can see what the Admiral's Men are playing against them') and calendar.json `why`: "
                        "'The bill, not an attendance. He reads it and does not go.' Only the 4 rival bills where "
                        "`attendees` includes `william_shakespeare` record him crossing to the Rose or Newington Butts."
                    ),
                },
                {
                    "condition": "layer == 'money'",
                    "decision": "include ONLY when organizer == 'william_shakespeare' or 'william_shakespeare' in attendees (5 included; 12 instances of cal-0578 excluded)",
                    "why": (
                        "`cal-0578` (`Firing and washing, vj d.`, 12 weekly Mondays at `ansell_house`) has "
                        "`organizer: 'agnes_ansell'`, `attendees: null`, and `why: 'Household account line on the "
                        "calendar so the winter rise in the quarter bill is visible Week by Week.'` During "
                        "`cal-0578` on `2025-10-06` and `2025-11-10`, William is at `the_theatre` for 08:30–11:30 "
                        "rehearsals (`cal-0579`, `cal-0665`). The 5 personal reckoning/payment events (`cal-0001`, "
                        "`cal-0177`, `cal-0199`, `cal-0770`, `cal-0795`) have `organizer: 'william_shakespeare'`."
                    ),
                },
                {
                    "condition": "layer == 'company_play'",
                    "decision": "include ONLY when '(I play)' in title (160 included: 159 public afternoons + cal-0745 Canon Row; 79 stock bills without '(I play)' excluded unless § 6 places him there)",
                    "why": (
                        "world.md § 7.1: 'Every afternoon the company plays (Cross Keys to 3 Mar, Theatre from "
                        "21 Apr, plus inoculations at the Guildhall, two nights at Canon Row, five Court days at "
                        "Greenwich, Richmond and Whitehall), with `(I play)` on about four days in six and his role "
                        "in the description.' Stock plays without `(I play)` are bills where he does not act and "
                        "writes at `ansell_house` unless a § 6 entry places him at the playhouse (e.g., `2025-05-03` "
                        "`W038` where he watches from the yard, or Saturdays when he walks up for the 17:00 reckoning)."
                    ),
                },
                {
                    "condition": "layer in {'rehearsal', 'company_business', 'travel', 'sunday', 'feast', 'social', 'carrier', 'family_day', 'print', 'court', 'other', 'quarter_day', 'law_term'}",
                    "decision": "include all confirmed timed events with a `place_slug` (327 instances), subject to Rank 1 & Rank 2 overrides",
                    "why": "These layers record William's own rehearsals, company reckonings, church attendance, carrier visits, printing-house stops, court calls, and road stages.",
                },
            ],
        },
        "day_type_rules": {
            "source": "world/world.md § 7.8",
            "types": [
                {
                    "day_type": "Playing day",
                    "step_band": [9000, 15000],
                    "rule": "Days where William plays (`(I play)` in `company_play` or § 6 performance).",
                },
                {
                    "day_type": "Rehearsal-heavy day",
                    "step_band": [7000, 12000],
                    "rule": "Non-playing days with a rehearsal (`layer == 'rehearsal'`) or playhouse reading/part-copying session.",
                },
                {
                    "day_type": "Writing day at the lodging",
                    "step_band": [2500, 6000],
                    "rule": "London days at `ansell_house` without performance or rehearsal (4,000–7,000 during Lent 5 Mar – 19 Apr; includes short errands to Paul's, Field's, or the Bell).",
                },
                {
                    "day_type": "Rose day",
                    "step_band": [8000, 13000],
                    "rule": "Days where William crosses the river to stand in the yard at the Rose (`the_rose`).",
                },
                {
                    "day_type": "Boat day",
                    "step_band": [3000, 7000],
                    "rule": "Days dominated by a Thames wherry or tilt-boat crossing (`2025-03-15`, `2025-05-03`, `2025-07-19`, `2025-12-24`, `2025-12-29`).",
                },
                {
                    "day_type": "Court day",
                    "step_band": [7500, 8500],
                    "rule": "Days with Court performances at `richmond_palace` (`2025-12-26..28`).",
                },
                {
                    "day_type": "Household and rest",
                    "step_band": [2000, 5500],
                    "rule": "Sundays in London, Richmond rest day (`2025-12-25`), Southwell's execution day (`2025-02-21`), and London sick/recovery days (`2025-01-18..19`, `2025-10-15..16`, `2025-10-18`, with explicit § 6 step overrides).",
                },
                {
                    "day_type": "Stratford ordinary day",
                    "step_band": [5000, 10500],
                    "rule": "Stratford residence days (`henley_street` overnight base, `2025-03-29..04-07` and `2025-08-01..17`, with explicit § 6 step overrides on field/market and illness days).",
                },
                {
                    "day_type": "Riding day",
                    "step_band": [4500, 7000],
                    "rule": "6 horse-journey days in March/April (`2025-03-26..28`, `2025-04-08..10`; boot-in-stirrup jolt plus stable/inn walking).",
                },
                {
                    "day_type": "Foot road day",
                    "step_band": [44000, 68000],
                    "rule": "8 foot-journey days in July/August (`2025-07-28..31`, `2025-08-18..21`).",
                },
            ],
        },
        "route_and_dwell_defaults": {
            "source": "world/world.md § 7.9",
            "walk_minutes_from_ansell_house": WALK_MIN_FROM_HOME,
            "default_dwell_minutes": DEFAULT_DWELL_MIN,
            "carrier_day_rule": (
                "world.md § 7.9: 'Carrier day: Ansell -> Bell in Carter Lane (15 min walk, 30 min dwell) -> back, "
                "usually before rehearsal or after the play.' Where calendar.json schedules a generic carrier "
                "arrival window (`11:30–13:00` or `12:00–13:00`) on a day when William plays at `the_theatre` "
                "(`14:00–16:30`) or rehearses at `the_theatre` (`09:00–11:30`), or where § 6 explicitly places his "
                "Bell visit after the play or before rehearsal, the § 6 / § 7.9 timing governs."
            ),
        },
    }


def build_disagreements_list() -> list[dict[str, str]]:
    """Return every disagreement where two sources give a different place or time for the same stretch of a day, quoting both sources verbatim from the canon."""
    s6_by_id: dict[str, dict[str, Any]] = {e["id"]: e for e in parse_world_sec6_entries()}
    cal_by_key: dict[tuple[str, str], dict[str, Any]] = {
        (c["instance_date"], c["id"]): c for c in expand_calendar_events()
    }

    def s6_q(sid: str) -> str:
        e = s6_by_id[sid]
        prose_lines = [
            ln.strip()
            for ln in e["body"].splitlines()
            if ln.strip() and not ln.startswith("people:") and not ln.startswith("sources:")
        ]
        prose = " ".join(prose_lines)
        first_sent = prose.split(". ")[0] + ("." if not prose.split(". ")[0].endswith(".") else "")
        return (
            f"Rank 2 (§ 6 `{sid}` · `{e['date']} {e['time']}` · `{e['place_slug']}` · *{e['title']}*): "
            f"\"{first_sent}\""
        )

    def cal_q(d_str: str, cid: str) -> str:
        c = cal_by_key[(d_str, cid)]
        span = f"{c.get('start')}–{c.get('end')}" if c.get("start") else "all_day"
        rrule_tag = " RRULE instance" if c.get("rrule") else ""
        return f"Rank 3 (`{cid}`{rrule_tag} · `{d_str} {span}` · `{c.get('place_slug')}` · *{c.get('title')}*)"

    return [
        {
            "date": "2025-01-04",
            "stretch": "11:00–11:30",
            "higher_rank": s6_q("W001"),
            "lower_rank": cal_q("2025-01-04", "cal-0009"),
            "resolution": "Rank 2 (`W001`) places William at `crosby_place` (`11:00–11:30`), overriding `cal-0009`'s general `bishopsgate` slug.",
        },
        {
            "date": "2025-01-05",
            "stretch": "09:00–09:30",
            "higher_rank": s6_q("G002"),
            "lower_rank": cal_q("2025-01-05", "cal-0014"),
            "resolution": "Same place (`st_helens_church`); `cal-0014` spans `09:00–11:00` with `G002` logged at `09:30` during the sermon.",
        },
        {
            "date": "2025-01-11",
            "stretch": "18:00–18:15",
            "higher_rank": s6_q("W004"),
            "lower_rank": f"{cal_q('2025-01-11', 'cal-0012')} & {cal_q('2025-01-11', 'cal-0029')}",
            "resolution": "Same place (`the_jackdaw`); after `cal-0012` at `cross_keys_inn`, William and Burbage walk to `the_jackdaw` (`18:10–20:00`, merging `W004` and `cal-0029`).",
        },
        {
            "date": "2025-01-18",
            "stretch": "16:45–18:00",
            "higher_rank": s6_q("G006"),
            "lower_rank": cal_q("2025-01-18", "cal-0012"),
            "resolution": "Rank 2 (`G006`) keeps William abed at `ansell_house` all day (`450` steps; Cowley plays Egeon), overriding the recurring Saturday reckoning `cal-0012` at `cross_keys_inn`.",
        },
        {
            "date": "2025-01-23",
            "stretch": "09:00–11:00",
            "higher_rank": s6_q("S008a"),
            "lower_rank": cal_q("2025-01-23", "cal-0056"),
            "resolution": "Rank 2 (`S008a`) and `cal-0057` place William walking west with Bryan to `westminster_hall` (`10:00–11:30`), overriding `cal-0056` (`09:00–11:00` rehearsal at `cross_keys_inn`).",
        },
        {
            "date": "2025-02-25",
            "stretch": "09:00–11:00",
            "higher_rank": s6_q("G013"),
            "lower_rank": cal_q("2025-02-25", "cal-0138"),
            "resolution": "Rank 2 (`G013`) and `cal-0139` place William at `the_theatre` (`10:00–12:00`) inspecting the rotten north sill-beams with James and Cuthbert Burbage, overriding `cal-0138` (`09:00–11:00` rehearsal at `cross_keys_inn`).",
        },
        {
            "date": "2025-03-04",
            "stretch": "17:00–17:45",
            "higher_rank": s6_q("S022"),
            "lower_rank": cal_q("2025-03-04", "cal-0162"),
            "resolution": "Rank 2 (`S022`, `14:00–18:00` at `cross_keys_inn`, striking the trestles and drinking the patron's health before walking home by Cornhill) overrides `cal-0162` (`17:00–17:45` at `st_helens_church`).",
        },
        {
            "date": "2025-03-09",
            "stretch": "09:00–11:30 (hand dayplan vs calendar RRULE)",
            "higher_rank": "the hand plan (`content/weeks/2025-03-09/dayplan.md`): \"`st_helens_church` 09:30–11:30 (§ 4.2, Sunday church)\"",
            "lower_rank": cal_q("2025-03-09", "cal-0014"),
            "resolution": "`cal-0014` sets Sunday prayer at `09:00–11:00` (`why: 'Start is nine'`); the hand plan uses `09:30–11:30` and governs `2025-03-09` in `build/journal/`.",
        },
        {
            "date": "2025-03-10",
            "stretch": "08:30–12:30",
            "higher_rank": f"{s6_q('W118')} (prose: \"A hired cart, 8d, up Bishopsgate Street; William walks behind it with Nick\")",
            "lower_rank": cal_q("2025-03-10", "cal-0168"),
            "resolution": "`W118` header and `cal-0168` both tag `cross_keys_inn` (`08:30–11:00`), while `W118` prose describes walking behind the cart up Bishopsgate Street to `the_theatre`. The hand plan includes `the_theatre 09:45–12:30` and governs `2025-03-10` in `build/journal/`.",
        },
        {
            "date": "2025-03-15",
            "stretch": "11:30–14:00",
            "higher_rank": s6_q("S027"),
            "lower_rank": cal_q("2025-03-15", "cal-0177"),
            "resolution": "Same place (`burbage_house_holywell`); `S027` starts at `11:40` while `cal-0177` spans `11:30–13:30`.",
        },
        {
            "date": "2025-03-17",
            "stretch": "09:00–15:00 vs 11:00–15:00",
            "higher_rank": s6_q("W021"),
            "lower_rank": cal_q("2025-03-17", "cal-0178"),
            "resolution": "Same place (`bull_inn`); `W021` starts the errands window at `09:00–15:00`, absorbing `cal-0178` (`11:00–15:00`).",
        },
        {
            "date": "2025-03-26",
            "stretch": "05:40–18:00 road timings",
            "higher_rank": s6_q("S030a"),
            "lower_rank": f"{cal_q('2025-03-26', 'cal-0186')}, {cal_q('2025-03-26', 'cal-0187')} & {cal_q('2025-03-26', 'cal-0188')}",
            "resolution": "Rank 2 (`S030a`) gives `05:40` departure from `bull_inn`, `10:00` at `uxbridge`, `13:00` at `beaconsfield`, and `15:30` arrival at `high_wycombe`.",
        },
        {
            "date": "2025-03-27",
            "stretch": "05:30–20:40 road timings",
            "higher_rank": f"{s6_q('S030b')} & {s6_q('W025')}",
            "lower_rank": f"{cal_q('2025-03-27', 'cal-0189')}, {cal_q('2025-03-27', 'cal-0190')} & {cal_q('2025-03-27', 'cal-0191')}",
            "resolution": "Rank 2 (`S030b`, `W025`) sets `05:30` departure from `high_wycombe`, `17:45–19:15` bait at `oxford`, and `20:40` arrival at `woodstock`.",
        },
        {
            "date": "2025-04-08",
            "stretch": "05:30–18:30 road timings",
            "higher_rank": s6_q("W032a"),
            "lower_rank": f"{cal_q('2025-04-08', 'cal-0204')}, {cal_q('2025-04-08', 'cal-0205')} & {cal_q('2025-04-08', 'cal-0206')}",
            "resolution": "Rank 2 (`W032a`) sets `05:30` departure over `clopton_bridge`, `shipston_on_stour` (`09:30–10:00`), `chipping_norton` (`12:00–12:30`), and `woodstock` arrival at `17:30`.",
        },
        {
            "date": "2025-04-09",
            "stretch": "11:20–12:30 at Oxford",
            "higher_rank": s6_q("W032b"),
            "lower_rank": cal_q("2025-04-09", "cal-0208"),
            "resolution": "Rank 2 (`W032b`: \"Past Oxford without stopping, on the rise toward Wheatley, at a walk\") overrides `cal-0208` (`11:30–12:30` bait at `oxford`), recording `oxford` as a pass-through waypoint at `11:00`.",
        },
        {
            "date": "2025-04-13",
            "stretch": "09:00–09:30",
            "higher_rank": s6_q("S034"),
            "lower_rank": cal_q("2025-04-13", "cal-0215"),
            "resolution": "Same place (`st_helens_church`); `S034` begins at `09:00` and runs through `cal-0215`'s `11:30` end.",
        },
        {
            "date": "2025-05-08",
            "stretch": "08:40–09:00",
            "higher_rank": s6_q("S041"),
            "lower_rank": cal_q("2025-05-08", "cal-0276"),
            "resolution": "`S041` places William reading the post at `bishopsgate` at `08:40` on his walk to `the_theatre` (`09:10–11:00`, `cal-0276`).",
        },
        {
            "date": "2025-05-17",
            "stretch": "Daily step total (internal Rank 2 conflict: `S047` vs `W042`)",
            "higher_rank": f"{s6_q('W042')} (body states `7,900 steps` for the full day after the reckoning and supper)",
            "lower_rank": f"{s6_q('S047')} (body states `3,400 steps` at `10:00` on the morning walk to Paul's)",
            "resolution": "Both are Rank 2 (§ 6) on `2025-05-17`: `S047` logs `3,400` steps at `10:00` in the morning, whereas `W042` (`21:30–01:10`) logs `7,900` steps at night after the afternoon reckoning (`cal-0247`) at `the_theatre`. The end-of-day total (`7,900`) governs.",
        },
        {
            "date": "2025-05-20",
            "stretch": "09:00–11:00",
            "higher_rank": s6_q("G039"),
            "lower_rank": cal_q("2025-05-20", "cal-0303"),
            "resolution": "Rank 2 (`G039`: \"Before *Hercules*, a morning's revision of the Welsh scenes\") keeps William writing at `ansell_house` in the morning, overriding `cal-0303` (`09:00–11:00` rehearsal at `the_theatre`), before he crosses `london_bridge` to `the_rose` (`W043`, `cal-0305`).",
        },
        {
            "date": "2025-05-24",
            "stretch": "17:30–18:00",
            "higher_rank": s6_q("W131"),
            "lower_rank": cal_q("2025-05-24", "cal-0247"),
            "resolution": "Rank 2 (`W131`) finishes the reckoning at `the_theatre` by `17:25` so William and Burbage are on the settle at `the_jackdaw` at `17:30`.",
        },
        {
            "date": "2025-06-02",
            "stretch": "11:00–12:30 vs 17:00",
            "higher_rank": s6_q("S051"),
            "lower_rank": cal_q("2025-06-02", "cal-0335"),
            "resolution": "Same place (`the_theatre`); `cal-0335` (`11:00–12:30`), `cal-0336` (`14:00–16:30`), and `S051` (`17:00`) all take place at `the_theatre`.",
        },
        {
            "date": "2025-06-05",
            "stretch": "11:30–13:00 vs 12:50",
            "higher_rank": s6_q("W134"),
            "lower_rank": cal_q("2025-06-05", "cal-0343"),
            "resolution": "Rank 2 (`W134`) places William at `the_theatre` at `12:50` taking Richard Field's call before the `14:00` play (`cal-0344`), overriding `cal-0343`'s `11:30–13:00` carrier window at `the_bell_carter_lane` (visited after the play at `17:15–17:45` per § 7.9).",
        },
        {
            "date": "2025-06-10",
            "stretch": "09:00–11:00",
            "higher_rank": s6_q("S094"),
            "lower_rank": cal_q("2025-06-10", "cal-0355"),
            "resolution": "Rank 2 (`S094`, `03:50–11:00` at `ansell_house`, \"He does not walk once\") overrides `cal-0355` (`09:00–11:00` rehearsal at `the_theatre`).",
        },
        {
            "date": "2025-06-17",
            "stretch": "09:00–11:00",
            "higher_rank": f"{s6_q('W137')} & {s6_q('G045')}",
            "lower_rank": cal_q("2025-06-17", "cal-0371"),
            "resolution": "Rank 2 (`G045`, `09:00` at `ansell_house`) keeps William at `ansell_house` in the morning after Cuthbert's `08:10` call (`W137`), overriding `cal-0371` (`09:00–11:00` rehearsal at `the_theatre`).",
        },
        {
            "date": "2025-06-26",
            "stretch": "11:30–13:00",
            "higher_rank": f"Rank 1 (`where-he-is.md`: \"13 Jun – 5 Jul (fear radius)... 600 m triangle of `ansell_house` – `the_theatre` – `st_helens_church`\") & {s6_q('S066')} (prose: \"William does not walk that far this week; he sends the canvas and a line by Heminges's man\")",
            "lower_rank": cal_q("2025-06-26", "cal-0398"),
            "resolution": "Rank 1 (`where-he-is.md`) and Rank 2 (`S066`) explicitly state that William does not walk to `the_bell_carter_lane` and sends Heminges's man instead, overriding `cal-0398`.",
        },
        {
            "date": "2025-06-30",
            "stretch": "09:00–10:00",
            "higher_rank": s6_q("W053"),
            "lower_rank": cal_q("2025-06-30", "cal-0405"),
            "resolution": "Same place (`burbage_house_holywell`); `W053` spans `09:00–12:30`, absorbing `cal-0405` (`10:00–12:30`).",
        },
        {
            "date": "2025-07-08",
            "stretch": "09:00–11:00",
            "higher_rank": s6_q("G049"),
            "lower_rank": cal_q("2025-07-08", "cal-0419"),
            "resolution": "Rank 2 (`G049`, `08:00–11:00` at `ansell_house`) overrides `cal-0419` (`09:00–11:00` rehearsal at `the_theatre`).",
        },
        {
            "date": "2025-07-12",
            "stretch": "17:30–18:00",
            "higher_rank": s6_q("G051"),
            "lower_rank": cal_q("2025-07-12", "cal-0247"),
            "resolution": "Rank 2 (`G051`: \"An early supper after the reckoning (14s)\") finishes `cal-0247` at `the_theatre` by `17:20` so William, Pope, and Kemp reach `split_hazel` by `17:35`, followed by `S071` (`19:00–21:40` at `old_swan_stairs`).",
        },
        {
            "date": "2025-07-17",
            "stretch": "11:30–13:00 vs 12:20 & 17:40",
            "higher_rank": f"{s6_q('W058')} & {s6_q('W304')}",
            "lower_rank": cal_q("2025-07-17", "cal-0434"),
            "resolution": "Rank 2 (`W058` at `12:20` at `the_theatre`, and `W304` at `17:40` at `the_bell_carter_lane`) places his carrier visit at `17:40–18:20` after the afternoon play (`cal-0435`), overriding `cal-0434`'s `11:30–13:00` window.",
        },
        {
            "date": "2025-07-19",
            "stretch": "17:30–19:30",
            "higher_rank": s6_q("W059"),
            "lower_rank": f"{cal_q('2025-07-19', 'cal-0247')} & {cal_q('2025-07-19', 'cal-0438')}",
            "resolution": "Rank 2 (`W059`) ends `cal-0247` at `the_theatre` by `17:15`, walks to `old_swan_stairs` (`17:35–18:30`, `cal-0438`), and crosses by wherry to `paris_garden_swan` (`18:40–19:20`).",
        },
        {
            "date": "2025-07-29",
            "stretch": "03:50–19:40 vs 06:00–18:30",
            "higher_rank": s6_q("W062"),
            "lower_rank": cal_q("2025-07-29", "cal-0455"),
            "resolution": "Rank 2 (`W062`, `03:50–19:40`) sets the exact departure from `chalfont_st_giles` (`03:50`) and arrival at `grendon_underwood` (`19:40`).",
        },
        {
            "date": "2025-07-31",
            "stretch": "04:30–17:30 road timings",
            "higher_rank": s6_q("W064"),
            "lower_rank": f"{cal_q('2025-07-31', 'cal-0457')}, {cal_q('2025-07-31', 'cal-0458')} & {cal_q('2025-07-31', 'cal-0459')}",
            "resolution": "Rank 2 (`W064`) sets departure from `banbury` at `04:30`, `clopton_bridge` at `17:00–17:20`, and `henley_street` from `17:30`.",
        },
        {
            "date": "2025-08-03",
            "stretch": "09:00–09:30",
            "higher_rank": s6_q("W065"),
            "lower_rank": cal_q("2025-08-03", "cal-0462"),
            "resolution": "Same place (`holy_trinity`); `W065` starts at `09:00` and spans through `cal-0462` (`11:30`).",
        },
        {
            "date": "2025-08-10",
            "stretch": "12:00 boundary & daily step total (`W068` vs `G060`)",
            "higher_rank": f"{s6_q('G060')} (`7,800 steps` after the evening walk to Shottery) & {s6_q('W068')} (`12:00` at `high_cross_market`)",
            "lower_rank": f"{cal_q('2025-08-10', 'cal-0467')} & `W068` (`6,900` steps at midday)",
            "resolution": "Morning prayer at `holy_trinity` (`cal-0467`) finishes at `11:50` before dinner at the Sadlers' (`W068` at `12:00`); `G060`'s evening step figure (`7,800`) governs the full day.",
        },
        {
            "date": "2025-08-18",
            "stretch": "05:40–06:00 departure",
            "higher_rank": s6_q("W073a"),
            "lower_rank": cal_q("2025-08-18", "cal-0473"),
            "resolution": "Rank 2 (`W073a`) sets departure from `henley_street` at `05:40` (`clopton_bridge` at `06:00`) and arrival at `chipping_norton` at `18:00`.",
        },
        {
            "date": "2025-08-21",
            "stretch": "04:30–18:20 road timings",
            "higher_rank": f"{s6_q('W073d')} & {s6_q('W074')}",
            "lower_rank": f"{cal_q('2025-08-21', 'cal-0476')} & {cal_q('2025-08-21', 'cal-0477')}",
            "resolution": "Rank 2 (`W073d`, `W074`) sets `04:30` departure from `beaconsfield`, `10:00` at `uxbridge`, and `18:10` arrival at `the_bell_carter_lane`.",
        },
        {
            "date": "2025-08-24",
            "stretch": "13:00–18:00",
            "higher_rank": s6_q("S082"),
            "lower_rank": cal_q("2025-08-24", "cal-0480"),
            "resolution": "Same place (`smithfield`); `cal-0480` (`13:00–16:30`) and `S082` (`13:30–18:00`) merge to `13:00–18:00`.",
        },
        {
            "date": "2025-08-28",
            "stretch": "08:00–11:30 vs 09:00–11:00",
            "higher_rank": s6_q("G068"),
            "lower_rank": cal_q("2025-08-28", "cal-0489"),
            "resolution": "Rank 2 (`G068`: \"Seated, because the back will allow nothing else after yesterday\") keeps William at `ansell_house` (`08:00–11:30`), overriding `cal-0489` (`09:00–11:00` rehearsal at `the_theatre`).",
        },
        {
            "date": "2025-09-11",
            "stretch": "11:30–13:00 vs 17:40",
            "higher_rank": s6_q("W334"),
            "lower_rank": cal_q("2025-09-11", "cal-0519"),
            "resolution": "Rank 2 (`W334`, `17:40` at `the_bell_carter_lane`) places William's carrier visit after the afternoon play (`cal-0520`), overriding `cal-0519`'s `11:30–13:00` carrier arrival window.",
        },
        {
            "date": "2025-09-18",
            "stretch": "09:00–11:00 & 12:15–12:45",
            "higher_rank": s6_q("W082"),
            "lower_rank": f"{cal_q('2025-09-18', 'cal-0535')} & {cal_q('2025-09-18', 'cal-0536')}",
            "resolution": "Rank 2 (`W082`, `10:00` at `pauls_churchyard`) overrides `cal-0535` (`09:00–11:00` rehearsal at `the_theatre`) and merges with `cal-0536` (`12:15–12:45` at `pauls_churchyard`).",
        },
        {
            "date": "2025-09-23",
            "stretch": "09:00–11:00",
            "higher_rank": s6_q("S091"),
            "lower_rank": cal_q("2025-09-23", "cal-0546"),
            "resolution": "Rank 2 (`S091`: \"A writing morning; the tables say 'banished.'\") keeps William at `ansell_house` in the morning, overriding `cal-0546` (`09:00–11:00` rehearsal at `the_theatre`).",
        },
        {
            "date": "2025-10-01",
            "stretch": "09:00–11:00",
            "higher_rank": s6_q("G075"),
            "lower_rank": cal_q("2025-10-01", "cal-0568"),
            "resolution": "Rank 2 (`G075`, `09:00` at `fields_printing_house`, \"stays an hour\") overrides `cal-0568` (`09:00–11:00` rehearsal at `the_theatre`).",
        },
        {
            "date": "2025-10-02",
            "stretch": "11:30–13:00",
            "higher_rank": f"{s6_q('W400')} & {s6_q('W085')}",
            "lower_rank": cal_q("2025-10-02", "cal-0571"),
            "resolution": "Rank 2 (`W400` on 1 Oct: \"Gilbert comes after the shop shuts to carry the Michaelmas money to the Bell... tomorrow at about a quarter to three William will be dying at Ely House\", and `W085` at `the_theatre` from `13:00`) overrides personal attendance at `cal-0571` (`11:30–13:00` at `the_bell_carter_lane`).",
        },
        {
            "date": "2025-10-16",
            "stretch": "09:00–11:00",
            "higher_rank": f"{s6_q('W404')} & {s6_q('S099')} (prose: \"Pope's Gaunt drew no laugh\" on Thursday)",
            "lower_rank": cal_q("2025-10-16", "cal-0604"),
            "resolution": "Rank 2 (`W404` & `S099`, plus `world.md` § 5.2 / § 7.8) keeps William recovering at `ansell_house` all day on Thursday 16 Oct while Pope plays Gaunt, overriding `cal-0604` (`09:00–11:00` rehearsal at `the_theatre`).",
        },
        {
            "date": "2025-10-18",
            "stretch": "16:45–18:00",
            "higher_rank": s6_q("S099"),
            "lower_rank": cal_q("2025-10-18", "cal-0247"),
            "resolution": "Rank 2 (`S099`, `17:10` at `ansell_house`) has William leave the reckoning (`cal-0247`) at `the_theatre` by `16:50` so he is back at `ansell_house` at `17:10` before `cal-0612` (`18:15–19:00` at `st_helens_church`).",
        },
        {
            "date": "2025-10-23",
            "stretch": "11:30–13:00 vs 17:30",
            "higher_rank": s6_q("W406"),
            "lower_rank": cal_q("2025-10-23", "cal-0623"),
            "resolution": "Rank 2 (`W406`: \"After the comedy he walks to Carter Lane by Cheapside in the last light\") places his Bell visit at `17:30–18:20` after `cal-0624` (`14:00–16:30`), overriding `cal-0623`'s `11:30–13:00` window.",
        },
        {
            "date": "2025-11-11",
            "stretch": "06:30–11:45",
            "higher_rank": f"{s6_q('W093')} & {s6_q('S105')}",
            "lower_rank": f"{cal_q('2025-11-11', 'cal-0668')} & {cal_q('2025-11-11', 'cal-0669')}",
            "resolution": "Rank 2 (`W093` writing at `ansell_house` `06:30–10:15`, then `S105` at `leadenhall` `10:30–11:45` with Mistress Ansell) overrides `cal-0668`'s `06:30–08:45` window and `cal-0669` (`09:00–11:00` rehearsal at `the_theatre`).",
        },
        {
            "date": "2025-11-17",
            "stretch": "17:00–17:45",
            "higher_rank": s6_q("S106"),
            "lower_rank": cal_q("2025-11-17", "cal-0686"),
            "resolution": "Rank 2 (`S106`, `09:30–17:30` at `whitehall_tiltyard`) keeps William at the Accession Day tilt until `17:30`, overriding `cal-0686` (`17:00–17:45` at `st_helens_church`).",
        },
        {
            "date": "2025-11-22",
            "stretch": "17:30–20:30",
            "higher_rank": s6_q("W097"),
            "lower_rank": f"{cal_q('2025-11-22', 'cal-0247')} & {cal_q('2025-11-22', 'cal-0701')}",
            "resolution": "Rank 2 (`W097`, `17:30` at `the_jackdaw`) ends `cal-0247` at `the_theatre` at `17:25` and opens `the_jackdaw` stop at `17:30–20:30` (merging `W097` and `cal-0701`).",
        },
        {
            "date": "2025-11-30",
            "stretch": "09:00–09:30",
            "higher_rank": s6_q("S110"),
            "lower_rank": cal_q("2025-11-30", "cal-0721"),
            "resolution": "Same place (`st_helens_church`); `S110` starts at `09:00` and spans through `cal-0721` (`11:30`).",
        },
        {
            "date": "2025-12-01",
            "stretch": "10:45–11:00",
            "higher_rank": s6_q("S111"),
            "lower_rank": cal_q("2025-12-01", "cal-0722"),
            "resolution": "Rank 2 (`S111`, `10:45` at `pauls_churchyard`) has William leave `cal-0722` (`09:00–11:00` rehearsal at `the_theatre`) at `10:20` to reach `pauls_churchyard` by `10:45`, before returning for `cal-0723` (`14:00–16:30` at `the_theatre`).",
        },
        {
            "date": "2025-12-04",
            "stretch": "11:30–13:00 vs after the play",
            "higher_rank": f"Rank 4 / § 7.9 Carrier day rule ('after the play') + {cal_q('2025-12-04', 'cal-0731')} & {cal_q('2025-12-04', 'cal-0733')}",
            "lower_rank": cal_q("2025-12-04", "cal-0732"),
            "resolution": "Per § 7.9 ('Carrier day: Ansell -> Bell in Carter Lane... usually before rehearsal or after the play'), William visits `the_bell_carter_lane` (`17:15–17:55`) after the afternoon play (`cal-0733`).",
        },
        {
            "date": "2025-12-18",
            "stretch": "11:30–13:00 vs 12:00",
            "higher_rank": s6_q("W105"),
            "lower_rank": cal_q("2025-12-18", "cal-0761"),
            "resolution": "Same place (`the_bell_carter_lane`); `cal-0761` (`11:30–13:00`) and `W105` (`12:00`) merge at `the_bell_carter_lane` between morning rehearsal (`cal-0760`) and the afternoon play (`cal-0762`).",
        },
        {
            "date": "2025-12-22",
            "stretch": "14:00 header tag vs prose body & calendar",
            "higher_rank": f"{s6_q('W106')} (prose: \"The play is *Errors* at the Theatre... he plays the old Syracusan\"), {s6_q('M053')} & {cal_q('2025-12-22', 'cal-0772')}",
            "lower_rank": "Rank 2 (`W106` header tag: `11:30 and 14:00 · ansell_house`)",
            "resolution": "Internal § 6 header-vs-prose disagreement: `W106` carries a single place slug (`ansell_house`, for the `11:30` rent payment `cal-0771`), while its `14:00` timestamp and prose (and `cal-0772`) place him at `the_theatre` (`14:00–16:30`) after `old_swan_stairs` (`12:15–13:00`, `M053`).",
        },
        {
            "date": "2025-12-24",
            "stretch": "07:00–15:30 vs 09:00–13:00",
            "higher_rank": s6_q("W107"),
            "lower_rank": f"{cal_q('2025-12-24', 'cal-0776')} & {cal_q('2025-12-24', 'cal-0777')}",
            "resolution": "Rank 2 (`W107`, `07:00–15:30`) sets the exact tilt-boat departure window at `old_swan_stairs` (`07:00–11:00`) and arrival at `the_feathers_richmond` (`from 15:30`).",
        },
        {
            "date": "2025-12-29",
            "stretch": "13:00–14:00",
            "higher_rank": f"{s6_q('W108')} & {s6_q('M056')}",
            "lower_rank": cal_q("2025-12-29", "cal-0790"),
            "resolution": "Rank 2 (`W108`, `09:00–14:00` downriver to `old_swan_stairs`, and `M056`, `14:30` turning straight into `bull_inn` on the walk up Fish Street Hill) overrides `cal-0790` (`13:00–14:00` at `ansell_house`); he reaches `ansell_house` at `16:05` after the Bull.",
        },
    ]


def _compute_steps(d: date, day_type: str) -> tuple[int, bool]:
    """Return `(steps, is_explicit)` from `EXPLICIT_STEPS_BY_DATE` or deterministic § 7.8 band sampling."""
    d_str = d.isoformat()
    if d_str in EXPLICIT_STEPS_BY_DATE:
        return EXPLICIT_STEPS_BY_DATE[d_str][0], True

    dt_key = resolve_day_type_key(day_type, d_str)
    lo, hi = DAY_TYPE_STEP_BANDS[dt_key]
    digest = hashlib.sha256(f"steps:{d_str}:{day_type}".encode("utf-8")).digest()
    val = int.from_bytes(digest[:4], "big")
    raw_steps = lo + (val % (hi - lo + 1))
    rounded = int(round(raw_steps / 100.0) * 100)
    return max(lo, min(hi, rounded)), False


def generate_year_dayplans() -> list[dict[str, Any]]:
    """Generate the 365 day plans for 2025 from the canon."""
    s6_by_date: dict[str, list[dict[str, Any]]] = {}
    for e in parse_world_sec6_entries():
        s6_by_date.setdefault(e["date"], []).append(e)

    cal_by_date: dict[str, list[dict[str, Any]]] = {}
    for ev in expand_calendar_events():
        present, _ = is_presence_calendar_event(ev)
        if present:
            cal_by_date.setdefault(ev["instance_date"], []).append(ev)

    road_and_special = _road_and_special_day_itineraries()

    days: list[dict[str, Any]] = []
    cur = date(2025, 1, 1)
    while cur <= date(2025, 12, 31):
        d_str = cur.isoformat()
        s6_entries = s6_by_date.get(d_str, [])
        cal_events = cal_by_date.get(d_str, [])
        wakes = sleeping_place_for_night(cur - timedelta(days=1)) if cur > date(2025, 1, 1) else "ansell_house"
        sleeps = sleeping_place_for_night(cur)

        if d_str in road_and_special:
            spec = road_and_special[d_str]
            day_type = spec["day_type"]
            places_in_order = spec["places_in_order"]
            sources = spec["sources"]
        else:
            day_type, places_in_order, sources = _build_day_itinerary_general(
                cur, wakes, sleeps, s6_entries, cal_events
            )

        if cur > date(2025, 1, 1):
            prev_entries = s6_by_date.get((cur - timedelta(days=1)).isoformat(), [])
            for pe in prev_entries:
                carry = _extract_cross_midnight_carry(pe)
                if carry is not None:
                    places_in_order = _apply_overnight_carry_to_next_day(places_in_order, wakes, carry)

        steps, steps_is_explicit = _compute_steps(cur, day_type)
        steps_str = f"`{steps:,}`" if steps_is_explicit else f"~{steps:,}"

        days.append(
            {
                "date": d_str,
                "weekday": cur.strftime("%a"),
                "day_label": f"{cur.strftime('%a')} {cur.day} {cur.strftime('%b')}",
                "day_type": day_type,
                "steps": steps,
                "steps_is_explicit": steps_is_explicit,
                "steps_display": steps_str,
                "places_in_order": places_in_order,
                "sources": sources,
                "has_location_gap": False,
            }
        )
        cur += timedelta(days=1)

    return days


def parse_hand_march_dayplan(md_path: Path = DEFAULT_MARCH_DAYPLAN_MD) -> list[dict[str, str]]:
    """Parse the editor's hand dayplan for 2025-03-09..2025-03-15 without modifying it."""
    text = md_path.read_text(encoding="utf-8")
    month_map = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
        "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
    }
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        line_s = line.strip()
        if not line_s.startswith("|"):
            continue
        cells = [c.strip() for c in line_s.strip("|").split("|")]
        if len(cells) < 5:
            continue
        m = re.match(r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(\d{1,2})\s+([A-Z][a-z]{2})$", cells[0])
        if not m:
            continue
        day_num = int(m.group(1))
        mon_num = month_map[m.group(2)]
        d_str = f"2025-{mon_num:02d}-{day_num:02d}"
        rows.append(
            {
                "date": d_str,
                "day_label": cells[0],
                "day_type": cells[1],
                "steps_display": cells[2],
                "places_in_order": cells[3],
                "sources": cells[4],
            }
        )
    return rows


def build_march_comparison(generated_days: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compare generated 9-15 Mar against the hand plan (`content/weeks/2025-03-09/dayplan.md`)."""
    gen_by_date = {d["date"]: d for d in generated_days}
    hand_rows = parse_hand_march_dayplan()
    explanations: dict[str, dict[str, str]] = {
        "2025-03-09": {
            "steps": f"Hand plan writes literal `band`; `dayplan.py` samples a concrete deterministic value `{gen_by_date['2025-03-09']['steps_display']}` from the `2,000–5,500` `Household and rest` band.",
            "places": "Hand plan uses `09:30–11:30 (§ 4.2, Sunday church)` with 0-min walk buffer; `dayplan.py` uses expanded RRULE `cal-0014` (`09:00–11:00`, `why: 'Start is nine'`) with 2-min walk buffer (`to 08:58`, `from 11:02`).",
        },
        "2025-03-10": {
            "steps": "Same explicit § 6 step count (`8,200` from `W118`), formatted as `8,200 (W118)` in hand plan vs `` `8,200` `` in `dayplan.py`.",
            "places": "`W118` header and `cal-0168` both tag `cross_keys_inn` (`08:30–11:00`), whereas `W118` prose says 'A hired cart, 8d, up Bishopsgate Street; William walks behind it with Nick'. Hand plan splits the morning into `cross_keys_inn 08:30–09:15` and `the_theatre 09:45–12:30`; `dayplan.py`'s general rule uses the header/calendar stop `cross_keys_inn 08:30–11:00` without inferring the unheaded destination stop.",
        },
        "2025-03-11": {
            "steps": f"Hand plan writes `band`; `dayplan.py` samples deterministic `{gen_by_date['2025-03-11']['steps_display']}` from the `4,000–7,000` `Writing day at the lodging (Lent)` band.",
            "places": "Both start at `ansell_house to 11:10 · pauls_churchyard 11:30` (`M007`) and note `W020` at `18:40`. Hand plan uses a 45-min dwell (`11:30–12:15`, back `from 12:35`); `dayplan.py`'s default dwell at `pauls_churchyard` is 60 min (`11:30–12:30`, back `from 12:50`).",
        },
        "2025-03-12": {
            "steps": f"Hand plan writes `band`; `dayplan.py` samples deterministic `{gen_by_date['2025-03-12']['steps_display']}` from the `7,000–12,000` `Rehearsal-heavy day` band.",
            "places": "Hand plan extends `the_theatre` to `10:00–12:30 (S025; cal-0172 10:00–12:00)` with a 30-min walk back (`from 13:00`); `dayplan.py` uses `cal-0172`'s `10:00–12:00` window and § 7.9's 20-min walk (`from 12:20`).",
        },
        "2025-03-13": {
            "steps": f"Hand plan writes `band`; `dayplan.py` samples deterministic `{gen_by_date['2025-03-13']['steps_display']}` from the `4,000–7,000` `Writing day at the lodging (Lent)` band.",
            "places": "Exact match (`` `ansell_house` all day ``).",
        },
        "2025-03-14": {
            "steps": f"Hand plan writes `band`; `dayplan.py` samples deterministic `{gen_by_date['2025-03-14']['steps_display']}` from the `4,000–7,000` `Writing day at the lodging (Lent)` band.",
            "places": "Both place him at `` `bishopsgate` 15:30–16:00 (S026) ``; hand plan uses `to 15:15` / `from 16:10` while `dayplan.py` uses `WALK_MIN_FROM_HOME['bishopsgate'] = 5` (`to 15:25` / `from 16:05`).",
        },
        "2025-03-15": {
            "day_type": "Both resolve to `Boat day`; hand plan appends explanatory note `, with § 7.8's special value`.",
            "steps": "Same explicit § 6 step count (`9,600` from `W119`), formatted as `9,600 (W119)` in hand plan vs `` `9,600` `` in `dayplan.py`.",
            "places": "Both follow `ansell_house to 07:15 · old_swan_stairs 07:30 · by wherry to whitehall_palace 08:15–10:30 (W119) · on foot by the Strand and Holborn · burbage_house_holywell · ansell_house`. Hand plan uses `S027`'s `11:40–14:00` window (`from 14:30`); `dayplan.py` merges `S027` (`11:40`) with `cal-0177` (`11:30–13:30`, back `from 13:50`).",
        },
    }
    diffs: list[dict[str, Any]] = []
    for h in hand_rows:
        d_str = h["date"]
        g = gen_by_date[d_str]
        diffs.append(
            {
                "date": d_str,
                "day_label": h["day_label"],
                "hand": {
                    "day_type": h["day_type"],
                    "steps": h["steps_display"],
                    "places_in_order": h["places_in_order"],
                    "sources": h["sources"],
                },
                "generated": {
                    "day_type": g["day_type"],
                    "steps": g["steps_display"],
                    "places_in_order": g["places_in_order"],
                    "sources": g["sources"],
                },
                "day_type_matches": h["day_type"] == g["day_type"],
                "steps_matches": h["steps_display"] == g["steps_display"],
                "places_matches": h["places_in_order"] == g["places_in_order"],
                "explanations": explanations.get(d_str, {}),
            }
        )
    return diffs


def _week_buckets(days: list[dict[str, Any]]) -> list[tuple[str, list[dict[str, Any]]]]:
    """Group the 365 days of 2025 into Sunday-to-Saturday weeks named by their Sunday start date (or 2025-01-01 for the partial first week)."""
    buckets: list[tuple[str, list[dict[str, Any]]]] = []
    current_week: list[dict[str, Any]] = []
    current_label = "2025-01-01"

    for d in days:
        dt = date.fromisoformat(d["date"])
        if dt.weekday() == 6 and current_week:  # Sunday starts a new week
            buckets.append((current_label, current_week))
            current_week = [d]
            current_label = d["date"]
        else:
            current_week.append(d)
    if current_week:
        buckets.append((current_label, current_week))
    return buckets


def _render_week_markdown(week_label: str, week_days: list[dict[str, Any]]) -> str:
    """Render a Sunday-to-Saturday week in the exact table format of `content/weeks/2025-03-09/dayplan.md`."""
    first_dt = date.fromisoformat(week_days[0]["date"])
    last_dt = date.fromisoformat(week_days[-1]["date"])
    if first_dt.month == last_dt.month:
        span_str = f"{first_dt.day}–{last_dt.day} {last_dt.strftime('%B %Y')}"
    else:
        span_str = f"{first_dt.day} {first_dt.strftime('%B')} – {last_dt.day} {last_dt.strftime('%B %Y')}"

    lines = [
        f"# Day plan — week of {span_str}",
        "",
        "| Date | Day type (§ 7.8) | Steps | Places, in order | Sources |",
        "|---|---|---:|---|---|",
    ]
    for d in week_days:
        lines.append(
            f"| {d['day_label']} | {d['day_type']} | {d['steps_display']} | {d['places_in_order']} | {d['sources']} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_dayplan_outputs(
    output_dir: Path = DEFAULT_DAYPLANS_DIR,
) -> dict[str, Any]:
    """Generate and write `content/dayplans/2025.json`, `content/dayplans/weeks/*.md`, and `content/dayplans/index.md`."""
    output_dir.mkdir(parents=True, exist_ok=True)
    weeks_dir = output_dir / "weeks"
    weeks_dir.mkdir(parents=True, exist_ok=True)

    days = generate_year_dayplans()
    rules = build_rules_spec()
    disagreements = build_disagreements_list()
    march_comparison = build_march_comparison(days)
    week_buckets = _week_buckets(days)

    # Write weekly markdown tables
    week_files: list[str] = []
    for week_label, week_days in week_buckets:
        wk_path = weeks_dir / f"{week_label}.md"
        wk_path.write_text(_render_week_markdown(week_label, week_days), encoding="utf-8")
        week_files.append(f"weeks/{week_label}.md")

    # Write machine-readable 2025.json
    payload = {
        "year": 2025,
        "total_days": len(days),
        "governed_by_hand_plan_in_year_tree": {
            "dates": ["2025-03-09", "2025-03-10", "2025-03-11", "2025-03-12", "2025-03-13", "2025-03-14", "2025-03-15"],
            "hand_plan_path": "content/weeks/2025-03-09/dayplan.md",
            "note": (
                "Per Wave 0 specification, the editor's hand dayplan at content/weeks/2025-03-09/dayplan.md "
                "stays untouched and governs 9–15 Mar in build/journal/ until the editor rules on the comparison differences."
            ),
        },
        "rules": rules,
        "disagreements": disagreements,
        "march_comparison": march_comparison,
        "days": days,
    }
    json_path = output_dir / "2025.json"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Summarize counts by day_type
    type_counts: dict[str, int] = {}
    explicit_step_days = 0
    for d in days:
        type_counts[d["day_type"]] = type_counts.get(d["day_type"], 0) + 1
        if d["steps_is_explicit"]:
            explicit_step_days += 1

    # Write human-readable index.md with rules, disagreements, March comparison, and links to all weekly tables
    md_lines = [
        "# 2025 Day Plans — William Shakespeare (`william-journal` Wave 0)",
        "",
        "Generated by [`tools/dayplan.py`](../../tools/dayplan.py) from:",
        "- [`content/threads/merged/where-he-is.md`](../threads/merged/where-he-is.md) and [`world/world.md`](../../world/world.md) § 7.9 (Rank 1 — overnight base and geographic bounds across all 365 nights)",
        "- [`world/world.md`](../../world/world.md) § 6 (Rank 2 — 376 dated narrative entries across 307 distinct days)",
        "- [`calendar/merged/calendar.json`](../../calendar/merged/calendar.json) (Rank 3 — 795 raw events expanding to 874 instances across 349 days, filtered by the written presence rule to 496 presence-recording instances)",
        "- [`world/world.md`](../../world/world.md) § 7.8 & § 7.9 (Rank 4 — day-type step bands, route transit minutes, dwell defaults, and stationary home-base fallback)",
        "",
        "Machine-readable source of truth: [`2025.json`](2025.json).",
        "",
        "---",
        "",
        "## 1. Summary of the 365 Days",
        "",
        f"- **Total days covered:** {len(days)} (`2025-01-01` through `2025-12-31`)",
        f"- **Days with explicit § 6 step counts (`backticked`):** {explicit_step_days}",
        f"- **Days with deterministic § 7.8 band step counts (`~tilde`):** {len(days) - explicit_step_days}",
        "- **Days with unplaced away gaps:** 0 (every day has a known overnight base in `where-he-is.md` and every stop resolves to a canonical place slug in `world/world.md` § 4)",
        "- **Riot-season river constraint (`2025-06-12` – `2025-07-18`):** 0 stops south of the Thames (`lat < 51.5085`); William remains within the north-bank triangle (`ansell_house` – `the_theatre` – `st_helens_church`, returning to `the_bell_carter_lane` only on 17 Jul per `W304`).",
        "",
        "| Day type (§ 7.8) | Step band | Days in 2025 |",
        "|---|---:|---:|",
    ]
    for dt_spec in rules["day_type_rules"]["types"]:
        dt_name = dt_spec["day_type"]
        lo, hi = dt_spec["step_band"]
        md_lines.append(f"| {dt_name} | {lo:,}–{hi:,} | {type_counts.get(dt_name, 0)} |")

    md_lines.extend(
        [
            "",
            "---",
            "",
            "## 2. Written Rules Used by `tools/dayplan.py`",
            "",
            "### 2.1 Precedence Ranks for Where He Is",
            "",
            "1. **Rank 1 — `where-he-is.md` & `world.md` § 7.9 (365-night table):** Sets the overnight base (`ansell_house` 317 nights, `henley_street` 28 nights across Mar 28–Apr 7 and Jul 31–Aug 17, `the_feathers_richmond` 5 nights across Dec 24–28, and 15 road/carrier nights across 4 Stratford journeys) plus the 12 Jun – 18 Jul riot-season river ban (`lat >= 51.5085`) and the 13 Jun – 5 Jul 600 m triangle (`ansell_house` – `the_theatre` – `st_helens_church`).",
            "2. **Rank 2 — `world.md` § 6 (376 dated entries):** Places William at the entry's `place_slug` and time window, plus any secondary movements stated in the entry's prose (e.g., wherry crossings via `old_swan_stairs`, `paris_garden_swan`, `canon_row`, `whitehall_palace`, `the_feathers_richmond`, or road waypoints `chipping_norton`, `clopton_bridge`). Overrides Rank 3 whenever a § 6 entry keeps him at `ansell_house`/`henley_street` or places him elsewhere during a calendar event.",
            "3. **Rank 3 — Presence-recording events in `calendar/merged/calendar.json`:** Timed confirmed events with a `place_slug` that pass the written presence filter below.",
            "4. **Rank 4 — Written defaults (`world.md` § 7.8 & § 7.9):** When Ranks 1–3 record no movement outside the overnight base, William remains at his overnight base (`all day`). Walk transit times from `ansell_house` (`WALK_MIN_FROM_HOME`) and dwell durations (`DEFAULT_DWELL_MIN`) follow § 7.9 (`10 min` Cross Keys, `15 min` Bell, `20 min` Paul's / Theatre, `25 min` Field's, `15 min` Old Swan Stairs, `2–5 min` St Helen's / Bull / Split Hazel). Whenever a gap between two London stops is at least 60 minutes and at least `walk_out + walk_in + 20` minutes, he returns to `ansell_house` in between.",
            "",
            "### 2.2 Calendar Presence Filter (`layer`, `why`, `attendees`)",
            "",
            "Out of **795** raw events in `calendar/merged/calendar.json` (**874** expanded instances once the 4 `rrule` events `cal-0012`, `cal-0014`, `cal-0247`, `cal-0578` are expanded with their `exdates`), **496** instances record William's presence and **378** are excluded:",
            "",
            "| Rule | Included | Excluded | Written basis (`world.md` / `calendar.json`) |",
            "|---|---:|---:|---|",
            "| `status != 'confirmed'` | 0 | 3 | `cal-0045` (`2025-01-19`), `cal-0407` (`2025-06-30`), and `cal-0779` (`2025-12-26`) have `status: 'cancelled'` and `why` explaining the cancelled supper/gathering. |",
            "| `all_day == true` or `place_slug == null` | 0 | 79 | 72 all-day banner spans + 4 `No play` lines + 3 null-place timed events (`cal-0468` Aug 10 Sadlers' dinner, `cal-0591` Oct 10 Yaxley, `cal-0599` Oct 14 Yaxley, each placed by § 6 entries `W068`, `W402`, `W089`). |",
            "| `layer == 'rival_bill'` | 4 | 205 | `world.md` § 7.1 & `why`: *\"The bill, not an attendance. He reads it and does not go.\"* Included only when `'william_shakespeare' in attendees` (`cal-0115` Feb 6, `cal-0305` May 20, `cal-0493` Aug 29, `cal-0718` Nov 29). |",
            "| `layer == 'money'` | 5 | 12 | `cal-0578` (*Firing and washing, vj d.*, 12 Mondays) has `organizer: 'dorcas_ansell'`, `attendees: null`, and `why: 'Household account line on the calendar'`. Included only when `organizer == 'william_shakespeare'` (`cal-0001`, `cal-0177`, `cal-0199`, `cal-0770`, `cal-0795`). |",
            "| `layer == 'company_play'` | 160 | 79 | `world.md` § 7.1: *\"with `(I play)` on about four days in six and his role in the description.\"* Stock bills without `(I play)` do not require his presence at the playhouse unless a § 6 entry (`W038` on May 3, `S008b` on Jan 23) or Saturday reckoning (`cal-0012` / `cal-0247`) places him there. |",
            "| All other confirmed timed layers (`rehearsal`, `company_business`, `travel`, `sunday`, `feast`, `social`, `carrier`, `family_day`, `print`, `court`, `other`, `quarter_day`, `law_term`) | 327 | 0 | Direct personal/company schedule, subject to Rank 1 & Rank 2 overrides on specific days. |",
            "",
            "---",
            "",
            "## 3. Comparison Against the hand plan (`2025-03-09` – `2025-03-15`)",
            "",
            "Per the Wave 0 specification, [`content/weeks/2025-03-09/dayplan.md`](../weeks/2025-03-09/dayplan.md) is **untouched** and continues to govern `2025-03-09` through `2025-03-15` in `build/journal/` until the editor rules on any differences.",
            "",
            "| Date | Field | the hand plan (`content/weeks/2025-03-09/dayplan.md`) | Code-Generated (`tools/dayplan.py`) | Why They Differ / Match |",
            "|---|---|---|---|---|",
        ]
    )

    for comp in march_comparison:
        d_lbl = f"{comp['day_label']} (`{comp['date']}`)"
        h = comp["hand"]
        g = comp["generated"]
        exps = comp.get("explanations", {})
        if not comp["day_type_matches"]:
            md_lines.append(
                f"| {d_lbl} | `Day type` | {h['day_type']} | {g['day_type']} | {exps.get('day_type', 'Difference in day type string.')} |"
            )
        if not comp["steps_matches"]:
            md_lines.append(
                f"| {d_lbl} | `Steps` | {h['steps']} | {g['steps']} | {exps.get('steps', 'Difference in step representation.')} |"
            )
        if not comp["places_matches"]:
            md_lines.append(
                f"| {d_lbl} | `Places, in order` | {h['places_in_order']} | {g['places_in_order']} | {exps.get('places', 'Difference in stop sequence.')} |"
            )
        else:
            md_lines.append(
                f"| {d_lbl} | `Places, in order` | {h['places_in_order']} | {g['places_in_order']} | {exps.get('places', 'Exact match.')} |"
            )

    md_lines.extend(
        [
            "",
            "---",
            "",
            f"## 4. Source Disagreements Across 2025 ({len(disagreements)} Cases)",
            "",
            "Every date where two sources of different rank (or two § 6 entries on the same day) give a different place, time window, or step count for the same stretch of a day:",
            "",
            "| Date | Stretch | Higher-Rank Source (Governs) | Lower-Rank / Conflicting Source | Resolution |",
            "|---|---|---|---|---|",
        ]
    )

    for dis in disagreements:
        md_lines.append(
            f"| `{dis['date']}` | {dis['stretch']} | {dis['higher_rank']} | {dis['lower_rank']} | {dis['resolution']} |"
        )

    md_lines.extend(
        [
            "",
            "---",
            "",
            "## 5. Weekly Day Plan Tables (53 Weeks)",
            "",
            "| Week file | Dates covered |",
            "|---|---|",
        ]
    )
    for week_label, week_days in week_buckets:
        md_lines.append(
            f"| [`weeks/{week_label}.md`](weeks/{week_label}.md) | `{week_days[0]['date']}` – `{week_days[-1]['date']}` ({len(week_days)} days) |"
        )
    md_lines.append("")

    index_path = output_dir / "index.md"
    index_path.write_text("\n".join(md_lines), encoding="utf-8")

    return {
        "total_days": len(days),
        "total_weeks": len(week_buckets),
        "total_disagreements": len(disagreements),
        "json_path": str(json_path),
        "index_path": str(index_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate 2025 day plans for the william-journal project.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_DAYPLANS_DIR,
        help="Directory to write 2025.json, index.md, and weeks/*.md",
    )
    args = parser.parse_args()
    summary = write_dayplan_outputs(args.output_dir)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
