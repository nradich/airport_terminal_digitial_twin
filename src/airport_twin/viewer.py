"""Governed viewer artifacts. Desktop reads published files, never a side database."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_bundle(path: Path) -> dict[str, Any]:
    """Read a local copy of an immutable Volume/MLflow viewer artifact."""
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("format_version") != 1 or not value.get("labels") or not value.get("runs"):
        raise ValueError("Invalid viewer artifact; run prepare-viewer first")
    return value


def prepare_bundle(platform: Any, run_ids: list[str]) -> dict[str, Any]:
    """Resolve explicit runs through UC assets/scene_pushes and MLflow."""
    from airport_twin.bridge import UsdVolumeTransport
    from airport_twin.presentation import asset_labels
    from airport_twin.scene import canonical, digest
    from airport_twin.tracking import assert_run, client

    assets = [r.asDict() for r in platform.spark.table(platform.config.table("assets")).collect()]
    runs = []
    c = client(platform.config)
    for run_id in run_ids:
        run = assert_run(platform.config, run_id)
        push_id = run.data.tags.get("twin.last_push_id")
        frame = platform.spark.table(platform.config.table("scene_pushes"))
        rows = frame.where((frame.run_id == run_id) & (frame.push_id == push_id)).collect()
        if len(rows) != 1:
            raise ValueError("Run must have one explicitly linked successful scene push")
        audit = rows[0].asDict()
        manifest = json.loads((Path(audit["usd_path"]).parent / "manifest.json").read_text())
        if manifest["run_id"] != run_id or manifest["push_id"] != push_id:
            raise ValueError("Scene audit and publication disagree")
        runs.append(
            {
                "run_id": run_id,
                "scenario": run.data.params["scenario"],
                "publication": manifest,
                "audit": audit,
            }
        )
    if {r["scenario"] for r in runs} != {"baseline", "delay_A4"} or len(runs) != 2:
        raise ValueError("Supply exactly one baseline and one delay_A4 run")
    bundle = {
        "format_version": 1,
        "namespace": platform.config.namespace,
        "labels": asset_labels(assets),
        "runs": runs,
        "assets_version": platform.versions()["assets"],
    }
    payload = canonical(bundle)
    bundle_id = digest(payload)
    relative = f"viewer/{bundle_id}/viewer.json"
    UsdVolumeTransport(platform.volume_root()).publish(relative, payload)
    for run_id in run_ids:
        c.log_dict(run_id, json.loads(payload), relative)
        c.set_tag(run_id, "twin.viewer_artifact", relative)
    return {"bundle_id": bundle_id, "artifact_path": relative}


def export_bundle(config: Any, run_id: str, destination: Path) -> Path:
    """Retrieve the governed artifact and complete relative USD composition trees."""
    from pxr import Sdf, Usd, UsdGeom

    from airport_twin.scene.usd import verify_composition
    from airport_twin.tracking import assert_run, client

    destination = destination.resolve()
    c = client(config)
    run = assert_run(config, run_id)
    artifact = run.data.tags.get("twin.viewer_artifact")
    if not artifact:
        raise ValueError("Prepare a viewer bundle for the explicit run first")
    destination.mkdir(parents=True, exist_ok=True)
    bundle = load_bundle(Path(c.download_artifacts(run_id, artifact)))
    for item in bundle["runs"]:
        folder = destination / item["scenario"]
        folder.mkdir(exist_ok=True)
        scene = Path(c.download_artifacts(item["run_id"], "scene", str(folder)))
        publication = item["publication"]
        state = (
            scene
            / "runs"
            / item["run_id"]
            / publication["push_id"]
            / f"terminal_state_{item['run_id']}.usda"
        )
        verify_composition(state, publication["states"])
        stage = Usd.Stage.CreateInMemory()
        stage.GetRootLayer().defaultPrim = "World"
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
        UsdGeom.SetStageMetersPerUnit(stage, 1.0)
        layer = Sdf.Layer.CreateAnonymous(".usda")
        layer.TransferContent(stage.GetRootLayer())
        layer.subLayerPaths = [state.relative_to(destination).as_posix()]
        layer.Export(str(destination / f"{item['scenario']}.usda"))
    target = destination / "viewer.json"
    target.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    return target
