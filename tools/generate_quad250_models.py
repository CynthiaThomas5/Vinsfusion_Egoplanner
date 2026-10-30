#!/usr/bin/env python3
"""Regenerate local 250-class model derivatives without modifying pinned PX4.

Review the generated SDFs/provenance/diffs and rerun geometry/allocation/SITL
checks after changing the proxy config. Meshes remain upstream symlinks.
"""
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def generate():
    config = json.loads((ROOT / 'config/components/simulation/quad250.json').read_text())
    length = float(config['length_scale'])
    mass = float(config['airframe_mass_scale'])
    if not 0 < length <= 1 or not 0 < mass <= 1:
        raise ValueError('proxy length and mass scales must be in (0, 1]')
    manifest = {}
    for name in ('x500_base', 'x500'):
        source = ROOT / f'external/PX4-Autopilot/Tools/simulation/gz/models/{name}/model.sdf'
        tree = ET.parse(source)
        model = tree.getroot().find('model')
        if name == 'x500_base':
            for element in model.iter('pose'):
                pose = list(map(float, element.text.split()))
                element.text = ' '.join(format(v * length if i < 3 else v, '.12g')
                                        for i, v in enumerate(pose))
            for tag in ('size', 'scale'):
                for element in model.iter(tag):
                    element.text = ' '.join(format(float(v) * length, '.12g')
                                            for v in element.text.split())
            for link in model.findall('link'):
                inertial = link.find('inertial')
                if inertial is None:
                    continue
                element = inertial.find('mass')
                element.text = format(float(element.text) * mass, '.12g')
                for element in inertial.find('inertia'):
                    element.text = format(float(element.text) * mass * length**2, '.12g')
        else:
            factors = {'motorConstant': mass, 'momentConstant': length,
                       'rotorDragCoefficient': mass * length,
                       'rollingMomentCoefficient': mass * length**2}
            for plugin in model.findall('plugin'):
                for tag, factor in factors.items():
                    element = plugin.find(tag)
                    element.text = format(float(element.text) * factor, '.12g')
        destination = ROOT / f'simulation/models/{name}/model.sdf'
        destination.parent.mkdir(parents=True, exist_ok=True)
        ET.indent(tree, space='  ')
        tree.write(destination, encoding='utf-8', xml_declaration=True)
        manifest[str(source.relative_to(ROOT))] = {
            'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'derived_path': str(destination.relative_to(ROOT)),
            'derived_sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
        }
        diff = ''.join(difflib.unified_diff(
            source.read_text().splitlines(True), destination.read_text().splitlines(True),
            fromfile=str(source.relative_to(ROOT)), tofile=str(destination.relative_to(ROOT))))
        (ROOT / f'dependencies/patches/simulation/quad250-{name}.diff').write_text(diff)
    manifest.update({
        'baseline_commit': subprocess.check_output(
            ['git', '-C', str(ROOT / 'external/PX4-Autopilot'), 'rev-parse', 'HEAD'],
            text=True).strip(),
        'license': 'BSD-3-Clause; model derivative of PX4; meshes referenced from unchanged PX4 sources',
        'application_order': 'Local model overlays only; diffs describe each upstream-to-local SDF derivation, never applied to external/PX4-Autopilot.',
    })
    (ROOT / 'dependencies/quad250-model-provenance.json').write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    generate()
