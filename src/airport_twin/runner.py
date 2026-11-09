"""Execute canonical Databricks source cells through the real local notebook kernel."""

from __future__ import annotations

import ast
import json
import logging
import re
from pathlib import Path

LOG = logging.getLogger(__name__)


def execute(notebooks: list[Path], params: dict) -> dict:
    from jupyter_client import KernelManager

    km = KernelManager()
    km.start_kernel()
    kc = km.client()
    kc.start_channels()
    result = {}
    try:
        kc.wait_for_ready(timeout=120)
        initial = [
            "import logging; logging.basicConfig(level=logging.INFO)",
            "twin_params = " + repr(params),
        ]

        def execute_cell(cell: str, expressions: dict | None = None) -> dict:
            if not cell.strip():
                return {}
            msg_id = kc.execute(cell, user_expressions=expressions or {})
            error = None
            while True:
                msg = kc.get_iopub_msg(timeout=180)
                if msg.get("parent_header", {}).get("msg_id") != msg_id:
                    continue
                if msg["msg_type"] == "stream":
                    output = msg["content"]["text"].strip()
                    LOG.info("%s", output)
                if msg["msg_type"] == "error":
                    error = "\n".join(msg["content"]["traceback"])
                if msg["msg_type"] == "status" and msg["content"]["execution_state"] == "idle":
                    break
            while True:
                reply = kc.get_shell_msg(timeout=180)
                if reply.get("parent_header", {}).get("msg_id") == msg_id:
                    break
            if error or reply["content"]["status"] == "error":
                raise RuntimeError(error)
            return reply["content"]

        for cell in initial:
            execute_cell(cell)
        for path in notebooks:
            LOG.info("NOTEBOOK_START %s", path.name)
            for cell in re.split(
                r"(?m)^# COMMAND ----------\s*$", path.read_text(encoding="utf-8")
            ):
                execute_cell(cell)
            LOG.info("NOTEBOOK_DONE %s", path.name)
        reply = execute_cell("import json", {"result": "json.dumps(twin_params)"})
        expression = reply["user_expressions"]["result"]
        if expression["status"] != "ok":
            raise RuntimeError("Notebook result serialization failed")
        result = json.loads(ast.literal_eval(expression["data"]["text/plain"]))
    finally:
        kc.stop_channels()
        km.shutdown_kernel(now=True)
    return result
