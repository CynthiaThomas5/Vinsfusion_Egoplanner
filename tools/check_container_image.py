#!/usr/bin/env python3
"""Verify immutable runtime content across Docker image-store representations."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def runtime_content(image):
    return {key:image[key] for key in ('Architecture','Os','Config','RootFS')}


def content_sha256(image):
    return hashlib.sha256(json.dumps(runtime_content(image),sort_keys=True,separators=(',',':')).encode()).hexdigest()


def verify_image(image, runtime):
    actual=content_sha256(image)
    expected=runtime.get('image_content_sha256')
    if expected:
        if actual != expected:
            raise ValueError('Fixed container runtime content differs from the pinned configuration')
    elif image['Id'] != runtime['image_id']:
        raise ValueError('Fixed container image identity mismatch')
    return {'tag':runtime['image'],'image_id':image['Id'],
            'recorded_original_image_id':runtime['image_id'],
            'content_sha256':actual,'architecture':image['Architecture'],'os':image['Os']}


def inspect_and_verify(runtime):
    image=json.loads(subprocess.check_output(['docker','image','inspect',runtime['image']],text=True))[0]
    return verify_image(image,runtime)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',type=Path,default=Path(__file__).resolve().parents[1]/'config/runtime.json')
    args=parser.parse_args()
    print(json.dumps(inspect_and_verify(json.loads(args.runtime.read_text())),sort_keys=True))
