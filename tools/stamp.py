#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Copyright (c) 2026 sol pbc

"""Deterministic post-checkout mtime stamp for committed William journal trees.

Why this exists:
`solstone-journal`'s `segment_thinking_is_current` (`completion.rs:119-128`) and
`newest_segment_input_ms` (`scan.rs:636-672`) compare the filesystem `mtime` of
each segment's extract files (`chronicle/<day>/<stream>/<seg>/*`) against the
`sense_input_ms` timestamp recorded inside `chronicle/<day>/health/<ts>_segment.jsonl`
(`newest < read_from`). Because Git does not preserve file `mtime`s across clones
or checkouts, a freshly checked-out journal tree has wall-clock checkout `mtime`s
that are newer than the historical receipt timestamps in `<ts>_segment.jsonl`.

Running `stamp_journal_tree(journal_root)` (or `python3 stamp.py --week 2025-03-09`)
reads each day's committed `chronicle/<day>/health/*_segment.jsonl` receipt,
finds the minimum receipt timestamp `min_ts_ms`, and sets `os.utime` on that
day's segment files to `(min_ts_ms / 1000.0) - 300.0` without modifying a single
byte of any tracked file.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
DEFAULT_WEEK = "2025-03-09"


def stamp_journal_tree(journal_root: Path) -> dict[str, Any]:
    """Stamp segment file mtimes in `journal_root` strictly before each day's health receipt `ts`."""
    chronicle_root = journal_root / "chronicle"
    days_stamped = 0
    segments_stamped = 0
    files_stamped = 0
    earliest_extract_mtime: float | None = None

    if chronicle_root.is_dir():
        for day_dir in sorted(chronicle_root.iterdir()):
            if not day_dir.is_dir():
                continue
            health_dir = day_dir / "health"
            if not health_dir.is_dir():
                continue
            receipt_files = sorted(health_dir.glob("*_segment.jsonl"))
            if not receipt_files:
                continue

            ts_values: list[int] = []
            for rf in receipt_files:
                for line in rf.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    if isinstance(row, dict) and isinstance(row.get("ts"), int):
                        ts_values.append(row["ts"])

            if not ts_values:
                continue

            min_ts_ms = min(ts_values)
            max_ts_ms = max(ts_values)
            extract_mtime_sec = (min_ts_ms / 1000.0) - 300.0
            receipt_mtime_sec = max_ts_ms / 1000.0

            if earliest_extract_mtime is None or extract_mtime_sec < earliest_extract_mtime:
                earliest_extract_mtime = extract_mtime_sec

            days_stamped += 1

            for stream_dir in sorted(day_dir.iterdir()):
                if not stream_dir.is_dir() or stream_dir.name in ("health", "talents"):
                    continue
                for seg_dir in sorted(stream_dir.iterdir()):
                    if not seg_dir.is_dir():
                        continue
                    segments_stamped += 1
                    for path in sorted(seg_dir.rglob("*")):
                        if path.is_file():
                            os.utime(path, (extract_mtime_sec, extract_mtime_sec))
                            files_stamped += 1

            day_talents_dir = day_dir / "talents"
            if day_talents_dir.is_dir():
                for path in sorted(day_talents_dir.rglob("*")):
                    if path.is_file():
                        os.utime(path, (receipt_mtime_sec, receipt_mtime_sec))
                        files_stamped += 1

            for rf in receipt_files:
                os.utime(rf, (receipt_mtime_sec, receipt_mtime_sec))
                files_stamped += 1

    if earliest_extract_mtime is not None:
        streams_dir = journal_root / "streams"
        if streams_dir.is_dir():
            for path in sorted(streams_dir.glob("*.json")):
                if path.is_file():
                    os.utime(path, (earliest_extract_mtime, earliest_extract_mtime))
                    files_stamped += 1

    return {
        "journal": str(journal_root),
        "days_stamped": days_stamped,
        "segments_stamped": segments_stamped,
        "files_stamped": files_stamped,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Stamp deterministic mtimes on a William journal tree from its committed health receipts."
    )
    parser.add_argument(
        "--week",
        type=str,
        default=None,
        help="Optional week folder name (retained for CLI compatibility).",
    )
    parser.add_argument(
        "--journal",
        type=Path,
        default=None,
        help="Explicit journal root directory (defaults to build/journal).",
    )
    args = parser.parse_args(argv)
    journal_root = (
        args.journal.resolve()
        if args.journal is not None
        else (PROJECT_ROOT / "build" / "journal").resolve()
    )
    summary = stamp_journal_tree(journal_root)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
