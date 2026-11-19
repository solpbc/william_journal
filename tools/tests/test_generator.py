# SPDX-License-Identifier: CC-BY-NC-4.0
# Copyright (c) 2026 sol pbc

"""Tests for the William journal backdrop generator, converter, and schema contracts."""

from __future__ import annotations

import importlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from datetime import datetime

import pytest


def _load_tools():
    tools_dir = Path(__file__).resolve().parents[1]
    pkg_name = "william_journal_tools"
    if pkg_name not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            pkg_name,
            tools_dir / "__init__.py",
            submodule_search_locations=[str(tools_dir)],
        )
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        sys.modules[pkg_name] = mod
        spec.loader.exec_module(mod)

    backdrop = importlib.import_module(f"{pkg_name}.backdrop")
    contracts = importlib.import_module(f"{pkg_name}.contracts")
    converter = importlib.import_module(f"{pkg_name}.converter")
    dayplan = importlib.import_module(f"{pkg_name}.dayplan")
    stamp = importlib.import_module(f"{pkg_name}.stamp")
    world_data = importlib.import_module(f"{pkg_name}.world_data")
    return backdrop, contracts, converter, dayplan, stamp, world_data


backdrop, contracts, converter, dayplan, stamp, world_data = _load_tools()

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
PROJECT_DIR = Path(__file__).resolve().parents[2]
BACKDROP_BUILD_DIR = PROJECT_DIR / "build" / "journal"
SOLSTONE_REPO = Path(os.environ.get("WILLIAM_SOLSTONE_REPO") or Path.home() / "projects" / "solstone-journal")
_RUNTIME_SOLSTONE_BIN = Path("/var/tmp/william-journal-runtime/prefix/current/bin/solstone")
SOLSTONE_BIN = (
    Path(os.environ["WILLIAM_SOLSTONE_BIN"])
    if "WILLIAM_SOLSTONE_BIN" in os.environ
    else _RUNTIME_SOLSTONE_BIN
    if _RUNTIME_SOLSTONE_BIN.is_file()
    else SOLSTONE_REPO / "core" / "target" / "debug" / "solstone"
)


def test_world_data_counts() -> None:
    assert len(world_data.CANON_CAST) == 71
    assert any(c.slug == "william_shakespeare" and c.is_principal for c in world_data.CANON_CAST)
    assert sum(1 for c in world_data.CANON_CAST if c.is_principal) == 1
    assert len(world_data.FACET_EXTRA_ENTITIES) == 16
    assert len(world_data.FACET_DEFINITIONS) == 4
    assert set(world_data.FACET_DEFINITIONS.keys()) == {"company", "writing", "household", "stratford"}


_UUID_V4 = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def test_facet_ids_are_fixed_and_well_formed(tmp_path: Path) -> None:
    """Each facet keeps one UUIDv4, in the generator and in the committed tree."""
    seen = set()
    for slug, fdef in world_data.FACET_DEFINITIONS.items():
        facet_id = fdef["id"]
        assert _UUID_V4.fullmatch(facet_id), slug
        assert facet_id not in seen
        seen.add(facet_id)
        stored = json.loads((BACKDROP_BUILD_DIR / "facets" / slug / "facet.json").read_text())
        assert stored["id"] == facet_id

    journal = tmp_path / "journal"
    backdrop.write_entities_and_facets(journal)
    for slug, fdef in world_data.FACET_DEFINITIONS.items():
        written = json.loads((journal / "facets" / slug / "facet.json").read_text())
        assert written["id"] == fdef["id"]


def test_face_manifest_writes_the_confirmed_state_and_its_jpeg(tmp_path: Path) -> None:
    from PIL import Image
    from william_journal_tools.lived_in import install_faces

    journal = tmp_path / "journal"
    entity = journal / "entities" / "anne_shakespeare"
    entity.mkdir(parents=True)
    (entity / "entity.json").write_text('{"id":"anne_shakespeare","type":"Person"}')
    assert install_faces(journal, tmp_path) == 0

    photos = tmp_path / "photos" / "faces"
    photos.mkdir(parents=True)
    image = photos / "fixture.jpg"
    Image.new("RGB", (256, 256), "gray").save(image, format="JPEG")
    (photos / "install.json").write_text(
        '{"by_entity":{"anne_shakespeare":"photos/faces/fixture.jpg"}}'
    )
    assert install_faces(journal, tmp_path) == 1
    photo = json.loads((entity / "faces_state.json").read_text())["photo"]
    assert bytes(photo["jpeg"]) == (entity / "photo.jpg").read_bytes() == image.read_bytes()
    assert photo["face"]["metadata"]["source_name"] == "anne_shakespeare"
    assert len(photo["face"]["embedding"]) == photo["encoder"]["width"] == 128


def test_parse_fixture_day_and_week() -> None:
    day_spec = converter.parse_day_markdown(FIXTURES_DIR / "2025-03-15.md")
    assert day_spec.day_iso == "2025-03-15"
    assert day_spec.wakes == "ansell_house"
    assert day_spec.sleeps == "ansell_house"
    assert day_spec.day_type == "Boat day"
    assert len(day_spec.segments) == 4

    s027_meeting = day_spec.segments[0]
    assert s027_meeting.kind == "meeting"
    assert s027_meeting.segment_key == "114000_420"
    assert len(s027_meeting.transcript_lines) == 53
    assert s027_meeting.transcript_lines[0].speaker == "john_heminges"
    assert "A warrant has no weight" in s027_meeting.transcript_lines[0].text

    s027_photo = day_spec.segments[1]
    assert s027_photo.kind == "photo"
    assert "Twenty pounds in gold and silver" in s027_photo.photo_text

    week_spec = converter.parse_week_markdown(FIXTURES_DIR / "week.md")
    assert week_spec.sunday_iso == "2025-03-09"
    assert len(week_spec.memories) == 1
    assert len(week_spec.said) == 3
    assert len(week_spec.observations) == 2


