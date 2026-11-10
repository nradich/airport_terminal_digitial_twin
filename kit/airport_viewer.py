"""Thin native renderer/controller. Governed data and interpolation live in the library."""

from __future__ import annotations

import asyncio
import hashlib
import os
from pathlib import Path

import carb
import carb.settings
import omni.kit.app
import omni.kit.async_engine
import omni.ui as ui
import omni.usd
from airport_labels import AssetLabels
from airport_panel import SnapshotPanel
from omni.kit.viewport.utility import (
    get_active_viewport,
    get_active_viewport_window,
)
from pxr import Gf, Sdf, Usd, UsdGeom

from airport_twin.playback import animate_frame
from airport_twin.presentation import linear_rgb
from airport_twin.viewer import load_bundle


class AirportViewer:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = Path(os.getenv(
            "TWIN_VIEWER_DIRECTORY", str(root / ".local/omniverse-test")
        )).resolve()
        self.bundle = load_bundle(self.directory / "viewer.json")
        self.assets = self.bundle["runs"][0]["publication"]["assets"]
        self.current = None
        self.step = 59
        self.busy = False
        self.play_task = None
        self.previous_guides = {}
        self.previous_windows = {}
        self.panel = SnapshotPanel(
            self.bundle["legend"],
            self.choose_scenario,
            self.seek,
            self.play_pause,
            self.replay,
            self.camera,
            self.film_mode,
            self.capture_frame,
        )
        self.labels = None
        self.checksums = {}
        omni.kit.async_engine.run_coroutine(self.start())

    def camera(self, name: str) -> None:
        if self.busy:
            return
        viewport = get_active_viewport()
        if viewport is not None and name in {"Overview", "A4CloseUp"}:
            viewport.camera_path = "/World/Film/" + name

    def film_mode(self, enabled: bool) -> None:
        if self.busy:
            return
        viewport = get_active_viewport()
        if viewport is None:
            return
        settings = carb.settings.get_settings()
        for item in (
            "guide/grid",
            "guide/axis",
            "guide/selection",
            "scene/cameras",
            "scene/lights",
            "hud/renderFPS",
            "hud/renderResolution",
            "hud/deviceMemory",
            "hud/hostMemory",
        ):
            key = f"/persistent/app/viewport/{viewport.id}/{item}/visible"
            if key not in self.previous_guides:
                self.previous_guides[key] = bool(settings.get(key))
            settings.set(key, False if enabled else self.previous_guides[key])
        for title in (
            "Stage",
            "Layer",
            "Property",
            "Content",
            "Environments",
            "Materials",
            "Console",
            "Configurator Samples",
            "Render Settings",
            "Variant Presenter",
        ):
            window = ui.Workspace.get_window(title)
            if window:
                self.previous_windows.setdefault(title, bool(window.visible))
                window.visible = False if enabled else self.previous_windows[title]

    def choose_scenario(self, scenario: str) -> None:
        omni.kit.async_engine.run_coroutine(self.switch(scenario))

    async def switch(self, scenario: str) -> None:
        self.pause()
        await asyncio.sleep(0)
        if self.busy:
            return
        run = next(r for r in self.bundle["runs"] if r["scenario"] == scenario)
        await self.apply_frame(run, min(self.step, run["minutes"] - 1), 1.5)

    def seek(self, step: int) -> None:
        omni.kit.async_engine.run_coroutine(self.seek_async(step))

    async def seek_async(self, step: int) -> None:
        self.pause()
        await asyncio.sleep(0)
        if self.current is not None and not self.busy:
            await self.apply_frame(self.current, step)

    def pause(self) -> None:
        if self.play_task is not None:
            self.play_task.cancel()
            self.play_task = None
        self.panel.play_button.text = "Play"

    def play_pause(self) -> None:
        if self.play_task is not None:
            self.pause()
        elif self.current is not None and not self.busy:
            self.play_task = omni.kit.async_engine.run_coroutine(self.play())

    def replay(self) -> None:
        omni.kit.async_engine.run_coroutine(self.restart())

    async def restart(self) -> None:
        self.pause()
        await asyncio.sleep(0)
        if self.current is not None and not self.busy:
            self.play_task = omni.kit.async_engine.run_coroutine(self.play(reset=True))

    async def play(self, reset: bool = False) -> None:
        self.panel.play_button.text = "Pause"
        try:
            if reset or self.step == self.current["minutes"] - 1:
                await self.apply_frame(self.current, 0)
            while self.step < self.current["minutes"] - 1:
                await asyncio.sleep(0.15)
                await self.apply_frame(self.current, self.step + 1, 0.08)
        except asyncio.CancelledError:
            pass
        finally:
            self.play_task = None
            self.panel.play_button.text = "Play"

    def colours(self, values: dict[str, tuple]) -> None:
        stage = omni.usd.get_context().get_stage()
        with Usd.EditContext(stage, stage.GetSessionLayer()):
            for asset in self.assets:
                prim = stage.GetPrimAtPath(asset["prim_path"])
                UsdGeom.Gprim(prim).CreateDisplayColorAttr([Gf.Vec3f(*values[asset["asset_id"]])])

    async def apply_frame(self, run: dict, step: int, duration: float = 0) -> None:
        if self.busy:
            return
        self.busy = True
        self.panel.slider.enabled = False
        try:
            frame = run["frames"][step]
            stage = omni.usd.get_context().get_stage()
            start = {
                asset["asset_id"]: tuple(
                    UsdGeom.Gprim(stage.GetPrimAtPath(asset["prim_path"]))
                    .GetDisplayColorAttr()
                    .Get()[0]
                )
                for asset in self.assets
            }
            self.panel.status.text = f"Transitioning to {run['scenario']} · minute {step}"
            await animate_frame(
                start,
                frame["states"],
                self.assets,
                duration,
                self.colours,
                omni.kit.app.get_app().next_update_async,
                lambda: self.commit_frame(run, step),
            )
        except Exception as error:
            self.panel.status.text = str(error)
            carb.log_error(f"AIRPORT_FILM_ERROR {error}")
        finally:
            self.busy = False
            self.panel.slider.enabled = True

    def commit_frame(self, run: dict, step: int) -> None:
        frame = run["frames"][step]
        stage = omni.usd.get_context().get_stage()
        self.colours({r["asset_id"]: linear_rgb(r["colour"]) for r in frame["states"]})
        with Usd.EditContext(stage, stage.GetSessionLayer()):
            for row in frame["states"]:
                stage.GetPrimAtPath(row["prim_path"]).CreateAttribute(
                    "twin:status", Sdf.ValueTypeNames.String
                ).Set(row["status"])
            stage.GetSessionLayer().customLayerData = {
                "run_id": run["run_id"],
                "scenario": run["scenario"],
                "step": step,
                "source_push_id": frame["push"]["push_id"],
            }
        self.current, self.step = run, step
        self.panel.update(run, step)
        a4 = next(row for row in frame["states"] if row["asset_id"] == "GATE_A4")
        self.panel.status.text = f"A4: {a4['status']} · {frame['ts']} UTC"

    async def start(self) -> None:
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()
        try:
            scenario = os.getenv("TWIN_VIEWER_SCENARIO", "baseline")
            run = next(r for r in self.bundle["runs"] if r["scenario"] == scenario)
            path = self.directory / f"{scenario}.usda"
            context = omni.usd.get_context()
            success, error = await context.open_stage_async(str(path))
            if not success:
                raise RuntimeError(error)
            stage = context.get_stage()
            self.checksums = {
                Path(layer.realPath): hashlib.sha256(Path(layer.realPath).read_bytes()).hexdigest()
                for layer in stage.GetUsedLayers()
                if layer.realPath
            }
            if len([p for p in stage.Traverse() if p.HasAttribute("twin:asset_id")]) != 10:
                raise RuntimeError("Expected ten asset prims")
            for _ in range(8):
                await omni.kit.app.get_app().next_update_async()
            self.labels = AssetLabels(get_active_viewport_window(), self.bundle["labels"])
            self.camera("Overview")
            self.film_mode(True)
            panel = ui.Workspace.get_window("Airport snapshots")
            viewport = ui.Workspace.get_window(get_active_viewport_window().title)
            if panel and viewport:
                panel.dock_in(viewport, ui.DockPosition.RIGHT, 0.26)
            await self.apply_frame(run, run["minutes"] - 1)
            if any(
                hashlib.sha256(path.read_bytes()).hexdigest() != sha
                for path, sha in self.checksums.items()
            ):
                raise RuntimeError("Published scene layer changed")
            carb.log_info(f"AIRPORT_FILM_READY {scenario} labels=10 replay_steps={run['minutes']}")
            if os.getenv("TWIN_CAPTURE_ALL") == "1":
                await self.capture_all()
        except Exception as error:
            self.panel.status.text = str(error)
            carb.log_error(f"AIRPORT_FILM_ERROR {error}")

    def capture_frame(self) -> None:
        omni.kit.async_engine.run_coroutine(self.capture_current())

    async def capture_current(self) -> None:
        self.pause()
        await asyncio.sleep(0)
        if self.busy or self.current is None:
            return
        self.busy = True
        self.panel.slider.enabled = False
        try:
            await self.render_capture()
        finally:
            self.busy = False
            self.panel.slider.enabled = True

    async def render_capture(self) -> None:
        from omni.kit.renderer.capture import acquire_renderer_capture_interface

        from airport_twin.captures import capture_receipt

        run, step = self.current, self.step
        camera = str(get_active_viewport().camera_path).rsplit("/", 1)[-1]
        # All display opinions must match the exact audited frame before rendering.
        stage = omni.usd.get_context().get_stage()
        for row in run["frames"][step]["states"]:
            actual = (
                UsdGeom.Gprim(stage.GetPrimAtPath(row["prim_path"])).GetDisplayColorAttr().Get()[0]
            )
            if any(
                abs(a - b) > 1e-6 for a, b in zip(actual, linear_rgb(row["colour"]), strict=True)
            ):
                raise ValueError("Viewport differs from the audited frame")
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()
        folder = self.directory / "captures"
        folder.mkdir(parents=True, exist_ok=True)
        pending = folder / "pending.png"
        renderer = acquire_renderer_capture_interface()
        renderer.capture_next_frame_swapchain(str(pending))
        for _ in range(3):
            await omni.kit.app.get_app().next_update_async()
        renderer.wait_async_capture()
        receipt = capture_receipt(folder, pending, run, step, camera)
        carb.log_info(f"AIRPORT_CAPTURE_OK {receipt}")

    async def capture_all(self) -> None:
        self.camera("Overview")
        for run in self.bundle["runs"]:
            for step in range(run["minutes"]):
                await self.apply_frame(run, step)
                if self.current != run or self.step != step:
                    raise RuntimeError("Capture preflight did not reach its audited frame")
                await self.capture_current()
        await self.apply_frame(self.bundle["runs"][0], 59)
        carb.log_info("AIRPORT_CAPTURE_ALL_OK frames=120")
