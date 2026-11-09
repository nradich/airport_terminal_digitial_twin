"""Notebook operations shared by local and Databricks execution."""

from __future__ import annotations

import logging
import time

from airport_twin.config import SimulationConfig
from airport_twin.data import FLIGHT_SCHEMA, READING_SCHEMA, merge_rows
from airport_twin.platform import Platform
from airport_twin.sim import numeric_status, simulate, validate_readings
from airport_twin.tracking import assert_run, client, log_metrics, start_run

LOG = logging.getLogger(__name__)


def thresholds(platform: Platform) -> list[tuple]:
    rows = [tuple(r) for r in platform.spark.table(platform.config.table("thresholds")).collect()]
    if len({(r[0], r[1]) for r in rows}) != len(rows):
        raise ValueError("Duplicate thresholds")
    for _, _, warn, crit in rows:
        numeric_status(0.0, warn, crit)
    return sorted(rows)


def run_simulation(platform: Platform, config: SimulationConfig) -> str:
    started = time.perf_counter()
    limits = thresholds(platform)
    run_id = start_run(platform.config, config, limits)
    c = client(platform.config)
    try:
        result = simulate(config, run_id, limits)
        merge_rows(platform, "flights", result.flights, FLIGHT_SCHEMA, ["run_id", "flight_id"])
        merge_rows(
            platform,
            "sensor_readings",
            result.readings,
            READING_SCHEMA,
            ["run_id", "asset_id", "ts", "metric"],
        )
        log_metrics(platform.config, run_id, config, result.metrics)
        c.set_tag(run_id, "twin.simulation_complete", "true")
        c.log_metric(run_id, "simulation_elapsed_s", time.perf_counter() - started)
    except Exception:
        c.set_terminated(run_id, "FAILED")
        raise
    c.set_terminated(run_id)
    LOG.info(
        "SIMULATE_OK scenario=%s run_id=%s rows=%d elapsed_s=%.3f",
        config.scenario,
        run_id,
        len(result.readings),
        time.perf_counter() - started,
    )
    return run_id


def validate(platform: Platform, run_id: str, phase: str = "all") -> dict:
    run = assert_run(platform.config, run_id)
    # Read using DataFrame filters, never interpolate externally supplied run IDs into SQL.
    readings = [
        tuple(r)
        for r in platform.spark.table(platform.config.table("sensor_readings"))
        .where(f"run_id = '{run.info.run_id}'")
        .collect()
    ]
    validate_readings(readings)
    expected = 42 * int(run.data.params["minutes"])
    if len(readings) != expected:
        raise AssertionError(f"Expected {expected} readings, got {len(readings)}")
    assets = {r.asset_id for r in platform.spark.table(platform.config.table("assets")).collect()}
    if len(assets) != 10 or any(r[0] not in assets for r in readings):
        raise AssertionError("Wrong asset count or orphan readings")
    flights = (
        platform.spark.table(platform.config.table("flights"))
        .where(f"run_id = '{run.info.run_id}'")
        .collect()
    )
    if len(flights) != 8 or any(f.gate_id not in assets for f in flights):
        raise AssertionError("Wrong flight count or orphan gates")
    states = (
        platform.spark.table(platform.config.table("latest_state"))
        .where(f"run_id = '{run.info.run_id}'")
        .collect()
    )
    if len(states) != 42 or any(r.status not in {"ok", "warn", "crit"} for r in states):
        raise AssertionError("Incomplete or invalid latest state")
    health = (
        platform.spark.table(platform.config.table("gate_health"))
        .where(f"run_id = '{run.info.run_id}'")
        .collect()
    )
    if len(health) != 8 or any(r.invalid_metrics for r in health):
        raise AssertionError("Invalid gate health")
    if phase == "all":
        from airport_twin.scene import validate_publications

        validate_publications(platform, run_id)
    report = {
        "run_id": run_id,
        "readings": len(readings),
        "flights": len(flights),
        "latest_state": len(states),
        "gates": len(health),
        "phase": phase,
    }
    client(platform.config).log_dict(run_id, report, "validation.json")
    LOG.info("VALIDATE_OK %s", report)
    return report
