"""Build the desktop's feed from the journal.

Reads build/journal and writes desktop/feed.js: every desk frame's legible text
and surface, the calendar, the calls with their speakers and lines, and the
people in them (their faces are read from build/journal/entities/<id>/photo.jpg).
The desktop assembles any moment from this feed (stage.js). Nothing here reaches
the screen except what the journal says was in front of William.

usage: python3 desktop/feed.py      (run again after the journal changes)
"""
import json, os, re, pathlib

HERE = pathlib.Path(__file__).resolve().parent
J = HERE.parent / "build/journal"
ROSTER = ["john_heminges", "richard_burbage", "cuthbert_burbage", "will_kemp", "richard_field", "gilbert_shakespeare",
          "john_florio", "richard_quiney", "ambrose_kettleby", "anne_shakespeare", "nick_sorrell", "thomas_hobbins"]


def surface(seg):
    try:
        sj = json.load(open(seg / "talents/screen.json"))
    except Exception:
        return None
    for e in sj.get("entities", []):
        m = re.search(r"Shown on (\w+)", e.get("context", ""))
        if m:
            return m.group(1)
    return None


def sections(seg):
    raw = (seg / "talents/screen_text.md").read_text()
    out = []
    for block in re.split(r"\n(?=## )", raw.strip()):
        body = re.sub(r"^## [^\n]*\n?", "", block).strip()
        if body and body.lower() not in ("none", "(none)"):
            out.append(body)
    uniq = []
    for b in out:  # the same legible text seen twice is one surface, not two
        if b not in uniq:
            uniq.append(b)
    return uniq


def entity_people(seg):
    try:
        se = json.load(open(seg / "talents/sense.json"))
    except Exception:
        return [], None
    ppl = [e["name"] for e in se.get("entities", []) if e.get("type") == "Person" and e["name"] != "William Shakespeare"]
    return ppl, se.get("content_type")


def slug_index():
    idx = {}
    for d in os.listdir(J / "entities"):
        p = J / "entities" / d / "entity.json"
        if p.exists():
            e = json.load(open(p))
            for n in [e.get("name", "")] + e.get("aka", []):
                idx.setdefault(n.lower(), d)
    return idx


def main():
    frames = []
    for seg in sorted(J.glob("chronicle/*/desk/*/")):
        day = seg.parts[-3]
        s = seg.name
        texts = sections(seg)
        try:
            assets = [a["name"] for a in json.load(open(seg / "talents/documents.json")).get("assets", [])]
        except Exception:
            assets = []
        ppl, ctype = entity_people(seg)
        try:
            act = " ".join(x.get("activity", "") for x in json.load(open(seg / "talents/facets.json")))
        except Exception:
            act = ""
        try:
            act += " " + json.load(open(seg / "talents/documents.json")).get("overview", "")
        except Exception:
            pass
        frames.append({
            "day": f"{day[:4]}-{day[4:6]}-{day[6:]}", "seg": s, "t": f"{s[:2]}:{s[2:4]}",
            "surface": surface(seg), "kind": ctype, "work": assets[0] if assets else None,
            "people": ppl, "text": texts, "activity": act.strip(), "photo": (seg / "screenshot_screen.jpg").exists() or (seg / "page_screen.jpg").exists()})

    # an untagged frame takes its surface from what the journal's own activity line says it was
    for f in frames:
        if f["surface"] is None:
            a = f["activity"].lower()
            for pat, surf in [(r"letter", "letter"), (r"almanac", "almanac"), (r"\bbill\b|playbill", "bill"),
                              (r"ledger|account|coffer|reckon", "ledger"), (r"\btables\b", "tables"), (r"\bplot\b", "plot"),
                              (r"\bpart\b|\broll\b", "part"), (r"chaucer|holinshed|plutarch|ovid|read the|reading", "book")]:
                if re.search(pat, a):
                    f["surface"] = surf
                    break

    calendar = {}
    for f in sorted(J.glob("chronicle/*/calendar/*/calendar_*.jsonl")):
        for line in open(f):
            ev = json.loads(line)
            if ev.get("change") == "removed":
                continue
            day = ev["start"][:10]
            calendar.setdefault(day, {})[ev["event"]] = {"t": ev["start"][11:16], "title": ev["title"], "where": ev.get("location")}
    calendar = {d: sorted(v.values(), key=lambda e: e["t"]) for d, v in sorted(calendar.items())}

    idx = slug_index()
    calls, faced = [], set(ROSTER)
    for seg in sorted(J.glob("chronicle/*/calls/*/")):
        day = seg.parts[-3]
        lines = [json.loads(l) for l in open(seg / "audio.jsonl")][1:]
        try:
            speakers = json.load(open(seg / "talents/speakers.json"))
        except Exception:
            speakers = []
        ids = [idx.get(n.lower()) for n in speakers]
        calls.append({"day": f"{day[:4]}-{day[4:6]}-{day[6:]}", "seg": seg.name, "t": f"{seg.name[:2]}:{seg.name[2:4]}",
                      "with": [i for i in ids if i and i != "william_shakespeare"],
                      "lines": [{"who": l.get("speaker"), "at": l.get("start"), "text": l.get("text")} for l in lines]})
        faced.update(i for i in ids if i)

    people = {}
    for d in sorted(faced):
        e = J / "entities" / d
        if not (e / "entity.json").exists():
            continue
        meta = json.load(open(e / "entity.json"))
        has = (e / "photo.jpg").exists()
        people[d] = {"name": meta["name"], "face": f"../build/journal/entities/{d}/photo.jpg" if has else None}

    out = {"frames": frames, "calendar": calendar, "calls": calls, "people": people, "roster": ROSTER}
    (HERE / "feed.js").write_text(
        "/* generated by desktop/feed.py from build/journal: do not edit */\nwindow.JOURNAL = "
        + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print(f"frames {len(frames)} · calendar days {len(calendar)} · calls {len(calls)} · people {len(people)} "
          f"({sum(1 for p in people.values() if p['face'])} with faces)")


if __name__ == "__main__":
    main()
