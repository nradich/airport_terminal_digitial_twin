# Databricks notebook source
from airport_twin.platform import notebook_context
from airport_twin.viewer import prepare_bundle

config, platform, params = notebook_context(globals())
params["viewer_bundle"] = prepare_bundle(platform, params["run_ids"])
