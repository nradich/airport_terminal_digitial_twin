import pytest
from pxr import Sdf, Usd, UsdGeom

from airport_twin.bridge import KitMessageTransport, UsdVolumeTransport
from airport_twin.data import ASSETS
from airport_twin.scene.usd import base_bytes, linear_rgb, override_bytes, verify_composition


def assets():
    keys = ("asset_id", "asset_type", "zone", "prim_path", "display_name")
    return [dict(zip(keys, row, strict=True)) for row in ASSETS]


def test_usd_round_trip_and_base_immutable(tmp_path):
    transport = UsdVolumeTransport(tmp_path)
    base = base_bytes(assets())
    transport.publish("terminal_base.usda", base)
    states = [
        {
            **a,
            "colour": "#EF4444" if a["asset_id"] == "GATE_A4" else "#22C55E",
            "status": "crit" if a["asset_id"] == "GATE_A4" else "ok",
        }
        for a in assets()
    ]
    path = transport.publish("runs/run/push/terminal_state_run.usda", override_bytes(states, {}))
    verify_composition(path, states)
    assert (tmp_path / "terminal_base.usda").read_bytes() == base
    assert transport.publish("terminal_base.usda", base).read_bytes() == base
    root = Sdf.Layer.FindOrOpen(str(path))
    for state in states:
        assert root.GetPrimAtPath(state["prim_path"]).specifier == Sdf.SpecifierOver
    stage = Usd.Stage.Open(str(path))
    assert UsdGeom.GetStageUpAxis(stage) == UsdGeom.Tokens.z
    assert UsdGeom.GetStageMetersPerUnit(stage) == 1
    assert len([p for p in stage.Traverse() if p.HasAttribute("twin:asset_id")]) == 10


def test_transport_retry_after_publication(tmp_path):
    transport = UsdVolumeTransport(tmp_path)
    # Model a crash between the verified file publication and the database audit.
    transport.publish("runs/run/push/scene.usda", b"verified state")
    assert (
        transport.publish("runs/run/push/scene.usda", b"verified state").read_bytes()
        == b"verified state"
    )
    with pytest.raises(FileExistsError):
        transport.publish("runs/run/push/scene.usda", b"different")
    with pytest.raises(ValueError):
        transport.publish("../escape", b"bad")
    assert not list(tmp_path.rglob("*.pending-*"))


def test_linear_rgb_and_kit_stub():
    assert linear_rgb("#FFFFFF") == (1.0, 1.0, 1.0)
    assert linear_rgb("#000000") == (0.0, 0.0, 0.0)
    with pytest.raises(NotImplementedError):
        KitMessageTransport().publish("x", b"x")


def test_retry_after_audit_failure(tmp_path, monkeypatch):
    from contextlib import nullcontext
    from types import SimpleNamespace

    import mlflow

    import airport_twin.scene as scene
    import airport_twin.tracking as tracking
    from airport_twin.config import Config

    transport = UsdVolumeTransport(tmp_path)
    transport.publish("terminal_base.usda", base_bytes(assets()))
    states = [{**a, "colour": "#22C55E", "status": "ok"} for a in assets()]
    snapshot = {
        "run_id": "test",
        "scenario": "baseline",
        "step": 59,
        "assets": assets(),
        "states": states,
        "metric_states": [],
        "thresholds": [],
        "base_sha256": "base",
        "delta_versions": {},
    }
    monkeypatch.setattr(scene, "capture", lambda *_: snapshot)
    monkeypatch.setattr(mlflow, "active_run", lambda: None)
    monkeypatch.setattr(mlflow, "start_run", lambda **_: nullcontext())
    monkeypatch.setattr(scene, "client", lambda _: SimpleNamespace(set_tag=lambda *_: None))
    monkeypatch.setattr(tracking, "log_scene", lambda *_: None)
    audit = {}
    attempts = []

    def commit(_platform, _name, rows, _schema, keys):
        assert keys == ["push_id"]
        attempts.append(rows[0][0])
        if len(attempts) == 1:
            raise RuntimeError("simulated failure after verified USD publication")
        audit.setdefault(rows[0][0], rows[0])

    monkeypatch.setattr(scene, "merge_rows", commit)
    platform = SimpleNamespace(
        config=Config(platform="local", tracking_uri="http://localhost:5000"),
        volume_root=lambda: tmp_path,
    )
    with pytest.raises(RuntimeError, match="simulated failure"):
        scene.push_scene(platform, "test")
    assert not audit
    path = next(tmp_path.rglob("terminal_state_test.usda"))
    original = path.read_bytes()
    first = scene.push_scene(platform, "test")
    second = scene.push_scene(platform, "test")
    assert first["push_id"] == second["push_id"]
    assert path.read_bytes() == original
    assert len(audit) == 1
