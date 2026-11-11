import asyncio

import pytest

from airport_twin.playback import animate_frame
from airport_twin.presentation import linear_rgb


def test_pause_during_blend_finishes_exact_frame_and_lineage():
    async def exercise():
        assets = [
            {"asset_id": "GATE_A4", "asset_type": "gate"},
            {"asset_id": "GATE_A1", "asset_type": "gate"},
        ]
        states = [{"asset_id": asset["asset_id"], "colour": "#EF4444"} for asset in assets]
        start = {asset["asset_id"]: (0.0, 0.0, 0.0) for asset in assets}
        expected = {row["asset_id"]: linear_rgb(row["colour"]) for row in states}
        colours, lineage = [], []
        blended = asyncio.Event()

        async def next_update():
            blended.set()
            await asyncio.Future()

        def commit():
            colours.append(expected)
            lineage.append(("run", 12, "push-for-minute-12"))

        times = iter([0.0, 0.75])
        task = asyncio.create_task(
            animate_frame(
                start, states, assets, 1.5, colours.append, next_update, commit, lambda: next(times)
            )
        )
        await blended.wait()
        assert colours[-1] != expected
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert colours[-1] == expected
        assert lineage == [("run", 12, "push-for-minute-12")]

    asyncio.run(exercise())


def test_instant_frame_commits_once_without_waiting_for_renderer():
    calls = []

    async def no_wait():
        raise AssertionError("An instantaneous frame must not wait")

    asyncio.run(animate_frame({}, [], [], 0, lambda _: None, no_wait, lambda: calls.append(1)))
    assert calls == [1]
