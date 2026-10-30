#!/usr/bin/env python3
"""Check that the canonical PX4 debug profile derives EV_POS from the SDF."""

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from stage_px4_debug_params import stage  # noqa: E402


class Px4DebugParameterTests(unittest.TestCase):
    def test_overlay_uses_config_values_and_sdf_mount(self):
        with tempfile.TemporaryDirectory() as temp:
            build = Path(temp) / 'build/px4_sitl_default'
            airframes = build / 'etc/init.d-posix/airframes'
            airframes.mkdir(parents=True)
            (airframes / '4001_gz_x500').write_text('# pinned x500 source\n')
            report = stage(ROOT, build)
            script = Path(report['path']).read_text()
            self.assertEqual(report['autostart_id'], 5010)
            self.assertEqual(report['parameters']['EKF2_EV_CTRL'], 15)
            self.assertEqual(report['parameters']['EKF2_GPS_CTRL'], 0)
            self.assertEqual(report['parameters']['EKF2_EV_POS_X'], 0.0)
            self.assertAlmostEqual(report['parameters']['CA_ROTOR0_PX'], 0.087)
            self.assertAlmostEqual(report['parameters']['CA_ROTOR0_PY'], 0.087)
            self.assertAlmostEqual(report['parameters']['CA_ROTOR0_KM'], 0.008)
            self.assertEqual(report['parameters']['EKF2_EV_POS_Z'], -0.08)
            self.assertEqual(report['parameters']['COM_RC_IN_MODE'], 4)
            self.assertEqual(report['parameters']['COM_OBL_RC_ACT'], 4)
            self.assertEqual(report['parameters']['SIM_GZ_EN_ODOM'], 0)
            self.assertEqual(report['parameters']['UXRCE_DDS_SYNCT'], 0)
            self.assertIn('param set SIM_GZ_EN_ODOM 0', script)
            self.assertIn('param set UXRCE_DDS_SYNCT 0', script)
            self.assertIn('param set EKF2_EV_POS_X 0', script)
            self.assertIn('param set EKF2_EV_POS_Z -0.08', script)
            self.assertIn('. ${R}etc/init.d-posix/airframes/4001_gz_x500', script)
            self.assertEqual(Path(report['path']).stat().st_mode & 0o777, 0o755)

    def test_vio_overlay_uses_isolated_id_and_shared_no_gnss_parameters(self):
        with tempfile.TemporaryDirectory() as temp:
            build = Path(temp) / 'build/px4_sitl_default'
            airframes = build / 'etc/init.d-posix/airframes'
            airframes.mkdir(parents=True)
            (airframes / '4001_gz_x500').write_text('# pinned x500 source\n')
            report = stage(ROOT, build, profile='vio_closed_loop')
            script = Path(report['path']).read_text()
            self.assertEqual(report['profile'], 'vio_closed_loop')
            self.assertEqual(report['autostart_id'], 5011)
            self.assertEqual(report['parameters']['EKF2_EV_CTRL'], 15)
            self.assertEqual(report['parameters']['EKF2_GPS_CTRL'], 0)
            self.assertEqual(report['parameters']['SIM_GZ_EN_ODOM'], 0)
            self.assertEqual(report['parameters']['UXRCE_DDS_SYNCT'], 0)
            self.assertIn('param set EKF2_EV_CTRL 15', script)
            self.assertIn('param set EKF2_GPS_CTRL 0', script)
            self.assertIn('param set SIM_GZ_EN_ODOM 0', script)
            self.assertIn('param set UXRCE_DDS_SYNCT 0', script)
            self.assertNotIn('debug_truth', script)
            self.assertTrue(Path(report['path']).name.endswith('_vio_closed_loop'))


if __name__ == '__main__':
    unittest.main()
