"""Prepare locked CPU Python 3.11 wheels; no upload or deployment is performed."""

from __future__ import annotations

import hashlib
import logging
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    root = Path.cwd()
    folder = root / ".local" / "wheelhouse"
    folder.mkdir(parents=True, exist_ok=True)
    requirements = root / ".local" / "requirements-runtime.txt"
    subprocess.run(
        [
            "uv",
            "export",
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
    )
    project_wheels = sorted((root / "dist").glob("airport_twin-*.whl"))
    if len(project_wheels) != 1:
        raise ValueError("Build exactly one current airport wheel with uv build --wheel first")
    shutil.copy2(project_wheels[0], folder / project_wheels[0].name)
    wheels = sorted(folder.glob("*.whl"))
    lines = [f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}" for path in wheels]
    (folder / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    logging.info("OFFLINE_WHEELS_OK count=%d folder=%s", len(wheels), folder)


if __name__ == "__main__":
    main()
