#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Copyright (c) 2026 sol pbc

"""Synthesize and install William 2025 journal audio (`audio.flac` + aligned `audio.jsonl`).

Uses ElevenLabs `eleven_v4` with Cast v2 licensed Voice Library voices (zero cloning),
scene-matched built-in `--audio-effects` room/outdoor acoustics, smooth 40 ms crossfaded
per-turn RMS leveling, and subtle non-voice 1595 ambient beds mixed into 16 kHz mono
FLAC (`audio.flac`).

Resumable: intermediate chunk responses are cached under `--cache-dir` (default
`<tempdir>/william-audio-cache`) so re-runs never re-synthesize completed chunks.
Override the CLI binary with `--elevenlabs-bin` or `WILLIAM_ELEVENLABS_BIN` (default
`elevenlabs`).
"""

from __future__ import annotations

import argparse
import array
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, time, timedelta
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time as time_mod
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from contracts import ContractRegistry  # type: ignore[import-not-found]
from stamp import stamp_journal_tree  # type: ignore[import-not-found]

AUDIO_DIR = PROJECT_ROOT / "audio"
AMBIENCE_DIR = AUDIO_DIR / "ambience"
DEFAULT_BATCH = AUDIO_DIR / "batch-48.json"
DEFAULT_VOICES = AUDIO_DIR / "voices.json"
DEFAULT_INSTALL_MANIFEST = AUDIO_DIR / "install.json"
DEFAULT_JOURNAL_DIR = PROJECT_ROOT / "build" / "journal"
DEFAULT_CACHE_DIR = Path(tempfile.gettempdir()) / "william-audio-cache"
DEFAULT_ELEVENLABS_BIN = os.environ.get("WILLIAM_ELEVENLABS_BIN", "elevenlabs")

MODEL_ID = "eleven_v4"
MAX_CHUNK_CHARS = 1720
CHUNK_GAP_S = 0.35
OWNER_SLUG = "william_shakespeare"
TARGET_OWNER_DBFS = -22.0
TARGET_OTHER_DBFS = -23.0
MAX_GAIN_BOOST_DB = 16.0
MAX_GAIN_CUT_DB = -6.0
TURN_XFADE_S = 0.04

# Calibrated from ffmpeg volumedetect so the 4 non-voice ambient beds sit ~30+ dB below
# active speech RMS (-52 to -55 dB mean for room/hall/lane; -67.5 dB mean for bonfire_night):
# audible and immersive with zero WeSpeaker voiceprint degradation.
AMBIENCE_PRESETS: dict[str, dict[str, Any]] = {
    "bonfire_street": {
        "environment_id": "street",
        "distance": 0.35,
        "send_level": 0.25,
        "ambience_file": "bonfire_night.mp3",
        "ambience_gain_db": -22.0,
    },
    "country_walk": {
        "environment_id": "street",
        "distance": 0.35,
        "send_level": 0.22,
        "ambience_file": "country_lane.mp3",
        "ambience_gain_db": 6.0,
    },
    "theatre_hall": {
        "environment_id": "big_room",
        "distance": 0.35,
        "send_level": 0.26,
        "ambience_file": "wood_hall.mp3",
        "ambience_gain_db": -6.0,
    },
    "household_room": {
        "environment_id": "small_room",
        "distance": 0.35,
        "send_level": 0.28,
        "ambience_file": "timber_hearth.mp3",
        "ambience_gain_db": 10.0,
    },
    "call_room": {
        "environment_id": "small_room",
        "distance": 0.28,
        "send_level": 0.22,
        "ambience_file": "timber_hearth.mp3",
        "ambience_gain_db": 8.0,
    },
    "memo_room": {
        "environment_id": "small_room",
        "distance": 0.20,
        "send_level": 0.18,
        "ambience_file": "timber_hearth.mp3",
        "ambience_gain_db": 6.0,
    },
    "memo_walk": {
        "environment_id": "street",
        "distance": 0.25,
        "send_level": 0.20,
        "ambience_file": "country_lane.mp3",
        "ambience_gain_db": 6.0,
    },
}

