#!/usr/bin/env python3
"""Check a week of content against FORMAT.md and the canon.

Usage: python3 content/lint.py content/weeks/<Sunday>/<author>/

Structural and canon checks only: fields, kinds, slugs, places (and against the
week's day plan), calendar and
entry ids by date, verbatim quotes, the meeting rule, and forbidden words.
It does not judge prose. Exit 1 on any error.
"""
import json
import re
from collections import Counter
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORLD = (ROOT / "world/world.md").read_text()
CAL = {e["id"]: e for e in json.loads((ROOT / "calendar/merged/calendar.json").read_text())["events"]}

SLUGS = set(re.findall(r"^#### `([a-z_]+)`", WORLD, re.M))
s3 = WORLD[WORLD.index("## 3. The cast bible"):WORLD.index("## 4. The places bible")]
s4 = WORLD[WORLD.index("## 4. The places bible"):WORLD.index("## 5. The year's arc")]
PEOPLE = set(re.findall(r"^#### `([a-z_]+)`", s3, re.M))
PLACES = set(re.findall(r"^#### `([a-z_]+)`", s4, re.M))
ENTRIES = {m.group(1): m.group(2) for m in re.finditer(r"^\*\*([A-Z]\d+[a-d]?) · (2025-\d\d-\d\d)", WORLD, re.M)}
FACETS = {"company", "writing", "household", "stratford"}
KINDS = {"meeting": "Transcript", "call": "Transcript", "memo": "Transcript",
         "note": "Page", "frame": "Frames", "photo": "Photo"}
# The pipeline's own words, leaked into his day (batch 4: "as the entry has it", "New fiction, not a text of the play").
PIPELINE = re.compile(r"new fiction|label only|not set out here|(?:is|are|was|were) not set out|not written out here|public[- ]domain|into (?:this|the) frame|as the entry has it|the entry's own words|(?:was|were|is) not denied|failed to happen|(?:the|this) day plan|has no entry of its own|not a text of the play", re.I)
FORBIDDEN = re.compile(r"\b(captured?|recorded|recording|watched|device|phone|app|screen ?time|emilia|bassano|lanier)\b", re.I)
SEG = re.compile(r"^## (\d\d:\d\d) · (\d+) min · (\w+) · (.+)$", re.M)
LINE = re.compile(r"^\[(\d\d):(\d\d)\] (?:([a-z_]+): (.+)|\(([^)]+)\): (.+)|\((.+)\))$")

errors, warns = [], []
DAYPLAN = {}  # day iso -> set of place slugs the day plan allows


def load_dayplan(week_dir):
    """The hand plan in the week's own folder wins; else the generated one."""
    sunday = week_dir.parent.name if week_dir.name != week_dir.parent.name else week_dir.name
    hand = ROOT / "content/weeks" / sunday / "dayplan.md"
    gen = ROOT / "content/dayplans/weeks" / f"{sunday}.md"
    src = hand if hand.exists() else gen
    if not src.exists():
        return None
    import datetime as dt
    for row in src.read_text().splitlines():
        cols = row.split("|")
        if len(cols) < 6 or not re.match(r"\s*\w{3} \d+ \w{3}", cols[1]):
            continue
        d = dt.datetime.strptime(cols[1].strip() + " 2025", "%a %d %b %Y").date().isoformat()
        DAYPLAN[d] = set(re.findall(r"`([a-z_]+)`", cols[4]))
    return src


def err(where, msg):
    errors.append(f"{where}: {msg}")


def warn(where, msg):
    warns.append(f"{where}: {msg}")


def field(block, name):
    m = re.search(rf"^- {re.escape(name)}: (.+)$", block, re.M)
    return m.group(1).strip() if m else None


def section(block, name):
    m = re.search(rf"^### {re.escape(name)}\n(.*?)(?=^### |\Z)", block, re.M | re.S)
    return m.group(1) if m else None


def ids(val):
    if not val or val.strip().lower() == "none":
        return []
    return [x.strip() for x in re.split(r"[,;]", val.split("(")[0]) if x.strip()]


