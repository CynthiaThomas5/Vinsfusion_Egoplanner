#!/usr/bin/env python3
"""Offline, model-bounded inter-solver-step clearance analysis for N10."""
import argparse
import bisect
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import numpy as np

try:
    from evaluate_n10_clearance import (
        distance_to_obstacle,
        parse_obstacles,
        quaternion_rotation,
        vehicle_vertical_cylinder,
    )
except ModuleNotFoundError as exc:
    if exc.name != "evaluate_n10_clearance":
        raise
    from tools.debug_truth.evaluate_n10_clearance import (
        distance_to_obstacle,
        parse_obstacles,
        quaternion_rotation,
        vehicle_vertical_cylinder,
    )


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from truth_reference import model_to_imu_contract
try:
    from kinematics_evidence import instantaneous_endpoints
except ModuleNotFoundError:
    from tools.debug_truth.kinematics_evidence import instantaneous_endpoints
DEFAULTS = {
    "envelope": ROOT / "config/components/navigation/vehicle_envelope.json",
    "world_model": ROOT / "simulation/models/x500_d435i/model.sdf",
    "camera_model": ROOT / "simulation/models/d435i/model.sdf",
    "base_model": ROOT / "simulation/models/x500_base/model.sdf",
    "airframe_model": ROOT / "external/PX4-Autopilot/Tools/simulation/gz/models/x500/model.sdf",
    "motor_source": ROOT / "external/PX4-Autopilot/src/modules/simulation/gz_plugins/generic_motor/GenericMotorModel.cpp",
    "esc_source": ROOT / "external/PX4-Autopilot/src/modules/simulation/gz_bridge/GZMixingInterfaceESC.cpp",
}


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def _pose_xyz_rpy(node):
    values = [float(x) for x in (node.findtext("pose") or "0 0 0 0 0 0").split()]
    if len(values) != 6 or not np.isfinite(values).all():
        raise ValueError("unsupported_or_invalid_sdf_pose")
    return np.asarray(values[:3], dtype=float), values[3:]


def _rotation_from_rpy(rpy):
    roll, pitch, yaw = map(float, rpy)
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]], dtype=float)
    ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]], dtype=float)
    rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]], dtype=float)
    return rz @ ry @ rx


def _inertia_matrix(inertial):
    node = inertial.find("inertia")
    if node is None:
        raise ValueError("missing_inertial_tensor")
    matrix = np.array([
        [float(node.findtext("ixx")), float(node.findtext("ixy") or 0), float(node.findtext("ixz") or 0)],
        [float(node.findtext("ixy") or 0), float(node.findtext("iyy")), float(node.findtext("iyz") or 0)],
        [float(node.findtext("ixz") or 0), float(node.findtext("iyz") or 0), float(node.findtext("izz"))],
    ], dtype=float)
    if not np.isfinite(matrix).all():
        raise ValueError("nonfinite_inertial_tensor")
    inertial_pose = inertial.find("pose")
    if inertial_pose is not None:
        _, rpy = _pose_xyz_rpy(inertial)
        rotation = _rotation_from_rpy(rpy)
        matrix = rotation @ matrix @ rotation.T
    return matrix


def _link_component(link, link_position, link_rotation, name):
    inertial = link.find("inertial")
    if inertial is None:
        return None
    inertial_pose = inertial.find("pose")
    if inertial_pose is None:
        local_position, local_rotation = np.zeros(3), np.eye(3)
    else:
        local_position, rpy = _pose_xyz_rpy(inertial)
        local_rotation = _rotation_from_rpy(rpy)
    return {
        "name": name,
        "mass": float(inertial.findtext("mass")),
        "position": link_position + link_rotation @ local_position,
        "inertia": link_rotation @ _inertia_matrix(inertial) @ link_rotation.T,
    }


def _pose_matrix(node):
    position, rpy = _pose_xyz_rpy(node)
    transform = np.eye(4, dtype=float)
    transform[:3, :3] = _rotation_from_rpy(rpy)
    transform[:3, 3] = position
    return transform


def _collision_component_spheres(base_model_path, vehicle_model_path,
                                 camera_model_path):
    """Enclose each model collision primitive separately by a sphere.

    Rotor collision boxes are enclosed by spheres centered on their joint
    axes, so the enclosure remains valid for every rotor angle. The spheres
    are conservative per component; they do not fill the empty space between
    the four rotors as the legacy whole-vehicle disk does.
    """
    base_root = ET.parse(base_model_path).getroot().find("model")
    vehicle_root = ET.parse(vehicle_model_path).getroot().find("model")
    camera_root = ET.parse(camera_model_path).getroot().find("model")
    if base_root is None or vehicle_root is None or camera_root is None:
        raise ValueError("vehicle_collision_model_missing")

    base_model = _pose_matrix(base_root)
    base_link = base_root.find("./link[@name='base_link']")
    if base_link is None:
        raise ValueError("x500_base_missing_base_link")
    base_link_model = base_model @ _pose_matrix(base_link)
    components = []

    def add_link_collisions(link, link_model, prefix):
        for collision in link.findall("collision"):
            geometry = collision.find("geometry")
            size_node = collision.find("geometry/box/size")
            if geometry is None or len(geometry) != 1 or size_node is None:
                raise ValueError(
                    f"unsupported_vehicle_collision_geometry:{prefix}/{collision.get('name', '')}"
                )
            size = np.asarray([float(value) for value in size_node.text.split()], dtype=float)
            if size.shape != (3,) or not np.isfinite(size).all() or np.any(size <= 0):
                raise ValueError(f"invalid_vehicle_collision_box:{prefix}/{collision.get('name', '')}")
            collision_model = link_model @ _pose_matrix(collision)
            components.append({
                "name": f"{prefix}/{collision.get('name', 'unnamed_collision')}",
                "center_model_origin_m": collision_model[:3, 3].tolist(),
                "enclosing_sphere_radius_m": float(np.linalg.norm(size / 2.0)),
                "source_geometry": "SDF collision box circumscribed sphere",
            })

    # Include every physical collision box in the x500 SDF, including each
    # rotating propeller box at its link/joint center.
    for link in base_root.findall("link"):
        link_name = link.get("name", "unnamed_link")
        link_model = base_model @ _pose_matrix(link)
        add_link_collisions(link, link_model, f"x500_base/{link_name}")

    mount = vehicle_root.find("./joint[@name='d435i_mount']/pose")
    if mount is None:
        raise ValueError("d435i_mount_pose_missing")
    camera_model = base_link_model @ _pose_matrix(mount) @ _pose_matrix(camera_root)
    for link in camera_root.findall("link"):
        link_model = camera_model @ _pose_matrix(link)
        add_link_collisions(link, link_model, f"d435i/{link.get('name', 'unnamed_link')}")

    if not components:
        raise ValueError("vehicle_collision_component_list_empty")
    return components


