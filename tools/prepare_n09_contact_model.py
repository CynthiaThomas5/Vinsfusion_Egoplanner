#!/usr/bin/env python3
"""Create a run-local model overlay with read-only Gazebo contact sensors."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
X500_BASE = ROOT / 'simulation/models/x500_base'
D435I = ROOT / 'simulation/models/d435i'
WRAPPER = ROOT / 'simulation/models/x500_d435i'


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def instrument_model(model_dir, model_name, topic_prefix):
    path = model_dir / 'model.sdf'
    tree = ET.parse(path)
    model = tree.getroot().find('model')
    if model is None or model.get('name') != model_name:
        raise ValueError(f'unexpected_model_root:{path}')
    records = []
    for link in model.findall('link'):
        collisions = [collision.get('name') for collision in link.findall('collision')]
        collisions = [name for name in collisions if name]
        if not collisions:
            continue
        topic = f'{topic_prefix}/{link.get("name")}'
        sensor = ET.SubElement(link, 'sensor', {
            'name': 'n09_contact_observer', 'type': 'contact'})
        contact = ET.SubElement(sensor, 'contact')
        ET.SubElement(contact, 'topic').text = topic
        for collision in collisions:
            ET.SubElement(contact, 'collision').text = collision
        records.append({'link': link.get('name'), 'collisions': collisions,
                        'topic': topic})
    if not records:
        raise ValueError(f'model_has_no_collisions:{model_name}')
    ET.indent(tree, space='  ')
    tree.write(path, encoding='utf-8', xml_declaration=True)
    return records


def prepare(output, kinematics=False):
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f'refusing to reuse contact overlay: {output}')
    output.mkdir(parents=True)
    x500_target = output / 'x500_base'
    d435i_target = output / 'd435i'
    shutil.copytree(X500_BASE, x500_target)
    shutil.copytree(D435I, d435i_target)
    source_paths = sorted([path for directory in (X500_BASE, D435I)
                           for path in directory.rglob('*') if path.is_file()])
    x500_sensors = instrument_model(x500_target, 'x500_base',
                                    '/n09/contact/x500')
    d435i_sensors = instrument_model(d435i_target, 'd435i',
                                     '/n09/contact/d435i')
    sensors = x500_sensors + d435i_sensors
    required_links = {'base_link', 'rotor_0', 'rotor_1', 'rotor_2',
                      'rotor_3', 'd435i_link'}
    if {row['link'] for row in sensors} != required_links:
        raise ValueError('contact_sensor_vehicle_link_coverage_mismatch')
    generated = {
        'x500_base/model.sdf': sha256(x500_target / 'model.sdf'),
        'd435i/model.sdf': sha256(d435i_target / 'model.sdf'),
    }
    kinematics_info = {'enabled': False}
    if kinematics:
        wrapper_target = output / 'x500_d435i'
        shutil.copytree(WRAPPER, wrapper_target)
        source_paths.extend(path for path in WRAPPER.rglob('*') if path.is_file())
        tree = ET.parse(wrapper_target / 'model.sdf')
        model = tree.getroot().find('model')
        plugin = ET.SubElement(model, 'plugin', {
            'filename': 'libuav_truth_kinematics.so',
            'name': 'uav::debug_truth::ModelKinematics'})
        ET.SubElement(plugin, 'topic').text = '/debug_truth/model_kinematics'
        ET.indent(tree, space='  ')
        tree.write(wrapper_target / 'model.sdf', encoding='unicode', xml_declaration=True)
        generated['x500_d435i/model.sdf'] = sha256(wrapper_target / 'model.sdf')
        binary = ROOT / 'install/uav_debug_truth/lib/libuav_truth_kinematics.so'
        source_cpp = ROOT / 'src/own/uav_debug_truth/src/model_kinematics.cpp'
        kinematics_info = {
            'enabled': True, 'plugin_filename': 'libuav_truth_kinematics.so',
            'plugin_class': 'uav::debug_truth::ModelKinematics',
            'topic': '/debug_truth/model_kinematics',
            'pose_reference': 'model_origin',
            'velocity_frame': 'world', 'velocity_kind': 'instantaneous_physics_components',
            'plugin_binary_sha256': sha256(binary) if binary.is_file() else None,
            'plugin_source_sha256': sha256(source_cpp),
            'missing_binary_is_offline_insufficient_not_a_control_gate': True,
        }
    report = {
        'schema': 'n09-contact-model-overlay/v1',
        'read_only_observation_only': True,
        'collision_geometry_changed': False,
        'sensor_topics': [row['topic'] for row in sensors],
        'sensors': sensors,
        'source_sha256': {str(path.relative_to(ROOT)): sha256(path)
                          for path in source_paths},
        'generated_model_sha256': generated,
        'kinematics_observer': kinematics_info,
        'overlay_root': str(output),
        'qualification': ('N09 run-local observer instrumentation; does not alter '
                          'link poses, collision geometry, control topics or flight code.'),
    }
    (output / 'n09-contact-model-manifest.json').write_text(
        json.dumps(report, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--kinematics', action='store_true',
                        help='add the read-only model-origin physics observer')
    args = parser.parse_args()
    report = prepare(args.output, kinematics=args.kinematics)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
