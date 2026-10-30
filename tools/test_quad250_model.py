"""Cross-check physical geometry, motor authority and allocation for the proxy."""
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from stage_px4_debug_params import stage

ROOT = Path(__file__).resolve().parents[1]


class Quad250Tests(unittest.TestCase):
    def test_physical_model_and_px4_allocator_use_same_rotors(self):
        body = ET.parse(ROOT / 'simulation/models/x500_base/model.sdf').getroot().find('model')
        with tempfile.TemporaryDirectory() as temp:
            airframes = Path(temp) / 'etc/init.d-posix/airframes'
            airframes.mkdir(parents=True)
            (airframes / '4001_gz_x500').write_text('# fixture\n')
            params = stage(ROOT, temp, 'vio_closed_loop')['parameters']
        positions = []
        for i in range(4):
            xyz = [float(v) for v in body.findtext(f"link[@name='rotor_{i}']/pose").split()[:3]]
            positions.append(xyz)
            for axis, value in zip(('PX', 'PY', 'PZ'), (xyz[0], -xyz[1], -xyz[2])):
                self.assertAlmostEqual(params[f'CA_ROTOR{i}_{axis}'], value)
        diagonal = sum((a-b)**2 for a, b in zip(positions[0], positions[1]))**.5
        self.assertGreater(diagonal, .24)
        self.assertLess(diagonal, .26)

    def test_proxy_has_positive_inertia_and_sufficient_hover_thrust(self):
        body = ET.parse(ROOT / 'simulation/models/x500_base/model.sdf').getroot().find('model')
        camera = ET.parse(ROOT / 'simulation/models/d435i/model.sdf').getroot().find('model')
        total_mass = sum(float(e.text) for model in (body, camera) for e in model.findall('link/inertial/mass'))
        self.assertGreater(total_mass, 1.1)
        self.assertLess(total_mass, 1.2)
        for inertial in body.findall('link/inertial'):
            moments = [float(inertial.findtext('inertia/'+axis)) for axis in ('ixx','iyy','izz')]
            self.assertTrue(all(v > 0 for v in moments))
            self.assertLessEqual(max(moments), sum(moments)-max(moments))
        motors = ET.parse(ROOT / 'simulation/models/x500/model.sdf').getroot().find('model')
        maximum_thrust = sum(float(p.findtext('motorConstant'))*float(p.findtext('maxRotVelocity'))**2
                             for p in motors.findall('plugin'))
        self.assertGreater(maximum_thrust, 1.5 * total_mass * 9.81)
        # The real-sized camera is not scaled with the vehicle.
        self.assertEqual(camera.findtext('link/collision/geometry/box/size'), '0.025 0.09 0.025')
