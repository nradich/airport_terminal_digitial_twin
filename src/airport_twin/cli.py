"""Local notebook orchestration; never creates its own compute engine."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "data",
            "run",
            "push",
            "validate",
            "setup",
            "prepare-viewer",
            "collect-captures",
            "validate-viewer",
            "publish-replay",
        ],
    )
    parser.add_argument("--scenario", default="baseline", choices=["baseline", "delay_A4"])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--minutes", type=int, default=60)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--step", type=int, default=-1)
    parser.add_argument("--run-ids", nargs="+", default=[])
    parser.add_argument("--capture-dir", default=".local/omniverse-test/captures")
    args = parser.parse_args()
    from airport_twin.bundle import local_environment

    local_environment(Path.cwd() / "databricks.yml")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from airport_twin.runner import execute

    root = Path.cwd() / "notebooks"
    stages = {
        "data": ["00_setup", "02_simulate", "04_validate"],
        "run": ["00_setup", "01_build_scene", "02_simulate", "03_push_scene", "04_validate"],
        "setup": ["00_setup"],
        "push": ["03_push_scene"],
        "validate": ["04_validate"],
        "prepare-viewer": ["00_setup", "06_prepare_viewer"],
        "collect-captures": ["07_collect_captures"],
        "validate-viewer": ["08_validate_viewer"],
        "publish-replay": ["09_publish_replay"],
    }
    params = {
        "scenario": args.scenario,
        "seed": args.seed,
        "minutes": args.minutes,
        "run_id": args.run_id,
        "phase": "data" if args.command == "data" else "all",
        "run_ids": args.run_ids,
        "step": args.step,
        "capture_dir": args.capture_dir,
    }
    result = execute([root / (name + ".py") for name in stages[args.command]], params)
    logging.getLogger(__name__).info("PIPELINE_OK %s", json.dumps(result))


if __name__ == "__main__":
    main()
