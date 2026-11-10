import threading
from types import SimpleNamespace

import pytest

from airport_twin import readers
from airport_twin.config import Config


def test_local_busy_retries_are_reads_with_identical_parameters(monkeypatch):
    responses = iter(
        [
            SimpleNamespace(status_code=429),
            SimpleNamespace(
                status_code=200, ok=True, json=lambda: {"rows": [{"asset_id": "GATE_A4"}]}
            ),
        ]
    )
    calls = []

    def post(_url, **kwargs):
        calls.append(kwargs)
        return next(responses)

    monkeypatch.setenv("TWIN_QUERY_URL", "http://gateway")
    monkeypatch.setenv("TWIN_QUERY_TOKEN", "test-only")
    monkeypatch.setattr(readers.requests, "post", post)
    monkeypatch.setattr(readers.time, "sleep", lambda _: None)
    result = readers.LocalSqlReader().read("assets")
    assert result == [{"asset_id": "GATE_A4"}]
    assert calls[0]["json"] == calls[1]["json"] == {"query": "assets", "parameters": {}}


@pytest.mark.parametrize(
    "code", ["DELTA_VERSION_NOT_FOUND", "DELTA_FILE_NOT_FOUND", "DELTA_TRUNCATED_TRANSACTION_LOG"]
)
def test_cloud_historical_errors_are_redacted_410(code):
    error = readers.query_error(RuntimeError(code + " secret SQL details"))
    assert (error.code, error.status) == ("AUDIT_VERSION_UNAVAILABLE", 410)
    assert "secret" not in str(error)


def test_cloud_rows_and_bytes_never_truncate():
    assert readers.bounded_rows([{"value": 42}]) == [{"value": 42}]
    for rows in ([{}] * 5001, [{"value": "x" * (2 * 1024 * 1024)}]):
        with pytest.raises(readers.ReadError) as error:
            readers.bounded_rows(rows)
        assert error.value.code == "READ_LIMIT_EXCEEDED"


def test_cloud_native_binding_and_error_translation(monkeypatch):
    from databricks import sql
    from databricks.sdk import core

    calls = []

    class Cursor:
        description = [("asset_id",)]

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def execute(self, statement, parameters):
            calls.append((statement, parameters))

        def fetchmany(self, size):
            assert size == 5001
            return [("GATE_A4",)]

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def cursor(self):
            return Cursor()

    monkeypatch.setattr(core, "Config", lambda: SimpleNamespace(host="https://workspace.example"))
    monkeypatch.setattr(sql, "connect", lambda **_: Connection())
    monkeypatch.setenv("TWIN_WAREHOUSE_ID", "warehouse")
    reader = readers.DatabricksSqlReader(Config())
    result = reader.read("current", {"run_id": "a" * 32})
    assert result == [{"asset_id": "GATE_A4"}]
    assert calls[0][1] == {"run_id": "a" * 32}

    def unavailable(*_):
        raise RuntimeError("[DELTA_VERSION_NOT_FOUND] details")

    monkeypatch.setattr(reader, "_execute", unavailable)
    with pytest.raises(readers.ReadError) as error:
        reader.read("assets")
    assert error.value.status == 410


def test_cloud_deadline_cancels_and_retains_capacity_until_worker_exits(monkeypatch):
    gate, finished, cancelled = threading.Event(), threading.Event(), threading.Event()
    slots = threading.BoundedSemaphore(1)
    monkeypatch.setattr(readers, "_SQL_SLOTS", slots)
    monkeypatch.setattr(readers, "QUERY_SECONDS", 0.02)
    reader = readers.DatabricksSqlReader(Config())

    def blocked(_query, holder):
        holder["cursor"] = SimpleNamespace(cancel=cancelled.set)
        try:
            gate.wait(2)
        finally:
            finished.set()
        return []

    monkeypatch.setattr(reader, "_execute", blocked)
    try:
        with pytest.raises(readers.ReadError) as error:
            reader.read("assets")
        assert error.value.status == 504 and cancelled.wait(1)
        with pytest.raises(readers.ReadError) as error:
            reader.read("assets")
        assert error.value.status == 429
    finally:
        gate.set()
        assert finished.wait(1)
