# Databricks notebook source
from airport_twin.comparison import publish_pair
from airport_twin.platform import notebook_context

config, platform, params = notebook_context(globals())
if len(params["run_ids"]) != 2:
    raise ValueError("Supply explicit baseline and delay_A4 run IDs in that order")
params["comparison"] = publish_pair(platform, *params["run_ids"])
