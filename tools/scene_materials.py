"""Project-owned static-scene adaptations; no control or map inputs."""
from copy import deepcopy
from pathlib import Path
import xml.etree.ElementTree as ET


def physicalize_visuals(models):
    """Give visual-only static primitives matching physical collision geometry."""
    added = []
    for model in models:
        for link in model.findall('link'):
            if link.findall('collision'):
                continue
            for index, visual in enumerate(link.findall('visual')):
                geometry = visual.find('geometry')
                if geometry is None or len(geometry) != 1 or geometry[0].tag not in ('box','cylinder','sphere'):
                    raise ValueError('visual-only scene geometry must be a supported primitive')
                collision = ET.SubElement(link, 'collision', name=f'physical_{index}')
                pose = visual.find('pose')
                if pose is not None:
                    collision.append(deepcopy(pose))
                collision.append(deepcopy(geometry))
                added.append({'model': model.get('name'), 'link': link.get('name'),
                              'collision': collision.get('name'), 'visual': visual.get('name')})
    return added


def material(visual, color, texture=None):
    old = visual.find('material')
    if old is not None:
        visual.remove(old)
    mat = ET.SubElement(visual, 'material')
    rgba = ' '.join(str(v) for v in (*color, 1))
    ET.SubElement(mat, 'ambient').text = rgba
    ET.SubElement(mat, 'diffuse').text = rgba
    ET.SubElement(mat, 'specular').text = '.08 .08 .08 1'
    metal = ET.SubElement(ET.SubElement(mat, 'pbr'), 'metal')
    if texture is not None:
        ET.SubElement(metal, 'albedo_map').text = str(texture)
    ET.SubElement(metal, 'metalness').text = '0'
    ET.SubElement(metal, 'roughness').text = '.95'


def natural_materials(root, models):
    texture = Path(root)/'simulation/textures/natural_terrazzo.png'
    if not texture.is_file():
        raise FileNotFoundError(texture)
    palette = [(0.20,.50,.56),(.28,.40,.62),(.38,.58,.45),(.62,.49,.32)]
    for index, model in enumerate(models):
        if model.get('name') == 'ground_plane':
            link = model.find('link')
            for visual in link.findall('visual'):
                material(visual, (.80,.77,.70))
            # Repeat a seamless 8m albedo patch across a40x40m visual floor.
            # Collision ground remains the original source plane at Z=0.
            for x in range(-2,3):
                for y in range(-2,3):
                    tile = ET.SubElement(link, 'visual', name=f'natural_floor_{x+2}_{y+2}')
                    ET.SubElement(tile, 'pose').text = f'{8*x} {8*y} .001 0 0 0'
                    plane = ET.SubElement(ET.SubElement(tile,'geometry'),'plane')
                    ET.SubElement(plane,'normal').text = '0 0 1'
                    ET.SubElement(plane,'size').text = '8 8'
                    material(tile, (1,1,1), texture)
            continue
        for link in model.findall('link'):
            originals = list(link.findall('visual'))
            for visual in originals:
                material(visual, palette[index % len(palette)])
                geometry = visual.find('geometry')
                # Two matte bands supply visible features without a checker texture.
                for band_index, factor in enumerate((-.25,.25)):
                    band = ET.SubElement(link, 'visual', name=f'{visual.get("name")}_band_{band_index}')
                    geo = deepcopy(geometry)
                    cylinder = geo.find('cylinder')
                    box = geo.find('box')
                    if cylinder is not None:
                        height = float(cylinder.findtext('length'))
                        cylinder.find('length').text = '.08'
                        cylinder.find('radius').text = str(float(cylinder.findtext('radius'))+.001)
                    elif box is not None:
                        sx,sy,height = map(float,box.findtext('size').split())
                        box.find('size').text = f'{sx+.002} {sy+.002} .08'
                    else:
                        raise ValueError('natural pillar bands support boxes/cylinders only')
                    ET.SubElement(band, 'pose').text = f'0 0 {factor*height} 0 0 0'
                    band.append(geo)
                    material(band, (.83,.87,.84))
    return {'profile':'natural','floor_texture':str(texture),
            'floor_tile_size_m':8,'floor_visual_height_m':.001,
            'pillar_colors':palette,'bands_visual_only':True}
