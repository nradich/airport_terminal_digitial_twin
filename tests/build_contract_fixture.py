"""Synthetic browser contract assets; never used as live business data."""

import json
from pathlib import Path

from airport_twin.data import ASSETS, THRESHOLDS
from airport_twin.journey import Policy, simulate
from airport_twin.layout import CAMERAS
from airport_twin.presentation import asset_labels
from airport_twin.scene.glb import glb_bytes

assets = [
    dict(zip(("asset_id", "asset_type", "zone", "prim_path", "display_name"), row, strict=True))
    for row in ASSETS
]
for asset in assets:
    asset["asset_name"] = asset["display_name"]
folder = Path(__file__).resolve().parents[1] / "app/frontend/.local/contracts"
folder.mkdir(parents=True, exist_ok=True)
_, profiles = simulate(40, 1500, 42, 100, Policy())
(folder / "journey.json").write_text(json.dumps([{
    "run_id": "test-journey", "url": "https://mlflow.invalid/run/test-journey",
    "inputs": {"gate": "GATE_A4", "flight": "AT104", "budget": 1500,
               "close": "2026-11-09T22:30:00+00:00", "trials": 100, "queue": 40, "policy": {}},
    "profiles": profiles,
}]))
(folder / "terminal.glb").write_bytes(glb_bytes(assets))
(folder / "metadata.json").write_text(
    json.dumps({"labels": asset_labels(assets), "cameras": CAMERAS, "thresholds": THRESHOLDS})
)
