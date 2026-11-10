"""Governed application reads shared by all web routes."""

from __future__ import annotations

import hashlib
import json

from airport_twin.config import Config
from airport_twin.layout import CAMERAS
from airport_twin.presentation import asset_labels, legend_data
from airport_twin.readers import ReadError, SqlReader, VolumeReader
from airport_twin.tracking import assert_run, run_url


class TwinData:
    def __init__(self, config: Config, sql: SqlReader, volume: VolumeReader) -> None:
        self.config, self.sql, self.volume = config, sql, volume

    def runs(self) -> list[dict]:
        result = {}
        for push in self.sql.read("pushes"):
            if push["run_id"] not in result:
                run = assert_run(self.config, push["run_id"])
                result[push["run_id"]] = {
                    "run_id": push["run_id"],
                    "scenario": push["scenario"],
                    "run_name": run.data.tags.get("mlflow.runName", push["run_id"]),
                    "minutes": int(run.data.params["minutes"]),
                    "push_id": push["push_id"],
                    "run_url": run_url(self.config, push["run_id"]),
                }
        return list(result.values())

    def publication(self, push_id: str) -> dict:
        rows = [row for row in self.sql.read("pushes") if row["push_id"] == push_id]
        if len(rows) != 1:
            raise ReadError("PUBLICATION_NOT_FOUND", status=404)
        audit = rows[0]
        relative = self.volume.relative(audit["usd_path"])
        manifest_path = relative.rsplit("/", 1)[0] + "/manifest.json"
        manifest = json.loads(self.volume.read(manifest_path))
        if any(
            audit[key] != manifest[key]
            for key in ("push_id", "run_id", "step", "scenario", "glb_path", "glb_sha256")
        ):
            raise ReadError("PUBLICATION_MISMATCH", status=409)
        return {
            "audit": audit,
            "manifest": manifest,
            "labels": asset_labels(manifest["assets"]),
            "cameras": CAMERAS,
            "legend": legend_data(
                [tuple(row) for row in manifest["thresholds"]], self.sql.read("palette")
            ),
            "image_type": "Renderer capture" if audit["capture_path"] else "Heatmap preview",
        }

    def model(self, push_id: str) -> bytes:
        publication = self.publication(push_id)
        manifest = publication["manifest"]
        payload = self.volume.read(manifest["glb_path"])
        if hashlib.sha256(payload).hexdigest() != manifest["glb_sha256"]:
            raise ReadError("GLB_CHECKSUM_MISMATCH", status=409)
        return payload

    def frame(self, push_id: str) -> bytes:
        publication = self.publication(push_id)
        audit, manifest = publication["audit"], publication["manifest"]
        path = audit["capture_path"] or audit["preview_path"]
        payload = self.volume.read(path)
        if audit["capture_path"]:
            receipt = json.loads(
                self.volume.read(self.volume.relative(path).rsplit("/", 1)[0] + "/receipt.json")
            )
            if any(receipt[key] != audit[key] for key in ("push_id", "run_id", "step", "scenario")):
                raise ReadError("CAPTURE_LINEAGE_MISMATCH", status=409)
            checksum = receipt["sha256"]
        else:
            checksum = manifest["preview_sha256"]
        if hashlib.sha256(payload).hexdigest() != checksum:
            raise ReadError("PNG_CHECKSUM_MISMATCH", status=409)
        return payload

    def current(self, run_id: str) -> list[dict]:
        assert_run(self.config, run_id)
        rows = self.sql.read("current", {"run_id": run_id})
        if len(rows) != 10 or len({r["asset_id"] for r in rows}) != 10:
            raise ReadError("INCOMPLETE_CURRENT_STATE", status=409)
        return rows
