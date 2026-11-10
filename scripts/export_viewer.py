"""Download an explicitly prepared UC/MLflow viewer artifact for desktop Kit."""

import argparse
import logging
from pathlib import Path

from airport_twin.config import Config
from airport_twin.viewer import export_bundle

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--run-id", required=True)
parser.add_argument("--output", type=Path, default=Path(".local/omniverse-test"))
args = parser.parse_args()
logging.basicConfig(level=logging.INFO)
logging.info("VIEWER_EXPORT_OK %s", export_bundle(Config.from_env(), args.run_id, args.output))
