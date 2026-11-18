# william journal research: the synthesis

**The editor · 2026-11-14 · step 0 of the william journal.** It reconciles three deep-research reports (ChatGPT, Gemini and a third, Claude by its format) that answered the request. Six editors worked in parallel, one per topic. Each read all three reports, checked the load-bearing claims against primary and authoritative sources on the web, and wrote one section of the source book. This file is the summary and the index.

## TL;DR

**One document names Shakespeare in 1595, and nothing places him on any day of it.** That document is the Council warrant of 15 March 1594/5, which pays Kemp, Shakespeare and Burbage £20 for two plays before the Queen at Christmas 1594. Every day of the journal is therefore invented. What isn't invented is the scaffold, and it is richer than expected:

- the Rose's repertory, day by day from Henslowe's diary (215 performances in 1595, 16 of them new);
- the court's itinerary, from Colthorpe, including **Christmas 1595 at Richmond with his company playing 26, 27 and 28 December**, which none of the reports had;
- a crisis year of dated public events (Southwell's execution, the June riots and the Tower Hill executions, the Spanish raid on Cornwall, Drake's last voyage, Accession Day);
- a defensible creative arc: *Love's Labour's Lost* in winter, *Richard II* in spring, *Romeo and Juliet* through summer and autumn, the *Dream* from late autumn.

That is enough to write a true-feeling year. The sources are unanimous on one rule for writing it: **present-tense invention is fine, provided every anchor keeps its honest tier.**

## The source book

| § | Section | What it gives the build |
|---|---|---|
| 1 | [Chronology and the 1595 calendar](sourcebook/01-chronology-and-calendar.md) | the decade, then every 1595 day that carries anything: Julian date, weekday (also the 2025 weekday), feast, term, court, event, moon |
| 2 | [The cast](sourcebook/02-cast.md) | William himself, every person around him with their age in 1595, and "voices" notes for the 10–15 people he talks to most |
| 3 | [Places and itinerary](sourcebook/03-places-and-itinerary.md) | a best-guess itinerary, a gazetteer with coordinates, walking and riding distances, the Stratford road |
| 4 | [Works, company and rival repertory](sourcebook/04-works-company-repertory.md) | works timeline, the creative arc by season, working method, the company as a business, Henslowe's 1595 day by day, public-domain texts |
| 5 | [Daily life, body, news and myth](sourcebook/05-life-body-news-myth.md) | prices, food, speech, the working day, body-data ranges, the news of 1595, the contested questions, traditions, the imagined Shakespeare, the source pack |
| 6 | [Scene seeds](sourcebook/06-scene-seeds.md) | 118 merged seeds, anchors checked, coverage counts, and **a light first cut of 33** that covers every month and every journal source |

## Corrections the reports got wrong (all of them, or the best of them)

Three reports agreeing was not verification. These calls came from the primary-source checks:

| Claim | The reports | The call | Section |
|---|---|---|---|
| The Christmas 1594 plays were at Greenwich | all three: T1 | **T2.** The warrant names no venue; Greenwich follows from where the court was | 1, 2, 3 |
| Stratford's second fire, 21 or 22 Sept 1595 | ChatGPT T1, Gemini May | **1595, date unknown, probably July and smaller.** The September dates are a 1938 deduction that Bearman (2000) calls "seriously flawed". The first fire was about 13 May 1594 | 1, 5 |
| A cold, wet summer in 1595 | the request's seed; Gemini T1 | **That was 1594.** The only documented 1595 weather is two days | 1, 5 |
| Christmas 1595 at court | open, or "probably Richmond" | **Richmond, T1:** 26, 27 and 28 Dec, 6 Jan and 22 Feb, paid to Bryan and Heminges, not him | 1, 3 |
| *Galfrido and Bernardo* at the Rose, 18 May | ChatGPT | **A 19th-century Collier forgery. Never use it** | 1, 6 |
| The battle of Clontibret | ChatGPT: March | **25–27 May 1595** | 1, 5 |
| He lived in St Helen's from 1596 | Gemini | **The earliest record is Nov 1597.** In 1595 it is a working model (T2/T3) | 2, 3 |
| Simon Forman in Lambeth, with plague scenes | Gemini | **1601 onward, and 1595 was a low-plague year.** Forman stays out | 2, 6 |

All 172 weekday claims in the source book that carry a 1595 date were re-checked by the editor in code: no errors (`/var/tmp/wj-check/wd.py`, 2026-11-14; lines that carry other years were excluded and checked by hand).

## Where all three agree (the spine)

