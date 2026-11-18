# The content format

*The editor, 2026-11-16. The markdown every creative scope writes, and the only input the formatter reads. The creative scopes decide what happened and how it is said. The formatter decides nothing: it maps these fields onto the journal's stored files (framework § 1).*

**The rule that splits the work:** if a value needs judgment (a word, a time, who was there, what it meant), it is in this file. If it can be computed (ids, segment keys, hashes, confidence numbers, receipts, file splits, entity records from slugs), the formatter computes it, and the content never carries it.

A creative scope may add a field it needs, with a reason in its `reasoning.md`. The merge keeps or drops it, and the editor updates this file.

## Files in a week

```
content/weeks/<Sunday YYYY-MM-DD>/<author>/
  2025-03-09.md … 2025-03-15.md   one file per day, seven of them
  week.md                         the weekly reflection and the week's observations
  canon-delta.md                  everything invented that the world does not already say
  reasoning.md                    why you chose what you chose (creative builds and merges only)
```

`<author>` is `grok` or `gemini` for a build, `merged-grok` or `merged-gemini` for a merge, and `merged` for the version the editor accepts.

## A day file

*The example's values follow world § 6 W118, but they are only an illustration. The world governs every real value.*

```markdown
# Sun 9 Mar 2025

- wakes: ansell_house · sleeps: ansell_house
- day type: Writing day at the lodging   (a row of world § 7.8 "Steps by day type")
- calendar: none                 (the merged calendar's ids for this date, or none)
- entries: G018                  (the world § 6 entry ids this day carries, or none)

## Pulse

- title: <a short headline for the day, plain at a glance to someone who has not read it; the same rule as activity titles>
- one sentence: <the day in one sentence, addressed to "you">
- details: <one paragraph, "you">

## Briefing for tomorrow morning

*The briefing Home shows on the next day, about this one. It reports; it never lists obligations.*

- coverage: <one sentence on what the journal holds for today>
- <bullet: one thing from today worth carrying into tomorrow>
- <two to five bullets>

## 08:30 · 12 min · meeting · The baskets carted to Shoreditch

- place: cross_keys_inn
- facet: company                 (company, writing, household or stratford)
- kind: meeting                  (meeting, call, memo, note, frame or photo)
- content type: planning         (from the sense list: meeting, writing, reading, planning, media, social, idle, …)
- density: active                (active, low_change or idle)
- people: john_heminges (attendee), abel_garnish (attendee), nick_sorrell (attendee), sam_latchet (heard), hired_men (attendee)
- entries: W118
- calendar: cal-0168

### Transcript

[00:00] john_heminges: <a line>
[00:12] william_shakespeare: <a line>
[01:40] (carts in the yard; nobody speaks)
…

### Sense

- summary: <two or three sentences, "you", what happened in this stretch>
- topics: <three to six short noun phrases>
- quotes: <two to four lines lifted verbatim from the transcript, as `slug: text`>
- also mentioned: <named things that are not people: a play, a book, a place, a sum, with a type: Project, Company or Tool>

### Activity

- title: <one line, past tense, "you" implied, plain enough to read at a glance on the day grid: "Rehearsed at the Theatre", "Ate breakfast with Mistress Ansell and Alse", "Read the Rose's playbill". Never a riddle, never the "did X and left Y" formula, and no negation unless not doing it is the event ("Did not go to the Rose"), reworded or not: "kept the chest shut", "left it unsent" and "without" are negations too. If a title cannot be made plain without inventing, leave it (revised 2026-11-17, after the screenshot review)>
- story: <one paragraph, "you", only what the transcript or page shows>
- participation: one line per person in `people`, saying what they did here
  - john_heminges: <what he did>
- relations: `from_slug → to_slug · kind · note · "quote or none"`, kind from works-with, works-at, reports-to, family-of, knows, uses, created, other
```

### What each kind carries

