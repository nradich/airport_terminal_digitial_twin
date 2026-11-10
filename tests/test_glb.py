import json
import math
import struct

from airport_twin.data import ASSETS
from airport_twin.layout import shape
from airport_twin.scene.glb import glb_bytes


def test_glb_geometry_mapping_and_neutral_materials():
    assets = [
        dict(zip(("asset_id", "asset_type", "zone", "prim_path", "display_name"), row, strict=True))
        for row in ASSETS
    ]
    payload = glb_bytes(assets)
    assert payload == glb_bytes(list(reversed(assets)))
    magic, version, length = struct.unpack_from("<III", payload)
    assert (magic, version, length) == (0x46546C67, 2, len(payload))
    n, kind = struct.unpack_from("<II", payload, 12)
    assert kind == 0x4E4F534A
    doc = json.loads(payload[20 : 20 + n])
    assert len(payload) < 1024 * 1024
    assert doc["nodes"][0]["rotation"] == [-math.sqrt(0.5), 0, 0, math.sqrt(0.5)]
    nodes = {node["name"]: node for node in doc["nodes"][1:]}
    assert set(nodes) == {a["asset_id"] for a in assets} | {"CONCOURSE_FLOOR"}
    for asset in assets:
        node = nodes[asset["asset_id"]]
        assert node["translation"] == list(shape(asset).position)
        assert node["scale"] == list(shape(asset).size)
        assert node["extras"]["prim_path"] == asset["prim_path"]
    assert len({doc["meshes"][i]["primitives"][0]["material"] for i in range(10)}) == 10
    assert all(
        m["pbrMetallicRoughness"]["baseColorFactor"] == [0.3, 0.3, 0.3, 1]
        for m in doc["materials"][:10]
    )
