# Databricks notebook source
from airport_twin.contracts import run_contracts
from airport_twin.platform import notebook_context

config, platform, params = notebook_context(globals())
params["contracts"] = run_contracts(platform)
