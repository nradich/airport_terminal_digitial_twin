import runpy
from pathlib import Path


def test_cli_unicode_patterns_accept_names_and_reject_paths():
    module = runpy.run_path(
        str(Path(__file__).resolve().parents[1] / "scripts/check_bundle_schema.py")
    )
    pattern = r"^[\p{L}\p{N}_-]+$"
    validate = module["unicode_pattern"]
    assert list(validate(None, pattern, "airport-A4", {})) == []
    assert list(validate(None, pattern, "../airport", {}))
