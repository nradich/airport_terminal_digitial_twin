import json

import pytest
from PIL import Image

from airport_twin.captures import capture_receipt, png_dimensions


def test_capture_receipt_records_exact_audited_frame(tmp_path):
    png = tmp_path / "render.png"
    Image.new("RGB", (640, 360), "red").save(png)
    audit = {
        "push_id": "push",
        "run_id": "run",
        "scenario": "delay_A4",
        "step": 0,
        "usd_path": "/Volumes/c/s/scenes/runs/run/push/state.usda",
    }
    run = {"run_id": "run", "scenario": "delay_A4", "frames": [{"push": audit}]}
    path = capture_receipt(tmp_path / "inbox", png, run, 0, "Overview")
    receipt = json.loads(path.read_text())
    assert receipt["step"] == 0 and receipt["push_id"] == "push"
    assert receipt["width"] == 640 and receipt["height"] == 360
    assert (path.parent / "frame.png").read_bytes() == png.read_bytes()
    assert capture_receipt(tmp_path / "inbox", png, run, 0, "Overview") == path
    assert json.loads(path.read_text())["captured_at"] == receipt["captured_at"]
    audit["run_id"] = "another-run"
    with pytest.raises(ValueError, match="lineage"):
        capture_receipt(tmp_path, png, run, 0, "Overview")


def test_capture_rejects_non_png_and_tiny_images(tmp_path):
    with pytest.raises(ValueError, match="PNG"):
        png_dimensions(b"not a screenshot")
    png = tmp_path / "tiny.png"
    Image.new("RGB", (10, 10)).save(png)
    with pytest.raises(ValueError, match="small"):
        png_dimensions(png.read_bytes())
