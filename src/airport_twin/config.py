"""Portable configuration, validated before generating SQL or storage paths."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Config:
    catalog: str = "dbx_twin"
    schema: str = "airport"
    experiment: str = "/Shared/airport-twin"
    platform: str = "databricks"
    tracking_uri: str = "databricks"
    registry_uri: str = "databricks-uc"

    def __post_init__(self) -> None:
        for item in (self.catalog, self.schema):
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", item):
                raise ValueError(f"Invalid UC identifier: {item!r}")
        if self.platform not in {"local", "databricks"}:
            raise ValueError("platform must be local or databricks")

    @property
    def namespace(self) -> str:
        return f"{self.catalog}.{self.schema}"

    def table(self, name: str) -> str:
        if name not in {
            "assets",
            "flights",
            "sensor_readings",
            "thresholds",
            "scene_pushes",
            "latest_state",
            "gate_health",
        }:
            raise ValueError(f"Unknown twin object: {name}")
        return f"{self.namespace}.{name}"

    @classmethod
    def from_env(cls) -> Config:
        platform = os.getenv("TWIN_PLATFORM", "databricks")
        return cls(
            catalog=os.getenv("TWIN_CATALOG", "dbx_twin"),
            schema=os.getenv("TWIN_SCHEMA", "airport"),
            experiment=os.getenv("TWIN_EXPERIMENT", "/Shared/airport-twin"),
            platform=platform,
            tracking_uri=os.getenv("MLFLOW_TRACKING_URI", "databricks"),
            registry_uri=os.getenv("MLFLOW_REGISTRY_URI", "databricks-uc"),
        )


@dataclass(frozen=True)
class SimulationConfig:
    scenario: str = "baseline"
    seed: int = 42
    minutes: int = 60
    n_gates: int = 8
    start: datetime = datetime(2026, 11, 9, 22, 0)

    def __post_init__(self) -> None:
        if self.scenario not in {"baseline", "delay_A4"}:
            raise ValueError("scenario must be baseline or delay_A4")
        if self.n_gates != 8 or not 1 <= self.minutes <= 240:
            raise ValueError("The v1 scene requires eight gates and 1..240 simulation minutes")
        if self.start.tzinfo is not None:
            raise ValueError("Use a naive UTC start; both platforms set their SQL timezone to UTC")
