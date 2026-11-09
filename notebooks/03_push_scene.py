# Databricks notebook source
from airport_twin.platform import notebook_context
from airport_twin.scene import push_scene

config, platform, params = notebook_context(globals())
publication = push_scene(platform, params["run_id"])
