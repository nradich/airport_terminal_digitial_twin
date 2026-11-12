"""Publish a frozen passenger experiment to Delta and the source twin's MLflow experiment."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from airport_twin.data import merge_rows
from airport_twin.journey import STAGES, Policy, simulate
from airport_twin.tracking import assert_run, client, git_sha


def utc(value):
    parsed = datetime.fromisoformat(str(value))
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def publish_journey(platform, push_id, flight_id, seed=42, trials=10000, policy=None):
    from mlflow.entities import Dataset, DatasetInput, InputTag

    policy = policy or Policy()
    if not re.fullmatch(r"[0-9a-f]{64}", push_id):
        raise ValueError("Supply the full publication push ID")
    config, spark = platform.config, platform.spark
    pushes = spark.table(config.table("scene_pushes"))
    [audit] = pushes.where(pushes.push_id == push_id).collect()
    raw = (Path(audit.usd_path).parent / "manifest.json").read_bytes()
    manifest = json.loads(raw)
    if any(manifest[k] != audit[k] for k in ("push_id", "run_id", "step", "usd_path")):
        raise ValueError("Source manifest differs from publication audit")
    parent = assert_run(config, audit.run_id)
    [queue] = [
        r
        for r in manifest["metric_states"]
        if r["asset_id"] == "SECURITY" and r["metric"] == "queue_len"
    ]
    entry = utc(parent.data.params["start_utc"]) + timedelta(minutes=audit.step)
    if utc(queue["ts"]) != entry or queue["run_id"] != audit.run_id:
        raise ValueError("Security reading differs from publication minute or run")
    count = int(queue["value_num"])
    if count != queue["value_num"]:
        raise ValueError("Expected a whole passenger count")
    versions = manifest["delta_versions"]
    flights = spark.read.option("versionAsOf", int(versions["flights"])).table(
        config.table("flights")
    )
    [flight] = (
        flights.where((flights.run_id == audit.run_id) & (flights.flight_id == flight_id))
        .selectExpr("gate_id", "unix_timestamp(sched_dep) AS departure_epoch")
        .collect()
    )
    departure = datetime.fromtimestamp(flight.departure_epoch, UTC)
    close = departure - timedelta(minutes=policy.boarding_buffer_minutes)
    budget = int((close - entry).total_seconds())
    inputs = dict(
        push_id=push_id,
        source_run=audit.run_id,
        step=audit.step,
        flight=flight_id,
        gate=flight.gate_id,
        entry=entry.isoformat(),
        departure=departure.isoformat(),
        close=close.isoformat(),
        budget=budget,
        queue=count,
        policy=asdict(policy),
        manifest_sha256=hashlib.sha256(raw).hexdigest(),
        versions=versions,
        seed=seed,
        trials=trials,
        model="journey-v1",
        git_sha=git_sha(),
    )
    serialized = json.dumps(inputs, sort_keys=True)
    key = hashlib.sha256(serialized.encode()).hexdigest()
    tracking = client(config)
    run = tracking.create_run(
        parent.info.experiment_id,
        tags={
            "mlflow.parentRunId": audit.run_id,
            "mlflow.runName": f"Journey {flight_id} · minute {audit.step}",
            "twin.namespace": config.namespace,
            "journey.push_id": push_id,
            "journey.key": key,
        },
    ).info.run_id
    try:
        rows, profiles = simulate(count, budget, seed, trials, policy)
        schemas = {
            "journey_trials": "run_id STRING, trial INT, checkpoint STRING, lanes INT, "
            + ", ".join(f"{s} INT" for s in STAGES),
            "journey_experiments": "run_id STRING, push_id STRING, source_run STRING, "
            "flight_id STRING, input_json STRING, summary_json STRING",
        }
        for table, schema in schemas.items():
            spark.sql(
                f"CREATE TABLE IF NOT EXISTS {config.table(table)} ({schema}) USING DELTA"
                + platform.table_location(table)
            )
        merge_rows(
            platform,
            "journey_trials",
            [(run, *r) for r in rows],
            schemas["journey_trials"],
            ["run_id", "trial", "checkpoint", "lanes"],
        )
        summary = dict(inputs=inputs, profiles=profiles, run_id=run)
        merge_rows(
            platform,
            "journey_experiments",
            [(run, push_id, audit.run_id, flight_id, serialized, json.dumps(profiles))],
            schemas["journey_experiments"],
            ["run_id"],
        )
        tracking.log_dict(run, summary, "journey.json")
        datasets = []
        for table, version in versions.items():
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
            datasets.append(DatasetInput(dataset, [InputTag("mlflow.data.context", "frozen_twin")]))
        tracking.log_inputs(run, datasets)
        for name in ("seed", "trials", "flight", "queue", "model", "git_sha"):
            tracking.log_param(run, name, inputs[name])
        for p in profiles:
            prefix = (
                f"{p['kind']}.bag{int(p['bag'])}.coffee{int(p['coffee'])}"
                f".restroom{int(p['restroom'])}"
            )
            tracking.log_metric(run, prefix + ".gain_pp", 100 * p["gain"])
            for arm, result in zip(("baseline", "extra"), p["arms"], strict=True):
                tracking.log_metric(run, f"{prefix}.{arm}.success", result["probability"])
                tracking.log_metric(run, f"{prefix}.{arm}.p90_seconds", result["p90"])
        tracking.set_terminated(run)
    except Exception:
        tracking.set_terminated(run, status="FAILED")
        raise
    return run
