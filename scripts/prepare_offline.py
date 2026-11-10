"""Prepare locked CPU Python 3.11 wheels; no upload or deployment is performed."""

from __future__ import annotations

import argparse
import hashlib
import logging
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--app", action="store_true", help="Prepare the locked App dependency closure"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    root = Path.cwd()
    project = root / "app" if args.app else root
    lock_id = hashlib.sha256((project / "uv.lock").read_bytes()).hexdigest()[:12]
    folder = (
        root / ".local" / "app-wheelhouse" / lock_id if args.app else root / ".local" / "wheelhouse"
    )
    folder.mkdir(parents=True, exist_ok=True)
    requirements = (
        root
        / ".local"
        / (f"requirements-app-{lock_id}.txt" if args.app else "requirements-runtime.txt")
    )
    subprocess.run(
        [
            "uv",
            "export",
            "--project",
            str(project),
            "--frozen",
            "--no-dev",
            "--no-emit-project",
            "--no-hashes",
            "--format",
            "requirements.txt",
            "--output-file",
            str(requirements),
        ],
        check=True,
        cwd=project,
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            "--only-binary=:all:",
            "--dest",
            str(folder),
            "-r",
            str(requirements),
        ],
        check=True,
        cwd=project,
    )
    project_wheels = sorted((root / "dist").glob("airport_twin-*.whl"))
    if len(project_wheels) != 1:
        raise ValueError("Build exactly one current airport wheel with uv build --wheel first")
    shutil.copy2(project_wheels[0], folder / project_wheels[0].name)
    wheels = sorted(folder.glob("*.whl"))
    lines = [f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}" for path in wheels]
    (folder / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if args.app:
        from packaging.utils import parse_wheel_filename

        pins = sorted(
            {
                f"{parse_wheel_filename(path.name)[0]}=={parse_wheel_filename(path.name)[1]}"
                for path in wheels
            }
        )
        (folder / "install.txt").write_text("\n".join(pins) + "\n")
    logging.info("OFFLINE_WHEELS_OK count=%d folder=%s", len(wheels), folder)


if __name__ == "__main__":
    main()
