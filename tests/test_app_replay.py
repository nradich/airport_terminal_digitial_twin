from datetime import datetime
from types import SimpleNamespace

import pytest

from airport_twin import app_data, app_replay, comparison
from airport_twin.config import Config, SimulationConfig
from airport_twin.data import THRESHOLDS
from airport_twin.queries import build_query
from airport_twin.readers import ReadError
from airport_twin.sim import simulate


def test_replay_asset_identity_ignores_spark_collect_order(monkeypatch):
    monkeypatch.setattr(
        app_replay,
        "assert_run",
        lambda *_: SimpleNamespace(
            data=SimpleNamespace(params={"minutes": "2", "start_utc": "2026-11-09T22:00:00"})
        ),
    )
    assets = [{"asset_id": "GATE_A1"}, {"asset_id": "GATE_A2"}]
    publications = {
        str(step): {
            "manifest": {
                "step": step,
                "delta_versions": {},
                "thresholds": [],
                "base_sha256": "base",
                "glb_sha256": "glb",
                "assets": assets if step == 0 else assets[::-1],
            }
        }
        for step in range(2)
    }
    data = SimpleNamespace(
        config=Config(),
        pushes=lambda: [{"run_id": "run", "push_id": str(i)} for i in range(2)],
        publication=publications.__getitem__,
    )
    assert len(app_replay.replay_sets(data, "run")) == 1


@pytest.mark.parametrize("mixed_versions", [False, True])
def test_run_selector_requires_one_complete_source_identity(monkeypatch, mixed_versions):
    run = SimpleNamespace(data=SimpleNamespace(
        params={"minutes": "2", "start_utc": "2026-11-09T22:00:00"}, tags={}
    ))
    monkeypatch.setattr(app_replay, "assert_run", lambda *_: run)
    monkeypatch.setattr(app_data, "assert_run", lambda *_: run)
    monkeypatch.setattr(app_data, "run_url", lambda *_: "http://mlflow.invalid/run")
    monkeypatch.setattr(comparison, "run_comparison", lambda *_: {})
    publications = {
        str(step): {"manifest": {
            "step": step,
            "delta_versions": {"sensor_readings": 14 + int(mixed_versions and step == 1)},
            "thresholds": [], "base_sha256": "base", "glb_sha256": "glb", "assets": [],
        }} for step in range(2)
    }
    data = app_data.TwinData(Config(), None, None)
    monkeypatch.setattr(data, "pushes", lambda: [
        {"run_id": "run", "scenario": "baseline", "push_id": str(i)} for i in range(2)
    ])
    monkeypatch.setattr(data, "publication", publications.__getitem__)
    listed = data.runs()[0]
    assert listed["replay_available"] is not mixed_versions
    if mixed_versions:
        assert "matching source versions" in listed["replay_unavailable_reason"]
        with pytest.raises(ReadError, match="REPLAY_NOT_FOUND"):
            app_replay.timeline(data, "run", "previous-run-replay", 0, 2)
    else:
        assert listed["replay_unavailable_reason"] is None


def test_long_simulation_matches_spark_double_contract():
    result = simulate(SimulationConfig(minutes=120), "a" * 32)
    assert len(result.readings) == 5040
    assert all(type(row[3]) is float for row in result.readings if row[3] is not None)
    assert len(result.metrics) == 120


def test_history_query_is_version_pinned_and_bounded():
    parameters = dict(
        run_id="a" * 32,
        versions=dict(assets=4, flights=12, sensor_readings=12, thresholds=2),
        thresholds=THRESHOLDS,
        start_ts="2026-11-09T22:00:00",
        end_ts="2026-11-09T23:00:00",
    )
    query = build_query("history", parameters, Config())
    assert "sensor_readings VERSION AS OF 12" in query.sql
    assert "assets VERSION AS OF 4" in query.sql
    assert "LEFT JOIN (SELECT * FROM VALUES" in query.sql
    assert query.parameters["run_id"] == "a" * 32
    for bad in (
        dict(parameters, versions={"assets": "1; DROP TABLE assets"}),
        dict(parameters, run_id="' OR true"),
        dict(parameters, end_ts="2026-11-10T22:00:00"),
    ):
        with pytest.raises(ValueError):
            build_query("history", bad, Config())


@pytest.mark.parametrize(
    "error",
    [
        ReadError("AUDIT_VERSION_UNAVAILABLE", status=410),
        ReadError("AUDIT_VERSION_UNAVAILABLE", "missing historical file", 410),
    ],
)
def test_unavailable_history_never_substitutes_current(monkeypatch, error):
    replay = dict(
        replay_id="id",
        minutes=1,
        start_ts="2026-11-09T22:00:00",
        identity={"delta_versions": {}, "thresholds": []},
    )
    monkeypatch.setattr(app_replay, "replay_sets", lambda *_: [replay])

    class Reader:
        def read(self, name, parameters):
            assert name == "history"
            raise error

    with pytest.raises(ReadError) as result:
        app_replay.timeline(SimpleNamespace(sql=Reader()), "run", "id", 0, 1)
    assert result.value.status == 410
    assert result.value.code == "AUDIT_VERSION_UNAVAILABLE"


def test_page_reduces_until_one_step_but_never_truncates(monkeypatch):
    replay = dict(
        replay_id="id",
        minutes=60,
        start_ts="2026-11-09T22:00:00",
        identity={"delta_versions": {}, "thresholds": []},
    )
    monkeypatch.setattr(app_replay, "replay_sets", lambda *_: [replay])
    spans = []

    class Reader:
        def read(self, name, parameters):
            spans.append(
                int(
                    (
                        datetime.fromisoformat(parameters["end_ts"])
                        - datetime.fromisoformat(parameters["start_ts"])
                    ).total_seconds()
                    / 60
                )
            )
            raise ReadError("READ_LIMIT_EXCEEDED", status=422)

    with pytest.raises(ReadError, match="READ_LIMIT_EXCEEDED"):
        app_replay.timeline(SimpleNamespace(sql=Reader()), "run", "id", 0, 60)
    assert spans == [60, 30, 15, 7, 3, 1]
