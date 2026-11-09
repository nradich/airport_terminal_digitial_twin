"""Execute canonical Databricks source cells through the real local notebook kernel."""

from __future__ import annotations

import json
import logging
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
        cells = [
            "import logging; logging.basicConfig(level=logging.INFO)",
            "twin_params = " + repr(params),
        ]
        for path in notebooks:
            LOG.info("NOTEBOOK_START %s", path.name)
            cells.extend(path.read_text(encoding="utf-8").split("# COMMAND ----------"))
        cells.append("import json; print('TWIN_RESULT=' + json.dumps(twin_params))")
        for cell in cells:
            if not cell.strip():
                continue
            msg_id = kc.execute(cell)
            error = None
            while True:
                msg = kc.get_iopub_msg(timeout=180)
                if msg.get("parent_header", {}).get("msg_id") != msg_id:
                    continue
                if msg["msg_type"] == "stream":
                    output = msg["content"]["text"].strip()
                    if "TWIN_RESULT=" in output:
                        result = json.loads(output.split("TWIN_RESULT=", 1)[1])
                    else:
                        LOG.info("%s", output)
                if msg["msg_type"] == "error":
                    error = "\n".join(msg["content"]["traceback"])
                if msg["msg_type"] == "status" and msg["content"]["execution_state"] == "idle":
                    break
            if error:
                raise RuntimeError(error)
    finally:
        kc.stop_channels()
        km.shutdown_kernel(now=True)
    return result
