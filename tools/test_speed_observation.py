"""The flight probe records speed without issuing a speed-limit fault."""
import math
import time
import unittest
from types import SimpleNamespace

from run_vio_ego_flight import EgoFlightProbe


class SpeedObservationTests(unittest.TestCase):
    def probe_state(self):
        return SimpleNamespace(
            speed_observation_maxima_m_s={}, speed_observation_sample_counts={},
            speed_observation_samples=[], speed_observation_last_samples={},
            started_wall=time.monotonic(), sim_clock_ns=123)

    def test_above_old_caps_is_recorded_without_fault(self):
        probe = self.probe_state()
        for source in ('ego_position_command_reference', 'px4_vehicle_local_position'):
            EgoFlightProbe._observe_speed(probe, source, (0.3, 0.4, 0.6), 42)
            row = probe.speed_observation_last_samples[source]
            self.assertTrue(row['sample_valid'])
            self.assertAlmostEqual(row['vector_speed_m_s'], math.sqrt(0.61))
            self.assertNotIn('limit_m_s', row)
            self.assertNotIn('violation', row)
        self.assertFalse(hasattr(probe, 'speed_guard_fault'))
        self.assertEqual(len(probe.speed_observation_samples), 2)

    def test_invalid_measurement_does_not_become_valid_speed(self):
        probe = self.probe_state()
        EgoFlightProbe._observe_speed(probe, 'px4_vehicle_local_position', (0.2, 0, 0), 1)
        EgoFlightProbe._observe_speed(probe, 'px4_vehicle_local_position', (math.nan, 0, 0), 2)
        row = probe.speed_observation_last_samples['px4_vehicle_local_position']
        self.assertFalse(row['sample_valid'])
        self.assertIsNone(row['vector_speed_m_s'])
        self.assertEqual(probe.speed_observation_maxima_m_s['px4_vehicle_local_position'], 0.2)
        self.assertEqual(probe.speed_observation_sample_counts['px4_vehicle_local_position'], 2)


if __name__ == '__main__':
    unittest.main()