def check_day(path, transcripts):
    day = path.stem
    text = path.read_text()
    head = text.split("\n## ", 1)[0]
    for pm in PIPELINE.finditer(text):
        err(day, f"pipeline words in the day: '{pm.group(0)}' (keep them in reasoning.md)")
    for name in ("wakes", "day type", "calendar", "entries"):
        if not re.search(rf"^- {name}:", head, re.M):
            err(day, f"header lacks '{name}'")
    for cid in ids(field(head, "calendar")):
        if cid not in CAL:
            err(day, f"calendar id {cid} does not exist")
        elif CAL[cid]["date"] != f"{day}" and not CAL[cid].get("end_date") and not CAL[cid].get("rrule"):
            err(day, f"{cid} is dated {CAL[cid]['date']}")
    for eid in ids(field(head, "entries")):
        if ENTRIES.get(eid) != day:
            err(day, f"entry {eid} is dated {ENTRIES.get(eid)}")
    for sec in ("## Pulse", "## Briefing for tomorrow morning"):
        if sec not in text:
            err(day, f"missing {sec}")
    segs = list(SEG.finditer(text))
    counts = {}
    for i, m in enumerate(segs):
        hhmm, mins, kind, title = m.groups()
        where = f"{day} {hhmm} {kind}"
        block = text[m.end(): segs[i + 1].start() if i + 1 < len(segs) else len(text)]
        counts[kind] = counts.get(kind, 0) + 1
        if kind not in KINDS:
            err(where, f"unknown kind {kind}")
            continue
        if field(block, "kind") != kind:
            err(where, "kind field disagrees with heading")
        place = field(block, "place")
        if place not in PLACES:
            err(where, f"place {place} is not a § 4 slug")
        elif DAYPLAN and day in DAYPLAN and place not in DAYPLAN[day]:
            err(where, f"place {place} is not in the day plan for {day} ({', '.join(sorted(DAYPLAN[day]))})")
        if field(block, "facet") not in FACETS:
            err(where, f"facet {field(block, 'facet')}")
        ppl = field(block, "people") or ""
        slugs = re.findall(r"([a-z_]+) \((?:attendee|mentioned|visible|heard)\)", ppl)
        for s in slugs:
            if s not in PEOPLE:
                err(where, f"person {s} is not a § 3 slug")
        for eid in ids(field(block, "entries")):
            if ENTRIES.get(eid) != day:
                err(where, f"entry {eid} is dated {ENTRIES.get(eid)}")
        cont = field(block, "continues")
        if cont:
            # A continuation segment carries on an activity begun earlier the same day
            # (FORMAT.md, "continues"): it has no Activity of its own.
            prior = [(h, k) for h, _, k, _ in (x.groups() for x in segs[:i])]
            if (cont.strip(), kind) not in prior:
                err(where, f"continues: {cont} names no earlier {kind} segment today")
            if section(block, "Activity") is not None:
                err(where, "a continuation segment has no ### Activity (the first segment carries it)")
            needed = ("Sense", KINDS[kind])
        else:
            needed = ("Sense", "Activity", KINDS[kind])
        for name in needed:
            if section(block, name) is None:
                err(where, f"missing ### {name}")
        if kind == "frame" and not field(block, "surface"):
            err(where, "frame lacks surface")
        body = section(block, KINDS[kind]) or ""
        if KINDS[kind] == "Transcript":
            spoken = []
            for ln in [l for l in body.splitlines() if l.strip()]:
                lm = LINE.match(ln.strip())
                if not lm:
                    err(where, f"bad transcript line: {ln[:60]}")
                    continue
                if lm.group(5):
                    spoken.append(("(" + lm.group(5) + ")", lm.group(6)))
                if lm.group(3):
                    spoken.append((lm.group(3), lm.group(4)))
                    if lm.group(3) not in PEOPLE:
                        err(where, f"speaker {lm.group(3)} is not a § 3 slug")
            transcripts.setdefault(day, []).extend(t for _, t in spoken)
            # His own lines per segment, for the week's Said check.
            transcripts[("william", day, hhmm, kind)] = [t for sp, t in spoken if sp == "william_shakespeare"]
            if kind == "meeting":
                voices = {s for s, _ in spoken if not s.startswith("(")}
                if len(spoken) < 25 or len(spoken) > 60:
                    warn(where, f"meeting has {len(spoken)} lines (rule 18: 25-60 for a set piece; a short overheard exchange is fine, never pad it)")
                if "william_shakespeare" not in voices or len(voices) < 3:
                    warn(where, f"meeting voices {sorted(voices)} (rule 18: William and two or more)")
            sense = section(block, "Sense") or ""
            qm = re.search(r"^- quotes: (.+?)(?=^- |\Z)", sense, re.M | re.S)
            if qm:
                for q in re.findall(r"[a-z_]+: ([^`\"\n]+?)(?:[`\"]|$|; )", qm.group(1)):
                    q = q.strip().rstrip(".,;")
                    if len(q) > 12 and not any(q[:40] in t for _, t in spoken):
                        err(where, f"sense quote not verbatim: {q[:50]}")
        for fm in FORBIDDEN.finditer(block):
            warn(where, f"forbidden word '{fm.group(0)}'")
    return counts


