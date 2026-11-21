# Contextual Imported Files (`content/imports/`)

This folder holds 17 source files (producing 18 segments across 11 days in 2025) that populate the imported-file streams in the William journal alongside his meetings, calls, voice memos, commonplace notes, desk pages, calendar, location, body, and phone photos.

## Contents

- [`manifest.json`](manifest.json) defines the date, time, stream, kind, place, facet, people, sense summary, activity record, and (for the PDFs and screenshots) extracted text or image descriptions across the 18 items.
- `files/` holds the 17 source files:
  - Four personal notes (`import.text`, kind `notes`): 15 March Whitehall warrant reckoning, 12 May Theatre ground lease figures, 7 July summer closure vote, and 22 October vial scene working notes.
  - Three text documents (`import.text`, kind `documents`): 17 May *Richard II* Act III Scene II working draft, 7 July company summer reckoning memorandum, and 11 November *Romeo and Juliet* Act II Scene II reading extract.
  - Three timed transcripts (`import.text`, kind `transcripts`): 12 May tiring-house lease exchange, 7 July post-vote exchange, and 13 November steps outside St John's Gate after Edmund Tilney's licence.
  - Three PDFs (`import.document`): 15 March Greenwich Chamber warrant, 12 May Theatre ground lease heads, and 15 September Guildhall copyist's digest of the Lord Mayor's petition to the Privy Council.
  - One Evernote export (`import.evernote`, two notes): 16 August Chapel Street walk in Stratford and 22 November notes on Will Kemp reading the mechanicals casting sheets.
  - Three screenshots (`import.image`, kind `screen_text`): 15 March Heminges's warrant reckoning slate, 15 May damp Plutarch proof sheet at Richard Field's press, and 15 September Bishopsgate playbill for *The Knave*. Each PNG carries `Software=gnome-screenshot` metadata so solstone's importer classifies it as screen text.

## Installing

Run [`../../tools/imports.py`](../../tools/imports.py) after conversion, pointing `--solstone-repo` or `WILLIAM_SOLSTONE_REPO` at a `solstone-journal` checkout (defaults to `~/projects/solstone-journal`) for schema validation:

```bash
python3 tools/imports.py --journal build/journal --solstone-repo /path/to/solstone-journal
```

The installer writes each segment's extract files, schema-validated `talents/` outputs, health receipts, facet activities and daily entities, and `imports/` publication records, rebuilds stream chains, and stamps segment `mtime`s. Re-running it is idempotent.
