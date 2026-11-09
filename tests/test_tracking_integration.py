"""Real MLflow server histories and artifact round-trip (no SQLite/file backend)."""

import os
import tempfile
from pathlib import Path

import pytest

from airport_twin.config import Config, SimulationConfig
from airport_twin.data import THRESHOLDS
from airport_twin.sim import simulate
from airport_twin.tracking import client, log_metrics, start_run

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("TWIN_RUN_INTEGRATION") != "1", reason="requires local MLflow server"
    ),
]


def test_real_tracking_histories_and_artifact():
    config = Config.from_env()
    simulation = SimulationConfig(minutes=3)
    run_id = start_run(config, simulation, THRESHOLDS)
    c = client(config)
    try:
        log_metrics(config, run_id, simulation, simulate(simulation, run_id).metrics)
        assert [m.step for m in c.get_metric_history(run_id, "avg_co2")] == [0, 1, 2]
        c.log_dict(run_id, {"run_id": run_id}, "contract.json")
        with tempfile.TemporaryDirectory() as folder:
            path = c.download_artifacts(run_id, "contract.json", folder)
            assert run_id in Path(path).read_text()
        assert c.get_run(run_id).data.tags["platform"] == "local"
    finally:
        c.set_terminated(run_id)
        c.delete_run(run_id)