def main(d):
    d = Path(d).resolve()
    plan = load_dayplan(d)
    if plan is None:
        warn(str(d), "no day plan found; places not checked against one")
    days = sorted(p for p in d.glob("2025-*.md"))
    want = len(DAYPLAN) if plan else 7  # the year's edge weeks (2025-01-01, 2025-12-28) have 4 days
    dense = d.name.startswith("dense")  # a wall-to-wall day: one day file, no week.md
    if dense:
        want = 1
    if len(days) != want:
        err(str(d), f"{len(days)} day files, not {want}")
    transcripts, total = {}, {}
    for p in days:
        for k, v in check_day(p, transcripts).items():
            total[k] = total.get(k, 0) + v
    wk = d / "week.md"
    if dense:
        pass
    elif not wk.exists():
        err(str(d), "no week.md")
    else:
        w = wk.read_text()
        for pm in PIPELINE.finditer(w):
            err("week", f"pipeline words in the week: '{pm.group(0)}' (keep them in reasoning.md)")
        for sec in ("## Reflection", "## Memories", "## Said", "## Observations"):
            if sec not in w:
                err("week", f"missing {sec}")
        said = w.split("## Said", 1)[-1].split("## Observations")[0]
        for m in re.finditer(r"^- (2025-\d\d-\d\d) .*?: \"(.+?)\"", said, re.M):
            q = m.group(2)[:40]
            if not any(q in t for t in transcripts.get(m.group(1), [])):
                err("week said", f"not verbatim on {m.group(1)}: {q}")
        # The journal shows this list as "said by you": the owner's own words,
        # up to three a day (solstone CHANGELOG). Nobody else's line belongs here.
        per_day = Counter()
        for ln in [l.strip() for l in said.splitlines() if l.strip().startswith("- ")]:
            m = re.match(r'^- (2025-\d\d-\d\d) · (\d\d:\d\d) (\w+) · (.+?): "(.+)"$', ln)
            if not m:
                err("week said", f"bad Said line: {ln[:70]}")
                continue
            day_, hhmm_, kind_, who, quote = m.groups()
            per_day[day_] += 1
            if who != "william_shakespeare":
                err("week said", f"{day_}: '{who}' is not William; the journal shows Said as \"said by you\"")
                continue
            mine = transcripts.get(("william", day_, hhmm_, kind_))
            if mine is None:
                err("week said", f"{day_} {hhmm_} {kind_}: no such segment heading (the journal would link the day's first segment)")
            elif not any(quote[:40] in t for t in mine):
                err("week said", f"{day_} {hhmm_} {kind_}: not a line of William's in that segment: {quote[:40]}")
        for day, n in per_day.items():
            if n > 3:
                err("week said", f"{day}: {n} Said lines; the journal shows up to three a day")
        if sum(per_day.values()) < 3:
            warn("week said", f"{sum(per_day.values())} Said lines (FORMAT.md: three to eight)")
    print(f"{d}: segments {sum(total.values())} {dict(sorted(total.items()))}")
    for e in errors:
        print("ERROR", e)
    for w_ in warns:
        print("warn ", w_)
    print(f"{len(errors)} errors, {len(warns)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
