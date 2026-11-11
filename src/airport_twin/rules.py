"""Frozen governed SQL identity. Caller-supplied SQL is never executed."""

from __future__ import annotations

import hashlib
import json

from airport_twin.data import sql_text


def rule_snapshot() -> dict:
    templates = {
        name: sql_text(name)
        for name in ("latest_state.sql", "gate_health.sql", "colour.sql", "status_colour.sql")
    }
    payload = json.dumps(templates, sort_keys=True, separators=(",", ":")).encode()
    return {
        "rule_id": hashlib.sha256(payload).hexdigest(),
        "templates": templates,
        "replay_mode": "canonical_sql_replay",
        "version": 1,
    }
