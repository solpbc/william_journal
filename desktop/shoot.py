#!/usr/bin/env python3
"""Screenshot William's desktop at any moment of his year.

    uv run --with playwright python desktop/shoot.py frame 2025-10-22/100800_420
    uv run --with playwright python desktop/shoot.py call 2025-09-16/165000_240
    uv run --with playwright python desktop/shoot.py frame 2025-10-22/100800_420 --install
    uv run --with playwright python desktop/shoot.py frames [--day 2025-10-22] [--photo-frames] [--install]
    uv run --with playwright python desktop/shoot.py check

frame   one desk frame, by <day>/<segment> (the folder under build/journal/chronicle/<YYYYMMDD>/desk/)
call    one call, by <day>/<segment> under .../calls/; the Glass, mid-call
frames  every desk frame the feed knows, or one --day of them; --photo-frames keeps only
        the frames that already have a page image
check   render one frame and one call and fail on any page error

Output goes to desktop/out/<kind>-<day>-<segment>.png unless --out names a file.
--install also writes the render as the frame's picture: a JPEG in photos/pages/images/,
its by_segment entry in photos/pages/install.json (so a re-convert keeps it), and the
segment's screenshot_screen.jpg in build/journal. Run desktop/feed.py first if the journal changed.
Chrome: /usr/bin/google-chrome when present, otherwise Playwright's own Chromium
(`uv run --with playwright playwright install chromium`).
"""
import argparse, asyncio, json, os, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
PAGES = ROOT / "photos/pages"
VIEW = {"width": 1440, "height": 900}


def feed():
    s = (HERE / "feed.js").read_text()
    return json.loads(s[s.index("=") + 1:].rstrip().rstrip(";"))


async def render(targets, out=None, install=False):
    from playwright.async_api import async_playwright
    chrome = "/usr/bin/google-chrome" if os.path.exists("/usr/bin/google-chrome") else None
    errors = 0
    async with async_playwright() as pw:
        b = await pw.chromium.launch(executable_path=chrome, args=["--no-sandbox", "--allow-file-access-from-files"])
        for kind, ref in targets:
            p = await (await b.new_context(viewport=VIEW)).new_page()
            errs = []
            p.on("pageerror", lambda e: errs.append(str(e)))
            await p.goto((HERE / "index.html").as_uri() + f"?{kind}={ref}&quiet=1")
            await p.wait_for_timeout(1500)
            day, seg = ref.split("/")
            name = f"{kind}-{day}-{seg}"
            dest = pathlib.Path(out) if out else HERE / "out" / f"{name}.png"
            dest.parent.mkdir(parents=True, exist_ok=True)
            await p.screenshot(path=str(dest))
            if install and kind == "frame":
                rel = f"photos/pages/images/screen_{day}_{seg}.jpg"
                await p.screenshot(path=str(ROOT / rel), type="jpeg", quality=88)
                inst = json.loads((PAGES / "install.json").read_text())
                inst.setdefault("by_segment", {})[ref] = rel
                (PAGES / "install.json").write_text(json.dumps(inst, indent=2, ensure_ascii=False) + "\n")
                seg_dir = ROOT / "build/journal/chronicle" / day.replace("-", "") / "desk" / seg
                if seg_dir.exists():
                    (seg_dir / "page_screen.jpg").unlink(missing_ok=True)
                    (seg_dir / "screenshot_screen.jpg").write_bytes((ROOT / rel).read_bytes())
            errors += bool(errs)
            print(name, "page errors: " + "; ".join(errs) if errs else "ok", dest)
            await p.context.close()
        await b.close()
    return errors


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["frame", "call", "frames", "check"])
    ap.add_argument("ref", nargs="?", help="<day>/<segment>, e.g. 2025-10-22/100800_420")
    ap.add_argument("--out"); ap.add_argument("--install", action="store_true")
    ap.add_argument("--day"); ap.add_argument("--photo-frames", action="store_true")
    a = ap.parse_args()
    if a.what in ("frame", "call"):
        if not a.ref:
            ap.error("give <day>/<segment>")
        targets = [(a.what, a.ref)]
    elif a.what == "frames":
        F = feed()["frames"]
        targets = [("frame", f"{f['day']}/{f['seg']}") for f in F
                   if f["surface"] not in (None, "stage") and (not a.day or f["day"] == a.day) and (not a.photo_frames or f["photo"])]
    else:
        targets = [("frame", "2025-10-22/100800_420"), ("call", "2025-09-16/165000_240")]
    n = asyncio.run(render(targets, a.out if len(targets) == 1 else None, a.install))
    sys.exit(1 if n else 0)


if __name__ == "__main__":
    main()
