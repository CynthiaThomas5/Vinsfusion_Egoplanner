"""Pure serialization helpers for the read-only Gazebo truth observer."""

import math


def odometry_sample(message, wall_elapsed_s, wall_monotonic_s):
    """Copy one gz.msgs.Odometry sample without changing its source fields."""
    position = message.pose.position
    quaternion = message.pose.orientation
    # gz.msgs.Odometry.twist is gz.msgs.Twist, not ROS TwistWithCovariance.
    linear = message.twist.linear
    angular = message.twist.angular
    return {
        'wall_s': float(wall_elapsed_s),
        'wall_monotonic_s': float(wall_monotonic_s),
        'stamp_ns': int(message.header.stamp.sec) * 10**9 + int(message.header.stamp.nsec),
        'xyz': [float(position.x), float(position.y), float(position.z)],
        'q_xyzw': [float(quaternion.x), float(quaternion.y),
                   float(quaternion.z), float(quaternion.w)],
        'linear_velocity_xyz_m_s': [float(linear.x), float(linear.y), float(linear.z)],
        'angular_velocity_xyz_rad_s': [float(angular.x), float(angular.y), float(angular.z)],
    }


def kinematics_sample(message, wall_elapsed_s, wall_monotonic_s):
    """Accept only explicitly identified world-frame instantaneous states."""
    metadata = {}
    for item in message.header.data:
        if item.key in metadata:
            raise ValueError('duplicate_kinematics_metadata')
        metadata[item.key] = list(item.value)
    expected = {
        'schema': 'uav-model-kinematics/v1',
        'frame_id': 'world',
        'pose_reference': 'model_origin',
        'linear_velocity_reference': 'model_origin',
        'linear_velocity_frame': 'world',
        'angular_velocity_frame': 'world',
        'velocity_kind': 'instantaneous_physics_components',
        'source': 'canonical_link_world_components_with_sdk_point_transform',
    }
    if any(metadata.get(key) != [value] for key, value in expected.items()):
        raise ValueError('kinematics_frame_reference_or_source_mismatch')
    model = metadata.get('child_frame_id') or []
    if len(model) != 1 or not model[0]:
        raise ValueError('kinematics_model_identity_missing')
    row = odometry_sample(message, wall_elapsed_s, wall_monotonic_s)
    values = (row['xyz'] + row['q_xyzw'] + row['linear_velocity_xyz_m_s']
              + row['angular_velocity_xyz_rad_s'])
    if not all(math.isfinite(value) for value in values):
        raise ValueError('nonfinite_kinematics_state')
    if abs(sum(value * value for value in row['q_xyzw']) - 1.0) > 2e-5:
        raise ValueError('invalid_kinematics_quaternion')
    row['schema'] = expected['schema']
    row['model_name'] = model[0]
    row['pose_reference'] = expected['pose_reference']
    row['linear_velocity_world_m_s'] = row.pop('linear_velocity_xyz_m_s')
    row['angular_velocity_world_rad_s'] = row.pop('angular_velocity_xyz_rad_s')
    return row
