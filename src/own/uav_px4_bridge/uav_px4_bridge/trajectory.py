"""Pure conversion from the debug ENU trajectory contract to PX4 NED."""

from __future__ import annotations

from dataclasses import dataclass
import math
import re


@dataclass(frozen=True)
class NEDTrajectorySetpoint:
    position: tuple[float, float, float]
    velocity: tuple[float, float, float]
    acceleration: tuple[float, float, float]
    yaw: float
    yaw_speed: float
    trajectory_id: int
    goal_id: str
    epoch: str


@dataclass(frozen=True)
class NEDFrameAlignment:
    origin_offset_ned: tuple[float, float, float]
    yaw_offset_ned: float


def validate_px4_runtime_profile(profile: dict, frame_contract: dict) -> None:
    """Validate an explicitly isolated truth-debug or VINS control profile."""
    name = profile.get('name')
    common_profile = (
        profile.get('gps_position_aiding_allowed') is False
        and profile.get('evaluation_ground_truth_read_only') is True
    )
    if name == 'debug_truth':
        source_valid = (
            profile.get('mapping_localization') == 'ground_truth'
            and profile.get('planner_localization') == 'ground_truth'
            and profile.get('px4_position_source') == 'debug_position'
            and profile.get('ground_truth_online_allowed') is True
            and profile.get('px4_debug_position_allowed') is True
        )
        truth_online = True
    elif name == 'vio_closed_loop':
        source_valid = (
            profile.get('mapping_localization') == 'vins'
            and profile.get('planner_localization') == 'vins'
            and profile.get('px4_position_source') == 'vins_external_odometry'
            and profile.get('ground_truth_online_allowed') is False
            and profile.get('px4_debug_position_allowed') is False
        )
        truth_online = False
    else:
        raise ValueError('unsupported PX4 runtime profile')
    if not common_profile or not source_valid:
        raise ValueError(f'invalid source-isolation flags for {name} profile')
    if (frame_contract.get('schema') != 1
            or frame_contract.get('profile') != name
            or frame_contract.get('source_world_frame') != 'ENU'
            or frame_contract.get('source_body_frame_prefix') != 'd435i_imu_'
            or frame_contract.get('px4_local_frame') != 'NED'
            or frame_contract.get('px4_body_frame') != 'FRD'
            or frame_contract.get('trajectory_input_topic') != '/position_cmd'
            or frame_contract.get('ground_truth_online_allowed') is not truth_online
            or frame_contract.get('gps_position_aiding_allowed') is not False):
        raise ValueError('unsupported PX4 frame contract configuration')


def validate_debug_truth_profile(profile: dict, frame_contract: dict) -> None:
    """Keep an explicit guard for code paths that are P3 truth-debug only."""
    if profile.get('name') != 'debug_truth':
        raise ValueError('operation requires the guarded debug_truth profile')
    validate_px4_runtime_profile(profile, frame_contract)


def _finite_vector(vector, name):
    values = tuple(float(value) for value in vector)
    if len(values) != 3 or not all(math.isfinite(value) for value in values):
        raise ValueError(f'{name} must contain three finite values')
    return values


def enu_to_ned(vector, origin_offset_ned=(0.0, 0.0, 0.0)):
    """Convert a free vector or position from ROS/Gazebo ENU to PX4 NED."""
    east, north, up = _finite_vector(vector, 'ENU vector')
    offset = _finite_vector(origin_offset_ned, 'NED origin offset')
    return north + offset[0], east + offset[1], -up + offset[2]


def yaw_enu_to_ned(yaw):
    """Convert ROS ENU yaw (CCW from east) to PX4 NED yaw (CW from north)."""
    yaw = float(yaw)
    if not math.isfinite(yaw):
        raise ValueError('yaw must be finite')
    return (math.pi / 2.0 - yaw + math.pi) % (2.0 * math.pi) - math.pi


def angle_difference(lhs, rhs):
    lhs, rhs = float(lhs), float(rhs)
    if not math.isfinite(lhs) or not math.isfinite(rhs):
        raise ValueError('angles must be finite')
    return (lhs - rhs + math.pi) % (2.0 * math.pi) - math.pi


def compute_ned_origin_offset(enu_position, px4_ned_position):
    """Align the arbitrary ENU odometry origin with PX4's local NED origin."""
    px4 = _finite_vector(px4_ned_position, 'PX4 NED position')
    enu_as_ned = enu_to_ned(enu_position)
    return tuple(target - source for target, source in zip(px4, enu_as_ned))


