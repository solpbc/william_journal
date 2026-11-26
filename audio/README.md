# William Journal Audio (`audio/`)

Synthesized speech recordings, cast metadata, acoustic presets, ambient beds, and WeSpeaker voiceprints for **the william journal** (William Shakespeare's 1595, held on 2025 dates).

## Coverage

Across the journal's `1,075` transcript segments (`804` talks, `237` voice memos, `34` calls), **`303` segments (`1,953` turns, `182.44 min`, `185.52 MB`)** are backed by real `audio.flac` recordings under `build/journal/chronicle/<day>/<stream>/<segment>/audio.flac`, with matching `duration`, `timing.start/end`, and wall-clock `start` values in each segment's `audio.jsonl`:

| Stream | Recorded | Total in journal | Coverage | Acoustic presets |
|---|---:|---:|---:|---|
| `memos` (William voice notes) | `237` | `237` | `100%` | `212` `memo_room`, `25` `memo_walk` |
| `calls` (London calls) | `34` | `34` | `100%` | `34` `call_room` |
| `talk` (multi-speaker scenes) | `32` | `804` | `4.0%` | `16` `household_room`, `13` `theatre_hall`, `2` `country_walk`, `1` `bonfire_street` |
| **Total** | **`303`** | **`1,075`** | **`28.2%`** | `182.44 min`, `185.52 MB` (`16 kHz` mono FLAC L8) |

All `303` recordings are encoded as `16 kHz`, mono, 16-bit PCM FLAC (compression level `8`, source metadata stripped). Largest single file: `4.01 MB` (`20250201/talk/164500_840`).

## Files in `audio/`

| Path | What it holds |
|---|---|
| [`voices.json`](voices.json) | Cast registry for all `19` licensed stock voices (slug, display name, ElevenLabs Voice Library name and `voice_id`, character notes, corpus segment counts, wave). |
| [`voiceprints.json`](voiceprints.json) | Extracted `256`-d L2-normalized WeSpeaker ResNet34-256 centroids for all `19` speakers, the `19x19` pairwise centroid cosine matrix, held-out turn accuracy, and in-scene pair statistics. |
| [`install.json`](install.json) | Deterministic manifest of all `303` installed segments: preset, acoustic parameters, duration, byte size, SHA-256, and aligned turn timings. |
| [`batch-48.json`](batch-48.json) | Wave 1 selection (`48` transcripts across `10` primary cast speakers: `11` company, `10` household, `5` Stratford, `10` calls, `12` memos). |
| [`batch-wave2.json`](batch-wave2.json) | Wave 2 selection (`255` transcripts: remaining `225` memos, remaining `24` calls, and `6` multi-speaker talks introducing Wave 2 voices). |
| `ambience/*.mp3` | Four loopable non-voice 1595 ambient beds (`timber_hearth.mp3`, `wood_hall.mp3`, `country_lane.mp3`, `bonfire_night.mp3`) mixed ~30 dB below active speech. |

## Cast (19 Licensed Stock Voices)

Every voice is a licensed stock voice from the ElevenLabs Voice Library (`rate=1.0`, zero custom voice slots, cloning nobody). Metrics below are measured across all `303` final leveled FLACs by [`tools/voiceprint_eval.py`](../tools/voiceprint_eval.py):

| # | Slug | Character | Library Name | Voice ID | Wave | Segs | Speech (s) | Held-out Top-1 | Median Margin | Max Centroid Impostor |
|---:|---|---|---|---|---:|---:|---:|---:|---:|---|
| 1 | `william_shakespeare` | William Shakespeare | Daniel - Warm Southern British | `d1m8Ymi40kmfxA6QQi8F` | 1 | 303 | 5898.0 | 1070/1070 | +0.532 | +0.383 (`john_florio`) |
| 2 | `dorcas_ansell` | Mistress Dorcas Ansell | Esjai | `UWhYG4NgASy4ripg5Ov6` | 1 | 12 | 662.5 | 97/97 | +0.582 | +0.363 (`anne_shakespeare`) |
| 3 | `alse_pinder` | Alse Pinder | Amie - Easy going & friendly | `Ui0Q64wzShXAKGp2LDv2` | 1 | 10 | 217.1 | 48/48 | +0.626 | +0.256 (`anne_shakespeare`) |
| 4 | `john_heminges` | John Heminges | Adam - Steady, Rich and Round | `Gsndh0O5AnuI2Hj3YUlA` | 1 | 18 | 785.7 | 110/110 | +0.569 | +0.370 (`henry_carey_hunsdon`) |
| 5 | `richard_burbage` | Richard Burbage | Sterling - British Professional | `BEoudO57vUvMNWWJJ7nh` | 1 | 15 | 400.6 | 63/63 | +0.496 | +0.461 (`richard_field`) |
| 6 | `will_kemp` | Will Kemp | Daryl - Friendly & Conversational | `eco1uQaywu8bl5XXX7Cl` | 1 | 13 | 462.5 | 65/65 | +0.531 | +0.404 (`henry_wriothesley_southampton`) |
| 7 | `augustine_phillips` | Augustine Phillips | Ash - Relaxed | `7DPK3BeItL9bXzJuCOEn` | 1 | 8 | 126.9 | 23/23 | +0.579 | +0.344 (`gilbert_shakespeare`) |
| 8 | `anne_shakespeare` | Anne Shakespeare | Philippa - Clear British Narrator | `IbXTsH7MlHi5GQco8zZH` | 1 | 5 | 253.7 | 38/38 | +0.580 | +0.363 (`dorcas_ansell`) |
| 9 | `abel_garnish` | Abel Garnish | AK - British Well-Spoken Old Man | `y0SYydk17lMbUIUvSf3N` | 1 | 8 | 283.4 | 37/37 | +0.535 | +0.381 (`thomas_pope`) |
| 10 | `gillis_verbeke` | Gillis Verbeke | Kenneth - Neutral, Calm, and Natural | `i7G4u9tyZGel56RnYhXb` | 1 | 7 | 122.2 | 25/25 | +0.550 | +0.335 (`john_florio`) |
| 11 | `richard_field` | Richard Field | Tom | `5hZv9mAOcmcMt1TxA5Iz` | 2 | 6 | 284.1 | 43/43 | +0.487 | +0.461 (`richard_burbage`) |
| 12 | `gilbert_shakespeare` | Gilbert Shakespeare | Aaron - Friendly Warm British | `hXrCG2sVUeLC0DfTSHwH` | 2 | 6 | 284.4 | 53/53 | +0.508 | +0.353 (`richard_burbage`) |
| 13 | `john_florio` | John Florio | Luca - Clear Neutral Narration | `sp6F311QRVXR53QPGIgK` | 2 | 3 | 128.4 | 20/20 | +0.499 | +0.383 (`william_shakespeare`) |
| 14 | `cuthbert_burbage` | Cuthbert Burbage | Mark - Authentic, Natural British | `c6fGb09bcAfraocfEaPh` | 2 | 4 | 162.2 | 25/25 | +0.552 | +0.374 (`richard_field`) |
| 15 | `ambrose_kettleby` | Ambrose Kettleby | Cedric M - Slow Burn, Expressive Conversational Voice | `P6bTNc9ZMZitpFPNJFbo` | 2 | 4 | 208.8 | 25/25 | +0.605 | +0.343 (`henry_carey_hunsdon`) |
| 16 | `henry_wriothesley_southampton` | Henry Wriothesley, Earl of Southampton | Edmund - British Podcast Host | `bDTlr4ICxntY9qVWyL0o` | 2 | 1 | 44.0 | 7/7 | +0.522 | +0.404 (`will_kemp`) |
| 17 | `henry_carey_hunsdon` | Henry Carey, Lord Hunsdon | Julian - Deep, Rich and Mature | `7p1Ofvcwsv7UBPoFNcpI` | 2 | 1 | 114.0 | 11/11 | +0.574 | +0.370 (`john_heminges`) |
| 18 | `richard_quiney` | Richard Quiney | Alan - Warm, Scottish and Clear | `06Te1sUCUc98TG97R9be` | 2 | 3 | 172.6 | 27/27 | +0.581 | +0.332 (`william_shakespeare`) |
| 19 | `thomas_pope` | Thomas Pope | Dan - Deep and Authentic Storyteller | `2DwyWvJJS5LeWSltZbS6` | 2 | 2 | 39.0 | 6/6 | +0.491 | +0.381 (`abel_garnish`) |

## Voiceprints and WeSpeaker Evaluation

[`voiceprints.json`](voiceprints.json) stores the L2-normalized `256`-d WeSpeaker ResNet34-256 speaker centroids extracted directly from the installed `audio.flac` corpus using [`tools/voiceprint_eval.py`](../tools/voiceprint_eval.py).

The extractor replicates `solstone-journal`'s speaker-embedding pipeline:

- **Frontend:** `16 kHz` mono float32, 80-bin Kaldi log-mel filterbank (`20 Hz` to `8000 Hz`, `400`-sample / `25 ms` Povey window, `160`-sample / `10 ms` shift, pre-emphasis `0.97`, per-utterance CMN), matching `core/crates/solstone-core-speakers/src/filterbank.rs`. Parity verified against `core/fixtures/speaker_filterbank.json` (`max_abs_diff = 0.000513`).
- **Model:** `core/models/assets/wespeaker-resnet34-256.onnx` (`256`-d L2-normalized embeddings).
- **Reference thresholds** (from `core/crates/solstone-core-speaker-id/src/{calibration.rs,run_numbers.rs}` and `core/crates/solstone-core-speaker-resolve/src/candidate_tracker.rs`): `ACOUSTIC_HIGH = 0.36`, `OWNER_THRESHOLD = 0.43`, `CONSOLIDATE_MERGE_THRESHOLD = 0.65`, `RUN_MATCH = 0.72`.
- **Evaluation protocol:** Strict held-out top-1 turn accuracy for every turn `>= 1.5 s`: leave-one-segment-out centroid for speakers present in `>= 2` segments, and leave-one-turn-out centroid for single-segment speakers (`henry_wriothesley_southampton`, `henry_carey_hunsdon`) so no turn is scored against a centroid containing itself.

Corpus results across all `303` recordings and `19` speakers:

- **Held-out top-1 turn accuracy:** `1,793 / 1,793` (`100.00%`, `0` mismatches).
- **Per-speaker median margins:** `+0.487` to `+0.626`.
- **In-scene co-occurring speaker pairs (`241` pairs):** median `0.2086`, p90 `0.3072`, `235 / 241 < 0.36`, `240 / 241 < 0.43`, max `0.4345` (`john_florio` vs `william_shakespeare` in `20250318/calls/110000_240`).
- **Centroid pairwise cosine (`171` pairs):** `170 / 171 <= 0.4036`; single pair above `0.43` is `richard_burbage` vs `richard_field` at `0.4610` (they do not co-occur in a scene, and score `63/63` and `43/43` held-out top-1).

To re-run the evaluation and regenerate `audio/voiceprints.json` against a local `solstone-journal` checkout:

```bash
WILLIAM_SOLSTONE_REPO=~/projects/solstone-journal \
  uv run --with onnxruntime --with numpy python3 tools/voiceprint_eval.py
```

## Synthesis Pipeline and Design Notes

[`tools/audiogen.py`](../tools/audiogen.py) synthesizes segments from `build/journal/chronicle/<day>/<stream>/<segment>/audio.jsonl` and installs `audio.flac` plus aligned turn timings:

1. **Model and endpoints:** `eleven_v4` (`text-to-dialogue/convert_with_timestamps` for multi-turn chunks; `text-to-speech/convert_with_timestamps` for single-turn chunks). Turns are chunked at `<= 1,720` characters and stitched with `0.35 s` gaps. Restrained delivery cues (`SPEAKER_CUES` in `tools/audiogen.py`) are sent on the first turn of each chunk and every sixth turn thereafter to keep pacing conversational; cues are never written back into `audio.jsonl`.
2. **Stock Voice Library vs. Voice Design:** Early testing with ElevenLabs Voice Design produced voices that clustered tightly in WeSpeaker space (`0.47` to `0.819` inter-speaker cosine in multi-speaker dialogue). Casting distinct real-actor voices from the Voice Library eliminated that clustering.
3. **Room acoustics and non-voice ambient beds:** Each segment uses ElevenLabs built-in `--audio-effects` (`small_room`, `big_room`, or `street`) for room impulse response, layered with one of four loopable non-voice 1595 ambient beds in `audio/ambience/` calibrated ~30 dB below active speech RMS (`-52` to `-55 dB` mean for room, hall, and lane; `-67.5 dB` mean for `bonfire_night.mp3`). Built-in background noise presets containing human chatter (such as `cafe`) contaminate WeSpeaker embeddings across speakers (shifting cross-speaker cosine from `0.09` to `0.46`) and must not be used.
4. **Per-turn active-RMS leveling:** Native Voice Library actors vary by up to `18.4 dB` in output loudness, making characters in the same room sound closer or farther from the microphone. `tools/audiogen.py` measures active speech RMS (top 60% of `20 ms` frames) per turn, applies per-turn gain toward `-22.0 dBFS` (William) and `-23.0 dBFS` (other speakers), clamps gain to `[-6.0, +16.0] dB`, crossfades turn boundaries linearly over `40 ms`, and passes speech through a soft peak limiter (`alimiter=limit=0.89`) before mixing the continuous ambient bed. Across all `303` recordings and `19` speakers, median active speech RMS spread is `1.94 dB` (`-23.94` to `-22.00 dBFS`), with no measurable WeSpeaker impact.
5. **Checking for `eleven_v4` semantic voice-carry:** In long multi-speaker dialogues where consecutive turns share a tight parallel structure (such as a day-by-day schedule list), `eleven_v4` `text-to-dialogue` can occasionally carry the previous speaker's voice into the next turn. Always run `tools/voiceprint_eval.py` after synthesizing a batch: any speaker-carry glitch surfaces immediately as a held-out turn mismatch and is fixed by splitting the chunk right before that turn.
6. **Preservation on re-convert:** `tools/converter.py` preserves any valid `audio.flac` (`fLaC` magic, `>= 1024` bytes) and its aligned `audio.jsonl` duration and turn timings when weeks are re-converted, with `audio/install.json` as an optional fallback timing source.

## Generating Additional Segments

### Adding a new voice

1. Browse licensed `rate=1.0` stock voices in the ElevenLabs Voice Library matching the character's age, accent, and register (no voice cloning).
2. Pre-screen preview clips in WeSpeaker against all existing `centroid_256` vectors in [`voiceprints.json`](voiceprints.json), targeting max cosine `< 0.38` on previews.
3. Synthesize a `10` to `15 s` test line using `eleven_v4` (raw library previews can drift `0.05` to `0.10` in cosine after `eleven_v4` synthesis) and verify the synthesized embedding stays `< 0.43` against all existing centroids (`< 0.36` against William and frequent co-speakers).
4. Audit the synthesized clip by ear for naturalness and character fit.
5. Append the voice entry to [`voices.json`](voices.json) and add a delivery cue in `SPEAKER_CUES` inside [`tools/audiogen.py`](../tools/audiogen.py).

### Running a synthesis batch

1. Create a batch JSON file following the shape of [`batch-wave2.json`](batch-wave2.json), listing each segment's `rel`, `category`, optional `preset` (`memo_room`, `memo_walk`, `call_room`, `household_room`, `theatre_hall`, `country_walk`, `bonfire_street`), `speakers`, `turns`, `chars`, and `note`.
2. Ensure `ffmpeg`, `ffprobe`, the ElevenLabs CLI (`elevenlabs`, authenticated via your own `ELEVENLABS_API_KEY`), and a local `solstone-journal` checkout (`WILLIAM_SOLSTONE_REPO`, defaulting to `~/projects/solstone-journal`, needed for `audio.jsonl` contract checks) are available.
3. Run the resumable synthesizer against your new batch file (`--cache-dir` caches chunk responses so interrupted runs do not re-synthesize finished chunks, and `--only <rel>` scopes a run to individual segments; `audiogen.py` does not skip segments already present in `audio/install.json`, so do not pass an already-shipped batch file unless you intend to re-synthesize it; finished runs merge into `audio/install.json` and run `tools/stamp.py` automatically):

```bash
WILLIAM_SOLSTONE_REPO=~/projects/solstone-journal \
  python3 tools/audiogen.py \
  --batch audio/batch-custom.json \
  --workers 4
```


4. Re-run WeSpeaker evaluation and verify `0` unexpected mismatches:

```bash
WILLIAM_SOLSTONE_REPO=~/projects/solstone-journal \
  uv run --with onnxruntime --with numpy python3 tools/voiceprint_eval.py
```

5. Verify `audio.jsonl` contract checks and re-convert audio preservation (see [`../tools/README.md`](../tools/README.md) for prerequisites of the full test suite):

```bash
WILLIAM_SOLSTONE_REPO=~/projects/solstone-journal \
  python3 -m pytest tools/tests/test_generator.py \
  -k "test_reconvert_leaves_real_audio_and_timings_intact or test_convert_fixture_and_contract_check"
```
