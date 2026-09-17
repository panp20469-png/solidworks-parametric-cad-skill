# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import math
import sys
import traceback
from pathlib import Path
from typing import Any

import pythoncom
import win32gui
import win32process


ROOT = Path(__file__).resolve().parents[1]
TASK_DIR = Path(__file__).resolve().parent
SERVER_DIR = ROOT / "external_sources" / "Solidworks-MCP-Server"
if not SERVER_DIR.exists():
    raise RuntimeError("缺少随示例提供的 COM 客户端，请保留 examples/elbow 的目录结构。")
sys.path.insert(0, str(TASK_DIR))
sys.path.insert(0, str(SERVER_DIR))

from win32com.client import VARIANT
from sw_client import SolidWorksClient, _m, _get, _invoke, _resolve_dispid  # noqa: E402
from validate_elbow_v10_contract import SpecContract, validate_spec  # noqa: E402


SPEC_PATH = TASK_DIR / "elbow_v10_spec.json"
OUT_DIR = TASK_DIR / "output"
OUT_SLDPRT = OUT_DIR / "elbow_436_v10_spec.SLDPRT"
OUT_LOG = OUT_DIR / "elbow_436_v10_spec.log.json"


class TargetClient(SolidWorksClient):
    """每次模型操作都核对目标文档，连接失败时不进入保存流程。"""

    target_title = None

    def _active_doc(self):
        doc = super()._active_doc()
        if self.target_title is not None and _get(doc, "GetTitle") != self.target_title:
            raise RuntimeError("当前文档已切换，停止操作以保护其它零件。")
        return doc


def verify_visible_instance(sw: SolidWorksClient) -> int:
    pid = int(_get(sw._app, "GetProcessID"))
    windows = []

    def visit(hwnd, _):
        if win32gui.IsWindowVisible(hwnd) and win32process.GetWindowThreadProcessId(hwnd)[1] == pid:
            windows.append(hwnd)

    win32gui.EnumWindows(visit, None)
    if not windows:
        raise RuntimeError("连接到的 SW 没有可见窗口，请先手动打开 SW；不会强制显示后台实例。")
    return pid


