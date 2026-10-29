import unittest
from types import SimpleNamespace

from tools.debug_truth.truth_observer import odometry_sample, kinematics_sample


class N10TruthObserverTests(unittest.TestCase):
    def test_copies_gz_odometry_pose_and_direct_twist_fields(self):
        vector = lambda x, y, z: SimpleNamespace(x=x, y=y, z=z)
        message = SimpleNamespace(
            header=SimpleNamespace(stamp=SimpleNamespace(sec=12, nsec=345)),
            pose=SimpleNamespace(
                position=vector(1.0, 2.0, 3.0),
                orientation=SimpleNamespace(x=0.0, y=0.0, z=0.5, w=0.5)),
            twist=SimpleNamespace(
                linear=vector(0.1, 0.2, 0.3),
                angular=vector(-0.1, -0.2, -0.3)),
        )

        sample = odometry_sample(message, 4.5, 123.0)

        self.assertEqual(sample['stamp_ns'], 12_000_000_345)
        self.assertEqual(sample['xyz'], [1.0, 2.0, 3.0])
        self.assertEqual(sample['q_xyzw'], [0.0, 0.0, 0.5, 0.5])
        self.assertEqual(sample['linear_velocity_xyz_m_s'], [0.1, 0.2, 0.3])
        self.assertEqual(sample['angular_velocity_xyz_rad_s'], [-0.1, -0.2, -0.3])
        self.assertEqual(sample['wall_s'], 4.5)
        self.assertEqual(sample['wall_monotonic_s'], 123.0)


class KinematicsSerializationTests(unittest.TestCase):
    def message(self):
        vector = lambda x, y, z: SimpleNamespace(x=x, y=y, z=z)
        metadata = {'schema': 'uav-model-kinematics/v1', 'frame_id': 'world',
            'child_frame_id': 'vehicle', 'pose_reference': 'model_origin',
            'linear_velocity_reference': 'model_origin', 'linear_velocity_frame': 'world',
            'angular_velocity_frame': 'world', 'velocity_kind': 'instantaneous_physics_components',
            'source': 'canonical_link_world_components_with_sdk_point_transform'}
        return SimpleNamespace(header=SimpleNamespace(stamp=SimpleNamespace(sec=1,nsec=0),
            data=[SimpleNamespace(key=k,value=[v]) for k,v in metadata.items()]),
            pose=SimpleNamespace(position=vector(1,2,3),orientation=SimpleNamespace(x=0,y=0,z=0,w=1)),
            twist=SimpleNamespace(linear=vector(1,0,0),angular=vector(0,0,1)))

    def test_explicit_world_velocity_fields(self):
        row = kinematics_sample(self.message(), 0, 1)
        self.assertEqual(row['linear_velocity_world_m_s'], [1,0,0])
        self.assertNotIn('linear_velocity_xyz_m_s', row)

    def test_rejects_body_frame_smoothed_duplicate_and_invalid_states(self):
        for mutation in ('body','smooth','duplicate','nan','quaternion'):
            m = self.message()
            if mutation == 'body': m.header.data[5].value = ['body']
            if mutation == 'smooth': m.header.data[7].value = ['rolling_mean']
            if mutation == 'duplicate': m.header.data.append(m.header.data[0])
            if mutation == 'nan': m.twist.linear.x = float('nan')
            if mutation == 'quaternion': m.pose.orientation.w = 2
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                kinematics_sample(m, 0, 1)


if __name__ == '__main__':
    unittest.main()
