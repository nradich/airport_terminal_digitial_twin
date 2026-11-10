"""Kit --exec entry point. Runs only in desktop Composer, never in Spark."""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import carb
import omni.kit.app
import omni.kit.async_engine
import omni.ui as ui
import omni.usd
from omni.kit.viewport.utility import (
    frame_viewport_prims,
    get_active_viewport,
    get_active_viewport_window,
)
from pxr import Usd, UsdLux

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "kit")]
from airport_labels import AssetLabels  # noqa: E402

from airport_twin.viewer import load_bundle  # noqa: E402

busy = False
labels = None
window = ui.Window("Airport snapshots", width=360, height=140)


async def open_snapshot(scenario: str) -> None:
    """Open an explicit exported snapshot with session-only preview lighting."""
    global busy, labels
    if busy:
        return
    busy = True
    status.text = f"Loading {scenario}..."
    try:
        if scenario not in {"baseline", "delay_A4"}:
            raise ValueError("Choose baseline or delay_A4")
        path = ROOT / ".local" / "omniverse-test" / f"{scenario}.usda"
        if not path.is_file():
            raise FileNotFoundError(f"Export the scene bundle first: {path}")
        context = omni.usd.get_context()
        bundle = load_bundle(ROOT / ".local" / "omniverse-test" / "viewer.json")
        success, error = await context.open_stage_async(str(path))
        if not success:
            raise RuntimeError(error)
        stage = context.get_stage()
        files = [Path(layer.realPath) for layer in stage.GetUsedLayers() if layer.realPath]
        checksums = {file: hashlib.sha256(file.read_bytes()).hexdigest() for file in files}
        with Usd.EditContext(stage, stage.GetSessionLayer()):
            light = UsdLux.DomeLight.Define(stage, "/AirportPreview/Light")
            light.CreateIntensityAttr(700.0)
        for _ in range(8):
            await omni.kit.app.get_app().next_update_async()
        viewport = get_active_viewport()
        if viewport is None or not frame_viewport_prims(viewport, ["/World/Concourse_A"]):
            raise RuntimeError("Could not frame the airport viewport")
        context.get_selection().set_selected_prim_paths([], False)
        if labels is not None:
            labels.destroy()
        labels = AssetLabels(get_active_viewport_window(), bundle["labels"])
        assets = [prim for prim in stage.Traverse() if prim.HasAttribute("twin:asset_id")]
        if len(assets) != 10:
            raise RuntimeError(f"Expected ten assets, found {len(assets)}")
        a4 = stage.GetPrimAtPath("/World/Concourse_A/Gate_A4")
        severity = a4.GetAttribute("twin:status").Get()
        if severity != ("ok" if scenario == "baseline" else "crit"):
            raise RuntimeError(f"Unexpected A4 status: {severity}")
        if any(
            hashlib.sha256(file.read_bytes()).hexdigest() != sha for file, sha in checksums.items()
        ):
            raise RuntimeError("Opening the viewer modified a published USD layer")
        status.text = f"{scenario} | A4: {severity} | 10 assets"
        carb.log_info(f"AIRPORT_VIEWER_READY scenario={scenario} A4={severity} assets=10")
    except Exception as error:
        status.text = str(error)
        carb.log_error(f"AIRPORT_VIEWER_ERROR {error}")
    finally:
        busy = False


with window.frame:
    with ui.VStack(spacing=8):
        with ui.HStack(spacing=8):
            ui.Button(
                "Baseline",
                clicked_fn=lambda: omni.kit.async_engine.run_coroutine(open_snapshot("baseline")),
            )
            ui.Button(
                "Delay A4",
                clicked_fn=lambda: omni.kit.async_engine.run_coroutine(open_snapshot("delay_A4")),
            )
        status = ui.Label("Preparing airport scene", word_wrap=True)


async def start() -> None:
    # The standard Composer setup creates its default stage after five frames.
    for _ in range(10):
        await omni.kit.app.get_app().next_update_async()
    await open_snapshot(os.getenv("TWIN_VIEWER_SCENARIO", "delay_A4"))


omni.kit.async_engine.run_coroutine(start())
