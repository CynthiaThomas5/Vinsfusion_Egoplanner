"""Validation rules for read-only N10 occupancy query evidence."""

import math
import sys
from pathlib import Path


RAW_OCCUPANCY_SERVICE = "/mapping/query_occupancy_sphere"
PLANNING_OCCUPANCY_SERVICE = "/mapping/query_planning_occupancy"


def resolve_point_query_identity(run_dir, spec):
    """Bind a point-query specification to its task identity before flight.json exists."""
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "tools"))
    from n10_run_identity import read_run_identity

    declared = spec.get("run_identity") or {}
    goal_id = spec.get("goal_id") or declared.get("goal_id")
    identity = read_run_identity(
        run_dir,
        goal_id=goal_id,
        epoch=str(spec.get("epoch", "")),
        map_id=str(spec.get("map_id", "")),
        frame_id=str(spec.get("frame_id", "")),
    )
    conflicts = {
        field: {"declared": declared[field], "resolved": identity.get(field)}
        for field in ("run_id", "runtime_contract_sha256", "goal_id", "epoch",
                      "map_id", "frame_id")
        if declared.get(field) and identity.get(field)
        and declared[field] != identity[field]
    }
    return identity, conflicts


def radius_for_service(service, raw_query_radius_m):
    """Keep raw sphere and official EGO point-query semantics distinct."""
    if service == RAW_OCCUPANCY_SERVICE:
        radius = float(raw_query_radius_m)
        if not math.isfinite(radius) or radius <= 0.0 or radius > 2.0:
            raise ValueError("raw occupancy sphere radius must satisfy 0 < r <= 2 m")
        return radius
    if service == PLANNING_OCCUPANCY_SERVICE:
        return 0.0
    raise ValueError(f"unsupported occupancy query service: {service}")


def response_query_geometry(response):
    """Serialize the request geometry echoed by QueryOccupancySphere."""
    return {
        'center_xyz_odom_m': [
            float(response.center.x),
            float(response.center.y),
            float(response.center.z),
        ],
        'radius_m': float(response.radius_m),
    }


def response_capture_error(row):
    """Return why a response cannot support a query capture, independent of verdict."""
    request = row.get("request") or {}
    response = row.get("response") or {}
    service = row.get("service")
    if row.get("error"):
        return "service_call_error"
    if response.get("accepted") is not True:
        return "service_rejected:" + str(response.get("reason") or "unspecified")
    if row.get("identity_matches_request") is not True:
        return "response_identity_mismatch"
    try:
        expected_radius = radius_for_service(service, request.get("radius_m"))
    except (TypeError, ValueError):
        return "invalid_request_radius"
    try:
        request_radius = float(request.get("radius_m"))
        response_radius = float(response.get("radius_m"))
    except (TypeError, ValueError):
        return "query_radius_missing_or_invalid"
    if not math.isclose(request_radius, expected_radius, rel_tol=0.0, abs_tol=1e-12):
        return "service_request_radius_mismatch"
    if not math.isclose(response_radius, expected_radius, rel_tol=0.0, abs_tol=1e-12):
        return "response_radius_mismatch"
    if (response.get("epoch") != request.get("expected_epoch")
            or response.get("map_id") != request.get("expected_map_id")
            or response.get("header_frame_id") != request.get("frame_id")):
        return "response_identity_mismatch"
    request_center = request.get("xyz_odom_m")
    response_center = response.get("center_xyz_odom_m")
    if (not isinstance(request_center, list) or len(request_center) != 3
            or not isinstance(response_center, list) or len(response_center) != 3):
        return "response_center_missing"
    try:
        if any(not math.isclose(float(a), float(b), rel_tol=0.0, abs_tol=1e-9)
               for a, b in zip(request_center, response_center)):
            return "response_center_mismatch"
    except (TypeError, ValueError):
        return "response_center_invalid"
    return ""
