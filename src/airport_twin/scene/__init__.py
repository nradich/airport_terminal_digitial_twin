"""Content-addressed, audited publication from governed UC state."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from airport_twin.bridge import UsdVolumeTransport
from airport_twin.data import merge_rows
from airport_twin.platform import Platform
from airport_twin.scene.usd import base_bytes, override_bytes, verify_composition
from airport_twin.tracking import assert_run, client
from airport_twin.workflow import thresholds

LOG = logging.getLogger(__name__)
PUSH_SCHEMA = (
    "push_id STRING, ts TIMESTAMP, run_id STRING, n_prims INT, usd_path STRING, "
    "scenario STRING, step INT, preview_path STRING, capture_path STRING, "
    "glb_path STRING, glb_sha256 STRING"
)


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), default=lambda v: v.isoformat()
    ).encode("utf-8")


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def build_scene(platform: Platform) -> Path:
    assets = [r.asDict() for r in platform.spark.table(platform.config.table("assets")).collect()]
    path = UsdVolumeTransport(platform.volume_root()).publish(
        "terminal_base.usda", base_bytes(assets)
    )
    LOG.info("BASE_OK path=%s assets=%d sha256=%s", path, len(assets), digest(path.read_bytes()))
    return path


def capture(platform: Platform, run_id: str, step: int = -1) -> dict:
    run = assert_run(platform.config, run_id)
    if run.data.tags.get("twin.simulation_complete") != "true":
        raise ValueError("Run has no completed simulation")
    last = int(run.data.params["minutes"]) - 1
    step = last if step == -1 else step
    if not 0 <= step <= last:
        raise ValueError("Scene step is outside the run")
    if step != last:
        from airport_twin.timeline import timeline_frames

        frames, versions = timeline_frames(platform, run_id)
        assets = [
            r.asDict() for r in platform.spark.table(platform.config.table("assets")).collect()
        ]
        base = platform.volume_root() / "terminal_base.usda"
        if base.read_bytes() != base_bytes(assets):
            raise ValueError("Base geometry differs from assets")
        return {
            **frames[step],
            "run_id": run_id,
            "scenario": run.data.params["scenario"],
            "assets": assets,
            "thresholds": thresholds(platform),
            "delta_versions": versions,
            "base_sha256": digest((platform.volume_root() / "terminal_base.usda").read_bytes()),
        }
    before = platform.versions()
    assets = [r.asDict() for r in platform.spark.table(platform.config.table("assets")).collect()]
    states = []
    frame = platform.spark.table(platform.config.table("gate_health"))
    states.extend(r.asDict() for r in frame.where(frame.run_id == run_id).collect())
    frame = platform.spark.table(platform.config.table("latest_state"))
    metric_states = frame.where(frame.run_id == run_id).collect()
    if len(metric_states) != 42 or any(r.status is None or r.colour is None for r in metric_states):
        raise ValueError("Scene requires complete, valid metric state")
    states.extend(r.asDict() for r in metric_states if r.asset_type != "gate")
    limits = thresholds(platform)
    if before != platform.versions():
        raise RuntimeError("Source tables changed while capturing; retry the push")
    if len(states) != len(assets) or {s["asset_id"] for s in states} != {
        a["asset_id"] for a in assets
    }:
        raise ValueError("Scene assets and state differ")
    base = platform.volume_root() / "terminal_base.usda"
    if base.read_bytes() != base_bytes(assets):
        raise ValueError("Base geometry differs from assets; explicit migration required")
    return {
        "run_id": run_id,
        "scenario": run.data.params["scenario"],
        "step": step,
        "assets": sorted(assets, key=lambda a: a["asset_id"]),
        "states": sorted(states, key=lambda s: s["asset_id"]),
        "metric_states": sorted(
            (r.asDict() for r in metric_states), key=lambda s: (s["asset_id"], s["metric"])
        ),
        "thresholds": limits,
        "delta_versions": before,
        "base_sha256": digest(base.read_bytes()),
    }


def write_publication(platform: Platform, snapshot: dict) -> dict:
    """Publish verified immutable files/artifacts; caller commits the audit in a batch."""
    from importlib.metadata import version

    from airport_twin.rules import rule_snapshot
    from airport_twin.scene.cameras import story_layer_bytes
    from airport_twin.scene.glb import glb_bytes
    from airport_twin.tracking import git_sha, log_scene

    run_id = snapshot["run_id"]
    story = story_layer_bytes()
    glb = glb_bytes(snapshot["assets"])
    snapshot = {
        **snapshot,
        "manifest_version": 2,
        "rules": rule_snapshot(),
        "publisher": {
            "git_sha": git_sha(),
            "package_version": version("airport-twin"),
            "geometry_generator": "airport-twin/glb-v1",
            "source_sha256": digest(
                canonical(
                    {
                        str(path.relative_to(Path(__file__).resolve().parents[1])): digest(
                            path.read_bytes()
                        )
                        for path in Path(__file__).resolve().parents[1].rglob("*.py")
                    }
                )
            ),
        },
        "story_sha256": digest(story),
        "glb_sha256": digest(glb),
        "glb_format": "airport-twin/glb-v1",
    }
    identity = {
        k: snapshot[k]
        for k in (
            "run_id",
            "scenario",
            "step",
            "assets",
            "states",
            "metric_states",
            "thresholds",
            "base_sha256",
            "story_sha256",
            "glb_sha256",
            "glb_format",
            "delta_versions",
            "rules",
            "publisher",
            "manifest_version",
        )
    }
    identity["assets"] = sorted(snapshot["assets"], key=lambda r: r["asset_id"])
    identity["states"] = [
        {key: row[key] for key in ("asset_id", "prim_path", "status", "colour")}
        for row in sorted(snapshot["states"], key=lambda r: r["asset_id"])
    ]
    identity["metric_states"] = sorted(
        snapshot["metric_states"], key=lambda r: (r["asset_id"], r["metric"])
    )
    push_id = digest(canonical(identity))
    relative = f"runs/{run_id}/{push_id}/terminal_state_{run_id}.usda"
    transport = UsdVolumeTransport(platform.volume_root())
    glb_relative = f"geometry/{snapshot['glb_sha256']}/terminal.glb"
    transport.publish(glb_relative, glb)
    story_relative = f"story/{snapshot['story_sha256']}/terminal_story.usda"
    transport.publish(story_relative, story)
    payload = override_bytes(
        snapshot["states"],
        {
            "run_id": run_id,
            "push_id": push_id,
            "scenario": snapshot["scenario"],
            "step": str(snapshot["step"]),
            "base_sha256": snapshot["base_sha256"],
        },
        story_relative,
    )
    path = transport.publish(relative, payload)
    verify_composition(path, snapshot["states"])
    manifest = {
        **snapshot,
        "push_id": push_id,
        "state_sha256": digest(payload),
        "usd_path": str(path),
        "n_prims": len(snapshot["states"]),
        "story_relative": story_relative,
        "glb_path": glb_relative,
    }
    import tempfile

    from airport_twin.scene.heatmap import render_heatmap

    with tempfile.TemporaryDirectory() as folder:
        png = Path(folder) / "heatmap.png"
        render_heatmap(manifest, snapshot["scenario"], png)
        preview = png.read_bytes()
    transport.publish(str((path.parent / "heatmap.png").relative_to(transport.root)), preview)
    manifest["preview_sha256"] = digest(preview)
    manifest_path = path.parent / "manifest.json"
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text())
        if old["state_sha256"] != manifest["state_sha256"]:
            raise ValueError("Existing publication manifest differs")
        manifest = old
    else:
        transport.publish(str(manifest_path.relative_to(transport.root)), canonical(manifest))
    log_scene(platform.config, manifest)
    return manifest


def audit_rows(manifests: list[dict]) -> list[tuple]:
    return [
        (
            m["push_id"],
            datetime.now(UTC).replace(tzinfo=None),
            m["run_id"],
            m["n_prims"],
            m["usd_path"],
            m["scenario"],
            m["step"],
            str(Path(m["usd_path"]).parent / "heatmap.png"),
            None,
            m["glb_path"],
            m["glb_sha256"],
        )
        for m in manifests
    ]


def publish_snapshots(platform: Platform, snapshots: list[dict]) -> list[dict]:
    """Resume one originating run, publish files first, then commit one UC audit batch."""
    import mlflow

    run_ids = {snapshot["run_id"] for snapshot in snapshots}
    if len(run_ids) != 1:
        raise ValueError("Publication batch must belong to one explicit run")
    run_id = next(iter(run_ids))
    active = mlflow.active_run()
    if active is not None:
        raise RuntimeError("Finish the current MLflow context before pushing an explicit run")
    previous = mlflow.get_tracking_uri()
    mlflow.set_tracking_uri(platform.config.tracking_uri)
    try:
        with mlflow.start_run(run_id=run_id):
            manifests = []
            for snapshot in snapshots:
                manifests.append(write_publication(platform, snapshot))
                if len(manifests) % 10 == 0:
                    LOG.info("PUBLISH_PROGRESS run_id=%s frames=%d", run_id, len(manifests))
            merge_rows(platform, "scene_pushes", audit_rows(manifests), PUSH_SCHEMA, ["push_id"])
            manifest = manifests[-1]
            c = client(platform.config)
            c.set_tag(run_id, "twin.last_push_id", manifest["push_id"])
            c.set_tag(run_id, "twin.last_usd_path", manifest["usd_path"])
    finally:
        mlflow.set_tracking_uri(previous)
    return manifests


def push_scene(platform: Platform, run_id: str, step: int = -1) -> dict:
    snapshot = capture(platform, run_id, step)
    manifest = publish_snapshots(platform, [snapshot])[0]
    LOG.info(
        "PUSH_OK run_id=%s step=%d push_id=%s path=%s",
        run_id,
        manifest["step"],
        manifest["push_id"],
        manifest["usd_path"],
    )
    return manifest


def publish_replay(
    platform: Platform,
    run_id: str,
    frames: list[dict],
    versions: dict,
    assets: list[dict],
    limits: list[tuple],
    scenario: str,
) -> list[dict]:
    base = platform.volume_root() / "terminal_base.usda"
    if base.read_bytes() != base_bytes(assets):
        raise ValueError("Base geometry differs from UC assets")
    snapshots = [
        {
            **frame,
            "run_id": run_id,
            "scenario": scenario,
            "assets": assets,
            "thresholds": limits,
            "delta_versions": versions,
            "base_sha256": digest(base.read_bytes()),
        }
        for frame in frames
    ]
    return publish_snapshots(platform, snapshots)


def validate_publications(platform: Platform, run_id: str) -> None:
    table = platform.spark.table(platform.config.table("scene_pushes"))
    pushes = table.where(table.run_id == run_id).collect()
    if not pushes or len({p.push_id for p in pushes}) != len(pushes):
        raise AssertionError("Missing or duplicate scene publication")
    root = platform.volume_root().resolve()
    for push in pushes:
        path = Path(push.usd_path).resolve()
        if not path.is_relative_to(root):
            raise AssertionError("Publication path is outside the scenes Volume")
        manifest = json.loads((path.parent / "manifest.json").read_text())
        if digest(path.read_bytes()) != manifest["state_sha256"]:
            raise AssertionError("State checksum mismatch")
        if digest((root / "terminal_base.usda").read_bytes()) != manifest["base_sha256"]:
            raise AssertionError("Base geometry changed")
        if push.n_prims != 10 or manifest["run_id"] != run_id:
            raise AssertionError("Publication lineage mismatch")
        if "step" in manifest and (
            push.step != manifest["step"] or push.scenario != manifest["scenario"]
        ):
            raise AssertionError("Publication run/step audit differs")
        verify_composition(path, manifest["states"])
    from airport_twin.tracking import validate_scene_artifacts

    validate_scene_artifacts(platform.config, run_id, [p.push_id for p in pushes])
