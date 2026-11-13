"""Paired, frozen-minute passenger journeys. All durations are integer seconds."""

from __future__ import annotations

import heapq
import math
from dataclasses import asdict, dataclass
from itertools import product
from random import Random


@dataclass(frozen=True)
class Policy:
    # Synthetic minimum, most likely and maximum durations in seconds.
    bag: tuple = (120, 420, 1200)
    standard: tuple = (35, 70, 150)
    precheck: tuple = (15, 35, 75)
    coffee: tuple = (90, 240, 600)
    restroom: tuple = (60, 150, 360)
    walk: tuple = (120, 240, 480)
    standard_lanes: int = 3
    precheck_lanes: int = 1
    precheck_share: float = 0.25
    boarding_buffer_minutes: int = 15

    def validate(self):
        for stage in ("bag", "standard", "precheck", "coffee", "restroom", "walk"):
            lo, mode, hi = getattr(self, stage)
            if not 0 <= lo <= mode <= hi or not math.isfinite(hi):
                raise ValueError(f"Invalid durations for {stage}")
        if not 0 <= self.precheck_share <= 1 or self.boarding_buffer_minutes < 0:
            raise ValueError("Invalid queue share or boarding buffer")
        if any(type(n) is not int or n < 1 for n in (self.standard_lanes, self.precheck_lanes)):
            raise ValueError("Each queue needs at least one lane")


def wait_seconds(services, lanes):
    available = [0] * lanes
    for duration in services:
        heapq.heapreplace(available, available[0] + duration)
    return available[0]


def interval(hits, n):
    """Wilson 95% interval for Monte Carlo sampling uncertainty."""
    p, z = hits / n, 1.959964
    scale = 1 + z * z / n
    center = (p + z * z / (2 * n)) / scale
    radius = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / scale
    return [max(0, center - radius), min(1, center + radius)]


STAGES = ("bag", "security_wait", "screening", "coffee", "restroom", "walk")


def simulate(queue: int, budget: int, seed: int, trials: int, policy: Policy):
    """One draw row supports all eight bag/stop combinations for an arm and queue."""
    policy.validate()
    if type(queue) is not int or queue < 0 or not 1 <= trials <= 100_000:
        raise ValueError("Invalid queue or trial count")
    streams = {key: Random(f"journey-v1/{seed}/{key}") for key in asdict(policy)}

    def draw(stage):
        lo, mode, hi = getattr(policy, stage)
        return round(streams[stage].triangular(lo, hi, mode))

    rows = []
    profiles = []
    # Each trial uses the same optional activity times for both checkpoint types.
    shared = [[draw(k) for k in ("bag", "coffee", "restroom", "walk")] for _ in range(trials)]
    pre_queue = round(queue * policy.precheck_share)
    for kind, ahead in (("standard", queue - pre_queue), ("precheck", pre_queue)):
        lanes = getattr(policy, kind + "_lanes")
        arms = [[], []]
        for trial, (bag, coffee, restroom, walk) in enumerate(shared):
            services = [draw(kind) for _ in range(ahead)]
            screening = draw(kind)
            for extra, arm in enumerate(arms):
                wait = wait_seconds(services, lanes + extra)
                stages = (bag, wait, screening, coffee, restroom, walk)
                arm.append(stages)
                rows.append((trial, kind, lanes + extra, *stages))
        for bag, coffee, restroom in product((False, True), repeat=3):
            summaries = []
            mask = (bag, True, True, coffee, restroom, True)
            for arm in arms:
                durations = [sum(v for v, use in zip(row, mask, strict=True) if use) for row in arm]
                durations.sort()
                hits = sum(t <= budget for t in durations)
                bins = [0] * (durations[-1] // 300 + 1)
                for duration in durations:
                    bins[duration // 300] += 1
                means = {
                    k: sum(row[i] for row in arm) / trials for i, k in enumerate(STAGES) if mask[i]
                }
                summaries.append(
                    dict(
                        hits=hits,
                        probability=hits / trials,
                        ci=interval(hits, trials),
                        p50=durations[math.ceil(0.5 * trials) - 1],
                        p90=durations[math.ceil(0.9 * trials) - 1],
                        bins=bins,
                        means=means,
                        sample={
                            k: v for k, v, use in zip(STAGES, arm[0], mask, strict=True) if use
                        },
                    )
                )
            gains = summaries[1]["hits"] - summaries[0]["hits"]
            profiles.append(
                dict(
                    kind=kind,
                    ahead=ahead,
                    lanes=lanes,
                    bag=bag,
                    coffee=coffee,
                    restroom=restroom,
                    arms=summaries,
                    gain=gains / trials,
                    gain_ci=interval(gains, trials),
                )
            )
    return rows, profiles
