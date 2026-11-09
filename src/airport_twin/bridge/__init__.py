"""Scene transport contracts; the Volume implementation is the v1 transport."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Protocol
from uuid import uuid4


class Transport(Protocol):
    def publish(self, relative_path: str, payload: bytes) -> Path: ...


class UsdVolumeTransport:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def publish(self, relative_path: str, payload: bytes) -> Path:
        path = (self.root / relative_path).resolve()
        if not path.is_relative_to(self.root) or path == self.root:
            raise ValueError("Publication must remain inside the scenes Volume")
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if path.read_bytes() != payload:
                raise FileExistsError(f"Immutable publication differs: {path}")
            return path
        temporary = path.with_name(path.name + ".pending-" + uuid4().hex)
        try:
            temporary.write_bytes(payload)
            if temporary.read_bytes() != payload:
                raise OSError("Staged publication failed verification")
            if path.exists():
                if path.read_bytes() != payload:
                    raise FileExistsError(path)
            else:
                temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
        if hashlib.sha256(path.read_bytes()).digest() != hashlib.sha256(payload).digest():
            raise OSError("Published payload checksum mismatch")
        return path


class KitMessageTransport:
    def publish(self, relative_path: str, payload: bytes) -> Path:
        raise NotImplementedError("Kit livestream set_colours transport is deferred to M5")
