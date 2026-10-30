#!/usr/bin/env python3
"""Combine the project's EGO navigation scene with the pinned PX4 world systems."""

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from scene_config import resolve_scene
from scene_materials import physicalize_visuals, natural_materials

ROOT = Path(__file__).resolve().parents[1]


def generate(project_root, px4_world, px4_server_config, output, scene_name=None):
    project_root = Path(project_root).resolve()
    px4_world = Path(px4_world).resolve()
    px4_server_config = Path(px4_server_config).resolve()
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f'Refusing to overwrite bootstrap world: {output}')
    scene = resolve_scene(project_root, scene_name) if scene_name else None
    geometry_source = project_root / (scene['geometry'] if scene else 'simulation/worlds/ego.sdf')
    px4_tree = ET.parse(px4_world)
    px4_world_element = px4_tree.getroot().find('world')
    if px4_world_element is None:
        raise ValueError('PX4 source world does not contain a world')
    geometry_world = ET.parse(geometry_source).getroot().find('world')
    if geometry_world is None:
        raise ValueError('project navigation source does not contain a world')
    models = geometry_world.findall('model')
    if not models or any(model.findtext('static') not in ('true', '1') for model in models):
        raise ValueError('navigation scenery must contain only static models')
    if geometry_world.find('.//sensor') is not None:
        raise ValueError('navigation scenery must not add sensors')
    # Preserve PX4 timing, gravity and geographic conventions; replace only scenery.
    for child in list(px4_world_element):
        if child.tag in ('model', 'include', 'light', 'scene', 'gui', 'state'):
            px4_world_element.remove(child)
    insertion_index = next((index for index, child in enumerate(px4_world_element)
                            if child.tag in ('plugin', 'spherical_coordinates')),
                           len(px4_world_element))
    for child in geometry_world:
        if child.tag in ('model', 'light', 'scene', 'gui'):
            px4_world_element.insert(insertion_index, deepcopy(child))
            insertion_index += 1
    # Retain the existing world identifier so current PX4 launch callers stay valid.
    px4_world_element.set('name', 'vio_initialization')

    # World plugins in server.config are not reliably attached when a custom
    # world is launched directly, so materialize them in this diagnostic world.
    server_plugins = ET.parse(px4_server_config).getroot().find('plugins')
    if server_plugins is None:
        raise ValueError('PX4 server config does not contain a plugins section')
    by_name = {plugin.get('name'): plugin for plugin in px4_world_element.findall('plugin')}
    for source_plugin in server_plugins.findall('plugin'):
        name = source_plugin.get('name')
        filename = source_plugin.get('filename')
        if not name or not filename:
            raise ValueError('PX4 server config contains a plugin without name/filename')
        target = by_name.get(name)
        if target is None:
            target = ET.Element('plugin', {'filename': filename, 'name': name})
            for child in source_plugin:
                target.append(deepcopy(child))
            px4_world_element.append(target)
            by_name[name] = target
        elif target.get('filename') != filename:
            raise ValueError(f'plugin {name} filename conflicts with the project world')

    selected_models = px4_world_element.findall('model')
    collisions_added = physicalize_visuals(selected_models) if scene and scene.get('physicalize_visuals', False) else []
    profile = scene.get('material_profile', 'legacy') if scene else 'legacy'
    if profile not in ('legacy', 'natural'):
        raise ValueError('unknown scene material profile')
    # Legacy scenes retain their original verified procedural texture bytes.
    collision_before = b''.join(ET.tostring(c) for c in px4_world_element.findall('.//collision'))
    material_report = {'profile': 'legacy'}
    if profile == 'natural':
        material_report = natural_materials(project_root, selected_models)
    else:
        for model in px4_world_element.findall('model'):
            texture = project_root / 'simulation/textures' / ('floor.png' if model.get('name') == 'ground_plane' else 'obstacles.png')
            if not texture.is_file():
                raise FileNotFoundError(texture)
            for visual in model.findall('.//visual'):
                old = visual.find('material')
                if old is not None:
                    visual.remove(old)
                material = ET.SubElement(visual, 'material')
                ET.SubElement(material, 'ambient').text = '.6 .6 .6 1'
                ET.SubElement(material, 'diffuse').text = '1 1 1 1'
                metal = ET.SubElement(ET.SubElement(material, 'pbr'), 'metal')
                ET.SubElement(metal, 'albedo_map').text = str(texture)
                ET.SubElement(metal, 'metalness').text = '0'
                ET.SubElement(metal, 'roughness').text = '1'
    assert collision_before == b''.join(ET.tostring(c) for c in px4_world_element.findall('.//collision'))

    world = px4_world_element
    ET.indent(px4_tree, space='  ')
    output.parent.mkdir(parents=True, exist_ok=True)
    px4_tree.write(output, encoding='utf-8', xml_declaration=True)
    return {
        'collisions_added_from_visuals': collisions_added,
        'material_profile': material_report,
        'scene': scene['scene'] if scene else 'room',
        'scene_registry_sha256': scene['registry_sha256'] if scene else None,
        'px4_world_source': str(px4_world),
        'px4_world_sha256': hashlib.sha256(px4_world.read_bytes()).hexdigest(),
        'px4_server_config_source': str(px4_server_config),
        'px4_server_config_sha256': hashlib.sha256(px4_server_config.read_bytes()).hexdigest(),
        'project_geometry_source': str(geometry_source.relative_to(project_root)),
        'project_geometry_sha256': hashlib.sha256(geometry_source.read_bytes()).hexdigest(),
        'output': str(output),
        'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
        'world': 'vio_initialization',
        'models': [model.get('name') for model in world.findall('model')],
        'world_plugins': sorted(plugin.get('name') for plugin in world.findall('plugin')),
        'qualification': 'Selected static navigation scenery; no truth or prebuilt map input. '
                         'World loading does not qualify VINS, planning clearance or flight.',
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project-root', type=Path, default=ROOT)
    parser.add_argument('--px4-world', type=Path, required=True)
    parser.add_argument('--px4-server-config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--scene', default='')
    args = parser.parse_args()
    report = generate(args.project_root, args.px4_world,
                      args.px4_server_config, args.output, args.scene or None)
    payload = json.dumps(report, indent=2, sort_keys=True) + '\n'
    if args.report:
        args.report.write_text(payload, encoding='utf-8')
    print(payload, end='')


if __name__ == '__main__':
    main()