def _sample_component_sphere_clearances(rows, components, obstacles):
    """Return conservative nearest-obstacle clearance for each model state."""
    if not rows or not components or not obstacles:
        raise ValueError("component_clearance_inputs_empty")
    origins = np.asarray([row["xyz"] for row in rows], dtype=float)
    rotations = np.asarray([quaternion_rotation(row["q_xyzw"]) for row in rows], dtype=float)
    local_centers = np.asarray(
        [item["center_model_origin_m"] for item in components], dtype=float
    )
    radii = np.asarray(
        [item["enclosing_sphere_radius_m"] for item in components], dtype=float
    )
    centers = origins[:, None, :] + np.einsum("nij,kj->nki", rotations, local_centers)
    nearest = np.full((len(rows), len(components)), np.inf, dtype=float)
    nearest_obstacle = np.full((len(rows), len(components)), -1, dtype=int)
    for obstacle_index, obstacle in enumerate(obstacles):
        delta = centers - np.asarray(obstacle["center_xyz_m"], dtype=float)
        if obstacle["kind"] == "vertical_cylinder":
            horizontal = np.maximum(
                0.0,
                np.linalg.norm(delta[:, :, :2], axis=2) - float(obstacle["radius_m"]),
            )
        else:
            yaw = float(obstacle["yaw_rad"])
            cosine, sine = math.cos(yaw), math.sin(yaw)
            local_x = cosine * delta[:, :, 0] + sine * delta[:, :, 1]
            local_y = -sine * delta[:, :, 0] + cosine * delta[:, :, 1]
            half = np.asarray(obstacle["size_xyz_m"][:2], dtype=float) / 2.0
            outside = np.stack((
                np.maximum(np.abs(local_x) - half[0], 0.0),
                np.maximum(np.abs(local_y) - half[1], 0.0),
            ), axis=2)
            horizontal = np.linalg.norm(outside, axis=2)
        vertical = np.maximum(
            0.0,
            np.maximum(
                float(obstacle["z_min_m"]) - centers[:, :, 2],
                centers[:, :, 2] - float(obstacle["z_max_m"]),
            ),
        )
        point_distance = np.hypot(horizontal, vertical)
        clearance = np.maximum(0.0, point_distance - radii[None, :])
        better = clearance < nearest
        nearest = np.minimum(nearest, clearance)
        nearest_obstacle[better] = obstacle_index
    component_index = np.argmin(nearest, axis=1)
    sample_index = np.arange(len(rows))
    values = nearest[sample_index, component_index]
    details = [{
        "stamp_ns": int(rows[index]["stamp_ns"]),
        "clearance_m": float(values[index]),
        "component": components[int(component_index[index])]["name"],
        "obstacle": obstacles[int(nearest_obstacle[index, component_index[index]])]["name"],
    } for index in range(len(rows))]
    return values.tolist(), details


def _parse_model_physics(world_path, base_model_path, airframe_path,
                         vehicle_model_path, camera_model_path):
    world = ET.parse(world_path).getroot().find("world")
    if world is None:
        raise ValueError("world_sdf_missing_world")
    step = float(world.findtext("physics/max_step_size"))
    gravity_values = [float(x) for x in world.findtext("gravity", "0 0 -9.8").split()]
    if len(gravity_values) != 3 or not math.isfinite(step) or step <= 0:
        raise ValueError("invalid_world_physics")
    gravity = float(np.linalg.norm(gravity_values))

    base_root = ET.parse(base_model_path).getroot().find("model")
    if base_root is None:
        raise ValueError("base_model_sdf_missing_model")
    model_position, model_rpy = _pose_xyz_rpy(base_root)
    model_rotation = _rotation_from_rpy(model_rpy)
    parts = []
    base_link = base_root.find("./link[@name='base_link']")
    if base_link is None:
        raise ValueError("x500_base_missing_base_link")
    base_pose, base_rpy = _pose_xyz_rpy(base_link)
    base_link_rotation_local = _rotation_from_rpy(base_rpy)
    base_link_position_model = model_position + model_rotation @ base_pose
    base_link_rotation_model = model_rotation @ base_link_rotation_local
    base_part = _link_component(
        base_link, base_link_position_model, base_link_rotation_model, "base_link"
    )
    if base_part is None:
        raise ValueError("x500_base_base_link_missing_inertial")
    parts.append(base_part)
    base_inertia_eigenvalues = np.linalg.eigvalsh(base_part["inertia"])

    rotor_parts = {}
    for link in base_root.findall("link"):
        name = link.get("name", "")
        if not name.startswith("rotor_"):
            continue
        link_pose, link_rpy = _pose_xyz_rpy(link)
        link_rotation = model_rotation @ _rotation_from_rpy(link_rpy)
        link_position_model = model_position + model_rotation @ link_pose
        part = _link_component(link, link_position_model, link_rotation, name)
        if part is None:
            raise ValueError(f"{name}_missing_inertial")
        parts.append(part)
        rotor_parts[name] = (part, link_rotation)

    vehicle_root = ET.parse(vehicle_model_path).getroot().find("model")
    camera_root = ET.parse(camera_model_path).getroot().find("model")
    if vehicle_root is None or camera_root is None:
        raise ValueError("vehicle_or_camera_model_missing")
    mount = vehicle_root.find("./joint[@name='d435i_mount']/pose")
    if mount is None:
        raise ValueError("d435i_mount_pose_missing")
    mount_values = [float(x) for x in mount.text.split()]
    if len(mount_values) != 6:
        raise ValueError("invalid_d435i_mount_pose")
    camera_position_base = np.asarray(mount_values[:3], dtype=float)
    camera_rotation_base = _rotation_from_rpy(mount_values[3:])
    camera_link = camera_root.find("./link[@name='d435i_link']")
    if camera_link is None:
        raise ValueError("d435i_link_missing")
    camera_link_pose, camera_link_rpy = _pose_xyz_rpy(camera_link)
    camera_link_rotation = _rotation_from_rpy(camera_link_rpy)
    camera_position_model = (
        base_link_position_model
        + base_link_rotation_model @ (
            camera_position_base + camera_rotation_base @ camera_link_pose
        )
    )
    camera_rotation_model = (
        base_link_rotation_model @ camera_rotation_base @ camera_link_rotation
    )
    camera_part = _link_component(
        camera_link,
        camera_position_model,
        camera_rotation_model,
        "d435i_link",
    )
    if camera_part is None:
        raise ValueError("d435i_link_missing_inertial")
    parts.append(camera_part)

    total_mass = sum(part["mass"] for part in parts)
    com = sum((part["mass"] * part["position"] for part in parts), start=np.zeros(3)) / total_mass
    total_inertia = np.zeros((3, 3), dtype=float)
    eye = np.eye(3)
    for part in parts:
        offset = part["position"] - com
        total_inertia += part["inertia"] + part["mass"] * (
            float(offset @ offset) * eye - np.outer(offset, offset)
        )
    total_inertia_eigenvalues = np.linalg.eigvalsh(total_inertia)

    plugins = []
    airframe_root = ET.parse(airframe_path).getroot().find("model")
    if airframe_root is None:
        raise ValueError("airframe_model_sdf_missing_model")
    for plugin in airframe_root.findall("plugin"):
        if "MulticopterMotorModel" not in str(plugin.get("name", "")):
            continue
        plugins.append({
            "link_name": plugin.findtext("linkName"),
            "max_rot_velocity_rad_s": float(plugin.findtext("maxRotVelocity")),
            "time_constant_up_s": float(plugin.findtext("timeConstantUp")),
            "time_constant_down_s": float(plugin.findtext("timeConstantDown")),
            "motor_constant_n_per_rad_s2": float(plugin.findtext("motorConstant")),
            "moment_constant_m": float(plugin.findtext("momentConstant")),
            "rotor_drag_coefficient": float(plugin.findtext("rotorDragCoefficient")),
            "rolling_moment_coefficient": float(plugin.findtext("rollingMomentCoefficient")),
        })
    if len(plugins) != 4:
        raise ValueError(f"expected_four_motor_plugins_got_{len(plugins)}")
    by_link = {item["link_name"]: item for item in plugins}
    if len(by_link) != len(plugins) or set(by_link) != set(rotor_parts):
        raise ValueError("motor_plugin_and_rotor_link_sets_differ")

    max_thrusts = []
    rotor_arms = []
    spin_inertias = []
    rotor_speeds = []
    rotor_speed_delta_max = []
    rotor_time_constant_up = []
    rotor_time_constant_down = []
    moment_constants = []
    drag_coefficients = []
    rolling_coefficients = []
    for name, (part, rotation) in rotor_parts.items():
        motor = by_link[name]
        thrust = motor["motor_constant_n_per_rad_s2"] * motor["max_rot_velocity_rad_s"] ** 2
        max_thrusts.append(thrust)
        rotor_arms.append(float(np.linalg.norm(part["position"] - com)))
        rotor_axis = rotation[:, 2]
        spin_inertias.append(float(rotor_axis @ part["inertia"] @ rotor_axis))
        rotor_speeds.append(motor["max_rot_velocity_rad_s"])
        tau_up = motor["time_constant_up_s"]
        tau_down = motor["time_constant_down_s"]
        if (not math.isfinite(tau_up) or not math.isfinite(tau_down)
                or tau_up <= 0.0 or tau_down <= 0.0):
            raise ValueError(f"{name}_motor_filter_time_constant_invalid")
        rotor_time_constant_up.append(tau_up)
        rotor_time_constant_down.append(tau_down)
        maximum_filter_fraction = max(
            1.0 - math.exp(-step / tau_up),
            1.0 - math.exp(-step / tau_down),
        )
        rotor_speed_delta_max.append(
            motor["max_rot_velocity_rad_s"] * maximum_filter_fraction
        )
        moment_constants.append(motor["moment_constant_m"])
        drag_coefficients.append(motor["rotor_drag_coefficient"])
        rolling_coefficients.append(motor["rolling_moment_coefficient"])
    max_speeds = np.asarray(rotor_speeds)
    if np.any(max_speeds <= 0) or np.max(max_speeds) != np.min(max_speeds):
        raise ValueError("motor_speed_limits_not_uniform_positive")
    imu_to_com = com - camera_position_model
    model_origin_to_com = com
    model_origin_to_base_link = base_link_position_model
    motor_rotation_accel_torque_step = sum(
        inertia * delta_speed / step
        for inertia, delta_speed in zip(spin_inertias, rotor_speed_delta_max)
    )
    return {
        "physics_step_s": step,
        "gravity_m_s2": gravity,
        "total_mass_kg": total_mass,
        "com_position_truth_model_m": com.tolist(),
        "model_origin_to_com_vector_m": model_origin_to_com.tolist(),
        "model_origin_to_com_radius_m": float(np.linalg.norm(model_origin_to_com)),
        "truth_model_to_base_link_position_m": model_origin_to_base_link.tolist(),
        "truth_model_to_base_link_rotation_matrix": base_link_rotation_model.tolist(),
        "imu_position_model_m": camera_position_model.tolist(),
        "imu_to_com_vector_m": imu_to_com.tolist(),
        "imu_to_com_radius_m": float(np.linalg.norm(imu_to_com)),
        "base_inertia_min_eigenvalue_kg_m2": float(np.min(base_inertia_eigenvalues)),
        "total_inertia_max_eigenvalue_kg_m2": float(np.max(total_inertia_eigenvalues)),
        "total_inertia_eigenvalues_kg_m2": total_inertia_eigenvalues.tolist(),
        "max_motor_thrusts_n": max_thrusts,
        "sum_max_motor_thrust_n": float(sum(max_thrusts)),
        "motor_arm_radii_m": rotor_arms,
        "max_motor_arm_m": float(max(rotor_arms)),
        "motor_reaction_torque_bounds_nm": [
            moment * thrust for moment, thrust in zip(moment_constants, max_thrusts)
        ],
        "rotor_spin_inertias_kg_m2": spin_inertias,
        "rotor_speed_max_rad_s": max_speeds.tolist(),
        "rotor_speed_time_constant_up_s": rotor_time_constant_up,
        "rotor_speed_time_constant_down_s": rotor_time_constant_down,
        "rotor_speed_max_change_per_step_rad_s": rotor_speed_delta_max,
        "rotor_spin_step_impulse_equivalent_torque_bound_nm": motor_rotation_accel_torque_step,
        "rotor_drag_coefficients": drag_coefficients,
        "rolling_moment_coefficients": rolling_coefficients,
        "source_identity": {
            "world": str(world_path),
            "world_sha256": sha256(world_path),
            "base_model": str(base_model_path),
            "base_model_sha256": sha256(base_model_path),
            "airframe_model": str(airframe_path),
            "airframe_model_sha256": sha256(airframe_path),
            "vehicle_model": str(vehicle_model_path),
            "vehicle_model_sha256": sha256(vehicle_model_path),
            "camera_model": str(camera_model_path),
            "camera_model_sha256": sha256(camera_model_path),
        },
    }


