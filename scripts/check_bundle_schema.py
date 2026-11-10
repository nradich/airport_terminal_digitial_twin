"""Offline schema check against the real CLI schema; not workspace validation."""

from __future__ import annotations

import argparse
import copy
import json
import logging
from pathlib import Path

import jsonschema
import regex
import yaml


def merge(left: dict, right: dict) -> dict:
    for key, value in right.items():
        if isinstance(value, dict) and isinstance(left.get(key), dict):
            merge(left[key], value)
        else:
            left[key] = copy.deepcopy(value)
    return left


def unicode_pattern(_validator, pattern: str, instance, _schema):
    """CLI schema uses Unicode properties that Python's stdlib re cannot parse."""
    if isinstance(instance, str) and regex.search(pattern, instance) is None:
        yield jsonschema.ValidationError(f"{instance!r} does not match {pattern!r}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("schema", type=Path)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    config = yaml.safe_load(Path("databricks.yml").read_text())
    for pattern in config.get("include", []):
        for path in Path.cwd().glob(pattern):
            merge(config, yaml.safe_load(path.read_text()))
    schema = json.loads(args.schema.read_text(encoding="utf-8-sig"))
    validator_type = jsonschema.validators.extend(
        jsonschema.validators.validator_for(schema), {"pattern": unicode_pattern}
    )
    validator = validator_type(schema)
    errors = sorted(validator.iter_errors(config), key=lambda e: str(e.path))
    if errors:
        raise ValueError("\n".join(f"{list(e.path)}: {e.message}" for e in errors))
    logging.info(
        "BUNDLE_SCHEMA_OK targets=%s (workspace execution UNTESTED)", ",".join(config["targets"])
    )


if __name__ == "__main__":
    main()