def test_converter_fails_loudly_on_missing_creative_fields(tmp_path: Path) -> None:
    src = (FIXTURES_DIR / "2025-03-15.md").read_text(encoding="utf-8")

    # 1. Missing Pulse one sentence
    bad_pulse = src.replace("- one sentence:", "- omitted:")
    p1 = tmp_path / "2025-03-15.md"
    p1.write_text(bad_pulse, encoding="utf-8")
    with pytest.raises(converter.ContentFormatError, match="Pulse"):
        converter.parse_day_markdown(p1)

    # 2. Missing Sense summary
    bad_sense = src.replace("- summary:", "- missing_summary:", 1)
    p1.write_text(bad_sense, encoding="utf-8")
    with pytest.raises(converter.ContentFormatError, match="summary"):
        converter.parse_day_markdown(p1)

    # 3. Missing Activity story
    bad_story = src.replace("- story:", "- missing_story:", 1)
    p1.write_text(bad_story, encoding="utf-8")
    with pytest.raises(converter.ContentFormatError, match="story"):
        converter.parse_day_markdown(p1)

    # 4. Unknown speaker slug
    bad_speaker = src.replace("[00:00] john_heminges:", "[00:00] sir_francis_drake:", 1)
    p1.write_text(bad_speaker, encoding="utf-8")
    with pytest.raises(converter.ContentFormatError, match="unknown speaker slug"):
        converter.parse_day_markdown(p1)


def _stage_march_week_backdrop(dest: Path) -> None:
    backdrop.generate_backdrop(
        output_journal=dest,
        dayplan_md=PROJECT_DIR / "content" / "weeks" / "2025-03-09" / "dayplan.md",
        solstone_repo=SOLSTONE_REPO,
    )


