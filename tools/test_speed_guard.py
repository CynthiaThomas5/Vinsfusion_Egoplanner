import math
import unittest

from speed_guard import speed_limit_event


class SpeedGuardTest(unittest.TestCase):
    def test_uses_three_dimensional_vector_magnitude(self):
        self.assertIsNone(speed_limit_event(
            (0.06, 0.06, 0.0), 0.12, source='test'))

    def test_reports_vector_speed_over_limit(self):
        event = speed_limit_event((0.09, 0.09, 0.0), 0.12,
                                  source='test', timestamp=42)
        self.assertEqual(event['reason'], 'vector_speed_exceeded')
        self.assertAlmostEqual(event['vector_speed_m_s'], math.sqrt(0.0162))
        self.assertEqual(event['timestamp'], 42)

    def test_invalid_speed_sample_fails_closed(self):
        event = speed_limit_event((float('nan'), 0.0, 0.0), 0.12,
                                  source='test')
        self.assertEqual(event['reason'], 'invalid_speed_guard_sample')
        self.assertIsNone(event['vector_speed_m_s'])


if __name__ == '__main__':
    unittest.main()
