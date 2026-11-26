# William's desktop

This folder imagines the computer William might have had on his board in 1595, and takes screenshots of it at any moment of his year. A screenshot is the picture of a desk frame: what was on his screen while he wrote, read, reckoned or talked.

What changes from moment to moment is assembled from the journal: the frame's legible text, his letters, his account lines, his calls, and his marks in the almanack. The period furniture (the almanack's weather and physick, the carrier days, the stalls of Paul's) is fixed in `data.js`, along with his commonplace notes, which are shown up to that day. The year's calendar sits on the almanack whole. A frame with `surface: glass` opens The Glass on the call he was in. A frame with `surface: commonplace` opens the Commonplace Book on that frame's lines. A proof opens on the bookwheel. A frame with nothing legible still opens its cabinet. A screenshot holds only what William would have seen and used. Labels, captions and staging stay outside the picture.

## The desktop

Open `index.html` in a browser to use it. It shows the evening of Wednesday 22 October. Add `?quiet=1` to keep the evening's ambient note from arriving.

- **Home is a memory theatre.** It has eight gangways, one for each of the seven planets and an eighth for the fixed stars. Each gangway opens one cabinet and shows that cabinet's state underneath: the sheet on the board, an unread letter or the next carrier, the last line in the account book, and so on.
- **The stage** gathers every open cabinet, shrunk and set apart. Touch it again, or press Esc, to leave. Open cabinets burn as lamps on the stage.
- **The dial** in the corner is a clock and calendar. It shows the 24 hours, the sun's hand, the moon and the day, and touching it opens the almanack.
- **The sky follows the hour:** night, dawn, the painted day with the sun on its arc, then dusk, from London's sunrise and sunset on that day.

The cabinets:

| Gangway | Cabinet | What it is |
|---|---|---|
| ☽ Luna | Coffer | bundles of papers, and two locks on the private leaves |
| ☿ Mercurius | Letters | his letters by correspondent, sent by carrier, by boy or by hand |
| ♀ Venus | Commonplace Book | notes under his headings |
| ☉ Sol | Almanack | the month, with his calendar, the moon and his own marks |
| ♂ Mars | Foul Papers | drafts, his tables, parts and plots |
| ♃ Iupiter | Bookwheel | books, bills and pamphlets; an address is a shop sign |
| ♄ Saturnus | Account Book | his lines in pounds, shillings and pence |
| ✶ Stellatum | The Glass | calls, face to face; his own glass shows no face |

## Taking screenshots

Run these from the repo root. You need Python 3, [uv](https://docs.astral.sh/uv/), and a Chromium. The script uses `/usr/bin/google-chrome` if it is there. Otherwise run `uv run --with playwright playwright install chromium` once.

```bash
python3 desktop/feed.py                                                     # rebuild the feed from build/journal
uv run --with playwright python desktop/shoot.py frame 2025-10-22/100800_420  # one desk frame
uv run --with playwright python desktop/shoot.py call 2025-09-16/165000_240   # one call, in the Glass
uv run --with playwright python desktop/shoot.py frames --day 2025-10-22      # every desk frame on a day
uv run --with playwright python desktop/shoot.py check                       # render two and fail on any page error
```

A frame or call is named `<day>/<segment>`, after its folder: `build/journal/chronicle/<YYYYMMDD>/desk/<segment>/` or `.../calls/<segment>/`. Screenshots go to `desktop/out/`, at 1440 × 900.

**Installing a screenshot as the frame's picture:** add `--install`. It writes a JPEG to `photos/pages/images/screen_<day>_<segment>.jpg` and its `by_segment` entry to `photos/pages/install.json`, so a re-convert (`tools/converter.py`) keeps it. It also writes the segment's `screenshot_screen.jpg` in `build/journal`.

To see a moment in the browser, open `index.html?frame=<day>/<segment>` or `index.html?call=<day>/<segment>`. If you have used the desktop in that browser, add `&reset=1` so its saved state does not carry in (it clears that state).

## How a moment is put together

`feed.py` reads the journal into `feed.js`, and `stage.js` uses the feed to set the desktop for one moment:

- **The frame's surface** decides which cabinet is in front. The surface comes from the frame's `talents/screen.json` ("Shown on …"). The mapping:
  - `draft`, `tables`, `part` and `plot` → Foul Papers
  - `ledger` → Account Book
  - `letter` → Letters
  - `book`, `bill`, `pamphlet` and `proof` → Bookwheel
  - `almanac` → Almanack
  - `commonplace` → Commonplace Book
  - `glass` → The Glass, showing the call he was on at that time
  - Where that line is missing, the activity line sets letter, almanac, bill or playbill, ledger (also account, coffer or reckon), tables, plot, part or roll, and book when it names Chaucer, Holinshed, Plutarch, Ovid or reading. A miss opens as Foul Papers.
- **The frame's legible text** (`talents/screen_text.md`) is what the front cabinet shows.
- **The rest of the desk** comes from the journal up to that moment:
  - the board holds the latest state of his most recent works
  - the account book holds his most recent lines
  - letters are grouped by correspondent, and when the frame is a letter he is writing, that day's sheets of it sit in the compose box
  - the almanack holds the year's calendar whole, and his own marks up to that moment
  - when a different cabinet was out earlier that day, it stays open behind the front one
- **The time and sky** come from the frame's segment.

To make a screen richer, make the journal richer: write more of what was legible into the frame in `content/` (see `content/FORMAT.md`), re-convert it into `build/journal` with `tools/converter.py` (see `tools/README.md`), run `feed.py`, and shoot again. Faces in the Glass are each person's `build/journal/entities/<id>/photo.jpg`.

## Files

- `index.html`: the desktop: its look, the theatre, the stage, the dial and the sky
- `core.js`: the windows and the eight cabinets
- `stage.js`: sets one moment from the feed
- `feed.py` and `feed.js`: the feed builder and its output
- `data.js`: the evening of 22 October, and the fixed furniture every moment shares
- `base.css`: fonts and cabinet layout
- `shoot.py`: screenshots and installs
- `fonts/`: Cinzel, EB Garamond and UnifrakturMaguntia, under the SIL Open Font License (`OFL-*.txt`)