def test_convert_fixture_and_contract_check(tmp_path: Path) -> None:
    scratch_journal = tmp_path / "journal"
    _stage_march_week_backdrop(scratch_journal)

    summary = converter.convert_content_to_journal(
        content_dir=FIXTURES_DIR,
        journal_dir=scratch_journal,
        solstone_repo=SOLSTONE_REPO,
    )
    assert summary["days_converted"] == 1
    assert summary["segments_converted"] == 4
    assert summary["week_converted"] == "2025-03-09"

    # Verify config has no thinking provider or lane
    cfg = json.loads((scratch_journal / "config" / "journal.json").read_text(encoding="utf-8"))
    assert "thinking" not in cfg
    assert "providers" not in cfg
    assert "lanes" not in cfg

    # Verify S027 meeting files and sense projections
    seg_dir = scratch_journal / "chronicle" / "20250315" / "talk" / "114000_420"
    assert (seg_dir / "audio.jsonl").is_file()
    assert (seg_dir / "stream.json").is_file()
    talents_dir = seg_dir / "talents"
    for expected_talent_file in (
        "speaker_labels.json",
        "sense.json",
        "activity.md",
        "facets.json",
        "density.json",
        "sense.md",
        "speakers.json",
        "change.json",
        "topics.md",
        "documents.json",
    ):
        assert (talents_dir / expected_talent_file).is_file(), f"Missing {expected_talent_file}"

    # Verify photo segment files (a phone share, not a screen segment)
    photo_dir = scratch_journal / "chronicle" / "20250315" / "import.image" / "114800_0"
    assert (photo_dir / "original.jpg").is_file()
    assert (photo_dir / "image_meta.json").is_file()
    assert (photo_dir / "image_transcript.md").is_file()
    assert (photo_dir / "import_kind.json").is_file()
    assert not (photo_dir / "talents" / "screen.json").exists()
    assert not (scratch_journal / "chronicle" / "20250315" / "screenshots").exists()
    meta = json.loads((photo_dir / "image_meta.json").read_text(encoding="utf-8"))
    assert meta == {"schema": 1, "time_source": "capture", "utc_offset_seconds": 0}
    kind = json.loads((photo_dir / "import_kind.json").read_text(encoding="utf-8"))
    assert kind["kind"] == "photos"
    transcript = (photo_dir / "image_transcript.md").read_text(encoding="utf-8")
    assert "> [image description — model-derived]" in transcript
    assert "Twenty pounds in gold and silver" in transcript
    imported = json.loads(
        (scratch_journal / "imports" / "20250315_114800" / "imported.json").read_text(encoding="utf-8")
    )
    assert imported["schema"] == "solstone.import.publication.v2"
    assert imported["segments"][0]["segment"] == "114800_0"
    assert imported["segments"][0]["stream"] == "import.image"

    # Verify weekly reflection
    assert (scratch_journal / "reflections" / "weekly" / "20250309.json").is_file()
    assert (scratch_journal / "reflections" / "weekly" / "20250309.md").is_file()

    # Run `solstone journal contract check` against the converted scratch tree
    if SOLSTONE_BIN.is_file():
        res = subprocess.run(
            [
                str(SOLSTONE_BIN),
                "journal",
                "contract",
                "check",
                "--journal",
                str(scratch_journal),
                "--root",
                str(SOLSTONE_REPO),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert res.returncode == 0, f"contract check failed:\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}"
        assert "validated" in res.stdout


def test_said_refuses_a_speaker_other_than_william(tmp_path: Path) -> None:
    """The journal shows Said as "said by you", so a Said line in anyone else's voice is refused."""
    src = (FIXTURES_DIR / "week.md").read_text(encoding="utf-8")
    bad = src.replace(
        '- 2025-03-15 · 11:40 meeting · william_shakespeare: "Whitehall, the fifteenth of March, fifteen ninety-four."',
        '- 2025-03-15 · 11:40 meeting · james_burbage: "What\'s the date on it?"',
        1,
    )
    assert bad != src
    p = tmp_path / "week.md"
    p.write_text(bad, encoding="utf-8")
    with pytest.raises(converter.ContentFormatError, match="'james_burbage' is not william_shakespeare"):
        converter.parse_week_markdown(p)


def test_superseded_march_merger_variants_are_refused_for_other_speakers_said() -> None:
    """The March week's two pre-acceptance merger drafts carry other people's lines in Said; the converter refuses both."""
    for variant in ("merged-grok", "merged-gemini"):
        week_md = PROJECT_DIR / "content" / "weeks" / "2025-03-09" / variant / "week.md"
        if not week_md.is_file():
            pytest.skip("the pre-acceptance merger drafts are workshop material and are not in this tree")
        with pytest.raises(converter.ContentFormatError, match="is not william_shakespeare"):
            converter.parse_week_markdown(week_md)


def _fat_jpeg(tag: bytes) -> bytes:
    """A valid JPEG larger than the 1x1 placeholder, so the converter treats it as real."""
    base = converter._make_minimal_jpeg("fat-jpeg-seed")
    payload = (tag + b"\x00" * 2400)[:2400]
    comment = b"\xff\xfe" + (len(payload) + 2).to_bytes(2, "big") + payload
    assert base.endswith(b"\xff\xd9")
    return base[:-2] + comment + b"\xff\xd9"


def test_reconvert_leaves_a_real_photo_intact(tmp_path: Path) -> None:
    """A second convert must not blank a photo that is already a real JPEG."""
    scratch_journal = tmp_path / "journal"
    _stage_march_week_backdrop(scratch_journal)
    converter.convert_content_to_journal(
        content_dir=FIXTURES_DIR,
        journal_dir=scratch_journal,
        solstone_repo=SOLSTONE_REPO,
    )
    photo = scratch_journal / "chronicle" / "20250315" / "import.image" / "114800_0" / "original.jpg"
    assert photo.is_file()
    real = _fat_jpeg(b"keep-this-photo")
    assert len(real) >= converter._REAL_PHOTO_MIN_BYTES
    photo.write_bytes(real)

    converter.convert_content_to_journal(
        content_dir=FIXTURES_DIR,
        journal_dir=scratch_journal,
        solstone_repo=SOLSTONE_REPO,
    )
    assert photo.read_bytes() == real


def test_reconvert_adopts_a_legacy_screenshot_jpeg(tmp_path: Path) -> None:
    """Bytes installed as a screen segment become the imported photo, unchanged."""
    scratch_journal = tmp_path / "journal"
    _stage_march_week_backdrop(scratch_journal)
    legacy = (
        scratch_journal
        / "chronicle"
        / "20250315"
        / "screenshots"
        / "114800_60"
        / "screenshot_screen.jpg"
    )
    legacy.parent.mkdir(parents=True)
    real = _fat_jpeg(b"legacy-screenshot")
    legacy.write_bytes(real)

    converter.convert_content_to_journal(
        content_dir=FIXTURES_DIR,
        journal_dir=scratch_journal,
        solstone_repo=SOLSTONE_REPO,
    )
    photo = scratch_journal / "chronicle" / "20250315" / "import.image" / "114800_0" / "original.jpg"
    assert photo.read_bytes() == real
    assert not legacy.exists()
    assert not (scratch_journal / "streams" / "screenshots.json").exists()
    stream = json.loads((scratch_journal / "streams" / "import.image.json").read_text(encoding="utf-8"))
    assert stream["name"] == "import.image"
    assert "source" not in stream


def test_placeholder_photo_is_replaced_from_the_install_manifest(tmp_path: Path) -> None:
    """A placeholder is replaced from the year manifest; a real file is not."""
    day = converter.parse_day_markdown(FIXTURES_DIR / "2025-03-15.md")
    photo_seg = next(seg for seg in day.segments if seg.kind == "photo")
    real = _fat_jpeg(b"from-manifest")
    source = tmp_path / "shot.jpg"
    source.write_bytes(real)
    manifest = tmp_path / "install.json"
    manifest.write_text(
        json.dumps({"by_segment": {f"{photo_seg.day_iso}/{photo_seg.segment_key}": str(source)}}),
        encoding="utf-8",
    )
    dest = tmp_path / "original.jpg"
    seed = f"{photo_seg.day_iso}:{photo_seg.segment_key}:{photo_seg.heading_title}"
    dest.write_bytes(converter._make_minimal_jpeg(seed))

    assert converter.photo_jpeg_bytes(photo_seg, dest, manifest_path=manifest) == real

    dest.write_bytes(real)
    other = tmp_path / "other.jpg"
    other.write_bytes(_fat_jpeg(b"should-not-replace"))
    manifest.write_text(
        json.dumps({"by_segment": {f"{photo_seg.day_iso}/{photo_seg.segment_key}": str(other)}}),
        encoding="utf-8",
    )
    assert converter.photo_jpeg_bytes(photo_seg, dest, manifest_path=manifest) == real


def test_desk_page_is_installed_and_preserved_on_reconvert(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    day = converter.parse_day_markdown(FIXTURES_DIR / "2025-03-15.md")
    frame = next(seg for seg in day.segments if seg.kind == "frame")
    manifest = tmp_path / "install.json"
    image = tmp_path / "page.jpg"
    jpeg = _fat_jpeg(b"page from manifest")
    image.write_bytes(jpeg)
    monkeypatch.setattr(converter, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(converter, "PAGE_INSTALL_MANIFEST", manifest)

    journal = tmp_path / "journal"
    segment = journal / "chronicle" / day.day_key / frame.stream_name / frame.segment_key
    extract = segment / "screen.jsonl"
    jpeg_path = segment / "page_screen.jpg"

    def convert() -> list[str]:
        converter.convert_content_to_journal(FIXTURES_DIR, journal, SOLSTONE_REPO)
        rows = [json.loads(line) for line in extract.read_text().splitlines()]
        return [row["raw"] for row in rows if "raw" in row]

    assert convert() == ["screen.mp4"]
    assert not jpeg_path.exists()
    manifest.write_text(json.dumps({"by_segment": {f"{frame.day_iso}/{frame.segment_key}": image.name}}))
    assert convert() == ["screen.mp4", jpeg_path.name]
    assert jpeg_path.read_bytes() == jpeg
    manifest.unlink()
    assert convert() == ["screen.mp4", jpeg_path.name]
    assert jpeg_path.read_bytes() == jpeg


def test_heart_rate_follows_sleep_travel_and_performance() -> None:
    rows = {row.date_iso: row for row in backdrop.load_year_dayplan_rows()}
    for day, night, seated, active in (
        ("2025-08-10", (3, 4), (10, 11), (16, 17)),
        ("2025-10-22", (2, 3), (12, 13), (14, 16)),
    ):
        plan = rows[day]
        result = backdrop.build_body_rows_for_day(
            day, world_data.resolve_day_type_key(plan.day_type_label, day),
            plan.explicit_steps, stops=plan.stops,
        )
        samples = [
            (datetime.fromisoformat(row["at"]).astimezone(backdrop.LONDON_TZ), int(row["value"]))
            for row in result if row["label"] == "heart rate"
        ]
        assert len(samples) >= 170
        assert len({at.timestamp() for at, _ in samples}) == len(samples)
        stored_first = next(row["at"] for row in result if row["label"] == "heart rate")
        assert stored_first == f"{day}T00:00:00+01:00"
        means = []
        for start, end in (night, seated, active):
            rates = [rate for at, rate in samples if start <= at.hour < end]
            means.append(sum(rates) / len(rates))
        assert means[0] < means[1] < means[2]


def test_convey_read_back_fixture(tmp_path: Path) -> None:
    """Serve the converted fixture in Convey with no thinking provider and read back all 7 surfaces."""
    from william_journal_tools.read_back import run_read_back

    fixture_backdrop = tmp_path / "fixture_backdrop"
    _stage_march_week_backdrop(fixture_backdrop)

    report = run_read_back(
        content_dir=FIXTURES_DIR,
        backdrop_dir=fixture_backdrop,
        solstone_root=SOLSTONE_REPO,
        solstone_bin=SOLSTONE_BIN if SOLSTONE_BIN.exists() else None,
    )
    assert report["status"] == "ok"
    # Measured 2026-11-19 on this fixture: 38. The one photo no longer writes
    # talents/screen.json and talents/screen_text.md. The prior floor was 40.
    assert report["talents_files_verified_unchanged"] >= 38
    assert report["william_speaker_labels_verified"] >= 1
    assert report["search_hits_twenty_pound"] >= 1
    assert report["search_hits_whitehall"] >= 1

def test_year_backdrop_invariants(tmp_path: Path) -> None:
    """Verify the year's backdrop: 365 body days, every placed day has a location track, no location where the day plan has a gap, and no fix crosses the river between 12 Jun and 18 Jul (§ 9.3)."""
    from william_journal_tools.read_back import verify_year_backdrop_invariants

    check = verify_year_backdrop_invariants(BACKDROP_BUILD_DIR)
    assert check["body_days_verified"] == 365
    assert check["placed_location_days_verified"] == 365
    assert check["gap_days_verified_empty"] == 0
    assert check["river_ban_fixes_checked"] > 0
    assert check["river_ban_violations"] == 0

    # Also verify that if a day plan has a gap (`stops == []`), write_body_and_location_from_dayplan emits body rows but no location files
    gap_row = backdrop.DayPlanRow(
        date_iso="2025-01-01",
        day_type_label="Writing day at the lodging",
        explicit_steps=3000,
        stops=backdrop.parse_places_column("gap"),
        raw_places="gap",
        sources="synthetic gap test",
    )
    assert gap_row.stops == []
    reg = contracts.ContractRegistry(solstone_repo=SOLSTONE_REPO)
    gap_journal = tmp_path / "gap_journal"
    stats = backdrop.write_body_and_location_from_dayplan(gap_journal, [gap_row], reg)
    assert stats["days"] == 1
    assert stats["placed_days"] == 0
    assert stats["gap_days"] == 1
    assert (gap_journal / "chronicle" / "20250101" / "import.apple_health" / "060000_300" / "body.jsonl").is_file()
    assert not (gap_journal / "chronicle" / "20250101" / "phone").exists()


def test_cross_midnight_carry() -> None:
    """Verify cross-midnight entry carry across 24:00 into the next day's dayplan and location track."""
    # 1. Unit checks on _extract_cross_midnight_carry and _apply_overnight_carry_to_next_day
    assert (
        dayplan._extract_cross_midnight_carry(
            {
                "id": "S001",
                "date": "2025-03-10",
                "time": "09:00–17:00",
                "place_slug": "the_theatre",
                "title": "Rehearsal",
                "body": "",
            }
        )
        is None
    )

    carry_s112b = dayplan._extract_cross_midnight_carry(
        {
            "id": "S112b",
            "date": "2025-12-09",
            "time": "23:00–01:10",
            "place_slug": "ansell_house",
            "title": "The cold walk home",
            "body": "Body: steps 16,900 for the day; heart 96 on the walk; bed 01:20; slept 5 h 05.",
        }
    )
    assert carry_s112b == {
        "id": "S112b",
        "date": "2025-12-09",
        "place_slug": "ansell_house",
        "start_hm": "23:00",
        "end_hm": "01:10",
        "bed_hm": "01:20",
        "is_walk_home": True,
    }
    applied_dec10 = dayplan._apply_overnight_carry_to_next_day(
        "`ansell_house` to 13:40 · `the_theatre` 14:00–16:30 (cal-0746) · `ansell_house` from 16:50",
        "ansell_house",
        carry_s112b,
    )
    assert applied_dec10.startswith("`ansell_house` from 01:10 (S112b, bed 01:20) to 13:40")

    carry_s115b = dayplan._extract_cross_midnight_carry(
        {
            "id": "S115b",
            "date": "2025-12-27",
            "time": "21:00–00:20",
            "place_slug": "richmond_palace",
            "title": "St John's night: the lovers; a button lost",
            "body": "",
        }
    )
    assert carry_s115b is not None and carry_s115b["end_hm"] == "00:20"
    applied_dec28 = dayplan._apply_overnight_carry_to_next_day(
        "`the_feathers_richmond` to 20:50 (cal-0786 at 09:00–11:00) · `richmond_palace` 21:00–23:45 (S115c, cal-0787)",
        "the_feathers_richmond",
        carry_s115b,
    )
    assert applied_dec28.startswith(
        "`richmond_palace` to 00:20 (S115b) · `the_feathers_richmond` from 00:25 (S115b, bed 00:30) to 20:50"
    )

    # 2. Full-year dayplans and parse_places_column on the 5 cross-midnight pairs
    data = json.loads((PROJECT_DIR / "content" / "dayplans" / "2025.json").read_text(encoding="utf-8"))
    plans = {row["date"]: row for row in data["days"]}
    assert "(W042 at 21:30–01:10)" in plans["2025-05-17"]["places_in_order"]
    assert "`ansell_house` to 08:58 (W042 to 01:10, bed 01:10)" in plans["2025-05-18"]["places_in_order"]
    assert "(W067 at 22:00–02:30)" in plans["2025-08-09"]["places_in_order"]
    assert "`henley_street` to 09:48 (W067 to 02:30, bed 02:30)" in plans["2025-08-10"]["places_in_order"]
    assert "(W092 at 20:00–00:10)" in plans["2025-11-08"]["places_in_order"]
    assert "`ansell_house` to 08:58 (W092 to 00:10, bed 00:30)" in plans["2025-11-09"]["places_in_order"]
    assert "past midnight (S112b" in plans["2025-12-09"]["places_in_order"]
    assert "`ansell_house` from 01:10 (S112b, bed 01:20) to 13:40" in plans["2025-12-10"]["places_in_order"]
    assert "`richmond_palace` from 21:00 past midnight (S115b, cal-0785)" in plans["2025-12-27"]["places_in_order"]
    assert (
        "`richmond_palace` to 00:20 (S115b) · `the_feathers_richmond` from 00:25 (S115b, bed 00:30) to 20:50"
        in plans["2025-12-28"]["places_in_order"]
    )

    stops_dec09 = backdrop.parse_places_column(plans["2025-12-09"]["places_in_order"])
    assert any(s.place_slug == "canon_row" and s.end_time.strftime("%H:%M") == "23:00" for s in stops_dec09)
    assert stops_dec09[-2].place_slug == "somerset_house" and stops_dec09[-2].start_time.strftime("%H:%M") == "23:45"

    stops_dec10 = backdrop.parse_places_column(plans["2025-12-10"]["places_in_order"])
    assert (
        stops_dec10[0].place_slug == "ansell_house"
        and stops_dec10[0].start_time.strftime("%H:%M") == "01:10"
        and stops_dec10[0].end_time.strftime("%H:%M") == "13:40"
    )

    stops_dec27 = backdrop.parse_places_column(plans["2025-12-27"]["places_in_order"])
    assert (
        stops_dec27[-1].place_slug == "richmond_palace"
        and stops_dec27[-1].start_time.strftime("%H:%M") == "21:00"
        and stops_dec27[-1].end_time.strftime("%H:%M") == "23:55"
    )

    stops_dec28 = backdrop.parse_places_column(plans["2025-12-28"]["places_in_order"])
    assert (
        stops_dec28[0].place_slug == "richmond_palace"
        and stops_dec28[0].start_time.strftime("%H:%M") == "00:00"
        and stops_dec28[0].end_time.strftime("%H:%M") == "00:20"
    )
    assert (
        stops_dec28[1].place_slug == "the_feathers_richmond"
        and stops_dec28[1].start_time.strftime("%H:%M") == "00:25"
        and stops_dec28[1].end_time.strftime("%H:%M") == "20:50"
    )


def test_sound_line_dropped_and_walk_on_kept(tmp_path: Path) -> None:
    """Verify pure sound lines (`[MM:SS] (...)`) are dropped from stored transcripts while walk-on speech (`[MM:SS] (the clerk): words`) is kept, and a sound-only segment keeps its lines."""
    src = (FIXTURES_DIR / "2025-03-15.md").read_text(encoding="utf-8")
    modified = src.replace(
        "[00:00] john_heminges: Set it down there.",
        "[00:00] (the seal breaks in the yard)\n"
        "[00:02] (the clerk): Count it twice, master.\n"
        "[00:04] john_heminges: Set it down there.",
        1,
    )
    assert modified != src
    content_dir = tmp_path / "content"
    content_dir.mkdir(parents=True, exist_ok=True)
    (content_dir / "2025-03-15.md").write_text(modified, encoding="utf-8")
    shutil.copy2(FIXTURES_DIR / "week.md", content_dir / "week.md")

    scratch_journal = tmp_path / "journal"
    _stage_march_week_backdrop(scratch_journal)
    converter.convert_content_to_journal(
        content_dir=content_dir,
        journal_dir=scratch_journal,
        solstone_repo=SOLSTONE_REPO,
    )

    seg_dir = scratch_journal / "chronicle" / "20250315" / "talk" / "114000_420"
    audio_rows = [
        json.loads(ln)
        for ln in (seg_dir / "audio.jsonl").read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    body_rows = audio_rows[1:]
    texts = [r["text"] for r in body_rows]
    speakers = [r.get("speaker") for r in body_rows]

    # Pure sound line is dropped from audio.jsonl
    assert "(the seal breaks in the yard)" not in texts
    assert all(not (t.startswith("(") and t.endswith(")")) for t in texts)

    # Walk-on speech line is stored in audio.jsonl with its parenthesized speaker
    assert body_rows[0]["speaker"] == "(the clerk)"
    assert body_rows[0]["text"] == "Count it twice, master."
    assert body_rows[0]["sentence_id"] == 1
    assert body_rows[1]["speaker"] == "john_heminges"
    assert body_rows[1]["sentence_id"] == 2

    # Walk-on is not added to speaker_labels.json
    label_rows = json.loads((seg_dir / "talents" / "speaker_labels.json").read_text(encoding="utf-8"))["labels"]
    label_speakers = {r["speaker"] for r in label_rows}
    assert "(the clerk)" not in label_speakers
    assert any(r["sentence_id"] == 2 and r["speaker"] == "john_heminges" for r in label_rows)


def _observation_lines(journal: Path, keep) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for obs_file in sorted((journal / "facets").glob("*/entities/*/observations.jsonl")):
        lines = [ln for ln in obs_file.read_text(encoding="utf-8").splitlines() if ln.strip() and keep(json.loads(ln))]
        if lines:
            out[str(obs_file.relative_to(journal))] = lines
    return out


def test_year_edge_week_keys_to_29_dec_and_keeps_5_jan_observations(tmp_path: Path) -> None:
    """The 1 Jan week (`# Week of Wed 1 Jan 2025`) is keyed to Sun 29 Dec 2024, creates no 2024 day, and leaves the 5 Jan week's observations and the backdrop baselines untouched."""
    scratch = tmp_path / "journal"
    for sub in ("facets", "entities"):
        shutil.copytree(BACKDROP_BUILD_DIR / sub, scratch / sub)
    jan5_days = {f"202501{d:02d}" for d in range(5, 12)}
    is_jan5 = lambda o: o.get("source_day") in jan5_days  # noqa: E731
    is_baseline = lambda o: o.get("source_day") == "20250101" and "id" in o  # noqa: E731
    jan5_before = _observation_lines(scratch, is_jan5)
    baseline_before = _observation_lines(scratch, is_baseline)
    assert jan5_before and baseline_before

    summary = converter.convert_content_to_journal(
        content_dir=PROJECT_DIR / "content" / "weeks" / "2025-01-01" / "merged",
        journal_dir=scratch,
        solstone_repo=SOLSTONE_REPO,
    )

    assert summary["week_converted"] == "2024-12-29"
    assert summary["days_converted"] == 4
    weekly = json.loads((scratch / "reflections" / "weekly" / "20241229.json").read_text(encoding="utf-8"))
    assert weekly["week"] == {"start": "20241229", "end": "20250104"}
    assert [d["state"] for d in weekly["days"][:3]] == ["nothing_shared"] * 3
    assert not (scratch / "reflections" / "weekly" / "20250101.json").exists()
    assert not list((scratch / "chronicle").glob("2024*"))
    assert _observation_lines(scratch, is_jan5) == jan5_before
    assert _observation_lines(scratch, is_baseline) == baseline_before
    own = _observation_lines(scratch, lambda o: o.get("source_day", "") in {"20250101", "20250102", "20250103", "20250104"} and "id" not in o)
    assert own, "the 1 Jan week's own observations were written"


def test_cancelled_calendar_events_are_stored_struck(tmp_path: Path) -> None:
    """Every cancelled event keeps its `added` note and gains a `removed` note at its `modified` time, so the journal no longer lists it; confirmed events get one `added` note."""
    from datetime import datetime

    scratch = tmp_path / "journal"
    scratch.mkdir()
    calendar_json = PROJECT_DIR / "calendar" / "merged" / "calendar.json"
    summary = backdrop.write_calendar_backdrop(
        journal_root=scratch,
        calendar_json_path=calendar_json,
        registry=contracts.ContractRegistry(solstone_repo=SOLSTONE_REPO),
    )
    events = json.loads(calendar_json.read_text(encoding="utf-8"))["events"]
    cancelled = {e["id"]: e for e in events if e.get("status") == "cancelled"}
    assert set(cancelled) == {"cal-0045", "cal-0224", "cal-0407", "cal-0779"}
    assert summary["events"] == len(events) + len(cancelled)

    notes: dict[str, list[tuple[Path, dict]]] = {}
    for f in (scratch / "chronicle").glob("*/calendar/*/calendar_*.jsonl"):
        rec = json.loads(f.read_text(encoding="utf-8"))
        notes.setdefault(rec["event"], []).append((f, rec))

    for ev in events:
        changes = sorted(rec["change"] for _, rec in notes[ev["id"]])
        if ev["id"] not in cancelled:
            assert changes == ["added"], ev["id"]
            continue
        assert changes == ["added", "removed"], ev["id"]
        (path, removed), = [(f, r) for f, r in notes[ev["id"]] if r["change"] == "removed"]
        modified = datetime.fromisoformat(ev["modified"]).replace(tzinfo=backdrop.LONDON_TZ)
        assert datetime.fromisoformat(removed["changed_at"]) == modified
        assert path.parts[-4] == modified.strftime("%Y%m%d")
        assert removed["title"] == ev["title"] and removed["start"] is None
        added = next(r for _, r in notes[ev["id"]] if r["change"] == "added")
        # The removal is the latest note, so the journal stops listing the event.
        assert datetime.fromisoformat(removed["changed_at"]) > datetime.fromisoformat(added["changed_at"])


def test_committed_tree_checkout_mtime_and_read_back() -> None:
    """Validate a fresh copy of the committed build/journal tree with simulated checkout mtimes and no re-conversion."""
    from william_journal_tools.read_back import run_read_back

    cal_files = list((BACKDROP_BUILD_DIR / "chronicle").rglob("calendar_*.jsonl"))
    assert len(cal_files) == 799

    receipt_files = sorted((BACKDROP_BUILD_DIR / "chronicle").glob("*/health/*_segment.jsonl"))
    assert len(receipt_files) == 365

    report = run_read_back(
        content_dir=None,
        committed_journal=BACKDROP_BUILD_DIR,
        solstone_root=SOLSTONE_REPO,
        solstone_bin=SOLSTONE_BIN if SOLSTONE_BIN.exists() else None,
    )
    assert report["status"] == "ok"
    assert report["conversion"]["mode"] == "committed_tree_no_reconversion"
    assert report["conversion"]["stamp"]["days_stamped"] == 365
    assert report["home_weeks_verified"] == [
        "20241229",
        "20250105",
        "20250112",
        "20250119",
        "20250126",
        "20250202",
        "20250209",
        "20250216",
        "20250223",
        "20250302",
        "20250309",
        "20250316",
        "20250323",
        "20250330",
        "20250406",
        "20250413",
        "20250420",
        "20250427",
        "20250504",
        "20250511",
        "20250518",
        "20250525",
        "20250601",
        "20250608",
        "20250615",
        "20250622",
        "20250629",
        "20250706",
        "20250713",
        "20250720",
        "20250727",
        "20250803",
        "20250810",
        "20250817",
        "20250824",
        "20250831",
        "20250907",
        "20250914",
        "20250921",
        "20250928",
        "20251005",
        "20251012",
        "20251019",
        "20251026",
        "20251102",
        "20251109",
        "20251116",
        "20251123",
        "20251130",
        "20251207",
        "20251214",
        "20251221",
        "20251228",
    ]
    assert report["named_places_verified"] == 31
    assert report["year_backdrop_check"]["body_days_verified"] == 365
    assert report["year_backdrop_check"]["placed_location_days_verified"] == 365
    assert report["year_backdrop_check"]["river_ban_violations"] == 0
    # Measured 2026-11-19 by read_back.py on the reconverted year:
    # len(talents_after) == 20290. Photos no longer write talents/screen.json
    # or talents/screen_text.md (2 files x 183). The prior pin was 20656.
    assert report["talents_files_verified_unchanged"] == 20290
    assert report["william_speaker_labels_verified"] == 796
    assert report["search_hits_twenty_pound"] >= 1
    assert report["search_hits_whitehall"] >= 1


# --- Continuing an activity (FORMAT.md, "continues:") -------------------------

_CONTINUATION_TEMPLATE = """## {hhmm} · {minutes} min · meeting · {title}

- place: burbage_house_holywell
- facet: company
- kind: meeting
- content type: social
- density: {density}
- people: {people}
- entries: none
- calendar: none
- continues: {continues}

### Transcript

[00:00] richard_burbage: The Bull, then, and the Queen's health.
[00:20] william_shakespeare: One cup.

### Sense

- summary: You stayed at the table while the coin went into purses.
- topics: the Bull, the share
- quotes: richard_burbage: The Bull, then, and the Queen's health.; william_shakespeare: One cup.
- also mentioned: none

"""


def _continuing_fixture(tmp_path: Path, continuations: list[dict[str, str]]) -> Path:
    """The fixture day with continuation segments inserted after the 11:40 meeting, in the order given."""
    src = (FIXTURES_DIR / "2025-03-15.md").read_text(encoding="utf-8")
    blocks = "".join(_CONTINUATION_TEMPLATE.format(**c) for c in continuations)
    anchor = "## 11:48 · 1 min · photo ·"
    assert anchor in src
    content_dir = tmp_path / "content"
    content_dir.mkdir(parents=True, exist_ok=True)
    (content_dir / "2025-03-15.md").write_text(src.replace(anchor, blocks + anchor, 1), encoding="utf-8")
    shutil.copy2(FIXTURES_DIR / "week.md", content_dir / "week.md")
    return content_dir


_TWO_CONTINUATIONS = [
    # Written out of time order on purpose: `segments` must still come out in time order.
    {
        "hhmm": "12:05",
        "minutes": "10",
        "title": "The share carried to the door",
        "density": "low_change",
        "people": "william_shakespeare (attendee), richard_burbage (attendee), will_sly (attendee), edith_kettlewood (mentioned)",
        "continues": "11:40",
    },
    {
        "hhmm": "11:52",
        "minutes": "8",
        "title": "The purses filled",
        "density": "active",
        "people": "william_shakespeare (attendee), richard_burbage (attendee), john_heminges (attendee)",
        "continues": "11:40",
    },
]


def _activity_time_range(segments: list[str]) -> str:
    """`activity_time_range` in solstone-core-format/src/content/activities.rs: first entry's start to last entry's end."""
    first, last = segments[0], segments[-1]
    start_h, start_m = int(first[0:2]), int(first[2:4])
    end_sec = int(last[0:2]) * 3600 + int(last[2:4]) * 60 + int(last[4:6]) + int(last.split("_")[1])
    end_sec = min(end_sec, 23 * 3600 + 59 * 60 + 59)
    return f"{start_h:02}:{start_m:02}-{end_sec // 3600:02}:{(end_sec % 3600) // 60:02}"


def _converted_company_activities(tmp_path: Path, continuations: list[dict[str, str]]) -> tuple[Path, list[dict]]:
    content_dir = _continuing_fixture(tmp_path, continuations)
    scratch_journal = tmp_path / "journal"
    _stage_march_week_backdrop(scratch_journal)
    converter.convert_content_to_journal(
        content_dir=content_dir,
        journal_dir=scratch_journal,
        solstone_repo=SOLSTONE_REPO,
    )
    act_file = scratch_journal / "facets" / "company" / "activities" / "20250315.jsonl"
    rows = [json.loads(ln) for ln in act_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return scratch_journal, rows


def test_continuation_joins_its_heads_activity_in_time_order(tmp_path: Path) -> None:
    journal, rows = _converted_company_activities(tmp_path, _TWO_CONTINUATIONS)
    meeting_rows = [r for r in rows if r["stream"] == "talk"]
    assert [r["id"] for r in meeting_rows] == ["meeting_114000_420"], "a continuation gets no activity of its own"
    act = meeting_rows[0]
    assert act["segments"] == ["114000_420", "115200_480", "120500_600"]
    assert act["title"] == "Divided the Queen's twenty pounds into eight parts at Holywell"
    assert act["activity"] == "meeting", "the head's content type governs, not the continuation's 'social'"
    assert act["level_avg"] == 0.5, "the last segment (low_change) sets the level, as the product's state machine does"
    # Each continuation is still its own segment in the stream, with its own sense.
    for key in act["segments"][1:]:
        seg_dir = journal / "chronicle" / "20250315" / "talk" / key
        assert (seg_dir / "stream.json").is_file()
        sense = json.loads((seg_dir / "talents" / "sense.json").read_text(encoding="utf-8"))
        assert sense["content_type"] == "social"
        assert sense["facets"][0]["activity"] == act["title"]
        assert [q["speaker"] for q in sense["quotes"]] == ["richard_burbage", "william_shakespeare"]


def test_continuation_span_runs_from_head_start_to_last_end(tmp_path: Path) -> None:
    _, rows = _converted_company_activities(tmp_path, _TWO_CONTINUATIONS)
    act = next(r for r in rows if r["id"] == "meeting_114000_420")
    assert _activity_time_range(act["segments"]) == "11:40-12:15"
    end_ms = converter.to_epoch_ms("2025-03-15T12:15:00+00:00")
    assert act["created_at"] == end_ms and act["updated_at"] == end_ms


def test_continuation_people_join_the_head_activity(tmp_path: Path) -> None:
    _, rows = _converted_company_activities(tmp_path, _TWO_CONTINUATIONS)
    act = next(r for r in rows if r["id"] == "meeting_114000_420")
    by_slug = {p["entity_id"]: p for p in act["participation"]}
    # The head's authored entries stay as written.
    assert by_slug["john_heminges"]["context"].startswith("Counted the twenty pounds")
    assert by_slug["richard_burbage"]["context"].startswith("Complained of the passage wait")
    # People only a continuation names join, with the converter's generic context.
    assert by_slug["will_sly"]["role"] == "attendee"
    assert by_slug["will_sly"]["context"] == "attendee in The share carried to the door"
    assert by_slug["edith_kettlewood"]["role"] == "mentioned"
    assert len(act["participation"]) == len(by_slug), "nobody is listed twice"


def test_continuation_with_no_matching_head_is_refused(tmp_path: Path) -> None:
    for continues in ("11:41", "11:48"):  # no segment at 11:41; 11:48 is a photo, not a meeting
        bad = [dict(_TWO_CONTINUATIONS[1], continues=continues)]
        content_dir = _continuing_fixture(tmp_path / continues.replace(":", ""), bad)
        with pytest.raises(converter.ContentFormatError, match=f"continues: {continues} names no earlier meeting"):
            converter.parse_day_markdown(content_dir / "2025-03-15.md")


def test_continuation_with_its_own_activity_is_refused(tmp_path: Path) -> None:
    content_dir = _continuing_fixture(tmp_path, [_TWO_CONTINUATIONS[1]])
    day = content_dir / "2025-03-15.md"
    text = day.read_text(encoding="utf-8").replace(
        "- also mentioned: none\n\n## 11:48",
        "- also mentioned: none\n\n### Activity\n\n- title: Filled the purses\n- story: You filled them.\n\n## 11:48",
        1,
    )
    day.write_text(text, encoding="utf-8")
    with pytest.raises(converter.ContentFormatError, match="a continuation segment has no '### Activity'"):
        converter.parse_day_markdown(day)


def test_said_line_with_no_matching_head_raises(tmp_path: Path) -> None:
    """A Said line that names no activity head fails loudly; it never falls back to the day's first activity."""
    content_dir = _continuing_fixture(tmp_path, [_TWO_CONTINUATIONS[1]])
    week = content_dir / "week.md"
    src = week.read_text(encoding="utf-8")
    # 11:52 is a real meeting segment, but a continuation: it opens no activity.
    bad = src.replace(
        '- 2025-03-15 · 11:40 meeting · william_shakespeare: "Whitehall, the fifteenth of March, fifteen ninety-four."',
        '- 2025-03-15 · 11:52 meeting · william_shakespeare: "One cup."',
        1,
    )
    assert bad != src
    week.write_text(bad, encoding="utf-8")
    scratch_journal = tmp_path / "journal"
    _stage_march_week_backdrop(scratch_journal)
    with pytest.raises(converter.ContentFormatError, match="2025-03-15 11:52 meeting, but no activity opens at that time"):
        converter.convert_content_to_journal(
            content_dir=content_dir,
            journal_dir=scratch_journal,
            solstone_repo=SOLSTONE_REPO,
        )


def test_inline_quotes_split_into_one_quote_per_speaker() -> None:
    assert converter._split_inline_quotes(
        "margery_pell: Two hundred, if I am to put one figure on it.; richard_cowley: Then go; see.; william_shakespeare: No."
    ) == [
        "margery_pell: Two hundred, if I am to put one figure on it.",
        "richard_cowley: Then go; see.",
        "william_shakespeare: No.",
    ]
