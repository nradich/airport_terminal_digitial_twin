# Databricks notebook source
from airport_twin.captures import validate_filming
from airport_twin.platform import notebook_context

config, platform, params = notebook_context(globals())
params["film_validation"] = validate_filming(platform, params["run_ids"])