def interval_motion_allowance(dt_s, endpoint_speed_m_s, endpoint_rate_rad_s,
                              point_acceleration_bound_m_s2,
                              angular_acceleration_bound_rad_s2,
                              body_radius_m):
    values = [
        dt_s, endpoint_speed_m_s, endpoint_rate_rad_s,
        point_acceleration_bound_m_s2,
        angular_acceleration_bound_rad_s2, body_radius_m,
    ]
    if not all(math.isfinite(float(x)) for x in values):
        raise ValueError("nonfinite_interval_bound_input")
    if dt_s <= 0 or min(values[1:]) < 0:
        raise ValueError("invalid_interval_bound_input")
    speed_bound = endpoint_speed_m_s + point_acceleration_bound_m_s2 * dt_s
    rate_bound = endpoint_rate_rad_s + angular_acceleration_bound_rad_s2 * dt_s
    point_speed_bound = speed_bound + body_radius_m * rate_bound
    return {
        "endpoint_speed_upper_m_s": float(endpoint_speed_m_s),
        "endpoint_angular_rate_upper_rad_s": float(endpoint_rate_rad_s),
        "within_step_speed_bound_m_s": float(speed_bound),
        "within_step_angular_rate_bound_rad_s": float(rate_bound),
        "body_point_speed_bound_m_s": float(point_speed_bound),
        "maximum_nearest_endpoint_motion_m": float(point_speed_bound * dt_s / 2.0),
    }


