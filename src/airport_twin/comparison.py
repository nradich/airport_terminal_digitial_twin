"""Explicit, governed filming pairs. No implicit latest-run pairing."""

from __future__ import annotations

import hashlib
import json
import os
import re
from urllib.parse import quote, urlsplit

from airport_twin.config import Config
from airport_twin.readers import ReadError
from airport_twin.tracking import assert_run, client, run_url


def comparison_url(config: Config, runs: list[str], experiment_id: str) -> str | None:
    if config.platform == "databricks":
        # Workspace-native routes must be observed/verified, not guessed.
        template = os.getenv("TWIN_MLFLOW_COMPARE_URL_TEMPLATE", "")
        if not template:
            return None
        return template.format(
            baseline_run_id=quote(runs[0], safe=""),
            delay_run_id=quote(runs[1], safe=""),
            experiment_id=quote(experiment_id, safe=""),
        )
    base = run_url(config, runs[0]).split("/#/")[0]
    return (
        base
        + "/#/compare-runs?runs="
        + quote(json.dumps(runs, separators=(",", ":")))
        + "&experiments="
        + quote(json.dumps([experiment_id]))
    )


def pair_metadata(config: Config, baseline_id: str, delay_id: str) -> dict:
    runs = [assert_run(config, run_id) for run_id in (baseline_id, delay_id)]
    for key in ("seed", "start_utc", "minutes", "n_gates", "thresholds_snapshot"):
        if runs[0].data.params[key] != runs[1].data.params[key]:
            raise ValueError(f"Comparison mismatch: {key}")
    if [r.data.params["scenario"] for r in runs] != ["baseline", "delay_A4"]:
        raise ValueError("An explicit baseline then delay_A4 pair is required")
    if runs[0].info.experiment_id != runs[1].info.experiment_id:
        raise ValueError("Comparison experiment differs")
    body = {
        "format_version": 1,
        "namespace": config.namespace,
        "baseline_run_id": baseline_id,
        "delay_run_id": delay_id,
        "experiment_id": runs[0].info.experiment_id,
        "assumptions": runs[0].data.params,
    }
    body["comparison_id"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    return body


def publish_pair(platform, baseline_id: str, delay_id: str) -> dict:
    from airport_twin.bridge import UsdVolumeTransport

    metadata = pair_metadata(platform.config, baseline_id, delay_id)
    path = f"comparisons/{metadata['comparison_id']}/comparison.json"
    stored = UsdVolumeTransport(platform.volume_root()).publish(
        path, json.dumps(metadata, sort_keys=True).encode()
    )
    tracking = client(platform.config)
    for run_id in (baseline_id, delay_id):
        tracking.log_artifact(run_id, str(stored), f"comparisons/{metadata['comparison_id']}")
        tracking.set_tag(run_id, "twin.comparison_path", path)
    return metadata


def run_comparison(data, run_id: str) -> dict:
    run = assert_run(data.config, run_id)
    path = run.data.tags.get("twin.comparison_path")
    if not path:
        return {"url": None, "reason": "No explicit comparison pair published"}
    if not re.fullmatch(r"comparisons/[a-f0-9]{64}/comparison.json", path):
        raise ReadError("INVALID_COMPARISON", status=409)
    body = json.loads(data.volume.read(path))
    verified = pair_metadata(data.config, body["baseline_run_id"], body["delay_run_id"])
    if body != verified or run_id not in (body["baseline_run_id"], body["delay_run_id"]):
        raise ReadError("COMPARISON_MISMATCH", status=409)
    url = comparison_url(
        data.config, [body["baseline_run_id"], body["delay_run_id"]], body["experiment_id"]
    )
    if url and urlsplit(url).scheme not in {"http", "https"}:
        raise ReadError("INVALID_COMPARISON_URL", status=409)
    return {**body, "url": url, "reason": None if url else "Databricks comparison route UNVERIFIED"}
