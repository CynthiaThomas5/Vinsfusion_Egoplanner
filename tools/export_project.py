#!/usr/bin/env python3
"""Create a local source delivery; exclude downloads, builds, raw logs and secrets."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import tarfile

ROOT=Path(__file__).resolve().parents[1]


def files_to_share(root):
    root=Path(root)
    result=[]
    for name in ['README.md','AGENTS.md','GOAL.md','.gitignore','start.sh']:
        if (root/name).is_file():result.append(root/name)
    for folder in ['src/own','config','simulation','dependencies','docker','docs','tools','progress','collaboration']:
        for p in sorted((root/folder).rglob('*')):
            rel=p.relative_to(root)
            if not p.is_file() or p.is_symlink():continue
            if any(part in ['__pycache__','.git','.pytest_cache','raw','local'] for part in rel.parts):continue
            if p.name.startswith('.env') or p.suffix in ['.pem','.key','.pyc'] or p.name=='auth.json':continue
            result.append(p)
    for folder in ['src/vendor','external','artifacts']:
        p=root/folder/'README.md'
        if p.is_file():result.append(p)
    return sorted(set(result))


def file_hash(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def export(root, output, code_only=False):
    root=Path(root).resolve();output=Path(output).resolve()
    if output.exists():raise FileExistsError('Refusing to overwrite delivery directory: '+str(output))
    selected=files_to_share(root)
    lock=json.loads((root/'dependencies/sources.json').read_text())
    image=lock['container_rebuild']['portable_image_bundle']
    source_image=root/image['path']
    if not code_only and (not source_image.is_file() or file_hash(source_image)!=image['sha256']):
        raise ValueError('Verified fixed image bundle is missing; supply it or explicitly use --code-only')
    output.mkdir(parents=True)
    archive=output/'project-source.tar.gz'
    with archive.open('wb') as raw, gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as compressed:
        with tarfile.open(fileobj=compressed,mode='w') as tar:
            for p in selected:
                info=tar.gettarinfo(str(p),'project/'+p.relative_to(root).as_posix())
                info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
                with p.open('rb') as stream:tar.addfile(info,stream)
    artifacts={archive.name:file_hash(archive)}
    if not code_only:
        dest=output/'container-images.tar.zst'
        try:os.link(source_image,dest)
        except OSError:shutil.copyfile(source_image,dest)
        artifacts[dest.name]=image['sha256']
    manifest={'scope':'Local delivery only; no upload or Git operation. Runtime verification is documented separately.',
              'files':{p.relative_to(root).as_posix():file_hash(p) for p in selected},'artifacts_sha256':artifacts,
              'image_included':not code_only}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (output/'SHA256SUMS').write_text(''.join(f'{h}  {name}\n' for name,h in artifacts.items()))
    (output/'README.txt').write_text('Verify: sha256sum -c SHA256SUMS\nLoad environment: zstd -dc container-images.tar.zst | docker load\nExtract: tar -xzf project-source.tar.gz\nThen: cd project; bash tools/project.sh fetch; bash tools/project.sh build\nRead project/README.md before starting simulation.\n'+('CODE ONLY: the fixed image archive is a separate required input.\n' if code_only else ''))
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path);parser.add_argument('--code-only',action='store_true');args=parser.parse_args()
    report=export(ROOT,args.output,args.code_only);print(f"Delivery saved: {args.output}; {len(report['files'])} source/metadata files")
