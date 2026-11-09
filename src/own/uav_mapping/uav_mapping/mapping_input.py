"""Time-aligned depth and pose helpers for the single-camera mapping input."""
import math


def normalize_quaternion(q):
    norm = math.sqrt(sum(value * value for value in q))
    if not math.isfinite(norm) or norm < 1e-9:
        raise ValueError('Invalid quaternion')
    return tuple(value / norm for value in q)


def quaternion_multiply(a, b):
    ax, ay, az, aw = normalize_quaternion(a)
    bx, by, bz, bw = normalize_quaternion(b)
    return normalize_quaternion((
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    ))


def rotate_vector(q, vector):
    x, y, z, w = normalize_quaternion(q)
    vx, vy, vz = vector
    # Expanded q * [v, 0] * conjugate(q), avoiding a matrix dependency.
    tx, ty, tz = 2 * (y * vz - z * vy), 2 * (z * vx - x * vz), 2 * (x * vy - y * vx)
    return (vx + w * tx + y * tz - z * ty,
            vy + w * ty + z * tx - x * tz,
            vz + w * tz + x * ty - y * tx)


def quaternion_from_matrix(m):
    trace = m[0] + m[4] + m[8]
    if trace > 0:
        scale = math.sqrt(trace + 1.0) * 2
        q = ((m[7] - m[5]) / scale, (m[2] - m[6]) / scale,
             (m[3] - m[1]) / scale, 0.25 * scale)
    elif m[0] > m[4] and m[0] > m[8]:
        scale = math.sqrt(1.0 + m[0] - m[4] - m[8]) * 2
        q = (0.25 * scale, (m[1] + m[3]) / scale,
             (m[2] + m[6]) / scale, (m[7] - m[5]) / scale)
    elif m[4] > m[8]:
        scale = math.sqrt(1.0 + m[4] - m[0] - m[8]) * 2
        q = ((m[1] + m[3]) / scale, 0.25 * scale,
             (m[5] + m[7]) / scale, (m[2] - m[6]) / scale)
    else:
        scale = math.sqrt(1.0 + m[8] - m[0] - m[4]) * 2
        q = ((m[2] + m[6]) / scale, (m[5] + m[7]) / scale,
             0.25 * scale, (m[3] - m[1]) / scale)
    return normalize_quaternion(q)


def slerp(a, b, t):
    qa, qb = normalize_quaternion(a), normalize_quaternion(b)
    dot = sum(x * y for x, y in zip(qa, qb))
    if dot < 0:
        qb = tuple(-value for value in qb)
        dot = -dot
    dot = min(1.0, max(-1.0, dot))
    if dot > 0.9995:
        return normalize_quaternion(tuple(x + t * (y - x) for x, y in zip(qa, qb)))
    angle = math.acos(dot)
    sin_angle = math.sin(angle)
    left = math.sin((1 - t) * angle) / sin_angle
    right = math.sin(t * angle) / sin_angle
    return normalize_quaternion(tuple(left * x + right * y for x, y in zip(qa, qb)))


def pose_at(history, stamp_ns, max_bracket_ns):
    """Interpolate (stamp, position, quaternion) samples; never extrapolate."""
    previous = None
    for current in history:
        current_stamp = current[0]
        if current_stamp == stamp_ns:
            return tuple(current[1]), normalize_quaternion(current[2])
        if current_stamp > stamp_ns:
            if previous is None:
                return None
            span = current_stamp - previous[0]
            if span <= 0 or span > max_bracket_ns:
                return None
            fraction = (stamp_ns - previous[0]) / span
            position = tuple(a + fraction * (b - a) for a, b in zip(previous[1], current[1]))
            return position, slerp(previous[2], current[2], fraction)
        previous = current
    return None


def depth_camera_pose(position, orientation, imu_translation, camera_translation, r_body_optical):
    """Compose VINS world→IMU with the SDF-derived body→optical transform."""
    rotation = quaternion_from_matrix(r_body_optical)
    offset = tuple(camera - imu for camera, imu in zip(camera_translation, imu_translation))
    world_position = rotate_vector(orientation, offset)
    camera_position = tuple(value + delta for value, delta in zip(position, world_position))
    return camera_position, quaternion_multiply(orientation, rotation)


def depth_layout_valid(msg, expected_width, expected_height, expected_frame):
    """Check the ROS image layout without requiring a minimum valid-pixel count."""
    return (msg.header.frame_id == expected_frame
            and msg.encoding == '32FC1'
            and msg.width == expected_width
            and msg.height == expected_height
            and msg.step >= msg.width * 4
            and len(msg.data) >= msg.step * msg.height)


def camera_info_matches(msg, camera):
    """Check that live CameraInfo describes the calibrated native image stream."""
    expected_frame = camera.get('camera_info_frame', camera.get('image_frame', camera['frame']))
    if (msg is None or msg.header.frame_id != expected_frame
            or msg.width != camera['width'] or msg.height != camera['height']
            or len(msg.k) != 9):
        return False
    expected = camera['K']
    return all(math.isfinite(msg.k[index])
               and abs(msg.k[index] - expected[index]) <= 1e-3
               for index in (0, 2, 4, 5, 8))
