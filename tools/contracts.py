# SPDX-License-Identifier: CC-BY-NC-4.0
# Copyright (c) 2026 sol pbc

"""Schema and contract validation against pinned solstone-journal schemas."""

from __future__ import annotations

from datetime import date, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

# A solstone-journal checkout at the commit pinned in manifest.json.
DEFAULT_SOLSTONE_REPO = Path(os.environ.get("WILLIAM_SOLSTONE_REPO") or Path.home() / "projects" / "solstone-journal")

CALENDAR_REQUIRED_KEYS = (
    "v",
    "change",
    "event",
    "occurrence",
    "changed_at",
    "calendar",
    "title",
    "location",
    "notes",
    "url",
    "start",
    "end",
    "all_day",
    "time_zone",
    "organizer",
    "attendees",
    "repeats",
)

CALENDAR_TEXT_FIELDS = (
    "calendar",
    "title",
    "location",
    "notes",
    "url",
    "repeats",
    "time_zone",
)

WEEKLY_ALLOWED_SECTIONS = ("The Week", "Highlights", "Patterns", "Looking Ahead")
WEEKLY_EMPHASIS = ("quiet", "normal", "milestone")
WEEKLY_MOODS = (
    "calm",
    "focused",
    "energized",
    "reflective",
    "accomplished",
    "stretched",
    "grounded",
    "curious",
    "steady",
    "restless",
    "grateful",
    "determined",
)


class ContractValidationError(ValueError):
    """Raised when an artifact violates a solstone-journal schema or contract."""


def _validate_jsonschema(instance: Any, schema: dict[str, Any], label: str) -> None:
    """Validate `instance` against `schema` using jsonschema if available, plus structural checks."""
    try:
        import jsonschema  # type: ignore[import-not-found]

        validator_cls = jsonschema.validators.validator_for(schema)
        validator = validator_cls(schema)
        errors = list(validator.iter_errors(instance))
        if errors:
            first = errors[0]
            loc = ".".join(str(p) for p in first.absolute_path)
            where = f"{label}:{loc}" if loc else label
            raise ContractValidationError(f"{where}: {first.message}")
        return
    except ImportError:
        pass

    _stdlib_validate_schema(instance, schema, schema, label)