# Restrained character-accurate conversational opening cues so eleven_v4 stays natural
# and un-declamatory (never written into audio.jsonl — only sent to synthesis).
SPEAKER_CUES: dict[str, str] = {
    "william_shakespeare": "[relaxed, conversational]",
    "dorcas_ansell": "[matter-of-fact, brisk]",
    "alse_pinder": "[casually, natural]",
    "john_heminges": "[dry, steady, conversational]",
    "richard_burbage": "[warm, conversational]",
    "will_kemp": "[playful, casual]",
    "augustine_phillips": "[quietly, calm]",
    "anne_shakespeare": "[warm, grounded, conversational]",
    "abel_garnish": "[dry, matter-of-fact]",
    "gillis_verbeke": "[quietly, gentle]",
    "richard_field": "[steady, brisk, conversational]",
    "gilbert_shakespeare": "[warm, natural, conversational]",
    "john_florio": "[crisp, articulate, dry]",
    "cuthbert_burbage": "[steady, matter-of-fact, brisk]",
    "ambrose_kettleby": "[measured, polite, calm]",
    "henry_wriothesley_southampton": "[brisk, articulate, casual]",
    "henry_carey_hunsdon": "[gruff, commanding, direct]",
    "richard_quiney": "[warm, hearty, conversational]",
    "thomas_pope": "[warm, rich, conversational]",
}


def preset_for_segment(row: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    explicit = row.get("preset")
    if isinstance(explicit, str) and explicit in AMBIENCE_PRESETS:
        return explicit, AMBIENCE_PRESETS[explicit]
    rel = row["rel"]
    cat = row["category"]
    if rel == "20250623/talk/213000_720":
        key = "bonfire_street"
    elif rel in ("20250405/talk/154000_840", "20250816/talk/164000_600"):
        key = "country_walk"
    elif cat == "company":
        key = "theatre_hall"
    elif cat == "calls":
        key = "call_room"
    elif cat == "memos":
        key = "memo_room"
    else:
        key = "household_room"
    return key, AMBIENCE_PRESETS[key]


def split_chunks(turns: list[dict[str, Any]], max_chars: int = MAX_CHUNK_CHARS) -> list[list[dict[str, Any]]]:
    chunks: list[list[dict[str, Any]]] = []
    cur: list[dict[str, Any]] = []
    cur_chars = 0
    for t in turns:
        tlen = len(t["text"]) + 32  # headroom for optional delivery cue
        if cur and (cur_chars + tlen > max_chars):
            chunks.append(cur)
            cur = []
            cur_chars = 0
        cur.append(t)
        cur_chars += tlen
    if cur:
        chunks.append(cur)
    return chunks


def ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(path),
        ],
        text=True,
    ).strip()
    return float(out)


def call_elevenlabs_with_retry(cmd: list[str], label: str, max_attempts: int = 4) -> dict[str, Any]:
    last_err = ""
    for attempt in range(1, max_attempts + 1):
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode == 0:
            return json.loads(p.stdout)
        last_err = (p.stderr or p.stdout or "").strip()
        if attempt < max_attempts:
            wait = 2.0 * (2 ** (attempt - 1))
            print(f"  [RETRY {attempt}/{max_attempts}] {label}: {last_err[:160]} (sleep {wait:.0f}s)", flush=True)
            time_mod.sleep(wait)
    raise RuntimeError(f"ElevenLabs failed for {label} after {max_attempts} attempts: {last_err[:400]}")


