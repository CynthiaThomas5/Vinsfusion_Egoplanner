#!/usr/bin/env python3
"""Generate a real static narrow passage, preserving the qualified room scene."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def prepare(source, output, width=2.4):
    source,output=Path(source),Path(output)
    if output.exists():raise ValueError('refuse existing scene')
    if not 0 < width < 10:raise ValueError('invalid passage width')
    tree=ET.parse(source);world=tree.getroot().find('world')
    removed=[]
    for model in list(world.findall('model')):
        if model.get('name','').startswith('n13_staggered_cylinder_'):
            removed.append(model.get('name'));world.remove(model)
    if len(removed)!=3:raise ValueError('expected qualified three-cylinder source')
    original=[ET.tostring(m) for m in world.findall('model')]
    for side,sign in [('left',1),('right',-1)]:
        model=ET.SubElement(world,'model',name='n14_corridor_'+side)
        ET.SubElement(model,'static').text='true'
        ET.SubElement(model,'pose').text=f'0 {sign*(width/2+.1)} 1.5 0 0 0'
        link=ET.SubElement(model,'link',name='wall')
        for kind in ['collision','visual']:
            part=ET.SubElement(link,kind,name=side+'_'+kind)
            box=ET.SubElement(ET.SubElement(part,'geometry'),'box')
            ET.SubElement(box,'size').text='6 0.2 3'
            if kind=='visual':
                material=ET.SubElement(part,'material')
                ET.SubElement(material,'ambient').text='0.65 0.65 0.65 1'
                ET.SubElement(material,'diffuse').text='0.65 0.65 0.65 1'
    assert original==[ET.tostring(m) for m in world.findall('model') if not m.get('name','').startswith('n14_corridor_')]
    output.parent.mkdir(parents=True,exist_ok=True);tree.write(output,encoding='utf-8',xml_declaration=True)
    report={'schema':'n14-corridor-provenance/v1','status':'prepared_not_flight_qualified',
            'source':str(source.resolve()),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'output_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
            'removed_models':removed,'room_models_unchanged':True,'clear_width_m':width,
            'corridor_x_world_m':[-3,3],'wall_thickness_m':.2,'wall_height_m':3,
            'online_truth_or_prior_map_added':False}
    output.with_suffix('.provenance.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--width',type=float,default=2.4)
    a=p.parse_args();print(json.dumps(prepare(a.source,a.output,a.width)))
