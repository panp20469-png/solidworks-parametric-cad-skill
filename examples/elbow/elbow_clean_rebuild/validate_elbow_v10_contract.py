from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_SPEC = ROOT / "elbow_v10_spec.json"
DEFAULT_LOG = ROOT / "output" / "elbow_436_v10_spec.log.json"
DEFAULT_JSON_REPORT = ROOT / "output" / "elbow_436_v10_contract_report.json"
DEFAULT_MD_REPORT = ROOT / "output" / "elbow_436_v10_contract_report.md"


def nested_get(data: dict[str, Any], path: str) -> Any:
    value: Any = data
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            raise KeyError(path)
        value = value[part]
    return value


class SpecContract:
    """Track which confirmed specification fields drive generated geometry."""

    def __init__(self, data: dict[str, Any]):
        self.data = data
        self.used_paths: set[str] = set()

    def get(self, path: str) -> Any:
        value = nested_get(self.data, path)
        self.used_paths.add(path)
        return value

    def assert_required_used(self) -> None:
        required = set(nested_get(self.data, "verification.required_spec_paths"))
        missing = sorted(required - self.used_paths)
        if missing:
            raise RuntimeError("Required specification fields were not consumed: " + ", ".join(missing))


@dataclass
class Check:
    check_id: str
    passed: bool
    expected: Any
    actual: Any
    note: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.check_id,
            "passed": self.passed,
            "expected": self.expected,
            "actual": self.actual,
            "note": self.note,
        }


def close(actual: float, expected: float, tolerance: float = 1e-9) -> bool:
    return math.isclose(float(actual), float(expected), abs_tol=tolerance, rel_tol=0.0)


def point_close(actual: Any, expected: list[float], tolerance: float = 1e-9) -> bool:
    return (
        isinstance(actual, (list, tuple))
        and len(actual) == len(expected)
        and all(close(a, e, tolerance) for a, e in zip(actual, expected))
    )


