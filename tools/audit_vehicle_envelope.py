#!/usr/bin/env python3
"""Audit the x500 + D435i collision envelope in the camera IMU frame."""
import hashlib
import itertools
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
X500 = ROOT / "external/PX4-Autopilot/Tools/simulation/gz/models/x500_base/model.sdf"
WRAPPER = ROOT / "simulation/models/x500_d435i/model.sdf"
D435I = ROOT / "simulation/models/d435i/model.sdf"
PLANNER_LAUNCH = ROOT / "src/vendor/ego_planner/planner/plan_manage/launch/advanced_param.launch.py"
PLANNER_CONFIG = ROOT / "config/components/mapping/ego_planner.json"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def values(text, default=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)):
    return tuple(float(v) for v in text.split()) if text else default


def rotation(rpy):
    roll, pitch, yaw = rpy
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    return (
        (cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr),
        (sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr),
        (-sp, cp * sr, cp * cr),
    )


def mat_vec(matrix, point):
    return tuple(sum(matrix[i][j] * point[j] for j in range(3)) for i in range(3))


def compose(parent, child):
    px, py, pz, pr, pp, pyaw = parent
    cx, cy, cz, cr, cp, cyaw = child
    parent_r = rotation((pr, pp, pyaw))
    child_xyz = mat_vec(parent_r, (cx, cy, cz))
    # All collision/link orientations in these selected SDFs are axis-aligned.
    # The composed pose is only used for box centers and orientation checks.
    return (px + child_xyz[0], py + child_xyz[1], pz + child_xyz[2],
            pr + cr, pp + cp, pyaw + cyaw)


def box_size(collision):
    geometry = collision.find("geometry/box/size")
    if geometry is None:
        raise ValueError(f"Unsupported collision geometry: {collision.get('name')}")
    result = tuple(float(v) for v in geometry.text.split())
    if len(result) != 3 or any(v <= 0 for v in result):
        raise ValueError(f"Invalid box size: {collision.get('name')}")
    return result


def box_corners(pose, size):
    center = pose[:3]
    matrix = rotation(pose[3:])
    half = tuple(v / 2 for v in size)
    for signs in itertools.product((-1, 1), repeat=3):
        offset = mat_vec(matrix, tuple(signs[i] * half[i] for i in range(3)))
        yield tuple(center[i] + offset[i] for i in range(3))


def relative(point, origin):
    return tuple(point[i] - origin[i] for i in range(3))


def radius_xy(point):
    return math.hypot(point[0], point[1])


