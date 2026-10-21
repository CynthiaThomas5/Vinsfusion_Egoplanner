#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from generate_vins_config import generate, ROOT


class ConfigTest(unittest.TestCase):
    def test_fresh_sessions_and_model_extrinsics(self):
        with tempfile.TemporaryDirectory() as tmp:
            first, second = Path(tmp)/'first', Path(tmp)/'second'
            a,b = generate(ROOT,first),generate(ROOT,second)
            self.assertNotEqual(a['epoch'],b['epoch'])
            text = (first/'vins.yaml').read_text()
            matrices = [json.loads(line.split('data: ')[1]) for line in text.splitlines() if 'data: ' in line]
            self.assertEqual(matrices[0], [0,0,1,0, -1,0,0,.025, 0,-1,0,0, 0,0,0,1])
            self.assertEqual(matrices[1][7], -.025)
            self.assertIn('imu: 1', text)
            self.assertIn('estimate_td: 0', text)
            for name, digest in a['files_sha256'].items():
                self.assertEqual(hashlib.sha256((first/name).read_bytes()).hexdigest(),digest)
            with self.assertRaises(FileExistsError):
                generate(ROOT,first)

    def test_extrinsics_relative_to_imu(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/'project'
            model = root/'simulation/models/d435i/model.sdf'
            model.parent.mkdir(parents=True)
            tree = ET.parse(ROOT/'simulation/models/d435i/model.sdf')
            tree.find('model/link/sensor[@name="imu"]/pose').text = '0 0.1 0 0 0 0'
            tree.write(model)
            settings = root/'config/components/localization/vins_sim.json'
            settings.parent.mkdir(parents=True)
            settings.write_bytes((ROOT/'config/components/localization/vins_sim.json').read_bytes())
            output = Path(tmp)/'generated'
            generate(root,output)
            matrices = [json.loads(line.split('data: ')[1]) for line in (output/'vins.yaml').read_text().splitlines() if 'data: ' in line]
            self.assertAlmostEqual(matrices[0][7], -.075)
            self.assertAlmostEqual(matrices[1][7], -.125)


if __name__ == '__main__':
    unittest.main()
