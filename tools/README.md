# William Journal Mechanical Generator (`tools/`)

Mechanical generator and validation harness for **the william journal** (William Shakespeare's 1595, held on 2025 dates), pinned to `solstone-journal` commit `6afa0a7c67b92d4cfc3ff7a0929f7c021a38a0ef` (`journal (solstone) 2.0.85`) in [`manifest.json`](manifest.json). That pin is for the stored formats and the tests; serving uses the latest solstone, and parts of the journal may need a release that hasn't shipped yet (see the repo README).

## Modules

- [`manifest.json`](manifest.json): Pin to `solstone-journal` (`6afa0a7c67b92d4cfc3ff7a0929f7c021a38a0ef`, `journal (solstone) 2.0.85`) with `file:line` citations for every stored format and schema.
- [`world_data.py`](world_data.py): Deterministic canon cast (71 people), 16 non-Person facet entities, 4 facets (`company`, `writing`, `household`, `stratford`), 57 places with stripped § 4 display names and coordinates, and day-type step bands, seasonal Apple Health parameters (§ 7.8 season table), and special-day / illness body overrides (`SPECIAL_DAY_BODY_OVERRIDES`).
- [`contracts.py`](contracts.py): Schema and contract registry wrapping `core/payload/solstone/talent/*.schema.json`, `core/payload/solstone/talent/journal/contract/bundle.json`, and the Rust weekly reflection judgment (`core/crates/solstone-core-home/src/weekly.rs:262-485`).
- [`dayplan.py`](dayplan.py): Derives the 365 day plans for 2025 from [`../content/threads/merged/where-he-is.md`](../content/threads/merged/where-he-is.md), [`../world/world.md`](../world/world.md) (§ 6, § 7.8, § 7.9), and [`../calendar/merged/calendar.json`](../calendar/merged/calendar.json), carrying any entry whose quoted time range crosses `24:00` into `00:00–<end>` on the following day, and writing [`../content/dayplans/2025.json`](../content/dayplans/2025.json), [`../content/dayplans/index.md`](../content/dayplans/index.md), and the 53 Sunday-to-Saturday weekly markdown tables in `../content/dayplans/weeks/*.md`.
- [`backdrop.py`](backdrop.py): Parses the 365 day plans from `content/dayplans/weeks/*.md` (with `content/weeks/2025-03-09/dayplan.md` governing 9–15 March) and `calendar/merged/calendar.json` (795 events) and writes the full-year backdrop journal tree (`config/journal.json`, `solstone/`, `solstone/apps/map/places.json`, `streams/`, `entities/`, `facets/`, `chronicle/<day>/calendar/`, `chronicle/<day>/import.apple_health/`, `chronicle/<day>/phone/`) to `build/journal/`. It writes no `chronicle/<day>/health/` receipt: those come from `converter.py`, with `imports.py` upserting receipts for imported segments. Supports a targeted refresh flag (`--refresh-body-and-places [--days YYYY-MM-DD,...]`) that updates seasonal sleep / body rows and the 31 derived map places (`derive_and_name_places` / `write_places_store`) without touching converted week artifacts. A `cancelled` event is stored as struck: its `added` note at `created`, then a `removed` note at `modified`, so the journal no longer lists it.
- [`converter.py`](converter.py): Converts content markdown in [`../content/FORMAT.md`](../content/FORMAT.md) shape (`YYYY-MM-DD.md` and `week.md`) into every authored journal artifact (`audio.jsonl`, `screen.jsonl`, `talents/screen.json` and `talents/screen_text.md` for a desk frame, `note_transcript.md`, `screenshot_screen.jpg` for a desk frame, and for a photo `chronicle/<day>/import.image/<HHMMSS>_0/original.jpg`, `image_meta.json`, `image_transcript.md`, `import_kind.json` plus `imports/<YYYYMMDD_HHMMSS>/`, `talents/speaker_labels.json`, `talents/sense.json` + 7 projections, `talents/documents.json`, deterministic `chronicle/<day>/health/<ts>_segment.jsonl`, `facets/<facet>/activities/<YYYYMMDD>.jsonl`, `facets/<facet>/entities/<YYYYMMDD>.jsonl`, `observations.jsonl`, `chronicle/<day>/talents/pulse.jsonl`, `chronicle/<day>/talents/morning_briefing.json`, and `reflections/weekly/<YYYYMMDD>.json` & `.md`), then stamps segment extract `mtime`s. Accepts repeating calendar events (`rrule`) on any date they recur in `- calendar:` lines. Fails loudly (`ContentFormatError`) on any missing creative field, and on a `## Said` line whose speaker is not `william_shakespeare` (the journal shows Said as "said by you"; `content/lint.py` enforces the same rule), or that names no activity head at its time and kind (it never falls back to another activity). A segment with `- continues: <HH:MM>` (FORMAT.md § Continuing an activity) keeps its own stream segment and sense but gets no activity record: it joins its head's activity, whose `segments` list stays in time order (the product reads the span from the first and last entries). The head's facet, content type, title and story govern; people only a continuation names join with their stated role and the generic context; `level_avg` is the product's number for the last segment's level (`activity_state.rs` `level_value`: 1.0 high, 0.5 medium, 0.25 low). A continuation with no earlier same-kind head, or with its own `### Activity`, is refused. An inline `- quotes: a: x; b: y` line splits into one quote per known speaker slug.
- [`stamp.py`](stamp.py): Deterministic post-checkout `mtime` stamper (`stamp_journal_tree(journal_root)`). Git does not preserve file `mtime`s, and `solstone-core-system-health` (`completion.rs` `segment_thinking_is_current`, `scan.rs` `newest_segment_input_ms`) compares each segment's newest input file `mtime` against `sense_input_ms` (`newest < read_from`). Sets segment files (`chronicle/<day>/<stream>/<seg>/**`) to `(min_ts_ms / 1000.0) - 300.0` and day-level `talents/` and health receipts to `max_ts_ms / 1000.0` without changing any file bytes.
- [`lived_in.py`](lived_in.py): Installs Claude's demo grant, notes and activity, standing corrections, possible names, the fixed journal mark and any supplied person portraits after conversion.
- [`imports.py`](imports.py): Installs the 18 contextual imported items from [`../content/imports/`](../content/imports/README.md) across `import.text`, `import.document`, `import.evernote`, and `import.image` (`screen_text`), with schema-validated `talents/` files, health receipts, facet activities, publication records, rebuilt stream chains, and stamped `mtime`s.
- [`audiogen.py`](audiogen.py): Resumable ElevenLabs `eleven_v4` batch synthesizer for transcript audio ([`../audio/README.md`](../audio/README.md), [`../audio/voices.json`](../audio/voices.json), [`../audio/install.json`](../audio/install.json)): scene-matched `--audio-effects`, smooth 40 ms crossfaded per-turn active-RMS leveling, and subtle non-voice 1595 ambient beds in `../audio/ambience/`, writing 16 kHz mono FLAC (`audio.flac`) and aligned `audio.jsonl` turn timings. Override the CLI binary with `--elevenlabs-bin` or `WILLIAM_ELEVENLABS_BIN`.
- [`voiceprint_eval.py`](voiceprint_eval.py): WeSpeaker ResNet34-256 voiceprint extractor and held-out turn evaluation harness matching `solstone-journal`'s filterbank and calibration thresholds, generating [`../audio/voiceprints.json`](../audio/voiceprints.json) across all installed `audio.flac` recordings.
- [`read_back.py`](read_back.py): Three-layer automated validation and Convey read-back harness against a `/var/tmp` scratch copy of the committed `build/journal/` tree (simulating fresh git checkout `mtime`s, running `stamp_journal_tree`, and validating with `SOLSTONE_JOURNAL`, `SOLSTONE_JOURNAL_SOCKET`, and `SOLSTONE_CONVEY_PORT` all explicitly set to scratch values and no thinking provider).
- [`photogen/`](photogen/README.md): Gemini API (`gemini-nano-banana-2.1`) photo generation tool, 20-shot × 3-framing sample prompt set (`prompts_sample_round.json`), static HTML side-by-side review renderer, and unit tests (`photogen/tests/test_photogen.py`).
- [`tests/test_generator.py`](tests/test_generator.py): Pytest suite covering world data counts, loud failures on missing creative fields, contract checks, live Convey read-back, and committed-tree checkout `mtime` + `stamp.py` + year-level backdrop validation.
- Test fixtures (S027 specimen + § 7.7 row 17 photo with `[TEST-FIXTURE-PLACEHOLDER]` markers):
  - [`tests/fixtures/2025-03-15.md`](tests/fixtures/2025-03-15.md)
  - [`tests/fixtures/week.md`](tests/fixtures/week.md)

## Map, body and screen media

- Packed-day map stops use the planned reported visit for each dwell and keep fixes for the travel legs. Place names come from the § 4 gazetteer after grouping visits across separate dates with the product's distance rules.
- Heart rate is sampled every five minutes while awake and every half hour during the recorded sleep window. Travel and playhouse stays come from the day plans. The packed days also use the content segments to distinguish stretches at the desk, on foot and in conversation.
- Source names are stored as device descriptions keyed by the existing stream CIDs. The journal's own source and device wording still governs the labels it renders.
- Photos use `photos/year/install.json` and desk frames can use `photos/pages/install.json`. Both accept `by_segment` entries keyed `YYYY-MM-DD/<segment_key>`. Re-converting keeps valid JPEGs on disk. Desk frames without a JPEG keep their text and timing.
- Audio segments (`talk`, `calls`, `memos`) preserve any existing real `audio.flac` (`fLaC` header, >= 1024 bytes) and its aligned `audio.jsonl` duration/turn timings across re-converts (mirroring photo preservation; optional timing fallback from `audio/install.json`).
- Person portraits use `photos/faces/install.json`. Map a person folder slug to its 256-pixel-wide JPEG, for example `{"by_entity":{"anne_shakespeare":"photos/faces/images/anne_shakespeare.jpg"}}`. Install with `lived_in.py` and Pillow. The installer writes the confirmed face state and its JPEG, and anchors that face to the person's real activities so a connected agent can see it in each facet where the person appears.

## Serving a copy

Serve a copy, never the tree itself: the journal writes as it runs. Use the latest solstone (see the repo README on releases) and point every `solstone` command at the copy with `SOLSTONE_JOURNAL`, `SOLSTONE_JOURNAL_SOCKET` and `SOLSTONE_CONVEY_PORT`, so it never reaches another journal on the same computer. Configure no thinking provider, and use the browser timezone `Europe/London`.

1. Copy `build/journal/` into a scratch directory. Run `python3 tools/stamp.py --journal <copy>`, then `solstone journal indexer --rescan-full` and `solstone journal journal-stats`. The stats command writes the per-day facet measurements Home reads; `--no-cache` writes only the top-level aggregate.
2. Give the copy its own Convey port and its own runtime directory, mode 0700. Set `SOLSTONE_JOURNAL_SOCKET` to `journal.sock` inside it. Callosum uses `callosum.sock` beside it, so each copy needs its own directory.
3. `solstone journal convey --port <port> --journal <copy>` serves it to a browser. The full supervisor, `solstone journal start <port> --journal <copy> --direct-port <unused port> --no-spl --no-schedule --no-daily`, adds the local agent door. It needs an installation set up for this copy (`solstone journal setup --journal <copy> --accept-existing-journal --skip-models --skip-brain`), so run it under a separate `HOME` from any journal you use.
4. `python3 tools/read_back.py --journal <copy> --solstone-bin <binary>` checks the stored layers and search coverage on another fresh stamped copy. The read-back and the tests also need a `solstone-journal` checkout at the commit in [`manifest.json`](manifest.json): point `WILLIAM_SOLSTONE_REPO` at it. Run `python3 -m pytest tools/tests/` with Pillow installed for the portrait test.

### The identity key

The journal's link identity lives in `build/journal/link/ca/`. `cert.pem` and `state.json` are in the tree. `private.pem`, its signing key, is not distributed. Without it a copy serves, searches and reads as usual, and a local agent connects through the agents app's pairing code. Its mark shows as unavailable, though, and no device can pair with it; `lived_in.py`, `read_back.py`, and the committed-tree read-back test in `tools/tests/test_generator.py` also expect `private.pem` to be present.


## Usage

```bash
# 1. Generate the 365 day plans (2025.json, index.md, and 53 weekly markdown tables)
python3 tools/dayplan.py

# 2. Convert all 53 weeks (the 1 Jan week's reflection is keyed to Sun 29 Dec 2024)
python3 tools/converter.py --week 2025-01-01,2025-01-05,2025-01-12,2025-01-19,2025-01-26,2025-02-02,2025-02-09,2025-02-16,2025-02-23,2025-03-02,2025-03-09,2025-03-16,2025-03-23,2025-03-30,2025-04-06,2025-04-13,2025-04-20,2025-04-27,2025-05-04,2025-05-11,2025-05-18,2025-05-25,2025-06-01,2025-06-08,2025-06-15,2025-06-22,2025-06-29,2025-07-06,2025-07-13,2025-07-20,2025-07-27,2025-08-03,2025-08-10,2025-08-17,2025-08-24,2025-08-31,2025-09-07,2025-09-14,2025-09-21,2025-09-28,2025-10-05,2025-10-12,2025-10-19,2025-10-26,2025-11-02,2025-11-09,2025-11-16,2025-11-23,2025-11-30,2025-12-07,2025-12-14,2025-12-21,2025-12-28

# 3. Refresh backdrop calendar notes or seasonal sleep / map places without touching converted weeks
#    (--refresh-calendar is a converter.py flag; after the refresh it converts --week, default 2025-03-09)
python3 tools/converter.py --refresh-calendar --week 2025-03-09
python3 tools/backdrop.py --refresh-body-and-places --days 2025-08-25,2025-08-29

# 4. After a fresh git checkout, restore deterministic segment extract mtimes in one command
python3 tools/stamp.py

# 5. Install the lived-in layer and contextual imported files on the synthetic year
python3 tools/lived_in.py
python3 tools/imports.py

# 6. Validate the year tree in /var/tmp and build its search index there
python3 tools/read_back.py

# 7. Run the test suite
pytest tools/tests/ -v
```
