# Databricks notebook source
from airport_twin.platform import notebook_context
from airport_twin.scene import build_scene

config, platform, params = notebook_context(globals())
base_path = build_scene(platform)