def _interval_dynamics_bound(endpoint_speed, endpoint_rate, dt, dynamics):
    alpha = 0.0
    max_thrust = dynamics["sum_max_motor_thrust_n"]
    mass = dynamics["total_mass_kg"]
    gravity = dynamics["gravity_m_s2"]
    r_model_origin = dynamics["model_origin_to_com_radius_m"]
    r_arm = dynamics["max_motor_arm_m"]
    i_min = dynamics["base_inertia_min_eigenvalue_kg_m2"]
    i_max = dynamics["total_inertia_max_eigenvalue_kg_m2"]
    h_rotor = sum(
        inertia * speed for inertia, speed in zip(
            dynamics["rotor_spin_inertias_kg_m2"],
            dynamics["rotor_speed_max_rad_s"],
        )
    )
    tau_arm = sum(
        thrust * arm for thrust, arm in zip(
            dynamics["max_motor_thrusts_n"], dynamics["motor_arm_radii_m"]
        )
    )
    tau_reaction = sum(dynamics["motor_reaction_torque_bounds_nm"])
    tau_spin = dynamics["rotor_spin_step_impulse_equivalent_torque_bound_nm"]
    omega_motor = np.asarray(dynamics["rotor_speed_max_rad_s"], dtype=float)
    drag_coeff = np.asarray(dynamics["rotor_drag_coefficients"], dtype=float)
    rolling_coeff = np.asarray(dynamics["rolling_moment_coefficients"], dtype=float)

    result = None
    for _ in range(100):
        omega_bound = endpoint_rate + alpha * dt
        model_origin_speed_bound = endpoint_speed
        for _ in range(100):
            com_speed_bound = model_origin_speed_bound + omega_bound * r_model_origin
            rotor_speed_bound = com_speed_bound + omega_bound * r_arm
            drag_force_bound = float(np.sum(drag_coeff * omega_motor * rotor_speed_bound))
            com_acceleration_bound = max_thrust / mass + gravity + drag_force_bound / mass
            model_origin_acceleration_bound = (
                com_acceleration_bound
                + r_model_origin * (alpha + omega_bound * omega_bound)
            )
            new_model_origin_speed_bound = (
                endpoint_speed + model_origin_acceleration_bound * dt
            )
            if abs(new_model_origin_speed_bound - model_origin_speed_bound) <= 1e-10:
                model_origin_speed_bound = new_model_origin_speed_bound
                break
            model_origin_speed_bound = new_model_origin_speed_bound
        else:
            raise ValueError("linear_speed_bound_did_not_converge")

        com_speed_bound = model_origin_speed_bound + omega_bound * r_model_origin
        rotor_speed_bound = com_speed_bound + omega_bound * r_arm
        drag_force_bound = float(np.sum(drag_coeff * omega_motor * rotor_speed_bound))
        rolling_torque_bound = float(np.sum(
            rolling_coeff * omega_motor * rotor_speed_bound
        ))
        torque_bound = (
            tau_arm + tau_reaction + tau_spin
            + drag_force_bound * r_arm + rolling_torque_bound
            + i_max * omega_bound * omega_bound + h_rotor * omega_bound
        )
        required_alpha = torque_bound / i_min
        result = {
            "alpha_candidate_rad_s2": float(alpha),
            "alpha_required_rad_s2": float(required_alpha),
            "omega_bound_rad_s": float(omega_bound),
            "model_origin_speed_bound_m_s": float(model_origin_speed_bound),
            "model_origin_acceleration_bound_m_s2": float(model_origin_acceleration_bound),
            "com_acceleration_bound_m_s2": float(com_acceleration_bound),
            "rotor_link_speed_bound_m_s": float(rotor_speed_bound),
            "rotor_drag_force_bound_n": float(drag_force_bound),
            "torque_bound_nm": float(torque_bound),
            "torque_terms_nm": {
                "motor_thrust_arms": float(tau_arm),
                "aerodynamic_reaction": float(tau_reaction),
                "filter_limited_rotor_speed_step_momentum": float(tau_spin),
                "rotor_drag_at_arm": float(drag_force_bound * r_arm),
                "rolling_moment": float(rolling_torque_bound),
                "rigid_body_gyroscopic": float(i_max * omega_bound * omega_bound),
                "rotor_gyroscopic": float(h_rotor * omega_bound),
            },
        }
        if required_alpha <= alpha + max(1e-8, alpha * 1e-9):
            result["alpha_bound_rad_s2"] = float(max(alpha, required_alpha))
            result["self_consistent"] = True
            return result
        alpha = required_alpha
    raise ValueError("angular_acceleration_bound_did_not_converge")


def _classify_dynamics_bound(endpoint_speed, endpoint_rate, dt, dynamics):
    """Keep a failed physical bound explicit instead of aborting the archive audit."""
    try:
        result = _interval_dynamics_bound(endpoint_speed, endpoint_rate, dt, dynamics)
    except (ValueError, FloatingPointError, OverflowError) as exc:
        return {
            "classification": "dynamics_bound_unavailable",
            "reason": str(exc),
        }
    return {
        "classification": "model_bounded_no_contact_interval",
        "dynamics": result,
    }


def _physics_endpoint_rows(run, rows):
    exact_rows, evidence = instantaneous_endpoints(run, rows)
    if exact_rows is None:
        return rows, None, evidence
    source_stamps = [int(row["stamp_ns"]) for row in rows]
    exact_stamps = [int(row["stamp_ns"]) for row in exact_rows]
    if exact_stamps != source_stamps:
        raise ValueError("instantaneous_endpoint_time_grid_mismatch")
    return exact_rows, exact_rows, evidence


def _sample_clearances(rows, envelope_geometry, obstacles,
                       model_to_base_position, model_to_base_rotation):
    bounds = envelope_geometry["collision_bounds_xyz_m"]
    z_min_local = min(float(v) for v in bounds[2])
    z_max_local = max(float(v) for v in bounds[2])
    body_radius = float(envelope_geometry["orientation_invariant_rotor_sweep_radius_m"])
    base_offset = np.asarray(model_to_base_position, dtype=float)
    base_rotation = np.asarray(model_to_base_rotation, dtype=float)
    clearances = []
    for row in rows:
        model_position = np.asarray(row["xyz"], dtype=float)
        model_rotation = quaternion_rotation(row["q_xyzw"])
        position = model_position + model_rotation @ base_offset
        base_q = _quaternion_from_rotation(model_rotation @ base_rotation)
        radius, z_min, z_max, _ = vehicle_vertical_cylinder(
            position, base_q, body_radius, z_min_local, z_max_local
        )
        clearance = min(
            distance_to_obstacle(position, radius, z_min, z_max, obstacle)
            for obstacle in obstacles
        )
        clearances.append(float(clearance))
    return clearances, body_radius, z_min_local, z_max_local


def _quaternion_from_rotation(rotation):
    matrix = np.asarray(rotation, dtype=float)
    if matrix.shape != (3, 3) or not np.isfinite(matrix).all():
        raise ValueError("invalid_rotation_matrix")
    trace = float(np.trace(matrix))
    if trace > 0.0:
        scale = math.sqrt(trace + 1.0) * 2.0
        q = np.array([
            (matrix[2, 1] - matrix[1, 2]) / scale,
            (matrix[0, 2] - matrix[2, 0]) / scale,
            (matrix[1, 0] - matrix[0, 1]) / scale,
            0.25 * scale,
        ])
    elif matrix[0, 0] > matrix[1, 1] and matrix[0, 0] > matrix[2, 2]:
        scale = math.sqrt(1.0 + matrix[0, 0] - matrix[1, 1] - matrix[2, 2]) * 2.0
        q = np.array([
            0.25 * scale,
            (matrix[0, 1] + matrix[1, 0]) / scale,
            (matrix[0, 2] + matrix[2, 0]) / scale,
            (matrix[2, 1] - matrix[1, 2]) / scale,
        ])
    elif matrix[1, 1] > matrix[2, 2]:
        scale = math.sqrt(1.0 + matrix[1, 1] - matrix[0, 0] - matrix[2, 2]) * 2.0
        q = np.array([
            (matrix[0, 1] + matrix[1, 0]) / scale,
            0.25 * scale,
            (matrix[1, 2] + matrix[2, 1]) / scale,
            (matrix[0, 2] - matrix[2, 0]) / scale,
        ])
    else:
        scale = math.sqrt(1.0 + matrix[2, 2] - matrix[0, 0] - matrix[1, 1]) * 2.0
        q = np.array([
            (matrix[0, 2] + matrix[2, 0]) / scale,
            (matrix[1, 2] + matrix[2, 1]) / scale,
            0.25 * scale,
            (matrix[1, 0] - matrix[0, 1]) / scale,
        ])
    q /= np.linalg.norm(q)
    return q.tolist()