def audit():
    x500_root = ET.parse(X500).getroot()
    x500_model = x500_root.find("model")
    wrapper = ET.parse(WRAPPER).getroot().find("model")
    d435i_model = ET.parse(D435I).getroot().find("model")
    imu_sensor = d435i_model.find("link/sensor[@name='imu']")
    imu_pose = values(imu_sensor.findtext("pose"))
    if any(abs(v) > 1e-12 for v in imu_pose):
        raise ValueError("This audit expects the IMU at the D435i link origin")

    mount = values(wrapper.find("joint[@name='d435i_mount']/pose" ).text)
    include = wrapper.find("include[uri='model://d435i']")
    include_pose = values(include.findtext("pose"))
    if any(abs(a - b) > 1e-12 for a, b in zip(mount, include_pose)):
        raise ValueError("D435i include pose and fixed mount joint disagree")
    if any(abs(v) > 1e-12 for v in mount[3:]):
        raise ValueError("This audit expects aligned x500 and D435i axes")
    origin = mount[:3]

    points = []
    objects = []
    rotor_sweeps = []
    rotor_swept_bounds = []
    base_link = x500_model.find("link[@name='base_link']")
    base_pose = values(base_link.findtext("pose"))
    for collision in base_link.findall("collision"):
        size = box_size(collision)
        pose = compose(base_pose, values(collision.findtext("pose")))
        corners = [relative(p, origin) for p in box_corners(pose, size)]
        points.extend(corners)
        objects.append({"name": collision.get("name"), "type": "static_box"})

    for link in x500_model.findall("link"):
        if not link.get("name", "").startswith("rotor_"):
            continue
        collision = link.find("collision")
        if collision is None:
            continue
        size = box_size(collision)
        link_pose = values(link.findtext("pose"))
        collision_pose = values(collision.findtext("pose"))
        joint = x500_model.find(f"joint[@name='{link.get('name')}_joint']")
        axis = tuple(float(v) for v in joint.findtext("axis/xyz").split()) if joint is not None else ()
        if joint is None or joint.get("type") != "revolute" or axis != (0.0, 0.0, 1.0):
            raise ValueError(f"Expected a Z-axis revolute joint for {link.get('name')}")
        if any(abs(v) > 1e-12 for v in link_pose[3:] + collision_pose[3:]):
            raise ValueError(f"Unexpected rotor/collision tilt for {link.get('name')}")
        center = relative(compose(link_pose, collision_pose)[:3], origin)
        hx, hy, hz = (v / 2 for v in size)
        local_sweep_radius = math.hypot(hx, hy)
        horizontal_sweep_radius = radius_xy(center) + local_sweep_radius
        vertical_extent = abs(center[2]) + hz
        swept_sphere_radius = math.hypot(horizontal_sweep_radius, vertical_extent)
        rotor_swept_bounds.append([
            [center[0] - local_sweep_radius, center[0] + local_sweep_radius],
            [center[1] - local_sweep_radius, center[1] + local_sweep_radius],
            [center[2] - hz, center[2] + hz],
        ])
        rotor_sweeps.append({
            "name": collision.get("name"),
            "center_d435i_imu_m": list(center),
            "collision_box_size_m": list(size),
            "box_half_diagonal_xy_m": local_sweep_radius,
            "max_horizontal_radius_from_imu_m": horizontal_sweep_radius,
            "max_orientation_invariant_radius_m": swept_sphere_radius,
        })
        objects.append({"name": collision.get("name"), "type": "rotating_box_sweep"})

    d435i_link = d435i_model.find("link[@name='d435i_link']")
    d435i_collisions = d435i_link.findall("collision")
    if len(d435i_collisions) != 1 or any(
            abs(actual - expected) > 1e-12
            for actual, expected in zip(box_size(d435i_collisions[0]), (0.025, 0.09, 0.025))):
        raise ValueError("Expected one nominal 25 x 90 x 25 mm D435i housing collision box")
    for collision in d435i_collisions:
        size = box_size(collision)
        pose = values(collision.findtext("pose"))
        points.extend(box_corners(pose, size))
        objects.append({"name": collision.get("name"), "type": "camera_housing_box"})

    bounds = [[min([p[i] for p in points] + [b[i][0] for b in rotor_swept_bounds]),
               max([p[i] for p in points] + [b[i][1] for b in rotor_swept_bounds])]
              for i in range(3)]
    max_horizontal_static = max(radius_xy(p) for p in points)
    max_sphere_static = max(math.sqrt(sum(v * v for v in p)) for p in points)
    max_horizontal = max_horizontal_static
    max_sphere = max_sphere_static
    max_horizontal = max(max_horizontal, *(v["max_horizontal_radius_from_imu_m"] for v in rotor_sweeps))
    max_sphere = max(max_sphere, *(v["max_orientation_invariant_radius_m"] for v in rotor_sweeps))
    planner_text = PLANNER_LAUNCH.read_text(errors="replace")
    config = json.loads(PLANNER_CONFIG.read_text())
    resolution_m = 0.1
    if "('grid_map/resolution': 0.1)" not in planner_text and "{'grid_map/resolution': 0.1}" not in planner_text:
        raise ValueError("Expected the pinned EGO launch resolution to remain 0.1 m")
    configured_inflation = float(config["obstacles_inflation_m"])

    result = {
        "reference_frame": "d435i_imu_frame / d435i_link origin",
        "mount_pose_base_link_xyzrpy": list(mount),
        "x500_static_collision_count": len(base_link.findall("collision")) + len(rotor_sweeps),
        "d435i_housing_collision_count": len(d435i_collisions),
        "collision_bounds_xyz_m": bounds,
        "max_horizontal_radius_level_all_rotor_angles_m": max_horizontal,
        "max_orientation_invariant_radius_all_rotor_angles_m": max_sphere,
        "rotor_sweep_method": "For each revolute Z-axis rotor, the collision rectangle sweeps a disk whose radius is its XY half diagonal; add the rotor-center radius from the IMU origin. Include the box half-thickness in Z.",
        "rotor_sweeps": rotor_sweeps,
        "planner_grid_resolution_m": resolution_m,
        "configured_obstacle_inflation_m": configured_inflation,
        "inflation_steps": math.ceil(configured_inflation / resolution_m),
        "minimum_grid_steps_to_cover_model_sphere_lower_bound": math.ceil(max_sphere / resolution_m),
        "objects": objects,
        "limitations": [
            "The D435i box uses nominal external dimensions; mounting bracket, cable, connectors, and manufacturing tolerance are excluded.",
            "The x500 collision boxes are the simulator's collision model; the propeller sweep is the swept union of its rectangular collision boxes, not a physical blade scan.",
            "Map, localization, control tracking, latency, stopping distance, and vibration/model uncertainty are not included.",
            "Grid-cell count is only a geometric lower-bound comparison; EGO's discrete dilation is not itself a validated minimum-clearance guarantee.",
        ],
        "source_sha256": {str(p.relative_to(ROOT)): sha256(p) for p in [X500, WRAPPER, D435I, PLANNER_LAUNCH, PLANNER_CONFIG]},
    }
    return result


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
