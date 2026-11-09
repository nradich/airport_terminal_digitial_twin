"""Read local bundle defaults without inventing a local Databricks deployment API."""

from __future__ import annotations

import os
from pathlib import Path

import yaml


def local_environment(path: Path) -> None:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    defaults = {name: value.get("default", "") for name, value in document["variables"].items()}
    defaults.update(document["targets"]["local"].get("variables", {}))
    for variable, environment in {
        "catalog": "TWIN_CATALOG",
        "schema": "TWIN_SCHEMA",
        "experiment": "TWIN_EXPERIMENT",
        "platform": "TWIN_PLATFORM",
        "tracking_uri": "MLFLOW_TRACKING_URI",
        "registry_uri": "MLFLOW_REGISTRY_URI",
        "git_sha": "TWIN_GIT_SHA",
    }.items():
        os.environ.setdefault(environment, str(defaults[variable]))
