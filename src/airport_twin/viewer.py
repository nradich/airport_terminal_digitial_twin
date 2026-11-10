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
    from airport_twin.data import sql_text
    from airport_twin.presentation import METRICS, asset_labels, legend_data, metric_values
    from airport_twin.scene import digest, publish_replay
    from airport_twin.scene.cameras import story_layer_bytes
    from airport_twin.timeline import timeline_frames
    from airport_twin.tracking import assert_run, client, run_url
    from airport_twin.workflow import thresholds

    assets = [r.asDict() for r in platform.spark.table(platform.config.table("assets")).collect()]
    runs = []
    c = client(platform.config)
    migrate_push_metadata(platform)
    limits = thresholds(platform)
    palette = [
        r.asDict()
        for r in platform.spark.sql(
            "SELECT severity, CASE severity WHEN 0 THEN 'ok' "
            "WHEN 1 THEN 'warn' ELSE 'crit' END status, "
            + sql_text("colour.sql")
            + " colour FROM VALUES (0), (1), (2) AS scores(severity)"
        ).collect()
    ]
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
        if sorted(tuple(row) for row in manifest["thresholds"]) != limits:
            raise ValueError("Thresholds changed; republish the run before preparing the viewer")
        histories = {
            key: [{"step": m.step, "value": m.value} for m in c.get_metric_history(run_id, key)]
            for key in METRICS
        }
        for step in range(int(run.data.params["minutes"])):
            metric_values(histories, step)
        frames, timeline_versions = timeline_frames(platform, run_id)
        publications = publish_replay(
            platform, run_id, frames, timeline_versions, assets, limits, run.data.params["scenario"]
        )
        published = platform.spark.table(platform.config.table("scene_pushes"))
        audit_by_id = {
            row.push_id: row.asDict()
            for row in published.where(
                published.push_id.isin([p["push_id"] for p in publications])
            ).collect()
        }
        for frame, publication in zip(frames, publications, strict=True):
            audit_row = audit_by_id[publication["push_id"]]
            if (audit_row["run_id"], audit_row["scenario"], audit_row["step"]) != (
                run_id,
                run.data.params["scenario"],
                frame["step"],
            ):
                raise ValueError("Replay frame and scene_pushes lineage disagree")
            frame["push"] = audit_row
            frame["source_versions"] = publication["delta_versions"]
        manifest, audit = publications[-1], audit_by_id[publications[-1]["push_id"]]
        runs.append(
            {
                "run_id": run_id,
                "scenario": run.data.params["scenario"],
                "publication": manifest,
                "audit": audit,
                "run_name": run.data.tags.get("mlflow.runName", run_id),
                "run_url": run_url(platform.config, run_id),
                "minutes": int(run.data.params["minutes"]),
                "metric_history": histories,
                "frames": frames,
                "timeline_versions": timeline_versions,
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
        "legend": legend_data(limits, palette),
        "story_sha256": digest(story_layer_bytes()),
    }
    return publish_bundle(platform, bundle)


def publish_bundle(platform: Any, bundle: dict) -> dict[str, str]:
    """Store the same immutable viewer artifact in its Volume and originating runs."""
    from airport_twin.bridge import UsdVolumeTransport
    from airport_twin.scene import canonical, digest
    from airport_twin.scene.cameras import story_layer_bytes
    from airport_twin.tracking import client

    if bundle["story_sha256"] != digest(story_layer_bytes()):
        raise ValueError("Story cameras changed; prepare a new viewer generation")
    c = client(platform.config)
    payload = canonical(bundle)
    bundle_id = digest(payload)
    relative = f"viewer/{bundle_id}/viewer.json"
    UsdVolumeTransport(platform.volume_root()).publish(relative, payload)
    UsdVolumeTransport(platform.volume_root()).publish(
        f"story/{bundle['story_sha256']}/terminal_story.usda", story_layer_bytes()
    )
    for run_id in [run["run_id"] for run in bundle["runs"]]:
        c.log_dict(run_id, json.loads(payload), relative)
        c.log_text(
            run_id, story_layer_bytes().decode("utf-8"), f"viewer/{bundle_id}/terminal_story.usda"
        )
        c.set_tag(run_id, "twin.viewer_artifact", relative)
    return {"bundle_id": bundle_id, "artifact_path": relative}


def refresh_audits(platform: Any, run_ids: list[str]) -> dict[str, str]:
    """Refresh capture receipts from UC without regenerating any historical frame."""
    from airport_twin.tracking import assert_run, client

    if not run_ids:
        raise ValueError("Explicit run IDs are required")
    c = client(platform.config)
    run = assert_run(platform.config, run_ids[0])
    bundle = load_bundle(
        Path(c.download_artifacts(run_ids[0], run.data.tags["twin.viewer_artifact"]))
    )
    if {item["run_id"] for item in bundle["runs"]} != set(run_ids):
        raise ValueError("Capture runs differ from the prepared viewer")
    table = platform.spark.table(platform.config.table("scene_pushes"))
    audits = {r.push_id: r.asDict() for r in table.where(table.run_id.isin(run_ids)).collect()}
    for item in bundle["runs"]:
        for frame in item["frames"]:
            audit = audits[frame["push"]["push_id"]]
            if (audit["run_id"], audit["scenario"], audit["step"]) != (
                item["run_id"],
                item["scenario"],
                frame["step"],
            ):
                raise ValueError("Refreshed audit differs from the prepared minute")
            frame["push"] = audit
        item["audit"] = item["frames"][-1]["push"]
    return publish_bundle(platform, bundle)


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
    import hashlib

    story = Path(c.download_artifacts(run_id, artifact.rsplit("/", 1)[0] + "/terminal_story.usda"))
    if hashlib.sha256(story.read_bytes()).hexdigest() != bundle["story_sha256"]:
        raise ValueError("Story camera layer checksum mismatch")
    (destination / "terminal_story.usda").write_bytes(story.read_bytes())
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
        if not publication.get("story_relative"):
            layer.subLayerPaths.insert(0, "terminal_story.usda")
        layer.Export(str(destination / f"{item['scenario']}.usda"))
    target = destination / "viewer.json"
    target.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    return target


def migrate_push_metadata(platform: Any) -> None:
    """Add lineage to legacy audit rows without deleting or rewriting their USD."""
    from airport_twin.data import merge_rows
    from airport_twin.scene import PUSH_SCHEMA
    from airport_twin.tracking import assert_run

    table = platform.spark.table(platform.config.table("scene_pushes"))
    legacy = table.where(table.scenario.isNull() | table.step.isNull()).collect()
    runs, rows = {}, []
    for row in legacy:
        if row.run_id not in runs:
            runs[row.run_id] = assert_run(platform.config, row.run_id)
        run = runs[row.run_id]
        rows.append(
            (
                row.push_id,
                row.ts,
                row.run_id,
                row.n_prims,
                row.usd_path,
                run.data.params["scenario"],
                int(run.data.params["minutes"]) - 1,
                row.preview_path,
                row.capture_path,
            )
        )
    merge_rows(platform, "scene_pushes", rows, PUSH_SCHEMA, ["push_id"], update=True)
