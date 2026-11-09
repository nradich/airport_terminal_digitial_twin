"""MLflow run identity, batched histories, and retrievable provenance artifacts."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC
from pathlib import Path
from typing import Any

from mlflow import MlflowClient
from mlflow.entities import Metric, Param

from airport_twin.config import Config, SimulationConfig


def git_sha() -> str:
    if value := os.getenv("TWIN_GIT_SHA"):
        return value
    # Git folders on Databricks can provide TWIN_GIT_SHA; the local image need not ship Git.
    git_dir = Path.cwd() / ".git"
    if git_dir.is_dir():
        head = (git_dir / "HEAD").read_text().strip()
        if head.startswith("ref: "):
            ref = git_dir / head.removeprefix("ref: ")
            if ref.exists():
                return ref.read_text().strip()
        elif len(head) == 40:
            return head
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
        )
    except FileNotFoundError:
        return "unknown"
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def client(config: Config) -> MlflowClient:
    return MlflowClient(tracking_uri=config.tracking_uri, registry_uri=config.registry_uri)


def start_run(config: Config, sim: SimulationConfig, thresholds: list[tuple]) -> str:
    c = client(config)
    experiment = c.get_experiment_by_name(config.experiment)
    experiment_id = (
        experiment.experiment_id if experiment else c.create_experiment(config.experiment)
    )
    run = c.create_run(
        experiment_id,
        tags={
            "scenario": sim.scenario,
            "git_sha": git_sha(),
            "platform": config.platform,
            "mlflow.runName": f"{sim.scenario}-seed{sim.seed}",
            "twin.namespace": config.namespace,
        },
    )
    params = {
        "scenario": sim.scenario,
        "seed": sim.seed,
        "n_gates": sim.n_gates,
        "minutes": sim.minutes,
        "start_utc": sim.start.isoformat(),
        "thresholds_snapshot": json.dumps(sorted(thresholds), separators=(",", ":")),
    }
    c.log_batch(run.info.run_id, params=[Param(k, str(v)) for k, v in params.items()])
    c.log_dict(run.info.run_id, {"rows": thresholds}, "thresholds_initial.json")
    return run.info.run_id


def log_metrics(
    config: Config, run_id: str, sim: SimulationConfig, histories: list[dict[str, float]]
) -> None:
    start = int(sim.start.replace(tzinfo=UTC).timestamp() * 1000)
    values = [
        Metric(key, float(value), start + minute * 60000, minute)
        for minute, row in enumerate(histories)
        for key, value in row.items()
    ]
    c = client(config)
    for offset in range(0, len(values), 500):
        c.log_batch(run_id, metrics=values[offset : offset + 500])


def assert_run(config: Config, run_id: str) -> Any:
    if not run_id:
        raise ValueError("An explicit run_id is required; latest run is never guessed")
    run = client(config).get_run(run_id)
    if run.data.tags.get("twin.namespace") != config.namespace:
        raise ValueError("Run belongs to another namespace")
    return run


def run_url(config: Config, run_id: str) -> str:
    run = assert_run(config, run_id)
    base = os.getenv("TWIN_MLFLOW_PUBLIC_URI", config.tracking_uri).rstrip("/")
    return f"{base}/#/experiments/{run.info.experiment_id}/runs/{run_id}"


def log_scene(config: Config, manifest: dict) -> None:
    """Log a composable scene bundle, heatmap, and the exact push provenance."""
    import tempfile

    from airport_twin.scene import canonical
    from airport_twin.scene.heatmap import render_heatmap

    c = client(config)
    run_id, push_id = manifest["run_id"], manifest["push_id"]
    run = assert_run(config, run_id)
    prefix = f"scene/runs/{run_id}/{push_id}"
    state = Path(manifest["usd_path"])
    base = state.parents[3] / "terminal_base.usda"
    c.log_artifact(run_id, str(base), "scene")
    c.log_artifact(run_id, str(state), prefix)
    c.log_dict(run_id, json.loads(canonical(manifest)), prefix + "/manifest.json")
    c.log_dict(run_id, {"rows": manifest["thresholds"]}, prefix + "/thresholds.json")
    with tempfile.TemporaryDirectory() as folder:
        png = Path(folder) / "heatmap.png"
        render_heatmap(manifest, run.data.params["scenario"], png)
        c.log_artifact(run_id, str(png), prefix)
    c.log_metric(run_id, "scene_n_prims", manifest["n_prims"])


def validate_scene_artifacts(config: Config, run_id: str, push_ids: list[str]) -> None:
    import tempfile

    from PIL import Image

    from airport_twin.scene import digest
    from airport_twin.scene.usd import verify_composition

    c = client(config)
    for metric in ("peak_pax_A4", "gates_in_crit", "avg_co2", "security_queue_p95"):
        history = c.get_metric_history(run_id, metric)
        minutes = int(assert_run(config, run_id).data.params["minutes"])
        if {m.step for m in history} != set(range(minutes)):
            raise AssertionError(f"Missing metric history for {metric}")
    with tempfile.TemporaryDirectory() as folder:
        root = Path(c.download_artifacts(run_id, "scene", folder))
        for push_id in push_ids:
            directory = root / "runs" / run_id / push_id
            manifest = json.loads((directory / "manifest.json").read_text())
            state = directory / f"terminal_state_{run_id}.usda"
            if digest(state.read_bytes()) != manifest["state_sha256"]:
                raise AssertionError("Retrieved USD differs from the publication")
            if digest((root / "terminal_base.usda").read_bytes()) != manifest["base_sha256"]:
                raise AssertionError("Retrieved base differs from the publication")
            if manifest["run_id"] != run_id or manifest["push_id"] != push_id:
                raise AssertionError("Retrieved manifest has wrong lineage")
            if (
                json.loads((directory / "thresholds.json").read_text())["rows"]
                != manifest["thresholds"]
            ):
                raise AssertionError("Retrieved thresholds differ")
            verify_composition(state, manifest["states"])
            with Image.open(directory / "heatmap.png") as image:
                image.verify()
