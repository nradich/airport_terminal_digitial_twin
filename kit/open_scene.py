"""Kit --exec entry point. Desktop rendering only; no Spark session is created."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "kit")]

from airport_viewer import AirportViewer  # noqa: E402

viewer = AirportViewer(ROOT)
