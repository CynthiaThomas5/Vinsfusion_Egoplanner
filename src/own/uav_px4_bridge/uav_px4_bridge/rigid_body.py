"""Rigid IMU-to-body reference change, with explicit FRD mount convention."""
import math

from .trajectory import _quaternion_product, rotate_frd_to_ned


def mount_rotation_translation(matrix):
    """T_BI maps IMU coordinates to body FRD; translation is IMU in body."""
    if len(matrix) != 16 or not all(math.isfinite(float(x)) for x in matrix):
        raise ValueError('T_body_imu must contain 16 finite values')
    if any(abs(a-b) > 1e-8 for a, b in zip(matrix[12:], (0, 0, 0, 1))):
        raise ValueError('T_body_imu bottom row must be homogeneous')
    r = [[float(matrix[4*i+j]) for j in range(3)] for i in range(3)]
    for i in range(3):
        for j in range(3):
            if abs(sum(r[k][i]*r[k][j] for k in range(3))-(i == j)) > 1e-6:
                raise ValueError('T_body_imu rotation must be orthonormal')
    det = sum(r[0][i]*(r[1][(i+1)%3]*r[2][(i+2)%3]
                      -r[1][(i+2)%3]*r[2][(i+1)%3]) for i in range(3))
    if abs(det-1) > 1e-6:
        raise ValueError('T_body_imu rotation must be proper')
    return r, tuple(float(matrix[i]) for i in (3, 7, 11))


def rotation_quaternion(r):
    """Proper rotation matrix to normalized xyzw, including 180 degree cases."""
    trace = sum(r[i][i] for i in range(3))
    if trace > 0:
        s = 2*math.sqrt(1+trace)
        q = [(r[2][1]-r[1][2])/s, (r[0][2]-r[2][0])/s,
             (r[1][0]-r[0][1])/s, s/4]
    else:
        i = max(range(3), key=lambda j: r[j][j])
        j, k = (i+1)%3, (i+2)%3
        s = 2*math.sqrt(1+r[i][i]-r[j][j]-r[k][k])
        q = [0., 0., 0., (r[k][j]-r[j][k])/s]
        q[i], q[j], q[k] = s/4, (r[j][i]+r[i][j])/s, (r[k][i]+r[i][k])/s
    norm = math.sqrt(sum(x*x for x in q))
    return tuple(x/norm for x in q)


def imu_to_body_flu(position_w, quaternion_wi, velocity_i, omega_i, matrix):
    """Return body point in W and FLU attitude/twist for the shared converter.

    Input pose is W<-I and both twists are I components (localization contract).
    v_B = R_BI v_I - omega_B cross t_BI; no yaw-only approximation here.
    """
    values = tuple(position_w)+tuple(quaternion_wi)+tuple(velocity_i)+tuple(omega_i)
    if not all(math.isfinite(float(x)) for x in values):
        raise ValueError('Rigid-body state must be finite')
    r, t = mount_rotation_translation(matrix)
    q_bi = rotation_quaternion(r)
    q_ib = (-q_bi[0], -q_bi[1], -q_bi[2], q_bi[3])
    q_wb = _quaternion_product(quaternion_wi, q_ib)
    lever_w = rotate_frd_to_ned(t, (q_wb[3], *q_wb[:3]))
    position = tuple(p-x for p, x in zip(position_w, lever_w))
    velocity = [sum(r[i][j]*velocity_i[j] for j in range(3)) for i in range(3)]
    omega = [sum(r[i][j]*omega_i[j] for j in range(3)) for i in range(3)]
    cross = (omega[1]*t[2]-omega[2]*t[1], omega[2]*t[0]-omega[0]*t[2],
             omega[0]*t[1]-omega[1]*t[0])
    velocity = [v-x for v, x in zip(velocity, cross)]
    flu = lambda v: (v[0], -v[1], -v[2])
    return position, _quaternion_product(q_wb, (1., 0., 0., 0.)), flu(velocity), flu(omega)