def validate_spec(spec: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []

    def add(check_id: str, passed: bool, expected: Any, actual: Any, note: str) -> None:
        checks.append(Check(check_id, bool(passed), expected, actual, note))

    add("units_mm", spec.get("units") == "mm", "mm", spec.get("units"), "SolidWorks wrapper receives millimetres.")

    unresolved = spec.get("gate", {}).get("unresolved", [])
    gate_status = spec.get("gate", {}).get("status")
    add(
        "unresolved_not_confirmed",
        not unresolved or gate_status != "CONFIRMED",
        "non-CONFIRMED while feature-critical items remain unresolved",
        gate_status,
        "The regression may run as an evaluation artifact but cannot claim final drawing match.",
    )

    required_paths = spec.get("verification", {}).get("required_spec_paths", [])
    missing_paths: list[str] = []
    for path in required_paths:
        try:
            nested_get(spec, path)
        except KeyError:
            missing_paths.append(path)
    add("required_paths_exist", not missing_paths, [], missing_paths, "Every feature-critical input must exist in the single source of truth.")

    base_bottom = 0.0
    inner_start = nested_get(spec, "main_tube.path.inner_start")
    add(
        "main_bore_crosses_base_bottom",
        float(inner_start[1]) < base_bottom,
        "inner path Y below 0 mm",
        inner_start,
        "The D30 cut must open through the bottom instead of stopping at the base top.",
    )

    visible = float(nested_get(spec, "side_branch.visible_pipe_length"))
    flange_thickness = float(nested_get(spec, "side_branch.flange.thickness"))
    add(
        "branch_dimension_chain",
        close(visible + flange_thickness, 31.0),
        31.0,
        visible + flange_thickness,
        "Keep the 25 mm visible pipe and 6 mm flange as separate physical segments.",
    )

    boss_height = float(nested_get(spec, "front_boss.center_height"))
    add("front_boss_height", close(boss_height, 20.0), 20.0, boss_height, "A-A passes through the front-boss axis at 20 mm.")

    center_radius = float(nested_get(spec, "side_branch.flange.center_radius"))
    ear_radius = float(nested_get(spec, "side_branch.flange.ear_radius"))
    add(
        "side_flange_r12_r6",
        close(center_radius, 12.0) and close(ear_radius, 6.0),
        {"center_radius": 12.0, "ear_radius": 6.0},
        {"center_radius": center_radius, "ear_radius": ear_radius},
        "R12 is the centre bulge and R6 is each end ear; their external tangents form one outline.",
    )

    add(
        "top_flange_user_accepted_profile",
        nested_get(spec, "top_flange.profile_status") == "user_accepted_existing_outline",
        "user_accepted_existing_outline",
        nested_get(spec, "top_flange.profile_status"),
        "Preserve the existing B outline; only correct the one-up/two-down hole orientation requested by the user.",
    )
    add(
        "top_single_lug_orientation",
        close(nested_get(spec, "top_flange.first_hole_angle_deg"), -90.0),
        -90.0,
        nested_get(spec, "top_flange.first_hole_angle_deg"),
        "In the anchored B local frame the single lug is above the main opening.",
    )
    add(
        "side_flange_exact_profile",
        nested_get(spec, "side_branch.flange.profile_status") == "exact_external_tangent_profile",
        "exact_external_tangent_profile",
        nested_get(spec, "side_branch.flange.profile_status"),
        "The C outline is the external-tangent envelope of R12 and two R6 ears.",
    )
    add(
        "local_features_terminate_at_inner_surface",
        nested_get(spec, "side_branch.outer_start_surface") == "main_tube_inner_surface"
        and nested_get(spec, "side_branch.bore_end_surface") == "main_tube_inner_surface"
        and nested_get(spec, "front_boss.outer_start_surface") == "main_tube_inner_surface"
        and nested_get(spec, "front_boss.bore_end_surface") == "main_tube_inner_surface",
        "all side/front local features terminate at the D30 inner surface",
        {
            "side_outer": nested_get(spec, "side_branch.outer_start_surface"),
            "side_bore": nested_get(spec, "side_branch.bore_end_surface"),
            "front_outer": nested_get(spec, "front_boss.outer_start_surface"),
            "front_bore": nested_get(spec, "front_boss.bore_end_surface"),
        },
        "Starting the solid at the main-axis centre would intrude into the flow passage.",
    )

    angle = math.radians(float(nested_get(spec, "side_branch.axis_angle_deg")))
    branch_axis = (math.cos(angle), math.sin(angle), 0.0)
    local_x = tuple(float(v) for v in nested_get(spec, "side_branch.flange.local_x_axis"))
    norm = math.sqrt(sum(v * v for v in local_x))
    dot = sum(a * b for a, b in zip(branch_axis, local_x))
    add(
        "side_flange_local_axis",
        close(norm, 1.0) and close(dot, 0.0),
        "unit axis perpendicular to the 30-degree branch axis",
        {"axis": local_x, "norm": norm, "dot": dot},
        "The local end-view X axis controls the two-hole flange orientation.",
    )

    return checks


def validate_runtime(spec: dict[str, Any], runtime: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []

    def add(check_id: str, passed: bool, expected: Any, actual: Any, note: str) -> None:
        checks.append(Check(check_id, bool(passed), expected, actual, note))

    add("runtime_status", runtime.get("status") == "ok", "ok", runtime.get("status"), "The modeling process must finish without an exception.")

    required_body_count = int(nested_get(spec, "verification.required_body_count"))
    body_count = int(runtime.get("body_count", -1))
    add("body_count", body_count == required_body_count, required_body_count, body_count, "The casting must finish as one solid body.")

    required_errors = int(nested_get(spec, "verification.required_geometry_errors"))
    geometry_errors = int(runtime.get("geometry", {}).get("errors", -1))
    add("geometry_errors", geometry_errors == required_errors, required_errors, geometry_errors, "Geometry validity is necessary but not sufficient for drawing match.")

    required_paths = set(nested_get(spec, "verification.required_spec_paths"))
    used_paths = set(runtime.get("used_spec_paths", []))
    missing = sorted(required_paths - used_paths)
    add("spec_coverage", not missing, [], missing, "The generator must consume every required field from the single specification file.")

    receipts = runtime.get("construction_receipts", {})
    add(
        "runtime_front_boss_height",
        close(receipts.get("front_boss_center_height", math.nan), nested_get(spec, "front_boss.center_height")),
        nested_get(spec, "front_boss.center_height"),
        receipts.get("front_boss_center_height"),
        "Compare the generated construction receipt with the independently loaded specification.",
    )
    boss_axis = [float(value) for value in nested_get(spec, "front_boss.axis")]
    boss_height = float(nested_get(spec, "front_boss.center_height"))
    boss_distance = float(nested_get(spec, "front_boss.outer_face_to_main_axis"))
    expected_boss_outer_face = [
        boss_axis[0] * boss_distance,
        boss_height + boss_axis[1] * boss_distance,
        boss_axis[2] * boss_distance,
    ]
    add(
        "runtime_front_boss_observer_side",
        point_close(receipts.get("front_boss_outer_face"), expected_boss_outer_face),
        expected_boss_outer_face,
        receipts.get("front_boss_outer_face"),
        "The boss outer face must lie in the positive specification-axis direction, not behind the main tube.",
    )
    add(
        "runtime_branch_visible_length",
        close(receipts.get("branch_visible_pipe_length", math.nan), nested_get(spec, "side_branch.visible_pipe_length")),
        nested_get(spec, "side_branch.visible_pipe_length"),
        receipts.get("branch_visible_pipe_length"),
        "The visible pipe length must not include flange thickness.",
    )
    add(
        "runtime_branch_flange_thickness",
        close(receipts.get("branch_flange_thickness", math.nan), nested_get(spec, "side_branch.flange.thickness")),
        nested_get(spec, "side_branch.flange.thickness"),
        receipts.get("branch_flange_thickness"),
        "The flange thickness is verified as its own segment.",
    )

    # Independent observer calculation: recompute the D30 inner-surface endpoints
    # from the drawing contract instead of trusting generator-reported dimensions.
    arc_center = [float(value) for value in nested_get(spec, "main_tube.path.arc_center")]
    arc_radius = float(nested_get(spec, "main_tube.path.arc_radius"))
    branch_height = float(nested_get(spec, "side_branch.axis_center_height"))
    dy = branch_height - arc_center[1]
    branch_path_x = arc_center[0] + math.sqrt(arc_radius * arc_radius - dy * dy)
    branch_angle = math.radians(float(nested_get(spec, "side_branch.axis_angle_deg")))
    branch_axis = (math.cos(branch_angle), math.sin(branch_angle), 0.0)
    radial_vector = (branch_path_x - arc_center[0], dy, 0.0)
    radial_projection = sum(a * b for a, b in zip(radial_vector, branch_axis))
    target_radius = arc_radius + float(nested_get(spec, "main_tube.inner_diameter")) / 2.0
    inner_distance = -radial_projection + math.sqrt(
        radial_projection * radial_projection + target_radius * target_radius - arc_radius * arc_radius
    )
    expected_branch_inner = [
        branch_path_x + branch_axis[0] * inner_distance,
        branch_height + branch_axis[1] * inner_distance,
        branch_axis[2] * inner_distance,
    ]
    side_tol = float(nested_get(spec, "side_branch.boolean_overlap_tolerance"))
    expected_branch_bore_start = [
        expected_branch_inner[index] - branch_axis[index] * side_tol for index in range(3)
    ]
    add(
        "runtime_branch_solid_stops_at_inner_wall",
        point_close(receipts.get("branch_solid_start"), expected_branch_inner),
        expected_branch_inner,
        receipts.get("branch_solid_start"),
        "The D20 branch solid starts at the D30 inner wall, never at the main-path centreline.",
    )
    add(
        "runtime_branch_bore_opens_only_to_inner_wall",
        point_close(receipts.get("branch_bore_start"), expected_branch_bore_start),
        expected_branch_bore_start,
        receipts.get("branch_bore_start"),
        "Only the declared boolean tolerance may enter the D30 void.",
    )

    front_axis = [float(value) for value in nested_get(spec, "front_boss.axis")]
    front_inner_distance = float(nested_get(spec, "main_tube.inner_diameter")) / 2.0
    expected_front_inner = [
        front_axis[0] * front_inner_distance,
        float(nested_get(spec, "front_boss.center_height")) + front_axis[1] * front_inner_distance,
        front_axis[2] * front_inner_distance,
    ]
    front_tol = float(nested_get(spec, "front_boss.boolean_overlap_tolerance"))
    expected_front_bore_start = [
        expected_front_inner[index] - front_axis[index] * front_tol for index in range(3)
    ]
    add(
        "runtime_front_boss_solid_stops_at_inner_wall",
        point_close(receipts.get("front_boss_solid_start"), expected_front_inner),
        expected_front_inner,
        receipts.get("front_boss_solid_start"),
        "The D24 boss starts at the D30 inner wall and cannot fill the main passage.",
    )
    add(
        "runtime_front_bore_opens_only_to_inner_wall",
        point_close(receipts.get("front_boss_bore_start"), expected_front_bore_start),
        expected_front_bore_start,
        receipts.get("front_boss_bore_start"),
        "The D12 front bore stops at the main inner wall except for boolean tolerance.",
    )

    hashes = runtime.get("view_hashes", {})
    required_views = list(nested_get(spec, "verification.required_views"))
    selected_hashes = [hashes.get(name) for name in required_views]
    distinct = all(selected_hashes) and len(set(selected_hashes)) == len(selected_hashes)
    add(
        "view_frames_distinct",
        bool(distinct),
        f"{len(required_views)} non-empty distinct hashes",
        dict(zip(required_views, selected_hashes)),
        "Identical front/isometric/section hashes prove the viewport did not change.",
    )

    view_states = runtime.get("view_states", {})
    unverified_views = [
        name
        for name in required_views
        if view_states.get(name, {}).get("orientation_verified") is not True
    ]
    add(
        "view_orientations_verified",
        not unverified_views,
        [],
        unverified_views,
        "Each proving view must match the requested standard-view rotation matrix before capture.",
    )

    section_active = runtime.get("section_view", {}).get("section_view_active") is True
    add("section_view_active", section_active, True, runtime.get("section_view"), "A real model section must be created before claiming section comparison.")

    return checks


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Elbow v10 Contract Validation",
        "",
        f"- Result: `{report['result']}`",
        f"- Drawing match claim: `{report['drawing_match_claim']}`",
        "",
        "| Check | Result | Expected | Actual |",
        "|---|---|---|---|",
    ]
    for check in report["checks"]:
        expected = json.dumps(check["expected"], ensure_ascii=False)
        actual = json.dumps(check["actual"], ensure_ascii=False)
        lines.append(f"| `{check['id']}` | {'PASS' if check['passed'] else 'FAIL'} | {expected} | {actual} |")
    lines.extend(["", "## Boundary", "", report["boundary"], ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--json-report", type=Path, default=DEFAULT_JSON_REPORT)
    parser.add_argument("--md-report", type=Path, default=DEFAULT_MD_REPORT)
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    checks = validate_spec(spec)
    runtime_loaded = args.log.exists()
    if runtime_loaded:
        runtime = json.loads(args.log.read_text(encoding="utf-8"))
        checks.extend(validate_runtime(spec, runtime))

    passed = all(check.passed for check in checks)
    unresolved = spec.get("gate", {}).get("unresolved", [])
    if unresolved:
        drawing_match_claim = "BLOCKED_BY_UNRESOLVED_DRAWING_EVIDENCE"
    elif not runtime_loaded:
        drawing_match_claim = "PREFLIGHT_ONLY"
    else:
        drawing_match_claim = "DRAWING_MATCH_PASS" if passed else "DRAWING_MATCH_FAIL"
    report = {
        "result": "PASS" if passed else "FAIL",
        "runtime_loaded": runtime_loaded,
        "drawing_match_claim": drawing_match_claim,
        "checks": [check.as_dict() for check in checks],
        "boundary": (
            "This validator proves specification coverage, exact profile selection, independently recomputed local-feature "
            "endpoints, model health, and distinct proving views. Final acceptance still requires visual B/C/A-A comparison "
            "against the source drawing."
        ),
    }

    args.json_report.parent.mkdir(parents=True, exist_ok=True)
    args.json_report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md_report.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
