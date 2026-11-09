#!/usr/bin/env python3
"""Reproduce the current ARM Agent library, then patch only framing in isolation."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

BASE_SHA = 'cb802f0a2f3e2bdf5af83d9fa64fb56e84bbcbbd515020d5e40eef7052585651'
SOURCE_SHA = 'a22d5164bf6af6f69b749e2442466af22e7fbf5ad0cb55ac1168fa1197f866f4'
REVISION = '73622810d984349b80bbac0ef55fc0b694d62222'
RELATIVE_SOURCE = 'src/cpp/transport/stream_framing/StreamFramingProtocol.cpp'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    build = source / 'build'
    workspace = Path(__file__).resolve().parents[1]
    patch = workspace / 'dependencies/patches/agent/0002-serial-framing-resync.patch'
    revision = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != REVISION or sha(source / RELATIVE_SOURCE) != SOURCE_SHA:
        raise RuntimeError('Source differs from the measured v2.4.3 framing baseline')
    installed = Path('/usr/local/lib/libmicroxrcedds_agent.so.2.4.3')
    if sha(installed) != BASE_SHA:
        raise RuntimeError('Installed Agent differs from the measured ARM baseline')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    link = shlex.split((build / 'CMakeFiles/microxrcedds_agent.dir/link.txt').read_text())
    index = link.index('-o') + 1
    baseline = output / 'baseline.so'
    link[index] = str(baseline)
    subprocess.run(link, cwd=build, check=True)
    if sha(baseline) != sha(build / 'libmicroxrcedds_agent.so.2.4.3'):
        raise RuntimeError('Original build cannot be reproduced')

    def remove_rpath(path):
        script = output / 'remove-rpath.cmake'
        script.write_text('file(RPATH_REMOVE FILE "' + str(path) + '")\n')
        subprocess.run(['cmake', '-P', str(script)], check=True)

    remove_rpath(baseline)
    if sha(baseline) != BASE_SHA:
        raise RuntimeError('Relinked baseline differs from the installed library')
    copied = output / 'source' / RELATIVE_SOURCE
    copied.parent.mkdir(parents=True)
    copied.write_bytes((source / RELATIVE_SOURCE).read_bytes())
    subprocess.run(['patch', '--batch', '-p1', '-i', str(patch)], cwd=output / 'source', check=True)
    flags = {}
    for line in (build / 'CMakeFiles/microxrcedds_agent.dir/flags.make').read_text().splitlines():
        if ' = ' in line:
            key, value = line.split(' = ', 1)
            flags[key] = shlex.split(value)
    compiler = ['/usr/bin/c++'] + flags['CXX_DEFINES'] + flags['CXX_INCLUDES'] + flags['CXX_FLAGS']
    obj = output / 'framing.o'
    subprocess.run(compiler + ['-c', str(copied), '-o', str(obj)], check=True)
    key = 'CMakeFiles/microxrcedds_agent.dir/' + RELATIVE_SOURCE + '.o'
    if link.count(key) != 1:
        raise RuntimeError('Expected exactly one original framing object')
    link[link.index(key)] = str(obj)
    target = output / 'lib/libmicroxrcedds_agent.so.2.4.3'
    target.parent.mkdir()
    link[index] = str(target)
    subprocess.run(link, cwd=build, check=True)
    remove_rpath(target)
    (target.parent / 'libmicroxrcedds_agent.so.2.4').symlink_to(target.name)
    (output / 'COLCON_IGNORE').touch()
    test = output / 'test-framing'
    subprocess.run(compiler + ['-UNDEBUG', str(workspace / 'tools/test_agent_framing.cpp'), str(copied), '-o', str(test)], check=True)
    subprocess.run([str(test)], check=True)
    if sha(installed) != BASE_SHA or sha(source / RELATIVE_SOURCE) != SOURCE_SHA:
        raise RuntimeError('Read-only baseline changed during build')
    inputs = {}
    for value in link:
        path = Path(value)
        path = path if path.is_absolute() else build / path
        if path.is_file() and path != target:
            inputs[str(path)] = sha(path)
    manifest = {'base_revision': revision, 'baseline_sha256': sha(baseline),
                'candidate_sha256': sha(target), 'source_sha256': sha(copied),
                'patch_sha256': sha(patch), 'link': link, 'link_inputs_sha256': inputs}
    (output / 'build-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({k: v for k, v in manifest.items() if k.endswith('sha256') and isinstance(v, str)}, indent=2))


if __name__ == '__main__':
    main()
