"""Unit tests for the William journal photo generation tool (`photogen`)."""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

try:
    from PIL import Image
except ModuleNotFoundError:
    if "/usr/lib/python3/dist-packages" not in sys.path:
        sys.path.append("/usr/lib/python3/dist-packages")
    from PIL import Image

PHOTOGEN_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = PHOTOGEN_DIR.parent.parent


def _load_photogen():
    spec = importlib.util.spec_from_file_location("photogen", PHOTOGEN_DIR / "photogen.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["photogen"] = mod
    spec.loader.exec_module(mod)
    return mod


photogen = _load_photogen()


def _make_fake_jpeg_bytes(
    width: int = 1200,
    height: int = 896,
    color: tuple[int, int, int] = (90, 70, 50),
) -> bytes:
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def test_load_api_key_and_redaction(tmp_path: Path) -> None:
    fake_key = "AIzaSyFAKEKEY_FOR_TESTING_DO_NOT_LOG_1234567"
    vault_file = tmp_path / "vault-key.md"
    vault_file.write_text(
        f"# Test Vault Key\n\n- **name:** `test`\n- **key:** {fake_key}\n",
        encoding="utf-8",
    )

    loaded = photogen.load_api_key(vault_file)
    assert loaded == fake_key

    leaked_msg = f"HTTPError at https://example.com?key={fake_key}: invalid argument"
    redacted = photogen.redact_secret(leaked_msg, fake_key)
    assert fake_key not in redacted
    assert "[REDACTED_API_KEY]" in redacted


def test_load_api_key_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(photogen.PhotogenError, match="not found"):
        photogen.load_api_key(tmp_path / "nonexistent.md")

    bad_file = tmp_path / "bad.md"
    bad_file.write_text("no key here\n", encoding="utf-8")
    with pytest.raises(photogen.PhotogenError, match="Could not parse"):
        photogen.load_api_key(bad_file)


def test_compute_usage_and_cost() -> None:
    usage_meta = {
        "promptTokenCount": 300,
        "candidatesTokenCount": 1220,
        "thoughtsTokenCount": 900,
        "totalTokenCount": 2420,
        "candidatesTokensDetails": [
            {"modality": "IMAGE", "tokenCount": 1120},
            {"modality": "TEXT", "tokenCount": 100},
        ],
    }
    usage = photogen.compute_usage_and_cost(usage_meta)
    assert usage["prompt_tokens"] == 300
    assert usage["image_output_tokens"] == 1120
    assert usage["text_and_thinking_output_tokens"] == 1000
    assert usage["thoughts_tokens"] == 900
    assert usage["total_tokens"] == 2420

    expected_cost = (
        (300 / 1_000_000) * 1.50
        + (1120 / 1_000_000) * 30.00
        + ((100 + 900) / 1_000_000) * 7.50
    )
    assert usage["cost_usd"] == pytest.approx(expected_cost, abs=1e-6)


def test_prompts_sample_round_matches_canon_day_files() -> None:
    prompt_set = json.loads(
        (PHOTOGEN_DIR / "prompts_sample_round.json").read_text(encoding="utf-8")
    )
    assert prompt_set["default_model"] == "gemini-nano-banana-2.1"

    framings = prompt_set["framings"]
    assert [f["id"] for f in framings] == ["A", "B", "C"]

    shots = prompt_set["shots"]
    assert len(shots) == 20

    jobs = photogen.build_jobs_from_prompt_set(prompt_set)
    assert len(jobs) == 60
    assert [j["number"] for j in jobs] == list(range(1, 61))
    assert jobs[0]["code"] == "S01-A"
    assert jobs[-1]["code"] == "S20-C"

    # Verify every shot cites a real merged day file and matches its verbatim ### Photo prose
    for shot in shots:
        day_path = PROJECT_ROOT / shot["day_file"]
        assert day_path.is_file(), f"Missing day_file for {shot['id']}: {day_path}"
        day_text = day_path.read_text(encoding="utf-8")
        assert shot["photo_text"] in day_text, (
            f"Shot {shot['id']} ({shot['date']}) photo_text not found verbatim in {day_path}"
        )


def test_run_photogen_end_to_end_mocked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_key = "AIzaSyFAKEKEY_FOR_TESTING_DO_NOT_LOG_9999999"
    vault_file = tmp_path / "vault.md"
    vault_file.write_text(f"- **key:** {fake_key}\n", encoding="utf-8")

    mini_prompt_set = {
        "schema_version": 1,
        "default_model": "gemini-nano-banana-2.1",
        "default_parameters": {
            "aspectRatio": "4:3",
            "imageSize": "1K",
            "seed": 1595,
            "responseModalities": ["IMAGE"],
        },
        "framings": [
            {
                "id": "A",
                "slug": "iphone-natural",
                "name": "Framing A",
                "short_label": "A · 24mm",
                "instruction": "Instruction A.",
            },
            {
                "id": "B",
                "slug": "iphone-dof",
                "name": "Framing B",
                "short_label": "B · 50mm",
                "instruction": "Instruction B.",
            },
        ],
        "shots": [
            {
                "shot_index": 1,
                "id": "S01",
                "date": "2025-01-01",
                "time": "08:00",
                "title": "Joan's desk at first light",
                "place": "ansell_house",
                "region": "London",
                "setting": "inside",
                "season": "Winter",
                "lighting": "daylight (first light)",
                "category": "room & objects",
                "people_present": False,
                "entries": "S001",
                "shot_list_ref": "§ 7.7 #1",
                "day_file": "content/weeks/2025-01-01/merged/2025-01-01.md",
                "photo_text": "The desk at first light: the account book open at a fresh leaf.",
                "world_text": "§ 7.7 #1",
                "subject_prompt": "A plain scarred oak writing-table at first light.",
            }
        ],
    }
    prompts_file = tmp_path / "prompts.json"
    prompts_file.write_text(json.dumps(mini_prompt_set), encoding="utf-8")

    fake_jpeg = _make_fake_jpeg_bytes(1200, 896)

    def _fake_call_gemini(**kwargs):
        assert kwargs["api_key"] == fake_key
        return (
            fake_jpeg,
            "image/jpeg",
            {
                "prompt_tokens": 250,
                "image_output_tokens": 1120,
                "text_and_thinking_output_tokens": 800,
                "thoughts_tokens": 800,
                "candidates_tokens": 1120,
                "total_tokens": 2170,
                "cost_usd": 0.04,
            },
        )

    monkeypatch.setattr(photogen, "call_gemini_image_api", _fake_call_gemini)

    out_dir = tmp_path / "out-run"
    manifest = photogen.run_photogen(
        prompt_set_path=prompts_file,
        output_dir=out_dir,
        key_file=vault_file,
        workers=2,
        overwrite=True,
    )

    assert manifest["total_images"] == 2
    assert manifest["total_shots"] == 1
    assert manifest["total_framings"] == 2
    assert manifest["total_cost_usd"] == pytest.approx(0.08, abs=1e-6)
    assert (out_dir / "manifest.json").is_file()
    assert (out_dir / "index.html").is_file()

    # Ensure key never appears anywhere in output directory
    for p in out_dir.rglob("*"):
        if p.is_file() and p.suffix in {".json", ".html"}:
            assert fake_key not in p.read_text(encoding="utf-8")

    html_text = (out_dir / "index.html").read_text(encoding="utf-8")
    assert "#1" in html_text
    assert "#2" in html_text
    assert "S01-A" in html_text
    assert "S01-B" in html_text
    assert "openLightboxFromEl(this)" in html_text
    assert "Joan&#x27;s desk at first light" in html_text
    assert "The desk at first light: the account book open at a fresh leaf." in html_text


def test_budget_counts_spend_on_deleted_images_across_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vault_file = tmp_path / "vault.md"
    vault_file.write_text("- **key:** AIzaSyFAKEKEY_12345\n", encoding="utf-8")
    framing = {"id": "A", "slug": "a", "name": "Framing A", "short_label": "A", "instruction": "A."}
    shot = {
        "shot_index": 1, "id": "S01", "date": "2025-01-01", "time": "08:00", "title": "Desk",
        "place": "ansell_house", "region": "London", "setting": "inside", "season": "Winter",
        "lighting": "daylight", "category": "room & objects", "people_present": False,
        "entries": "S001", "shot_list_ref": "§ 7.7 #1",
        "day_file": "content/weeks/2025-01-01/merged/2025-01-01.md",
        "photo_text": "Desk.", "world_text": "§ 7.7 #1", "subject_prompt": "A desk.",
    }
    prompts_file = tmp_path / "prompts.json"
    prompts_file.write_text(
        json.dumps({
            "schema_version": 1,
            "default_model": "gemini-nano-banana-2.1",
            "default_parameters": {"aspectRatio": "4:3", "imageSize": "1K", "seed": 1, "responseModalities": ["IMAGE"]},
            "framings": [framing, {**framing, "id": "B", "slug": "b", "name": "Framing B", "short_label": "B"}],
            "shots": [shot],
        }),
        encoding="utf-8",
    )
    fake_jpeg = _make_fake_jpeg_bytes(1200, 896)
    monkeypatch.setattr(
        photogen,
        "call_gemini_image_api",
        lambda **kwargs: (
            fake_jpeg,
            "image/jpeg",
            {
                "prompt_tokens": 250, "image_output_tokens": 1120,
                "text_and_thinking_output_tokens": 800, "thoughts_tokens": 800,
                "candidates_tokens": 1120, "total_tokens": 2170, "cost_usd": 0.04,
            },
        ),
    )
    out_dir = tmp_path / "out"
    first = photogen.run_photogen(prompt_set_path=prompts_file, output_dir=out_dir, key_file=vault_file)
    assert first["spent_usd"] == pytest.approx(0.08, abs=1e-6)

    # Delete one keeper and regenerate it: the keepers still total $0.08,
    # but $0.12 has been paid, and the budget must see $0.12.
    (out_dir / first["items"][0]["image_rel_path"]).unlink()
    second = photogen.run_photogen(prompt_set_path=prompts_file, output_dir=out_dir, key_file=vault_file)
    assert second["total_cost_usd"] == pytest.approx(0.08, abs=1e-6)
    assert second["spent_usd"] == pytest.approx(0.12, abs=1e-6)

    (out_dir / second["items"][0]["image_rel_path"]).unlink()
    with pytest.raises(photogen.PhotogenError, match=r"\$0\.12 already spent"):
        photogen.run_photogen(
            prompt_set_path=prompts_file, output_dir=out_dir, key_file=vault_file, budget_usd=0.15
        )


def test_budget_and_max_images_guards(tmp_path: Path) -> None:
    vault_file = tmp_path / "vault.md"
    vault_file.write_text("- **key:** AIzaSyFAKEKEY_12345\n", encoding="utf-8")
    prompts_file = PHOTOGEN_DIR / "prompts_sample_round.json"

    with pytest.raises(photogen.PhotogenError, match="exceeding --max-images=10"):
        photogen.run_photogen(
            prompt_set_path=prompts_file,
            output_dir=tmp_path / "out1",
            key_file=vault_file,
            max_images=10,
        )

    with pytest.raises(photogen.PhotogenError, match="exceeds budget cap"):
        photogen.run_photogen(
            prompt_set_path=prompts_file,
            output_dir=tmp_path / "out2",
            key_file=vault_file,
            budget_usd=0.50,
        )


def test_enforce_repo_size_limit_preserves_originals_and_sidecar(tmp_path: Path) -> None:
    out_dir = tmp_path / "261117-round1"
    img_dir = out_dir / "images"
    img_dir.mkdir(parents=True)

    raw_bytes = _make_fake_jpeg_bytes(1600, 1200, color=(120, 80, 40))
    img_path = img_dir / "01_S01_A.jpg"
    img_path.write_bytes(raw_bytes)

    items = [
        {
            "number": 1,
            "image_rel_path": "images/01_S01_A.jpg",
            "width": 1600,
            "height": 1200,
            "bytes": len(raw_bytes),
        }
    ]
    orig_root = tmp_path / "var_tmp" / "william-photogen-261117-round1"
    info = photogen.enforce_repo_size_limit(
        output_dir=out_dir,
        items=items,
        max_repo_mb=0.0001,  # force downscaling
        originals_root=orig_root,
        jpeg_quality=80,
        max_width=1200,
    )

    assert info["downscaled"] is True
    assert Path(items[0]["original_path"]).is_file()
    assert Path(items[0]["original_path"]).read_bytes() == raw_bytes
    assert items[0]["width"] == 1200
    assert items[0]["height"] == 900
    sidecar = orig_root.parent / f".sweep-protect.{orig_root.name}"
    assert sidecar.is_file()