| kind | body section | notes |
|---|---|---|
| meeting | `### Transcript` | timed lines from 00:00, speaker slugs; `(…)` alone for a silence or a sound; `[MM:SS] (the clerk): words` for an unnamed walk-on, who gets no slug and no person record (adopted 2026-11-16 from both first builds). A set-piece meeting (world § 7.2) is William plus two or more people, 25–60 lines, up to seven voices and at least one concrete number (world § 9.3, rule 18). A short exchange overheard on the way, such as a wherry or a doorway, can be a few lines, and is never padded to reach 25 (revised 2026-11-16) |
| call | `### Transcript` | the same; the far voice is the caller's slug. London only, at most two a week (world § 2.4) |
| memo | `### Transcript` | his voice alone, `william_shakespeare:` |
| note | `### Page` | the page as he wrote it, whole, at the time it was written; a later revision is a new note segment |
| frame | `### Frames` | `[MM:SS] <label>`, then `visual:` one sentence, then `text:` the literal words on the surface, if any (world § 2.7). The segment's fields add `- surface: <tag>`, one tag from world § 9.3, rule 21 (added 2026-11-16 from the first Gemini build) |
| photo | `### Photo` | the § 7.7 description, lifted; one photo per segment |

Every kind has `### Sense` and `### Activity`. A photo's activity may be one line.

**Not in the content:** steps, heart rate, hours of sleep, coordinates and the location track belong to the backdrop. The generator writes them from world § 7.8 and § 7.9 and the day plans. The day file's `wakes`, `sleeps` and `day type` lines are the only whereabouts the content carries. Leave out a step count even where a § 6 entry gives one.

**Continuing an activity** (added 2026-11-17, for the wall-to-wall days). A long occasion, such as a rehearsal, an afternoon in the tiring-house or a morning at the desk, is several consecutive segments. On the day grid it should read as **one activity spanning them all**. Give each segment after the first `- continues: <HH:MM>`, the heading time of the segment that opens the activity, same day and same kind. A continuing segment keeps its own `### Sense` and its body, and has **no `### Activity`**: the first segment's activity carries the title, story and participation for the whole run, and the converter lists every segment under it. `lint.py` checks that the named segment exists earlier that day and is the same kind.

**Lengths.** A heading's duration is real time. A segment is one stretch of a real occasion: write the minutes that carry it, timed truthfully, and let silence be silence. An occasion longer than about 15 minutes is two or more segments, with real gaps between them.

## The week file

```markdown
# Week of Sun 9 Mar 2025

## Reflection

<two or three paragraphs, "you", built only from this week's activities>

## Memories

- 2025-03-11: <one line, drawn from that day's briefing>
- <one to seven>

## Said

- 2025-03-15 · 11:40 meeting · william_shakespeare: "<his own line, lifted verbatim from that segment's transcript>"
- <three to eight, at most three from one day>

## Observations

*Durable things learned about a person this week, the kind that stay true.*

- will_kemp · 2025-03-12: <one sentence>
```

**Said is his own words only** (revised 2026-11-17). The journal shows this list as "said by you": in solstone's words, "things you said, word for word… up to three a day, taken only from conversations where your journal recognized your voice". So every Said line is `william_shakespeare:`, from a meeting, call or memo transcript, and no day has more than three. Another person's line can go in that segment's sense quotes. It never goes here. `lint.py` errors on any other speaker. Until 2026-11-17 this example showed `john_heminges`, and 292 of the year's 439 Said lines were other people's.

## The canon delta

One line per invention, grouped: **people** (any name not in world § 3; avoid them), **places**, **objects and sums**, **facts about a person**, **phrases** a later week should echo. Each line gives the date it first appears and the segment heading. Money must agree with the world's coffer and account lines (world § 5.1, § 9.2); state any sum you use.

## Voice rules (every prose field)

- **Two registers.** Transcripts, pages and memos are the novel: his words and theirs, alive. Everything else (pulse, briefing, sense, activity, the reflection, observations) is the journal's own writing about the day, and reads like solstone's real outputs: plain, concrete and past tense. Say who, where, what was decided and how much, one idea to a sentence. "one sentence" is a single sentence of about 30 words at most. No aphorism, riddle or hint the reader must decode. (Added 2026-11-16 from the first merges: one merge's summaries were cryptic, the other's overlong.)

- Address him as "you". Never "capture", "recorded", "watched", or a device word or modern tech word.
- Cast by world § 3 slugs only. The unnamed lady is never named, and appears only as the world's seven crosses.
- Nothing he does not yet know appears before he knows it. News arrives late and secondhand.
- Hamnet is ten. Nothing plays on what comes in 1596.
