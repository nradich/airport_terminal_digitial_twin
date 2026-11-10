"""Viewport receipts and UC/MLflow ingestion; no Kit or GPU imports."""

from __future__ import annotations

import hashlib
import json
import struct
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def png_dimensions(payload: bytes) -> tuple[int, int]:
    if len(payload) < 24 or payload[:8] != b"\x89PNG\r\n\x1a\n" or payload[12:16] != b"IHDR":
        raise ValueError("Expected a PNG screenshot")
    width, height = struct.unpack(">II", payload[16:24])
    if width < 100 or height < 100:
        raise ValueError("Screenshot dimensions are too small")
    return width, height


def capture_receipt(directory: Path, png: Path, run: dict, step: int, camera: str) -> Path:
    """Stage an actual Kit screenshot for governed ingestion with exact lineage."""
    payload = png.read_bytes()
    width, height = png_dimensions(payload)
    audit = run["frames"][step]["push"]
    if (audit["run_id"], audit["scenario"], audit["step"]) != (
        run["run_id"],
        run["scenario"],
        step,
    ):
        raise ValueError("Capture and scene_pushes lineage disagree")
    if camera not in {"Overview", "A4CloseUp"}:
        raise ValueError("Unknown story camera")
    digest = hashlib.sha256(payload).hexdigest()
    # Keep desktop staging paths below Windows' legacy path limit. Full identities
    # remain in the receipt; an abbreviated-path collision fails explicitly.
    target = directory / run["run_id"][:8] / audit["push_id"][:12] / camera / digest[:16]
    target.mkdir(parents=True, exist_ok=True)
    receipt = {
        "format_version": 1,
        "run_id": run["run_id"],
        "scenario": run["scenario"],
        "step": step,
        "push_id": audit["push_id"],
        "usd_path": audit["usd_path"],
        "camera": camera,
        "sha256": digest,
        "width": width,
        "height": height,
        "captured_at": datetime.now(UTC).isoformat(),
    }
    metadata = target / "receipt.json"
    if metadata.exists():
        previous = json.loads(metadata.read_text(encoding="utf-8"))
        if any(previous[key] != receipt[key] for key in receipt if key != "captured_at"):
            raise FileExistsError("Abbreviated capture path collision")
    else:
        (target / "frame.png").write_bytes(payload)
        metadata.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return metadata


def ingest_captures(platform: Any, directory: Path, run_ids: list[str]) -> dict:
    """Check receipts against UC audit rows, then store Volume and MLflow artifacts."""
    import logging
    import tempfile

    from PIL import Image

    from airport_twin.bridge import UsdVolumeTransport
    from airport_twin.data import merge_rows
    from airport_twin.scene import PUSH_SCHEMA
    from airport_twin.tracking import assert_run, client

    if not run_ids or not directory.is_dir():
        raise ValueError("Supply explicit run IDs and a populated capture inbox")
    table = platform.spark.table(platform.config.table("scene_pushes"))
    audits = {r.push_id: r.asDict() for r in table.where(table.run_id.isin(run_ids)).collect()}
    c = client(platform.config)
    for run_id in run_ids:
        assert_run(platform.config, run_id)
    transport = UsdVolumeTransport(platform.volume_root())
    updated, count, skipped = {}, 0, 0
    receipts = sorted(
        directory.rglob("receipt.json"),
        key=lambda p: (json.loads(p.read_text(encoding="utf-8"))["captured_at"], str(p)),
    )
    for receipt_path in receipts:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt["run_id"] not in run_ids:
            continue
        if receipt.get("format_version") != 1 or receipt.get("camera") not in {
            "Overview",
            "A4CloseUp",
        }:
            raise ValueError("Unsupported screenshot receipt")
        audit = audits.get(receipt["push_id"])
        if not audit or any(
            audit[key] != receipt[key] for key in ("run_id", "scenario", "step", "usd_path")
        ):
            raise ValueError("Screenshot receipt does not match a governed scene push")
        png = receipt_path.parent / "frame.png"
        payload = png.read_bytes()
        if hashlib.sha256(payload).hexdigest() != receipt["sha256"]:
            raise ValueError("Screenshot checksum differs from its receipt")
        if png_dimensions(payload) != (receipt["width"], receipt["height"]):
            raise ValueError("Screenshot dimensions differ from its receipt")
        with Image.open(png) as image:
            image.verify()
        if audit["capture_path"]:
            committed = Path(audit["capture_path"]).with_name("receipt.json")
            previous = json.loads(committed.read_text())
            if previous["captured_at"] >= receipt["captured_at"]:
                skipped += 1
                continue
        relative = (
            f"captures/{receipt['run_id']}/{receipt['push_id']}/"
            f"{receipt['camera']}/{receipt['sha256']}/frame.png"
        )
        stored = transport.publish(relative, payload)
        transport.publish(str(Path(relative).with_name("receipt.json")), receipt_path.read_bytes())
        prefix = f"scene/runs/{receipt['run_id']}/{receipt['push_id']}"
        immutable = prefix + f"/captures/{receipt['camera']}/{receipt['sha256']}"
        c.log_artifact(receipt["run_id"], str(stored), immutable)
        c.log_dict(receipt["run_id"], receipt, immutable + "/receipt.json")
        with tempfile.TemporaryDirectory() as temporary:
            alias = Path(temporary) / "viewport.png"
            alias.write_bytes(payload)
            c.log_artifact(receipt["run_id"], str(alias), prefix)
        c.log_dict(receipt["run_id"], receipt, prefix + "/viewport_receipt.json")
        updated[audit["push_id"]] = (
            audit["push_id"],
            audit["ts"],
            audit["run_id"],
            audit["n_prims"],
            audit["usd_path"],
            audit["scenario"],
            audit["step"],
            audit["preview_path"],
            str(stored),
        )
        count += 1
        if count % 20 == 0:
            logging.getLogger(__name__).info("CAPTURE_INGEST_PROGRESS frames=%d", count)
    if not updated and not skipped:
        raise ValueError("No matching captured publications found")
    merge_rows(
        platform, "scene_pushes", list(updated.values()), PUSH_SCHEMA, ["push_id"], update=True
    )
    return {"captures": count, "skipped": skipped, "publications": len(updated), "run_ids": run_ids}