- He is a sharer and the house playwright of the Lord Chamberlain's Men, formed in 1594, under Henry Carey, Lord Hunsdon.
- The company plays at the Theatre in Shoreditch (the Curtain beside it), possibly at the Cross Keys in winter, and at court at Christmas. Afternoons start at two.
- *Venus and Adonis* and *Lucrece* are selling in Paul's Churchyard. He is known as a poet before he is known as a playwright.
- 1595 is a dearth year: a poor harvest, high food prices and a shrinking penny loaf. The city is nervous, the Lord Mayor blames the playhouses, and the war is close (Ireland, Cornwall, Drake).
- Anne and the three children are in Stratford: Susanna is 12, and the twins turn 10 at Candlemas. His father John is in debt and on the 1592 recusancy list.
- Every intimate thread (the Fair Youth, the Dark Lady, a Catholic life, Southampton in 1595) is T3 and stays unnamed as fact.

## Divergences settled

The smaller disagreements are settled inside each section's divergences table, each with the positions, the call and how it was made: ages, receipts, routes, coordinates and dates. The cast section alone lists 34. Two calls are the editor's, because they sit between sections:

- **When he drafts *Romeo and Juliet*.** Seed S024 has him drafting it in Lent with Brooke open. The works section recommends summer and autumn for it, and winter for *Love's Labour's Lost*. **The call: follow the works arc.** The world step moves S024 to summer, or makes the Lent entry early notes.
- **Philip Howard's death:** 19 Oct (most authorities). Colthorpe's 15 Oct is the outlier.

## What each journal source can be built from (affordances)

| Source | Built on | Watch for |
|---|---|---|
| **Calendar** | feasts, law terms, Lent, Easter (20 Apr), court seasons, quarter days, the Rose's playbill, Richmond at Christmas | the journal holds 2025 dates, same day and weekday (decision 1) |
| **Audio meetings** | rehearsals from cue scripts, sharers' meetings (splitting the £20 on 15 Mar; tour or wait out the summer), the Hoby supper, court nights | dialogue from § 2 voices and § 5 speech; stock voices |
| **Calls** | his patron Hunsdon's household, Southampton (T3), the printer Richard Field, Stratford neighbours (Quiney) | thinnest source: 3 seeds. Fill it with invented calls on true relationships |
| **Voice memos** | his private reactions: Southwell, the riots, the executions, a line of verse on a walk | never present at an execution |
| **Writing** | the creative arc by season; public-domain quarto text (R&J Q1/Q2, the sonnets, *Lucrece*) | never date a composition as a record |
| **Screen and media** | the Rose's playbill as a watch history (215 performances in 1595), proof sheets at Field's, pamphlets, news | Henslowe's own dates slip and some fall on days that don't exist; keep his dates, use corrected weekdays |
| **Photos** | the river, Bankside, Crosby Place, Midsummer bonfires, Bartholomew Fair, Accession Day, the fire-scarred Stratford street | invented weather only |
| **Location** | the gazetteer's coordinates; the Stratford road (about 100 miles, 4 days on foot, 2–3 riding) | his lodging is a working model |
| **Body** | steps: performance day 9–15k, writing day 2.5–6k, a Stratford walking day 45–60k; seasonal daylight for sleep | all invention. Heart rate is pure invention. Illness mild, never plague, never the children |

## What has to be invented (the gaps)

His whereabouts on any day; his company's own 1595 repertory and playing days; any trip home (the two open windows are Lent and the summer break); his lodging and landlord; daily weather; the boy players' names; tavern keepers; almost all dialogue. **Unverified items that must be checked before anything appears externally:** the Hoby letter's wording, the Henslowe receipts (read from a machine-read scan of Greg 1904; check them against Foakes 2002), and the New Oxford dates (read from a secondary table).

## Decisions for the editor

1. ~~1995 dates: match the date or match the weekday?~~ **Settled: the journal holds 2025** (design decision, 2026-11-14). 2025's calendar is identical to 1595's (Julian), Easter on 20 April included, so date and weekday both carry over unchanged. Read every "1995 weekday" column in § 1 as superseded: the 1595 weekday is the 2025 weekday.
2. **The light year:** the 33-seed first cut in [§ 6.4](sourcebook/06-scene-seeds.md) as the starting year. The editor proposes taking it as the seed list for the world step.

## Next (proposed, not dispatched)

**Step 1, the world:** one session writes the canon from this source book. It covers the cast with voices, the rules of anachronism (what a meeting, a call, a screen and a photo are in his world), the year's arc by month, and the light year as dated entries. Then step 2, the calendar source, is the first build in field_journal.
