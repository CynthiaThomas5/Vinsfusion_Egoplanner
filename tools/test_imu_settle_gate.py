#!/usr/bin/env python3
import json
import unittest

from wait_sim_imu_settled import ROOT, acceleration_norms, settled


class SettleGateTests(unittest.TestCase):
    def test_native_json_stream_and_default_zero_axes(self):
        text = '\n {"linearAcceleration":{"z":9.8}}\n {"linear_acceleration":{"x":3,"y":4}}\n'
        self.assertEqual(acceleration_norms(text), [9.8, 5.0])

    def test_missing_or_nonfinite_measurement_rejected(self):
        for text in ('{}', '[]', '{"linearAcceleration":{"z":"NaN"}}', 'invalid'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                acceleration_norms(text)

    def test_original_30_sample_gravity_gate(self):
        policy = json.loads((ROOT / 'config/components/simulation/imu_settle_gate.json').read_text())
        self.assertFalse(settled([9.8] * 29, policy))
        self.assertFalse(settled([9.8] * 29 + [0], policy))
        self.assertTrue(settled([0] * 30 + [9.8] * 30, policy))


if __name__ == '__main__':
    unittest.main()