def rotate_ned_yaw(vector, yaw_offset_ned):
    """Rotate an NED vector around its down axis by a clockwise yaw offset."""
    north, east, down = _finite_vector(vector, 'NED vector')
    yaw = float(yaw_offset_ned)
    if not math.isfinite(yaw):
        raise ValueError('NED yaw offset must be finite')
    cosine, sine = math.cos(yaw), math.sin(yaw)
    return (cosine * north - sine * east,
            sine * north + cosine * east,
            down)


def rotate_frd_to_ned_yaw(vector_frd, yaw_ned):
    """Map a level vehicle's FRD vector into NED at the requested heading."""
    return rotate_ned_yaw(vector_frd, yaw_ned)


def rotate_frd_to_ned(vector_frd, quaternion_wxyz):
    """Rotate a PX4 FRD vector into NED using a body-to-NED quaternion."""
    vx, vy, vz = _finite_vector(vector_frd, 'FRD vector')
    q = tuple(float(value) for value in quaternion_wxyz)
    if len(q) != 4 or not all(math.isfinite(value) for value in q):
        raise ValueError('attitude quaternion must contain four finite values')
    norm = math.sqrt(sum(value * value for value in q))
    if norm < 1e-9:
        raise ValueError('attitude quaternion must be nonzero')
    w, x, y, z = (value / norm for value in q)
    tx = 2.0 * (y * vz - z * vy)
    ty = 2.0 * (z * vx - x * vz)
    tz = 2.0 * (x * vy - y * vx)
    return (vx + w * tx + y * tz - z * ty,
            vy + w * ty + z * tx - x * tz,
            vz + w * tz + x * ty - y * tx)


def px4_sensor_position_ned(body_position_ned, body_quaternion_wxyz,
                            sensor_leverarm_body_frd):
    """Convert PX4's body reference position to the mounted sensor position."""
    body_position = _finite_vector(body_position_ned, 'PX4 body position')
    leverarm = _finite_vector(sensor_leverarm_body_frd, 'sensor lever arm')
    sensor_offset = rotate_frd_to_ned(leverarm, body_quaternion_wxyz)
    return tuple(position + offset
                 for position, offset in zip(body_position, sensor_offset))


def compute_ned_frame_alignment(enu_position, enu_yaw, px4_ned_position,
                                px4_ned_yaw):
    """Pair one simultaneous source pose with PX4 local position and heading."""
    px4_position = _finite_vector(px4_ned_position, 'PX4 NED position')
    px4_yaw = float(px4_ned_yaw)
    if not math.isfinite(px4_yaw):
        raise ValueError('PX4 NED yaw must be finite')
    yaw_offset = angle_difference(px4_yaw, yaw_enu_to_ned(enu_yaw))
    source_position = rotate_ned_yaw(enu_to_ned(enu_position), yaw_offset)
    offset = tuple(target - source
                   for target, source in zip(px4_position, source_position))
    return NEDFrameAlignment(offset, yaw_offset)


def compute_rig_frame_alignment(enu_sensor_position, enu_sensor_yaw,
                                px4_body_position_ned,
                                px4_body_quaternion_wxyz,
                                px4_body_yaw_ned,
                                sensor_leverarm_body_frd):
    """Pair source sensor pose with PX4 body telemetry using the SDF lever arm."""
    sensor_position = px4_sensor_position_ned(
        px4_body_position_ned, px4_body_quaternion_wxyz,
        sensor_leverarm_body_frd)
    return compute_ned_frame_alignment(
        enu_sensor_position, enu_sensor_yaw, sensor_position, px4_body_yaw_ned)


def _quaternion_product(lhs, rhs):
    lx, ly, lz, lw = lhs
    rx, ry, rz, rw = rhs
    return (
        lw*rx + lx*rw + ly*rz - lz*ry,
        lw*ry - lx*rz + ly*rw + lz*rx,
        lw*rz + lx*ry - ly*rx + lz*rw,
        lw*rw - lx*rx - ly*ry - lz*rz,
    )


