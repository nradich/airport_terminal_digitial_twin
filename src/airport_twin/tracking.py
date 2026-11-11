"""MLflow run identity, batched histories, and retrievable provenance artifacts."""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import UTC
from pathlib import Path
from typing import Any

from mlflow import MlflowClient
from mlflow.entities import Metric, Param

from airport_twin.config import Config, SimulationConfig

_LOGGED_INPUTS: set[tuple] = set()


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
    sha = git_sha()
    if not re.fullmatch(r"[a-fA-F0-9]{40}", sha):
        raise ValueError("Set TWIN_GIT_SHA to the exact commit when Git metadata is unavailable")
    c = client(config)
    experiment = c.get_experiment_by_name(config.experiment)
    experiment_id = (
        experiment.experiment_id if experiment else c.create_experiment(config.experiment)
    )
    run = c.create_run(
        experiment_id,
        tags={
            "scenario": sim.scenario,
            "git_sha": sha,
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
    base = os.getenv("TWIN_MLFLOW_PUBLIC_URI")
    if not base and config.platform == "databricks":
        from databricks.sdk import WorkspaceClient

        base = WorkspaceClient().config.host
    if not base:
        from urllib.parse import urlsplit, urlunsplit

        parsed = urlsplit(config.tracking_uri)
        host = "localhost:5000" if parsed.netloc == "mlflow:5000" else parsed.netloc
        base = urlunsplit(parsed._replace(netloc=host))
    base = base.rstrip("/")
    route = "/ml/experiments" if config.platform == "databricks" else "/#/experiments"
    return f"{base}{route}/{run.info.experiment_id}/runs/{run_id}"


def log_scene(config: Config, manifest: dict) -> None:
    """Log a composable scene bundle, heatmap, and the exact push provenance."""
    from airport_twin.scene import canonical

    c = client(config)
    run_id, push_id = manifest["run_id"], manifest["push_id"]
    assert_run(config, run_id)
    import hashlib

    from mlflow.entities import Dataset, DatasetInput, InputTag

    for table, version in manifest["delta_versions"].items():
        key = (config.tracking_uri, run_id, table, version)
        if key not in _LOGGED_INPUTS:
            source = json.dumps(
                {"delta_table_name": config.table(table), "delta_table_version": version},
                sort_keys=True,
            )
            dataset = Dataset(
                config.table(table),
                hashlib.sha256(source.encode()).hexdigest()[:32],
                "delta_table",
                source,
            )
            c.log_inputs(
                run_id, [DatasetInput(dataset, [InputTag("mlflow.data.context", "scene_source")])]
            )
            _LOGGED_INPUTS.add(key)
    prefix = f"scene/runs/{run_id}/{push_id}"
    state = Path(manifest["usd_path"])
    base = state.parents[3] / "terminal_base.usda"
    c.log_artifact(run_id, str(base), "scene")
    c.log_artifact(run_id, str(state), prefix)
    if manifest.get("glb_path"):
        c.log_artifact(run_id, str(base.parent / manifest["glb_path"]), prefix)
    if manifest.get("story_relative"):
        story = base.parent / manifest["story_relative"]
        c.log_artifact(run_id, str(story), "scene/" + str(Path(manifest["story_relative"]).parent))
    c.log_dict(run_id, json.loads(canonical(manifest)), prefix + "/manifest.json")
    c.log_dict(run_id, {"rows": manifest["thresholds"]}, prefix + "/thresholds.json")
    c.log_artifact(run_id, str(state.parent / "heatmap.png"), prefix)
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
                manifest.get("glb_sha256")
                and digest((directory / "terminal.glb").read_bytes()) != manifest["glb_sha256"]
            ):
                raise AssertionError("Retrieved GLB checksum differs")
            if manifest.get("story_relative"):
                if (
                    digest((root / manifest["story_relative"]).read_bytes())
                    != manifest["story_sha256"]
                ):
                    raise AssertionError("Retrieved story cameras differ")
            if (
                json.loads((directory / "thresholds.json").read_text())["rows"]
                != manifest["thresholds"]
            ):
                raise AssertionError("Retrieved thresholds differ")
            verify_composition(state, manifest["states"])
            with Image.open(directory / "heatmap.png") as image:
                image.verify()
            if (
                manifest.get("preview_sha256")
                and digest((directory / "heatmap.png").read_bytes()) != manifest["preview_sha256"]
            ):
                raise AssertionError("Retrieved preview differs from the publication")
            if (directory / "viewport.png").exists():
                receipt = json.loads((directory / "viewport_receipt.json").read_text())
                if any(
                    receipt[key] != manifest[key]
                    for key in ("run_id", "push_id", "scenario", "step", "usd_path")
                ):
                    raise AssertionError("Retrieved viewport has wrong publication lineage")
                if digest((directory / "viewport.png").read_bytes()) != receipt["sha256"]:
                    raise AssertionError("Retrieved viewport checksum differs")
                with Image.open(directory / "viewport.png") as image:
                    if image.size != (receipt["width"], receipt["height"]):
                        raise AssertionError("Retrieved viewport dimensions differ")
                    image.verify()
