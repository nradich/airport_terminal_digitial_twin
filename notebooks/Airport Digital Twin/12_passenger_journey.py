# Databricks notebook source
import json
import logging

from airport_twin.journey import Policy
from airport_twin.journey_experiment import publish_journey
from airport_twin.platform import notebook_context

config, platform, params = notebook_context(globals())
for name, default in (("push_id", ""), ("flight_id", "AT104"), ("trials", "10000")):
    if config.platform == "databricks":
        dbutils.widgets.text(name, default)
        params[name] = dbutils.widgets.get(name)
    else:
        params.setdefault(name, default)

if config.platform == "databricks":
    dbutils.widgets.text("journey_policy", "{}")
    params["journey_policy"] = json.loads(dbutils.widgets.get("journey_policy"))

params["journey_run_id"] = publish_journey(
    platform,
    params["push_id"],
    params["flight_id"],
    int(params["seed"]),
    int(params["trials"]),
    Policy(**params.get("journey_policy", {})),
)
logging.getLogger(__name__).info("JOURNEY_COMPLETE run_id=%s", params["journey_run_id"])