def ros_enu_flu_quaternion_to_px4_ned_frd(quaternion_xyzw):
    """Transform a ROS ENU/FLU attitude into PX4 NED/FRD, returning wxyz."""
    x, y, z, w = tuple(float(v) for v in quaternion_xyzw)
    norm = math.sqrt(x*x + y*y + z*z + w*w)
    if not math.isfinite(norm) or norm < 1e-9:
        raise ValueError('attitude quaternion must be finite and nonzero')
    q_ros = (x/norm, y/norm, z/norm, w/norm)
    root_half = math.sqrt(0.5)
    q_ned_enu = (root_half, root_half, 0.0, 0.0)
    q_flu_frd = (1.0, 0.0, 0.0, 0.0)
    q = _quaternion_product(_quaternion_product(q_ned_enu, q_ros), q_flu_frd)
    return q[3], q[0], q[1], q[2]


def apply_ned_yaw_offset(quaternion_wxyz, yaw_offset_ned):
    """Apply a constant local-NED yaw alignment to a PX4 wxyz quaternion."""
    yaw = float(yaw_offset_ned)
    if not math.isfinite(yaw):
        raise ValueError('NED yaw offset must be finite')
    w, x, y, z = tuple(float(value) for value in quaternion_wxyz)
    norm = math.sqrt(w*w + x*x + y*y + z*z)
    if not math.isfinite(norm) or norm < 1e-9:
        raise ValueError('attitude quaternion must be finite and nonzero')
    q_yaw = (0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0))
    q_body = (x / norm, y / norm, z / norm, w / norm)
    q = _quaternion_product(q_yaw, q_body)
    return q[3], q[0], q[1], q[2]


def position_command_to_ned(command, profile, frame_contract, expected_epoch=None,
                            origin_offset_ned=(0.0, 0.0, 0.0),
                            yaw_offset_ned=0.0,
                            sensor_leverarm_body_frd=(0.0, 0.0, 0.0)):
    """Validate and convert a READY EGO command for a supported ENU profile.

    Terminal and non-ready trajectory flags return ``None`` so they cannot be
    mistaken for a position setpoint. Invalid identity, frame or values raise.
    """
    validate_px4_runtime_profile(profile, frame_contract)
    ready = getattr(command, 'TRAJECTORY_STATUS_READY', 1)
    if command.trajectory_flag != ready:
        return None

    epoch = command.epoch
    if not re.fullmatch(r'[0-9a-f]{32}', epoch or ''):
        raise ValueError('READY trajectory must carry a 32-character lowercase epoch')
    if expected_epoch is not None and epoch != expected_epoch:
        raise ValueError('trajectory epoch does not match the active localization epoch')
    if command.header.frame_id != f'odom_{epoch}':
        raise ValueError('trajectory frame must match its epoch-specific ENU odometry frame')
    if not command.goal_id:
        raise ValueError('READY trajectory must carry a goal_id')
    if type(command.trajectory_id) is not int or command.trajectory_id <= 0:
        raise ValueError('READY trajectory must carry a positive trajectory_id')

    point = command.position
    velocity = command.velocity
    acceleration = command.acceleration
    yaw_speed = float(command.yaw_dot)
    if not math.isfinite(yaw_speed):
        raise ValueError('yaw_dot must be finite')
    px4_yaw = angle_difference(yaw_enu_to_ned(command.yaw) + float(yaw_offset_ned), 0.0)
    # shortcut: planner supplies yaw/yaw rate only; measure tilt/lever-arm error
    # on the final hardware mount before qualifying this path for control.
    leverarm_ned = rotate_frd_to_ned_yaw(sensor_leverarm_body_frd, px4_yaw)
    sensor_position_ned = tuple(a + b for a, b in zip(
        rotate_ned_yaw(enu_to_ned((point.x, point.y, point.z)), yaw_offset_ned),
        _finite_vector(origin_offset_ned, 'NED origin offset')))
    yaw_speed_ned = -yaw_speed
    omega_cross_leverarm = (-yaw_speed_ned * leverarm_ned[1],
                            yaw_speed_ned * leverarm_ned[0], 0.0)
    return NEDTrajectorySetpoint(
        position=tuple(sensor - offset
                       for sensor, offset in zip(sensor_position_ned, leverarm_ned)),
        velocity=tuple(value - rotational for value, rotational in zip(
            rotate_ned_yaw(enu_to_ned((velocity.x, velocity.y, velocity.z)),
                           yaw_offset_ned), omega_cross_leverarm)),
        acceleration=rotate_ned_yaw(
            enu_to_ned((acceleration.x, acceleration.y, acceleration.z)),
            yaw_offset_ned),
        yaw=px4_yaw,
        yaw_speed=yaw_speed_ned,
        trajectory_id=command.trajectory_id,
        goal_id=command.goal_id,
        epoch=epoch,
    )
