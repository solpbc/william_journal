# William Journal Photo Generation Tool (`tools/photogen/`)

Re-runnable photo generation and side-by-side review harness for **the william journal** (``).

Given a prompt set JSON (such as [`prompts_sample_round.json`](prompts_sample_round.json)), [`photogen.py`](photogen.py):

1. Reads a Gemini API key at runtime from `GEMINI_API_KEY`, or from a key file named by `--key-file` or `WILLIAM_GEMINI_KEY_FILE` (and redacts it from any error/log output; the key is never printed, logged, or written to disk).
2. Calls the latest Google Gemini image generation model (`gemini-nano-banana-2.1`) via `POST https://generativelanguage.googleapis.com/v1beta/models/gemini-nano-banana-2.1:generateContent`.
3. Enforces hard caps on total image count (`--max-images`, default `60`) and USD spend (`--budget-usd`, default `$25.00`). The spend cap covers everything paid into the `--out` directory across runs, kept in `manifest.json` as `spent_usd`: an image you delete or regenerate still counts, so a retry passes the job's whole budget again, not what remains. `total_cost_usd` is only the keepers' cost. A manifest from before 2026-11-23 has no `spent_usd`, and its keepers' total stands in for it.
4. Writes generated JPEGs (`images/*.jpg`), a full provenance and token/cost manifest (`manifest.json`), and a self-contained static HTML side-by-side comparison page (`index.html`) under the requested `--out` directory (for example, `photos/samples/261117-round1/`).
5. If raw generated images exceed `--max-repo-mb` (default `50.0` MB), preserves the untouched full-resolution originals in `/var/tmp/william-photogen-<run>/` (with a `/var/tmp/.sweep-protect.william-photogen-<run>` sidecar and `original_path` recorded in `manifest.json`) and commits optimized `1200x896` JPEGs in the repo.

## Model Verification (Checked 2026-11-17)

- **Model ID:** `gemini-nano-banana-2.1` (*Nano Banana 2.1*, latest update October 2026)
- **How checked (2026-11-17):**
  1. Checked Google's official Gemini API documentation (`https://ai.google.dev/gemini-api/docs/image-generation.md.txt`, `https://ai.google.dev/gemini-api/docs/models/gemini-nano-banana-2.1.md.txt`, `https://ai.google.dev/gemini-api/docs/pricing.md.txt`, and `https://ai.google.dev/gemini-api/docs/imagen.md.txt`), which lists `gemini-nano-banana-2.1` (Oct 2026) as the latest and primary recommended image generation model—superseding `gemini-3.1-flash-image` (Feb 2026), `gemini-3.1-flash-lite-image` (Jun 2026), `gemini-3-pro-image` (Nov 2025), deprecated `gemini-2.5-flash-image`, and shut-down legacy Imagen endpoints.
  2. Verified live model availability via `GET https://generativelanguage.googleapis.com/v1beta/models` and `POST https://generativelanguage.googleapis.com/v1beta/models/gemini-nano-banana-2.1:generateContent` (`supportedGenerationMethods: ["generateContent", "countTokens"]`).
- **Published Paid-Tier Pricing (`gemini-nano-banana-2.1`):**
  - Input tokens: `$1.50 / 1M tokens`
  - Image output tokens: `$30.00 / 1M tokens` (`1,120` tokens per `1K` image = `$0.0336` / image)
  - Text & thinking output tokens: `$7.50 / 1M tokens` (~`800–1,050` thinking tokens per image = `~$0.006–$0.008`)
  - Total per `1K` (`1200x896`, `4:3`) image: **`~$0.041–$0.043`** (`~$2.50` for 60 sample images; `~$6.10` for all 146 photos in the year).

## Files

- [`photogen.py`](photogen.py) — CLI generator, budget/size guard, and static HTML review renderer.
- [`prompts_sample_round.json`](prompts_sample_round.json) — 20 varied scenes (`S01`–`S20`) across the accepted 1595 year × 3 style framings (`A`, `B`, `C`) = 60 sample images (`#1`–`#60`).
- [`prompts_year.json`](prompts_year.json) — one Framing C prompt per photo segment in the year, built by [`build_year_prompts.py`](build_year_prompts.py) from the segment caption plus the matching § 7.7 / § 8.6 lines.
- [`review_year.py`](review_year.py) — one Gemini vision check per generated year image, resumable, with a spend ceiling.
- [`year_sheet.py`](year_sheet.py) — the date-grouped contact sheet, `photos/year/install.json`, and the copy into `build/journal`.
- [`build_page_prompts.py`](build_page_prompts.py) — one Framing C prompt per desk-frame segment on the three packed days, naming the timed frame each picture uses.
- [`pages_sheet.py`](pages_sheet.py) — the day-grouped contact sheet and `photos/pages/install.json`. It does not copy into the journal.
- [`build_face_prompts.py`](build_face_prompts.py) — one Framing C head-and-shoulders prompt per person William meets in 1595, and the face/none list in `../../photos/faces/reasoning.md`.
- [`prompts_faces.json`](prompts_faces.json) — the prompt set that builder writes.
- [`review_faces.py`](review_faces.py) — one vision check per face against § 3, then one check of the set for a reused face.
- [`faces_sheet.py`](faces_sheet.py) — the 256-pixel crops, `photos/faces/install.json`, and the contact sheet.
- [`tests/test_photogen.py`](tests/test_photogen.py) — Unit tests covering key-file parsing, secret redaction, token/cost calculation, canon day-file verification for all 20 sample shots, budget/image-count guards, downscaling + `/var/tmp` original preservation, and mocked end-to-end generation.

## Usage

```bash
# Generate the 60-image sample round (resumable by default; pass --overwrite to regenerate all)
python3 tools/photogen/photogen.py \
  --prompts tools/photogen/prompts_sample_round.json \
  --out photos/samples/261117-round1 \
  --workers 6

# Re-render index.html from an existing manifest.json without calling the Gemini API
python3 tools/photogen/photogen.py \
  --out photos/samples/261117-round1 \
  --render-only

# Run unit tests
pytest tools/photogen/tests/test_photogen.py -v
```
