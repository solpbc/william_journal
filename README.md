# william_journal

One year in the journal of William Shakespeare: 1595, kept on 2025's calendar.

This is a complete [solstone](https://solstone.app) journal, built for demos, screenshots and agent experiments. Every day of the year has something in it, drawn from transcripts of meetings, calls and voice memos, notes, the page on his desk, photos, steps, sleep, heart rate, places and a calendar. The summaries, entities, briefings and reflections the journal's thinking would normally write were written in with everything else, so the journal reads as fully processed. It also holds 64 faces, a record of one connected agent and its history, and the journal's own mark, `crablike · cosmos`, which shows only with its identity key (see below).

It is fiction, made by language models, image models and speech synthesis working to a researched canon. Nobody living is in it.

## why it is shaped this way

**A real life, invented days.** The people, places and events of 1595 are the historical ones as far as the record goes: the Lord Chamberlain's Men in their first full year, *Romeo and Juliet* and *A Midsummer Night's Dream* in progress, the dearth, Anne and the children in Stratford. The research grades every fact from documented to invented, and the world bible carries those grades, so you can tell which is which. The days themselves, every conversation and every number, are made up.

**1595 on a 2025 calendar.** In England 1595 ran on the Julian calendar, which in that year lines up exactly with 2025's: both begin on a Wednesday, neither is a leap year, and Easter falls on 20 April in both. So every date keeps its real weekday, and Lent, Shrove Tuesday and the feasts land where they did. 2025 is the most recent year that does this, and it is already over, so the whole journal sits in the past.

**Modern sources, period causation.** The world is 1595 in every material, social and linguistic respect. Only the way his days reach the journal is modern: a meeting is any gathered talk he is part of, a call is a voice at a distance, the screen is the page in front of him, and something counts his steps on the road to Stratford. The sources never change what happens. News still comes by carrier, letters still take days, and nobody remarks on the devices. That lets a period life use everything a journal can hold without turning into a costume drama about technology.

**A quiet year with three packed days.** Most days are ordinary: rehearsals, the bill, debts, a letter home. Three are filled wall to wall, 10 August in Stratford, 22 October and 30 December, so there is somewhere to look closely as well as a year to look across.

**Photos that never show him.** Each photo is what his eye held, from his own eye level, in the light that was there: sun, fog, candle or fire. He never appears in one: no face, mirror or shadow, only his hands at the desk. People are caught mid-task and nobody poses. The look is a good phone camera of today pointed at 1595, not an old print.

**One canon every day is held to.** Before any day was written there was a world bible ([`world/world.md`](world/world.md)): the cast, the places with coordinates, the dated events of the year and the rules above. Each week was written to it, and anything new a week invented went into [`content/canon-additions.md`](content/canon-additions.md) for every later week to honour. A calendar ([`calendar/merged/`](calendar/merged/)) and a set of running threads ([`content/threads/merged/`](content/threads/merged/)) keep the plays, debts, journeys and people consistent from January to December.

One thing is deliberately absent. His son Hamnet is ten in 1595 and dies in August 1596. The year ends before that, and nothing in it plays on what is coming.

## how it was made

The research came from three deep-research reports, by ChatGPT, Gemini and a third that reads as Claude's, reconciled into the source book in [`research/`](research/). Three models (GPT-6 Astra, Gemini 4 Carbon and Fable 5.2) each wrote a full world bible, and those were folded into one. Every week was then written twice, once by Grok and once by Gemini, and a Grok merge took the best of each into the accepted text in `content/weeks/*/merged/`. A deterministic generator ([`tools/`](tools/)) turned that text into the journal's stored files, and validators checked the result. The photos, page images and faces were generated with Gemini's image model and checked against their captions. Speech recordings for 303 transcripts (all 237 voice memos, all 34 calls and 32 multi-speaker talks, 182.4 minutes in 16 kHz mono FLAC) were synthesized with ElevenLabs `eleven_v4` from 19 licensed stock voices, cloning nobody. Every recording was verified against solstone's WeSpeaker ResNet34-256 voiceprint pipeline ([`audio/README.md`](audio/README.md)).

The journal was written by machines working to a human-reviewed plan. The alternative drafts and the merge notes are not included; this repo holds what was accepted.

## what is in the repo

| Path | What it is |
|---|---|
| `build/journal/` | the finished journal: 365 days, the search index, entities, facets, reflections, 303 `audio.flac` recordings, photos, faces, the connected agent's record and the journal's identity (minus its key) |
| `audio/` | the 19-voice cast registry (`voices.json`), extracted WeSpeaker ResNet34-256 voiceprints (`voiceprints.json`), install manifest (`install.json`), ambient beds, batch lists and generation guide ([`audio/README.md`](audio/README.md)) |
| `photos/` | the accepted images, 183 year photos, 52 page images and 64 faces, with the install file that places each one and a contact sheet in each folder (`index.html`) |
| `world/world.md` | the world bible, *The Weight of a Penny* |
| `content/` | the accepted days and weeks, the day plans, the threads, the canon additions and the format and lint they follow |
| `calendar/merged/` | the year's 795 calendar events and the script that builds them |
| `research/` | the synthesis and the six-part source book |
| `tools/` | the generator, audio and photo tooling, voiceprint evaluator, read-back validator and tests ([`tools/README.md`](tools/README.md)) |
| `desktop/` | William's desktop: an imagined 1595 computer that his desk frames can be shot from, with the scripts that build it from the journal and take the screenshots ([`desktop/README.md`](desktop/README.md)) |
| `build/screens/` | a few screenshots |

The files come to about 428 MB. The largest is the search index, about 40 MB.

## serve it with solstone

This journal is only meant for sol pbc to run, for our own demos and tests, and it isn't kept in step with solstone's releases. The steps below are how we serve it. Parts of it may need a solstone release that hasn't shipped yet and may not work on the current one. Install solstone from [solstone.app/install](https://solstone.app/install).

⚠ A bare `solstone` command acts on the journal your computer already uses. Serve a copy of this one instead, and point every command at that copy:

```bash
git clone https://github.com/solpbc/william_journal && cd william_journal
mkdir -p /tmp/william/run && chmod 700 /tmp/william/run
cp -a build/journal /tmp/william/journal
export SOLSTONE_JOURNAL=/tmp/william/journal
export SOLSTONE_JOURNAL_SOCKET=/tmp/william/run/journal.sock
export SOLSTONE_CONVEY_PORT=5099
python3 tools/stamp.py --journal "$SOLSTONE_JOURNAL"
solstone journal indexer --rescan-full
solstone journal journal-stats
solstone journal convey --port 5099 --journal "$SOLSTONE_JOURNAL"
```

Then open `http://127.0.0.1:5099/` in a browser set to the `Europe/London` timezone, for example one started with `TZ=Europe/London` in its environment. `stamp.py` restores the file times git does not keep, which the journal reads to tell its days are processed. Don't configure an AI provider: what it would write is already in the journal, and a provider would rewrite some of it.

Home follows today's real date, so open a week or a day from the year directly, for example `/app/activities/20251022`. [`tools/README.md`](tools/README.md) covers the full supervisor, connecting an agent on the same computer, and the read-back.

## the identity key

A journal has an identity, and its mark is derived from it. This one's certificate is in `build/journal/link/ca/`, but its signing key is not distributed, so that nobody else can speak as this journal. A copy without the key serves, searches and reads normally, and under the full supervisor an agent on the same computer can connect through the agents app. Its mark shows as unavailable, though, and no phone or other device can pair with it.

## license

[CC BY-NC 4.0](LICENSE), covering the whole repository: the writing, the images, the audio, the journal and the code. You may share and adapt it for non-commercial purposes with attribution to sol pbc.

- **Shakespeare's own works are in the public domain**, and lines quoted from them stay so.
- **The images are generated.** No photograph of a real scene or person was used.
- **The voices are synthesized.** Licensed stock voices from the ElevenLabs Voice Library were used, cloning nobody.
- **The historical people** have been dead for centuries, and everyone else is invented.
