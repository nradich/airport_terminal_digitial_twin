from types import SimpleNamespace

import pytest

from airport_twin.bundle import local_environment
from airport_twin.config import Config
from airport_twin.platform import notebook_context


def test_bundle_local_defaults_preserve_environment(tmp_path, monkeypatch):
    path = tmp_path / "databricks.yml"
    path.write_text("""variables:
  catalog: {default: dbx_twin}
  schema: {default: airport}
  experiment: {default: /Shared/airport-twin}
  platform: {default: databricks}
  tracking_uri: {default: databricks}
  registry_uri: {default: databricks-uc}
  git_sha: {default: ''}
targets:
  local:
    variables: {platform: local, schema: custom}
""")
    monkeypatch.setenv("TWIN_CATALOG", "existing_catalog")
    monkeypatch.delenv("TWIN_SCHEMA", raising=False)
    local_environment(path)
    config = Config.from_env()
    assert config.catalog == "existing_catalog" and config.schema == "custom"


def test_databricks_widgets_and_explicit_run_id(monkeypatch):
    monkeypatch.setenv("TWIN_PLATFORM", "databricks")
    monkeypatch.setenv("TWIN_GIT_SHA", "")
    values = {
        "TWIN_CATALOG": "remote_catalog",
        "TWIN_SCHEMA": "remote_schema",
        "TWIN_EXPERIMENT": "/Shared/remote",
        "TWIN_GIT_SHA": "a" * 40,
        "run_id": "explicit-mlflow-run",
    }
    widgets = SimpleNamespace(
        text=lambda key, default: values.setdefault(key, default), get=lambda key: values[key]
    )
    statements = []
    spark = SimpleNamespace(sql=lambda query: statements.append(query))
    config, platform, params = notebook_context(
        {"spark": spark, "dbutils": SimpleNamespace(widgets=widgets)}
    )
    assert config.namespace == "remote_catalog.remote_schema"
    assert config.experiment == "/Shared/remote"
    assert platform.spark is spark
    assert params["run_id"] == "explicit-mlflow-run"
    assert statements == ["SET TIME ZONE 'UTC'"]


def test_invalid_identifier():
    with pytest.raises(ValueError):
        Config(catalog="catalog;DROP SCHEMA airport")