def unit(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    length = math.sqrt(sum(value * value for value in vector))
    if length <= 0:
        raise ValueError("zero vector")
    return tuple(value / length for value in vector)  # type: ignore[return-value]


def add(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def mul(vector: tuple[float, float, float], scalar: float) -> tuple[float, float, float]:
    return (vector[0] * scalar, vector[1] * scalar, vector[2] * scalar)


def dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return sum(left * right for left, right in zip(a, b))


def cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def as_point3(values: list[float] | tuple[float, ...]) -> tuple[float, float, float]:
    if len(values) == 2:
        return (float(values[0]), float(values[1]), 0.0)
    return (float(values[0]), float(values[1]), float(values[2]))


def latest_sketch(sw: SolidWorksClient) -> str:
    return sw._latest_sketch_name()


def select_sketch(sw: SolidWorksClient, sketch_name: str) -> None:
    sw.clear_selection()
    sw.select_entity(sketch_name, "SKETCH")


def extrude_sketch(
    sw: SolidWorksClient,
    sketch_name: str,
    depth: float,
    *,
    is_cut: bool = False,
    direction: str = "blind",
    flip: bool = False,
) -> str:
    select_sketch(sw, sketch_name)
    return sw.extrude(depth, direction=direction, flip_direction=flip, is_cut=is_cut)["feature"]


def create_3d_line_path(
    sw: SolidWorksClient,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
) -> str:
    doc = sw._active_doc()
    doc.ClearSelection2(True)
    sketch_manager = doc.SketchManager
    sketch_manager.Insert3DSketch(True)
    segment = sketch_manager.CreateLine(
        _m(start[0]),
        _m(start[1]),
        _m(start[2]),
        _m(end[0]),
        _m(end[1]),
        _m(end[2]),
    )
    if segment is None:
        raise RuntimeError("Create 3D line path failed.")
    sketch_manager.Insert3DSketch(True)
    return latest_sketch(sw)


def sweep_cylinder(
    sw: SolidWorksClient,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    diameter: float,
    *,
    is_cut: bool = False,
    merge_result: bool = True,
) -> str:
    path = create_3d_line_path(sw, start, end)
    return sw.sweep_circular_profile_by_path(
        path_sketch=path,
        diameter=diameter,
        is_cut=is_cut,
        merge_result=merge_result,
    )["feature"]


def segment_about(
    center: tuple[float, float, float],
    axis: tuple[float, float, float],
    length: float,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    axis_u = unit(axis)
    half = length / 2.0
    return add(center, mul(axis_u, -half)), add(center, mul(axis_u, half))


def create_centered_cylinder(
    sw: SolidWorksClient,
    center: tuple[float, float, float],
    axis: tuple[float, float, float],
    length: float,
    diameter: float,
    *,
    is_cut: bool = False,
) -> str:
    start, end = segment_about(center, axis, length)
    return sweep_cylinder(sw, start, end, diameter, is_cut=is_cut)


ProfileSegment = tuple[str, tuple[Any, ...]]


def point_on_circle(center: tuple[float, float], radius: float, angle_deg: float) -> tuple[float, float]:
    angle = math.radians(angle_deg)
    return (center[0] + radius * math.cos(angle), center[1] + radius * math.sin(angle))


def local_to_world(
    origin: tuple[float, float, float],
    local_x: tuple[float, float, float],
    local_y: tuple[float, float, float],
    point: tuple[float, float],
) -> tuple[float, float, float]:
    return add(origin, add(mul(local_x, point[0]), mul(local_y, point[1])))


def normalized_arc_angles(start_deg: float, end_deg: float, clockwise: bool) -> tuple[float, float]:
    start = float(start_deg)
    end = float(end_deg)
    if clockwise:
        while end >= start:
            end -= 360.0
    else:
        while end <= start:
            end += 360.0
    return start, end


def create_planar_3d_profile(
    sw: SolidWorksClient,
    origin: tuple[float, float, float],
    local_x: tuple[float, float, float],
    local_y: tuple[float, float, float],
    segments: list[ProfileSegment],
) -> str:
    """在显式基准面上构建二维闭合轮廓，不依赖三维草图的推断平面。"""
    doc = sw._active_doc()
    normal = unit(cross(local_x, local_y))
    axis_path = create_3d_line_path(sw, origin, add(origin, mul(normal, 10.0)))
    axis_sketch = _get(doc.FeatureByName(axis_path), "GetSpecificFeature2")
    axis_segment = _get(axis_sketch, "GetSketchSegments")[0]
    doc.ClearSelection2(True)
    selection = _get(doc.SelectionManager, "CreateSelectData")
    if not axis_segment.Select4(False, selection) or not _get(axis_segment, "GetStartPoint2").Select4(True, selection):
        raise RuntimeError("Cannot select profile plane axis/origin")
    plane = doc.CreatePlanePerCurveAndPassPoint3(True, False)
    if plane is None:
        raise RuntimeError("Cannot create profile reference plane")
    doc.ClearSelection2(True)
    if not plane.Select2(False, 0):
        raise RuntimeError("Cannot select profile reference plane")
    sm = doc.SketchManager
    sm.InsertSketch(True)
    sketch = _get(sm, "ActiveSketch")
    transform = _get(sketch, "ModelToSketchTransform")
    math_util = _get(sw._app, "GetMathUtility")

    def to_sketch(point):
        world = local_to_world(origin, local_x, local_y, point)
        mp = _invoke(math_util, _resolve_dispid(math_util, "CreatePoint"), VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, tuple(_m(v) for v in world)))
        mapped = _invoke(mp, _resolve_dispid(mp, "MultiplyTransform"), transform)
        result = tuple(_get(mapped, "ArrayData"))
        if abs(result[2]) > 1e-7:
            raise RuntimeError("Profile point is not on its reference plane")
        return result[0], result[1], 0.0

    o = to_sketch((0, 0)); x = to_sketch((1, 0)); y = to_sketch((0, 1))
    handedness = 1 if (x[0]-o[0])*(y[1]-o[1])-(x[1]-o[1])*(y[0]-o[0]) > 0 else -1
    old_add_to_db = sm.AddToDB
    sm.AddToDB = True
    created_arcs = []
    try:
        for kind, params in segments:
            if kind == "line":
                entity = sm.CreateLine(*(to_sketch(params[0]) + to_sketch(params[1])))
            elif kind == "arc":
                center, radius, start_deg, end_deg, clockwise = params
                start = to_sketch(point_on_circle(center, radius, start_deg))
                end = to_sketch(point_on_circle(center, radius, end_deg))
                direction = handedness * (-1 if clockwise else 1)
                entity = sm.CreateArc(*(to_sketch(center) + start + end + (direction,)))
                if entity is not None:
                    created_arcs.append((entity, radius))
            else:
                raise ValueError(f"Unsupported profile segment: {kind}")
            if entity is None:
                raise RuntimeError(f"Failed to create profile segment: {kind} {params}")
        sm.InsertSketch(True)
    finally:
        sm.AddToDB = old_add_to_db
    for entity, expected_radius in created_arcs:
        actual_radius = float(_get(entity, "GetRadius")) * 1000.0
        if abs(actual_radius - expected_radius) > 0.001:
            raise RuntimeError(f"草图圆弧半径不符：期望 {expected_radius}，实际 {actual_radius}")
    return latest_sketch(sw)


def loft_exact_profile(
    sw: SolidWorksClient,
    start_origin: tuple[float, float, float],
    end_origin: tuple[float, float, float],
    local_x: tuple[float, float, float],
    local_y: tuple[float, float, float],
    segments: list[ProfileSegment],
) -> str:
    start_sketch = create_planar_3d_profile(sw, start_origin, local_x, local_y, segments)
    # 等截面轮廓沿厚度方向扫描，避免两张三维草图放样的选择歧义。
    path = create_3d_line_path(sw, start_origin, end_origin)
    return sw.sweep_by_sketches(start_sketch, path, merge_result=True)["feature"]


def side_flange_profile(center_radius: float, ear_radius: float, hole_pitch: float) -> list[ProfileSegment]:
    half_pitch = hole_pitch / 2.0
    if not 0.0 < center_radius - ear_radius < half_pitch:
        raise ValueError("The R12/R6 C-profile does not admit the required external tangents.")
    theta = math.degrees(math.acos((center_radius - ear_radius) / half_pitch))
    c_tr = point_on_circle((0.0, 0.0), center_radius, theta)
    c_tl = point_on_circle((0.0, 0.0), center_radius, 180.0 - theta)
    c_bl = point_on_circle((0.0, 0.0), center_radius, 180.0 + theta)
    c_br = point_on_circle((0.0, 0.0), center_radius, 360.0 - theta)
    e_tl = point_on_circle((-half_pitch, 0.0), ear_radius, 180.0 - theta)
    e_bl = point_on_circle((-half_pitch, 0.0), ear_radius, 180.0 + theta)
    e_br = point_on_circle((half_pitch, 0.0), ear_radius, 360.0 - theta)
    e_tr = point_on_circle((half_pitch, 0.0), ear_radius, theta)
    return [
        ("arc", ((0.0, 0.0), center_radius, theta, 180.0 - theta, False)),
        ("line", (c_tl, e_tl)),
        ("arc", ((-half_pitch, 0.0), ear_radius, 180.0 - theta, 180.0 + theta, False)),
        ("line", (e_bl, c_bl)),
        ("arc", ((0.0, 0.0), center_radius, 180.0 + theta, 360.0 - theta, False)),
        ("line", (c_br, e_br)),
        ("arc", ((half_pitch, 0.0), ear_radius, 360.0 - theta, 360.0 + theta, False)),
        ("line", (e_tr, c_tr)),
    ]


def top_flange_profile(
    body_radius: float,
    lug_radius: float,
    transition_radius: float,
    pitch_radius: float,
    ear_angles_deg: list[float],
) -> list[ProfileSegment]:
    """Build the D56/R10/R5 three-lug outline as one closed sketch profile."""
    fillet_from_body = body_radius + transition_radius
    fillet_from_lug = lug_radius + transition_radius
    projection = (
        pitch_radius * pitch_radius
        + fillet_from_body * fillet_from_body
        - fillet_from_lug * fillet_from_lug
    ) / (2.0 * pitch_radius)
    ratio = projection / fillet_from_body
    if not -1.0 < ratio < 1.0:
        raise ValueError("The D56/R10/R5 top-flange dimensions do not form a closed filleted profile.")
    beta = math.degrees(math.acos(ratio))
    ears: list[dict[str, Any]] = []
    for angle in sorted(value % 360.0 for value in ear_angles_deg):
        ear_center = point_on_circle((0.0, 0.0), pitch_radius, angle)
        fillet_minus = point_on_circle((0.0, 0.0), fillet_from_body, angle - beta)
        fillet_plus = point_on_circle((0.0, 0.0), fillet_from_body, angle + beta)
        body_minus = point_on_circle((0.0, 0.0), body_radius, angle - beta)
        body_plus = point_on_circle((0.0, 0.0), body_radius, angle + beta)

        def lug_contact(fillet_center: tuple[float, float]) -> tuple[float, float]:
            return (
                ear_center[0] + (fillet_center[0] - ear_center[0]) * lug_radius / fillet_from_lug,
                ear_center[1] + (fillet_center[1] - ear_center[1]) * lug_radius / fillet_from_lug,
            )

        lug_minus = lug_contact(fillet_minus)
        lug_plus = lug_contact(fillet_plus)
        ears.append(
            {
                "angle": angle,
                "ear_center": ear_center,
                "fillet_minus": fillet_minus,
                "fillet_plus": fillet_plus,
                "body_minus": body_minus,
                "body_plus": body_plus,
                "lug_minus": lug_minus,
                "lug_plus": lug_plus,
            }
        )

    segments: list[ProfileSegment] = []
    for index, ear in enumerate(ears):
        next_ear = ears[(index + 1) % len(ears)]

        def angle_about(point: tuple[float, float], center: tuple[float, float]) -> float:
            return math.degrees(math.atan2(point[1] - center[1], point[0] - center[0]))

        fm = ear["fillet_minus"]
        fp = ear["fillet_plus"]
        ec = ear["ear_center"]
        segments.append(
            (
                "arc",
                (
                    fm,
                    transition_radius,
                    angle_about(ear["body_minus"], fm),
                    angle_about(ear["lug_minus"], fm),
                    True,
                ),
            )
        )
        segments.append(
            (
                "arc",
                (
                    ec,
                    lug_radius,
                    angle_about(ear["lug_minus"], ec),
                    angle_about(ear["lug_plus"], ec),
                    False,
                ),
            )
        )
        segments.append(
            (
                "arc",
                (
                    fp,
                    transition_radius,
                    angle_about(ear["lug_plus"], fp),
                    angle_about(ear["body_plus"], fp),
                    True,
                ),
            )
        )
        segments.append(
            (
                "arc",
                (
                    (0.0, 0.0),
                    body_radius,
                    angle_about(ear["body_plus"], (0.0, 0.0)),
                    angle_about(next_ear["body_minus"], (0.0, 0.0)),
                    False,
                ),
            )
        )
    return segments


def make_base(sw: SolidWorksClient, contract: SpecContract, groups: list[str]) -> None:
    width = float(contract.get("base.width"))
    depth = float(contract.get("base.depth"))
    thickness = float(contract.get("base.thickness"))
    radius = float(contract.get("base.corner_radius"))
    half_x = width / 2.0
    half_z = depth / 2.0

    sw.create_sketch("Top Plane")
    sw.sketch_line(-half_x + radius, -half_z, half_x - radius, -half_z)
    sw.sketch_arc(half_x - radius, -half_z + radius, radius, -90.0, 0.0)
    sw.sketch_line(half_x, -half_z + radius, half_x, half_z - radius)
    sw.sketch_arc(half_x - radius, half_z - radius, radius, 0.0, 90.0)
    sw.sketch_line(half_x - radius, half_z, -half_x + radius, half_z)
    sw.sketch_arc(-half_x + radius, half_z - radius, radius, 90.0, 180.0)
    sw.sketch_line(-half_x, half_z - radius, -half_x, -half_z + radius)
    sw.sketch_arc(-half_x + radius, -half_z + radius, radius, 180.0, 270.0)
    sw.exit_sketch()
    extrude_sketch(sw, latest_sketch(sw), thickness)
    groups.append("group_01")

    hole_count = int(contract.get("base.mounting_holes.count"))
    hole_diameter = float(contract.get("base.mounting_holes.diameter"))
    pitch_x = float(contract.get("base.mounting_holes.pitch_x"))
    pitch_z = float(contract.get("base.mounting_holes.pitch_z"))
    if hole_count != 4:
        raise ValueError("The v10 base regression expects four mounting holes.")
    sw.create_sketch("Top Plane")
    for x in (-pitch_x / 2.0, pitch_x / 2.0):
        for z in (-pitch_z / 2.0, pitch_z / 2.0):
            sw.sketch_circle(x, z, hole_diameter / 2.0)
    sw.exit_sketch()
    extrude_sketch(sw, latest_sketch(sw), thickness * 2.0, is_cut=True, direction="through_all")
    groups.append("group_02")


def create_main_path(
    sw: SolidWorksClient,
    start: tuple[float, float],
    arc_center: tuple[float, float],
    radius: float,
    start_angle: float,
    end_angle: float,
    upper_direction: float,
    top_height: float,
) -> tuple[str, tuple[float, float, float], tuple[float, float, float]]:
    p1 = (
        arc_center[0] + radius * math.cos(math.radians(start_angle)),
        arc_center[1] + radius * math.sin(math.radians(start_angle)),
    )
    p2 = (
        arc_center[0] + radius * math.cos(math.radians(end_angle)),
        arc_center[1] + radius * math.sin(math.radians(end_angle)),
    )
    upper_length = (top_height - p2[1]) / math.sin(math.radians(upper_direction))
    p3 = (
        p2[0] + upper_length * math.cos(math.radians(upper_direction)),
        top_height,
    )

    sw.create_sketch("Front Plane")
    sw.sketch_line(start[0], start[1], p1[0], p1[1])
    sw.sketch_arc(arc_center[0], arc_center[1], radius, start_angle, end_angle)
    sw.sketch_line(p2[0], p2[1], p3[0], p3[1])
    sw.exit_sketch()
    tangent = unit((math.cos(math.radians(upper_direction)), math.sin(math.radians(upper_direction)), 0.0))
    return latest_sketch(sw), (p3[0], p3[1], 0.0), tangent


def make_main_tube(
    sw: SolidWorksClient,
    contract: SpecContract,
    groups: list[str],
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    outer_diameter = float(contract.get("main_tube.outer_diameter"))
    inner_diameter = float(contract.get("main_tube.inner_diameter"))
    outer_start = tuple(float(v) for v in contract.get("main_tube.path.outer_start"))
    inner_start = tuple(float(v) for v in contract.get("main_tube.path.inner_start"))
    arc_center = tuple(float(v) for v in contract.get("main_tube.path.arc_center"))
    radius = float(contract.get("main_tube.path.arc_radius"))
    start_angle = float(contract.get("main_tube.path.arc_start_angle_deg"))
    end_angle = float(contract.get("main_tube.path.arc_end_angle_deg"))
    upper_direction = float(contract.get("main_tube.path.upper_direction_deg"))
    top_height = float(contract.get("main_tube.path.top_height"))

    outer_path, top_end, tangent = create_main_path(
        sw, outer_start, arc_center, radius, start_angle, end_angle, upper_direction, top_height
    )
    sw.sweep_circular_profile_by_path(outer_path, outer_diameter, is_cut=False, merge_result=True)

    # 主管内腔在所有外部凸台完成后统一生成，防止后续加料侵入流道。
    groups.append("group_03")
    return top_end, tangent


def make_top_flange(
    sw: SolidWorksClient,
    contract: SpecContract,
    top_end: tuple[float, float, float],
    tangent: tuple[float, float, float],
    groups: list[str],
) -> None:
    thickness = float(contract.get("top_flange.thickness"))
    body_diameter = float(contract.get("top_flange.body_diameter"))
    lug_radius = float(contract.get("top_flange.lug_radius"))
    transition_radius = float(contract.get("top_flange.transition_radius"))
    hole_count = int(contract.get("top_flange.hole_count"))
    hole_diameter = float(contract.get("top_flange.hole_diameter"))
    spacing = float(contract.get("top_flange.angular_spacing_deg"))
    first_angle = float(contract.get("top_flange.first_hole_angle_deg"))
    pitch_radius = float(contract.get("top_flange.pitch_radius"))
    profile_status = str(contract.get("top_flange.profile_status"))
    if profile_status != "user_accepted_existing_outline":
        raise ValueError("Top flange profile status must preserve the user-accepted existing outline.")

    axis = unit(tangent)
    center = add(top_end, mul(axis, thickness / 2.0))
    local_x = (0.0, 0.0, 1.0)
    local_y = unit((-axis[1], axis[0], 0.0))
    ear_angles = [first_angle + index * spacing for index in range(hole_count)]
    profile = top_flange_profile(body_diameter / 2.0, lug_radius, transition_radius, pitch_radius, ear_angles)
    loft_exact_profile(sw, top_end, add(top_end, mul(axis, thickness)), local_x, local_y, profile)

    hole_centers: list[tuple[float, float, float]] = []
    for angle_deg in ear_angles:
        angle = math.radians(angle_deg)
        radial = add(mul(local_x, math.cos(angle) * pitch_radius), mul(local_y, math.sin(angle) * pitch_radius))
        hole_center = add(center, radial)
        hole_centers.append(hole_center)

    create_centered_cylinder(sw, center, axis, thickness + 0.1, float(contract.get("main_tube.inner_diameter")), is_cut=True)
    for hole_center in hole_centers:
        create_centered_cylinder(sw, hole_center, axis, thickness + 0.1, hole_diameter, is_cut=True)
    groups.append("group_04")


def branch_origin_and_overlap(
    contract: SpecContract,
) -> tuple[tuple[float, float, float], tuple[float, float, float], float, float]:
    angle_deg = float(contract.get("side_branch.axis_angle_deg"))
    y = float(contract.get("side_branch.axis_center_height"))
    arc_center = tuple(float(v) for v in contract.get("main_tube.path.arc_center"))
    radius = float(contract.get("main_tube.path.arc_radius"))
    dy = y - arc_center[1]
    if abs(dy) >= radius:
        raise ValueError("Branch center height does not intersect the R35 main path.")
    x = float(contract.get("side_branch.axis_origin_x"))
    origin = (x, y, 0.0)
    axis = unit((math.cos(math.radians(angle_deg)), math.sin(math.radians(angle_deg)), 0.0))

    radial_vector = (x - arc_center[0], y - arc_center[1], 0.0)
    radial_projection = dot(radial_vector, axis)

    def outward_offset_intersection(offset_radius: float) -> float:
        target_radius = radius + offset_radius
        discriminant = radial_projection * radial_projection + target_radius * target_radius - radius * radius
        if discriminant <= 0.0:
            raise ValueError("Branch axis does not reach the requested main-tube offset surface.")
        return -radial_projection + math.sqrt(discriminant)

    outer_distance = outward_offset_intersection(float(contract.get("main_tube.outer_diameter")) / 2.0)
    inner_distance = outward_offset_intersection(float(contract.get("main_tube.inner_diameter")) / 2.0)
    return origin, axis, outer_distance, inner_distance


def make_side_branch(
    sw: SolidWorksClient,
    contract: SpecContract,
    groups: list[str],
    receipts: dict[str, Any],
) -> None:
    origin, axis, outer_distance, inner_distance = branch_origin_and_overlap(contract)
    visible_length = float(contract.get("side_branch.visible_pipe_length"))
    outer_diameter = float(contract.get("side_branch.outer_diameter"))
    inner_diameter = float(contract.get("side_branch.inner_diameter"))
    flange_thickness = float(contract.get("side_branch.flange.thickness"))
    start_surface = str(contract.get("side_branch.outer_start_surface"))
    bore_end_surface = str(contract.get("side_branch.bore_end_surface"))
    tolerance = float(contract.get("side_branch.boolean_overlap_tolerance"))
    profile_status = str(contract.get("side_branch.flange.profile_status"))
    if start_surface != "main_tube_inner_surface" or bore_end_surface != "main_tube_inner_surface":
        raise ValueError("The C branch must start/end at the D30 inner surface, not the main-axis centre.")
    if profile_status != "exact_external_tangent_profile":
        raise ValueError("The C flange must use one exact R12/R6 external-tangent profile.")

    inner_surface = add(origin, mul(axis, inner_distance))
    outer_surface = add(origin, mul(axis, outer_distance))
    # 图纸尺寸从轴线基准起算，不再额外叠加主管半径。
    pipe_end = add(origin, mul(axis, visible_length))
    sweep_cylinder(sw, origin, pipe_end, outer_diameter)

    outer_face = add(pipe_end, mul(axis, flange_thickness))
    bore_start = origin
    bore_end = add(outer_face, mul(axis, tolerance))
    sweep_cylinder(sw, bore_start, bore_end, inner_diameter, is_cut=True)

    flange_center = add(pipe_end, mul(axis, flange_thickness / 2.0))
    center_radius = float(contract.get("side_branch.flange.center_radius"))
    ear_radius = float(contract.get("side_branch.flange.ear_radius"))
    hole_count = int(contract.get("side_branch.flange.hole_count"))
    hole_diameter = float(contract.get("side_branch.flange.hole_diameter"))
    hole_pitch = float(contract.get("side_branch.flange.hole_pitch"))
    local_x = unit(as_point3(contract.get("side_branch.flange.local_x_axis")))
    if hole_count != 2:
        raise ValueError("The v10 side-flange regression expects two M6 holes.")

    local_y = unit(cross(axis, local_x))
    profile = side_flange_profile(center_radius, ear_radius, hole_pitch)
    loft_exact_profile(sw, pipe_end, outer_face, local_x, local_y, profile)
    ear_centers = [
        add(flange_center, mul(local_x, -hole_pitch / 2.0)),
        add(flange_center, mul(local_x, hole_pitch / 2.0)),
    ]
    create_centered_cylinder(sw, flange_center, axis, flange_thickness + 2.0 * tolerance, inner_diameter, is_cut=True)
    for ear_center in ear_centers:
        create_centered_cylinder(sw, ear_center, axis, flange_thickness + 2.0 * tolerance, hole_diameter, is_cut=True)

    receipts.update(
        {
            "branch_path_origin": origin,
            "branch_inner_surface": inner_surface,
            "branch_outer_surface": outer_surface,
            "branch_solid_start": inner_surface,
            "branch_bore_start": bore_start,
            "branch_visible_pipe_length": visible_length,
            "branch_flange_thickness": flange_thickness,
            "branch_outer_face": outer_face,
            "branch_local_x_axis": local_x,
        }
    )
    groups.append("group_05")


def make_front_boss(
    sw: SolidWorksClient,
    contract: SpecContract,
    groups: list[str],
    receipts: dict[str, Any],
) -> None:
    height = float(contract.get("front_boss.center_height"))
    outer_diameter = float(contract.get("front_boss.outer_diameter"))
    bore_diameter = float(contract.get("front_boss.bore_diameter"))
    distance = float(contract.get("front_boss.outer_face_to_main_axis"))
    axis = unit(as_point3(contract.get("front_boss.axis")))
    start_surface = str(contract.get("front_boss.outer_start_surface"))
    bore_end_surface = str(contract.get("front_boss.bore_end_surface"))
    tolerance = float(contract.get("front_boss.boolean_overlap_tolerance"))
    if start_surface != "main_tube_inner_surface" or bore_end_surface != "main_tube_inner_surface":
        raise ValueError("The front boss must terminate at the D30 inner surface.")
    main_axis = (0.0, height, 0.0)
    outer_face = add(main_axis, mul(axis, distance))
    inner_surface = add(main_axis, mul(axis, float(contract.get("main_tube.inner_diameter")) / 2.0))

    sweep_cylinder(sw, main_axis, outer_face, outer_diameter)
    bore_start = main_axis
    bore_end = add(outer_face, mul(axis, tolerance))
    sweep_cylinder(sw, bore_start, bore_end, bore_diameter, is_cut=True)
    receipts.update(
        {
            "front_boss_center_height": height,
            "front_boss_outer_face": outer_face,
            "front_boss_main_axis": main_axis,
            "front_boss_inner_surface": inner_surface,
            "front_boss_solid_start": inner_surface,
            "front_boss_bore_start": bore_start,
        }
    )
    groups.append("group_06")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def cut_main_passage(sw: SolidWorksClient, contract: SpecContract) -> None:
    path, _, _ = create_main_path(
        sw,
        tuple(contract.get("main_tube.path.inner_start")),
        tuple(contract.get("main_tube.path.arc_center")),
        float(contract.get("main_tube.path.arc_radius")),
        float(contract.get("main_tube.path.arc_start_angle_deg")),
        float(contract.get("main_tube.path.arc_end_angle_deg")),
        float(contract.get("main_tube.path.upper_direction_deg")),
        float(contract.get("main_tube.path.top_height")),
    )
    sw.sweep_circular_profile_by_path(path, float(contract.get("main_tube.inner_diameter")), is_cut=True)


def capture_proving_views(sw: SolidWorksClient) -> tuple[dict[str, str], dict[str, Any]]:
    paths = {
        "front": OUT_DIR / "elbow_436_v10_front.bmp",
        "isometric": OUT_DIR / "elbow_436_v10_iso.bmp",
        "front_section": OUT_DIR / "elbow_436_v10_front_section.bmp",
    }

    sw.remove_section_view()
    sw.set_view_orientation("front")
    sw.capture_screenshot(str(paths["front"]))
    sw.set_view_orientation("isometric")
    sw.capture_screenshot(str(paths["isometric"]))
    section = sw.create_section_view("Front Plane", 0.0)
    sw.set_view_orientation("front")
    sw.capture_screenshot(str(paths["front_section"]))

    hashes = {name: sha256(path) for name, path in paths.items()}
    return hashes, section


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    preflight = validate_spec(spec)
    failed_preflight = [check.check_id for check in preflight if not check.passed]
    if failed_preflight:
        raise RuntimeError("Specification preflight failed: " + ", ".join(failed_preflight))

    contract = SpecContract(spec)
    groups: list[str] = []
    receipts: dict[str, Any] = {}
    target_ready = False
    try:
        sw = TargetClient()
        connection = sw.connect(launch_if_not_running=False, ensure_document=False)
        connection["verified_visible_pid"] = verify_visible_instance(sw)
        resume = "--resume-top" in sys.argv
        if resume:
            doc = sw._active_doc()
            if Path(str(_get(doc, "GetPathName"))).resolve() != OUT_SLDPRT.resolve():
                raise RuntimeError("活动文档不是本次检查点，拒绝修改。")
            previous = json.loads(OUT_LOG.read_text(encoding="utf-8"))
            if previous.get("groups") != ["group_01", "group_02", "group_03"]:
                raise RuntimeError("检查点阶段与顶部修复入口不符。")
            sw.target_title = _get(doc, "GetTitle")
            trailing = sw.list_features()[-2:]
            if len(trailing) != 2 or any(f["type"] != "3DProfileFeature" for f in trailing):
                raise RuntimeError("失败草图状态已变化，拒绝自动删除。")
            for feature in reversed(trailing):
                doc.ClearSelection2(True)
                if not doc.FeatureByName(feature["name"]).Select2(False, 0):
                    raise RuntimeError("无法选中失败草图。")
                if not doc.Extension.DeleteSelection2(0):
                    raise RuntimeError("无法删除失败草图。")
            groups.extend(previous["groups"])
            contract.used_paths.update(previous["used_spec_paths"])
        else:
            if sw._app.ActiveDoc is not None:
                raise RuntimeError("已有活动文档，需先核对其中的建模进度，禁止自动重建覆盖。")
            sw.create_part()
        sw.target_title = _get(sw._active_doc(), "GetTitle")
        target_ready = True

        if resume:
            p = spec["main_tube"]["path"]
            angle = math.radians(p["upper_direction_deg"])
            tangent = (math.cos(angle), math.sin(angle), 0.0)
            arc_end = point_on_circle(tuple(p["arc_center"]), p["arc_radius"], p["arc_end_angle_deg"])
            length = (p["top_height"] - arc_end[1]) / tangent[1]
            top_end = (arc_end[0] + length * tangent[0], p["top_height"], 0.0)
        else:
            make_base(sw, contract, groups)
            top_end, tangent = make_main_tube(sw, contract, groups)
        make_top_flange(sw, contract, top_end, tangent, groups)
        make_side_branch(sw, contract, groups, receipts)
        make_front_boss(sw, contract, groups, receipts)
        cut_main_passage(sw, contract)
        groups.append("group_07")
        contract.assert_required_used()

        rebuild = sw.rebuild_model()
        geometry = sw.check_geometry()
        bodies = sw.list_bodies()
        bounding_box = sw.get_bounding_box()
        try:
            mass_properties = sw.get_mass_properties()
        except Exception as exc:
            mass_properties = {"error": f"{type(exc).__name__}: {exc}"}
        saved = sw.save_document(str(OUT_SLDPRT))
        if not OUT_SLDPRT.exists() or OUT_SLDPRT.stat().st_size <= 0:
            raise RuntimeError("Native SolidWorks file was not created.")

        view_hashes, section_view = capture_proving_views(sw)
        report = {
            "status": "ok",
            "connection": connection,
            "spec_path": str(SPEC_PATH),
            "spec_sha256": sha256(SPEC_PATH),
            "used_spec_paths": sorted(contract.used_paths),
            "groups": groups,
            "construction_receipts": receipts,
            "rebuild": rebuild,
            "geometry": geometry,
            "body_count": len(bodies),
            "bodies": bodies,
            "bounding_box": bounding_box,
            "mass_properties": mass_properties,
            "saved": saved,
            "output": str(OUT_SLDPRT),
            "view_hashes": view_hashes,
            "section_view": section_view,
            "result_level": ["EXECUTION_PASS", "GEOMETRY_PASS"],
            "drawing_match": "BLOCKED_BY_UNRESOLVED_DRAWING_EVIDENCE",
        }
        OUT_LOG.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        # 保留当前目标零件，出错后只修复失败位置。
        try:
            checkpoint = sw.save_document(str(OUT_SLDPRT)) if target_ready else {"skipped": "target_not_ready"}
        except Exception as save_exc:
            checkpoint = {"error": str(save_exc)}
        report = {
            "status": "error",
            "spec_path": str(SPEC_PATH),
            "used_spec_paths": sorted(contract.used_paths),
            "groups": groups,
            "construction_receipts": receipts,
            "error": f"{type(exc).__name__}: {exc}",
            "checkpoint": checkpoint,
        }
        OUT_LOG.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    pythoncom.CoInitialize()
    try:
        raise SystemExit(main())
    finally:
        pythoncom.CoUninitialize()
