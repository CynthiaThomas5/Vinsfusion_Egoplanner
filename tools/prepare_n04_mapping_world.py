#!/usr/bin/env python3
"""Generate a diagnostic sensor world and a static-only truth SDF for N04."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

from prepare_motion_world import prepare as prepare_motion_world


ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _geometry(obj):
    geometry = ET.Element('geometry')
    if obj['shape'] == 'box':
        box = ET.SubElement(geometry, 'box')
        ET.SubElement(box, 'size').text = ' '.join(map(str, obj['size_m']))
    elif obj['shape'] == 'cylinder':
        cylinder = ET.SubElement(geometry, 'cylinder')
        ET.SubElement(cylinder, 'radius').text = str(obj['radius_m'])
        ET.SubElement(cylinder, 'length').text = str(obj['length_m'])
    else:
        raise ValueError(f"unsupported N04 shape: {obj['shape']}")
    return geometry


def _object_model(obj):
    pose = ' '.join(map(str, obj['pose_xyz_rpy_m_rad']))
    rgba = ' '.join(map(str, obj['rgba']))
    model = ET.Element('model', name=obj['name'])
    ET.SubElement(model, 'static').text = 'true'
    ET.SubElement(model, 'pose').text = pose
    link = ET.SubElement(model, 'link', name='body')
    collision = ET.SubElement(link, 'collision', name='collision')
    collision.append(_geometry(obj))
    visual = ET.SubElement(link, 'visual', name='visual')
    visual.append(_geometry(obj))
    material = ET.SubElement(visual, 'material')
    for tag in ('ambient', 'diffuse'):
        ET.SubElement(material, tag).text = rgba
    ET.SubElement(material, 'specular').text = '0.05 0.05 0.05 1'
    return model


def prepare(layout_id, output_world, output_truth, output_manifest,
            config_path=ROOT/'config/components/simulation/n04_geometry_layouts.json'):
    for path in (output_world, output_truth, output_manifest):
        if path.exists():
            raise FileExistsError(path)
    config = json.loads(config_path.read_text())
    layouts = {layout['id']: layout for layout in config['layouts']}
    if layout_id not in layouts:
        raise ValueError(f"unknown layout {layout_id!r}; expected one of {sorted(layouts)}")
    layout = layouts[layout_id]
    if len({obj['name'] for obj in layout['objects']}) != len(layout['objects']):
        raise ValueError('layout object names must be unique')
    base_world = ROOT/config['base_world']
    output_world.parent.mkdir(parents=True, exist_ok=True)
    output_truth.parent.mkdir(parents=True, exist_ok=True)
    output_manifest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='n04-motion-world-') as temp_dir:
        moving_world = Path(temp_dir)/'moving.sdf'
        prepare_motion_world(moving_world)
        tree = ET.parse(moving_world)
    world = tree.find('world')
    if world is None or world.get('name') != 'sensor_calibration':
        raise ValueError('generated sensor world must preserve sensor_calibration world name')
    # The source calibration SDF has a historical visual/collision name clash.
    # Rename only the generated diagnostic collision; preserve the source file.
    for collision in world.findall("model[@name='calibration_wall']/link/collision"):
        collision.set('name', 'calibration_wall_collision')
    for obj in layout['objects']:
        world.append(_object_model(obj))
    ET.indent(tree)
    tree.write(output_world, encoding='utf-8', xml_declaration=True)

    truth_tree = ET.parse(output_world)
    truth_world = truth_tree.find('world')
    fixture = truth_world.find("model[@name='sensor_fixture']")
    if fixture is None:
        raise ValueError('generated world has no sensor fixture')
    truth_world.remove(fixture)
    for plugin in list(truth_world.findall('plugin')):
        truth_world.remove(plugin)
    ET.indent(truth_tree)
    truth_tree.write(output_truth, encoding='utf-8', xml_declaration=True)

    manifest = {
        'schema': 'n04-map-world-manifest/v1',
        'layout_id': layout_id,
        'description': layout['description'],
        'objects': layout['objects'],
        'regions': layout['regions'],
        'source': {
            'layout_config': str(config_path.resolve().relative_to(ROOT)),
            'layout_config_sha256': sha256(config_path),
            'base_world': config['base_world'],
            'base_world_sha256': sha256(base_world),
            'sensor_model': config['sensor_model'],
            'sensor_model_sha256': sha256(ROOT/config['sensor_model']),
        },
        'generated': {
            'moving_world': output_world.name,
            'moving_world_sha256': sha256(output_world),
            'truth_scene_sdf': output_truth.name,
            'truth_scene_sdf_sha256': sha256(output_truth),
        },
        'online_truth_input': False,
        'truth_scene_use': 'offline signed-distance and occlusion reference only',
    }
    output_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--layout', required=True)
    parser.add_argument('--world', type=Path, required=True)
    parser.add_argument('--truth-sdf', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--config', type=Path,
                        default=ROOT/'config/components/simulation/n04_geometry_layouts.json')
    args = parser.parse_args()
    print(json.dumps(prepare(args.layout, args.world, args.truth_sdf,
                             args.manifest, args.config.resolve()),
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
