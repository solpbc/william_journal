#!/usr/bin/env python3
"""Build William Shakespeare's 1595 almanac as calendar.json: the editor merge.

Forked from ../grok/build.py. The merge changes are marked "Merge" and listed in ../merge.md.

Dates are stored in 2025. The 2025 civil calendar matches the Julian 1595
weekdays (Wednesday 1 January, Easter Day Sunday 20 April). This script reads
world.md for slugs, section-6 ids and the section-5.3 week table. It does not
edit the world.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORLD_PATH = ROOT / "world" / "world.md"
OUT_PATH = Path(__file__).resolve().parent / "calendar.json"
# Merge: the day-by-day repertory is the Gemini build's (frozen in repertory.json),
# because the world counts performances (6 Nov is Richard II "for the sixth time").
REP = json.loads((Path(__file__).resolve().parent / "repertory.json").read_text())
# His named parts: Navarre, Egeon, Gaunt, the Chorus and the Prince (world § 5.3).
ROLES = {"LLL", "Errors", "Richard II", "Romeo and Juliet"}
STOCK = ["Shrew", "Two Gents", "Titus", "Richard III", "Knave", "Fair Em", "Hamlet", "Seven Deadly Sins", "Errors"]

ALMANAC = "2024-12-20T15:00"
OWNER = "william_shakespeare"

MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

PLAY_NORM = {
    "errors": "Errors",
    "the comedy of errors": "Errors",
    "two gents": "Two Gents",
    "shrew": "Shrew",
    "fair em": "Fair Em",
    "titus": "Titus",
    "knave": "Knave",
    "richard iii": "Richard III",
    "hamlet": "Hamlet",
    "seven deadly sins": "Seven Deadly Sins",
    "lll": "LLL",
    "richard ii": "Richard II",
    "romeo": "Romeo and Juliet",
    "romeo and juliet": "Romeo and Juliet",
}

# Title locked by the week table or by a named afternoon.
FORCED_TITLE = {
    "2025-01-06": "Errors",
    "2025-01-18": "Errors",
    "2025-02-20": "LLL",
    "2025-02-24": "LLL",
    "2025-03-03": "Two Gents",
    "2025-03-04": "LLL",
    "2025-04-21": "LLL",
    "2025-06-09": "LLL",
    "2025-07-26": "Errors",
    "2025-10-02": "Richard II",
    "2025-10-07": "Richard II",
    "2025-10-16": "Richard II",
    "2025-10-21": "Richard II",
    "2025-10-30": "Richard II",
    "2025-11-06": "Richard II",
    "2025-11-12": "Richard II",
    "2025-11-18": "Richard II",
    "2025-11-25": "Richard II",
    "2025-12-04": "Richard II",
    "2025-12-06": "Romeo and Juliet",
    # Merge 2026-11-16: the week's one *Errors* is Tue 9 Dec, "*Errors* at two in
    # Shoreditch, then ... Old Swan Stairs at five" (S112a), not Mon 8.
    "2025-12-09": "Errors",
    "2025-12-10": "Romeo and Juliet",
    "2025-12-12": "Richard II",
    "2025-12-15": "Romeo and Juliet",
    "2025-12-20": "Romeo and Juliet",
    "2025-12-22": "Errors",
    # Merge (2026-11-16): titles the world's § 6 entries name, found by the
    # Gemini thread register and checked against world.md.
    "2025-01-04": "Two Gents",   # W001 "*Two Gents* at two."
    "2025-01-17": "Errors",      # S007 "At two, *Errors*"
    "2025-01-23": "Two Gents",   # S008b "*Two Gents* plays to them."
    "2025-01-28": "Shrew",       # W009 "*The Shrew* at two."
    "2025-02-21": "Shrew",       # S019 "*The Shrew* plays without him"
    "2025-04-28": "Shrew",       # W127 "*The Shrew* at two; he is not in it"
    "2025-05-01": "LLL",         # S040 "The Theatre plays the comedy"
    "2025-05-20": "Shrew",       # W043 "Not cast in *The Shrew*"
    "2025-05-22": "Hamlet",      # W044 "played the Ghost in the old *Hamlet*"
    "2025-07-25": "LLL",         # W308 "*Love's Labour's Lost* at two"
    # Merge of the week of 8 Jun (2026-11-17): W136 "*The Shrew*, then." is
    # Saturday's play; Friday takes the comedy that was on Saturday.
    "2025-06-14": "Shrew",       # W136 "*The Shrew*, then."
    "2025-05-15": "Errors", # W130 "he walks the whole City north in forty minutes to speak Egeon at two" (found by the 11 May merge)
    "2025-09-05": "Two Gents", # S086 "On the post by the Bull, beside his own house's *Two Gentlemen*" (found by the 31 Aug merge)
    "2025-06-19": "Richard III", # S063 "The play at the Theatre was thin and he was a duke in it." Titus has no duke (found by the 15 Jun merge)
    "2025-06-13": "Two Gents",   # swapped with 14 Jun, so no title repeats
    # Merge of the week of 19 Oct (2026-11-17): two § 6 titles the calendar had
    # wrong. 17 and 22 Oct move so no title repeats within two days.
    "2025-10-18": "Two Gents",   # S099 "since *Two Gents* wants no dukes of his"
    "2025-10-20": "Shrew",       # W090 "After *The Shrew*, the tiring-house door shut."
    "2025-10-17": "Shrew",       # moved off Two Gents, which 18 Oct now is
    "2025-10-22": "Two Gents",   # moved off Shrew, which 20 Oct now is
    # the editor's sweep of § 6 play names against the calendar (2026-11-17).
    "2025-01-21": "Richard III", # W007 "After *Richard III* he puts the whole comedy into Garnish's hands"
    "2025-01-20": "Shrew",       # swapped with 21 Jan, so no title repeats
    "2025-07-01": "Errors",      # W300 "A thin *Errors*" ... "He speaks Egeon's tale"
    "2025-10-11": "Titus",       # W088 "The reckoning after *Titus* is 38s."
    "2025-10-10": "Shrew",       # swapped with 11 Oct, so no title repeats
    "2025-11-22": "Shrew",       # W097 "After *The Shrew* and a reckoning of 28s"
    "2025-11-21": "Two Gents",   # swapped with 22 Nov, so no title repeats
    "2025-09-09": "Errors",      # W080 "He is Egeon at two" (editor's casting sweep)
    "2025-09-08": "Fair Em",     # moved off Errors, which 9 Sep now is
    "2025-09-10": "Shrew",       # moved off Errors; not Fair Em, which 11 Sep is
    "2025-09-06": "Two Gents",   # W078 "*Two Gents* at two"
    "2025-04-24": "Titus",       # W126 "He plays an old Roman"
    "2025-05-26": "LLL",         # S049 "He played Navarre this afternoon"
}

# None means the ratio pass may choose.
FORCED_IPLAY = {
    # Merge (2026-11-16): casting the world's § 6 entries state, checked.
    "2025-01-01": False,  # S001 "he is not cast"
    "2025-01-10": False,  # S005 "he is not cast"
    "2025-01-13": False,  # W005 "*Titus* at the Cross Keys without him"
    "2025-01-29": True,   # W113 "William plays the Ghost"
    "2025-02-21": False,  # S019 "plays without him"
    "2025-04-28": False,  # W127 "he is not in it"
    "2025-05-09": False,  # W128 "Not cast"
    "2025-05-22": True,   # W044 "He has played the Ghost"
    "2025-06-10": False,  # S094 "Not cast."
    "2025-06-12": False,  # S058 "not cast today or tomorrow"
    "2025-06-13": False,  # S058 "not cast today or tomorrow"
    "2025-07-09": True,   # S073 "William is an old Roman"
    "2025-07-25": True,   # W308 "so is the King of Navarre"
    "2025-10-06": True,   # W087 "He plays an old Roman at two"
    "2025-11-28": False,  # S108 "plays *Fair Em* without him"
    "2025-12-09": True,   # S112a: Errors at two, then home for a clean band
    "2025-07-04": False,  # S070 "Coming home from a comedy he was not in" (found by the June merge)
    "2025-09-09": True,   # W080 "He is Egeon at two" (editor's casting sweep, 2026-11-17)
    "2025-11-05": False,  # S103a "Not cast; a book morning" (editor's casting sweep, 2026-11-17)
    "2025-07-21": True,   # W306 "He is hardly out of the Duke's gown after *Two Gents*" (found by the 20 Jul merge)
    "2025-05-13": False,  # S045 and § 7.6 "Tuesday 13 May, not cast": *Two Gents* watched from the tiring-house door (found by the 11 May merge)
    "2025-05-15": True,   # W130 "to speak Egeon at two" (found by the 11 May merge)
    "2025-06-19": True,   # S063 "he was a duke in it" (found by the 15 Jun merge)
    "2025-07-01": True,   # W300 "He speaks Egeon's tale to a yard that hears every word" (editor's sweep, 2026-11-17)
    "2025-01-23": False,  # S008b "William, not cast"
    "2025-04-24": True,   # W126 "He plays an old Roman"
    "2025-05-26": True,   # S049 "He played Navarre this afternoon"
    "2025-10-28": False,  # M041 "He is not cast today"
    "2025-01-06": True,
    "2025-01-17": True,
    "2025-01-18": False,
    "2025-02-14": False,
    "2025-02-20": True,
    "2025-02-24": True,
    "2025-03-04": True,
    "2025-04-21": True,
    "2025-05-20": False,
    "2025-07-26": True,
    "2025-08-29": False,
    "2025-10-02": True,
    "2025-10-07": True,
    "2025-10-13": False,
    "2025-10-14": False,
    "2025-10-15": False,
    "2025-10-16": False,
    "2025-10-17": False,
    "2025-10-18": False,
    "2025-10-20": False,
    "2025-10-21": False,
    "2025-11-06": True,
    "2025-11-12": True,
    "2025-11-18": True,
    "2025-11-25": True,
    "2025-11-28": False,
    "2025-12-04": True,
    "2025-12-06": True,
    "2025-12-10": True,
    "2025-12-12": True,
    "2025-12-15": True,
    "2025-12-20": True,
    "2025-12-22": True,
}

PLAY_ENTRIES = {
    "2025-02-20": ["W015"],
    "2025-04-21": ["S036"],
    "2025-07-26": ["S076"],
    "2025-10-02": ["W085"],
    "2025-12-06": ["W100"],
}

ROSE_ATTEND = {
    "2025-02-14": ["S016"],
    "2025-05-20": ["W043"],
    "2025-08-29": ["S085"],
    "2025-11-28": ["S108"],
}

CROSSES = [
    ("2025-01-05", "W002"),
    ("2025-02-28", "W018"),
    ("2025-03-22", "M009"),
    ("2025-05-22", "W044"),
    ("2025-06-08", "W048"),
    ("2025-09-14", "W336"),
    ("2025-10-29", "S101"),
]

CARRIER_DAYS = [
    "2025-01-16", "2025-02-06", "2025-02-27", "2025-03-20", "2025-04-24",
    "2025-05-15", "2025-06-05", "2025-06-26", "2025-07-17", "2025-09-11",
    "2025-10-02", "2025-10-23", "2025-11-13", "2025-12-04", "2025-12-18",
]

FULL_MOONS = [
    "2025-01-15", "2025-02-14", "2025-03-15", "2025-04-14", "2025-05-13",
    "2025-06-11", "2025-07-11", "2025-08-09", "2025-09-08", "2025-10-08",
    "2025-11-07", "2025-12-06",
]
NEW_MOONS = [
    "2025-01-30", "2025-03-01", "2025-03-30", "2025-04-29", "2025-05-29",
    "2025-06-27", "2025-07-26", "2025-08-25", "2025-09-23", "2025-10-22",
    "2025-11-21", "2025-12-20",
]

# Sundays that must not also fire the St Helen's series.
EXDATE_SUNDAYS = [
    "2025-01-19",  # abed
    "2025-02-02", "2025-02-16",
    "2025-03-30",
    "2025-04-06", "2025-04-13", "2025-04-20", "2025-04-27",
    "2025-05-25",
    "2025-06-08", "2025-06-15", "2025-06-29",
    "2025-08-03", "2025-08-10", "2025-08-17", "2025-08-24",
    "2025-09-07",
    "2025-11-30",
    "2025-12-21", "2025-12-28",
]


def D(iso: str) -> date:
    return date.fromisoformat(iso)


def iso(d: date) -> str:
    return d.isoformat()


def prev_saturday(d: date) -> date:
    delta = (d.weekday() - 5) % 7
    if delta == 0:
        delta = 7
    return d - timedelta(days=delta)


def stamp(d: date, hm: str) -> str:
    return f"{d.isoformat()}T{hm}"


def parse_world(text: str):
    def at(heading: str) -> int:
        m = re.search(rf"^{re.escape(heading)}", text, re.M)
        if not m:
            raise SystemExit(f"missing heading {heading}")
        return m.start()

    i3, i4, i5 = at("## 3. "), at("## 4. "), at("## 5. ")
    i6, i7 = at("## 6. "), at("## 7. ")
    people = set(re.findall(r"^#### `([a-z0-9_]+)`", text[i3:i4], re.M))
    places = set(re.findall(r"^#### `([a-z0-9_]+)`", text[i4:i5], re.M))
    entries = set(re.findall(r"\*\*([A-Z]\d+[a-z]?)\s·", text[i6:i7]))
    if len(people) < 60 or len(places) < 40 or len(entries) < 300:
        raise SystemExit(
            f"world parse looks short: {len(people)} people, {len(places)} places, {len(entries)} entries"
        )
    return people, places, entries


def parse_weeks(text: str):
    start = text.index("### 5.3 Week by week")
    end = text.index("**Anchor count.**", start)
    weeks = []
    for line in text[start:end].splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or not cells[0].isdigit():
            continue
        span = cells[1]
        m = re.search(
            r"(\d{1,2})\s+([A-Za-z]+)\s*[–—-]\s*[A-Za-z]+\s+(\d{1,2})\s+([A-Za-z]+)",
            span,
        )
        if not m:
            raise SystemExit(f"bad week span: {span}")
        sd, sm, ed, em = int(m.group(1)), MONTHS[m.group(2)], int(m.group(3)), MONTHS[m.group(4)]
        weeks.append({
            "n": int(cells[0]),
            "start": date(2025, sm, sd),
            "end": date(2025, em, ed),
            "playing": cells[4],
        })
    if [w["n"] for w in weeks] != list(range(1, 54)):
        raise SystemExit(f"expected weeks 1-53, got {[w['n'] for w in weeks]}")
    return weeks


def norm_play(raw: str) -> str | None:
    key = re.sub(r"\s+", " ", raw.strip().lower())
    if key in PLAY_NORM:
        return PLAY_NORM[key]
    return None


def company_titles(cell: str) -> list[str]:
    company = re.split(r"\bRose\b[^:]*:", cell, maxsplit=1)[0]
    company = company.split("**Court:")[0]
    # Bold markers sit against italics ("***LLL*"). Strip them before pairing single stars.
    company = company.replace("**", "")
    found = []
    unknown = []
    for raw in re.findall(r"\*([^*]+)\*", company):
        name = norm_play(raw)
        if name is None:
            unknown.append(raw.strip())
            continue
        if name not in found:
            found.append(name)
    return found, unknown


def rose_bills(week: dict) -> list[tuple[date, str]]:
    parts = re.split(r"\bRose\b[^:]*:", week["playing"], maxsplit=1)
    if len(parts) < 2:
        return []
    rose = parts[1]
    pat = re.compile(
        r"(?:\*\*)?(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(\d{1,2})\s+(?:\*\*)?\*([^*]+)\*(?:\s+and\s+\*([^*]+)\*)?",
        re.I,
    )
    out = []
    start, end = week["start"], week["end"]
    for m in pat.finditer(rose):
        wd, day = m.group(1), int(m.group(2))
        if wd.lower().startswith("sun"):
            continue
        title = re.sub(r"\s+", " ", m.group(3).strip())
        if m.group(4):
            title = f"{title} and {re.sub(r'\\s+', ' ', m.group(4).strip())}"
        month = start.month
        if start.month != end.month and day < start.day:
            month = end.month
        try:
            d = date(2025, month, day)
        except ValueError:
            continue
        if not (start <= d <= end) or d.weekday() == 6 or d == date(2025, 5, 18):
            continue
        out.append((d, title))
    return out


def week_of(weeks, d: date) -> dict:
    for w in weeks:
        if w["start"] <= d <= w["end"]:
            return w
    raise SystemExit(f"no week for {d}")


def title_available(title: str, d: date) -> bool:
    if title == "LLL" and d < date(2025, 2, 20):
        return False
    if title == "Richard II" and d < date(2025, 10, 2):
        return False
    if title == "Romeo and Juliet" and d < date(2025, 12, 6):
        return False
    return True


def playing_days() -> list[date]:
    days = []

    def span(a: date, b: date, skip: set[date]):
        d = a
        while d <= b:
            if d.weekday() != 6 and d not in skip:
                days.append(d)
            d += timedelta(days=1)

    span(date(2025, 1, 1), date(2025, 3, 4), set())
    span(date(2025, 4, 21), date(2025, 7, 26), {date(2025, 6, 30), date(2025, 7, 24)})
    span(date(2025, 8, 25), date(2025, 12, 22), {date(2025, 11, 17)})  # Merge 2026-11-16: 9 Dec plays (S112a)
    return days


# Merge (2026-11-16): the world plays *Errors* two days running, the fever and
# then Cowley's Egeon (S007, G006), against § 5.1's "never the same play on
# consecutive days". The story wins for this pair only.
# 1 Jul (W300) plays the *Errors* struck on 30 Jun (cal-0407, cancelled), after
# two dark days; and *Errors* plays again on 3 Jul in a thin week (the editor, 2026-11-17).
ALLOWED_REPEATS = {(date(2025, 1, 17), date(2025, 1, 18)),
                   (date(2025, 6, 30), date(2025, 7, 1)),
                   (date(2025, 7, 1), date(2025, 7, 3)),
                   (date(2025, 9, 5), date(2025, 9, 6))}  # S086's post and W078 "*Two Gents* at two" (31 Aug merge)


# Titles are frozen at the calendar of 2026-11-17 (before the § 6 sweep), as
# casting is: every fix to one day used to reshuffle unforced days, some of
# them inside accepted weeks. FORCED_TITLE still wins; a clash it causes now
# stops the build instead of moving a neighbour.
TITLES_FROZEN = json.loads((Path(__file__).resolve().parent / "titles-frozen.json").read_text())


def assign_plays(weeks) -> list[dict]:
    days = playing_days()
    days.append(date(2025, 6, 30))  # billed, then struck
    days = sorted(set(days))
    items = []
    for d in days:
        titles, _ = company_titles(week_of(weeks, d)["playing"])
        options = [t for t in titles if title_available(t, d)]
        forced = FORCED_TITLE.get(iso(d)) or TITLES_FROZEN.get(iso(d))
        r = REP.get(iso(d))
        if r and r != "Romeo and Juliet" and title_available(r, d):
            # Merge: Gemini's title first; if it must move, only old stock
            # stands in, so the new plays keep the world's counts.
            options = [r] + [s for s in STOCK if s != r]
        if forced and forced not in options:
            options = [forced] + options
        items.append({
            "date": d,
            "options": options,
            "title": forced,
            "locked": forced is not None,
            "cancel": d == date(2025, 6, 30),
        })
    last = None
    prev = None
    for it in items:
        if prev is not None and (it["date"] - prev).days > 2:
            last = None
        if it["title"] is None:
            if not it["options"]:
                raise SystemExit(f"no company title for {it['date']}")
            opts = [t for t in it["options"] if t != last] or it["options"]
            it["title"] = opts[0]
        last = it["title"]
        prev = it["date"]

    def clashes_with(idx: int, title: str) -> bool:
        if idx > 0:
            prev_it = items[idx - 1]
            if ((items[idx]["date"] - prev_it["date"]).days <= 2 and prev_it["title"] == title
                    and (prev_it["date"], items[idx]["date"]) not in ALLOWED_REPEATS):
                return True
        if idx + 1 < len(items):
            next_it = items[idx + 1]
            if ((next_it["date"] - items[idx]["date"]).days <= 2 and next_it["title"] == title
                    and (items[idx]["date"], next_it["date"]) not in ALLOWED_REPEATS):
                return True
        return False

    for _ in range(len(items)):
        changed = False
        for i, it in enumerate(items):
            if it["locked"] or not clashes_with(i, it["title"]):
                continue
            for alt in it["options"]:
                if alt != it["title"] and not clashes_with(i, alt):
                    it["title"] = alt
                    changed = True
                    break
        if not changed:
            break
    clashes = []
    for i in range(1, len(items)):
        a, b = items[i - 1], items[i]
        if ((b["date"] - a["date"]).days <= 2 and a["title"] == b["title"]
                and (a["date"], b["date"]) not in ALLOWED_REPEATS):
            clashes.append(f"{a['date']} and {b['date']} both {a['title']}")
    if clashes:
        raise SystemExit("consecutive plays:\n  " + "\n  ".join(clashes))
    return items


def house_for(d: date):
    if d <= date(2025, 3, 4):
        return "Cross Keys", "cross_keys_inn", "the Cross Keys"
    return "the Theatre", "the_theatre", "the Theatre"


def play_created(d: date, title: str) -> str:
    if title == "LLL" and date(2025, 2, 20) <= d <= date(2025, 3, 4):
        return "2025-01-30T15:00"
    if date(2025, 8, 25) <= d <= date(2025, 8, 30):
        return "2025-08-22T19:00"
    if d <= date(2025, 1, 4):
        return "2024-12-28T18:00"
    return stamp(prev_saturday(d), "18:00")


# Merge 2026-11-16: casting is frozen. Accepted weeks are written against it, and
# the ratio pass reshuffled unforced days on every fix. Explicit FORCED_IPLAY
# entries still win; frozen days come next; the spread pass only fills new days.
IPLAY_FROZEN = json.loads((Path(__file__).resolve().parent / "iplay-frozen.json").read_text())


def spread_iplay(items: list[dict]) -> None:
    """About four confirmed afternoons in six. Forced days stay forced."""
    confirmed = [it for it in items if not it["cancel"]]
    target = round(len(confirmed) * 4 / 6)
    forced_true = 0
    free = []
    for it in confirmed:
        force = FORCED_IPLAY.get(iso(it["date"]))
        if force is True:
            it["i_play"] = True
            forced_true += 1
        elif force is False:
            it["i_play"] = False
        elif iso(it["date"]) in IPLAY_FROZEN:
            it["i_play"] = IPLAY_FROZEN[iso(it["date"])]
            forced_true += it["i_play"]
        elif it["title"] in ROLES:
            it["i_play"] = True
            forced_true += 1
        else:
            it["i_play"] = False
            free.append(it)
    need = max(0, min(len(free), target - forced_true))
    if need:
        chosen = set()
        for i in range(need):
            chosen.add(min(len(free) - 1, int(round(i * len(free) / need))))
        k = 0
        while len(chosen) < need:
            if k not in chosen:
                chosen.add(k)
            k += 1
        for i, it in enumerate(free):
            it["i_play"] = i in chosen
    for it in items:
        if it["cancel"]:
            it["i_play"] = False


class Book:
    def __init__(self, people, places, entries):
        self.people = people
        self.places = places
        self.entries = entries
        self.events: list[dict] = []

    def add(
        self,
        when,
        title,
        *,
        start=None,
        end=None,
        all_day=False,
        end_date=None,
        description=None,
        location=None,
        place=None,
        organizer=OWNER,
        attendees=None,
        created,
        modified=None,
        after=False,
        status="confirmed",
        rrule=None,
        exdates=None,
        layer,
        tier,
        entries=None,
        why,
    ):
        d = when if isinstance(when, str) else iso(when)
        ev = {
            "date": d,
            "title": title,
            "created": created,
            "status": status,
            "layer": layer,
            "tier": tier,
            "entries": list(entries or []),
            "why": " ".join(why.split()),
            "organizer": organizer,
        }
        if all_day:
            ev["all_day"] = True
            if end_date:
                ev["end_date"] = end_date if isinstance(end_date, str) else iso(end_date)
        else:
            if not start or not end:
                raise SystemExit(f"timed event needs start and end: {title} {d}")
            ev["start"] = start
            ev["end"] = end
        if description:
            ev["description"] = description
        if location:
            ev["location"] = location
        if place:
            ev["place_slug"] = place
        if attendees:
            ev["attendees"] = list(attendees)
        if modified:
            ev["modified"] = modified
        if after:
            ev["after_the_fact"] = True
        if rrule:
            ev["rrule"] = rrule
        if exdates:
            ev["exdates"] = list(exdates)
        self._check_refs(ev)
        self.events.append(ev)

    def _check_refs(self, ev):
        if ev["organizer"] not in self.people:
            raise SystemExit(f"bad organizer {ev['organizer']} on {ev['title']}")
        for slug in ev.get("attendees", []):
            if slug not in self.people:
                raise SystemExit(f"bad attendee {slug} on {ev['title']}")
        if ev.get("place_slug") and ev["place_slug"] not in self.places:
            raise SystemExit(f"bad place {ev['place_slug']} on {ev['title']}")
        for eid in ev["entries"]:
            if eid not in self.entries:
                raise SystemExit(f"bad entry {eid} on {ev['date']} {ev['title']}")
        if ev["organizer"] == "the_lady_unnamed" or "the_lady_unnamed" in ev.get("attendees", []):
            raise SystemExit("the lady was given a slug")


def build_plays(book: Book, items: list[dict]):
    for it in items:
        d = it["date"]
        short, place, loc = house_for(d)
        title = f"Play: {it['title']}, {short}, 2 of the clock"
        if it["i_play"]:
            title += " (I play)"
        desc = "The old play." if it["title"] == "Hamlet" else None
        if it["cancel"]:
            book.add(
                d, title,
                start="14:00", end="16:30",
                description="Struck this morning.",
                location=loc, place=place,
                created=play_created(d, it["title"]),
                modified="2025-06-30T08:10",
                status="cancelled",
                layer="company_play", tier="T4",
                entries=[],
                why="The Monday bill, struck that morning. The world does not name the play, so this is the bill the week would have carried. No cause is written.",
            )
            continue
        book.add(
            d, title,
            start="14:00", end="16:30",
            description=desc,
            location=loc, place=place,
            created=play_created(d, it["title"]),
            layer="company_play", tier="T2" if iso(d) in PLAY_ENTRIES else "T4",
            entries=PLAY_ENTRIES.get(iso(d), []),
            why="The afternoon bill. Set at the Saturday reckoning, except the Love's Labour's Lost run (put down 30 Jan, when the sharers planned it) and the week the house reopens in August (put down the Friday he comes home).",
        )


def build_no_play(book: Book):
    book.add(
        "2025-03-05", "No play",
        all_day=True, end_date="2025-04-19",
        created=ALMANAC,
        layer="company_play", tier="T1",
        why="Lent, written as one span so the year view reads as a season. Easter Day is Sunday and is not inside the span. Easter Monday reopens the house.",
    )
    book.add(
        "2025-07-28", "No play",
        all_day=True, end_date="2025-08-23",
        created="2025-07-21T19:00",
        layer="company_play", tier="T1",
        why="The house rests while he walks home and stays. One span, not a 'No play' on every dark day. They reopen Monday 25 Aug.",
    )
    book.add(
        "2025-12-29", "No play",
        all_day=True, end_date="2025-12-31",
        created="2025-12-20T11:00",
        layer="company_play", tier="T4",
        why="Home from Richmond. The house stays dark through the last three days.",
    )
    holes = [
        ("2025-06-30", "2025-06-30T08:05", "The afternoon is empty. The bill was struck this morning."),
        ("2025-07-24", "2025-07-23T21:00", "The day reads only this. No cause is written, because he does not write one."),
        ("2025-11-17", ALMANAC, "Accession Day. The house does not play."),
        ("2025-12-23", "2025-12-20T18:00", "Dark from today. The court nights are later in the week, at Richmond."),
    ]
    for d, created, why in holes:
        book.add(
            d, "No play",
            start="14:00", end="16:30",
            created=created,
            layer="company_play", tier="T1" if d == "2025-07-24" else "T4",
            why=why,
        )


def build_rose(book: Book, weeks):
    bills = []
    for w in weeks:
        bills.extend(rose_bills(w))
    # Henslowe's Christmas numbering is a day early and does not match the weekday-first pattern.
    have = {iso(d) for d, _ in bills}
    for extra_d, extra_t in (
        (date(2025, 12, 26), "Wonder of a Woman"),
        (date(2025, 12, 27), "Barnardo"),
    ):
        if iso(extra_d) not in have:
            bills.append((extra_d, extra_t))
    bills.sort()
    seen = set()
    for d, title in bills:
        key = iso(d)
        if key in seen:
            raise SystemExit(f"two Rose bills on {key}")
        seen.add(key)
        attend = key in ROSE_ATTEND
        created_d = d - timedelta(days=1)
        book.add(
            d, f"Rose: {title}",
            start="14:00", end="16:30",
            description="To the yard." if attend else None,
            location="the Rose", place="the_rose",
            organizer="philip_henslowe",
            attendees=[OWNER] if attend else None,
            created=stamp(created_d, "18:00"),
            layer="rival_bill", tier="T1",
            entries=ROSE_ATTEND.get(key, []),
            why="He means to stand in the yard, and does. Written the night before, as an intention." if attend else "The bill, not an attendance. He reads it and does not go.",
        )
    return bills


def build_standing(book: Book):
    # Sunday habit. Feast Sundays, Stratford Sundays, the sick Sunday and Richmond are exceptions.
    book.add(
        "2025-01-05", "Church, St Helen's, morning prayer and sermon.",
        start="09:00", end="11:00",
        location="St Helen's, Bishopsgate", place="st_helens_church",
        created=ALMANAC,
        rrule="FREQ=WEEKLY;BYDAY=SU;UNTIL=20251228T090000Z",
        exdates=list(EXDATE_SUNDAYS),
        layer="sunday", tier="T1",
        why="The Sunday habit, written when he bought the almanac. Start is nine. Feast Sundays, Stratford Sundays, the Sunday he is abed, and Holy Innocents at Richmond are taken off the series and written on their own.",
    )
    book.add(
        "2025-01-19", "Church, St Helen's, morning prayer and sermon.",
        start="09:00", end="11:00",
        description="Abed with the cold.",
        location="St Helen's, Bishopsgate", place="st_helens_church",
        created=ALMANAC, modified="2025-01-19T07:30",
        status="cancelled",
        layer="sunday", tier="T5",
        why="Struck that morning. He is abed, and Mistress Ansell has the posset on the stair. The series does not also fire.",
    )

    feast_sundays = [
        ("2025-02-02", "09:30", "Candlemas. Church, St Helen's, morning prayer, sermon & communion.", "st_helens_church", "St Helen's, Bishopsgate", ["S012"], "Candlemas, and the twins are ten. The birthday is its own line."),
        ("2025-02-16", "09:00", "Septuagesima. Church, St Helen's, morning prayer and sermon.", "st_helens_church", "St Helen's, Bishopsgate", ["W013"], "Septuagesima. He writes to Anne after church."),
        ("2025-03-30", "09:30", "Mothering Sunday. Church, Holy Trinity, morning prayer and sermon.", "holy_trinity", "Holy Trinity, Stratford", ["W027"], "At Holy Trinity with his mother. His father stays home."),
        ("2025-04-13", "09:30", "Palm Sunday. Church, St Helen's, morning prayer and sermon.", "st_helens_church", "St Helen's, Bishopsgate", ["S034"], "Palm Sunday, a raw morning."),
        ("2025-04-20", "08:30", "Easter Day. Church, St Helen's, morning prayer, sermon & communion.", "st_helens_church", "St Helen's, Bishopsgate", ["S035"], "Easter Day, and nothing else on the page."),
        ("2025-04-27", "09:00", "Low Sunday. Church, St Helen's, morning prayer and sermon.", "st_helens_church", "St Helen's, Bishopsgate", ["W037"], "Low Sunday. A letter from home, four days late, is the day's other fact and is not given a line."),
        ("2025-05-25", "08:30", "Rogation Sunday. Church, St Helen's, morning prayer and sermon.", "st_helens_church", "St Helen's, Bishopsgate", ["W045"], "Rogation. The parish walks the bounds after the service."),
        ("2025-06-08", "09:30", "Whitsunday. Church, St Helen's, morning prayer, sermon & communion.", "st_helens_church", "St Helen's, Bishopsgate", ["W048"], "Whitsunday. The cross on this date is a separate mark and says nothing."),
        ("2025-06-15", "09:00", "Trinity Sunday. Church, St Helen's, morning prayer and sermon.", "st_helens_church", "St Helen's, Bishopsgate", ["W049"], "Trinity Sunday."),
        ("2025-06-29", "09:30", "St Peter. Church, St Helen's, morning prayer and sermon.", "st_helens_church", "St Helen's, Bishopsgate", ["S069"], "St Peter's day. He is at his own church. Nothing else is written."),
        ("2025-08-24", "09:00", "St Bartholomew. Church, St Helen's, morning prayer and sermon.", "st_helens_church", "St Helen's, Bishopsgate", [], "St Bartholomew falls on a Sunday. The fair is the afternoon."),
        ("2025-09-07", "09:00", "The Queen's birthday. Church, St Helen's, morning prayer and sermon.", "st_helens_church", "St Helen's, Bishopsgate", ["W079"], "Her sixty-second birthday. The bells."),
        ("2025-11-30", "09:30", "Advent Sunday and St Andrew. Church, St Helen's, morning prayer and sermon.", "st_helens_church", "St Helen's, Bishopsgate", ["S110"], "Advent Sunday, and St Andrew on the same day."),
        ("2025-12-21", "08:30", "St Thomas. Church, St Helen's, morning prayer and sermon.", "st_helens_church", "St Helen's, Bishopsgate", ["S113"], "St Thomas, the shortest day."),
        ("2025-12-28", "09:00", "Holy Innocents. Morning prayer at Richmond.", "the_feathers_richmond", "the Feathers, Richmond", ["S115c"], "The only Sunday he is not at St Helen's or Holy Trinity. The play is in the evening, before the Queen."),
    ]
    for d, start, title, place, loc, entries, why in feast_sundays:
        hh, mm = start.split(":")
        end_h = int(hh) + 2
        book.add(
            d, title,
            start=start, end=f"{end_h:02d}:{mm}",
            location=loc, place=place,
            created=ALMANAC,
            layer="feast", tier="T1",
            entries=entries, why=why,
        )

    stratford = [
        ("2025-04-06", "09:00", ["W030"], "Holy Trinity. His father stays home."),
        ("2025-08-03", "09:30", ["W065"], "Holy Trinity. A sermon on fire, and his father's aside."),
        ("2025-08-10", "10:00", ["W068"], "Holy Trinity, before dinner at the Sadlers'."),
        ("2025-08-17", "09:00", ["W072"], "Holy Trinity, the last Sunday before the road."),
    ]
    for d, start, entries, why in stratford:
        hh, mm = start.split(":")
        book.add(
            d, "Church, Holy Trinity, morning prayer and sermon.",
            start=start, end=f"{int(hh)+2:02d}:{mm}",
            location="Holy Trinity, Stratford", place="holy_trinity",
            created="2025-03-17T16:30" if d < "2025-07-01" else "2025-07-21T19:00",
            layer="sunday", tier="T3",
            entries=entries, why=why,
        )

    # Weekday feasts: the name, and evening prayer except where the brief withholds it.
    weekday_feasts = [
        ("2025-03-04", "Shrove Tuesday.", None, None, "The last day of playing, and a feast."),
        ("2025-03-05", "Ash Wednesday.", "st_helens_church", "St Helen's, Bishopsgate", "Ashes. The house is dark. The Rose is not, and that is their affair."),
        ("2025-03-25", "Lady Day. The year turns 1595.", "st_helens_church", "St Helen's, Bishopsgate", "Headings read 1595 from today. Yesterday was still 1594."),
        ("2025-04-18", "Good Friday.", "st_helens_church", "St Helen's, Bishopsgate", "One quiet hour. No rehearsal."),
        ("2025-04-23", "St George.", None, None, "St George only. No age, no family line."),
        ("2025-05-01", "May Day.", "bishopsgate", "Bishopsgate", "Hawthorn on the gate."),
        ("2025-05-29", "Ascension.", "st_helens_church", "St Helen's, Bishopsgate", "A holy day. No rehearsal."),
        ("2025-06-19", "Corpus Christi.", None, None, "The date only. No evening prayer. He remembers the Coventry plays and does not write them here."),
        ("2025-06-24", "Midsummer.", "st_helens_church", "St Helen's, Bishopsgate", "Midsummer, kept at home and at his own church."),
        ("2025-07-25", "St James.", "st_helens_church", "St Helen's, Bishopsgate", "St James. The house plays; he leaves on Monday."),
        ("2025-08-01", "Lammas.", "henley_street", "Henley Street", "Lammas at home."),
        ("2025-09-29", "Michaelmas.", "st_helens_church", "St Helen's, Bishopsgate", "Michaelmas. The rent is its own line, at noon."),
        ("2025-10-18", "St Luke.", "st_helens_church", "St Helen's, Bishopsgate", "St Luke. Earlier candles."),
        ("2025-10-28", "SS Simon and Jude.", "st_helens_church", "St Helen's, Bishopsgate", "Simon and Jude."),
        ("2025-11-01", "All Saints.", "st_helens_church", "St Helen's, Bishopsgate", "All Saints."),
        ("2025-11-11", "Martinmas.", "ansell_house", "Mistress Ansell's", "Martinmas. Winter stores come in. Romeo is finished."),
        ("2025-11-17", "Accession Day.", "whitehall_tiltyard", "Whitehall tilt-yard", "Accession Day. The tilt is its own line."),
        ("2025-12-26", "St Stephen.", "richmond_palace", "Richmond Palace", "St Stephen. The evening is the play, so there is no evening prayer."),
        ("2025-12-27", "St John.", "richmond_palace", "Richmond Palace", "St John. The evening is the play."),
    ]
    no_prayer = {"2025-06-19", "2025-12-26", "2025-12-27", "2025-12-25"}
    prayer_place = {
        "2025-08-01": ("holy_trinity", "Holy Trinity, Stratford"),
        "2025-12-26": ("richmond_palace", "Richmond Palace"),
        "2025-12-27": ("richmond_palace", "Richmond Palace"),
    }
    for d, title, place, loc, why in weekday_feasts:
        entries = ["S040"] if d == "2025-05-01" else ["S028"] if d == "2025-03-25" else ["S079"] if d == "2025-08-01" else ["S092"] if d == "2025-09-29" else ["S105"] if d == "2025-11-11" else ["S106"] if d == "2025-11-17" else ["W035"] if d == "2025-04-18" else []
        book.add(
            d, title, all_day=True,
            location=loc, place=place,
            created=ALMANAC,
            layer="feast", tier="T1",
            entries=entries, why=why,
        )
        if d in no_prayer:
            continue
        # After a play, prayer is at five; on a reckoning Saturday, after six.
        start = "18:15" if date.fromisoformat(d).weekday() == 5 else "17:00"
        if date.fromisoformat(d).weekday() == 5:
            end = "19:00"
        else:
            end = "17:45"
        # Dark days have no afternoon play, so four o'clock.
        if d < "2025-04-21" or ("2025-07-28" <= d <= "2025-08-23") or d >= "2025-12-23":
            if d != "2025-03-04":  # Shrove Tuesday is still a playing day
                start, end = "16:00", "16:45"
        p_place, p_loc = prayer_place.get(d, ("st_helens_church", "St Helen's, Bishopsgate"))
        if d == "2025-08-01":
            start, end = "16:00", "16:45"
        book.add(
            d, "Evening prayer.",
            start=start, end=end,
            location=p_loc, place=p_place,
            created=ALMANAC,
            layer="feast", tier="T1",
            why="Evening prayer on a feast day. Corpus Christi has none. The court evenings are the play.",
        )

    book.add(
        "2025-12-25", "Christmas Day. At the Feathers.",
        all_day=True,
        location="the Feathers, Richmond", place="the_feathers_richmond",
        created="2025-12-20T11:00",
        layer="feast", tier="T1",
        entries=["S114"],
        why="Christmas in a strange town. Not St Helen's. The court plays begin tomorrow.",
    )

    for d, name in (
        ("2025-01-23", "Hilary term opens."),
        ("2025-02-12", "Hilary term ends."),
        ("2025-05-07", "Easter term opens."),
        ("2025-06-02", "Easter term ends."),
        ("2025-06-20", "Trinity term opens."),
        ("2025-07-09", "Trinity term ends."),
        ("2025-10-09", "Michaelmas term opens."),
        ("2025-11-28", "Michaelmas term ends."),
    ):
        entries = ["S008a", "S008b"] if d == "2025-01-23" else ["W012"] if d == "2025-02-12" else ["S043"] if d == "2025-05-07" else ["S051"] if d == "2025-06-02" else ["S064"] if d == "2025-06-20" else ["S073"] if d == "2025-07-09" else ["S096"] if d == "2025-10-09" else ["S109"] if d == "2025-11-28" else []
        # S096 and S109 and some of these may exist; verified below by Book._check_refs.
        book.add(
            d, name, all_day=True,
            created=ALMANAC,
            layer="law_term", tier="T1",
            entries=entries,
            why="Open or close only. No place, so the book does not look as if he went. 23 Jan, when he does go, is a separate line.",
        )
    book.add(
        "2025-01-23", "Westminster Hall.",
        start="10:00", end="12:30",
        location="Westminster Hall", place="westminster_hall",
        created="2025-01-18T18:00",
        layer="law_term", tier="T1",
        entries=["S008a", "S008b"],
        why="The one law-term day he actually goes. Hilary opens, and he is in the Hall.",
    )

    for d, entries, desc, created, modified in (
        ("2025-03-25", ["S028"], None, ALMANAC, None),
        ("2025-06-24", ["W052"], None, ALMANAC, None),
        ("2025-09-29", ["S092"], None, ALMANAC, None),
        ("2025-12-22", ["W106"], "Christmas quarter, brought forward from Christmas Day.", ALMANAC, "2025-12-18T19:00"),
    ):
        book.add(
            d, "Rent, Mistress Ansell, xx s., by noon",
            start="11:15", end="12:00",
            description=desc,
            location="Mistress Ansell's", place="ansell_house",
            organizer="dorcas_ansell", attendees=[OWNER],
            created=created, modified=modified,
            layer="quarter_day", tier="T1",
            entries=entries,
            why="The quarter day, in the form the brief asks. Christmas is paid on the 22nd, moved once he knows he will be at Richmond on the day itself. The foul weather is the boat's fact, not this line's.",
        )

    book.add(
        "2025-10-06", "Firing and washing, vj d.",
        start="08:00", end="08:20",
        location="Mistress Ansell's", place="ansell_house",
        organizer="dorcas_ansell",
        created="2025-09-29T12:30",
        rrule="FREQ=WEEKLY;BYDAY=MO;UNTIL=20251222T080000Z",
        layer="money", tier="T3",
        why="Sixpence a week from Michaelmas, a real weekly charge rather than a sentence on the rent line. Mondays through 22 Dec.",
    )

    for d in FULL_MOONS:
        book.add(d, "Full moon", all_day=True, created=ALMANAC, layer="moon", tier="T1",
                 why="As the almanac prints it. No time.")
    for d in NEW_MOONS:
        book.add(d, "New moon", all_day=True, created=ALMANAC, layer="moon", tier="T1",
                 why="As the almanac prints it. No time.")

    book.add(
        "2025-01-04", "Reckoning",
        start="16:45", end="18:00",
        location="the Cross Keys", place="cross_keys_inn",
        organizer="john_heminges", attendees=[OWNER],
        created=ALMANAC,
        rrule="FREQ=WEEKLY;BYDAY=SA;UNTIL=20250301T164500Z",
        layer="company_business", tier="T3",
        why="Saturday reckoning at the Cross Keys, from the first playing Saturday through 1 Mar. Lent Saturdays are simply not in the series.",
    )
    book.add(
        "2025-04-26", "Reckoning",
        start="16:45", end="18:00",
        location="the Theatre", place="the_theatre",
        organizer="john_heminges", attendees=[OWNER],
        created="2025-04-19T18:00",
        rrule="FREQ=WEEKLY;BYDAY=SA;UNTIL=20251220T164500Z",
        exdates=["2025-08-02", "2025-08-09", "2025-08-16", "2025-08-23", "2025-09-13"],
        layer="company_business", tier="T3",
        why="Saturday reckoning at the Theatre. August's dark Saturdays are exceptions inside the span. 13 Sep is taken off because that reckoning is the Mayor's letter and is written on its own. No reckoning at court.",
    )

    for d in CARRIER_DAYS:
        entries = ["W121"] if d == "2025-03-20" else ["W114"] if d == "2025-02-06" else ["W130"] if d == "2025-05-15" else ["S066"] if d == "2025-06-26" else ["W105"] if d == "2025-12-18" else ["W334"] if d == "2025-09-11" else []
        book.add(
            d, "Carrier in at the Bell",
            start="11:30", end="13:00",
            location="the Bell, Carter Lane", place="the_bell_carter_lane",
            organizer="thomas_hobbins", attendees=[OWNER],
            created=ALMANAC,
            layer="carrier", tier="T3",
            entries=entries,
            why="One of the fifteen Thursdays. The unscheduled Monday 21 Jul is not here: he does not know it is coming. The gaps are uneven, so this is not a rule.",
        )


def build_rehearsals(book: Book):
    """Tuesday and Thursday mornings, plus the crowded weeks before a new play or a reopening."""
    skip = {
        date(2025, 1, 28),  # parts out occupies the morning
        date(2025, 5, 29),
        date(2025, 7, 10),
        date(2025, 7, 24),
        date(2025, 10, 14),
        date(2025, 11, 13),
        date(2025, 12, 16),
    }
    planned: dict[date, dict] = {}

    def put(d: date, title, place, loc, created, entries, why, start="09:00", end="11:00"):
        if d.weekday() == 6 or d in skip:
            return
        planned[d] = dict(title=title, place=place, loc=loc, created=created, entries=entries, why=why, start=start, end=end)

    def standing(a: date, b: date, place, loc):
        d = a
        while d <= b:
            if d.weekday() in (1, 3):
                put(
                    d, "Rehearsal, 9", place, loc,
                    stamp(prev_saturday(d), "18:00"), [],
                    "A rehearsal morning, two days a week while the house is up.",
                )
            d += timedelta(days=1)

    standing(date(2025, 1, 2), date(2025, 3, 4), "cross_keys_inn", "the Cross Keys")
    standing(date(2025, 4, 22), date(2025, 7, 22), "the_theatre", "the Theatre")
    standing(date(2025, 8, 28), date(2025, 12, 18), "the_theatre", "the Theatre")

    # Reopening week, known from Shrovetide.
    for d in (date(2025, 4, 11), date(2025, 4, 12)):
        put(d, "Rehearsal at the Theatre" if d.day == 11 else "Rehearsal, 9",
            "the_theatre", "the Theatre", "2025-03-04T21:00",
            ["S033"] if d.day == 11 else [],
            "Rehearsals resume on the 11th. Written down on Shrove night, when they know the dark weeks have an end.")
    d = date(2025, 4, 14)
    while d <= date(2025, 4, 19):
        put(d, "Rehearsal, 9", "the_theatre", "the Theatre", "2025-04-12T18:00", [],
            "Every morning in the week before the house reopens.")
        d += timedelta(days=1)

    for d, title, entries in (
        (date(2025, 2, 17), "Rehearsal, 9. LLL.", []),
        (date(2025, 2, 18), "Rehearsal, 9. LLL.", ["W014"]),
        (date(2025, 2, 19), "Rehearsal, 9. LLL.", []),
    ):
        put(d, title, "cross_keys_inn", "the Cross Keys", "2025-01-30T15:00", entries,
            "Daily, the week the new comedy opens. Put on the book with the run, on 30 Jan.")

    put(date(2025, 8, 27), "Rehearsal, 9. Richard.", "the_theatre", "the Theatre",
        "2025-08-22T19:30", ["W076"],
        "The first Richard rehearsal, the Wednesday after he is home and the parts are ready.",
        )
    put(date(2025, 9, 26), "Dress rehearsal, Richard.", "the_theatre", "the Theatre",
        "2025-09-20T18:00", ["W084"],
        "Dress. The plot is on its peg.", start="08:30", end="12:30")
    for d in (date(2025, 9, 29), date(2025, 9, 30), date(2025, 10, 1)):
        put(d, "Rehearsal, 9. Richard.", "the_theatre", "the Theatre",
            stamp(prev_saturday(d), "18:00"), [],
            "The week Richard first plays.")

    for n, d in enumerate(range(1, 6)):
        day = date(2025, 12, d)
        title = "Dress rehearsal, Romeo." if d == 3 else "Rehearsal, 9. Romeo."
        entries = ["W099"] if d == 3 else []
        put(day, title, "the_theatre", "the Theatre", "2025-11-29T18:00", entries,
            "Daily, the week Romeo opens. Wednesday is the dress.")

    put(date(2025, 5, 15), "Rehearsal, 9", "the_theatre", "the Theatre",
        stamp(prev_saturday(date(2025, 5, 15)), "18:00"), [],
        "Cut short. Field's shop, then the carrier.", start="09:00", end="10:00")

    # Good Friday (the editor, 2026-11-17, from the 13 Apr merge): the reopening week's
    # daily rehearsal is struck on the 18th. cal-0223 says "One quiet hour. No
    # rehearsal.", and W035 has church in the morning. Struck, not removed, so
    # every later id stays where it is.
    struck = {date(2025, 4, 18): ("2025-04-17T18:00",
              "Struck for Good Friday. One quiet hour, and church in the morning.")}
    for d, spec in sorted(planned.items()):
        extra = {}
        if d in struck:
            extra = dict(status="cancelled", modified=struck[d][0])
            spec = dict(spec, why=struck[d][1])
        book.add(
            d, spec["title"],
            start=spec["start"], end=spec["end"],
            location=spec["loc"], place=spec["place"],
            created=spec["created"],
            layer="rehearsal", tier="T4",
            entries=spec["entries"], why=spec["why"],
            **extra,
        )


def build_life(book: Book, play_items: list[dict]):
    # --- the book, the crosses, the private marks ---
    book.add(
        "2025-01-01", "The year's book, opened.",
        start="07:50", end="08:20",
        description="Still the year 1594. Of the Queen, for two plays at Greenwich, xx li., not yet had. The coffer, £24 10s.",
        location="Mistress Ansell's", place="ansell_house",
        created="2025-01-01T07:40",
        layer="money", tier="T1", entries=["S001"],
        why="Written as he opens the book, that morning. The heading is still 1594 until Lady Day.",
    )
    book.add(
        "2025-12-31", "The year's book, closed.",
        start="20:30", end="21:15",
        description="£33 10s. The court money is not counted as received.",
        location="Mistress Ansell's", place="ansell_house",
        created="2025-12-31T20:15",
        layer="money", tier="T1", entries=["S116"],
        why="Written as he casts the sum, a quarter-hour before he shuts the book. The figure is not planted in January.",
    )
    for d, eid in CROSSES:
        book.add(
            d, "×",
            all_day=True,
            created=f"{d}T21:40",
            after=True,
            layer="private_mark", tier="T3",
            entries=[eid],
            why="The only mark. No name, no place, no account. Written that night.",
        )

    # --- January ---
    book.add(
        "2025-01-04", "The Prince of Purpoole rides past.",
        start="11:00", end="11:30",
        location="Bishopsgate", place="bishopsgate",
        created="2025-01-04T18:30", after=True,
        layer="other", tier="T1", entries=["W001"],
        why="He did not have it in the book. He writes it after they have gone by. He does not go to the dinner.",
    )
    book.add(
        "2025-01-06", "Twelfth Day.",
        all_day=True, created=ALMANAC,
        layer="feast", tier="T1",
        why="Twelfth Day, the almanac's name for it. The play is its own line. The Admiral's Men are at court, so there is no Rose bill.",
    )
    book.add(
        "2025-01-06", "The bean-cake.",
        start="18:30", end="21:30",
        location="the Burbages', Holywell", place="burbage_house_holywell",
        organizer="james_burbage", attendees=[OWNER, "richard_burbage", "cuthbert_burbage"],
        created="2025-01-04T19:00",
        layer="social", tier="T3", entries=["W003"],
        why="Twelfth Night at the Burbages'. James asks him.",
    )
    book.add(
        "2025-01-21", "The book to Garnish.",
        start="16:45", end="17:30",
        location="the Cross Keys", place="cross_keys_inn",
        attendees=["abel_garnish"],
        created="2025-01-20T21:00",
        layer="print", tier="T5", entries=["W007"],
        why="The last line is that afternoon. He carries the book over.",
    )
    book.add(
        "2025-01-24", "Tilney, to license the comedy. vij s.",
        start="10:00", end="12:00",
        location="St John's, Clerkenwell", place="st_johns_clerkenwell",
        organizer="edmund_tilney", attendees=[OWNER],
        created="2025-01-21T18:00",
        layer="company_business", tier="T2", entries=["W008"],
        why="The license, once the book is out of his hands.",
    )
    book.add(
        "2025-01-26", "Supper at the Burbages'.",
        start="18:00", end="21:00",
        location="the Burbages', Holywell", place="burbage_house_holywell",
        organizer="james_burbage", attendees=[OWNER, "richard_burbage"],
        created="2025-01-24T18:00",
        layer="social", tier="T3", entries=["S009"],
        why="Sunday supper. A wedding at Greenwich is news the same day and is not a line of his.",
    )
    book.add(
        "2025-01-28", "Parts out. The first reading.",
        start="09:00", end="12:00",
        location="the Burbages', Holywell", place="burbage_house_holywell",
        organizer="john_heminges", attendees=[OWNER, "richard_burbage", "will_kemp", "augustine_phillips"],
        created="2025-01-24T19:00",
        layer="rehearsal", tier="T5", entries=["W009"],
        why="Parts given out. It takes the rehearsal morning.",
    )
    book.add(
        "2025-01-30", "Sharers: the run to Shrovetide.",
        start="17:00", end="18:30",
        location="the Cross Keys", place="cross_keys_inn",
        organizer="john_heminges",
        attendees=[OWNER, "richard_burbage", "will_kemp", "thomas_pope", "george_bryan", "augustine_phillips"],
        created="2025-01-25T18:00",
        layer="company_business", tier="T3", entries=["S010"],
        why="They put Love's Labour's Lost on the book through Shrove Tuesday. The afternoons themselves are dated from today.",
    )

    # --- February ---
    book.add(
        "2025-02-01", "The Prince's barges.",
        start="11:15", end="12:15",
        location="Tower Hill", place="tower_hill",
        created="2025-01-31T21:00",
        layer="other", tier="T1", entries=["S011"],
        why="His only Tower Hill of the year: the Prince's barges on the tide.",
    )
    book.add(
        "2025-02-02", "Twins' day",
        start="15:00", end="16:00",
        description="A groat each, to be spent foolishly. The letter goes down on Thursday.",
        location="Mistress Ansell's", place="ansell_house",
        created=ALMANAC,
        layer="family_day", tier="T3", entries=["S012"],
        why="The twins are ten. He is in London. Candlemas is the church line; this is theirs.",
    )
    book.add(
        "2025-02-07", "Sonnets, for private friends.",
        start="20:00", end="22:00",
        location="Mistress Ansell's", place="ansell_house",
        created="2025-02-05T21:00",
        layer="social", tier="T3", entries=["S118"],
        why="An evening for private friends. No addressee is written, because there is not one.",
    )
    book.add(
        "2025-02-10", "A paper for the porter's lodge.",
        start="10:40", end="11:10",
        location="the porter's lodge, Southampton House", place="southampton_house",
        created="2025-02-09T20:00",
        layer="social", tier="T3", entries=["W115"],
        why="He leaves a paper and gets no further than the lodge. He does not see the earl, so the earl is not on the line.",
    )
    book.add(
        "2025-02-25", "A rotten post, on the north side.",
        start="11:15", end="12:00",
        location="the Theatre", place="the_theatre",
        organizer="james_burbage", attendees=[OWNER, "cuthbert_burbage"],
        created="2025-02-24T18:00",
        layer="company_business", tier="T5", entries=["G013"],
        why="James takes him round after rehearsal and puts a knife into the post. Not a play, and not a lease.",
    )

    # --- March, and the ride ---
    book.add(
        "2025-03-02", "Supper with Nashe.",
        start="18:00", end="21:00",
        location="the Bull, Bishopsgate", place="bull_inn",
        organizer="thomas_nashe", attendees=[OWNER],
        created="2025-02-28T19:00",
        layer="social", tier="T3", entries=["S021"],
        why="Shrove Sunday. Nashe asks him to the Bull.",
    )
    book.add(
        "2025-03-04", "My lord's birthday",
        all_day=True, created=ALMANAC,
        layer="company_business", tier="T1", entries=["S022"],
        why="Hunsdon's birthday, a date. No age added.",
    )
    book.add(
        "2025-03-11", "Richard, xxi.",
        all_day=True, created=ALMANAC,
        layer="family_day", tier="T3", entries=["W020"],
        why="Richard is twenty-one. William is in London. A call from Gilbert that evening is not arranged, and is not entered.",
    )
    book.add(
        "2025-03-15", "The warrant. The Queen's twenty pounds.",
        start="11:30", end="13:30",
        location="the Burbages', Holywell", place="burbage_house_holywell",
        organizer="john_heminges",
        attendees=[OWNER, "will_kemp", "richard_burbage", "augustine_phillips", "thomas_pope", "george_bryan"],
        created="2025-03-13T16:00",
        layer="money", tier="T1", entries=["S027"],
        why="Heminges puts it on the book. The three named men fetch the coin; the sharers split it at the table. This Saturday is in Lent, so it is not the weekly reckoning.",
    )
    book.add(
        "2025-03-17", "Gifts, and a horse at the Bull.",
        start="11:00", end="15:00",
        location="the Bull, Bishopsgate", place="bull_inn",
        created="2025-03-16T20:00",
        layer="travel", tier="T5", entries=["W021"],
        why="The horse for the Lent ride is bespoken today. The road itself is entered this afternoon, once the bargain is made.",
    )
    book.add(
        "2025-03-19", "Holinshed, from Field.",
        start="10:30", end="11:30",
        location="Field's printing house", place="fields_printing_house",
        organizer="richard_field", attendees=[OWNER],
        created="2025-03-17T16:30",
        layer="print", tier="T3", entries=["W022"],
        why="He fetches the second volume before he rides. A visit, not a call.",
    )

    lent_created, lent_mod = "2025-03-17T16:30", "2025-03-20T12:30"
    legs = [
        ("2025-03-26", "07:00", "08:00", "Load at the Bull.", "bull_inn", "the Bull, Bishopsgate", ["S030a"]),
        ("2025-03-26", "11:00", "12:00", "Bait at Uxbridge.", "uxbridge", "Uxbridge", ["S030a"]),
        ("2025-03-26", "18:00", "21:00", "Night at High Wycombe.", "high_wycombe", "High Wycombe", ["S030a"]),
        ("2025-03-27", "07:00", "08:00", "Out from High Wycombe.", "high_wycombe", "High Wycombe", ["W025"]),
        ("2025-03-27", "17:30", "18:30", "Oxford at dusk.", "oxford", "Oxford", ["W025"]),
        ("2025-03-27", "19:00", "21:00", "Night at Woodstock.", "woodstock", "Woodstock", ["S030b", "W025"]),
        ("2025-03-28", "07:30", "08:15", "Out from Woodstock.", "woodstock", "Woodstock", ["S030c"]),
        ("2025-03-28", "12:00", "13:00", "Bait at Shipston.", "shipston_on_stour", "Shipston-on-Stour", ["S030c"]),
        ("2025-03-28", "17:00", "17:30", "Clopton Bridge at dusk.", "clopton_bridge", "Clopton Bridge", ["W026"]),
        ("2025-03-28", "18:00", "21:00", "Henley Street.", "henley_street", "Henley Street", ["W026", "S030c"]),
    ]
    for d, start, end, title, place, loc, entries in legs:
        book.add(
            d, title, start=start, end=end,
            location=loc, place=place,
            created=lent_created, modified=lent_mod,
            layer="travel", tier="T3", entries=entries,
            why="The Lent ride, load and bait and night. Entered on 17 Mar when the horse was bespoken, and the day of arrival sent ahead to Anne on the 20th.",
        )

    # --- Stratford, and back ---
    book.add(
        "2025-04-03", "Market.",
        start="11:00", end="13:00",
        location="the High Cross", place="high_cross_market",
        attendees=["anne_shakespeare", "susanna_shakespeare", "hamnet_shakespeare", "judith_shakespeare"],
        created="2025-03-20T12:30",
        layer="family_day", tier="T3", entries=["W028"],
        why="Thursday market, with Anne and the twins. An ordinary day. He is home.",
    )
    book.add(
        "2025-04-05", "Shottery, with Anne.",
        start="14:30", end="17:30",
        location="Hewlands, Shottery", place="hewlands_shottery",
        attendees=["anne_shakespeare"],
        created="2025-04-04T20:00",
        layer="family_day", tier="T3", entries=["W029"],
        why="The afternoon they walk to her old house. Written the night before.",
    )
    book.add(
        "2025-04-06", "Hamnet's wheel, at the bench.",
        start="16:00", end="17:30",
        location="Henley Street", place="henley_street",
        created="2025-04-06T21:10", after=True,
        layer="family_day", tier="T5", entries=["G026"],
        why="An ordinary afternoon, mending a toy. Written after. The boy is well.",
    )
    book.add(
        "2025-04-07", "The evening before the road.",
        start="19:00", end="21:00",
        location="Henley Street", place="henley_street",
        attendees=["anne_shakespeare"],
        created="2025-04-06T12:00",
        layer="family_day", tier="T3", entries=["W031"],
        why="The last night. He rides in the morning.",
    )
    back = [
        ("2025-04-08", "06:00", "07:00", "Load at Henley Street.", "henley_street", "Henley Street", ["W032a"]),
        ("2025-04-08", "12:00", "13:00", "Bait at Shipston.", "shipston_on_stour", "Shipston-on-Stour", ["W032a"]),
        ("2025-04-08", "18:30", "21:00", "Night at Woodstock.", "woodstock", "Woodstock", ["W032a"]),
        ("2025-04-09", "07:30", "08:15", "Out from Woodstock.", "woodstock", "Woodstock", ["W032b"]),
        ("2025-04-09", "11:30", "12:30", "Bait at Oxford.", "oxford", "Oxford", ["W032b"]),
        ("2025-04-09", "18:00", "21:00", "Night at the Catherine Wheel.", "high_wycombe", "the Catherine Wheel, High Wycombe", ["W032b"]),
        ("2025-04-10", "07:00", "08:00", "Out from High Wycombe.", "high_wycombe", "High Wycombe", ["W032c"]),
        ("2025-04-10", "11:00", "12:00", "Bait at Uxbridge.", "uxbridge", "Uxbridge", ["W032c"]),
        ("2025-04-10", "15:00", "16:00", "The Bull, and home.", "bull_inn", "the Bull, Bishopsgate", ["W032c"]),
    ]
    for d, start, end, title, place, loc, entries in back:
        book.add(
            d, title, start=start, end=end, location=loc, place=place,
            created=lent_created, modified=lent_mod,
            layer="travel", tier="T3", entries=entries,
            why="The ride back, the same horse. Night of the 9th is the Catherine Wheel at High Wycombe. Home on the 10th, the coffer at £19 6s.",
        )
    book.add(
        "2025-04-15", "Joan, xxvj.",
        all_day=True, created=ALMANAC,
        layer="family_day", tier="T3",
        why="Joan's day. He is in London. No visit is implied.",
    )
    book.add(
        "2025-04-15", "Daniel's Civil Wars, ij s.",
        start="11:00", end="11:30",
        location="Paul's Churchyard", place="pauls_churchyard",
        created="2025-04-14T21:00",
        layer="print", tier="T5", entries=["W033"],
        why="He buys the book he has been reading standing up. Not a birthday errand.",
    )
    book.add(
        "2025-04-26", "my christening day",
        all_day=True, created=ALMANAC,
        layer="family_day", tier="T3",
        why="The day the calendar keeps. St George's Day, three days earlier, is not this.",
    )

    # --- May ---
    book.add(
        "2025-05-03", "Edmund, xv.",
        all_day=True, created=ALMANAC,
        layer="family_day", tier="T3", entries=["W038"],
        why="Edmund is fifteen. A letter, not a journey.",
    )
    book.add(
        "2025-05-04", "Dinner at the Fields'.",
        start="12:00", end="14:30",
        location="Field's printing house", place="fields_printing_house",
        organizer="richard_field", attendees=[OWNER, "jacqueline_field"],
        created="2025-05-02T19:00",
        layer="social", tier="T3", entries=["W039"],
        why="Sunday dinner, as the year tells it.",
    )
    book.add(
        "2025-05-15", "Plutarch, still wet.",
        start="10:15", end="11:15",
        location="Field's printing house", place="fields_printing_house",
        organizer="richard_field", attendees=[OWNER],
        created="2025-05-14T18:00",
        layer="print", tier="T3", entries=["S046"],
        why="The sheets are on the line. He is back for the afternoon play. The carrier is the next hour.",
    )
    book.add(
        "2025-05-18", "Supper with Nashe.",
        start="17:30", end="20:30",
        location="the Split Hazel", place="split_hazel",
        organizer="thomas_nashe", attendees=[OWNER],
        created="2025-05-16T19:00",
        layer="social", tier="T3", entries=["G038"],
        why="Sunday supper. The Rose's 18 May is blank, and nothing is written to fill Henslowe's slip.",
    )
    book.add(
        "2025-05-26", "Susanna, xij.",
        all_day=True, created=ALMANAC,
        layer="family_day", tier="T3", entries=["S049"],
        why="Susanna is twelve. A letter and a thimble, sent on. He does not ride.",
    )

    # --- June and July, in the radius ---
    book.add(
        "2025-06-02", "Sharers: Whitsun to Midsummer.",
        start="11:00", end="12:30",
        location="the Theatre", place="the_theatre",
        organizer="john_heminges",
        attendees=[OWNER, "richard_burbage", "will_kemp", "augustine_phillips", "thomas_pope"],
        created="2025-05-31T18:00",
        layer="company_business", tier="T3", entries=["S051"],
        why="They map the next month. Easter term ends the same day, on its own line.",
    )
    book.add(
        "2025-06-08", "Dinner at the Fields'.",
        start="12:30", end="14:30",
        location="Field's printing house", place="fields_printing_house",
        organizer="richard_field", attendees=[OWNER, "jacqueline_field"],
        created="2025-06-05T18:00",
        layer="social", tier="T3", entries=["W135"],
        why="He was asked to come Sunday. The asking was a call, and the call is not entered. Last time west of Cheapside until July.",
    )
    book.add(
        "2025-06-23", "Bonfires in the street.",
        start="21:00", end="22:30",
        location="Bishopsgate", place="bishopsgate",
        created="2025-06-21T18:00",
        layer="feast", tier="T5", entries=["S065a"],
        why="Midsummer Eve, on his own street. He does not follow any crowd.",
    )
    book.add(
        "2025-06-24", "Birch and fennel at the door.",
        start="05:00", end="05:30",
        location="Mistress Ansell's", place="ansell_house",
        created="2025-06-23T21:30",
        layer="feast", tier="T5", entries=["S065b"],
        why="Midsummer morning. He goes no further than his own door.",
    )
    book.add(
        "2025-06-30", "Richard, read to the fellows.",
        start="10:00", end="12:30",
        location="the Burbages', Holywell", place="burbage_house_holywell",
        organizer="john_heminges", attendees=[OWNER, "richard_burbage", "will_kemp", "augustine_phillips", "thomas_pope", "george_bryan"],
        created="2025-06-30T08:20",
        layer="company_business", tier="T2", entries=["W053"],
        why="No play, so the morning is the reading. The afternoon bill is struck. Nothing here names a cause.",
    )
    book.add(
        "2025-07-07", "Sharers: play on, or rest the house?",
        start="17:00", end="18:30",
        location="the Theatre", place="the_theatre",
        organizer="john_heminges",
        attendees=[OWNER, "richard_burbage", "will_kemp", "augustine_phillips", "thomas_pope", "george_bryan"],
        created="2025-07-05T18:00",
        layer="company_business", tier="T2", entries=["S072"],
        why="The question, in Heminges's words as the calendar should hear them. They play on, then rest in August. No travelling season is put on the book, not even as struck.",
    )
    book.add(
        "2025-07-07", "Burbage, xxvij.",
        all_day=True, created=ALMANAC,
        layer="company_business", tier="T3", entries=["W055"],
        why="Burbage's day.",
    )
    book.add(
        "2025-07-07", "Supper for Burbage.",
        start="19:00", end="21:30",
        location="the Jackdaw", place="the_jackdaw",
        attendees=["richard_burbage", "will_kemp", "john_heminges"],
        created="2025-07-05T18:00",
        layer="social", tier="T3", entries=["W055"],
        why="The supper after the sharers' question.",
    )
    book.add(
        "2025-07-10", "Tilney. Leave out the deposing.",
        start="10:00", end="12:00",
        location="St John's, Clerkenwell", place="st_johns_clerkenwell",
        organizer="edmund_tilney", attendees=[OWNER],
        created="2025-07-08T19:00",
        layer="company_business", tier="T2", entries=["W056"],
        why="The license, with the cut. It takes the rehearsal morning. The phrase is the one he carries home.",
    )
    book.add(
        "2025-07-13", "Supper with Nashe.",
        start="19:00", end="21:30",
        location="the Bull, Bishopsgate", place="bull_inn",
        organizer="thomas_nashe", attendees=[OWNER],
        created="2025-07-11T19:00",
        layer="social", tier="T3", entries=["M022"],
        why="Sunday supper at the Bull.",
    )
    book.add(
        "2025-07-19", "The Swan, from the water.",
        start="17:30", end="18:30",
        location="the river, off the Swan", place="old_swan_stairs",
        attendees=["davy_gannet"],
        created="2025-07-18T20:00",
        layer="travel", tier="T5", entries=["W059"],
        why="His first crossing since May, the day the river is open to him again. He looks, from Davy's wherry. He does not land at the Swan.",
    )

    # (Merge: Grok's five habit dinners at the Fields' are dropped; 21 Dec, W418, replaces them.)

    # --- the walk, Stratford, the packhorses ---
    book.add(
        "2025-07-27", "Packing for the road.",
        start="20:00", end="21:30",
        description="£20 8s under the locks. £6 in the belt.",
        location="Mistress Ansell's", place="ansell_house",
        created="2025-07-21T19:00", modified="2025-07-27T18:00",
        layer="travel", tier="T5", entries=["W060"],
        why="He decided on the 21st, when Anne's letter came. He packs on Sunday. The road was rewritten that night.",
    )
    walk_created, walk_mod = "2025-07-21T19:00", "2025-07-27T21:00"
    walk = [
        ("2025-07-28", "05:00", "06:00", "Out, on foot.", "ansell_house", "Mistress Ansell's", ["W061"]),
        ("2025-07-28", "11:00", "12:00", "Bait at Uxbridge.", "uxbridge", "Uxbridge", ["W061"]),
        ("2025-07-28", "18:30", "21:00", "Night at Chalfont. A barn loft.", "chalfont_st_giles", "Chalfont St Giles", ["W061"]),
        ("2025-07-29", "06:00", "18:30", "On to Grendon Underwood.", "grendon_underwood", "Grendon Underwood", ["W062"]),
        ("2025-07-30", "05:30", "17:30", "On to Banbury.", "banbury", "Banbury", ["W063"]),
        ("2025-07-31", "06:00", "16:30", "On, the last day.", "banbury", "the road out of Banbury", ["W064"]),
        ("2025-07-31", "17:00", "17:30", "Clopton Bridge at five.", "clopton_bridge", "Clopton Bridge", ["W064"]),
        ("2025-07-31", "17:45", "21:00", "Henley Street.", "henley_street", "Henley Street", ["W064"]),
    ]
    for d, start, end, title, place, loc, entries in walk:
        book.add(
            d, title, start=start, end=end,
            location=loc, place=place,
            created=walk_created, modified=walk_mod,
            layer="travel", tier="T3", entries=entries,
            why="The summer walk, on foot. Entered when he decided, and touched again when he packed. No market on the day he arrives: it is five o'clock.",
        )
    book.add(
        "2025-08-04", "The household list.",
        start="08:00", end="10:00",
        location="Henley Street", place="henley_street",
        attendees=["anne_shakespeare"],
        created="2025-08-03T21:00",
        layer="family_day", tier="T5", entries=["G058"],
        why="Anne sets him a list before he opens the play. Ordinary work of the house.",
    )
    book.add(
        "2025-08-07", "Market.",
        start="09:30", end="12:00",
        location="the High Cross", place="high_cross_market",
        created="2025-08-06T18:00",
        layer="family_day", tier="T3", entries=["W066", "G059"],
        why="Thursday market. A loan is decided at the stall that morning; it was not written ahead, so it has no line of its own.",
    )
    book.add(
        "2025-08-10", "Dinner at the Sadlers'.",
        start="12:00", end="15:00",
        location="the Sadlers'",
        organizer="hamnet_sadler", attendees=[OWNER, "judith_sadler", "anne_shakespeare"],
        created="2025-08-08T19:00",
        layer="social", tier="T3", entries=["W068"],
        why="Sunday dinner. There is no house slug for the Sadlers, so the line has a name and no place-slug.",
    )
    book.add(
        "2025-08-16", "The house by the chapel, with Anne.",
        start="16:30", end="18:00",
        location="the house by the chapel", place="new_place",
        attendees=["anne_shakespeare"],
        created="2025-08-16T09:00",
        layer="family_day", tier="T3", entries=["W071"],
        why="A look, not a purchase. No price, no inquiry. Written that morning.",
    )
    book.add(
        "2025-08-17", "Supper, before the road.",
        start="18:00", end="20:30",
        location="Henley Street", place="henley_street",
        attendees=["anne_shakespeare", "edmund_shakespeare"],
        created="2025-08-16T12:00",
        layer="family_day", tier="T3", entries=["W072"],
        why="The night before the packhorses. Edmund asks about London and is answered.",
    )

    horse_created = "2025-08-07T11:30"  # bespoken at the market, not a regular Bell Thursday
    horses = [
        ("2025-08-18", "06:00", "18:00", "Night at Chipping Norton. The spare nag.", "chipping_norton", "Chipping Norton", ["W073a"]),
        ("2025-08-19", "06:00", "18:30", "Night at Oxford.", "oxford", "Oxford", ["W073b"]),
        ("2025-08-20", "05:30", "19:00", "Night at Beaconsfield.", "beaconsfield", "Beaconsfield", ["W073c"]),
        ("2025-08-21", "06:00", "17:30", "Uxbridge, and on.", "uxbridge", "Uxbridge", ["W073d"]),
        ("2025-08-21", "18:15", "20:30", "The Bell. Not home yet.", "the_bell_carter_lane", "the Bell, Carter Lane", ["W074", "W073d"]),
        ("2025-08-22", "08:00", "09:00", "Home. Mistress Ansell at the stair.", "ansell_house", "Mistress Ansell's", ["W075"]),
    ]
    for d, start, end, title, place, loc, entries in horses:
        book.add(
            d, title, start=start, end=end, location=loc, place=place,
            created=horse_created,
            layer="travel", tier="T3", entries=entries,
            why="Back with Hobbins's packhorses, bespoken at Stratford market on the 7th, not on a carrier Thursday. Thursday night is the Bell. Friday morning is home, and the Richard parts are ready.",
        )
    book.add(
        "2025-08-24", "Bartholomew Fair.",
        start="13:00", end="16:30",
        location="Smithfield", place="smithfield",
        attendees=["will_kemp", "thomas_pope"],
        created="2025-08-22T19:00",
        layer="social", tier="T1", entries=["S082"],
        why="The fair, the afternoon of St Bartholomew. Kemp and Pope. Church is the morning.",
    )

    # --- September to November ---
    book.add(
        "2025-09-13", "Reckoning. The Mayor's letter.",
        start="17:00", end="18:30",
        location="the Theatre", place="the_theatre",
        organizer="john_heminges",
        attendees=[OWNER, "richard_burbage", "cuthbert_burbage", "will_kemp", "augustine_phillips", "thomas_pope"],
        created="2025-09-13T12:30",
        layer="company_business", tier="T2", entries=["S088"],
        why="This Saturday's reckoning is taken off the weekly series. The news arrives at noon; the sharers weigh it after the play. No order follows, and none is written.",
    )
    book.add(
        "2025-09-18", "At Paul's.",
        start="12:15", end="12:45",
        location="Paul's Churchyard", place="pauls_churchyard",
        attendees=["richard_field"],
        created="2025-09-18T21:30", after=True,
        layer="print", tier="T3", entries=["W082"],
        why="A chance at a stall, written that night. The dated year has ten in the morning; the line sits after rehearsal so he is not in two places. No name he is given in the margin is copied onto the calendar.",
    )
    book.add(
        "2025-10-10", "Yaxley, a look at the tooth.",
        start="08:15", end="08:45",
        location="Yaxley's",
        organizer="barnaby_yaxley", attendees=[OWNER],
        created="2025-10-09T21:00",
        layer="other", tier="T5", entries=["W402"],
        why="He goes in the morning. The drawing is put on Tuesday. There is no shop slug, so the line names him and gives no place.",
    )
    book.add(
        "2025-10-13", "Gilbert, xxix.",
        all_day=True, created=ALMANAC,
        layer="family_day", tier="T3", entries=["W403"],
        why="Gilbert is twenty-nine. The call that day is not arranged, and is not entered.",
    )
    book.add(
        "2025-10-14", "Yaxley, to draw a tooth. xij d.",
        start="10:00", end="11:00",
        location="Yaxley's",
        organizer="barnaby_yaxley", attendees=[OWNER],
        created="2025-10-10T09:00",
        layer="other", tier="T5", entries=["W089"],
        why="Booked on Friday, when Yaxley looked. No rehearsal that morning. Cowley has the part.",
    )
    book.add(
        "2025-10-20", "Sharers: who pays at Christmas?",
        start="17:00", end="18:15",
        location="the Theatre", place="the_theatre",
        organizer="john_heminges",
        attendees=[OWNER, "richard_burbage", "will_kemp", "george_bryan"],
        created="2025-10-18T19:00",
        layer="company_business", tier="T3", entries=["W090"],
        why="The question, after Kettleby has been. His call is not entered. The vague Christmas line is written after this meeting, and later struck.",
    )
    book.add(
        "2025-12-26", "Court at Christmas?",
        all_day=True,
        created="2025-10-20T18:30", modified="2025-11-07T17:00",
        status="cancelled",
        layer="court", tier="T3", entries=["W405"],
        why="An expectation, written the day the warrant is in question. Struck on 7 Nov, when my lord names three nights. The call itself is not a line.",
    )
    book.add(
        "2025-10-23", "Supper with Master Daniel.",
        start="18:30", end="21:00",
        location="near Paul's", place="pauls_churchyard",
        organizer="samuel_daniel", attendees=[OWNER],
        created="2025-10-21T19:00",
        layer="social", tier="T3", entries=["M040"],
        why="Daniel asks him. The carrier was that morning. The play was the afternoon.",
    )
    book.add(
        "2025-11-13", "Tilney reads Romeo, and changes nothing.",
        start="10:00", end="12:00",
        location="St John's, Clerkenwell", place="st_johns_clerkenwell",
        organizer="edmund_tilney", attendees=[OWNER],
        created="2025-11-11T18:00",
        layer="company_business", tier="T2", entries=["W094"],
        why="The license, untouched. It takes the rehearsal morning. The public afternoons can be billed from here.",
    )
    book.add(
        "2025-11-17", "The tilt.",
        start="11:00", end="16:00",
        location="Whitehall tilt-yard", place="whitehall_tiltyard",
        created=ALMANAC,
        layer="court", tier="T1", entries=["S106"],
        why="Accession Day, written in the almanac. He goes. The house does not play. Nobody is met in the line.",
    )
    book.add(
        "2025-11-19", "Reading. Romeo.",
        start="09:00", end="12:15",
        description="Pope reads the Nurse.",
        location="the Burbages', Holywell", place="burbage_house_holywell",
        attendees=["thomas_pope", "richard_burbage", "will_kemp", "augustine_phillips"],
        created="2025-11-15T18:00",
        layer="rehearsal", tier="T5", entries=["W096"],
        why="The company reads it. Not a public afternoon.",
    )
    book.add(
        "2025-11-24", "Supper at the Bell, with Quiney.",
        start="18:00", end="21:00",
        location="the Bell, Carter Lane", place="the_bell_carter_lane",
        organizer="richard_quiney", attendees=[OWNER],
        created="2025-11-22T19:00",
        layer="social", tier="T3", entries=["W098"],
        why="Named on Saturday, so it is an arrangement. The calls that merely arrive are not.",
    )
    book.add(
        "2025-11-25", "Heminges, xxix.",
        all_day=True, created=ALMANAC,
        layer="company_business", tier="T3", entries=["W414"],
        why="Heminges's day. A call that turns to the court schedule is not entered.",
    )
    book.add(
        "2025-11-26", "Choosing the court plays.",
        start="17:00", end="18:30",
        location="the Theatre", place="the_theatre",
        organizer="john_heminges",
        attendees=[OWNER, "richard_burbage", "george_bryan", "will_kemp"],
        created="2025-11-22T18:00",
        layer="company_business", tier="T2", entries=["S107"],
        why="The three nights are already on the book. Tonight they are named. The Richmond lines are touched the same evening.",
    )

    # --- December ---
    book.add(
        "2025-12-09", "Canon Row: Richard II, the whole play (I play)",
        start="17:00", end="22:00",
        description="Supper, then the play, the deposing left in.",
        location="Canon Row", place="canon_row",
        organizer="edward_hoby", attendees=[OWNER, "richard_burbage"],
        created="2025-12-07T20:00",
        layer="company_play", tier="T2", entries=["S112a", "S112b"],
        why="Hoby's supper, and the one time the play is given whole. No public afternoon at the Theatre. The summons was a call on Sunday and is not itself a line.",
    )
    book.add(
        "2025-12-16", "Court rehearsal, before Master Tilney.",
        start="09:00", end="12:30",
        location="St John's, Clerkenwell", place="st_johns_clerkenwell",
        organizer="edmund_tilney", attendees=[OWNER, "richard_burbage", "john_heminges"],
        created="2025-11-26T20:30",
        layer="rehearsal", tier="T2", entries=["W104"],
        why="In place of the ordinary Tuesday rehearsal. Written when the plays were chosen.",
    )
    book.add(
        "2025-12-19", "At Field's, with James Burbage.",
        start="10:30", end="12:00",
        location="Field's printing house", place="fields_printing_house",
        attendees=["richard_field", "james_burbage"],
        created="2025-12-19T21:40", after=True,
        layer="company_business", tier="T3", entries=["M052"],
        why="Written that night. A hall is talked of. Nothing is bought.",
    )
    book.add(
        "2025-12-21", "The dole, ij s.",
        start="16:00", end="16:30",
        location="Mistress Ansell's", place="ansell_house",
        created="2025-12-21T15:40",
        layer="money", tier="T3", entries=["S113"],
        why="Two shillings, as he takes them out. Not written into the almanac a year ahead. The church is the morning line.",
    )
    court = [
        ("2025-12-26", "Richmond: LLL, before the Queen (I play)", ["S115a"]),
        ("2025-12-27", "Richmond: Romeo and Juliet, before the Queen (I play)", ["S115b"]),
        ("2025-12-28", "Richmond: Errors, before the Queen (I play)", ["S115c"]),
    ]
    for d, title, entries in court:
        book.add(
            d, title,
            start="21:00", end="23:45",
            location="Richmond Palace", place="richmond_palace",
            organizer="henry_carey_hunsdon",
            attendees=[OWNER, "john_heminges", "george_bryan", "richard_burbage"],
            created="2025-11-07T17:00", modified="2025-11-26T20:00",
            layer="court", tier="T1", entries=entries,
            why="Three nights, put on the book when my lord names them, and the titles written on 26 Nov. The night runs past midnight; the line stays on the day. The vague 'Court at Christmas?' is the struck line above these.",
        )
    book.add(
        "2025-12-24", "Tilt-boat to Richmond.",
        start="09:00", end="12:00",
        description="Put off a day. The weather is foul.",
        location="Old Swan Stairs", place="old_swan_stairs",
        attendees=["davy_gannet"],
        created="2025-12-20T11:00", modified="2025-12-22T19:00",
        layer="travel", tier="T3", entries=["W107"],
        why="Booked for the 23rd, moved on the 22nd when the weather holds the court. Davy takes the boat.",
    )
    book.add(
        "2025-12-24", "The Feathers.",
        start="12:00", end="13:00",
        location="the Feathers, Richmond", place="the_feathers_richmond",
        created="2025-12-20T11:00", modified="2025-12-22T19:00",
        layer="travel", tier="T3", entries=["W107"],
        why="Where he lodges until Monday. Christmas Day is here, not at St Helen's.",
    )
    book.add(
        "2025-12-29", "The tilt-boat, downriver.",
        start="09:00", end="12:00",
        location="the Feathers, Richmond", place="the_feathers_richmond",
        created="2025-12-20T11:00",
        layer="travel", tier="T3", entries=["W108"],
        why="Home on the Monday, as arranged with the going up.",
    )
    book.add(
        "2025-12-29", "Home.",
        start="13:00", end="14:00",
        location="Mistress Ansell's", place="ansell_house",
        created="2025-12-20T11:00",
        layer="travel", tier="T3", entries=["W108"],
        why="Back in Bishopsgate. The latch was mended while he was away.",
    )
    book.add(
        "2025-12-30", "Field's fire.",
        start="19:30", end="22:00",
        location="Field's printing house", place="fields_printing_house",
        organizer="richard_field", attendees=[OWNER, "jacqueline_field"],
        created="2025-12-29T18:00",
        layer="social", tier="T3", entries=["M057"],
        why="The last time he sees Field this year. The Dream is read. The Holinshed is still out. Nothing is said about being paid that belongs to a later year.",
    )

    # Silence a lint about play_items being unused in case a caller wants the ratio later.
    _ = play_items


def assert_shape(events: list[dict]):
    by_date: dict[str, list[dict]] = {}
    for ev in events:
        by_date.setdefault(ev["date"], []).append(ev)

    easter = by_date.get("2025-04-20", [])
    if len(easter) != 1 or not easter[0]["title"].startswith("Easter Day."):
        raise SystemExit(f"Easter Day should be one church line, got {[e['title'] for e in easter]}")

    jul = [e for e in by_date.get("2025-07-24", []) if e["layer"] == "company_play"]
    if len(jul) != 1 or jul[0]["title"] != "No play" or jul[0]["status"] != "confirmed":
        raise SystemExit(f"24 Jul company_play bad: {jul}")
    if len(by_date.get("2025-07-24", [])) != 1:
        raise SystemExit(f"24 Jul should read only No play, got {[e['title'] for e in by_date['2025-07-24']]}")

    rose_may = [e for e in by_date.get("2025-05-18", []) if e["layer"] == "rival_bill"]
    if rose_may:
        raise SystemExit("18 May has a Rose bill")

    marks = [e for e in events if e["layer"] == "private_mark"]
    if sorted(e["date"] for e in marks) != [d for d, _ in CROSSES] or any(e["title"] != "×" for e in marks):
        raise SystemExit("private marks drifted")

    feb6 = by_date.get("2025-02-06", [])
    blob = " ".join((e["title"] + " " + e.get("description", "")) for e in feb6).lower()
    if "raleigh" in blob or "guiana" in blob:
        raise SystemExit("Raleigh is on 6 Feb")

    # created before start, unless after the fact
    for ev in events:
        start = datetime.fromisoformat(ev["date"] + "T" + (ev.get("start") or "00:00"))
        created = datetime.fromisoformat(ev["created"])
        if not ev.get("after_the_fact") and created >= start:
            raise SystemExit(f"created not before start: {ev['date']} {ev['title']} {ev['created']}")
        if ev.get("modified"):
            modified = datetime.fromisoformat(ev["modified"])
            if not ev.get("after_the_fact") and modified >= start:
                raise SystemExit(f"modified not before start: {ev['date']} {ev['title']}")
            if modified < created and not ev.get("after_the_fact"):
                raise SystemExit(f"modified before created: {ev['date']} {ev['title']}")


def main():
    text = WORLD_PATH.read_text(encoding="utf-8")
    people, places, entries = parse_world(text)
    weeks = parse_weeks(text)
    unknown = []
    for w in weeks:
        _, unk = company_titles(w["playing"])
        unknown.extend((w["n"], u) for u in unk)
    if unknown:
        print("unknown company italics (ignored):")
        for n, u in unknown:
            print(f"  week {n}: {u}")

    items = assign_plays(weeks)
    spread_iplay(items)
    confirmed = [it for it in items if not it["cancel"]]
    played = sum(1 for it in confirmed if it["i_play"])
    ratio = played / len(confirmed)

    book = Book(people, places, entries)
    build_plays(book, items)
    build_no_play(book)
    bills = build_rose(book, weeks)
    build_standing(book)
    build_rehearsals(book)
    build_life(book, items)
    from extras import add_extras
    n_extras = add_extras(book)
    assert_shape(book.events)

    def key(ev):
        return (ev["date"], 0 if ev.get("all_day") else 1, ev.get("start") or "", ev["title"])

    book.events.sort(key=key)
    for i, ev in enumerate(book.events, 1):
        ev["id"] = f"cal-{i:04d}"
        # id first
    ordered = []
    for ev in book.events:
        head = {"id": ev.pop("id")}
        head.update(ev)
        ordered.append(head)

    payload = {"owner": OWNER, "timezone": "Europe/London", "events": ordered}
    OUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    from collections import Counter
    layers = Counter(ev["layer"] for ev in ordered)
    print(f"wrote {OUT_PATH}  events={len(ordered)}")
    for layer, n in sorted(layers.items(), key=lambda kv: -kv[1]):
        print(f"  {layer:20} {n}")
    print(f"plays confirmed={len(confirmed)}  (I play)={played}  ratio={ratio:.3f}")
    print(f"merge extras={n_extras}")
    print(f"rose bills={len(bills)}  attend={len(ROSE_ATTEND)}")
    cancelled = [ev["title"] for ev in items if ev["cancel"]]
    print("struck bill:", cancelled, items[[it['date'] for it in items].index(date(2025, 6, 30))]["title"])
    if not (0.62 <= ratio <= 0.72):
        raise SystemExit(f"(I play) ratio {ratio:.3f} outside 0.62-0.72")


if __name__ == "__main__":
    main()
