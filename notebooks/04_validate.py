# Databricks notebook source
from airport_twin.platform import notebook_context
from airport_twin.workflow import validate

config, platform, params = notebook_context(globals())
validation = validate(platform, params["run_id"], params.get("phase", "all"))
