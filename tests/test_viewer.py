import os

import pytest

from airport_twin.viewer import write_cache_file


def test_export_preserves_open_layers_and_local_usd_edits(tmp_path):
    path = tmp_path / "scene" / "terminal_base.usda"
    write_cache_file(path, b"published geometry", immutable=True)
    fixed = 1_700_000_000_000_000_000
    os.utime(path, ns=(fixed, fixed))
    original_mtime = path.stat().st_mtime_ns
    write_cache_file(path, b"published geometry", immutable=True)
    assert path.stat().st_mtime_ns == original_mtime
    path.write_bytes(b"local modeling edits")
    with pytest.raises(ValueError, match="fresh directory"):
        write_cache_file(path, b"published geometry", immutable=True)
    assert path.read_bytes() == b"local modeling edits"
