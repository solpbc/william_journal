#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Copyright (c) 2026 sol pbc

"""Deterministic installer for contextual imported files in the William journal.

Installs the 18 canon-reviewed items described in `content/imports/manifest.json`
across all Solstone import kinds (`import.text` notes/documents/transcripts,
`import.document` PDFs, `import.evernote` notes, and `import.image` screenshots),
along with schema-validated `talents/` outputs, health receipts, facet activities,
daily facet entities, clean 2025 `imports/` publication records, rebuilt stream
chains, and deterministic receipt-ordered mtimes.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any
import xml.etree.ElementTree as ET

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from backdrop import PROJECT_ROOT  # type: ignore[import-not-found]
    from contracts import (  # type: ignore[import-not-found]
        DEFAULT_SOLSTONE_REPO,
        ContractRegistry,
    )
    from converter import (  # type: ignore[import-not-found]
        CAST_BY_SLUG,
        FACET_ENTITIES_BY_SLUG,
        _entity_display_name,
        _literal_markdown,
        london_offset_str,
        rebuild_stream_chains,
        to_epoch_ms,
    )
    from stamp import stamp_journal_tree  # type: ignore[import-not-found]
else:
    from .backdrop import PROJECT_ROOT
    from .contracts import DEFAULT_SOLSTONE_REPO, ContractRegistry
    from .converter import (
        CAST_BY_SLUG,
        FACET_ENTITIES_BY_SLUG,
        _entity_display_name,
        _literal_markdown,
        london_offset_str,
        rebuild_stream_chains,
        to_epoch_ms,
    )
    from .stamp import stamp_journal_tree


DEFAULT_IMPORTS_DIR = PROJECT_ROOT / "content" / "imports"
DEFAULT_JOURNAL_DIR = PROJECT_ROOT / "build" / "journal"
EVERNOTE_IMPORT_ID = "20251122_211000"
EVERNOTE_IMPORTED_AT = "2025-11-22T21:10:00.000000"

_TIMED_TURN_RE = re.compile(r"^\[(\d{2}):(\d{2}):(\d{2})\]\s+([^:]+):\s*(.*)$")


def _parse_enex_notes(enex_path: Path) -> list[dict[str, Any]]:
    """Parse an Evernote `.enex` file into title, paragraphs, and tags per note."""
    root = ET.fromstring(enex_path.read_text(encoding="utf-8"))
    notes: list[dict[str, Any]] = []
    for note_el in root.findall("note"):
        title = (note_el.findtext("title") or "").strip()
        tags = [t.text.strip() for t in note_el.findall("tag") if t.text and t.text.strip()]
        raw_content = note_el.findtext("content") or ""
        # Extract inner <en-note> XML body
        paragraphs: list[str] = []
        try:
            en_root = ET.fromstring(raw_content.strip())
            for child in en_root:
                text = "".join(child.itertext()).strip()
                if text:
                    paragraphs.append(text)
            if not paragraphs:
                whole = "".join(en_root.itertext()).strip()
                if whole:
                    paragraphs.append(whole)
        except ET.ParseError:
            clean = re.sub(r"<[^>]+>", "\n", raw_content)
            paragraphs = [ln.strip() for ln in clean.splitlines() if ln.strip()]
        notes.append({"title": title, "paragraphs": paragraphs, "tags": tags})
    return notes


def _render_evernote_markdown(note: dict[str, Any]) -> str:
    """Format one Evernote note to match `solstone` Evernote importer output."""
    title = note["title"]
    lines = [f"## {title}", f"Source: {title}.md", ""]
    lines.append("\n\n".join(note["paragraphs"]))
    if note["tags"]:
        lines.append("")
        lines.append("tags: " + ", ".join(note["tags"]))
    return "\n".join(lines).rstrip() + "\n"


def _parse_timed_transcript(
    text: str,
    import_id: str,
    source_filename: str,
    source_ms: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Convert `[HH:MM:SS] Speaker: Text` into `conversation_transcript.jsonl` records."""
    records: list[dict[str, Any]] = [
        {
            "imported": {"id": import_id},
            "raw": f"../../../imports/{import_id}/{source_filename}",
        }
    ]
    speakers: list[str] = []
    seen_speakers: set[str] = set()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = _TIMED_TURN_RE.match(line)
        if match:
            hh, mm, ss = int(match.group(1)), int(match.group(2)), int(match.group(3))
            offset_sec = hh * 3600 + mm * 60 + ss
            speaker = match.group(4).strip()
            utterance = match.group(5).strip()
            records.append(
                {
                    "start": f"{hh:02d}:{mm:02d}:{ss:02d}",
                    "source_ms": source_ms + offset_sec * 1000,
                    "speaker": speaker,
                    "text": utterance,
                    "source": "import",
                }
            )
            if speaker not in seen_speakers:
                seen_speakers.add(speaker)
                speakers.append(speaker)
        else:
            records.append(
                {
                    "start": "00:00:00",
                    "source_ms": source_ms,
                    "text": line,
                    "source": "import",
                }
            )
    return records, speakers


