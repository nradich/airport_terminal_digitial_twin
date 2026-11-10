from types import SimpleNamespace

import pytest

from airport_twin import comparison, provenance
from airport_twin.config import Config
from airport_twin.readers import ReadError
from airport_twin.rules import rule_snapshot


def rows():
    return [
        dict(
            metric=m,
            value_num=213.0 if m == "pax_count" else None,
            value_str=None if m == "pax_count" else "on_time",
            warn=120.0,
            crit=180.0,
            severity=2 if m == "pax_count" else 0,
            status="crit" if m == "pax_count" else "ok",
        )
        for m in ("pax_count", "co2_ppm", "hvac_temp_c", "flight_status", "jet_bridge_status")
    ]


def test_explanation_is_worst_governed_signal():
    assert provenance.explain(rows()) == "213 passengers ≥ critical threshold 180"
    with pytest.raises(ReadError):
        provenance.explain(rows()[:4])
    values = rows()
    values[0]["severity"] = 0
    assert "healthy" in provenance.explain(values)


def test_rule_identity_changes_when_sql_changes(monkeypatch):
    first = rule_snapshot()
    monkeypatch.setattr("airport_twin.rules.sql_text", lambda name: "changed " + name)
    assert rule_snapshot()["rule_id"] != first["rule_id"]
    assert set(first["templates"]) == {
        "latest_state.sql",
        "gate_health.sql",
        "colour.sql",
        "status_colour.sql",
    }


def test_explicit_comparison_validates_and_never_guesses(monkeypatch):
    parameters = dict(
        seed="42",
        start_utc="2026-11-09T22:00:00",
        minutes="60",
        n_gates="8",
        thresholds_snapshot="[]",
    )
    runs = {
        "a" * 32: SimpleNamespace(
            data=SimpleNamespace(params={**parameters, "scenario": "baseline"}),
            info=SimpleNamespace(experiment_id="5"),
        ),
        "b" * 32: SimpleNamespace(
            data=SimpleNamespace(params={**parameters, "scenario": "delay_A4"}),
            info=SimpleNamespace(experiment_id="5"),
        ),
    }
    monkeypatch.setattr(comparison, "assert_run", lambda _config, id: runs[id])
    config = Config(platform="local")
    body = comparison.pair_metadata(config, "a" * 32, "b" * 32)
    assert body["baseline_run_id"] == "a" * 32
    monkeypatch.setattr(
        comparison, "run_url", lambda *_: "http://localhost:5000/mlflow/#/experiments/5/runs/aaa"
    )
    url = comparison.comparison_url(config, ["a" * 32, "b" * 32], "5")
    assert "/#/compare-runs?runs=%5B" in url and "a" * 32 in url and "b" * 32 in url
    monkeypatch.delenv("TWIN_MLFLOW_COMPARE_URL_TEMPLATE", raising=False)
    assert comparison.comparison_url(Config(), ["a" * 32, "b" * 32], "5") is None
    runs["b" * 32].data.params["seed"] = "7"
    with pytest.raises(ValueError, match="seed"):
        comparison.pair_metadata(config, "a" * 32, "b" * 32)