def validate_filming(platform: Any, run_ids: list[str]) -> dict:
    """Retrieve exact per-minute USD/PNG artifacts and verify their UC audit lineage."""
    import logging
    import tempfile

    from airport_twin.scene import digest
    from airport_twin.scene.usd import verify_composition
    from airport_twin.tracking import assert_run, client
    from airport_twin.viewer import load_bundle

    c = client(platform.config)
    table = platform.spark.table(platform.config.table("scene_pushes"))
    audits = {r.push_id: r.asDict() for r in table.where(table.run_id.isin(run_ids)).collect()}
    verified = 0
    for run_id in run_ids:
        run = assert_run(platform.config, run_id)
        bundle = load_bundle(
            Path(c.download_artifacts(run_id, run.data.tags["twin.viewer_artifact"]))
        )
        item = next(row for row in bundle["runs"] if row["run_id"] == run_id)
        with tempfile.TemporaryDirectory() as folder:
            scene = Path(c.download_artifacts(run_id, "scene", folder))
            for frame in item["frames"]:
                push = audits[frame["push"]["push_id"]]
                if (push["run_id"], push["scenario"], push["step"]) != (
                    run_id,
                    item["scenario"],
                    frame["step"],
                ):
                    raise AssertionError("Frame differs from UC scene_pushes")
                if not push["capture_path"]:
                    raise AssertionError("Publication has no actual viewport screenshot")
                directory = scene / "runs" / run_id / push["push_id"]
                manifest = json.loads((directory / "manifest.json").read_text())
                state = directory / f"terminal_state_{run_id}.usda"
                if digest(state.read_bytes()) != manifest["state_sha256"]:
                    raise AssertionError("Retrieved USD checksum differs")
                verify_composition(state, frame["states"])
                receipt = json.loads((directory / "viewport_receipt.json").read_text())
                if any(
                    receipt[key] != push[key]
                    for key in ("run_id", "push_id", "scenario", "step", "usd_path")
                ):
                    raise AssertionError("Screenshot is attached to a different push")
                png = (directory / "viewport.png").read_bytes()
                if (
                    digest(png) != receipt["sha256"]
                    or Path(push["capture_path"]).read_bytes() != png
                ):
                    raise AssertionError("Volume/MLflow screenshot mismatch")
                if png_dimensions(png) != (receipt["width"], receipt["height"]):
                    raise AssertionError("Retrieved screenshot dimensions differ")
                if digest((scene / "terminal_base.usda").read_bytes()) != manifest["base_sha256"]:
                    raise AssertionError("Published base checksum changed")
                verified += 1
        logging.getLogger(__name__).info(
            "FILM_ARTIFACTS_OK run_id=%s frames=%d", run_id, len(item["frames"])
        )
    return {"verified_publications": verified, "run_ids": run_ids}
