# Databricks notebook source
import logging

from airport_twin.data import setup
from airport_twin.platform import notebook_context

logging.basicConfig(level=logging.INFO)
config, platform, params = notebook_context(globals())
setup_result = setup(platform)