def _stdlib_validate_schema(
    instance: Any,
    schema: dict[str, Any],
    root_schema: dict[str, Any],
    path: str,
) -> None:
    """Fallback Draft 2020-12 structural validator when jsonschema is not installed."""
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/$defs/"):
            raise ContractValidationError(f"{path}: unsupported $ref {ref}")
        def_name = ref[len("#/$defs/") :]
        target = root_schema.get("$defs", {}).get(def_name)
        if not isinstance(target, dict):
            raise ContractValidationError(f"{path}: missing $def {def_name}")
        _stdlib_validate_schema(instance, target, root_schema, path)
        return

    if "anyOf" in schema:
        last_err: Exception | None = None
        for branch in schema["anyOf"]:
            try:
                _stdlib_validate_schema(instance, branch, root_schema, path)
                return
            except ContractValidationError as err:
                last_err = err
        raise ContractValidationError(f"{path}: failed all anyOf branches ({last_err})")

    if "const" in schema and instance != schema["const"]:
        raise ContractValidationError(f"{path}: expected const {schema['const']!r}, got {instance!r}")

    if "enum" in schema and instance not in schema["enum"]:
        raise ContractValidationError(f"{path}: {instance!r} not in enum {schema['enum']!r}")

    expected_type = schema.get("type")
    if expected_type is not None:
        allowed_types = [expected_type] if isinstance(expected_type, str) else list(expected_type)
        if not any(_matches_json_type(instance, t) for t in allowed_types):
            raise ContractValidationError(f"{path}: expected type {expected_type}, got {type(instance).__name__}")

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < int(schema["minLength"]):
            raise ContractValidationError(f"{path}: string shorter than minLength {schema['minLength']}")
        if "maxLength" in schema and len(instance) > int(schema["maxLength"]):
            raise ContractValidationError(f"{path}: string longer than maxLength {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            raise ContractValidationError(f"{path}: string {instance!r} does not match {schema['pattern']!r}")

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            raise ContractValidationError(f"{path}: {instance} < minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            raise ContractValidationError(f"{path}: {instance} > maximum {schema['maximum']}")

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < int(schema["minItems"]):
            raise ContractValidationError(f"{path}: list has fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(instance) > int(schema["maxItems"]):
            raise ContractValidationError(f"{path}: list has more than {schema['maxItems']} items")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for idx, item in enumerate(instance):
                _stdlib_validate_schema(item, item_schema, root_schema, f"{path}.{idx}")

    if isinstance(instance, dict):
        for req in schema.get("required", []):
            if req not in instance:
                raise ContractValidationError(f"{path}: missing required key {req!r}")
        props = schema.get("properties", {})
        addl = schema.get("additionalProperties", True)
        for k, v in instance.items():
            child_path = f"{path}.{k}"
            if k in props:
                _stdlib_validate_schema(v, props[k], root_schema, child_path)
            elif addl is False:
                raise ContractValidationError(f"{path}: additional property {k!r} not allowed")
            elif isinstance(addl, dict):
                _stdlib_validate_schema(v, addl, root_schema, child_path)


def _matches_json_type(val: Any, json_type: str) -> bool:
    if json_type == "null":
        return val is None
    if json_type == "boolean":
        return isinstance(val, bool)
    if json_type == "integer":
        return isinstance(val, int) and not isinstance(val, bool)
    if json_type == "number":
        return isinstance(val, (int, float)) and not isinstance(val, bool)
    if json_type == "string":
        return isinstance(val, str)
    if json_type == "array":
        return isinstance(val, list)
    if json_type == "object":
        return isinstance(val, dict)
    return False


class ContractRegistry:
    """Loads pinned schemas from solstone-journal and validates payloads before write."""

    def __init__(self, solstone_repo: Path = DEFAULT_SOLSTONE_REPO) -> None:
        self.solstone_repo = solstone_repo
        self.payload_root = solstone_repo / "core" / "payload" / "solstone"
        bundle_path = self.payload_root / "talent" / "journal" / "contract" / "bundle.json"
        if not bundle_path.is_file():
            raise FileNotFoundError(f"Missing contract bundle at {bundle_path}")
        self.bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        self.talent_schemas: dict[str, dict[str, Any]] = {}
        for schema_file in sorted((self.payload_root / "talent").glob("*.schema.json")):
            name = schema_file.name[: -len(".schema.json")]
            raw_text = schema_file.read_text(encoding="utf-8")
            if '"__RUNTIME_FACETS__"' in raw_text:
                raw_text = raw_text.replace(
                    '"__RUNTIME_FACETS__"',
                    '"company", "writing", "household", "stratford"',
                )
            self.talent_schemas[name] = json.loads(raw_text)

    def validate_bundle_json(self, format_id: str, data: dict[str, Any], label: str) -> None:
        schema = self.bundle["schemas"][format_id]["schema"]
        _validate_jsonschema(data, schema, label)

    def validate_headered_jsonl(self, format_id: str, lines: list[dict[str, Any]], label: str) -> None:
        if not lines:
            raise ContractValidationError(f"{label}: headered JSONL requires at least a header line")
        schema = self.bundle["schemas"][format_id]["schema"]
        header_schema = {**schema["$defs"]["header"], "$defs": schema.get("$defs", {})}
        record_schema = {**schema["$defs"]["record"], "$defs": schema.get("$defs", {})}
        _validate_jsonschema(lines[0], header_schema, f"{label}:1")
        for idx, rec in enumerate(lines[1:], start=2):
            _validate_jsonschema(rec, record_schema, f"{label}:{idx}")

    def validate_talent_output(self, talent_name: str, data: Any, label: str) -> None:
        if talent_name not in self.talent_schemas:
            raise KeyError(f"Unknown talent schema: {talent_name}")
        schema = self.talent_schemas[talent_name]
        _validate_jsonschema(data, schema, label)


def validate_calendar_file_bytes(
    filename: str,
    raw_bytes: bytes,
    day_key: str,
    segment_key: str,
) -> None:
    """Validate a `calendar_<sha256>.jsonl` file against `solstone-core-format/src/calendar.rs`."""
    expected_name = f"calendar_{hashlib.sha256(raw_bytes).hexdigest()}.jsonl"
    if filename != expected_name:
        raise ContractValidationError(f"calendar filename mismatch: got {filename}, expected {expected_name}")

    if not re.fullmatch(r"\d{8}", day_key):
        raise ContractValidationError(f"invalid day key {day_key!r}")
    if not re.fullmatch(r"\d{6}_300", segment_key):
        raise ContractValidationError(f"calendar segment {segment_key!r} must be HHMMSS_300")

    clock = segment_key.split("_")[0]
    hh, mm, ss = int(clock[0:2]), int(clock[2:4]), int(clock[4:6])
    if (hh * 3600 + mm * 60 + ss) % 300 != 0:
        raise ContractValidationError(f"calendar segment {segment_key!r} not on 300s grid")

    win_start = datetime.strptime(f"{day_key}{clock}", "%Y%m%d%H%M%S")
    win_end = win_start + timedelta(seconds=300)

    text = raw_bytes.decode("utf-8")
    lines = text.splitlines()
    if not lines:
        raise ContractValidationError(f"{filename}: file holds no notes")

    seen_identities: set[tuple[str, str]] = set()
    for line_no, line in enumerate(lines, start=1):
        if not line.strip():
            raise ContractValidationError(f"{filename}:{line_no}: empty line")
        rec = json.loads(line)
        if not isinstance(rec, dict):
            raise ContractValidationError(f"{filename}:{line_no}: line is not a JSON object")
        for req_key in CALENDAR_REQUIRED_KEYS:
            if req_key not in rec:
                raise ContractValidationError(f"{filename}:{line_no}: {req_key} is missing")
        if rec["v"] != 1:
            raise ContractValidationError(f"{filename}:{line_no}: v must be 1")
        if rec["change"] not in ("added", "changed", "removed"):
            raise ContractValidationError(f"{filename}:{line_no}: invalid change {rec['change']!r}")
        if not isinstance(rec["event"], str) or not rec["event"]:
            raise ContractValidationError(f"{filename}:{line_no}: event must be non-empty string")
        occ = rec["occurrence"]
        if occ is not None and not isinstance(occ, str):
            raise ContractValidationError(f"{filename}:{line_no}: occurrence must be string or null")
        ident = (rec["event"], occ or "")
        if ident in seen_identities:
            raise ContractValidationError(f"{filename}:{line_no}: duplicate (event, occurrence) {ident}")
        seen_identities.add(ident)

        changed_at_str = rec["changed_at"]
        if not isinstance(changed_at_str, str):
            raise ContractValidationError(f"{filename}:{line_no}: changed_at must be RFC3339 string")
        dt = datetime.fromisoformat(changed_at_str)
        if dt.tzinfo is None:
            raise ContractValidationError(f"{filename}:{line_no}: changed_at must carry offset")
        naive_local = dt.replace(tzinfo=None)
        if not (win_start <= naive_local < win_end):
            raise ContractValidationError(
                f"{filename}:{line_no}: changed_at {naive_local} outside window [{win_start}, {win_end})"
            )

        for tf in CALENDAR_TEXT_FIELDS:
            if rec[tf] is not None and not isinstance(rec[tf], str):
                raise ContractValidationError(f"{filename}:{line_no}: {tf} must be string or null")

        org = rec["organizer"]
        if org is not None:
            if not isinstance(org, dict):
                raise ContractValidationError(f"{filename}:{line_no}: organizer must be object or null")
            for pk in ("name", "email"):
                if pk in org and org[pk] is not None and not isinstance(org[pk], str):
                    raise ContractValidationError(f"{filename}:{line_no}: organizer.{pk} must be string or null")

        attendees = rec["attendees"]
        if not isinstance(attendees, list):
            raise ContractValidationError(f"{filename}:{line_no}: attendees must be array")
        for att in attendees:
            if not isinstance(att, dict):
                raise ContractValidationError(f"{filename}:{line_no}: attendee must be object")

        if rec["change"] != "removed":
            all_day = rec["all_day"]
            if not isinstance(all_day, bool):
                raise ContractValidationError(f"{filename}:{line_no}: all_day must be bool")
            start_val = rec["start"]
            end_val = rec["end"]
            if not isinstance(start_val, str):
                raise ContractValidationError(f"{filename}:{line_no}: start must be string")
            is_start_date = bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", start_val))
            if all_day != is_start_date:
                raise ContractValidationError(
                    f"{filename}:{line_no}: start must be YYYY-MM-DD iff all_day is true"
                )
            if end_val is not None:
                if not isinstance(end_val, str):
                    raise ContractValidationError(f"{filename}:{line_no}: end must be string or null")
                is_end_date = bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", end_val))
                if all_day != is_end_date:
                    raise ContractValidationError(
                        f"{filename}:{line_no}: end must be YYYY-MM-DD iff all_day is true"
                    )


def validate_body_rows(
    rows: list[dict[str, Any]],
    label: str,
    registry: ContractRegistry | None = None,
) -> None:
    """Validate `body.jsonl` rows against `body-records.schema.json` and `body_records.rs`."""
    if not rows:
        raise ContractValidationError(f"{label}: body.jsonl must contain at least one row")
    seen_ids: set[str] = set()
    prev_sort_key: tuple[int, int, str] | None = None
    for idx, row in enumerate(rows, start=1):
        row_label = f"{label}:{idx}"
        if registry is not None:
            registry.validate_bundle_json("body-records", row, row_label)
        if row.get("v") != 1:
            raise ContractValidationError(f"{row_label}: v must be 1")
        row_id = row.get("id")
        if not isinstance(row_id, str) or not row_id.strip():
            raise ContractValidationError(f"{row_label}: missing or empty id")
        if row_id in seen_ids:
            raise ContractValidationError(f"{row_label}: duplicate row id {row_id!r}")
        seen_ids.add(row_id)
        kind = row.get("kind")
        if kind not in (
            "experience",
            "experience_tile",
            "stage",
            "event",
            "reading",
            "count",
            "logged",
            "dated",
            "moved",
        ):
            raise ContractValidationError(f"{row_label}: unsupported body row kind {kind!r}")
        for req in ("source", "type", "label"):
            if req not in row or not isinstance(row[req], str) or not row[req]:
                raise ContractValidationError(f"{row_label}: missing or invalid {req!r}")
        begins = row.get("at") or row.get("start")
        if kind not in ("moved", "dated"):
            if not isinstance(begins, str):
                raise ContractValidationError(f"{row_label}: row must carry 'at' or 'start' timestamp")
            dt = datetime.fromisoformat(begins)
            if dt.tzinfo is None:
                raise ContractValidationError(f"{row_label}: timestamp {begins!r} must have timezone offset")
            sort_key = (1, int(dt.timestamp() * 1000), row_id)
        else:
            sort_key = (0, 0, row_id)
        if prev_sort_key is not None and sort_key < prev_sort_key:
            raise ContractValidationError(
                f"{row_label}: rows out of sort_rows order ({sort_key} < {prev_sort_key})"
            )
        prev_sort_key = sort_key


def validate_location_lines(lines: list[dict[str, Any]], label: str) -> None:
    """Validate `location.jsonl` lines against `solstone-core-location/src/record.rs`."""
    if not lines:
        raise ContractValidationError(f"{label}: location.jsonl is empty")
    header = lines[0]
    if header.get("schema") != "solstone.location.segment/1":
        raise ContractValidationError(f"{label}:1: first line must have schema 'solstone.location.segment/1'")
    if header.get("accuracy") not in ("full", "reduced"):
        raise ContractValidationError(f"{label}:1: header accuracy must be 'full' or 'reduced'")
    if header.get("platform") not in ("ios", "ipados", "watchos", "wearos", "android"):
        raise ContractValidationError(f"{label}:1: invalid platform {header.get('platform')!r}")
    for idx, rec in enumerate(lines[1:], start=2):
        rec_schema = rec.get("schema")
        lat = rec.get("lat")
        lon = rec.get("lon")
        if not isinstance(lat, (int, float)) or not (-90.0 <= float(lat) <= 90.0):
            raise ContractValidationError(f"{label}:{idx}: invalid lat {lat!r}")
        if not isinstance(lon, (int, float)) or not (-180.0 <= float(lon) <= 180.0):
            raise ContractValidationError(f"{label}:{idx}: invalid lon {lon!r}")
        h_acc = rec.get("h_acc")
        if not isinstance(h_acc, (int, float)) or float(h_acc) < 0.0:
            raise ContractValidationError(f"{label}:{idx}: invalid h_acc {h_acc!r}")
        if rec_schema == "solstone.location.fix/1":
            t_val = rec.get("t")
            if not isinstance(t_val, str):
                raise ContractValidationError(f"{label}:{idx}: fix missing RFC3339 't'")
            dt = datetime.fromisoformat(t_val.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                raise ContractValidationError(f"{label}:{idx}: fix 't' must carry timezone")
        elif rec_schema == "solstone.location.visit/1":
            for tk in ("arrival", "departure"):
                tv = rec.get(tk)
                if tv is not None:
                    if not isinstance(tv, str):
                        raise ContractValidationError(f"{label}:{idx}: visit {tk} must be string or null")
                    dt = datetime.fromisoformat(tv.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        raise ContractValidationError(f"{label}:{idx}: visit {tk} must carry timezone")
        else:
            raise ContractValidationError(f"{label}:{idx}: unknown location schema {rec_schema!r}")


def validate_stream_record(record: dict[str, Any], label: str) -> None:
    """Validate `streams/<name>.json` against `StreamRecord` in `stream_record.rs`."""
    for req in ("name", "kind", "created_at", "seq"):
        if req not in record:
            raise ContractValidationError(f"{label}: missing required field {req!r}")
    if not isinstance(record["name"], str) or not record["name"]:
        raise ContractValidationError(f"{label}: name must be non-empty string")
    if not isinstance(record["kind"], str) or not record["kind"]:
        raise ContractValidationError(f"{label}: kind must be non-empty string")
    if not isinstance(record["created_at"], int) or record["created_at"] < 0:
        raise ContractValidationError(f"{label}: created_at must be non-negative int")
    if not isinstance(record["seq"], int) or record["seq"] < 0:
        raise ContractValidationError(f"{label}: seq must be non-negative int")
    for opt_str in ("host", "platform", "last_day", "last_segment", "source"):
        if opt_str in record and record[opt_str] is not None and not isinstance(record[opt_str], str):
            raise ContractValidationError(f"{label}: {opt_str} must be string or null")
    if "cid" in record and record["cid"] is not None:
        cid = record["cid"]
        if not isinstance(cid, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", cid):
            raise ContractValidationError(f"{label}: cid must match sha256:<64 hex chars>")


def _is_plain_name(component: str) -> bool:
    return (
        bool(component)
        and component not in (".", "..")
        and bool(re.fullmatch(r"[A-Za-z0-9._-]+", component))
    )


def _activity_said_uri(uri: str, day_key: str) -> bool:
    prefix = "sol://facets/"
    if not uri.startswith(prefix):
        return False
    rest = uri[len(prefix) :]
    if "/" not in rest:
        return False
    facet, after_facet = rest.split("/", 1)
    if not _is_plain_name(facet) or "." in facet:
        return False
    act_prefix = "activities/"
    if not after_facet.startswith(act_prefix):
        return False
    after_activities = after_facet[len(act_prefix) :]
    if "#" not in after_activities:
        return False
    uri_day, act_id = after_activities.split("#", 1)
    return uri_day == day_key and _is_plain_name(act_id)


def judge_weekly_reflection(
    markdown: str,
    json_str: str,
    sunday_date: str,
) -> None:
    """Port of `judge_contents` and `read_said` in `core/crates/solstone-core-home/src/weekly.rs:258-536`."""
    try:
        if len(sunday_date) == 8 and sunday_date.isdigit():
            sunday = datetime.strptime(sunday_date, "%Y%m%d").date()
        else:
            sunday = date.fromisoformat(sunday_date)
    except ValueError as err:
        raise ContractValidationError(f"invalid sunday date {sunday_date!r}") from err

    # Python weekday(): Monday=0 ... Sunday=6
    if sunday.weekday() != 6:
        raise ContractValidationError(f"weekly reflection start_date {sunday} is not a Sunday")

    saturday = sunday + timedelta(days=6)
    expected_start_key = sunday.strftime("%Y%m%d")
    expected_end_key = saturday.strftime("%Y%m%d")

    data = json.loads(json_str)
    if not isinstance(data, dict):
        raise ContractValidationError("weekly json root is not an object")
    if data.get("version") != 1:
        raise ContractValidationError("weekly json version != 1")

    week_obj = data.get("week")
    if not isinstance(week_obj, dict):
        raise ContractValidationError("weekly json missing 'week' object")
    if week_obj.get("start") != expected_start_key or week_obj.get("end") != expected_end_key:
        raise ContractValidationError(
            f"weekly json week {week_obj!r} != {{'start': {expected_start_key!r}, 'end': {expected_end_key!r}}}"
        )

    memory_ids: set[str] = set()
    memory_keys: set[str] = set()
    memory_day_by_id: dict[str, str] = {}

    if "memories" in data:
        mem_arr = data["memories"]
        if not isinstance(mem_arr, list):
            raise ContractValidationError("weekly json 'memories' must be an array")
        for idx, m in enumerate(mem_arr):
            if not isinstance(m, dict):
                raise ContractValidationError(f"weekly json memories[{idx}] is not an object")
            m_id = m.get("id")
            m_key = m.get("key")
            m_day = m.get("day")
            m_text = m.get("text")
            m_source = m.get("source")
            if not all(isinstance(x, str) and x for x in (m_id, m_key, m_day, m_text)):
                raise ContractValidationError(f"weekly json memories[{idx}] missing non-empty id/key/day/text")
            if not re.fullmatch(r"\d{8}", m_day):
                raise ContractValidationError(f"weekly json memories[{idx}].day {m_day!r} is not YYYYMMDD")
            if not isinstance(m_source, dict):
                raise ContractValidationError(f"weekly json memories[{idx}].source must be an object")
            if m_source.get("kind") != "briefing":
                raise ContractValidationError(f"weekly json memories[{idx}].source.kind must be 'briefing'")
            uri = m_source.get("uri")
            if not isinstance(uri, str) or not uri:
                raise ContractValidationError(f"weekly json memories[{idx}].source.uri must be non-empty string")
            if m_id in memory_ids:
                raise ContractValidationError(f"weekly json duplicate memory id {m_id!r}")
            memory_ids.add(m_id)
            memory_keys.add(m_key)
            memory_day_by_id[m_id] = m_day

    days_arr = data.get("days")
    if not isinstance(days_arr, list) or len(days_arr) != 7:
        raise ContractValidationError("weekly json 'days' must be a 7-element array")

    referenced_memory_ids: set[str] = set()
    valid_days: set[str] = set()
    for i, d in enumerate(days_arr):
        if not isinstance(d, dict):
            raise ContractValidationError(f"weekly json days[{i}] must be an object")
        expected_day_str = (sunday + timedelta(days=i)).strftime("%Y%m%d")
        day_str = d.get("day")
        state = d.get("state")
        if day_str != expected_day_str:
            raise ContractValidationError(f"weekly json days[{i}].day {day_str!r} != {expected_day_str!r}")
        valid_days.add(day_str)
        mem_id = d.get("memory_id")
        if state == "memory":
            if not isinstance(mem_id, str) or mem_id not in memory_day_by_id:
                raise ContractValidationError(f"weekly json days[{i}] memory_id {mem_id!r} not in memories")
            if memory_day_by_id[mem_id] != day_str:
                raise ContractValidationError(
                    f"weekly json days[{i}] memory {mem_id!r} day {memory_day_by_id[mem_id]!r} != {day_str!r}"
                )
            if mem_id in referenced_memory_ids:
                raise ContractValidationError(f"weekly json duplicate referenced memory_id {mem_id!r}")
            referenced_memory_ids.add(mem_id)
        elif state in ("nothing_shared", "unreadable", "not_ready", "not_on_page"):
            pass
        else:
            raise ContractValidationError(f"weekly json days[{i}] invalid state {state!r}")

    if "said" in data:
        said_arr = data["said"]
        if not isinstance(said_arr, list):
            raise ContractValidationError("weekly json 'said' must be an array")
        seen_said_ids: set[str] = set()
        seen_said_keys: set[str] = set()
        for idx, item in enumerate(said_arr):
            if not isinstance(item, dict):
                raise ContractValidationError(f"weekly json said[{idx}] must be an object")
            s_id = item.get("id")
            s_key = item.get("key")
            s_day = item.get("day")
            s_quote = item.get("quote")
            s_source = item.get("source")
            if not all(isinstance(x, str) and x for x in (s_id, s_key, s_day, s_quote)):
                raise ContractValidationError(f"weekly json said[{idx}] missing non-empty id/key/day/quote")
            if not isinstance(s_source, dict) or s_source.get("kind") != "activity":
                raise ContractValidationError(f"weekly json said[{idx}].source.kind must be 'activity'")
            uri = s_source.get("uri")
            if not isinstance(uri, str) or not _activity_said_uri(uri, s_day):
                raise ContractValidationError(
                    f"weekly json said[{idx}].source.uri {uri!r} invalid for day {s_day!r}"
                )
            if s_day not in valid_days:
                raise ContractValidationError(f"weekly json said[{idx}].day {s_day!r} not in week days")
            if s_id in seen_said_ids or s_key in seen_said_keys or s_key in memory_keys:
                raise ContractValidationError(f"weekly json said[{idx}] duplicate id/key ({s_id!r}, {s_key!r})")
            seen_said_ids.add(s_id)
            seen_said_keys.add(s_key)

    gen = data.get("generated_at")
    if not isinstance(gen, str) or "T" not in gen:
        raise ContractValidationError("weekly json generated_at is not an RFC3339 timestamp")

    trimmed = markdown.strip()
    if not trimmed:
        raise ContractValidationError("weekly markdown is empty")
    if "sol://" in trimmed:
        raise ContractValidationError("weekly markdown contains sol:// URI")
    if re.search(r"facets/[A-Za-z0-9_-]+/activities/\d{8}", trimmed):
        raise ContractValidationError("weekly markdown contains raw activity path")
