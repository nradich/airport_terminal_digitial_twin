"""Simple OpenUSD geometry and non-destructive colour overrides."""

from __future__ import annotations

from pathlib import Path

from pxr import Gf, Sdf, Usd, UsdGeom

from airport_twin.scene.layout import shape


def linear_rgb(colour: str) -> tuple[float, float, float]:
    if len(colour) != 7 or not colour.startswith("#"):
        raise ValueError("Expected #RRGGBB colour")
    values = [int(colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in values)


def base_bytes(assets: list[dict]) -> bytes:
    stage = Usd.Stage.CreateInMemory()
    world = UsdGeom.Xform.Define(stage, "/World")
    UsdGeom.Xform.Define(stage, "/World/Concourse_A")
    stage.SetDefaultPrim(world.GetPrim())
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    floor = UsdGeom.Cube.Define(stage, "/World/Concourse_A/Floor")
    floor.CreateSizeAttr(1.0)
    floor.AddTranslateOp().Set((21.0, 0.0, -0.25))
    floor.AddScaleOp().Set((60.0, 15.0, 0.5))
    floor.CreateDisplayColorAttr([Gf.Vec3f(0.12, 0.15, 0.19)])
    seen = set()
    for asset in sorted(assets, key=lambda a: a["asset_id"]):
        path = asset["prim_path"]
        if path in seen or not Sdf.Path(path).IsPrimPath() or not path.startswith("/World/"):
            raise ValueError(f"Invalid or duplicate asset prim path: {path}")
        seen.add(path)
        layout = shape(asset)
        if layout.cylinder:
            geom = UsdGeom.Cylinder.Define(stage, path)
            geom.CreateRadiusAttr(layout.size[0] / 2)
            geom.CreateHeightAttr(layout.size[2])
            geom.CreateAxisAttr(UsdGeom.Tokens.z)
        else:
            geom = UsdGeom.Cube.Define(stage, path)
            geom.CreateSizeAttr(1.0)
            geom.AddScaleOp().Set(layout.size)
        geom.AddTranslateOp().Set(layout.position)
        # Put translation before scale so world-space positions are not scaled.
        ops = geom.GetOrderedXformOps()
        geom.SetXformOpOrder(sorted(ops, key=lambda op: "translate" not in op.GetOpName()))
        geom.CreateDisplayColorAttr([Gf.Vec3f(0.3, 0.3, 0.3)])
        geom.GetPrim().CreateAttribute("twin:asset_id", Sdf.ValueTypeNames.String).Set(
            asset["asset_id"]
        )
        geom.GetPrim().SetDisplayName(asset["display_name"])
    return stage.GetRootLayer().ExportToString().encode("utf-8")


def override_bytes(states: list[dict], metadata: dict[str, str]) -> bytes:
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    for state in sorted(states, key=lambda s: s["prim_path"]):
        prim = stage.OverridePrim(state["prim_path"])
        UsdGeom.Gprim(prim).CreateDisplayColorAttr([Gf.Vec3f(*linear_rgb(state["colour"]))])
        prim.CreateAttribute("twin:status", Sdf.ValueTypeNames.String).Set(state["status"])
    # Add the relative reference on an unbound layer: no anonymous-stage resolution warnings.
    layer = Sdf.Layer.CreateAnonymous(".usda")
    layer.TransferContent(stage.GetRootLayer())
    layer.customLayerData = metadata
    # Each publication lives at runs/<run>/<push>/, three levels below the base.
    layer.subLayerPaths = ["../../../terminal_base.usda"]
    return layer.ExportToString().encode("utf-8")


def verify_composition(path: Path, states: list[dict]) -> None:
    stage = Usd.Stage.Open(str(path))
    if not stage:
        raise AssertionError("USD stage failed to open")
    for state in states:
        prim = stage.GetPrimAtPath(state["prim_path"])
        if not prim or not prim.IsA(UsdGeom.Gprim):
            raise AssertionError(f"Missing geometry at {state['prim_path']}")
        actual = UsdGeom.Gprim(prim).GetDisplayColorAttr().Get()[0]
        expected = linear_rgb(state["colour"])
        if any(abs(a - b) > 1e-6 for a, b in zip(actual, expected, strict=True)):
            raise AssertionError(f"Wrong composed colour at {state['prim_path']}")