def _screenshot_transcript_md(title: str, day_iso: str, description: str) -> str:
    """Render `screenshot_transcript.md` in Solstone's standard image transcript shape."""
    lines = [
        f"# {title}",
        "",
        "**Type:** Image",
        "**Format:** PNG",
        "**Dimensions:** 1200×896",
        f"**Date:** {day_iso}",
        "",
        "---",
        "",
        "> [image description — model-derived]",
    ]
    for ln in description.strip().split("\n"):
        lines.append(">" if ln == "" else f"> {_literal_markdown(ln)}")
    return "\n".join(lines).rstrip() + "\n"


def _source_field_for_item(stream: str, import_kind: str | None) -> str:
    if stream == "import.image":
        return "screen"
    if import_kind == "transcripts":
        return "transcript"
    return "other"


def _level_for_density(density: str) -> str:
    if density == "active":
        return "high"
    if density == "low_change":
        return "medium"
    return "low"


def _level_value(level: str) -> float:
    """Match `level_value` in `solstone-core-system/src/activity_state.rs`."""
    return {"high": 1.0, "low": 0.25}.get(level, 0.5)


def _build_talents_and_activity(
    item: dict[str, Any],
    day_key: str,
    segment_key: str,
    seg_end_ms: int,
    seg_end_utc: str,
    predecessor_seg_key: str | None,
    transcript_speakers: list[str],
    registry: ContractRegistry,
) -> tuple[dict[str, Any], dict[str, str], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """Build schema-validated `sense.json`, 7-8 projections, `documents.json`, activity, and daily entities."""
    stream = item["stream"]
    import_kind = item.get("import_kind")
    is_transcript = import_kind == "transcripts"
    source_tag = _source_field_for_item(stream, import_kind)
    level = _level_for_density(item["density"])

    entities: list[dict[str, Any]] = []
    schema_participation: list[dict[str, Any]] = []
    activity_participation: list[dict[str, Any]] = []
    detected_entities: list[dict[str, Any]] = []

    for person in item["people"]:
        slug = person["slug"]
        if slug not in CAST_BY_SLUG and slug not in FACET_ENTITIES_BY_SLUG:
            raise ValueError(f"{item['id']}: unknown entity slug {slug!r}")
        role = person["role"]
        ctx = person["context"]
        display_name = _entity_display_name(slug)
        entities.append(
            {
                "type": "Person",
                "name": display_name,
                "role": role,
                "source": source_tag,
                "context": ctx,
                "level": "high" if role == "attendee" else "medium",
            }
        )
        schema_participation.append(
            {
                "name": display_name,
                "role": role,
                "source": source_tag,
                "confidence": 0.95,
                "context": ctx,
                "entity_id": None,
            }
        )
        activity_participation.append(
            {
                "name": display_name,
                "role": role,
                "source": source_tag,
                "confidence": 0.95,
                "context": ctx,
                "entity_id": slug,
            }
        )
        ent_type = FACET_ENTITIES_BY_SLUG[slug].entity_type if slug in FACET_ENTITIES_BY_SLUG else "Person"
        detected_entities.append(
            {
                "id": slug,
                "name": display_name,
                "type": ent_type,
                "description": ctx,
                "last_seen": day_key,
            }
        )

    for extra in item.get("also_mentioned", []):
        entities.append(
            {
                "type": extra["type"],
                "name": extra["name"],
                "role": "mentioned",
                "source": source_tag,
                "context": f"Mentioned in {item['heading_title']}",
                "level": "medium",
            }
        )

    topics = list(item.get("sense_topics", []))[:12]
    quotes = [{"speaker": q["speaker"], "text": q["text"]} for q in item.get("sense_quotes", [])]
    speakers = list(transcript_speakers)[:16] if is_transcript else []

    sense_obj: dict[str, Any] = {
        "density": item["density"],
        "content_type": item["content_type"],
        "activity_summary": item["sense_summary"],
        "entities": entities[:40],
        "facets": [
            {
                "facet": item["facet"],
                "activity": item["activity_title"],
                "level": level,
            }
        ],
        "speculative_facet": None,
        "meeting_detected": is_transcript,
        "speakers": speakers,
        "recommend": {
            "screen_record": False,
            "speaker_attribution": False,
        },
        "topics": topics,
        "quotes": quotes,
    }
    registry.validate_talent_output("sense", sense_obj, f"{day_key}/{stream}/{segment_key}/sense.json")

    projections: dict[str, str] = {}
    projections["activity.md"] = sense_obj["activity_summary"] + "\n"
    projections["facets.json"] = json.dumps(sense_obj["facets"], indent=2) + "\n"
    projections["density.json"] = (
        json.dumps(
            {
                "classification": sense_obj["density"],
                "timestamp": seg_end_utc,
            },
            indent=2,
        )
        + "\n"
    )
    if sense_obj["entities"]:
        sense_md_lines = ["# Sense Entities", ""]
        for ent in sense_obj["entities"]:
            sense_md_lines.append(
                f"- {ent['type']} — {ent['name']} (role={ent['role']}, source={ent['source']}) — {ent['context']}"
            )
        projections["sense.md"] = "\n".join(sense_md_lines) + "\n"

    if is_transcript:
        projections["speakers.json"] = json.dumps(speakers, indent=2) + "\n"

    projections["change.json"] = (
        json.dumps(
            {
                "change_class": "substantive",
                "predecessor": predecessor_seg_key,
                "timestamp": seg_end_utc,
            },
            indent=2,
        )
        + "\n"
    )

    if topics or quotes:
        topic_lines: list[str] = []
        if topics:
            topic_lines.append("## Topics")
            for topic in topics:
                topic_lines.append(f"- {topic}")
        if quotes:
            if topic_lines:
                topic_lines.append("")
            topic_lines.append("## Quotes")
            for quote in quotes:
                topic_lines.append(f"- {quote['speaker']}: {quote['text']}")
        projections["topics.md"] = "\n".join(topic_lines) + "\n"

    docs_obj: dict[str, Any] = {
        "overview": item["sense_summary"][:3000],
        "parties": [
            {
                "name": _entity_display_name(p["slug"])[:256],
                "role": p["role"][:512],
                "formal_term": _entity_display_name(p["slug"])[:256],
                "appointment_tier": "not_applicable",
                "context": p["context"][:1000],
            }
            for p in item["people"][:10]
        ],
        "key_provisions": [
            {
                "type": "other",
                "text": t[:1500],
                "applies_to": "William Shakespeare",
            }
            for t in topics[:5]
        ],
        "assets": [
            {
                "name": m["name"][:512],
                "asset_type": "other",
                "disposition": item["activity_title"][:1500],
            }
            for m in item.get("also_mentioned", [])[:5]
        ],
        "conditions": [],
        "important_dates": [
            {
                "date": item["day_iso"],
                "meaning": item["heading_title"][:1000],
            }
        ],
        "summary": item["activity_title"][:3000],
    }
    registry.validate_talent_output("documents", docs_obj, f"{day_key}/{stream}/{segment_key}/documents.json")

    story_relations = [
        {
            "from": _entity_display_name(rel["from"]),
            "to": _entity_display_name(rel["to"]),
            "kind": rel["kind"],
            "note": rel["note"][:300],
            "quote": rel["quote"][:400] if rel.get("quote") is not None else None,
        }
        for rel in item.get("relations", [])[:12]
    ]
    story_obj: dict[str, Any] = {
        "body": item["activity_story"][:4000],
        "topics": [t[:48].rstrip() for t in topics[:10]],
        "confidence": 0.95,
        "relations": story_relations,
    }
    activity_id = f"import_{item['id'].replace('-', '_')}"
    registry.validate_talent_output("story", story_obj, f"{day_key}/{activity_id}/story")

    participation_envelope = {
        "participation": schema_participation,
        "participation_confidence": 0.95,
    }
    registry.validate_talent_output(
        "participation", participation_envelope, f"{day_key}/{activity_id}/participation"
    )

    activity_record: dict[str, Any] = {
        "id": activity_id,
        "activity": item["content_type"],
        "title": item["activity_title"],
        "description": item["heading_title"],
        "details": "",
        "facet": item["facet"],
        "day": day_key,
        "stream": stream,
        "segments": [segment_key],
        "level_avg": _level_value(level),
        "created_at": seg_end_ms,
        "updated_at": seg_end_ms,
        "story": story_obj,
        "participation": activity_participation,
        "relations": story_relations,
    }

    return sense_obj, projections, docs_obj, activity_record, detected_entities


def _upsert_health_receipts(
    journal_dir: Path,
    day_key: str,
    day_iso: str,
    new_receipts_by_seg: list[tuple[str, str, str]],
) -> None:
    """Idempotently merge segment thinking receipts into `chronicle/<day>/health/<ts>_segment.jsonl`."""
    health_dir = journal_dir / "chronicle" / day_key / "health"
    health_dir.mkdir(parents=True, exist_ok=True)
    existing_files = sorted(health_dir.glob("*_segment.jsonl"))
    if existing_files:
        receipt_file = existing_files[0]
        rows = [
            json.loads(line)
            for line in receipt_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        max_ts = max((int(r["ts"]) for r in rows if isinstance(r.get("ts"), int)), default=0)
    else:
        offset = london_offset_str(date.fromisoformat(day_iso))
        base_ts_ms = to_epoch_ms(f"{day_iso}T23:55:00{offset}")
        receipt_file = health_dir / f"{base_ts_ms}_segment.jsonl"
        rows = []
        max_ts = base_ts_ms

    target_coords = {(day_key, stream, seg_key) for stream, seg_key, _ in new_receipts_by_seg}
    kept = [
        r
        for r in rows
        if (r.get("day"), r.get("stream"), r.get("segment")) not in target_coords
    ]
    offset = london_offset_str(date.fromisoformat(day_iso))
    default_base_ms = to_epoch_ms(f"{day_iso}T23:55:00{offset}")
    base_ts = max((int(r["ts"]) for r in kept if isinstance(r.get("ts"), int)), default=default_base_ms)
    # Round up to next multiple of 10 ms above existing timestamps for clean ordering
    cursor = ((base_ts // 10) + 1) * 10
    for stream, seg_key, density in sorted(new_receipts_by_seg):
        kept.extend(
            [
                {
                    "ts": cursor,
                    "event": "sense.complete",
                    "mode": "segment",
                    "day": day_key,
                    "stream": stream,
                    "segment": seg_key,
                    "density": density,
                },
                {
                    "ts": cursor + 1,
                    "event": "sense.change_detect",
                    "mode": "segment",
                    "day": day_key,
                    "stream": stream,
                    "segment": seg_key,
                    "change_class": "substantive",
                },
                {
                    "ts": cursor + 2,
                    "event": "talent.complete",
                    "mode": "segment",
                    "day": day_key,
                    "stream": stream,
                    "segment": seg_key,
                    "name": "documents",
                },
            ]
        )
        cursor += 10

    receipt_file.write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in kept),
        encoding="utf-8",
    )


def _upsert_facet_activities(
    journal_dir: Path,
    facet: str,
    day_key: str,
    new_records: list[dict[str, Any]],
) -> None:
    """Idempotently merge activity records into `facets/<facet>/activities/<day>.jsonl`."""
    act_dir = journal_dir / "facets" / facet / "activities"
    act_dir.mkdir(parents=True, exist_ok=True)
    act_path = act_dir / f"{day_key}.jsonl"

    existing: list[dict[str, Any]] = []
    if act_path.is_file():
        existing = [
            json.loads(line)
            for line in act_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    new_ids = {rec["id"] for rec in new_records}
    merged = [rec for rec in existing if rec.get("id") not in new_ids]
    merged.extend(new_records)
    merged.sort(key=lambda r: (r.get("segments", [""])[0], r.get("id", "")))
    act_path.write_text(
        "".join(json.dumps(rec, sort_keys=True, ensure_ascii=False) + "\n" for rec in merged),
        encoding="utf-8",
    )


def _upsert_facet_entities(
    journal_dir: Path,
    facet: str,
    day_key: str,
    new_entities: list[dict[str, Any]],
) -> None:
    """Idempotently merge daily detected entities into `facets/<facet>/entities/<day>.jsonl`."""
    ent_dir = journal_dir / "facets" / facet / "entities"
    ent_dir.mkdir(parents=True, exist_ok=True)
    ent_path = ent_dir / f"{day_key}.jsonl"

    by_id: dict[str, dict[str, Any]] = {}
    if ent_path.is_file():
        for line in ent_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if "id" in row:
                    by_id[row["id"]] = row
    for ent in new_entities:
        # Preserve richer existing daily entity description if already present
        if ent["id"] not in by_id:
            by_id[ent["id"]] = ent
    ordered = [by_id[k] for k in sorted(by_id)]
    ent_path.write_text(
        "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in ordered),
        encoding="utf-8",
    )


def _write_import_publication(
    journal_dir: Path,
    *,
    import_id: str,
    source_type: str,
    source_hash: str,
    imported_at: str,
    started_at_ms: int,
    segments: list[dict[str, Any]],
    files_created: list[str],
    days_affected: list[str],
    extra_files: dict[str, bytes] | None = None,
    content_manifest_row: dict[str, Any] | None = None,
    source_hint: str | None = None,
) -> None:
    """Write clean 2025 `imports/<import_id>/` publication files without lock files or `/var/tmp` paths."""
    import_dir = journal_dir / "imports" / import_id
    import_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "import_id": import_id,
        "source_type": source_type,
        "source_hash": source_hash,
        "entry_count": len(segments),
        "days_affected": sorted(set(days_affected)),
        "files_created": files_created,
        "imported_at": imported_at,
        "imported_via": "native",
        "link_id": None,
        "observer_handle": None,
    }
    (import_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    published = {
        "schema": "solstone.import.publication.v2",
        "status": "success",
        "segments": segments,
        "indexing": {"queued": [], "declined": [], "errored": []},
        "day_markers": [
            {"day": d, "outcome": {"status": "touched"}}
            for d in sorted(set(days_affected))
        ],
    }
    (import_dir / "imported.json").write_text(
        json.dumps(published, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    if source_type in ("text", "document"):
        import_meta: dict[str, Any] = {
            "originals_policy_v1": True,
            "import_id": import_id,
            "source_timestamp": import_id,
            "source_hash": source_hash,
            "attempt": {
                "attempt_id": f"{import_id}:1",
                "generation": 1,
                "state": "completed",
                "started_at_ms": started_at_ms,
                "finished_at_ms": started_at_ms + 210,
                "duration_ms": 210,
            },
            "task_id": import_id,
        }
        if source_hint is not None:
            import_meta["source_hint"] = source_hint
            import_meta["keep_original_at_import"] = False
        (import_dir / "import.json").write_text(
            json.dumps(import_meta, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    if content_manifest_row is not None:
        (import_dir / "content_manifest.jsonl").write_text(
            json.dumps(content_manifest_row, separators=(",", ":"), ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    if extra_files:
        for fname, raw_bytes in extra_files.items():
            (import_dir / fname).write_bytes(raw_bytes)


def install_imports(
    journal_dir: Path,
    imports_dir: Path = DEFAULT_IMPORTS_DIR,
    solstone_repo: Path = DEFAULT_SOLSTONE_REPO,
) -> dict[str, Any]:
    """Install all contextual imported items from `imports_dir/manifest.json` onto `journal_dir`."""
    manifest_path = imports_dir / "manifest.json"
    files_dir = imports_dir / "files"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing imports manifest: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    ruleset_version = int(manifest.get("ruleset_version", 7))
    items: list[dict[str, Any]] = manifest["items"]
    registry = ContractRegistry(solstone_repo=solstone_repo)

    enex_cache: dict[str, list[dict[str, Any]]] = {}
    predecessor_by_stream: dict[str, str | None] = {}
    receipts_by_day: dict[str, tuple[str, list[tuple[str, str, str]]]] = {}
    activities_by_facet_day: dict[tuple[str, str], list[dict[str, Any]]] = {}
    entities_by_facet_day: dict[tuple[str, str], list[dict[str, Any]]] = {}

    evernote_segments: list[dict[str, Any]] = []
    evernote_files_created: list[str] = []
    evernote_days: list[str] = []
    evernote_hash = ""

    installed_coords: list[str] = []
    by_stream: dict[str, int] = {}

    # Sort deterministically by (day_iso, start_hhmm, id)
    ordered_items = sorted(items, key=lambda x: (x["day_iso"], x["start_hhmm"], x["id"]))

    for item in ordered_items:
        source_file = item["source_file"]
        source_path = files_dir / source_file
        if not source_path.is_file():
            raise FileNotFoundError(f"{item['id']}: missing source file {source_path}")
        source_bytes = source_path.read_bytes()
        source_sha = hashlib.sha256(source_bytes).hexdigest()

        day_iso: str = item["day_iso"]
        day_key = day_iso.replace("-", "")
        hh, mm = [int(part) for part in item["start_hhmm"].split(":")]
        clock = f"{hh:02d}{mm:02d}00"
        duration_sec = int(item["duration_sec"])
        segment_key = f"{clock}_{duration_sec}"
        stream: str = item["stream"]
        import_kind: str | None = item.get("import_kind")
        import_id = EVERNOTE_IMPORT_ID if stream == "import.evernote" else f"{day_key}_{clock}"

        offset = london_offset_str(date.fromisoformat(day_iso))
        source_iso = f"{day_iso}T{hh:02d}:{mm:02d}:00{offset}"
        source_ms = to_epoch_ms(source_iso)
        seg_end_ms = source_ms + duration_sec * 1000
        seg_end_utc = datetime.fromtimestamp(seg_end_ms / 1000.0, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        imported_at_iso = f"{day_iso}T{hh:02d}:{mm:02d}:00.000000"

        seg_dir = journal_dir / "chronicle" / day_key / stream / segment_key
        talents_dir = seg_dir / "talents"
        talents_dir.mkdir(parents=True, exist_ok=True)

        transcript_speakers: list[str] = []
        primary_rel = ""

        if stream == "import.text":
            raw_text = source_bytes.decode("utf-8")
            if import_kind == "notes":
                (seg_dir / "note_transcript.md").write_text(raw_text, encoding="utf-8")
                primary_rel = f"chronicle/{day_key}/{stream}/{segment_key}/note_transcript.md"
            elif import_kind == "documents":
                (seg_dir / "document_transcript.md").write_text(raw_text, encoding="utf-8")
                primary_rel = f"chronicle/{day_key}/{stream}/{segment_key}/document_transcript.md"
            elif import_kind == "transcripts":
                records, transcript_speakers = _parse_timed_transcript(
                    raw_text, import_id, source_file, source_ms
                )
                (seg_dir / "conversation_transcript.jsonl").write_text(
                    "".join(json.dumps(r, separators=(",", ":"), ensure_ascii=False) + "\n" for r in records),
                    encoding="utf-8",
                )
                primary_rel = f"chronicle/{day_key}/{stream}/{segment_key}/conversation_transcript.jsonl"
            else:
                raise ValueError(f"{item['id']}: unsupported import.text kind {import_kind!r}")

            kind_payload = {
                "kind": import_kind,
                "reasons": list(item["triage_reasons"]),
                "ruleset_version": ruleset_version,
                "import_id": import_id,
                "source_ms": source_ms,
            }
            (seg_dir / "import_kind.json").write_text(
                json.dumps(kind_payload, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            _write_import_publication(
                journal_dir,
                import_id=import_id,
                source_type="text",
                source_hash=source_sha,
                imported_at=imported_at_iso,
                started_at_ms=source_ms,
                segments=[
                    {
                        "day": day_key,
                        "segment": segment_key,
                        "stream": stream,
                        "outcome": {
                            "status": "bound",
                            "prev_day": None,
                            "prev_segment": None,
                            "seq": 1,
                        },
                    }
                ],
                files_created=[primary_rel],
                days_affected=[day_key],
                extra_files={source_file: source_bytes},
            )

        elif stream == "import.document":
            extracted_md = item["extracted_markdown"]
            (seg_dir / "document_transcript.md").write_text(extracted_md, encoding="utf-8")
            doc_source = {
                "source_name": source_file,
                "container_import_id": None,
                "import_id": import_id,
                "extraction_complete": True,
                "source_sha256": source_sha,
                "source_timestamp": source_ms // 1000,
            }
            (seg_dir / "document_source.json").write_text(
                json.dumps(doc_source, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            primary_rel = f"chronicle/{day_key}/{stream}/{segment_key}/document_transcript.md"
            stem = Path(source_file).stem
            content_manifest_row = {
                "id": "document-0",
                "title": stem,
                "date": day_key,
                "type": "document",
                "preview": extracted_md[:200],
                "meta": {
                    "page_count": 1,
                    "engine": "pdfium 151.0.7920.0 (native)",
                    "timestamp_source": "owner",
                    "text_layer_pages": 1,
                    "model_extracted_pages": 0,
                    "unavailable_pages": 0,
                    "image_described_pages": 0,
                    "model_calls": 0,
                    "warnings": [],
                },
                "segments": [{"day": day_key, "key": segment_key}],
            }
            _write_import_publication(
                journal_dir,
                import_id=import_id,
                source_type="document",
                source_hash=source_sha,
                imported_at=imported_at_iso,
                started_at_ms=source_ms,
                segments=[
                    {
                        "day": day_key,
                        "segment": segment_key,
                        "stream": stream,
                        "outcome": {
                            "status": "bound",
                            "prev_day": None,
                            "prev_segment": None,
                            "seq": 1,
                        },
                    }
                ],
                files_created=[primary_rel],
                days_affected=[day_key],
                content_manifest_row=content_manifest_row,
                source_hint="document",
            )

        elif stream == "import.evernote":
            if source_file not in enex_cache:
                enex_cache[source_file] = _parse_enex_notes(source_path)
            note_idx = int(item["enex_note_index"])
            note = enex_cache[source_file][note_idx]
            (seg_dir / "note_transcript.md").write_text(
                _render_evernote_markdown(note), encoding="utf-8"
            )
            primary_rel = f"chronicle/{day_key}/{stream}/{segment_key}/note_transcript.md"
            evernote_hash = source_sha
            evernote_files_created.append(primary_rel)
            evernote_days.append(day_key)
            prev_ev = evernote_segments[-1] if evernote_segments else None
            evernote_segments.append(
                {
                    "day": day_key,
                    "segment": segment_key,
                    "stream": stream,
                    "outcome": {
                        "status": "bound",
                        "prev_day": prev_ev["day"] if prev_ev else None,
                        "prev_segment": prev_ev["segment"] if prev_ev else None,
                        "seq": len(evernote_segments) + 1,
                    },
                }
            )

        elif stream == "import.image":
            (seg_dir / "original.screenshot.png").write_bytes(source_bytes)
            image_meta = {
                "schema": 1,
                "time_source": "owner",
                "original_filename": source_file,
            }
            (seg_dir / "image_meta.json").write_text(
                json.dumps(image_meta, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            kind_payload = {
                "kind": "screen_text",
                "reasons": list(item["triage_reasons"]),
                "ruleset_version": ruleset_version,
            }
            (seg_dir / "import_kind.json").write_text(
                json.dumps(kind_payload, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            (seg_dir / "screenshot_transcript.md").write_text(
                _screenshot_transcript_md(
                    item["heading_title"], day_iso, item["screenshot_description"]
                ),
                encoding="utf-8",
            )
            primary_rel = f"chronicle/{day_key}/{stream}/{segment_key}/screenshot_transcript.md"
            _write_import_publication(
                journal_dir,
                import_id=import_id,
                source_type="image",
                source_hash=source_sha,
                imported_at=imported_at_iso,
                started_at_ms=source_ms,
                segments=[
                    {
                        "day": day_key,
                        "segment": segment_key,
                        "stream": stream,
                        "outcome": {
                            "status": "bound",
                            "prev_day": None,
                            "prev_segment": None,
                            "seq": 1,
                        },
                    }
                ],
                files_created=[primary_rel],
                days_affected=[day_key],
            )
        else:
            raise ValueError(f"{item['id']}: unsupported stream {stream!r}")

        # Build and write talents/
        pred_key = predecessor_by_stream.get(stream)
        sense_obj, projections, docs_obj, activity_record, detected_entities = (
            _build_talents_and_activity(
                item=item,
                day_key=day_key,
                segment_key=segment_key,
                seg_end_ms=seg_end_ms,
                seg_end_utc=seg_end_utc,
                predecessor_seg_key=pred_key,
                transcript_speakers=transcript_speakers,
                registry=registry,
            )
        )
        predecessor_by_stream[stream] = segment_key

        (talents_dir / "sense.json").write_text(
            json.dumps(sense_obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        for proj_name, proj_body in projections.items():
            (talents_dir / proj_name).write_text(proj_body, encoding="utf-8")
        (talents_dir / "documents.json").write_text(
            json.dumps(docs_obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

        # Accumulate day-level health receipts, facet activities, and facet entities
        receipts_by_day.setdefault(day_key, (day_iso, []))[1].append(
            (stream, segment_key, item["density"])
        )
        activities_by_facet_day.setdefault((item["facet"], day_key), []).append(activity_record)
        entities_by_facet_day.setdefault((item["facet"], day_key), []).extend(detected_entities)

        installed_coords.append(f"{day_key}/{stream}/{segment_key}")
        by_stream[stream] = by_stream.get(stream, 0) + 1

    # Write shared Evernote publication record
    if evernote_segments:
        ev_ms = to_epoch_ms("2025-11-22T21:10:00+00:00")
        _write_import_publication(
            journal_dir,
            import_id=EVERNOTE_IMPORT_ID,
            source_type="evernote",
            source_hash=evernote_hash,
            imported_at=EVERNOTE_IMPORTED_AT,
            started_at_ms=ev_ms,
            segments=evernote_segments,
            files_created=evernote_files_created,
            days_affected=evernote_days,
        )

    # Upsert health receipts, facet activities, and facet daily entities
    for day_key, (day_iso, seg_tuples) in sorted(receipts_by_day.items()):
        _upsert_health_receipts(journal_dir, day_key, day_iso, seg_tuples)
    for (facet, day_key), recs in sorted(activities_by_facet_day.items()):
        _upsert_facet_activities(journal_dir, facet, day_key, recs)
    for (facet, day_key), ents in sorted(entities_by_facet_day.items()):
        _upsert_facet_entities(journal_dir, facet, day_key, ents)

    # Rebuild chronological stream chains & stamp deterministic mtimes
    rebuild_stream_chains(journal_dir, registry)
    stamp_summary = stamp_journal_tree(journal_dir)

    return {
        "installed": len(installed_coords),
        "by_stream": dict(sorted(by_stream.items())),
        "days_touched": sorted(receipts_by_day.keys()),
        "coordinates": installed_coords,
        "stamp": stamp_summary,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Install contextual imported files onto a William journal tree."
    )
    parser.add_argument(
        "--journal",
        type=Path,
        default=DEFAULT_JOURNAL_DIR,
        help="Target journal directory (defaults to build/journal).",
    )
    parser.add_argument(
        "--imports",
        type=Path,
        default=DEFAULT_IMPORTS_DIR,
        help="Imports content directory holding manifest.json and files/.",
    )
    parser.add_argument(
        "--solstone-repo",
        type=Path,
        default=DEFAULT_SOLSTONE_REPO,
        help="Path to the solstone-journal checkout holding schema contracts.",
    )
    args = parser.parse_args(argv)
    summary = install_imports(
        journal_dir=args.journal.resolve(),
        imports_dir=args.imports.resolve(),
        solstone_repo=args.solstone_repo.resolve(),
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
