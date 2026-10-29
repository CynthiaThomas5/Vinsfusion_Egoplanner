#!/usr/bin/env python3
"""Create the N13 staggered scene from the qualified N12 source, offline only."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

POSITIONS = ((-2.5, -0.3, 1.5), (0.5, 0.3, 1.5), (3.5, -0.3, 1.5))


def prepare(source, output):
    source, output = Path(source), Path(output)
    if output.exists():
        raise ValueError('refuse to overwrite an existing scene')
    tree = ET.parse(source)
    world = tree.getroot().find('world')
    template = world.find("model[@name='n12_single_cylinder']")
    if template is None:
        raise ValueError('qualified cylinder template missing')
    shape = template.find('link/collision/geometry/cylinder')
    if shape is None or float(shape.findtext('radius')) != .5 or float(shape.findtext('length')) != 3:
        raise ValueError('unexpected source cylinder geometry')
    unaffected = [ET.tostring(m) for m in world.findall('model') if m is not template]
    world.remove(template)
    records = []
    for index, position in enumerate(POSITIONS, 1):
        model = copy.deepcopy(template)
        model.set('name', f'n13_staggered_cylinder_{index}')
        model.find('pose').text = ' '.join(map(str, (*position, 0, 0, 0)))
        world.append(model)
        records.append({'name': model.get('name'), 'center_xyz_m': list(position),
                        'radius_m': .5, 'length_m': 3.})
    assert unaffected == [ET.tostring(m) for m in world.findall('model')
                          if not m.get('name', '').startswith('n13_staggered_')]
    output.parent.mkdir(parents=True, exist_ok=True)
    tree.write(output, encoding='utf-8', xml_declaration=True)
    report = {'schema': 'n13-scene-provenance/v1', 'status': 'GEOMETRY_PREPARED_NOT_FLIGHT_QUALIFIED',
              'source': str(source.resolve()), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'output': str(output.resolve()), 'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
              'source_model': 'n12_single_cylinder', 'non_obstacle_models_unchanged': True,
              'obstacles': records, 'online_truth_or_map_added': False,
              'limitations': ['flight path and map/replan support not yet demonstrated',
                              'actual initial alignment/direct blockage must be evaluated per run']}
    output.with_suffix('.provenance.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.output)))
