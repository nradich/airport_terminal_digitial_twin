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


def capture(platform: Platform, run_id: str) -> dict:
    run = assert_run(platform.config, run_id)
    if run.data.tags.get("twin.simulation_complete") != "true":
        raise ValueError("Run has no completed simulation")
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
        "assets": sorted(assets, key=lambda a: a["asset_id"]),
        "states": sorted(states, key=lambda s: s["asset_id"]),
        "metric_states": sorted(
            (r.asDict() for r in metric_states), key=lambda s: (s["asset_id"], s["metric"])
        ),
        "thresholds": limits,
        "delta_versions": before,
        "base_sha256": digest(base.read_bytes()),
    }


def push_scene(platform: Platform, run_id: str) -> dict:
    import mlflow

    snapshot = capture(platform, run_id)
    identity = {
        k: snapshot[k] for k in ("run_id", "states", "metric_states", "thresholds", "base_sha256")
    }
    push_id = digest(canonical(identity))
    relative = f"runs/{run_id}/{push_id}/terminal_state_{run_id}.usda"
    transport = UsdVolumeTransport(platform.volume_root())
    active = mlflow.active_run()
    if active is not None:
        raise RuntimeError("Finish the current MLflow context before pushing an explicit run")
    previous = mlflow.get_tracking_uri()
    mlflow.set_tracking_uri(platform.config.tracking_uri)
    try:
        with mlflow.start_run(run_id=run_id):
            payload = override_bytes(
                snapshot["states"],
                {"run_id": run_id, "push_id": push_id, "base_sha256": snapshot["base_sha256"]},
            )
            path = transport.publish(relative, payload)
            verify_composition(path, snapshot["states"])
            manifest = {
                **snapshot,
                "push_id": push_id,
                "state_sha256": digest(payload),
                "usd_path": str(path),
                "n_prims": len(snapshot["states"]),
            }
            manifest_path = path.parent / "manifest.json"
            if manifest_path.exists():
                old = json.loads(manifest_path.read_text())
                if old["state_sha256"] != manifest["state_sha256"]:
                    raise ValueError("Existing publication manifest differs")
                manifest = old  # Preserve original Delta versions on an identical content retry.
            else:
                transport.publish(
                    str(manifest_path.relative_to(transport.root)), canonical(manifest)
                )
            from airport_twin.tracking import log_scene

            log_scene(platform.config, manifest)
            merge_rows(
                platform,
                "scene_pushes",
                [
                    (
                        push_id,
                        datetime.now(UTC).replace(tzinfo=None),
                        run_id,
                        len(snapshot["states"]),
                        str(path),
                    )
                ],
                "push_id STRING, ts TIMESTAMP, run_id STRING, n_prims INT, usd_path STRING",
                ["push_id"],
            )
            c = client(platform.config)
            c.set_tag(run_id, "twin.last_push_id", push_id)
            c.set_tag(run_id, "twin.last_usd_path", str(path))
    finally:
        mlflow.set_tracking_uri(previous)
    LOG.info(
        "PUSH_OK run_id=%s push_id=%s n_prims=%d path=%s",
        run_id,
        push_id,
        len(snapshot["states"]),
        path,
    )
    return manifest


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
        verify_composition(path, manifest["states"])
    from airport_twin.tracking import validate_scene_artifacts

    validate_scene_artifacts(platform.config, run_id, [p.push_id for p in pushes])
