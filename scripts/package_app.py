"""Build the self-contained Apps source artifact. Does not push or deploy."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import shutil
import subprocess
from pathlib import Path

import yaml


def package(
    root: Path,
    target: str,
    overrides: dict[str, str],
    skip_frontend: bool = False,
    skip_wheel: bool = False,
) -> Path:
    config = yaml.safe_load((root / "databricks.yml").read_text())
    values = {k: v.get("default", "") for k, v in config["variables"].items()}
    values.update(config["targets"][target].get("variables", {}))
    if overrides.keys() - values.keys():
        raise ValueError("Unknown bundle variable override")
    values.update(overrides)
    if not skip_wheel:
        subprocess.run(["uv", "build", "--wheel"], cwd=root, check=True)
    wheel = root / "dist/airport_twin-0.1.0-py3-none-any.whl"
    source = root / "app"
    (source / "wheels").mkdir(exist_ok=True)
    shutil.copy2(wheel, source / "wheels" / wheel.name)
    if not skip_frontend:
        subprocess.run(
            ["npm", "ci", "--no-audit", "--no-fund"], cwd=source / "frontend", check=True
        )
        subprocess.run(["npm", "run", "typecheck"], cwd=source / "frontend", check=True)
        subprocess.run(["npm", "run", "build"], cwd=source / "frontend", check=True)
    subprocess.run(
        [
            "uv",
            "lock",
            "--project",
            str(source),
            "--python",
            "3.11",
            "--refresh-package",
            "airport-twin",
        ],
        check=True,
    )
    output = root / "dist/app"
    if output.exists():
        if output.resolve() != root.resolve() / "dist/app":
            raise ValueError("Unsafe artifact destination")
        shutil.rmtree(output)
    output.mkdir(parents=True)
    for name in ("server", "static", "wheels"):
        shutil.copytree(source / name, output / name, ignore=shutil.ignore_patterns("__pycache__"))
    for name in ("launch.py", "pyproject.toml", "uv.lock"):
        shutil.copy2(source / name, output / name)
    runtime = yaml.safe_load((source / "app.yaml").read_text())
    names = {
        "catalog": "TWIN_CATALOG",
        "schema": "TWIN_SCHEMA",
        "experiment": "TWIN_EXPERIMENT",
        "platform": "TWIN_PLATFORM",
        "tracking_uri": "MLFLOW_TRACKING_URI",
        "registry_uri": "MLFLOW_REGISTRY_URI",
    }
    for key, name in names.items():
        entry = next(item for item in runtime["env"] if item["name"] == name)
        entry["value"] = str(values[key])
    (output / "app.yaml").write_text(yaml.safe_dump(runtime, sort_keys=False))
    files = {
        str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in output.rglob("*")
        if p.is_file()
    }
    (output / "build.json").write_text(json.dumps({"target": target, "files": files}, indent=2))
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=["local", "dev"], default="dev")
    parser.add_argument("--var", action="append", default=[])
    parser.add_argument("--skip-frontend", action="store_true")
    parser.add_argument("--skip-wheel", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logging.info(
        "APP_PACKAGE_OK %s",
        package(
            Path(__file__).resolve().parents[1],
            args.target,
            dict(v.split("=", 1) for v in args.var),
            args.skip_frontend,
            args.skip_wheel,
        ),
    )
