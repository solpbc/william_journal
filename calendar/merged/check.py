#!/usr/bin/env python3
"""Validate calendar.json against world.md and the calendar brief.

Independent of build.py. Exit 0 when the file is clean, 1 otherwise.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORLD = HERE.parents[1] / "world" / "world.md"
CAL = HERE / "calendar.json"

LAYERS = {
    "feast", "sunday", "law_term", "quarter_day", "moon", "company_play",
    "rival_bill", "rehearsal", "company_business", "carrier", "family_day",
    "travel", "social", "court", "print", "money", "private_mark", "other",
}
BYDAY = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}
CROSS_DATES = [
    "2025-01-05", "2025-02-28", "2025-03-22", "2025-05-22",
    "2025-06-08", "2025-09-14", "2025-10-29",
]
CARRIERS = [
    "2025-01-16", "2025-02-06", "2025-02-27", "2025-03-20", "2025-04-24",
    "2025-05-15", "2025-06-05", "2025-06-26", "2025-07-17", "2025-09-11",
    "2025-10-02", "2025-10-23", "2025-11-13", "2025-12-04", "2025-12-18",
]
ANCHORS = {
    "2025-01-01": 2, "2025-01-06": 0, "2025-02-02": 6, "2025-03-04": 1,
    "2025-03-25": 1, "2025-04-18": 4, "2025-04-20": 6, "2025-04-21": 0,
    "2025-05-18": 6, "2025-05-29": 3, "2025-06-08": 6, "2025-06-24": 1,
    "2025-06-29": 6, "2025-06-30": 0, "2025-07-24": 3, "2025-08-24": 6,
    "2025-09-07": 6, "2025-11-17": 0, "2025-12-22": 0, "2025-12-25": 3,
    "2025-12-26": 4, "2025-12-27": 5, "2025-12-28": 6, "2025-12-31": 2,
}
TITLE_WEEKDAY = (
    ("Easter Day", 6), ("Palm Sunday", 6), ("Low Sunday", 6),
    ("Whitsunday", 6), ("Trinity Sunday", 6), ("Rogation Sunday", 6),
    ("Septuagesima", 6), ("Mothering Sunday", 6), ("Advent Sunday", 6),
    ("Holy Innocents", 6), ("St Bartholomew", 6), ("The Queen's birthday", 6),
    ("St Peter.", 6), ("St Thomas.", 6), ("Shrove Tuesday", 1),
    ("Ash Wednesday", 2), ("Good Friday", 4), ("Lady Day", 1),
    ("Ascension.", 3), ("Twelfth Day", 0), ("Accession Day", 0),
    ("Christmas Day", 3), ("St Stephen", 4), ("St John.", 5),
)
BANNED = re.compile(
    r"\b(execution|executed|hanged|hanging|gallows|tyburn|quartered|beheaded|"
    r"plague|pestilence|tour|1596)\b",
    re.I,
)
CHILD_BAD = re.compile(r"\b(ill|sick|fever|dying|death|grave)\b", re.I)
CHILD_NAME = re.compile(r"\b(hamnet|judith|susanna)\b", re.I)


def load_world(text: str):
    def at(heading: str) -> int:
        m = re.search(rf"^{re.escape(heading)}", text, re.M)
        if not m:
            raise SystemExit(f"world is missing {heading}")
        return m.start()

    i3, i4, i5 = at("## 3. "), at("## 4. "), at("## 5. ")
    i6, i7 = at("## 6. "), at("## 7. ")
    people = set(re.findall(r"^#### `([a-z0-9_]+)`", text[i3:i4], re.M))
    places = set(re.findall(r"^#### `([a-z0-9_]+)`", text[i4:i5], re.M))
    entries = set(re.findall(r"\*\*([A-Z]\d+[a-z]?)\s·", text[i6:i7]))
    return people, places, entries


def parse_until(raw: str) -> datetime:
    return datetime.strptime(raw, "%Y%m%dT%H%M%SZ")


def rule_days(ev: dict) -> tuple[list[str], list[str]]:
    """Return (occurrences after exdates, raw days before exdates)."""
    parts = dict(p.split("=", 1) for p in ev["rrule"].split(";"))
    if parts.get("FREQ") != "WEEKLY" or "UNTIL" not in parts or "BYDAY" not in parts:
        raise ValueError(f"unsupported rule {ev['rrule']}")
    until = parse_until(parts["UNTIL"])
    by = BYDAY[parts["BYDAY"]]
    start = datetime.fromisoformat(ev["date"] + "T" + ev["start"])
    if start.weekday() != by:
        raise ValueError(f"BYDAY does not match {ev['date']} {ev['title']}")
    ex = set(ev.get("exdates") or [])
    raw, kept = [], []
    cur = start
    while cur <= until:
        key = cur.date().isoformat()
        raw.append(key)
        if key not in ex:
            kept.append(key)
        cur += timedelta(days=7)
    return kept, raw


def perf_name(title: str) -> str | None:
    for prefix in ("Play: ", "Richmond: ", "Canon Row: "):
        if title.startswith(prefix):
            return title[len(prefix):].split(",")[0].strip()
    return None


def visible(ev: dict) -> str:
    return " ".join(ev.get(k) or "" for k in ("title", "description", "location"))


def main() -> int:
    errors = []

    def bad(msg: str):
        errors.append(msg)

    people, places, entry_ids = load_world(WORLD.read_text(encoding="utf-8"))
    data = json.loads(CAL.read_text(encoding="utf-8"))
    if data.get("owner") != "william_shakespeare" or data.get("timezone") != "Europe/London":
        bad("owner or timezone is wrong")
    events = data.get("events")
    if not isinstance(events, list) or not events:
        bad("events missing")
        print("\n".join(errors))
        return 1

    ids = [ev.get("id") for ev in events]
    if ids != [f"cal-{i:04d}" for i in range(1, len(events) + 1)]:
        bad("ids are not cal-0001 upward in order")
    if len(ids) != len(set(ids)):
        bad("duplicate ids")

    by_date: dict[str, list[dict]] = {}
    explicit_key: dict[tuple[str, str], list[str]] = {}
    for ev in events:
        by_date.setdefault(ev["date"], []).append(ev)
        explicit_key.setdefault((ev["date"], ev["title"]), []).append(ev["id"])
    for key, owners in explicit_key.items():
        if len(owners) > 1:
            bad(f"duplicate {key[0]} {key[1]} ({', '.join(owners)})")

    expansions: list[tuple[dict, list[str]]] = []
    for ev in events:
        d = ev["date"]
        try:
            day = date.fromisoformat(d)
        except ValueError:
            bad(f"bad date {d}")
            continue
        if day.year != 2025:
            bad(f"date not in 2025: {d} {ev['title']}")
        if ev.get("end_date"):
            try:
                end_day = date.fromisoformat(ev["end_date"])
            except ValueError:
                bad(f"bad end_date on {ev['id']}")
                end_day = day
            if end_day < day or end_day.year != 2025:
                bad(f"end_date out of range on {ev['id']}")
        if d in ANCHORS and day.weekday() != ANCHORS[d]:
            bad(f"{d} weekday is {day.weekday()}, expected {ANCHORS[d]}")
        for prefix, wd in TITLE_WEEKDAY:
            if ev["title"].startswith(prefix) and day.weekday() != wd:
                bad(f"{ev['title']} on {d} is weekday {day.weekday()}, want {wd}")

        if ev.get("layer") not in LAYERS:
            bad(f"bad layer {ev.get('layer')} on {ev['id']}")
        if ev.get("tier") not in {"T1", "T2", "T3", "T4", "T5"}:
            bad(f"bad tier on {ev['id']}")
        if ev.get("status") not in {"confirmed", "tentative", "cancelled"}:
            bad(f"bad status on {ev['id']}")
        if ev.get("all_day"):
            if "start" in ev or "end" in ev:
                bad(f"all-day event has a clock time: {ev['id']}")
        else:
            for field in ("start", "end"):
                if not re.fullmatch(r"\d{2}:\d{2}", ev.get(field, "")):
                    bad(f"missing {field} on {ev['id']}")
            if re.fullmatch(r"\d{2}:\d{2}", ev.get("start", "")) and re.fullmatch(r"\d{2}:\d{2}", ev.get("end", "")):
                sh, sm = (int(x) for x in ev["start"].split(":"))
                eh, em = (int(x) for x in ev["end"].split(":"))
                if sm % 5 or em % 5:
                    bad(f"time not on a 5-minute mark: {ev['id']} {ev['start']}-{ev['end']}")
                if (eh, em) <= (sh, sm):
                    bad(f"end not after start: {ev['id']} {ev['title']}")

        for field in ("created", "modified"):
            raw = ev.get(field)
            if raw is None:
                if field == "created":
                    bad(f"no created on {ev['id']}")
                continue
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", raw):
                bad(f"bad {field} on {ev['id']}: {raw}")
                continue
            moment = datetime.fromisoformat(raw)
            if not (date(2024, 12, 1) <= moment.date() <= date(2025, 12, 31)):
                bad(f"{field} outside 2024-12..2025 on {ev['id']}")

        start_at = datetime.fromisoformat(d + "T" + (ev.get("start") or "00:00"))
        if not ev.get("after_the_fact"):
            created = datetime.fromisoformat(ev["created"])
            if created >= start_at:
                bad(f"created not before start: {ev['id']} {d} {ev['title']}")
            if ev.get("modified") and datetime.fromisoformat(ev["modified"]) >= start_at:
                bad(f"modified not before start: {ev['id']} {d} {ev['title']}")
        if ev.get("rrule"):
            if "UNTIL=" not in ev["rrule"]:
                bad(f"rrule without UNTIL: {ev['id']}")
            else:
                until = parse_until(dict(p.split("=", 1) for p in ev["rrule"].split(";"))["UNTIL"])
                if until.date() > date(2025, 12, 31):
                    bad(f"UNTIL past 2025: {ev['id']} {ev['rrule']}")
                try:
                    kept, raw = rule_days(ev)
                except ValueError as exc:
                    bad(str(exc))
                    kept, raw = [], []
                expansions.append((ev, kept))
                extra = set(ev.get("exdates") or []) - set(raw)
                if extra:
                    bad(f"exdate outside the series {ev['id']}: {sorted(extra)}")
                for day_key in kept:
                    if day_key == ev["date"]:
                        continue
                    if (day_key, ev["title"]) in explicit_key:
                        bad(f"series doubles an event on {day_key}: {ev['title']}")

        if ev.get("organizer") not in people:
            bad(f"organizer not in § 3: {ev.get('organizer')} ({ev['id']})")
        for slug in ev.get("attendees") or []:
            if slug not in people:
                bad(f"attendee not in § 3: {slug} ({ev['id']})")
            if "@" in slug:
                bad(f"attendee looks like an address: {slug}")
        if ev.get("place_slug") and ev["place_slug"] not in places:
            bad(f"place not in § 4: {ev['place_slug']} ({ev['id']})")
        for eid in ev.get("entries") or []:
            if eid not in entry_ids:
                bad(f"entry not in § 6: {eid} ({ev['id']})")
        if not isinstance(ev.get("entries"), list):
            bad(f"entries not a list on {ev['id']}")
        if not ev.get("why"):
            bad(f"missing why on {ev['id']}")

        blob = visible(ev)
        if "the_lady_unnamed" in json.dumps(ev):
            bad(f"the lady's slug is on {ev['id']}")
        if BANNED.search(blob):
            bad(f"never-list word in {ev['id']}: {ev['title']}")
        if re.search(r"\blady\b", blob, re.I) and "Lady Day" not in blob:
            bad(f"the word lady is on {ev['id']}: {ev['title']}")
        if CHILD_NAME.search(blob) and CHILD_BAD.search(blob):
            bad(f"a child is spoken of as unwell on {ev['id']}")
        if ev.get("place_slug") == "tyburn":
            bad("a line places him at Tyburn")
        if ev.get("place_slug") == "greenwich_palace":
            bad("a line places him at Greenwich")
        if ev.get("place_slug") == "tower_hill" and d != "2025-02-01":
            bad(f"Tower Hill on {d}")
        if ev.get("place_slug") in {"oxford_road", "banbury_road"}:
            bad(f"road token used as a place: {ev['place_slug']}")

        if ev["layer"] == "rival_bill" and "2025-06-12" <= d <= "2025-07-19":
            if re.search(r"\byard\b|I stood", blob, re.I):
                bad(f"Rose attendance language inside the river ban: {d}")
        if ev["layer"] == "rival_bill" and day.weekday() == 6:
            bad(f"Sunday Rose bill: {d} {ev['title']}")
        if ev["layer"] == "carrier" and day.weekday() != 3:
            bad(f"carrier not on a Thursday: {d}")
        name = perf_name(ev["title"])
        if name and ev["status"] == "confirmed" and day.weekday() == 6 and d != "2025-12-28":
            bad(f"Sunday performance: {d} {ev['title']}")

    # One church on every Sunday, the sick Sunday struck rather than kept.
    church_title = re.compile(
        r"^(Church,|Easter Day|Holy Innocents|Candlemas|Septuagesima|Mothering|Palm Sunday|"
        r"Low Sunday|Rogation|Whitsunday|Trinity Sunday|St Peter|St Bartholomew|"
        r"The Queen's birthday|Advent Sunday|St Thomas)",
    )
    series_days = {}
    for ev, days in expansions:
        if ev["layer"] == "sunday":
            for day_key in days:
                series_days.setdefault(day_key, []).append(ev["title"])
    sunday = date(2025, 1, 5)
    while sunday <= date(2025, 12, 28):
        key = sunday.isoformat()
        explicit = [
            ev for ev in by_date.get(key, [])
            if church_title.search(ev["title"])
            and ev["status"] == "confirmed"
            and not ev.get("rrule")
        ]
        from_series = series_days.get(key, [])
        if key == "2025-01-19":
            cancelled = [ev for ev in by_date.get(key, []) if ev["layer"] == "sunday" and ev["status"] == "cancelled"]
            if from_series or explicit or len(cancelled) != 1:
                bad(f"19 Jan church should be one struck line, series={from_series} explicit={len(explicit)} cancelled={len(cancelled)}")
        elif len(explicit) + len(from_series) != 1:
            bad(f"{key} has {len(explicit)} explicit churches and {len(from_series)} from the series")
        sunday += timedelta(days=7)

    # Reckoning series must not cover a dark Saturday, and 13 Sep is its own line.
    reckoning_days = set()
    for ev, days in expansions:
        if ev["title"] == "Reckoning":
            reckoning_days.update(days)
    for dark in ("2025-03-08", "2025-03-15", "2025-03-22", "2025-03-29",
                 "2025-04-05", "2025-04-12", "2025-04-19", "2025-08-02",
                 "2025-08-09", "2025-08-16", "2025-08-23", "2025-12-27"):
        if dark in reckoning_days:
            bad(f"reckoning fires on a dark Saturday {dark}")
    if "2025-09-13" in reckoning_days:
        bad("13 Sep reckoning was not taken off the series")
    if not any(ev["date"] == "2025-09-13" and ev["title"].startswith("Reckoning") for ev in events):
        bad("13 Sep has no reckoning of its own")

    jul = by_date.get("2025-07-24", [])
    if [ev["title"] for ev in jul] != ["No play"] or any(ev["status"] != "confirmed" for ev in jul):
        bad(f"24 Jul should be only a confirmed No play, got {[ev['title'] for ev in jul]}")
    easter = by_date.get("2025-04-20", [])
    if len(easter) != 1 or not easter[0]["title"].startswith("Easter Day."):
        bad(f"Easter Day should be one line, got {[ev['title'] for ev in easter]}")
    if any(ev["layer"] == "rival_bill" for ev in by_date.get("2025-05-18", [])):
        bad("18 May has a Rose bill")
    if any(ev["layer"] == "carrier" for ev in by_date.get("2025-07-21", [])):
        bad("21 Jul has a carrier line")
    marks = [ev for ev in events if ev["layer"] == "private_mark"]
    if [ev["date"] for ev in marks] != CROSS_DATES:
        bad(f"private marks are {[ev['date'] for ev in marks]}")
    for ev in marks:
        if ev["title"] != "×" or ev.get("description") or ev.get("location") or ev.get("place_slug") or ev.get("attendees"):
            bad(f"a cross carries words: {ev['date']}")
        if not ev.get("after_the_fact"):
            bad(f"cross on {ev['date']} is not after the fact")
    carriers = sorted(ev["date"] for ev in events if ev["layer"] == "carrier")
    if carriers != CARRIERS:
        bad(f"carrier Thursdays drifted: {carriers}")
    george = by_date.get("2025-04-23", [])
    if any(ev["layer"] == "family_day" for ev in george):
        bad("23 Apr has a family line")
    if any(re.search(r"thirty|birthday|christening|xxxj", ev["title"], re.I) for ev in george):
        bad("23 Apr is labelled as a birthday")
    feb6 = " ".join(visible(ev).lower() for ev in by_date.get("2025-02-06", []))
    if "raleigh" in feb6 or "guiana" in feb6:
        bad("Raleigh is on 6 Feb")

    perfs = []
    for ev in events:
        name = perf_name(ev["title"])
        if name and ev["status"] in {"confirmed", "cancelled"}:
            perfs.append((date.fromisoformat(ev["date"]), name, ev["status"], ev["title"]))
    perfs.sort()
    for (d1, n1, _, _), (d2, n2, _, _) in zip(perfs, perfs[1:]):
        # Merge 2026-11-16: the world's one repeat (S007, G006); see build.py.
        if n1 == n2 and (d2 - d1).days <= 2 and (str(d1), str(d2)) not in {("2025-01-17", "2025-01-18"), ("2025-06-30", "2025-07-01"), ("2025-07-01", "2025-07-03"), ("2025-09-05", "2025-09-06")}:
            bad(f"same play on {d1} and {d2}: {n1}")

    plays = [ev for ev in events if ev["title"].startswith("Play: ") and ev["status"] == "confirmed"]
    iplay = sum("(I play)" in ev["title"] for ev in plays)
    ratio = iplay / len(plays) if plays else 0
    if not (0.62 <= ratio <= 0.72):
        bad(f"(I play) ratio {ratio:.3f} is outside four days in six")

    layers = Counter(ev["layer"] for ev in events)
    print(f"events {len(events)}")
    for layer, n in sorted(layers.items(), key=lambda kv: -kv[1]):
        print(f"  {layer:20} {n}")
    print(f"confirmed Play lines {len(plays)}  (I play) {iplay}  ratio {ratio:.3f}")
    print(f"rrules {sum(1 for ev in events if ev.get('rrule'))}  cancelled {sum(ev['status']=='cancelled' for ev in events)}  after the fact {sum(bool(ev.get('after_the_fact')) for ev in events)}")
    if errors:
        print(f"\n{len(errors)} problems")
        for msg in errors[:80]:
            print(" -", msg)
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