def synthesize_chunk(
    chunk: list[dict[str, Any]],
    chunk_idx: int,
    voice_by_slug: dict[str, str],
    preset: dict[str, Any],
    cache_dir: Path,
    seg_label: str,
    elevenlabs_bin: str = DEFAULT_ELEVENLABS_BIN,
) -> tuple[Path, list[tuple[int, float, float]], float]:
    """Synthesize one chunk (cached) -> (mp3_path, [(sentence_id, start_s, end_s), ...], dur_s)."""
    mp3_path = cache_dir / f"chunk_{chunk_idx:02d}.mp3"
    meta_path = cache_dir / f"chunk_{chunk_idx:02d}.json"
    if mp3_path.is_file() and meta_path.is_file() and mp3_path.stat().st_size > 1000:
        cached = json.loads(meta_path.read_text(encoding="utf-8"))
        spans = [(int(s["sentence_id"]), float(s["start_s"]), float(s["end_s"])) for s in cached["spans"]]
        return mp3_path, spans, float(cached["duration_s"])

    cache_dir.mkdir(parents=True, exist_ok=True)
    env_flags = [
        f"--audio-effects.environment-id={preset['environment_id']}",
        f"--audio-effects.distance={preset['distance']}",
        f"--audio-effects.send-level={preset['send_level']}",
    ]

    if len(chunk) == 1:
        t = chunk[0]
        spk = t["speaker"]
        cue = SPEAKER_CUES.get(spk, "[casually]")
        txt = f"{cue} {t['text']}"
        cmd = [
            elevenlabs_bin,
            "text-to-speech",
            "convert_with_timestamps",
            "--voice-id",
            voice_by_slug[spk],
            "--model-id",
            MODEL_ID,
            "--text",
            txt,
            "--output-format",
            "mp3_44100_128",
            "--format",
            "json",
        ] + env_flags
        resp = call_elevenlabs_with_retry(cmd, f"{seg_label}#c{chunk_idx}")
        mp3_path.write_bytes(base64.b64decode(resp["audio_base64"]))
        dur = ffprobe_duration(mp3_path)
        align = resp.get("alignment") or {}
        starts = align.get("character_start_times_seconds") or []
        ends = align.get("character_end_times_seconds") or []
        s0 = float(min(starts)) if starts else 0.0
        e0 = float(max(ends)) if ends else dur
        if e0 <= s0:
            e0 = dur
        spans = [(int(t["sentence_id"]), round(s0, 3), round(min(e0, dur), 3))]
    else:
        inputs = []
        for idx, t in enumerate(chunk):
            spk = t["speaker"]
            txt = t["text"]
            # Cue the opening turn of the chunk and every 6th turn so delivery stays casual without over-tagging
            if idx == 0 or idx % 6 == 0:
                cue = SPEAKER_CUES.get(spk, "[casually]")
                txt = f"{cue} {txt}"
            inputs.append({"text": txt, "voice_id": voice_by_slug[spk]})
        cmd = [
            elevenlabs_bin,
            "text-to-dialogue",
            "convert_with_timestamps",
            "--model-id",
            MODEL_ID,
            "--inputs",
            json.dumps(inputs),
            "--output-format",
            "mp3_44100_128",
            "--format",
            "json",
        ] + env_flags
        resp = call_elevenlabs_with_retry(cmd, f"{seg_label}#c{chunk_idx}")
        mp3_path.write_bytes(base64.b64decode(resp["audio_base64"]))
        dur = ffprobe_duration(mp3_path)

        by_idx: dict[int, list[tuple[float, float]]] = {}
        for vs in resp.get("voice_segments") or []:
            di = int(vs["dialogue_input_index"])
            by_idx.setdefault(di, []).append((float(vs["start_time_seconds"]), float(vs["end_time_seconds"])))

        raw_spans: list[tuple[int, float | None, float | None]] = []
        for idx, t in enumerate(chunk):
            if idx in by_idx:
                s0 = min(x[0] for x in by_idx[idx])
                e0 = max(x[1] for x in by_idx[idx])
                raw_spans.append((int(t["sentence_id"]), s0, e0))
            else:
                raw_spans.append((int(t["sentence_id"]), None, None))

        # Repair any missing span (defensive) and clamp monotonically inside [0, dur]
        spans = []
        prev_end = 0.0
        for i, (sid, s0, e0) in enumerate(raw_spans):
            if s0 is None or e0 is None:
                # Look ahead for next known start
                nxt_start = dur
                for j in range(i + 1, len(raw_spans)):
                    if raw_spans[j][1] is not None:
                        nxt_start = float(raw_spans[j][1])
                        break
                s0 = prev_end
                e0 = max(s0 + 0.5, min(nxt_start, dur))
            s0 = max(0.0, min(s0, dur - 0.1))
            if s0 < prev_end - 0.05:
                s0 = prev_end
            e0 = max(s0 + 0.1, min(e0, dur))
            spans.append((sid, round(s0, 3), round(e0, 3)))
            prev_end = e0

    meta_path.write_text(
        json.dumps(
            {
                "duration_s": round(dur, 4),
                "spans": [{"sentence_id": sid, "start_s": s0, "end_s": e0} for sid, s0, e0 in spans],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return mp3_path, spans, dur


def _active_rms_dbfs(samples: array.array, sr: int = 16000) -> float | None:
    """Active speech RMS (top 60% of 20 ms frames) in dBFS for 16-bit PCM samples."""
    frame = sr // 50  # 320 samples = 20 ms
    n_frames = len(samples) // frame
    if n_frames < 5:
        return None
    energies: list[float] = []
    scale = 1.0 / (32768.0 * 32768.0 * frame)
    for fi in range(n_frames):
        off = fi * frame
        seg = samples[off : off + frame]
        energies.append(sum(x * x for x in seg) * scale)
    energies.sort()
    active = energies[int(n_frames * 0.40) :]
    mean_e = sum(active) / max(1, len(active))
    if mean_e <= 1e-11:
        return None
    return 10.0 * math.log10(mean_e)


def _compute_turn_gains(
    raw_speech_wav: Path,
    turns: list[tuple[str, float, float]],
) -> list[tuple[float, float, float]]:
    """Compute per-turn (lo_s, hi_s, gain_db) intervals partitioning the speech track cleanly.

    Balances native voice-actor level differences (which can span 18+ dB across ElevenLabs
    Voice Library voices) with smooth 40 ms linear crossfades at turn boundaries and zero
    mid-sentence pumping.
    """
    pcm_bytes = subprocess.check_output(
        ["ffmpeg", "-v", "error", "-i", str(raw_speech_wav), "-ac", "1", "-ar", "16000", "-f", "s16le", "pipe:1"]
    )
    samples = array.array("h")
    samples.frombytes(pcm_bytes)
    dur = len(samples) / 16000.0
    if not turns or dur <= 0.1:
        return [(0.0, max(dur, 0.1), 0.0)]

    # Measure active RMS per turn, with speaker-median fallback for very short utterances
    raw_dbs: list[float | None] = []
    by_spk: dict[str, list[float]] = {}
    for spk, s0, e0 in turns:
        i0 = max(0, int(round(s0 * 16000)))
        i1 = min(len(samples), int(round(e0 * 16000)))
        db = _active_rms_dbfs(samples[i0:i1]) if (i1 - i0) >= 3200 else None
        if db is not None and db < -52.0:
            db = None
        raw_dbs.append(db)
        if db is not None:
            by_spk.setdefault(spk, []).append(db)

    spk_median = {spk: statistics.median(vals) for spk, vals in by_spk.items() if vals}
    overall_median = statistics.median([d for d in raw_dbs if d is not None]) if any(d is not None for d in raw_dbs) else TARGET_OTHER_DBFS

    # Partition [0, dur] cleanly at midpoints between consecutive turns
    n = len(turns)
    bounds: list[tuple[float, float]] = []
    prev_cut = 0.0
    for i in range(n):
        if i + 1 < n:
            e_cur = turns[i][2]
            s_nxt = turns[i + 1][1]
            cut = 0.5 * (e_cur + s_nxt)
            cut = max(prev_cut + 0.05, min(cut, dur - 0.05))
        else:
            cut = dur
        bounds.append((prev_cut, cut))
        prev_cut = cut

    plan: list[tuple[float, float, float]] = []
    for i, (spk, _s0, _e0) in enumerate(turns):
        db = raw_dbs[i]
        if db is None:
            db = spk_median.get(spk, overall_median)
        target = TARGET_OWNER_DBFS if spk == OWNER_SLUG else TARGET_OTHER_DBFS
        gain_db = max(MAX_GAIN_CUT_DB, min(MAX_GAIN_BOOST_DB, target - db))
        a_i, b_i = bounds[i]
        plan.append((a_i, b_i, round(gain_db, 2)))
    return plan


def stitch_and_encode_flac(
    chunk_mp3s: list[Path],
    turns_ordered: list[tuple[str, float, float]],
    preset: dict[str, Any],
    dest_flac: Path,
    work_dir: Path,
) -> float:
    """Stitch chunks with exact CHUNK_GAP_S silence, level per-turn loudness, mix non-voice ambience, encode 16 kHz mono FLAC L8."""
    amb_path = AMBIENCE_DIR / preset["ambience_file"]
    if not amb_path.is_file():
        raise FileNotFoundError(f"Missing ambience bed: {amb_path}")
    gain_db = float(preset["ambience_gain_db"])

    # Step 1: Stitch raw speech chunks into a clean temporary 44.1 kHz stereo WAV so turn timestamps align 1:1
    raw_wav = work_dir / "stitched_raw.wav"
    inputs: list[str] = []
    filters: list[str] = []
    if len(chunk_mp3s) == 1:
        inputs += ["-i", str(chunk_mp3s[0])]
        filters.append("[0:a]aformat=sample_rates=44100:channel_layouts=stereo[speech]")
    else:
        for idx, cp in enumerate(chunk_mp3s):
            inputs += ["-i", str(cp)]
        gap_idx = len(chunk_mp3s)
        inputs += ["-f", "lavfi", "-t", f"{CHUNK_GAP_S:.3f}", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
        concat_parts: list[str] = []
        for idx in range(len(chunk_mp3s)):
            filters.append(f"[{idx}:a]aformat=sample_rates=44100:channel_layouts=stereo[c{idx}]")
            concat_parts.append(f"[c{idx}]")
            if idx + 1 < len(chunk_mp3s):
                concat_parts.append(f"[{gap_idx}:a]")
        filters.append(f"{''.join(concat_parts)}concat=n={len(concat_parts)}:v=0:a=1[speech]")

    subprocess.run(
        ["ffmpeg", "-v", "error", "-y"]
        + inputs
        + ["-filter_complex", ";".join(filters), "-map", "[speech]", "-c:a", "pcm_s16le", str(raw_wav)],
        check=True,
    )

    # Step 2: Compute per-turn RMS leveling plan and apply smooth 40 ms crossfaded gain + soft peak limiter + continuous ambience bed
    plan = _compute_turn_gains(raw_wav, turns_ordered)
    total_dur = plan[-1][1]
    half_xf = TURN_XFADE_S / 2.0
    n_seg = len(plan)

    f2: list[str] = []
    if n_seg == 1:
        g0 = plan[0][2]
        f2.append(f"[0:a]volume={g0:+.2f}dB,alimiter=limit=0.89:attack=5:release=50:level=false[lvl]")
    else:
        split_outs = "".join(f"[sp{i}]" for i in range(n_seg))
        f2.append(f"[0:a]asplit={n_seg}{split_outs}")
        mix_labels: list[str] = []
        for i, (a_i, b_i, g_db) in enumerate(plan):
            lo = max(0.0, a_i - (half_xf if i > 0 else 0.0))
            hi = min(total_dur, b_i + (half_xf if i + 1 < n_seg else 0.0))
            seg_len = max(0.05, hi - lo)
            chain = [f"atrim=start={lo:.4f}:end={hi:.4f}", "asetpts=PTS-STARTPTS", f"volume={g_db:+.2f}dB"]
            if i > 0:
                xf_in = min(TURN_XFADE_S, seg_len * 0.4)
                chain.append(f"afade=t=in:st=0:d={xf_in:.4f}:curve=tri")
            if i + 1 < n_seg:
                xf_out = min(TURN_XFADE_S, seg_len * 0.4)
                st_out = max(0.0, seg_len - xf_out)
                chain.append(f"afade=t=out:st={st_out:.4f}:d={xf_out:.4f}:curve=tri")
            delay_ms = int(round(lo * 1000.0))
            if delay_ms > 0:
                chain.append(f"adelay={delay_ms}|{delay_ms}")
            f2.append(f"[sp{i}]{','.join(chain)}[t{i}]")
            mix_labels.append(f"[t{i}]")
        f2.append(
            f"{''.join(mix_labels)}amix=inputs={n_seg}:duration=longest:normalize=0,"
            "alimiter=limit=0.89:attack=5:release=50:level=false[lvl]"
        )

    f2.append(f"[1:a]aformat=sample_rates=44100:channel_layouts=stereo,volume={gain_db:+.1f}dB[amb]")
    f2.append("[lvl][amb]amix=inputs=2:duration=first:normalize=0[mixed]")
    f2.append("[mixed]aformat=sample_fmts=s16:sample_rates=16000:channel_layouts=mono[out]")

    tmp_flac = dest_flac.with_suffix(".flac.tmp")
    cmd2 = [
        "ffmpeg",
        "-v",
        "error",
        "-y",
        "-i",
        str(raw_wav),
        "-stream_loop",
        "-1",
        "-i",
        str(amb_path),
        "-filter_complex",
        ";".join(f2),
        "-map",
        "[out]",
        "-map_metadata",
        "-1",
        "-c:a",
        "flac",
        "-compression_level",
        "8",
        "-f",
        "flac",
        str(tmp_flac),
    ]
    subprocess.run(cmd2, check=True)
    raw_wav.unlink(missing_ok=True)
    raw_head = tmp_flac.read_bytes()[:4]
    if raw_head != b"fLaC":
        raise RuntimeError(f"Encoded file lacks fLaC magic: {tmp_flac}")
    tmp_flac.replace(dest_flac)
    return ffprobe_duration(dest_flac)


def segment_start_dt(rel: str) -> datetime:
    day_key, _stream, seg_key = rel.split("/")
    hhmmss = seg_key.split("_")[0]
    d = date(int(day_key[0:4]), int(day_key[4:6]), int(day_key[6:8]))
    t = time(int(hhmmss[0:2]), int(hhmmss[2:4]), int(hhmmss[4:6]))
    return datetime.combine(d, t)


def process_segment(
    row: dict[str, Any],
    voice_by_slug: dict[str, str],
    journal_dir: Path,
    cache_root: Path,
    registry: ContractRegistry,
    elevenlabs_bin: str = DEFAULT_ELEVENLABS_BIN,
) -> dict[str, Any]:
    rel = row["rel"]
    seg_dir = journal_dir / "chronicle" / rel
    jsonl_path = seg_dir / "audio.jsonl"
    lines = [json.loads(ln) for ln in jsonl_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    header, body = lines[0], lines[1:]

    preset_name, preset = preset_for_segment(row)
    chunks = split_chunks(body)
    seg_cache = cache_root / rel.replace("/", "__")

    chunk_mp3s: list[Path] = []
    all_spans: dict[int, tuple[float, float]] = {}
    offset_s = 0.0
    for c_idx, chunk in enumerate(chunks):
        mp3_p, spans, c_dur = synthesize_chunk(
            chunk=chunk,
            chunk_idx=c_idx,
            voice_by_slug=voice_by_slug,
            preset=preset,
            cache_dir=seg_cache,
            seg_label=rel,
            elevenlabs_bin=elevenlabs_bin,
        )
        chunk_mp3s.append(mp3_p)
        for sid, s0, e0 in spans:
            all_spans[sid] = (round(offset_s + s0, 2), round(offset_s + e0, 2))
        offset_s += c_dur + (CHUNK_GAP_S if c_idx + 1 < len(chunks) else 0.0)

    turns_ordered = [
        (str(rec.get("speaker") or ""), all_spans[int(rec["sentence_id"])][0], all_spans[int(rec["sentence_id"])][1])
        for rec in body
    ]
    flac_path = seg_dir / "audio.flac"
    actual_dur = round(stitch_and_encode_flac(chunk_mp3s, turns_ordered, preset, flac_path, seg_cache), 2)
    flac_bytes = flac_path.read_bytes()
    flac_sha256 = hashlib.sha256(flac_bytes).hexdigest()

    # Align audio.jsonl header duration + per-turn timing & wall-clock start
    start_dt = segment_start_dt(rel)
    new_header = dict(header)
    new_header["duration"] = actual_dur
    new_header["raw"] = "audio.flac"

    new_body: list[dict[str, Any]] = []
    turn_timings: list[dict[str, Any]] = []
    for rec in body:
        sid = int(rec["sentence_id"])
        s0, e0 = all_spans[sid]
        s0 = max(0.0, min(s0, max(0.0, actual_dur - 0.1)))
        e0 = max(round(s0 + 0.1, 2), min(e0, actual_dur))
        wall_clock = (start_dt + timedelta(seconds=round(s0))).strftime("%H:%M:%S")
        upd = dict(rec)
        upd["start"] = wall_clock
        upd["timing"] = {"end": round(e0, 2), "start": round(s0, 2)}
        new_body.append(upd)
        turn_timings.append(
            {
                "sentence_id": sid,
                "start": wall_clock,
                "timing": {"start": round(s0, 2), "end": round(e0, 2)},
            }
        )

    new_lines = [new_header] + new_body
    registry.validate_headered_jsonl("audio-jsonl", new_lines, f"{rel}/audio.jsonl")
    jsonl_path.write_text(
        "".join(json.dumps(ln, sort_keys=True) + "\n" for ln in new_lines),
        encoding="utf-8",
    )

    return {
        "rel": rel,
        "category": row["category"],
        "note": row["note"],
        "speakers": row["speakers"],
        "turns_count": len(body),
        "chars": sum(len(r["text"]) for r in body),
        "chunks": len(chunks),
        "model_id": MODEL_ID,
        "preset": preset_name,
        "acoustics": {
            "environment_id": preset["environment_id"],
            "distance": preset["distance"],
            "send_level": preset["send_level"],
            "ambience_file": f"audio/ambience/{preset['ambience_file']}",
            "ambience_gain_db": preset["ambience_gain_db"],
        },
        "duration_s": actual_dur,
        "bytes": len(flac_bytes),
        "sha256": flac_sha256,
        "turns": turn_timings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Synthesize and install William 2025 journal audio batch.")
    parser.add_argument("--batch", type=Path, default=DEFAULT_BATCH)
    parser.add_argument("--voices", type=Path, default=DEFAULT_VOICES)
    parser.add_argument("--journal-dir", type=Path, default=DEFAULT_JOURNAL_DIR)
    parser.add_argument("--install-manifest", type=Path, default=DEFAULT_INSTALL_MANIFEST)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--elevenlabs-bin", default=DEFAULT_ELEVENLABS_BIN)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--only", nargs="*", help="Optional list of segment rel paths to process (e.g. 20250623/talk/213000_720)")
    parser.add_argument("--skip-stamp", action="store_true")
    args = parser.parse_args()

    batch = json.loads(args.batch.read_text(encoding="utf-8"))
    voices = json.loads(args.voices.read_text(encoding="utf-8"))
    voice_by_slug = {v["slug"]: v["voice_id"] for v in voices}
    registry = ContractRegistry()

    rows = batch["rows"]
    if args.only:
        want = set(args.only)
        rows = [r for r in rows if r["rel"] in want]
        missing = want - {r["rel"] for r in rows}
        if missing:
            raise SystemExit(f"Unknown --only segments: {sorted(missing)}")

    # Load existing manifest if resuming partial runs
    existing_by_seg: dict[str, Any] = {}
    if args.install_manifest.is_file():
        old_m = json.loads(args.install_manifest.read_text(encoding="utf-8"))
        existing_by_seg = dict(old_m.get("by_segment") or {})

    print(f"Processing {len(rows)} segments with {args.workers} worker(s) using {MODEL_ID}...", flush=True)
    t0 = time_mod.time()
    results: dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futs = {
            ex.submit(
                process_segment,
                row,
                voice_by_slug,
                args.journal_dir,
                args.cache_dir,
                registry,
                args.elevenlabs_bin,
            ): row
            for row in rows
        }
        done = 0
        for fut in as_completed(futs):
            row = futs[fut]
            res = fut.result()
            done += 1
            results[res["rel"]] = res
            print(
                f"  [{done:2d}/{len(rows)}] {res['rel']:<26} {res['preset']:<14} "
                f"dur={res['duration_s']:6.2f}s  {res['bytes']//1024:4d} KB  "
                f"chunks={res['chunks']}  turns={res['turns_count']}",
                flush=True,
            )

    existing_by_seg.update(results)
    ordered = {k: existing_by_seg[k] for k in sorted(existing_by_seg)}
    manifest = {
        "schema": "william.audio.install/1",
        "model_id": MODEL_ID,
        "format": {"codec": "flac", "sample_rate_hz": 16000, "channels": 1, "compression_level": 8, "metadata_stripped": True},
        "voice_registry": "audio/voices.json",
        "segments_count": len(ordered),
        "total_duration_s": round(sum(v["duration_s"] for v in ordered.values()), 2),
        "total_bytes": sum(v["bytes"] for v in ordered.values()),
        "by_segment": ordered,
    }
    args.install_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.install_manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    elapsed = time_mod.time() - t0
    print(
        f"\nInstalled {len(ordered)} segments ({manifest['total_duration_s']/60:.1f} min, "
        f"{manifest['total_bytes']/1024/1024:.2f} MB) in {elapsed:.1f}s -> {args.install_manifest}",
        flush=True,
    )
    if not args.skip_stamp:
        stamp_summary = stamp_journal_tree(args.journal_dir)
        print(f"Stamped journal tree: {stamp_summary}", flush=True)


if __name__ == "__main__":
    main()
