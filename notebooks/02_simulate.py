# Databricks notebook source
from airport_twin.config import SimulationConfig
from airport_twin.platform import notebook_context
from airport_twin.workflow import run_simulation

config, platform, params = notebook_context(globals())
run_id = run_simulation(
    platform,
    SimulationConfig(
        scenario=params["scenario"], seed=int(params["seed"]), minutes=int(params["minutes"])
    ),
)
params["run_id"] = run_id
if "twin_params" in globals():
    twin_params["run_id"] = run_id
else:
    dbutils.jobs.taskValues.set(key="run_id", value=run_id)
