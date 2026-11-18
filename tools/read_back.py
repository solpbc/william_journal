# SPDX-License-Identifier: CC-BY-NC-4.0
# Copyright (c) 2026 sol pbc

"""Automated, re-runnable three-layer validation and Convey read-back harness.

Runs exclusively against a `/var/tmp` scratch copy of the generated journal with
`SOLSTONE_JOURNAL`, `SOLSTONE_JOURNAL_SOCKET`, and `SOLSTONE_CONVEY_PORT` all set
explicitly to scratch values, and no thinking provider configured.

Validates:
1. Schema checks (`core/payload/solstone/talent/*.schema.json` and `bundle.json`)
   during content conversion.
2. `solstone journal contract check` on the scratch journal.
3. Serving the scratch tree in Convey with no thinking provider, running
   `solstone journal indexer --rescan-full` and `solstone journal journal-stats`,
   and reading back Home, Activities, Transcripts, Map, Body, Entities, Search,
   Thinking, and Health over HTTP.
4. Asserting that nothing was queued, no `talents/*` file changed, segments
   badge `"thought"`, William is named on `speaker_labels.json`, and body rows
   are visible.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tools.backdrop import PROJECT_ROOT, generate_backdrop, load_year_dayplan_rows
    from tools.converter import convert_content_to_journal
    from tools.lived_in import CATEGORIES, CONNECTION, CORRECTIONS, NOTES, POSSIBLE_NAMES, VISITS
    from tools.stamp import stamp_journal_tree
else:
    from .backdrop import PROJECT_ROOT, generate_backdrop, load_year_dayplan_rows
    from .converter import convert_content_to_journal
    from .lived_in import CATEGORIES, CONNECTION, CORRECTIONS, NOTES, POSSIBLE_NAMES, VISITS
    from .stamp import stamp_journal_tree


DEFAULT_SOLSTONE_ROOT = Path(os.environ.get("WILLIAM_SOLSTONE_REPO") or Path.home() / "projects" / "solstone-journal")
DEFAULT_BACKDROP_DIR = (
    Path(__file__).resolve().parents[1] / "build" / "journal"
)
DEFAULT_FIXTURE_CONTENT_DIR = (
    Path(__file__).resolve().parent / "tests" / "fixtures"
)


def verify_year_backdrop_invariants(journal_root: Path) -> dict[str, Any]:
    """Verify full-year Wave 0 invariants on `journal_root`:
    1. Every day of 2025 (365 days) has body rows (`import.apple_health/060000_300/body.jsonl`).
    2. Every placed day has a location track (`phone/*/location.jsonl`).
    3. No location file exists where a day plan has a gap (`not plan.stops`).
    4. No fix or visit crosses the river (`lat < 51.5085`) between 12 Jun and 18 Jul (§ 9.3).
    """
    rows = load_year_dayplan_rows()
    assert len(rows) == 365, f"Expected 365 day plan rows, got {len(rows)}"

    body_days = 0
    placed_days = 0
    gap_days = 0
    river_fixes_checked = 0
    river_violations: list[str] = []

    for row in rows:
        day_key = row.date_iso.replace("-", "")
        day_dir = journal_root / "chronicle" / day_key

        body_file = day_dir / "import.apple_health" / "060000_300" / "body.jsonl"
        assert body_file.is_file(), f"Missing body.jsonl on {row.date_iso} ({body_file})"
        body_lines = [ln for ln in body_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(body_lines) >= 10, f"Expected >=10 body rows on {row.date_iso}, got {len(body_lines)}"
        body_days += 1

        loc_files = sorted((day_dir / "phone").glob("*/location.jsonl")) if (day_dir / "phone").is_dir() else []
        if not row.stops:
            assert not loc_files, f"Day {row.date_iso} has a location gap in dayplan but has location files: {loc_files}"
            gap_days += 1
        else:
            assert loc_files, f"Placed day {row.date_iso} has no location.jsonl files"
            day_fix_count = 0
            for lf in loc_files:
                lines = [json.loads(ln) for ln in lf.read_text(encoding="utf-8").splitlines() if ln.strip()]
                assert lines and lines[0].get("schema") == "solstone.location.segment/1"
                day_fix_count += int(lines[0].get("fix_count", 0))
                if "2025-06-12" <= row.date_iso <= "2025-07-18":
                    for item in lines[1:]:
                        lat = item.get("lat")
                        if isinstance(lat, (int, float)):
                            river_fixes_checked += 1
                            if float(lat) < 51.5085:
                                river_violations.append(f"{row.date_iso} {lf.parent.name}: lat={lat}")
            assert day_fix_count >= 1, f"Placed day {row.date_iso} has 0 fixes across {len(loc_files)} location files"
            placed_days += 1

    assert not river_violations, (
        f"Found {len(river_violations)} river-crossing fixes (< 51.5085) between 12 Jun and 18 Jul: {river_violations[:5]}"
    )

    return {
        "body_days_verified": body_days,
        "placed_location_days_verified": placed_days,
        "gap_days_verified_empty": gap_days,
        "river_ban_fixes_checked": river_fixes_checked,
        "river_ban_violations": len(river_violations),
    }


def _find_solstone_binary(solstone_root: Path, explicit_bin: Path | None = None) -> Path:
    if explicit_bin is None and (override := os.environ.get("WILLIAM_SOLSTONE_BIN")):
        explicit_bin = Path(override).resolve()
    if explicit_bin is not None:
        if not explicit_bin.is_file():
            raise FileNotFoundError(f"Explicit solstone binary not found: {explicit_bin}")
        return explicit_bin
    candidates = [
        Path("/var/tmp/william-journal-runtime/prefix/current/bin/solstone"),
        solstone_root / "core" / "target" / "debug" / "solstone",
        solstone_root / "core" / "target" / "release" / "solstone",
    ]
    if on_path := shutil.which("solstone"):
        candidates.append(Path(on_path))
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    raise FileNotFoundError(
        "Could not locate `solstone` binary in /var/tmp/william-journal-runtime or "
        f"{solstone_root / 'core' / 'target'}"
    )


def _assert_scratch_path(path: Path) -> None:
    resolved = path.resolve()
    if not str(resolved).startswith("/var/tmp/"):
        raise ValueError(
            f"Refusing to run against non-/var/tmp path: {resolved}"
        )


def _allocate_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _snapshot_talents(journal_root: Path) -> dict[str, str]:
    """Return relative-path -> sha256 for every file inside any `talents/` directory."""
    digests: dict[str, str] = {}
    for path in sorted(journal_root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(journal_root)
        if "talents" in rel.parts:
            digests[rel.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digests


def index_coverage(journal: Path) -> dict[str, dict[str, int]]:
    """Count stored coordinates against distinct coordinates with search chunks."""
    stored = {
        f"{segment.parent.parent.name}/{segment.parent.name}/{segment.name}"
        for segment in (journal / "chronicle").glob("*/*/*")
        if segment.is_dir() and re.fullmatch(r"[0-9]{6}_[0-9]+", segment.name)
        and any(member.is_file() for member in segment.rglob("*"))
    }
    database = journal / "indexer" / "journal.sqlite"
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as connection:
        assert connection.execute("PRAGMA quick_check").fetchone() == ("ok",)
        indexed = {
            "/".join(path.split("/", 3)[:3])
            for (path,) in connection.execute("SELECT DISTINCT path FROM chunks")
        }
    def kind(coordinate: str) -> str:
        stream = coordinate.split("/")[1]
        return "agent_memory" if stream.startswith("agent-memory-") else stream

    on_disk = Counter(map(kind, stored))
    searchable = Counter(map(kind, stored & indexed))
    return {stream: {"stored": on_disk[stream], "indexed": searchable[stream]}
            for stream in sorted(on_disk)}


def verify_lived_in(journal: Path, port: int) -> dict[str, Any]:
    connections = _http_get_json(port, "/app/agents/api/state")["connections"]
    connection = next(row for row in connections if row["key"] == CONNECTION)
    assert connection["name"] == "Claude" and connection["paused"] is None
    assert connection["permission"]["read"]["categories"] == CATEGORIES
    notes = _http_get_json(port, f"/app/agents/api/memories/{connection['memory_source']}")
    assert notes["complete"] and [row["content"] for row in notes["memories"]] == [
        text for _, text in reversed(NOTES)
    ]
    activity = _http_get_json(port, "/app/agents/api/activity?from=20250101&to=20251231")
    assert activity["unreadable"] == 0 and len(activity["entries"]) == len(NOTES) + len(VISITS)
    assert all(row["connection"] == CONNECTION for row in activity["entries"])
    for day, facet, activity_id, details in CORRECTIONS:
        view = _http_get_json(port, f"/app/activities/api/day/{day}/record/{activity_id}?facet={facet}")
        assert view["record"]["details"] == details
        assert any(edit["actor"] == "owner:update" for edit in view["record"]["edits"])
    for day, segment, sentence, _, slug in POSSIBLE_NAMES:
        view = _http_get_json(port, f"/app/transcripts/api/segment/{day}/talk/{segment}")
        row = next(row for row in view["chunks"] if row.get("sentence_id") == sentence)
        entity = json.loads((journal / "entities" / slug / "entity.json").read_text())
        assert entity["name"] in {entry["name"] for entry in row["possible_names"]}
    identity = _http_get_json(port, "/app/network/api/identity")
    assert identity["committed"] and identity["mark"]
    return {"agent": connection["name"], "agent_notes": len(notes["memories"]),
            "agent_interactions": len(activity["entries"]), "corrections": len(CORRECTIONS),
            "possible_names": len(POSSIBLE_NAMES), "instance_id": identity["instance_id"]}


def _http_get_json(port: int, route: str, timeout: float = 10.0) -> Any:
    url = f"http://127.0.0.1:{port}{route}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise AssertionError(f"GET {route} failed with HTTP {exc.code}: {body}") from exc
    if status != 200:
        raise AssertionError(f"GET {route} returned status {status}: {raw}")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"GET {route} returned non-JSON body: {raw[:300]}") from exc


def _touch_all_to_checkout_mtime(journal_root: Path, checkout_epoch_sec: float | None = None) -> int:
    """Set every file in `journal_root` to `checkout_epoch_sec` (default `time.time()`) to simulate a fresh git checkout."""
    now_sec = checkout_epoch_sec if checkout_epoch_sec is not None else time.time()
    count = 0
    for path in sorted(journal_root.rglob("*")):
        if path.is_file():
            os.utime(path, (now_sec, now_sec))
            count += 1
    return count


def run_read_back(
    *,
    content_dir: Path | None = DEFAULT_FIXTURE_CONTENT_DIR,
    backdrop_dir: Path = DEFAULT_BACKDROP_DIR,
    committed_journal: Path | None = None,
    solstone_root: Path = DEFAULT_SOLSTONE_ROOT,
    solstone_bin: Path | None = None,
    keep_scratch: bool = False,
) -> dict[str, Any]:
    """Run the full 3-layer validation and Convey read-back on a scratch copy."""
    binary = _find_solstone_binary(solstone_root, solstone_bin)
    scratch_base = Path(tempfile.mkdtemp(prefix="william-journal-readback-", dir="/var/tmp"))
    _assert_scratch_path(scratch_base)

    scratch_journal = scratch_base / "journal"
    scratch_socket = scratch_base / "journal.sock"
    port = _allocate_free_port()

    env = os.environ.copy()
    env["SOLSTONE_JOURNAL"] = str(scratch_journal)
    env["SOLSTONE_JOURNAL_SOCKET"] = str(scratch_socket)
    env["SOLSTONE_CONVEY_PORT"] = str(port)
    env["SOLSTONE_ROOT"] = str(solstone_root)

    convey_proc: subprocess.Popen[str] | None = None
    convey_log_file = None
    try:
        # 1. Stage either a fresh copy of the committed journal tree (NO re-conversion,
        #    simulating a fresh git checkout followed by the one-command stamp step)
        #    or convert `content_dir` onto `backdrop_dir`.
        if committed_journal is not None:
            shutil.copytree(committed_journal, scratch_journal)
            checkout_files_touched = _touch_all_to_checkout_mtime(scratch_journal)
            stamp_summary = stamp_journal_tree(scratch_journal)
            conversion_summary: dict[str, Any] = {
                "mode": "committed_tree_no_reconversion",
                "source_journal": str(committed_journal),
                "simulated_checkout_files_touched": checkout_files_touched,
                "stamp": stamp_summary,
            }
        else:
            assert content_dir is not None, "content_dir must be provided when committed_journal is None"
            if backdrop_dir.is_dir():
                shutil.copytree(backdrop_dir, scratch_journal)
            else:
                generate_backdrop(scratch_journal, solstone_repo=solstone_root)

            conversion_summary = convert_content_to_journal(
                content_dir,
                scratch_journal,
                solstone_repo=solstone_root,
            )

        # 2. Verify no thinking provider or lane is configured
        config_data = json.loads(
            (scratch_journal / "config" / "journal.json").read_text(encoding="utf-8")
        )
        assert "thinking" not in config_data, (
            f"Unexpected thinking key in config/journal.json: {config_data}"
        )
        assert not config_data.get("providers"), (
            f"Expected no providers in config/journal.json, got: {config_data.get('providers')}"
        )
        has_lived_in = (scratch_journal / "mcp-endpoint" / "oauth.json").is_file()
        if has_lived_in:
            config_data.setdefault("pairing", {})["direct_port"] = _allocate_free_port()
            (scratch_journal / "config" / "journal.json").write_text(json.dumps(config_data) + "\n")

        # 2a. Verify full-year backdrop invariants when running on a full-year journal tree
        is_full_year = (scratch_journal / "chronicle" / "20251231" / "import.apple_health").is_dir()
        year_backdrop_check = (
            verify_year_backdrop_invariants(scratch_journal) if is_full_year else None
        )

        # 3. Verify William is named on speaker_labels.json in talk segments where he speaks
        speaker_label_files = sorted(
            scratch_journal.glob("chronicle/*/talk/*/talents/speaker_labels.json")
        )
        assert speaker_label_files, "Expected at least one talk speaker_labels.json file"
        william_speaking_files = 0
        william_named_count = 0
        for sl_path in speaker_label_files:
            audio_path = sl_path.parents[1] / "audio.jsonl"
            audio_has_william = any(
                json.loads(ln).get("speaker") == "william_shakespeare"
                for ln in audio_path.read_text(encoding="utf-8").splitlines()
                if ln.strip()
            )
            if not audio_has_william:
                continue
            william_speaking_files += 1
            sl_data = json.loads(sl_path.read_text(encoding="utf-8"))
            rows = sl_data.get("labels", [])
            if any(
                row.get("speaker") == "william_shakespeare"
                and row.get("method") == "user_assigned"
                and row.get("confidence") == "high"
                for row in rows
            ):
                william_named_count += 1
        assert william_named_count >= william_speaking_files, (
            f"William Shakespeare not user_assigned in all talk speaker_labels.json files where he speaks "
            f"({william_named_count}/{william_speaking_files})"
        )

        # 4. Snapshot talents/* digests before Convey / indexer / stats
        talents_before = _snapshot_talents(scratch_journal)
        assert talents_before, "Expected non-empty talents/* files before Convey startup"

        # 5. Layer 2: `solstone journal contract check`
        contract_res = subprocess.run(
            [
                str(binary),
                "journal",
                "contract",
                "check",
                "--journal",
                str(scratch_journal),
                "--root",
                str(solstone_root),
            ],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if contract_res.returncode != 0:
            raise AssertionError(
                f"solstone journal contract check failed (exit {contract_res.returncode}):\n"
                f"STDOUT:\n{contract_res.stdout}\nSTDERR:\n{contract_res.stderr}"
            )

        # 6. Start Convey on the scratch journal with no thinking provider
        convey_log_path = scratch_base / "convey.log"
        convey_log_file = convey_log_path.open("w", encoding="utf-8")
        convey_proc = subprocess.Popen(
            [
                str(binary),
                "journal",
                "convey",
                "--port",
                str(port),
                "--journal",
                str(scratch_journal),
            ],
            env=env,
            stdout=convey_log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )

        # Wait for Convey HTTP listener + initial location/body reconciliation
        deadline = time.monotonic() + 300.0
        convey_ready = False
        reconcile_ready = False
        while time.monotonic() < deadline:
            if convey_proc.poll() is not None:
                convey_log_file.flush()
                log_body = convey_log_path.read_text(encoding="utf-8", errors="replace")
                raise RuntimeError(
                    f"Convey exited prematurely with code {convey_proc.returncode}:\n{log_body}"
                )
            if not convey_ready:
                try:
                    about = _http_get_json(port, "/api/system/about", timeout=1.0)
                    if isinstance(about, dict):
                        convey_ready = True
                except Exception:
                    pass
            if convey_ready:
                body_md = scratch_journal / "chronicle" / "20250315" / "body.md"
                loc_md = scratch_journal / "chronicle" / "20250315" / "location.md"
                places_json = scratch_journal / "solstone" / "apps" / "map" / "places.json"
                dec_ready = True
                if is_full_year:
                    body_dec = scratch_journal / "chronicle" / "20251231" / "body.md"
                    loc_dec = scratch_journal / "chronicle" / "20251231" / "location.md"
                    dec_ready = body_dec.is_file() and loc_dec.is_file()
                if body_md.is_file() and loc_md.is_file() and dec_ready and places_json.is_file():
                    reconcile_ready = True
                    break
            time.sleep(0.2)

        assert convey_ready, "Timed out waiting for Convey HTTP server to listen"
        assert reconcile_ready, (
            "Timed out waiting for Convey startup reconciler to produce body.md, "
            "location.md, and places.json"
        )

        # 7. Run indexer (--rescan-full) and journal-stats against the scratch journal
        indexer_res = subprocess.run(
            [str(binary), "journal", "indexer", "--rescan-full"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if indexer_res.returncode != 0:
            raise AssertionError(
                f"solstone journal indexer --rescan-full failed (exit {indexer_res.returncode}):\n"
                f"STDOUT:\n{indexer_res.stdout}\nSTDERR:\n{indexer_res.stderr}"
            )
        assert (scratch_journal / "indexer" / "journal.sqlite").is_file(), (
            "Expected indexer/journal.sqlite to exist after indexer --rescan-full"
        )

        stats_res = subprocess.run(
            [str(binary), "journal", "journal-stats"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if stats_res.returncode != 0:
            raise AssertionError(
                f"solstone journal journal-stats failed (exit {stats_res.returncode}):\n"
                f"STDOUT:\n{stats_res.stdout}\nSTDERR:\n{stats_res.stderr}"
            )
        assert (scratch_journal / "stats.json").is_file(), (
            "Expected stats.json to exist after journal-stats"
        )

        # 8. Read back all 7 Convey surfaces + Thinking/Health state
        # 8a. Home
        home_pulse = _http_get_json(port, "/app/home/api/pulse")
        home_briefing = _http_get_json(port, "/app/home/api/briefing")
        assert isinstance(home_pulse, dict), "Home pulse payload must be a dict"
        assert isinstance(home_briefing, dict), "Home briefing payload must be a dict"

        expected_weeks = (
            [
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
            if is_full_year
            else ["20250309"]
        )
        home_weeks_verified: list[str] = []
        for wk_key in expected_weeks:
            home_week = _http_get_json(port, f"/app/home/api/week/{wk_key}")
            assert home_week.get("day") == wk_key, (
                f"Expected day {wk_key} on Home week route, got: {home_week}"
            )
            assert len(home_week.get("rows", [])) >= 1, (
                f"Expected >=1 memory row on Home week {wk_key}, got: {home_week}"
            )
            assert len(home_week.get("said", {}).get("days", [])) >= 1, (
                f"Expected >=1 said day on Home week {wk_key}, got: {home_week}"
            )
            home_weeks_verified.append(wk_key)

        # 8b. Activities
        activities_index = _http_get_json(port, "/app/activities/api/index")
        sample_days = (
            [
                "20250101",
                "20250105",
                "20250117",
                "20250119",
                "20250126",
                "20250202",
                "20250209",
                "20250216",
                "20250223",
                "20250302",
                "20250315",
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
                "20250612",
                "20250615",
                "20250622",
                "20250630",
                "20250707",
                "20250713",
                "20250721",
                "20250727",
                "20250803",
                "20250816",
                "20250817",
                "20250824",
                "20250831",
                "20250907",
                "20250914",
                "20250921",
                "20251002",
                "20251005",
                "20251012",
                "20251021",
                "20251026",
                "20251102",
                "20251111",
                "20251116",
                "20251123",
                "20251206",
                "20251209",
                "20251214",
                "20251221",
                "20251228",
            ]
            if is_full_year
            else ["20250315"]
        )
        activities_index_str = json.dumps(activities_index)
        for s_day in sample_days:
            assert s_day in activities_index_str or s_day[:6] in activities_index.get("months", {}), (
                f"Expected {s_day} (or month {s_day[:6]}) in /app/activities/api/index: {activities_index}"
            )
            activities_day = _http_get_json(port, f"/app/activities/api/day/{s_day}/view")
            day_activities = activities_day.get("items", [])
            assert len(day_activities) >= 1, (
                f"Expected >=1 activity on {s_day} view, got: {activities_day}"
            )

        # 8c. Transcripts (wait for background index cache warmer to complete across all weeks)
        tr_deadline = time.monotonic() + 120.0
        transcripts_index = _http_get_json(port, "/app/transcripts/api/index")
        while (
            time.monotonic() < tr_deadline
            and isinstance(transcripts_index, dict)
            and isinstance(transcripts_index.get("freshness"), dict)
            and not transcripts_index["freshness"].get("complete", True)
        ):
            time.sleep(0.5)
            transcripts_index = _http_get_json(port, "/app/transcripts/api/index")
        transcripts_index_str = json.dumps(transcripts_index)
        thought_seg_count = 0
        talk_segs_verified = 0
        for s_day in sample_days:
            assert s_day in transcripts_index_str or s_day[:6] in transcripts_index_str, (
                f"Expected {s_day} (or month {s_day[:6]}) in /app/transcripts/api/index: {transcripts_index}"
            )
            transcripts_segments = _http_get_json(port, f"/app/transcripts/api/segments/{s_day}")
            _ = _http_get_json(port, f"/app/transcripts/api/day/{s_day}")
            seg_list = transcripts_segments.get("segments", [])
            assert len(seg_list) >= 1, f"Expected >=1 segment on {s_day}"
            for seg in seg_list:
                think_badge = seg.get("think")
                assert think_badge != "awaiting", (
                    f"Segment {s_day}/{seg.get('stream')}/{seg.get('key')} has think='awaiting': {seg}"
                )
                if any(t in ("audio", "screen") for t in seg.get("types", [])):
                    assert think_badge == "thought", (
                        f"Expected segment {s_day}/{seg.get('stream')}/{seg.get('key')} to badge "
                        f"'thought', got {think_badge!r}"
                    )
                    thought_seg_count += 1

            talk_segs = [s for s in seg_list if s.get("stream") == "talk"]
            assert talk_segs, f"Expected at least one talk segment on {s_day}"
            talk_key = talk_segs[0]["key"]
            talk_detail = _http_get_json(
                port, f"/app/transcripts/api/segment/{s_day}/talk/{talk_key}"
            )
            assert talk_detail.get("data_state", {}).get("audio") == "analyzed", (
                f"Expected talk segment audio data_state == 'analyzed' on {s_day}, got: "
                f"{talk_detail.get('data_state')}"
            )
            assert talk_detail.get("speaker_labels", {}).get("loaded") is True, (
                f"Expected speaker_labels.loaded == True on {s_day} talk segment, got: "
                f"{talk_detail.get('speaker_labels')}"
            )
            assert "William Shakespeare" in json.dumps(talk_detail), (
                f"Expected 'William Shakespeare' resolved in {s_day} talk segment detail response"
            )
            talk_segs_verified += len(talk_segs)

        assert thought_seg_count >= len(sample_days), "Expected >=1 audio/screen segment badging 'thought' per sample day"

        # 8d. Map
        map_index = _http_get_json(port, "/app/map/api/index")
        map_day = _http_get_json(port, "/app/map/api/day/20250315")
        map_places = _http_get_json(port, "/app/map/api/places")
        map_week = _http_get_json(port, "/app/map/api/week/20250309")
        map_index_str = json.dumps(map_index)
        assert "202503" in map_index_str or "20250315" in map_index_str, (
            f"Expected March 2025 coverage in /app/map/api/index: {map_index}"
        )
        map_day_str = json.dumps(map_day)
        assert map_day.get("day") == "20250315" and len(map_day.get("entries", [])) >= 4, (
            f"Expected >=4 entries on 15 Mar in /app/map/api/day/20250315: {map_day}"
        )
        assert "London" in map_day_str and "51.5046" in map_day_str and "51.5251" in map_day_str, (
            f"Expected 15 Mar Whitehall/Holywell coordinates in /app/map/api/day/20250315: {map_day}"
        )
        places_list = map_places.get("places", [])
        assert places_list, (
            f"Expected non-empty places list in /app/map/api/places: {map_places}"
        )
        named_places_verified = sum(1 for p in places_list if p.get("name"))
        if is_full_year:
            assert len(places_list) == 31, (
                f"Expected 31 derived places on full-year journal, got {len(places_list)}"
            )
            assert named_places_verified == 31, (
                f"Expected all 31 derived places to have § 4 names, got {named_places_verified}/31"
            )
            home_places = [p for p in places_list if p.get("alias") == "home"]
            assert len(home_places) == 1 and home_places[0].get("name") == "Mistress Ansell's house, Great St Helen's", (
                f"Expected Mistress Ansell's house to have alias='home', got: {home_places}"
            )
            map_dec09 = _http_get_json(port, "/app/map/api/day/20251209")
            assert map_dec09.get("day") == "20251209" and len(map_dec09.get("entries", [])) >= 4, (
                f"Expected >=4 entries on 9 Dec in /app/map/api/day/20251209: {map_dec09}"
            )
        assert isinstance(map_week, dict), "Expected dict from /app/map/api/week/20250309"

        # 8e. Body
        body_index = _http_get_json(port, "/app/body/api/index")
        body_day = _http_get_json(port, "/app/body/api/day/20250315")
        body_status = _http_get_json(port, "/app/body/api/status")
        body_index_str = json.dumps(body_index)
        assert "202503" in body_index_str or "20250315" in body_index_str, (
            f"Expected March 2025 coverage in /app/body/api/index: {body_index}"
        )
        body_day_str = json.dumps(body_day)
        assert "9600" in body_day_str or "9,600" in body_day_str or "steps" in body_day_str.lower(), (
            f"Expected visible body rows on 20250315 in /app/body/api/day/20250315: {body_day}"
        )
        body_md_0315 = (scratch_journal / "chronicle" / "20250315" / "body.md").read_text(encoding="utf-8")
        assert "to 05:45" in body_md_0315, (
            f"Expected Lent 05:45 wake in chronicle/20250315/body.md, got:\n{body_md_0315}"
        )
        if is_full_year:
            body_aug13 = _http_get_json(port, "/app/body/api/day/20250813")
            body_aug13_str = json.dumps(body_aug13)
            assert "400" in body_aug13_str, (
                f"Expected 400 steps on laid-up day 20250813, got: {body_aug13}"
            )
            body_dec10 = _http_get_json(port, "/app/body/api/day/20251210")
            body_dec10_str = json.dumps(body_dec10)
            assert "1:20 AM" in body_dec10_str or "01:20" in body_dec10_str, (
                f"Expected 1:20 AM bedtime carried from S112b on 20251210, got: {body_dec10}"
            )
            for day_check, expected_wake in (
                ("20250117", "to 06:45"),
                ("20250315", "to 05:45"),
                ("20250629", "to 04:20"),
                ("20250813", "to 04:45"),
                ("20251109", "00:30 to 05:50"),
                ("20251206", "to 07:00"),
                ("20251210", "01:20 to 06:25"),
            ):
                b_md = (scratch_journal / "chronicle" / day_check / "body.md").read_text(encoding="utf-8")
                assert expected_wake in b_md, (
                    f"Expected seasonal wake {expected_wake!r} in chronicle/{day_check}/body.md, got:\n{b_md}"
                )
        assert isinstance(body_status, dict), "Expected dict from /app/body/api/status"

        # 8f. Entities
        entities_state = _http_get_json(port, "/app/entities/api/state")
        entities_overview = _http_get_json(port, "/app/entities/api/overview")
        entities_journal = _http_get_json(port, "/app/entities/api/journal")
        entity_william = _http_get_json(
            port, "/app/entities/api/journal/entity/william_shakespeare"
        )
        entity_heminges = _http_get_json(
            port, "/app/entities/api/journal/entity/john_heminges"
        )
        assert isinstance(entities_state, dict), "Expected dict from /app/entities/api/state"
        assert isinstance(entities_overview, dict), "Expected dict from /app/entities/api/overview"
        assert isinstance(entities_journal, dict), "Expected dict from /app/entities/api/journal"
        assert "William Shakespeare" in json.dumps(entity_william), (
            f"Expected William Shakespeare in entity route: {entity_william}"
        )
        assert "John Heminges" in json.dumps(entity_heminges), (
            f"Expected John Heminges in entity route: {entity_heminges}"
        )

        # 8g. Search
        search_20_pound = _http_get_json(
            port, "/app/search/api/search?" + urllib.parse.urlencode({"q": "twenty pound"})
        )
        search_whitehall = _http_get_json(
            port, "/app/search/api/search?" + urllib.parse.urlencode({"q": "Whitehall"})
        )
        assert search_20_pound.get("total", 0) >= 1 and search_20_pound.get("days"), (
            f"Expected >=1 search hit for 'twenty pound', got: {search_20_pound}"
        )
        assert search_whitehall.get("total", 0) >= 1 and search_whitehall.get("days"), (
            f"Expected >=1 search hit for 'Whitehall', got: {search_whitehall}"
        )

        # 8h. Thinking & Health (assert nothing queued)
        thinking_state = _http_get_json(port, "/app/thinking/api/state")
        health_state = _http_get_json(port, "/app/health/api/state")
        media_backlog = _http_get_json(port, "/app/health/api/media-backlog")
        assert thinking_state.get("saved_lane") is None, (
            f"Expected saved_lane == None in /app/thinking/api/state, got: {thinking_state.get('saved_lane')}"
        )
        work_state = health_state.get("work", {})
        assert work_state.get("inventory") is None, (
            f"Expected work.inventory == None (nothing queued), got: {work_state}"
        )
        assert work_state.get("retry_records") == [], (
            f"Expected empty work.retry_records, got: {work_state}"
        )
        assert health_state.get("backlog", {}).get("stuck_rows") == [], (
            f"Expected zero stuck backlog rows, got: {health_state.get('backlog')}"
        )
        assert health_state.get("agent_errors", {}).get("count") == 0, (
            f"Expected zero agent_errors, got: {health_state.get('agent_errors')}"
        )

        # 9. Re-snapshot talents/* digests and assert zero changes
        talents_after = _snapshot_talents(scratch_journal)
        assert talents_before == talents_after, (
            "talents/* files changed during Convey/indexer/read-back! "
            f"Added={set(talents_after) - set(talents_before)}, "
            f"Removed={set(talents_before) - set(talents_after)}, "
            f"Modified={[k for k in talents_before if talents_before.get(k) != talents_after.get(k)]}"
        )

        return {
            "status": "ok",
            "scratch_journal": str(scratch_journal),
            "port": port,
            "conversion": conversion_summary,
            "year_backdrop_check": year_backdrop_check,
            "contract_check": contract_res.stdout.strip(),
            "home_weeks_verified": home_weeks_verified,
            "named_places_verified": named_places_verified,
            "talents_files_verified_unchanged": len(talents_after),
            "talk_segments_verified_thought": thought_seg_count,
            "william_speaker_labels_verified": william_named_count,
            "search_hits_twenty_pound": int(search_20_pound.get("total", 0)),
            "search_hits_whitehall": int(search_whitehall.get("total", 0)),
            "health_state_keys": sorted(health_state.keys()) if isinstance(health_state, dict) else [],
            "media_backlog_keys": sorted(media_backlog.keys()) if isinstance(media_backlog, dict) else [],
            "lived_in": verify_lived_in(scratch_journal, port) if has_lived_in else None,
            "index_coverage": index_coverage(scratch_journal) if has_lived_in else None,
        }
    finally:
        if convey_proc is not None and convey_proc.poll() is None:
            convey_proc.terminate()
            try:
                convey_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                convey_proc.kill()
                convey_proc.wait(timeout=5)
        if convey_log_file is not None and not convey_log_file.closed:
            convey_log_file.close()
        if not keep_scratch and scratch_base.exists():
            shutil.rmtree(scratch_base, ignore_errors=True)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Run the 3-layer validation and Convey read-back on a scratch copy."
    )
    parser.add_argument(
        "--week",
        type=str,
        default="2025-03-09",
        help="Optional week folder name (retained for CLI compatibility).",
    )
    parser.add_argument(
        "--journal",
        type=Path,
        default=None,
        help="Committed journal directory to copy and validate without re-conversion (defaults to build/journal).",
    )
    parser.add_argument(
        "--content",
        type=Path,
        default=None,
        help="If set, convert this content directory onto --backdrop instead of validating a committed tree.",
    )
    parser.add_argument(
        "--backdrop",
        type=Path,
        default=DEFAULT_BACKDROP_DIR,
        help="Path to the backdrop journal directory (used only when --content is passed).",
    )
    parser.add_argument(
        "--solstone-root",
        type=Path,
        default=DEFAULT_SOLSTONE_ROOT,
        help="Path to the solstone-journal repository",
    )
    parser.add_argument(
        "--solstone-bin",
        type=Path,
        default=None,
        help="Optional explicit path to the solstone binary",
    )
    parser.add_argument(
        "--keep-scratch",
        action="store_true",
        help="Keep the /var/tmp scratch directory after completion",
    )
    args = parser.parse_args(argv)
    if args.content is not None:
        report = run_read_back(
            content_dir=args.content.resolve(),
            backdrop_dir=args.backdrop.resolve(),
            committed_journal=None,
            solstone_root=args.solstone_root.resolve(),
            solstone_bin=args.solstone_bin.resolve() if args.solstone_bin else None,
            keep_scratch=args.keep_scratch,
        )
    else:
        committed = (
            args.journal.resolve()
            if args.journal is not None
            else (PROJECT_ROOT / "build" / "journal").resolve()
        )
        report = run_read_back(
            content_dir=None,
            backdrop_dir=args.backdrop.resolve(),
            committed_journal=committed,
            solstone_root=args.solstone_root.resolve(),
            solstone_bin=args.solstone_bin.resolve() if args.solstone_bin else None,
            keep_scratch=args.keep_scratch,
        )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