def _body_point_radius_from_model_origin(body_radius, z_min, z_max,
                                          model_to_base_position,
                                          model_to_base_rotation):
    offset = np.asarray(model_to_base_position, dtype=float)
    rotation = np.asarray(model_to_base_rotation, dtype=float)
    if offset.shape != (3,) or rotation.shape != (3, 3):
        raise ValueError("invalid_truth_model_to_base_link_transform")
    if not np.isfinite(offset).all() or not np.isfinite(rotation).all():
        raise ValueError("nonfinite_truth_model_to_base_link_transform")
    model_origin_in_base = rotation.T @ offset
    horizontal = float(np.linalg.norm(model_origin_in_base[:2])) + float(body_radius)
    vertical = max(
        abs(float(model_origin_in_base[2]) + float(z_min)),
        abs(float(model_origin_in_base[2]) + float(z_max)),
    )
    return math.hypot(horizontal, vertical)


def _contact_step_classes(contact_path, start_ns, end_ns, allowed_ground_collisions):
    report = json.loads(contact_path.read_text())
    classified = {}
    goal_event_count = 0
    for event in report.get("events", []):
        stamp = int(event["stamp_ns"])
        if stamp < start_ns or stamp > end_ns:
            continue
        goal_event_count += 1
        pairs = event.get("pairs", [])
        allowed_event = bool(pairs)
        for pair in pairs:
            c1 = str(pair.get("collision1", ""))
            c2 = str(pair.get("collision2", ""))
            if c1.startswith("ground_plane::"):
                ground_name, vehicle_name = c1, c2
            elif c2.startswith("ground_plane::"):
                ground_name, vehicle_name = c2, c1
            else:
                allowed_event = False
                continue
            vehicle_collision = vehicle_name.rsplit("::", 1)[-1]
            if (ground_name != "ground_plane::link::collision"
                    or vehicle_collision not in allowed_ground_collisions):
                allowed_event = False
        kind = "allowed_ground" if allowed_event else "prohibited"
        if classified.get(stamp) == "prohibited" or kind == "prohibited":
            classified[stamp] = "prohibited"
        else:
            classified[stamp] = kind
    return classified, report, goal_event_count


