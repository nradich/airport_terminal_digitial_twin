"""Cancellation-safe frame presentation, independent of Kit and compute engines."""

from __future__ import annotations

import asyncio
import math
import time
from collections.abc import Awaitable, Callable

from airport_twin.presentation import transition_colours

RGB = tuple[float, float, float]


async def animate_frame(
    start: dict[str, RGB],
    states: list[dict],
    assets: list[dict],
    duration: float,
    apply: Callable[[dict[str, RGB]], None],
    next_update: Callable[[], Awaitable[object]],
    commit: Callable[[], None],
    clock: Callable[[], float] = time.perf_counter,
) -> None:
    """Finish exact colours and lineage together, even when playback is paused."""
    if not math.isfinite(duration) or duration < 0:
        raise ValueError("Frame duration must be finite and nonnegative")
    try:
        if duration:
            began = clock()
            while (elapsed := clock() - began) < duration:
                apply(transition_colours(start, states, assets, elapsed, duration))
                await next_update()
    except asyncio.CancelledError:
        commit()
        raise
    commit()
