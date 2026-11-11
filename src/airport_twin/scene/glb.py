"""Deterministic neutral glTF 2 binary geometry; only standard-library dependencies."""

from __future__ import annotations

import json
import math
import struct

from airport_twin.layout import FLOOR, shape


def mesh_data(cylinder: bool) -> tuple[list, list, list]:
    positions, normals, indices = [], [], []

    def face(points: list, directions: list) -> None:
        start = len(positions)
        positions.extend(points)
        normals.extend(directions)
        indices.extend([start, start + 1, start + 2])
        if len(points) == 4:
            indices.extend([start, start + 2, start + 3])

    if cylinder:
        for i in range(32):
            a, b = 2 * math.pi * i / 32, 2 * math.pi * (i + 1) / 32
            x, y, u, v = math.cos(a), math.sin(a), math.cos(b), math.sin(b)
            face(
                [
                    (x / 2, y / 2, -0.5),
                    (u / 2, v / 2, -0.5),
                    (u / 2, v / 2, 0.5),
                    (x / 2, y / 2, 0.5),
                ],
                [(x, y, 0), (u, v, 0), (u, v, 0), (x, y, 0)],
            )
            face([(0, 0, 0.5), (x / 2, y / 2, 0.5), (u / 2, v / 2, 0.5)], [(0, 0, 1)] * 3)
            face([(0, 0, -0.5), (u / 2, v / 2, -0.5), (x / 2, y / 2, -0.5)], [(0, 0, -1)] * 3)
    else:
        for axis in range(3):
            for sign in (-1, 1):
                normal = [0, 0, 0]
                normal[axis] = sign
                first, second = (axis + 1) % 3, (axis + 2) % 3
                points = []
                for a, b in [(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)]:
                    point = [0, 0, 0]
                    point[axis], point[first], point[second] = sign / 2, a, b * sign
                    points.append(point)
                face(points, [normal] * 4)
    return positions, normals, indices


def glb_bytes(assets: list[dict]) -> bytes:
    """Export stable asset-id nodes in metres, with a Z-up to Y-up root transform."""
    if len({a["asset_id"] for a in assets}) != len(assets):
        raise ValueError("Duplicate GLB asset IDs")
    document = {
        "asset": {"version": "2.0", "generator": "airport-twin/glb-v1"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [
            {
                "name": "USD_Z_UP_TO_GLTF_Y_UP",
                "rotation": [-math.sqrt(0.5), 0, 0, math.sqrt(0.5)],
                "children": list(range(1, len(assets) + 2)),
            }
        ],
        "meshes": [],
        "materials": [],
        "bufferViews": [],
        "accessors": [],
    }
    binary = bytearray()

    def accessor(values: list, kind: str, component: int, target: int) -> int:
        while len(binary) % 4:
            binary.append(0)
        offset = len(binary)
        flat = [item for row in values for item in row] if kind == "VEC3" else values
        binary.extend(struct.pack("<" + ("f" if component == 5126 else "H") * len(flat), *flat))
        view = len(document["bufferViews"])
        document["bufferViews"].append(
            {
                "buffer": 0,
                "byteOffset": offset,
                "byteLength": len(binary) - offset,
                "target": target,
            }
        )
        result = {
            "bufferView": view,
            "componentType": component,
            "count": len(values),
            "type": kind,
        }
        if kind == "VEC3":
            result["min"] = [min(row[i] for row in values) for i in range(3)]
            result["max"] = [max(row[i] for row in values) for i in range(3)]
        document["accessors"].append(result)
        return len(document["accessors"]) - 1

    items = [(a, shape(a)) for a in sorted(assets, key=lambda a: a["asset_id"])]
    items.append(({"asset_id": "CONCOURSE_FLOOR"}, FLOOR))
    for index, (asset, layout) in enumerate(items):
        positions, normals, indices = mesh_data(layout.cylinder)
        p = accessor(positions, "VEC3", 5126, 34962)
        n = accessor(normals, "VEC3", 5126, 34962)
        ix = accessor(indices, "SCALAR", 5123, 34963)
        document["materials"].append(
            {
                "name": asset["asset_id"],
                "pbrMetallicRoughness": {
                    "baseColorFactor": [0.3, 0.3, 0.3, 1]
                    if index < len(assets)
                    else [0.12, 0.15, 0.19, 1],
                    "metallicFactor": 0,
                    "roughnessFactor": 0.8,
                },
            }
        )
        document["meshes"].append(
            {
                "primitives": [
                    {"attributes": {"POSITION": p, "NORMAL": n}, "indices": ix, "material": index}
                ]
            }
        )
        document["nodes"].append(
            {
                "name": asset["asset_id"],
                "mesh": index,
                "translation": layout.position,
                "scale": layout.size,
                "extras": {k: asset[k] for k in ("asset_id", "prim_path") if k in asset},
            }
        )
    document["buffers"] = [{"byteLength": len(binary)}]
    encoded = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    encoded += b" " * (-len(encoded) % 4)
    binary.extend(b"\0" * (-len(binary) % 4))
    return (
        struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(encoded) + 8 + len(binary))
        + struct.pack("<II", len(encoded), 0x4E4F534A)
        + encoded
        + struct.pack("<II", len(binary), 0x004E4942)
        + binary
    )
