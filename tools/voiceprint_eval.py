#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Copyright (c) 2026 sol pbc

"""WeSpeaker ResNet34-256 voiceprint extraction & evaluation harness for the William journal.

Mirrors solstone-journal's production speaker-embedding pipeline:
  - `core/crates/solstone-core-speakers/src/filterbank.rs` (80-bin Kaldi log-mel, Povey window, CMN)
  - `core/crates/solstone-core-speakers-onnx/src/wespeaker.rs` (`wespeaker-resnet34-256.onnx`, 256-d)
  - `core/crates/solstone-core-speaker-id/src/calibration.rs` (production thresholds)

Run via `uv run --with onnxruntime --with numpy python3 tools/voiceprint_eval.py ...`
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np
import onnxruntime as ort

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOLSTONE_REPO = Path(os.environ.get("WILLIAM_SOLSTONE_REPO") or Path.home() / "projects" / "solstone-journal")
DEFAULT_MODEL_PATH = DEFAULT_SOLSTONE_REPO / "core" / "models" / "assets" / "wespeaker-resnet34-256.onnx"
DEFAULT_FIXTURE_PATH = DEFAULT_SOLSTONE_REPO / "core" / "fixtures" / "speaker_filterbank.json"

SAMPLE_RATE = 16_000
MEL_BINS = 80
FRAME_LEN = 400
FRAME_SHIFT = 160
FFT_SIZE = 512
LOW_FREQ = 20.0
HIGH_FREQ = SAMPLE_RATE / 2.0
PREEMPH = 0.97
AUDIO_SCALE = 32768.0
F32_EPS = float(np.finfo(np.float32).eps)

# Pinned from solstone-journal calibration.rs, candidate_tracker.rs, run_numbers.rs
THRESHOLDS: dict[str, float] = {
    "VP_OUTLIER_MIN_SIMILARITY": 0.18,
    "ACOUSTIC_OPEN_MARGIN_MIN": 0.20,
    "ACOUSTIC_MEDIUM": 0.22,
    "ACOUSTIC_HIGH": 0.36,
    "OWNER_THRESHOLD": 0.43,
    "CONSOLIDATE_MERGE_THRESHOLD": 0.65,
    "RUN_MATCH": 0.72,
}


def _mel_scale(freq: np.ndarray | float) -> np.ndarray | float:
    return np.float32(1127.0) * np.log(np.float32(1.0) + np.float32(freq) / np.float32(700.0))


def _build_povey_window() -> np.ndarray:
    idx = np.arange(FRAME_LEN, dtype=np.float64)
    scale = 2.0 * math.pi / (FRAME_LEN - 1.0)
    return np.power(0.5 - 0.5 * np.cos(scale * idx), 0.85).astype(np.float32)


def _build_mel_bank() -> np.ndarray:
    mel_low = float(_mel_scale(LOW_FREQ))
    mel_high = float(_mel_scale(HIGH_FREQ))
    delta = (mel_high - mel_low) / (MEL_BINS + 1.0)
    fft_bin_width = SAMPLE_RATE / float(FFT_SIZE)
    freqs = np.arange(FFT_SIZE // 2, dtype=np.float32) * np.float32(fft_bin_width)
    mels = _mel_scale(freqs).astype(np.float32)
    bank = np.zeros((MEL_BINS, FFT_SIZE // 2), dtype=np.float32)
    for b in range(MEL_BINS):
        left = np.float32(mel_low + b * delta)
        center = np.float32(mel_low + (b + 1.0) * delta)
        right = np.float32(mel_low + (b + 2.0) * delta)
        mask_l = (mels > left) & (mels <= center)
        mask_r = (mels > center) & (mels < right)
        bank[b, mask_l] = (mels[mask_l] - left) / (center - left)
        bank[b, mask_r] = (right - mels[mask_r]) / (right - center)
    return bank


POVEY = _build_povey_window()
MEL_BANK = _build_mel_bank()


def compute_wespeaker_filterbank_cmn(audio: np.ndarray) -> np.ndarray:
    audio = np.asarray(audio, dtype=np.float32)
    n = audio.shape[0]
    if n < FRAME_LEN:
        return np.zeros((0, MEL_BINS), dtype=np.float32)
    num_frames = 1 + (n - FRAME_LEN) // FRAME_SHIFT
    idx = np.arange(FRAME_LEN)[None, :] + np.arange(num_frames)[:, None] * FRAME_SHIFT
    frames = audio[idx] * np.float32(AUDIO_SCALE)
    frames = frames - frames.mean(axis=1, keepdims=True, dtype=np.float32)
    pre = np.empty_like(frames)
    pre[:, 0] = frames[:, 0] - np.float32(PREEMPH) * frames[:, 0]
    pre[:, 1:] = frames[:, 1:] - np.float32(PREEMPH) * frames[:, :-1]
    pre *= POVEY[None, :]
    padded = np.zeros((num_frames, FFT_SIZE), dtype=np.float32)
    padded[:, :FRAME_LEN] = pre
    spec = np.fft.rfft(padded, n=FFT_SIZE, axis=1)
    power = (spec.real.astype(np.float32) ** 2 + spec.imag.astype(np.float32) ** 2)[:, : FFT_SIZE // 2]
    energies = power @ MEL_BANK.T
    log_energies = np.log(np.maximum(energies, np.float32(F32_EPS))).astype(np.float32)
    log_energies = log_energies - log_energies.mean(axis=0, keepdims=True, dtype=np.float32)
    return log_energies


def verify_filterbank_parity(fixture_path: Path = DEFAULT_FIXTURE_PATH) -> float:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    raw = base64.b64decode(fixture["waveform"]["samples_f32_le_base64"])
    audio = np.frombuffer(raw, dtype="<f4")
    got = compute_wespeaker_filterbank_cmn(audio)
    rows = fixture["matrices"]["filterbank_cmn"]["rows"]
    expected = np.array([[float(x) for x in r.split()] for r in rows], dtype=np.float32)
    if got.shape != expected.shape:
        raise AssertionError(f"Filterbank shape mismatch: {got.shape} vs {expected.shape}")
    max_diff = float(np.max(np.abs(got - expected)))
    if max_diff >= 1e-2:
        raise AssertionError(f"Filterbank parity failed: max_abs_diff={max_diff}")
    return max_diff


def open_session(model_path: Path = DEFAULT_MODEL_PATH, threads: int = 8) -> ort.InferenceSession:
    so = ort.SessionOptions()
    so.intra_op_num_threads = threads
    so.inter_op_num_threads = 1
    return ort.InferenceSession(str(model_path), sess_options=so, providers=["CPUExecutionProvider"])


def decode_audio_16k(path: Path, start_s: float | None = None, end_s: float | None = None) -> np.ndarray:
    cmd = ["ffmpeg", "-v", "error"]
    if start_s is not None:
        cmd += ["-ss", f"{start_s:.4f}"]
    if end_s is not None:
        cmd += ["-to", f"{end_s:.4f}"]
    cmd += ["-i", str(path), "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "f32le", "pipe:1"]
    proc = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return np.frombuffer(proc.stdout, dtype="<f4").copy()


def l2_norm(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-12 else v


def embed_audio(session: ort.InferenceSession, audio: np.ndarray) -> np.ndarray:
    feats = compute_wespeaker_filterbank_cmn(audio)
    if feats.shape[0] < 16:
        raise ValueError(f"Audio too short: {feats.shape[0]} frames")
    out = session.run(None, {"feats": feats[None, :, :]})[0][0]
    return l2_norm(out.astype(np.float64))


def evaluate_corpus(
    journal_dir: Path,
    install_manifest_path: Path,
    voices_path: Path,
    voiceprints_out: Path | None = None,
    model_path: Path = DEFAULT_MODEL_PATH,
    fixture_path: Path = DEFAULT_FIXTURE_PATH,
    min_turn_s: float = 1.5,
) -> dict[str, Any]:
    parity = verify_filterbank_parity(fixture_path) if fixture_path.is_file() else None
    session = open_session(model_path)
    voices = json.loads(voices_path.read_text(encoding="utf-8"))
    install = json.loads(install_manifest_path.read_text(encoding="utf-8"))
    by_seg = install["by_segment"]
    slugs = [v["slug"] for v in voices]

    # Collect per-speaker audio across all installed segments to compute corpus centroids + turn eval
    # Use leave-one-segment-out centroid (or pooled audio across segments) so eval has zero self-leakage!
    seg_turn_embs: list[tuple[str, int, str, float, np.ndarray]] = []
    seg_spk_emb: dict[tuple[str, str], np.ndarray] = {}
    spk_all_embs: dict[str, list[np.ndarray]] = {s: [] for s in slugs}
    spk_seg_count: dict[str, int] = {s: 0 for s in slugs}
    spk_dur_s: dict[str, float] = {s: 0.0 for s in slugs}

    chronicle = journal_dir / "chronicle"
    for rel in sorted(by_seg):
        seg_dir = chronicle / rel
        flac = seg_dir / "audio.flac"
        jsonl = seg_dir / "audio.jsonl"
        if not flac.is_file() or not jsonl.is_file():
            continue
        lines = [json.loads(ln) for ln in jsonl.read_text(encoding="utf-8").splitlines() if ln.strip()][1:]
        wav_full = decode_audio_16k(flac)
        by_spk: dict[str, list[np.ndarray]] = {}
        for rec in lines:
            spk = rec.get("speaker")
            if spk not in spk_all_embs:
                continue
            s0, e0 = float(rec["timing"]["start"]), float(rec["timing"]["end"])
            seg_wav = wav_full[int(round(s0 * SAMPLE_RATE)) : int(round(e0 * SAMPLE_RATE))]
            if len(seg_wav) < int(0.4 * SAMPLE_RATE):
                continue
            by_spk.setdefault(spk, []).append(seg_wav)
            spk_dur_s[spk] += len(seg_wav) / SAMPLE_RATE
            if (e0 - s0) >= min_turn_s and len(seg_wav) >= int(1.2 * SAMPLE_RATE):
                te = embed_audio(session, seg_wav)
                seg_turn_embs.append((rel, int(rec["sentence_id"]), spk, round(e0 - s0, 2), te))
        for spk, chunks in by_spk.items():
            joined = np.concatenate(chunks)
            if len(joined) >= SAMPLE_RATE:
                emb = embed_audio(session, joined)
                seg_spk_emb[rel, spk] = emb
                spk_all_embs[spk].append(emb)
                spk_seg_count[spk] += 1

    # Compute L2-normalized centroid per speaker across all segments where they speak
    centroids: dict[str, np.ndarray] = {}
    for s in slugs:
        if spk_all_embs[s]:
            centroids[s] = l2_norm(np.mean(np.stack(spk_all_embs[s], axis=0), axis=0))

    active_slugs = [s for s in slugs if s in centroids]
    C = np.stack([centroids[s] for s in active_slugs], axis=0)
    S = C @ C.T

    # Strict held-out turn top-1 evaluation:
    # - speakers with >=2 segments: leave-one-segment-out centroid
    # - speakers with 1 segment (>=2 turns): leave-one-turn-out centroid (zero self-leakage)
    spk_emb_sum: dict[str, np.ndarray] = {
        s: np.sum(np.stack(spk_all_embs[s], axis=0), axis=0) for s in active_slugs
    }
    spk_turn_sum: dict[str, np.ndarray] = {}
    spk_turn_count: dict[str, int] = {}
    for _rel, _sid, spk, _dur, te in seg_turn_embs:
        spk_turn_sum[spk] = spk_turn_sum.get(spk, np.zeros(256, dtype=np.float64)) + te
        spk_turn_count[spk] = spk_turn_count.get(spk, 0) + 1

    per_spk_hits: dict[str, list[int]] = {s: [0, 0] for s in active_slugs}
    per_spk_margins: dict[str, list[float]] = {s: [] for s in active_slugs}
    mismatches: list[dict[str, Any]] = []
    for rel, sid, spk, dur, te in seg_turn_embs:
        if spk not in centroids:
            continue
        if spk_seg_count[spk] >= 2 and (rel, spk) in seg_spk_emb:
            own_c = l2_norm(spk_emb_sum[spk] - seg_spk_emb[rel, spk])
        elif spk_turn_count.get(spk, 0) >= 2:
            own_c = l2_norm(spk_turn_sum[spk] - te)
        else:
            own_c = centroids[spk]
        own_score = float(te @ own_c)
        best_imp_s, best_imp_n = -2.0, ""
        for other in active_slugs:
            if other == spk:
                continue
            sc = float(te @ centroids[other])
            if sc > best_imp_s:
                best_imp_s, best_imp_n = sc, other
        hit = own_score > best_imp_s
        per_spk_hits[spk][1] += 1
        if hit:
            per_spk_hits[spk][0] += 1
        else:
            mismatches.append(
                {
                    "rel": rel,
                    "sentence_id": sid,
                    "expected": spk,
                    "predicted": best_imp_n,
                    "own_score": round(own_score, 4),
                    "impostor_score": round(best_imp_s, 4),
                    "dur_s": dur,
                }
            )
        per_spk_margins[spk].append(own_score - best_imp_s)

    # In-scene pooled inter-speaker cosines across all multi-speaker segments
    by_rel_spks: dict[str, list[str]] = {}
    for rel, spk in seg_spk_emb:
        by_rel_spks.setdefault(rel, []).append(spk)
    in_scene_pairs: list[tuple[float, str, str, str]] = []
    for rel, spks in by_rel_spks.items():
        if len(spks) < 2:
            continue
        for i in range(len(spks)):
            for j in range(i + 1, len(spks)):
                a, b = spks[i], spks[j]
                in_scene_pairs.append((float(seg_spk_emb[rel, a] @ seg_spk_emb[rel, b]), rel, a, b))
    in_scene_pairs.sort(reverse=True)

    # Pairwise centroid pairs
    centroid_pairs = sorted(
        [
            (float(S[i, j]), active_slugs[i], active_slugs[j])
            for i in range(len(active_slugs))
            for j in range(i + 1, len(active_slugs))
        ],
        reverse=True,
    )

    total_hits = sum(v[0] for v in per_spk_hits.values())
    total_turns = sum(v[1] for v in per_spk_hits.values())
    in_vals = np.array([x[0] for x in in_scene_pairs]) if in_scene_pairs else np.array([0.0])

    voice_by_slug = {v["slug"]: v for v in voices}
    speaker_records: dict[str, Any] = {}
    for i, s in enumerate(active_slugs):
        others = sorted([(float(S[i, j]), active_slugs[j]) for j in range(len(active_slugs)) if j != i], reverse=True)
        h, t = per_spk_hits[s]
        ms = per_spk_margins[s]
        speaker_records[s] = {
            "display_name": voice_by_slug[s].get("display_name", s),
            "voice_id": voice_by_slug[s]["voice_id"],
            "library_name": voice_by_slug[s].get("library_name", ""),
            "segments_count": spk_seg_count[s],
            "speech_seconds": round(spk_dur_s[s], 1),
            "turns_tested": t,
            "turns_top1": h,
            "top1_accuracy": round(h / t, 4) if t else None,
            "median_margin": round(float(np.median(ms)), 4) if ms else None,
            "p10_margin": round(float(np.percentile(ms, 10)), 4) if ms else None,
            "max_centroid_impostor": round(others[0][0], 4) if others else None,
            "max_centroid_impostor_slug": others[0][1] if others else None,
            "centroid_256": [round(float(x), 6) for x in centroids[s]],
        }

    result: dict[str, Any] = {
        "schema": "william.audio.voiceprints/1",
        "model": "wespeaker-resnet34-256.onnx",
        "embedding_dim": 256,
        "normalization": "l2_unit",
        "filterbank_parity_max_abs_diff": round(parity, 6) if parity is not None else None,
        "thresholds": THRESHOLDS,
        "evaluation": {
            "segments_evaluated": len(by_seg),
            "speakers_evaluated": len(active_slugs),
            "min_turn_seconds": min_turn_s,
            "protocol": "leave_one_segment_out_or_turn_out_centroid",
            "turns_tested": total_turns,
            "turns_top1": total_hits,
            "top1_accuracy": round(total_hits / total_turns, 5) if total_turns else None,
            "mismatches": mismatches,
            "centroid_max_pairwise_cosine": round(centroid_pairs[0][0], 4) if centroid_pairs else None,
            "centroid_top_pairs": [
                {"cosine": round(sc, 4), "a": a, "b": b} for sc, a, b in centroid_pairs[:10]
            ],
            "in_scene_pairs_count": len(in_scene_pairs),
            "in_scene_median": round(float(np.median(in_vals)), 4),
            "in_scene_p90": round(float(np.percentile(in_vals, 90)), 4),
            "in_scene_max": round(float(in_vals.max()), 4),
            "in_scene_ge_036": int((in_vals >= 0.36).sum()),
            "in_scene_ge_043": int((in_vals >= 0.43).sum()),
            "in_scene_top_pairs": [
                {"cosine": round(sc, 4), "rel": rel, "a": a, "b": b} for sc, rel, a, b in in_scene_pairs[:10]
            ],
        },
        "slugs": active_slugs,
        "centroid_cosine_matrix": [[round(float(S[i, j]), 4) for j in range(len(active_slugs))] for i in range(len(active_slugs))],
        "speakers": speaker_records,
    }
    if voiceprints_out is not None:
        voiceprints_out.parent.mkdir(parents=True, exist_ok=True)
        voiceprints_out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="WeSpeaker ResNet34-256 voiceprint builder & evaluator for William journal.")
    parser.add_argument("--journal-dir", type=Path, default=PROJECT_ROOT / "build" / "journal")
    parser.add_argument("--install-manifest", type=Path, default=PROJECT_ROOT / "audio" / "install.json")
    parser.add_argument("--voices", type=Path, default=PROJECT_ROOT / "audio" / "voices.json")
    parser.add_argument("--out", type=Path, default=PROJECT_ROOT / "audio" / "voiceprints.json")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE_PATH)
    parser.add_argument("--min-turn-s", type=float, default=1.5)
    args = parser.parse_args()

    res = evaluate_corpus(
        journal_dir=args.journal_dir,
        install_manifest_path=args.install_manifest,
        voices_path=args.voices,
        voiceprints_out=args.out,
        model_path=args.model,
        fixture_path=args.fixture,
        min_turn_s=args.min_turn_s,
    )
    ev = res["evaluation"]
    print(f"Parity max_abs_diff={res['filterbank_parity_max_abs_diff']}")
    print(f"Speakers={ev['speakers_evaluated']} Segments={ev['segments_evaluated']} Turns={ev['turns_top1']}/{ev['turns_tested']} ({100*(ev['top1_accuracy'] or 0):.2f}%)")
    print(f"Centroid max pair={ev['centroid_max_pairwise_cosine']} | In-scene pairs={ev['in_scene_pairs_count']} max={ev['in_scene_max']} >=0.36:{ev['in_scene_ge_036']} >=0.43:{ev['in_scene_ge_043']}")
    for s in res["slugs"]:
        sp = res["speakers"][s]
        print(
            f"  {s:<30} segs={sp['segments_count']:3d} dur={sp['speech_seconds']:6.1f}s "
            f"top1={sp['turns_top1']:3d}/{sp['turns_tested']:3d} med_m={sp['median_margin'] or 0:+.3f} "
            f"max_imp={sp['max_centroid_impostor']:+.3f} ({sp['max_centroid_impostor_slug']})"
        )
    if ev["mismatches"]:
        print(f"Mismatches ({len(ev['mismatches'])}):")
        for m in ev["mismatches"][:15]:
            print(" ", m)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
