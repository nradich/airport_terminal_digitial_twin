"""Read-only App adapters. Spark stays in the platform, never in the App."""

from __future__ import annotations

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse

import requests

from airport_twin.config import Config
from airport_twin.queries import build_query

_SQL_WORKERS = ThreadPoolExecutor(max_workers=2)
_SQL_SLOTS = threading.BoundedSemaphore(2)
QUERY_SECONDS = 30


def query_error(error: Exception) -> ReadError:
    """Expose a stable adapter contract without leaking SQL/auth exception text."""
    message = str(error).upper()
    if any(
        code in message
        for code in (
            "DELTA_VERSION_NOT_FOUND",
            "DELTA_CANNOT_TIME_TRAVEL_VERSION",
            "DELTA_FILE_NOT_FOUND",
            "FILE_NOT_EXIST",
            "DELTA_MISSING_PART_FILES",
            "DELTA_TRUNCATED_TRANSACTION_LOG",
            "DELTA_MISSING_TRANSACTION_LOG",
        )
    ):
        return ReadError("AUDIT_VERSION_UNAVAILABLE", status=410)
    return ReadError("QUERY_FAILED", status=502)


def bounded_rows(rows: list[dict]) -> list[dict]:
    if (
        len(rows) > 5000
        or len(json.dumps(rows, default=lambda value: value.isoformat(), allow_nan=False).encode())
        > 2 * 1024 * 1024
    ):
        raise ReadError("READ_LIMIT_EXCEEDED", status=422)
    return rows


class ReadError(Exception):
    def __init__(self, code: str, message: str = "", status: int = 502) -> None:
        self.code, self.status = code, status
        super().__init__(message or code)


class SqlReader(Protocol):
    def read(self, name: str, parameters: dict | None = None) -> list[dict]: ...


class VolumeReader(Protocol):
    def read(self, path: str) -> bytes: ...
    def relative(self, path: str) -> str: ...


class LocalSqlReader:
    def read(self, name: str, parameters: dict | None = None) -> list[dict]:
        deadline, attempt = time.monotonic() + 35, 0
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ReadError("BUSY", "Query capacity unavailable within deadline", 429)
            response = requests.post(
                os.environ["TWIN_QUERY_URL"].rstrip("/") + "/query",
                json={"query": name, "parameters": parameters or {}},
                headers={"Authorization": "Bearer " + os.environ["TWIN_QUERY_TOKEN"]},
                timeout=remaining,
            )
            if response.status_code != 429:
                break
            time.sleep(min(0.1 * 2 ** min(attempt, 4), 1.0, max(0, deadline - time.monotonic())))
            attempt += 1
        body = response.json()
        if not response.ok:
            code = body.get("error", "QUERY_FAILED").split(":", 1)[0]
            raise ReadError(code, json.dumps(body), status=response.status_code)
        return body["rows"]


class DatabricksSqlReader:
    def __init__(self, config: Config) -> None:
        self.config = config

    def read(self, name: str, parameters: dict | None = None) -> list[dict]:
        query = build_query(name, parameters or {}, self.config)
        if not _SQL_SLOTS.acquire(blocking=False):
            raise ReadError("BUSY", status=429)
        holder = {}
        future = _SQL_WORKERS.submit(self._execute, query, holder)
        future.add_done_callback(lambda _: _SQL_SLOTS.release())
        try:
            return future.result(timeout=QUERY_SECONDS)
        except TimeoutError as error:
            cursor = holder.get("cursor")
            if cursor is not None:
                threading.Thread(target=self._cancel, args=(cursor,), daemon=True).start()
            raise ReadError("QUERY_TIMEOUT", status=504) from error
        except ReadError:
            raise
        except Exception as error:
            raise query_error(error) from error

    @staticmethod
    def _cancel(cursor) -> None:
        try:
            cursor.cancel()
        except Exception:
            pass  # The deadline response is already returned; worker still owns its slot.

    def _execute(self, query, holder: dict) -> list[dict]:
        from databricks import sql
        from databricks.sdk.core import Config as SdkConfig
        from databricks.sdk.core import oauth_service_principal

        cfg = SdkConfig()
        with sql.connect(
            server_hostname=cfg.host.removeprefix("https://"),
            http_path="/sql/1.0/warehouses/" + os.environ["TWIN_WAREHOUSE_ID"],
            credentials_provider=lambda: oauth_service_principal(cfg),
        ) as connection:
            with connection.cursor() as cursor:
                holder["cursor"] = cursor
                cursor.execute(query.sql, parameters=query.parameters)
                rows = cursor.fetchmany(5001)
                columns = [entry[0] for entry in cursor.description]
                return bounded_rows([dict(zip(columns, row, strict=True)) for row in rows])


class LocalVolumeReader:
    def __init__(self, config: Config) -> None:
        response = requests.get(
            os.environ["UNITY_CATALOG_URL"].rstrip("/")
            + "/volumes/"
            + config.namespace
            + ".scenes",
            timeout=15,
        )
        response.raise_for_status()
        uri = urlparse(response.json()["storage_location"])
        if uri.scheme != "file":
            raise ValueError("Local Volume must resolve to the platform's file mount")
        self.root = Path(uri.path).resolve()
        if not self.root.is_relative_to(Path("/data")):
            raise ValueError("Local Volume is outside platform storage")

    def relative(self, path: str) -> str:
        value = Path(path)
        resolved = value.resolve() if value.is_absolute() else (self.root / value).resolve()
        if resolved == self.root or not resolved.is_relative_to(self.root):
            raise ValueError("File is outside scenes Volume")
        return resolved.relative_to(self.root).as_posix()

    def read(self, path: str) -> bytes:
        return (self.root / self.relative(path)).read_bytes()


class DatabricksVolumeReader:
    def __init__(self, config: Config) -> None:
        from databricks.sdk import WorkspaceClient

        self.workspace = WorkspaceClient()
        self.root = f"/Volumes/{config.catalog}/{config.schema}/scenes/"

    def relative(self, path: str) -> str:
        path = path.removeprefix(self.root)
        if path.startswith("/") or ".." in Path(path).parts:
            raise ValueError("File is outside scenes Volume")
        return path

    def read(self, path: str) -> bytes:
        response = self.workspace.files.download(self.root + self.relative(path))
        with response.contents as stream:
            return stream.read()
