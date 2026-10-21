#!/usr/bin/env python3
"""Materialize the model for a debug-only moving sensor rig, not a flight scene."""
import argparse
from copy import deepcopy
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def prepare(output):
    if output.exists():
        raise FileExistsError(output)
    tree = ET.parse(ROOT/'simulation/worlds/sensor_calibration.sdf')
    fixture = tree.find('world/model[@name="sensor_fixture"]')
    fixture.remove(fixture.find('joint'))
    fixture.remove(fixture.find('include'))
    link = deepcopy(ET.parse(ROOT/'simulation/models/d435i/model.sdf').find('model/link'))
    ET.SubElement(link,'gravity').text = 'false'
    fixture.append(link)
    force = ET.SubElement(tree.find('world'),'plugin',filename='gz-sim-apply-link-wrench-system',name='gz::sim::systems::ApplyLinkWrench')
    ET.SubElement(force,'verbose').text = 'false'
    pose = ET.SubElement(fixture,'plugin',filename='gz-sim-pose-publisher-system',name='gz::sim::systems::PosePublisher')
    for key,value in [('publish_model_pose','true'),('publish_link_pose','false'),('publish_nested_model_pose','false'),('use_pose_vector_msg','true'),('update_frequency','100')]:
        ET.SubElement(pose,key).text = value
    ET.indent(tree)
    tree.write(output,encoding='unicode',xml_declaration=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    prepare(args.output)
