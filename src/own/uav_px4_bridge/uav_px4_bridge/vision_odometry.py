"""Convert epoch-bound ROS ENU odometry into PX4 VehicleOdometry values."""

from dataclasses import dataclass
import math
import re

from .trajectory import (apply_ned_yaw_offset, enu_to_ned,
                         ros_enu_flu_quaternion_to_px4_ned_frd,
                         rotate_ned_yaw)


@dataclass(frozen=True)
class PX4VisualOdometry:
    timestamp: int
    timestamp_sample: int
    position_ned: tuple[float, float, float]
    quaternion_ned_frd_wxyz: tuple[float, float, float, float]
    velocity_body_frd: tuple[float, float, float]
    angular_velocity_body_frd: tuple[float, float, float]
    position_variance: tuple[float, float, float]
    orientation_variance: tuple[float, float, float]
    velocity_variance: tuple[float, float, float]
    quality: int
    epoch: str


def _finite(values, name):
    values = tuple(float(value) for value in values)
    if not all(math.isfinite(value) for value in values):
        raise ValueError(f'{name} must contain only finite values')
    return values


def _variance(value, name):
    value = float(value)
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(f'{name} must be positive and finite')
    return (value, value, value)


def odometry_to_px4_values(odometry, profile, frame_contract, timestamp_us,
                            position_variance_m2, orientation_variance_rad2,
                            velocity_variance_m2_s2, source_quality,
                            expected_epoch=None,
                            timestamp_sample_us=None,
                            origin_offset_ned=(0.0, 0.0, 0.0),
                            yaw_offset_ned=0.0):
    """Convert D435i IMU-frame ENU odometry to PX4 NED/FRD fields.

    Variances are explicit profile configuration. VINS covariance is currently
    unavailable from the localization adapter, so VIO variances stay provisional.
    """
    from .trajectory import validate_px4_runtime_profile
    validate_px4_runtime_profile(profile, frame_contract)

    frame = odometry.header.frame_id
    match = re.fullmatch(r'odom_([0-9a-f]{32})', frame or '')
    if not match:
        raise ValueError('odometry frame must be odom_<32-character epoch>')
    epoch = match.group(1)
    if expected_epoch is not None and epoch != expected_epoch:
        raise ValueError('odometry epoch does not match the active localization epoch')
    expected_child = frame_contract.get('source_body_frame_prefix', '') + epoch
    if not expected_child or odometry.child_frame_id != expected_child:
        raise ValueError('odometry child frame does not match the configured sensor frame')

    source_stamp_ns = odometry.header.stamp.sec * 1_000_000_000 + odometry.header.stamp.nanosec
    timestamp_us = int(timestamp_us)
    if timestamp_sample_us is None:
        raise ValueError('timestamp_sample_us must be explicitly mapped into PX4 time')
    timestamp_sample_us = int(timestamp_sample_us)
    source_quality = int(source_quality)
    if source_stamp_ns <= 0 or timestamp_us <= 0 or timestamp_sample_us <= 0:
        raise ValueError('source, PX4, and mapped sample timestamps must be positive')
    if source_quality < 0 or source_quality > 100:
        raise ValueError('source quality must be within the PX4 range 0..100')

    pose = odometry.pose.pose
    position = _finite((pose.position.x, pose.position.y, pose.position.z), 'position')
    origin_offset_ned = _finite(origin_offset_ned, 'NED origin offset')
    if len(origin_offset_ned) != 3:
        raise ValueError('NED origin offset must contain three values')
    orientation = apply_ned_yaw_offset(
        ros_enu_flu_quaternion_to_px4_ned_frd(
            (pose.orientation.x, pose.orientation.y, pose.orientation.z,
             pose.orientation.w)), yaw_offset_ned)
    twist = odometry.twist.twist
    velocity_flu = _finite((twist.linear.x, twist.linear.y, twist.linear.z), 'linear velocity')
    angular_flu = _finite((twist.angular.x, twist.angular.y, twist.angular.z), 'angular velocity')
    return PX4VisualOdometry(
        timestamp=timestamp_us,
        timestamp_sample=timestamp_sample_us,
        position_ned=tuple(a + b for a, b in zip(
            rotate_ned_yaw(enu_to_ned(position), yaw_offset_ned),
            origin_offset_ned)),
        quaternion_ned_frd_wxyz=orientation,
        velocity_body_frd=(velocity_flu[0], -velocity_flu[1], -velocity_flu[2]),
        angular_velocity_body_frd=(angular_flu[0], -angular_flu[1], -angular_flu[2]),
        position_variance=_variance(position_variance_m2, 'position variance'),
        orientation_variance=_variance(orientation_variance_rad2, 'orientation variance'),
        velocity_variance=_variance(velocity_variance_m2_s2, 'velocity variance'),
        quality=source_quality,
        epoch=epoch,
    )
