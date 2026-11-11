# Databricks notebook source
from pathlib import Path

from airport_twin.captures import ingest_captures
from airport_twin.platform import notebook_context
from airport_twin.viewer import refresh_audits

config, platform, params = notebook_context(globals())
params["capture_result"] = ingest_captures(platform, Path(params["capture_dir"]), params["run_ids"])
params["viewer_bundle"] = refresh_audits(platform, params["run_ids"])
