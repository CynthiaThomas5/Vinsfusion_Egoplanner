import unittest

from n10_motion_cancel import StopWindowTracker, cancel_trigger


class MotionCancelHelpersTest(unittest.TestCase):
    def command(self, **changes):
        row = {
            'goal_id': 'goal', 'epoch': 'epoch', 'flag': 1,
            'trajectory_id': 7, 'source_stamp_ns': 10_000_000_000,
            'velocity_enu_m_s': [0.5, 0.0, 0.0],
            'acceleration_enu_m_s2': [0.0, 0.0, 0.0],
        }
        row.update(changes)
        return row

    def local(self, **changes):
        row = {
            'xy_valid': True, 'z_valid': True,
            'vx': 0.52, 'vy': 0.0, 'vz': 0.0,
            'sim_time_ns': 11_000_000_000, 'timestamp_sample_us': 10_000_000,
            'x': 1.0, 'y': 2.0, 'z': -1.0,
        }
        row.update(changes)
        return row

    def test_trigger_requires_matching_ready_goal_and_actual_window(self):
        hit = cancel_trigger(self.command(), self.local(), goal_id='goal', epoch='epoch',
                             ready_flag=1, speed_window_m_s=(0.50, 0.56))
        self.assertAlmostEqual(hit['px4_horizontal_speed_m_s'], 0.52)
        self.assertEqual(hit['ego_reference_trajectory_id'], 7)
        self.assertIsNone(cancel_trigger(
            self.command(goal_id='old'), self.local(), goal_id='goal', epoch='epoch',
            ready_flag=1, speed_window_m_s=(0.50, 0.56)))
        self.assertIsNone(cancel_trigger(
            self.command(), self.local(vx=0.49), goal_id='goal', epoch='epoch',
            ready_flag=1, speed_window_m_s=(0.50, 0.56)))

    def test_trigger_rejects_invalid_window_and_invalid_px4_state(self):
        with self.assertRaises(ValueError):
            cancel_trigger(self.command(), self.local(), goal_id='goal', epoch='epoch',
                           ready_flag=1, speed_window_m_s=(0.56, 0.50))
        self.assertIsNone(cancel_trigger(
            self.command(), self.local(xy_valid=False), goal_id='goal', epoch='epoch',
            ready_flag=1, speed_window_m_s=(0.50, 0.56)))

    def test_stop_window_requires_contiguous_one_second_and_resets_on_motion(self):
        tracker = StopWindowTracker(trigger_sim_ns=1_000_000_000)
        result = None
        for i, speed in enumerate((0.02, 0.02, 0.08, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02)):
            t = 1_000_000_000 + i * 200_000_000
            row = self.local(vx=speed, sim_time_ns=t,
                             timestamp_sample_us=t // 1000)
            result = tracker.observe(row)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result['dwell_sim_s'], 1.0)
        self.assertEqual(result['sample_count'], 6)

    def test_stop_window_does_not_pass_across_large_sample_gap(self):
        tracker = StopWindowTracker(trigger_sim_ns=1_000_000_000)
        rows = [
            self.local(sim_time_ns=1_000_000_000, timestamp_sample_us=1_000_000),
            self.local(sim_time_ns=1_200_000_000, timestamp_sample_us=1_200_000),
            self.local(sim_time_ns=1_500_000_001, timestamp_sample_us=1_500_000),
            self.local(sim_time_ns=1_700_000_000, timestamp_sample_us=1_700_000),
        ]
        self.assertTrue(all(tracker.observe(row) is None for row in rows))

    def test_stop_window_rejects_source_time_regression(self):
        tracker = StopWindowTracker(trigger_sim_ns=1_000_000_000)
        tracker.observe(self.local(sim_time_ns=1_200_000_000, timestamp_sample_us=1_200_000))
        with self.assertRaises(ValueError):
            tracker.observe(self.local(sim_time_ns=1_100_000_000, timestamp_sample_us=1_100_000))


if __name__ == '__main__':
    unittest.main()
