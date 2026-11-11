# Databricks notebook source
from airport_twin.platform import notebook_context
from airport_twin.scene import publish_replay
from airport_twin.timeline import timeline_frames
from airport_twin.tracking import assert_run
from airport_twin.workflow import thresholds

config, platform, params = notebook_context(globals())
run_id = params["run_id"]
run = assert_run(config, run_id)
frames, versions = timeline_frames(platform, run_id)
assets = [r.asDict() for r in platform.spark.table(config.table("assets")).collect()]
params["publications"] = len(publish_replay(
    platform, run_id, frames, versions, assets, thresholds(platform), run.data.params["scenario"]
))
