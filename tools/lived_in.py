#!/usr/bin/env python3
"""Install the William-only stored layers after conversion, before indexing."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
import re
import shutil
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT = Path(__file__).resolve().parents[1]
JOURNAL = PROJECT / "build" / "journal"
MARK_FILES = ("cert.pem", "private.pem", "state.json")
GRANT_ID = "Ui6UEpHGQomNbwmlyfxlsQ"
CONNECTION = f"oauth:{GRANT_ID}"
SOURCE = hashlib.sha256(f"solstone-agent-memory-source-v1\n{CONNECTION}".encode()).hexdigest()
# Every kind an owner can allow (journal kinds list): this journal exists to show agent access.
CATEGORIES = [
    "transcripts", "entities", "profile_pics", "facets", "screen_text", "body",
    "notes", "documents", "calendar", "places", "photos",
]
CONNECTED_AT = "2025-01-03T19:45:00Z"

# The authored summaries already reflect these facts. The edits retain the owner's account.
CORRECTIONS = (
    ("20250315", "company", "meeting_091000_600", "I heard the twenty pound counted in the passage. Kemp carried the bag away, still shut."),
    ("20250810", "stratford", "meeting_142000_120", "It was the twins who raced the boats. Susanna kept the book off the grass."),
    ("20251022", "company", "meeting_162000_360", "George Bryan brought word in the yard. Sunday was when the Earl died; Wednesday was when I heard it."),
)
POSSIBLE_NAMES = (
    ("20251206", "170500_720", 6, "Humphrey", "humphrey_larkham"),
    ("20251206", "170500_720", 10, "A church hat", "dorcas_ansell"),
)
# One plausible search per visit. The activity id makes the subject checkable.
VISITS = (
    ("20250103", "company", "meeting_120500_480", "twenty pounds"),
    ("20250315", "company", "meeting_091000_600", "twenty pound warrant"),
    ("20250615", "household", "meeting_092000_720", "glass St Helen's"),
    ("20250810", "stratford", "meeting_142000_120", "boats grass"),
    ("20251022", "company", "meeting_162000_360", "Arundel Tower"),
    ("20251206", "company", "meeting_170500_720", "forty shillings share"),
)
NOTES = (
    ("20250315", "The warrant's twenty pound and the thirty-seven shillings and sixpence William took that day are separate entries. Keep both figures with their source."),
    ("20250810", "Susanna asked why the lovers do not use the door after the twins raced their bark boats. William's answer was that the book does not say."),
    ("20251022", "George Bryan told William in the yard on 22 October that Philip Howard died on Sunday in the Tower. Keep the day William heard the news with the source."),
    ("20251206", "For the 6 December account, keep the twelve pound thirteen box and the forty-shilling share as two figures. Heminges expressly refused to derive the share from the box."),
)


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def rows_at(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def iso_at(day: str, hours: str) -> str:
    local = datetime.fromisoformat(f"{day[:4]}-{day[4:6]}-{day[6:]}T{hours}")
    return local.replace(tzinfo=ZoneInfo("Europe/London")).astimezone(UTC).isoformat().replace("+00:00", "Z")


def install_agent(journal: Path) -> None:
    client = {
        "id": "VAsWlhHBRw2fmGiSbnPQdg",
        "client_id": "solstone_william_claude_demo",
        "redirect_uris": ["http://127.0.0.1:9/callback"],
        "client_name": "Claude",
        "source": "william-demo",
        "created_at": CONNECTED_AT,
        "last_used_at": "2025-12-06T21:16:00Z",
        "revocation_generation": 0,
    }
    grant = {
        "id": GRANT_ID,
        "client_record_id": client["id"],
        "client_id": client["client_id"],
        # Independently sampled verifier-shaped bytes. No underlying token was issued.
        "access_verifier": "-hmu_D3rErHzaH6W4-uBOVX6jIWjcHRm9hxj6MNmmUk",
        "refresh_verifier": "jTje_yCJG1h4AtqrgtiApmU4OgKC_IKGyOB_FCx2zrQ",
        "refresh_generation": 0,
        "revocation_generation": 0,
        "access_expires_at": "2025-01-03T20:00:00Z",
        # The owner page treats an expired refresh as a paused connection.
        "refresh_expires_at": "2099-12-31T00:00:00Z",
        "created_at": CONNECTED_AT,
        "resource": "http://127.0.0.1:7659/mcp",
        "generation": 1,
    }
    endpoint = journal / "mcp-endpoint"
    write_json(endpoint / "oauth.json", {
        "schema": 2, "pairing_generation": 1, "clients": [client], "grants": [grant],
        "pending": [], "pairing": None,
    })
    write_json(endpoint / "permissions.json", {"schema": 1, "permissions": [{
        "connection": CONNECTION, "schema": 1, "generation": 1, "evaluation": "enforce",
        "read": {"categories": CATEGORIES, "scope": {"kind": "whole_journal"}},
    }]})
    write_json(endpoint / "agent-state.json", {"schema": 1, "entries": [{
        "kind": "memory_source", "connection": CONNECTION, "source": SOURCE,
    }]})

    stream = f"agent-memory-{SOURCE}"
    source_key = f"sha256:{SOURCE}"
    previous_day = previous_segment = None
    for seq, (day, note) in enumerate(NOTES, start=1):
        segment = "211600_1"
        created_at = iso_at(day, "21:16:00")
        coordinate = {"day": day, "stream": stream, "segment": segment}
        origin = {
            "kind": "agent_memory", "source_key": source_key, "creation_label": "Claude",
            "created_at": created_at, "stream": stream, "segment": segment,
        }
        chain = {"prev_day": previous_day, "prev_segment": previous_segment, "seq": seq}
        note_bytes = note.encode("utf-8")
        facts = {"coordinate": coordinate, "created_at": created_at, "chain": chain,
                 "digest": hashlib.sha256(note_bytes).hexdigest(), "byte_count": len(note_bytes)}
        target = journal / "chronicle" / day / stream / segment
        target.mkdir(parents=True, exist_ok=True)
        (target / "note.txt").write_bytes(note_bytes)
        write_json(target / "origin.json", origin)
        write_json(target / "stream.json", {"stream": stream, **chain})
        write_json(target / "ready.json", {"source_key": source_key, "origin": origin, **facts})
        operation = f"william-note-{day}"
        operation_hash = hashlib.sha256(operation.encode()).hexdigest()
        write_json(journal / "config" / "agent-memory" / SOURCE / f"{operation_hash}.json", {
            "operation_id": operation, "creation_label": "Claude", "origin_kind": "agent_memory",
            "phase": "ready", **facts,
        })
        write_call(journal, day, segment, "save_memory", {
            "operation_id": operation, "digest": facts["digest"],
            "byte_count": facts["byte_count"], "authority": "own_memory",
        }, {
            "count": 1, "targets": [], "digest": facts["digest"], "origin": origin,
            "created_at": created_at, "byte_count": facts["byte_count"],
            "memory": {"complete": True, "own_recall_ready": True, "ordinary_readable": False},
        })
        previous_day, previous_segment = day, segment

    write_json(journal / "streams" / f"{stream}.json", {
        "name": stream, "kind": "agent_memory", "host": None, "platform": None,
        "created_at": int(datetime.fromisoformat(CONNECTED_AT).timestamp()),
        "last_day": previous_day, "last_segment": previous_segment, "seq": len(NOTES),
        "cid": source_key, "source": SOURCE, "last_marker": chain,
    })
    for day, facet, activity, query in VISITS:
        path = journal / "facets" / facet / "activities" / f"{day}.jsonl"
        record = next(row for row in rows_at(path) if row["id"] == activity)
        result = {"title": record["title"], "day": day, "facet": facet, "id": activity}
        digest = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
        write_call(journal, day, "211500_1", "search", {"query": query}, {
            "count": 1, "targets": [f"{path.relative_to(journal)}#{activity}"], "digest": digest,
        })


def write_call(journal: Path, day: str, segment: str, tool: str, arguments: dict, result: dict) -> None:
    target = journal / "chronicle" / day / "mcp.agent" / segment
    time = f"{segment[:2]}:{segment[2:4]}:{segment[4:6]}"
    timestamp = iso_at(day, time)
    is_save = tool == "save_memory"
    request = {"arguments": arguments}
    if not is_save:
        request["permission"] = {
            "generation": 1, "categories": CATEGORIES, "scope": "whole_journal",
        }
    write_json(target / "interaction.json", {
        "schema": 3, "agent_identity": f"sha256:{SOURCE}" if is_save else "Claude",
        "timestamp": timestamp, "tool_name": tool, "connection": CONNECTION, "request": request,
    })
    write_json(target / "outcome.json", {
        "schema": 1, "timestamp": timestamp, "outcome": "stored" if is_save else "served",
        "reason": None, "result": result,
    })


def install_corrections(journal: Path) -> None:
    for day, facet, activity, details in CORRECTIONS:
        path = journal / "facets" / facet / "activities" / f"{day}.jsonl"
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        rows = [json.loads(line) for line in lines]
        position, record = next((i, row) for i, row in enumerate(rows) if row["id"] == activity)
        timestamp = iso_at(day, "20:30:00")
        patch = {"details": details}
        edit_id = f"{facet}/{activity}/{timestamp}/0"
        edits = record.setdefault("edits", [])
        if any(edit.get("stretch", {}).get("id") == edit_id for edit in edits):
            continue
        edits.append({
            "timestamp": timestamp, "actor": "owner:update", "fields": ["details"], "note": "",
            "set": patch, "before": {"details": record.get("details", "")}, "stretch": {"id": edit_id},
        })
        record.update(patch)
        lines[position] = json.dumps(record, sort_keys=True) + "\n"
        path.write_text("".join(lines), encoding="utf-8")


def install_possible_names(journal: Path) -> None:
    sidecars: dict[Path, dict] = {}
    for day, segment, sentence, heard, slug in POSSIBLE_NAMES:
        target = journal / "chronicle" / day / "talk" / segment
        audio = target / "audio.jsonl"
        identity = read_json(journal / "entities" / slug / "entity.json")
        if target not in sidecars:
            source_digest = hashlib.sha256(audio.read_bytes()).hexdigest()
            sidecars[target] = {
                "schema": "solstone-possible-names-v1", "talent_version": "possible-names-v1-william-demo",
                "source": {"file": audio.name, "sha256": source_digest},
                "registry_revision": hashlib.sha256(b"william-demo").hexdigest(),
                "generated_at_ms": int(datetime.fromisoformat(iso_at(day, "20:45:00")).timestamp() * 1000),
                "entries": [],
            }
        row = next(row for row in rows_at(audio) if row.get("sentence_id") == sentence)
        words = row.get("corrected") or row["text"]
        start = words.encode().index(heard.encode())
        sidecars[target]["entries"].append({
            "sentence": sentence, "start_byte": start, "end_byte": start + len(heard.encode()),
            "heard": heard, "entity_id": identity["id"], "name": identity["name"],
        })
    for target, sidecar in sidecars.items():
        write_json(target / "talents" / "possible_names.json", sidecar)


def install_mark(journal: Path, mark_bundle: Path) -> None:
    target = journal / "link" / "ca"
    if not all((mark_bundle / name).is_file() for name in MARK_FILES):
        raise ValueError(f"Missing William's fixed demo mark bundle at {mark_bundle}")
    if target.resolve() == mark_bundle.resolve():
        return
    target.mkdir(mode=0o700, parents=True, exist_ok=True)
    for name in MARK_FILES:
        shutil.copyfile(mark_bundle / name, target / name)
        (target / name).chmod(0o600 if name != "cert.pem" else 0o644)


def install_faces(journal: Path, project: Path = PROJECT) -> int:
    manifest = project / "photos" / "faces" / "install.json"
    if not manifest.exists():
        return 0
    from PIL import Image

    by_entity = read_json(manifest)["by_entity"]
    person_slugs = [path.parent.name for path in sorted(journal.glob("entities/*/entity.json"))
                    if read_json(path)["type"] == "Person"]
    if len(person_slugs) > 128:
        raise ValueError("Too many people for William's synthetic face fixtures")
    portraits = []
    for slug, relative in sorted(by_entity.items()):
        if not re.fullmatch(r"[a-z0-9_]+", slug) or Path(relative).is_absolute():
            raise ValueError(f"Unsafe portrait manifest entry for {slug!r}")
        directory = journal / "entities" / slug
        if slug not in person_slugs:
            raise ValueError(f"Cannot install a person portrait for {slug}")
        source = (project / relative).resolve(strict=True)
        if not source.is_relative_to(project.resolve()):
            raise ValueError(f"Portrait for {slug} is outside the William project")
        with Image.open(source) as image:
            if image.format != "JPEG" or image.width != 256:
                raise ValueError(f"Portrait for {slug} must be a 256-pixel-wide JPEG")
            image.verify()
        portraits.append((slug, directory, source.read_bytes()))

    for slug, directory, jpeg in portraits:
        stamp = "2025-12-31T21:00:00Z"
        embedding = [0.0] * 128
        embedding[person_slugs.index(slug)] = 1.0
        face = {
            # Synthetic unit vector required by the confirmed-state reader. No model produced it.
            "embedding": embedding,
            "metadata": {
                "schema_version": 1, "day": "20251231", "stream": "william-demo",
                "stream_layout": "named", "segment_key": "210000_1", "source_name": slug,
                "frame_id": 0, "face_idx": 0, "activities": [], "source": "anchored",
                "label_text": None, "quality": 1, "det_score": 1, "face_w": 256,
                "category": "portrait", "crop": None, "added_at": stamp, "rejected": False,
            },
        }
        write_json(directory / "faces_state.json", {
            "schema_version": 1, "last": None, "dismissed_at": None,
            "dismissed_looks": [], "rejections": [], "photo": {
                "face": face, "encoder": {"id": "william-demo-portrait", "sha256": "0" * 64, "width": 128},
                "chosen_at": stamp, "jpeg": list(jpeg),
            },
        })
        (directory / "photo.jpg").write_bytes(jpeg)
    return len(portraits)


def install(journal: Path, mark_bundle: Path) -> dict:
    install_mark(journal, mark_bundle)
    install_agent(journal)
    install_corrections(journal)
    install_possible_names(journal)
    return {"corrections": len(CORRECTIONS), "possible_names": len(POSSIBLE_NAMES),
            "agent_notes": len(NOTES), "agent_interactions": len(NOTES) + len(VISITS),
            "faces": install_faces(journal)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", type=Path, default=JOURNAL)
    parser.add_argument("--mark-bundle", type=Path, default=JOURNAL / "link" / "ca")
    args = parser.parse_args()
    journal = args.journal.resolve()
    if "agent-reveals-william" in journal.parts or (
        journal != JOURNAL.resolve() and not journal.is_relative_to("/var/tmp")
    ):
        parser.error("Use the William build tree or a disposable /var/tmp copy")
    if not (journal / "entities" / "william_shakespeare" / "entity.json").is_file():
        parser.error("Expected a converted William journal")
    print(json.dumps(install(journal, args.mark_bundle.resolve()), sort_keys=True))


if __name__ == "__main__":
    main()