def evaluate(run, envelope_path, world_sdf, vehicle_model, camera_model,
             base_model, airframe_model, motor_source, esc_source):
    flight = json.loads((run / "flight.json").read_text())
    truth_report = json.loads((run / "debug-truth-evaluation.json").read_text())
    truth = truth_report.get("samples") or []
    goal_start = int((flight.get("goal") or {})["source_ns"])
    bridge_rows = [
        json.loads(line) for line in (run / "bridge-alignment-timeline.jsonl").read_text().splitlines()
        if line.strip()
    ]
    landed = [
        int(row["stamp_ns"]) for row in bridge_rows
        if row.get("phase") == "LANDED" and int(row["stamp_ns"]) >= goal_start
    ]
    if not landed:
        raise ValueError("no_bridge_landed_stamp_after_goal")
    goal_end = min(landed)
    rows = [
        row for row in truth
        if goal_start <= int(row["stamp_ns"]) <= goal_end
    ]
    stamps = np.asarray([int(row["stamp_ns"]) for row in rows], dtype=np.int64)
    if len(rows) < 3 or np.any(np.diff(stamps) <= 0):
        raise ValueError("insufficient_or_nonmonotonic_truth")
    world_step = _parse_model_physics(
        world_sdf, base_model, airframe_model, vehicle_model, camera_model
    )
    step_s = world_step["physics_step_s"]
    gaps_s = np.diff(stamps) / 1e9
    if np.any(np.abs(gaps_s - step_s) > 2e-9):
        raise ValueError("truth_does_not_cover_each_configured_physics_step")
    if not np.isfinite(np.asarray([r["xyz"] for r in rows], dtype=float)).all():
        raise ValueError("nonfinite_truth_pose")
    for row in rows:
        for key in ("linear_velocity_xyz_m_s", "angular_velocity_xyz_rad_s"):
            value = np.asarray(row.get(key, []), dtype=float)
            if value.shape != (3,) or not np.isfinite(value).all():
                raise ValueError(f"missing_or_invalid_truth_{key}")

    rows, exact_rows, velocity_evidence = _physics_endpoint_rows(run, rows)
    if exact_rows is not None:
        exact_stamps = np.asarray([int(row["stamp_ns"]) for row in exact_rows], dtype=np.int64)
        if not np.array_equal(exact_stamps, stamps):
            raise ValueError("instantaneous_endpoint_time_grid_mismatch")

    envelope = json.loads(envelope_path.read_text())["geometry"]
    obstacles, skipped = parse_obstacles(world_sdf)
    truth_contract = model_to_imu_contract(run)
    model_to_base_position = np.asarray(truth_contract["model_origin_to_imu_m"], dtype=float)
    if not np.allclose(model_to_base_position, world_step["imu_position_model_m"], atol=1e-12, rtol=0):
        raise ValueError("truth_reference_geometry_disagrees_with_dynamics_model")
    model_to_base_rotation = np.asarray(
        world_step["truth_model_to_base_link_rotation_matrix"], dtype=float
    )
    legacy_clearances, body_radius, z_min_local, z_max_local = _sample_clearances(
        rows, envelope, obstacles, model_to_base_position, model_to_base_rotation
    )
    collision_components = _collision_component_spheres(
        base_model, vehicle_model, camera_model
    )
    clearances, clearance_details = _sample_component_sphere_clearances(
        rows, collision_components, obstacles
    )
    body_point_radius = _body_point_radius_from_model_origin(
        body_radius, z_min_local, z_max_local,
        model_to_base_position, model_to_base_rotation,
    )
    component_point_radius = max(
        float(np.linalg.norm(item["center_model_origin_m"]))
        + float(item["enclosing_sphere_radius_m"])
        for item in collision_components
    )
    body_point_radius = max(body_point_radius, component_point_radius)
    allowed_ground_collisions = set(envelope["ground_contact_collisions"])
    contact_by_stamp, contact_report, goal_contact_event_count = _contact_step_classes(
        run / "n09-contact-observation.json", int(stamps[0]), int(stamps[-1]),
        allowed_ground_collisions,
    )
    contact_stamps = sorted(contact_by_stamp)
    contact_evaluation = json.loads((run / "vehicle-contact-evaluation.json").read_text())
    runtime_contract = json.loads((run / "runtime-contract.json").read_text())
    contact_identity = contact_report.get("run_identity", {})
    runtime_contract_sha = runtime_contract.get("sha256")
    contact_identity_checks = {
        "complete_identity": contact_identity.get("complete") is True,
        "run_id_matches": contact_identity.get("run_id") == run.name,
        "goal_id_matches": contact_identity.get("goal_id") == flight.get("goal_id"),
        "epoch_matches": contact_identity.get("epoch") == flight.get("localization_epoch"),
        "runtime_contract_matches": contact_identity.get("runtime_contract_sha256") == runtime_contract_sha,
    }

    intervals = []
    for index, (left, right) in enumerate(zip(rows[:-1], rows[1:])):
        t0, t1 = int(stamps[index]), int(stamps[index + 1])
        dt = (t1 - t0) / 1e9
        first_contact = bisect.bisect_left(contact_stamps, t0)
        contact_in_interval = (
            first_contact < len(contact_stamps) and contact_stamps[first_contact] <= t1
        )
        if contact_in_interval:
            contact_kind = "prohibited" if any(
                contact_by_stamp[stamp] == "prohibited"
                for stamp in contact_stamps[first_contact:bisect.bisect_right(contact_stamps, t1)]
            ) else "allowed_ground"
            intervals.append({
                "index": index, "start_ns": t0, "end_ns": t1,
                "duration_s": dt,
                "classification": "contact_interval_not_dynamics_bounded",
                "contact_kind": contact_kind,
                "sampled_endpoint_clearance_min_m": min(clearances[index], clearances[index + 1]),
            })
            continue
        v_end = max(
            float(np.linalg.norm(left["linear_velocity_xyz_m_s"])),
            float(np.linalg.norm(right["linear_velocity_xyz_m_s"])),
        )
        w_end = max(
            float(np.linalg.norm(left["angular_velocity_xyz_rad_s"])),
            float(np.linalg.norm(right["angular_velocity_xyz_rad_s"])),
        )
        bound_result = _classify_dynamics_bound(v_end, w_end, dt, world_step)
        if bound_result["classification"] == "dynamics_bound_unavailable":
            intervals.append({
                "index": index,
                "start_ns": t0,
                "end_ns": t1,
                "duration_s": dt,
                "classification": "dynamics_bound_unavailable",
                "reason": bound_result["reason"],
                "endpoint_clearance_min_m": min(clearances[index], clearances[index + 1]),
            })
            continue
        dynamics_bound = bound_result["dynamics"]
        motion = interval_motion_allowance(
            dt,
            v_end,
            w_end,
            dynamics_bound["model_origin_acceleration_bound_m_s2"],
            dynamics_bound["alpha_bound_rad_s2"],
            body_point_radius,
        )
        lower = min(clearances[index], clearances[index + 1]) - motion["maximum_nearest_endpoint_motion_m"]
        intervals.append({
            "index": index,
            "start_ns": t0,
            "end_ns": t1,
            "duration_s": dt,
            "classification": "model_bounded_no_contact_interval",
            "endpoint_clearance_min_m": min(clearances[index], clearances[index + 1]),
            "motion_allowance_m": motion["maximum_nearest_endpoint_motion_m"],
            "clearance_lower_bound_m": float(lower),
            "dynamics": dynamics_bound,
            "motion": motion,
        })

    bounded = [x for x in intervals if x["classification"] == "model_bounded_no_contact_interval"]
    contact_intervals = [x for x in intervals if x["classification"] == "contact_interval_not_dynamics_bounded"]
    unavailable_bound_intervals = [
        x for x in intervals if x["classification"] == "dynamics_bound_unavailable"
    ]
    prohibited_contact_intervals = [x for x in contact_intervals if x["contact_kind"] == "prohibited"]
    ground_contact_intervals = [x for x in contact_intervals if x["contact_kind"] == "allowed_ground"]
    min_bound_interval = min(bounded, key=lambda x: x["clearance_lower_bound_m"]) if bounded else None
    sample_min = min(clearances)
    minimum_sample_index = int(np.argmin(np.asarray(clearances, dtype=float)))
    component_geometry_complete = (
        len(clearance_details) == len(rows)
        and all(math.isfinite(float(item["clearance_m"])) for item in clearance_details)
    )
    runtime_files = runtime_contract.get("files", {})
    contact_manifest = json.loads((run / "n09-contact-model-manifest.json").read_text())
    source_lock_path = ROOT / "dependencies/sources.json"
    source_lock = json.loads(source_lock_path.read_text())
    px4_source = next(
        item for item in source_lock.get("sources", [])
        if item.get("target") == "external/PX4-Autopilot"
    )
    tool_freeze = json.loads((run / "n10-tool-freeze-used.json").read_text())
    px4_repo = ROOT / "external/PX4-Autopilot"
    px4_gz_repo = px4_repo / "Tools/simulation/gz"
    px4_gz_rel = "Tools/simulation/gz"
    airframe_rel = "models/x500/model.sdf"
    motor_rel = "src/modules/simulation/gz_plugins/generic_motor/GenericMotorModel.cpp"
    esc_rel = "src/modules/simulation/gz_bridge/GZMixingInterfaceESC.cpp"
    submodule_manifest_path = ROOT / px4_source["submodules_manifest"]
    source_identity_error = None
    try:
        px4_commit = subprocess.check_output(
            ["git", "-C", str(px4_repo), "rev-parse", "HEAD"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
        locked_gz_revision = subprocess.check_output(
            ["git", "-C", str(px4_repo), "rev-parse",
             f"{px4_source['target_revision']}:{px4_gz_rel}"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
        px4_gz_commit = subprocess.check_output(
            ["git", "-C", str(px4_gz_repo), "rev-parse", "HEAD"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
        submodule_manifest = json.loads(submodule_manifest_path.read_text())
        gz_manifest_entry = next(
            item for item in submodule_manifest.get("submodules", [])
            if item.get("path") == px4_gz_rel
        )
        airframe_at_lock = subprocess.check_output(
            ["git", "-C", str(px4_gz_repo), "show",
             f"{gz_manifest_entry['revision']}:{airframe_rel}"]
        )
        motor_at_lock = subprocess.check_output(
            ["git", "-C", str(px4_repo), "show", f"{px4_source['target_revision']}:{motor_rel}"]
        )
        esc_at_lock = subprocess.check_output(
            ["git", "-C", str(px4_repo), "show", f"{px4_source['target_revision']}:{esc_rel}"]
        )
        airframe_clean = subprocess.run(
            ["git", "-C", str(px4_gz_repo), "diff", "--quiet", "HEAD", "--", airframe_rel],
            check=False,
        ).returncode == 0
        motor_clean = subprocess.run(
            ["git", "-C", str(px4_repo), "diff", "--quiet", "HEAD", "--", motor_rel],
            check=False,
        ).returncode == 0
        esc_clean = subprocess.run(
            ["git", "-C", str(px4_repo), "diff", "--quiet", "HEAD", "--", esc_rel],
            check=False,
        ).returncode == 0
    except (OSError, KeyError, StopIteration, subprocess.CalledProcessError,
            json.JSONDecodeError, TypeError, ValueError) as exc:
        source_identity_error = f"{type(exc).__name__}:{exc}"
        px4_commit = None
        locked_gz_revision = None
        px4_gz_commit = None
        gz_manifest_entry = {}
        airframe_at_lock = motor_at_lock = esc_at_lock = b""
        airframe_clean = motor_clean = esc_clean = False

    lock_sha = sha256(source_lock_path)
    image_lock_matches = (
        tool_freeze.get("container_image_id")
        == source_lock.get("container_rebuild", {}).get("derived_image_id")
    )
    source_identity_checks = {
        "run_runtime_contract_binds_source_lock": runtime_files.get("dependencies/sources.json") == lock_sha,
        "px4_checkout_matches_locked_revision": px4_commit == px4_source.get("target_revision"),
        "px4_gz_submodule_matches_parent_gitlink_and_lock": (
            locked_gz_revision == px4_gz_commit == gz_manifest_entry.get("revision")
            and _sha256_bytes(submodule_manifest_path.read_bytes())
            == px4_source.get("submodules_manifest_sha256")
        ),
        "run_freeze_binds_locked_derived_image": image_lock_matches,
        "run_freeze_declares_pre_sitl_current_source": tool_freeze.get("created_from_current_source_before_sitl") is True,
        "airframe_sdf_matches_locked_revision_and_is_clean": (
            airframe_clean and _sha256_bytes(airframe_at_lock) == sha256(airframe_model)
        ),
        "motor_plugin_matches_locked_revision_and_is_clean": (
            motor_clean and _sha256_bytes(motor_at_lock) == sha256(motor_source)
        ),
        "esc_bridge_matches_locked_revision_and_is_clean": (
            esc_clean and _sha256_bytes(esc_at_lock) == sha256(esc_source)
        ),
        "runtime_contract_vehicle_model_matches": runtime_files.get("simulation/models/x500_d435i/model.sdf") == sha256(vehicle_model),
        "runtime_contract_camera_model_matches": runtime_files.get("simulation/models/d435i/model.sdf") == sha256(camera_model),
        "contact_manifest_base_model_matches": contact_manifest.get("source_sha256", {}).get("simulation/models/x500_base/model.sdf") == sha256(base_model),
    }
    identity_checks = {
        **source_identity_checks,
        **{f"contact_{key}": value for key, value in contact_identity_checks.items()},
        "vehicle_contact_evaluation_passed": contact_evaluation.get("passed") is True,
        "vehicle_contact_evaluation_reports_zero_prohibited": contact_evaluation.get("prohibited_contact_event_count") == 0,
        "contact_observer_ready_and_terminal": (
            contact_report.get("ready") is True
            and contact_report.get("terminal_flight_record_observed") is True
            and contact_report.get("safe_session_terminal_observed") is True
        ),
    }
    # Old rolling-mean twist remains diagnostic. Only identity-bound physics
    # endpoint states can support a verified no-contact interval bound.
    if not all(source_identity_checks.values()):
        status = "INSUFFICIENT_MODEL_IDENTITY"
    elif not all(contact_identity_checks.values()) or not identity_checks["contact_observer_ready_and_terminal"]:
        status = "INSUFFICIENT_CONTACT_EVIDENCE"
    elif prohibited_contact_intervals or contact_evaluation.get("prohibited_contact_event_count") != 0:
        status = "INSUFFICIENT_PROHIBITED_CONTACT"
    elif (contact_evaluation.get("passed") is not True
          or contact_evaluation.get("landing_ground_contact_observed") is not True):
        status = "INSUFFICIENT_CONTACT_EVALUATION"
    elif (unavailable_bound_intervals or not bounded
          or min_bound_interval["clearance_lower_bound_m"] <= 0):
        status = "INSUFFICIENT_AIRBORNE_BOUND"
    elif exact_rows is None:
        status = "INSUFFICIENT_INSTANTANEOUS_VELOCITY_EVIDENCE"
    else:
        status = "AIRBORNE_MODEL_BOUND_POSITIVE_CONTACT_PHASE_SEPARATE"

    return {
        "schema": "n10-model-bounded-interval-clearance/v3",
        "evaluator_sha256": sha256(Path(__file__)),
        "truth_reference_contract": truth_contract,
        "interval_bound_verified": status == "AIRBORNE_MODEL_BOUND_POSITIVE_CONTACT_PHASE_SEPARATE",
        "velocity_endpoint_evidence": velocity_evidence,
        "run_id": run.name,
        "classification": "offline SITL-only inter-solver-step geometric lower-bound; not a real-aircraft or final acceptance threshold",
        "formal_qualification": False,
        "status": status,
        "flight_interval": {
            "start_source_ns": int(stamps[0]),
            "end_source_ns": int(stamps[-1]),
            "duration_s": float((stamps[-1] - stamps[0]) / 1e9),
            "solver_state_count": len(rows),
            "step_s": step_s,
            "maximum_observed_step_gap_s": float(np.max(gaps_s)),
            "every_solver_step_present": True,
        },
        "interval_partition_coverage": {
            "expected_adjacent_interval_count": max(0, len(rows) - 1),
            "reported_interval_count": len(intervals),
            "bounded_no_contact_interval_count": len(bounded),
            "unavailable_no_contact_interval_count": len(unavailable_bound_intervals),
            "contact_interval_count": len(contact_intervals),
            "complete_partition": len(intervals) == max(0, len(rows) - 1),
        },
        "body_envelope": {
            "source": str(envelope_path),
            "truth_pose_reference": "Gazebo OdometryPublisher model origin",
            "collision_geometry_reference": "SDF vehicle collision boxes in Gazebo model-origin coordinates",
            "truth_model_to_imu_position_m": model_to_base_position.tolist(),
            "truth_model_to_imu_rotation_matrix": model_to_base_rotation.tolist(),
            "legacy_imu_envelope_yaw_swept_horizontal_radius_m": body_radius,
            "legacy_imu_envelope_local_z_bounds_m": [z_min_local, z_max_local],
            "maximum_body_point_radius_from_truth_model_origin_m": body_point_radius,
            "clearance_geometry": "one circumscribed sphere per SDF collision box, transformed from Gazebo model-origin truth pose; rotor-link boxes are enclosed for every rotor angle",
            "interval_motion_geometry": "body-point speed bounded by model-origin speed plus body-point-radius-from-model-origin times angular-rate bound",
        },
        "collision_component_sphere_geometry": {
            "schema": "n10-sdf-collision-component-spheres/v1",
            "component_count": len(collision_components),
            "complete_for_parsed_vehicle_models": component_geometry_complete,
            "components": collision_components,
            "source_sha256": {
                str(path): sha256(path)
                for path in (base_model, vehicle_model, camera_model)
            },
            "method": "Each SDF collision box is enclosed by its circumscribed sphere; the rotor-link collision sphere is invariant to rotor yaw. Obstacle surface distance is reduced by the component radius and clamped to zero for overlap.",
        },
        "solver_state_clearance": {
            "status": "COMPLETE" if component_geometry_complete else "INSUFFICIENT",
            "geometry_schema": "n10-sdf-collision-component-spheres/v1",
            "solver_state_count": len(rows),
            "clearance_sample_count": len(clearance_details),
            "all_solver_states_have_clearance": component_geometry_complete,
            "minimum_component_clearance_m": float(sample_min),
            "limiting_solver_state": clearance_details[minimum_sample_index],
            "legacy_whole_vehicle_cylinder_minimum_clearance_m": float(min(legacy_clearances)),
            "legacy_whole_vehicle_cylinder_is_acceptance_geometry": False,
        },
        "model_dynamics_bound": {
            **world_step,
            "assumptions": [
                "PX4 ESC outputs are unsigned uint16 values. For velocity-mode motors, GenericMotorModel clamps the nonnegative command to maxRotVelocity; the filter state starts from that bounded command and its first-order recurrence stays within the command range.",
                "Per-step rotor-speed change is bounded by maxRotVelocity * max(1-exp(-dt/timeConstantUp), 1-exp(-dt/timeConstantDown)), using the SDF filter constants and physics step; rotor angular-momentum change is converted to a conservative step-equivalent torque.",
                "The world has zero wind and all rotor drag/rolling moment terms are included using a self-consistent upper bound on rotor-link speed.",
                "No obstacle-contact impulse occurs inside a dynamics-bounded interval; contact intervals are reported separately.",
                "Base-link inertia is a lower bound on whole-vehicle rotational inertia; total inertial tensor gives the gyroscopic upper bound.",
                "Truth translation and velocity are referenced to the Gazebo model origin; translational acceleration and the body-point rotation radius are bounded from that origin.",
                "The x500_base SDF model pose is applied as the model-origin-to-base_link transform; collision geometry remains in base_link coordinates.",
            ],
            "source_files": {
                str(path): sha256(path) for path in (
                    base_model, airframe_model, vehicle_model, camera_model,
                    motor_source, esc_source, world_sdf, envelope_path,
                )
            },
            "px4_source_revision": px4_commit,
            "px4_gz_submodule_revision": px4_gz_commit,
            "source_identity_error": source_identity_error,
            "runtime_model_identity_checks": identity_checks,
            "source_lock_identity_checks": source_identity_checks,
            "source_identity_matches_run_model_inputs": all(source_identity_checks.values()),
            "airframe_identity_binding_note": "The run did not separately record x500/model.sdf SHA. Its frozen runtime contract records the exact dependency-lock SHA, the freeze record binds the derived image and says it was created before SITL from current source, and the PX4 revision, Gazebo submodule gitlink/manifest, and model file are checked against that locked chain here. This is a lock-derived source identity chain, not a direct per-run SDF hash.",
            "motor_speed_clamp_source": str(motor_source),
            "unsigned_esc_output_source": str(esc_source),
        },
        "airborne_intervals": {
            "status": status,
            "count": len(bounded),
            "dynamics_bound_unavailable_interval_count": len(unavailable_bound_intervals),
            "dynamics_bound_unavailable_intervals": unavailable_bound_intervals,
            "duration_s": float(sum(x["duration_s"] for x in bounded)),
            "min_clearance_lower_bound_m": (
                float(min_bound_interval["clearance_lower_bound_m"])
                if min_bound_interval else None
            ),
            "limiting_interval": min_bound_interval,
            "positive_lower_bound_interval_count": sum(
                x["clearance_lower_bound_m"] > 0 for x in bounded
            ),
            "nonpositive_lower_bound_interval_count": sum(
                x["clearance_lower_bound_m"] <= 0 for x in bounded
            ),
            "maximum_required_angular_acceleration_bound_rad_s2": max(
                (x["dynamics"]["alpha_bound_rad_s2"] for x in bounded), default=None
            ),
            "maximum_body_point_motion_allowance_m": max(
                (x["motion_allowance_m"] for x in bounded), default=None
            ),
        },
        "contact_intervals": {
            "total_interval_count": len(contact_intervals),
            "allowed_ground_interval_count": len(ground_contact_intervals),
            "prohibited_contact_interval_count": len(prohibited_contact_intervals),
            "contact_event_count_in_goal_window": goal_contact_event_count,
            "unique_contact_stamp_count_in_goal_window": len(contact_by_stamp),
            "allowed_ground_event_stamp_count_in_goal_window": sum(
                kind == "allowed_ground" for kind in contact_by_stamp.values()
            ),
            "prohibited_event_stamp_count_in_goal_window": sum(
                kind == "prohibited" for kind in contact_by_stamp.values()
            ),
            "allowed_ground_collision_names": sorted(allowed_ground_collisions),
            "independent_contact_evaluation": contact_evaluation,
            "contact_identity_checks": contact_identity_checks,
            "minimum_sampled_clearance_m": (
                min((x["sampled_endpoint_clearance_min_m"] for x in contact_intervals), default=None)
            ),
            "classification": "Only configured base_link_collision_3/4 against ground_plane are allowed ground contacts; intervals overlapping any other contact are prohibited and excluded from the free-flight bound.",
        },
        "whole_goal_to_landed_clearance": {
            "sampled_minimum_clearance_m": sample_min,
            "sampled_minimum_clearance_at_every_received_solver_state": (
                component_geometry_complete and sample_min > 0
            ),
            "clearance_geometry_schema": "n10-sdf-collision-component-spheres/v1",
            "continuous_interval_status": (
                "AIRBORNE_BOUND_POSITIVE_WITH_SKID_CONTACT_PHASE_SEPARATE"
                if contact_intervals and status == "AIRBORNE_MODEL_BOUND_POSITIVE_CONTACT_PHASE_SEPARATE"
                else status
            ),
            "note": "This result bounds only no-contact intervals. The skid-contact landing intervals are classified separately by collision identity and checked against the independent contact evaluation; it is not a dynamics bound through ground contact.",
        },
        "scene_geometry": {
            "source": str(world_sdf),
            "sha256": sha256(world_sdf),
            "non_ground_obstacle_count": len(obstacles),
            "skipped": skipped,
            "dynamic_spawned_obstacle_treatment": "The final static SDF is treated as present for the whole interval, which is conservative before its actual insertion time.",
        },
        "input_sha256": {
            "flight.json": sha256(run / "flight.json"),
            "debug-truth-evaluation.json": sha256(run / "debug-truth-evaluation.json"),
            "bridge-alignment-timeline.jsonl": sha256(run / "bridge-alignment-timeline.jsonl"),
            "n09-contact-observation.json": sha256(run / "n09-contact-observation.json"),
            "vehicle-contact-evaluation.json": sha256(run / "vehicle-contact-evaluation.json"),
            "runtime-contract.json": sha256(run / "runtime-contract.json"),
            "n10-tool-freeze-used.json": sha256(run / "n10-tool-freeze-used.json"),
            "n09-contact-model-manifest.json": sha256(run / "n09-contact-model-manifest.json"),
            "n10-px4-model-source.json": sha256(run / "n10-px4-model-source.json"),
            "dependencies/sources.json": sha256(source_lock_path),
            "px4_recursive_submodules_manifest": sha256(submodule_manifest_path),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--vehicle-envelope", type=Path, default=DEFAULTS["envelope"])
    parser.add_argument("--world-sdf", type=Path)
    parser.add_argument("--vehicle-model", type=Path, default=DEFAULTS["world_model"])
    parser.add_argument("--camera-model", type=Path, default=DEFAULTS["camera_model"])
    parser.add_argument("--base-model", type=Path, default=DEFAULTS["base_model"])
    parser.add_argument("--airframe-model", type=Path, default=DEFAULTS["airframe_model"])
    parser.add_argument("--motor-source", type=Path, default=DEFAULTS["motor_source"])
    parser.add_argument("--esc-source", type=Path, default=DEFAULTS["esc_source"])
    parser.add_argument("--output", type=Path,
                        help="write the report here instead of modifying the run archive")
    args = parser.parse_args()
    run = args.run.resolve()
    world_sdf = args.world_sdf.resolve() if args.world_sdf else run / "n10-dynamic-clearance-world.sdf"
    report = evaluate(
        run, args.vehicle_envelope.resolve(), world_sdf.resolve(),
        args.vehicle_model.resolve(), args.camera_model.resolve(),
        args.base_model.resolve(), args.airframe_model.resolve(),
        args.motor_source.resolve(), args.esc_source.resolve(),
    )
    output = args.output.resolve() if args.output else run / "n10-interval-clearance-bound.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "AIRBORNE_MODEL_BOUND_POSITIVE_CONTACT_PHASE_SEPARATE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
