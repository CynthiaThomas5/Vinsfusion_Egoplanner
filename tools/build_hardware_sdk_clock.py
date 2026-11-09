#!/usr/bin/env python3
"""Reproduce pinned HID SDK, then rebuild only its clock translation unit in isolation."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

BASE_SHA='a72cc3c5030be54ee532347d10a40b3839535bc79b2b4709d10d452c370b69f9'


def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--source',type=Path,required=True);p.add_argument('--build',type=Path,required=True)
 p.add_argument('--commands',type=Path,required=True);p.add_argument('--patch',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
 a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 commands=json.loads(a.commands.read_text());link=list(commands['link'])
 baseline=out/'baseline/librealsense2.so.2.58.1';baseline.parent.mkdir()
 link[link.index('-o')+1]=str(baseline)
 subprocess.run(link,cwd=a.build,check=True)
 baseline_sha=hashlib.sha256(baseline.read_bytes()).hexdigest()
 if baseline_sha!=BASE_SHA:raise RuntimeError('Baseline relink differs from pinned runtime SDK: '+baseline_sha)
 source=out/'source/src/global_timestamp_reader.cpp';source.parent.mkdir(parents=True)
 source.write_bytes((a.source/'src/global_timestamp_reader.cpp').read_bytes())
 subprocess.run(['patch','--batch','-p1','-i',str(a.patch.resolve())],cwd=out/'source',check=True)
 obj=out/'global_timestamp_reader.cpp.o';compile=list(commands['compile'])
 compile[compile.index('-o')+1]=str(obj);compile[compile.index('-c')+1]=str(source)
 subprocess.run(compile,cwd=a.build,check=True)
 target=out/'lib/librealsense2.so.2.58.1';target.parent.mkdir()
 link[link.index('-o')+1]=str(target)
 matched=[i for i,v in enumerate(link) if v.endswith('/src/global_timestamp_reader.cpp.o')]
 if len(matched)!=1:raise RuntimeError('Expected one clock object in original link')
 link[matched[0]]=str(obj);subprocess.run(link,cwd=a.build,check=True)
 for name in ('librealsense2.so.2.58','librealsense2.so'):(target.parent/name).symlink_to(target.name)
 inputs={}
 for v in commands['link']:
  path=Path(v);path=path if path.is_absolute() else a.build/path
  if path.is_file():inputs[str(path.resolve())]=hashlib.sha256(path.read_bytes()).hexdigest()
 manifest={'baseline_sha256':baseline_sha,'candidate_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
  'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'patch_sha256':hashlib.sha256(a.patch.read_bytes()).hexdigest(),
  'compile':compile,'link':link,'object_inputs_sha256':inputs}
 (out/'build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({k:v for k,v in manifest.items() if k.endswith('sha256') and not isinstance(v,dict)},indent=2))


if __name__=='__main__':main()
