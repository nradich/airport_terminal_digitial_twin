"""Deterministic synthetic flight, crowding, and environmental signals."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import timedelta

from airport_twin.config import SimulationConfig
from airport_twin.data import THRESHOLDS

NUMERIC = {"pax_count", "hvac_temp_c", "co2_ppm", "queue_len", "belt_load_pct"}
CATEGORIES = {
    "jet_bridge_status": {"docked", "idle", "fault"},
    "flight_status": {"on_time", "delayed", "boarding", "departed"},
}


@dataclass
class Simulation:
    readings: list[tuple]
    flights: list[tuple]
    metrics: list[dict[str, float]]


def numeric_status(value: float, warn: float, crit: float) -> str:
    if not all(math.isfinite(x) for x in (value, warn, crit)) or warn >= crit:
        raise ValueError("Finite measurements and warn < crit are required")
    return "crit" if value >= crit else "warn" if value >= warn else "ok"


def validate_readings(rows: list[tuple]) -> None:
    seen = set()
    for asset, ts, metric, num, text, run_id in rows:
        if not asset or not run_id or ts is None:
            raise ValueError("Reading identity, timestamp, and run ID are required")
        key = (run_id, asset, ts, metric)
        if key in seen:
            raise ValueError(f"Duplicate reading {key}")
        seen.add(key)
        if metric in NUMERIC:
            if text is not None or num is None or not math.isfinite(num):
                raise ValueError(f"Invalid numeric reading for {metric}")
        elif metric in CATEGORIES:
            if num is not None or text not in CATEGORIES[metric]:
                raise ValueError(f"Invalid categorical reading for {metric}")
        else:
            raise ValueError(f"Unknown metric {metric}")


def simulate(
    config: SimulationConfig, run_id: str, thresholds: list[tuple] | None = None
) -> Simulation:
    rng = random.Random(config.seed)
    limits = {(a, m): (w, c) for a, m, w, c in (THRESHOLDS if thresholds is None else thresholds)}
    readings, metrics = [], []
    co2, temps = [450.0] * 8, [22.0] * 8
    departures = [30, 40, 50, 45, 60, 70, 80, 90]
    target = departures.copy()
    if config.scenario == "delay_A4":
        target[3] += 60
    queues: list[float] = []
    peak_a4 = 0.0
    for minute in range(config.minutes):
        ts = config.start + timedelta(minutes=minute)
        gate_values = []
        n_crit = 0
        for index in range(8):
            dep, actual = departures[index], target[index]
            noise = rng.uniform(-3, 3)  # Same random draws across scenarios.
            base = 12 + 112 * math.exp(-(((minute - (dep - 12)) / 19) ** 2))
            if actual > dep and minute >= dep - 18:
                pax = min(285.0, base + (minute - (dep - 18)) * 5.7)
            elif minute >= actual:
                pax = max(4.0, 24 - (minute - actual) * 3)
            else:
                pax = base
            pax = float(max(0, round(pax + noise)))
            ventilation = 1.0 if co2[index] > 900 or temps[index] > 24 else 0.0
            co2[index] += 0.15 * ((450 + pax * 5.5 - ventilation * 140) - co2[index])
            temps[index] += 0.12 * ((22 + pax * 0.033 - ventilation * 2.2) - temps[index])
            status = (
                "departed"
                if minute >= actual
                else "delayed"
                if actual > dep and minute >= dep - 18
                else "boarding"
                if minute >= dep - 15
                else "on_time"
            )
            values = {
                "pax_count": pax,
                "hvac_temp_c": round(temps[index], 3),
                "co2_ppm": round(co2[index], 3),
                "jet_bridge_status": "idle" if status == "departed" else "docked",
                "flight_status": status,
            }
            for metric, value in values.items():
                numeric = metric in NUMERIC
                readings.append(
                    (
                        f"GATE_A{index + 1}",
                        ts,
                        metric,
                        float(value) if numeric else None,
                        None if numeric else value,
                        run_id,
                    )
                )
            numeric_crit = any(
                numeric_status(values[m], *limits[("gate", m)]) == "crit"
                for m in ("pax_count", "hvac_temp_c", "co2_ppm")
            )
            n_crit += int(numeric_crit)
            gate_values.append(pax)
        queue = float(round(15 + sum(gate_values) * 0.055 + rng.uniform(-3, 3)))
        belt = round(min(100, 38 + minute * 0.65 + rng.uniform(-3, 3)), 3)
        readings.extend(
            [
                ("SECURITY", ts, "queue_len", queue, None, run_id),
                ("BAGGAGE", ts, "belt_load_pct", belt, None, run_id),
            ]
        )
        queues.append(queue)
        peak_a4 = max(peak_a4, gate_values[3])
        ordered = sorted(queues)
        p95 = ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)]
        metrics.append(
            {
                "peak_pax_A4": peak_a4,
                "gates_in_crit": float(n_crit),
                "avg_co2": sum(co2) / 8,
                "security_queue_p95": p95,
            }
        )
    flights = [
        (
            f"AT{i + 101}",
            f"GATE_A{i + 1}",
            config.start + timedelta(minutes=dep),
            config.start + timedelta(minutes=target[i]) if target[i] < config.minutes else None,
            "departed"
            if target[i] < config.minutes
            else "delayed"
            if target[i] > dep
            else "on_time",
            run_id,
        )
        for i, dep in enumerate(departures)
    ]
    validate_readings(readings)
    return Simulation(readings, flights, metrics)
