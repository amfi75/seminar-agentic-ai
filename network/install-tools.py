#!/usr/bin/env python3
"""Install the same pinned native clients in the guest and management image."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import time
import urllib.request


def architecture(name):
    aliases = {'x86_64': 'amd64', 'amd64': 'amd64', 'aarch64': 'arm64', 'arm64': 'arm64'}
    if name not in aliases:
        raise ValueError('Unsupported guest architecture: ' + name)
    return aliases[name]


def artifact(tool, arch, manifest=None):
    versions = manifest if manifest is not None else json.loads(Path(__file__).with_name('versions.json').read_text())
    return versions[tool]['artifacts'][architecture(arch)]


def download(spec, destination):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(spec['url'], timeout=120) as source, destination.open('wb') as target:
                shutil.copyfileobj(source, target)
            break
        except (OSError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(2)
    if hashlib.sha256(destination.read_bytes()).hexdigest() != spec['sha256']:
        destination.unlink()
        raise ValueError('Checksum mismatch: ' + spec['url'])


def install(tool, spec, stage):
    file = stage / (tool + ('.tar.gz' if tool == 'opencode' else '.deb'))
    download(spec, file)
    if tool == 'opencode':
        # Extract only the expected executable, never paths supplied by an archive.
        with tarfile.open(file) as bundle:
            member = bundle.getmember('opencode')
            if not member.isfile():
                raise ValueError('OpenCode archive does not contain a regular executable')
            with bundle.extractfile(member) as source, (stage / 'opencode').open('wb') as target:
                shutil.copyfileobj(source, target)
        subprocess.run(['install', '-m', '0755', str(stage / 'opencode'), '/usr/local/bin/opencode'], check=True)
    else:
        subprocess.run(['apt-get', 'install', '-y', '-qq', str(file)], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arch', help='Architecture; defaults to this guest architecture')
    parser.add_argument('--resolve', action='store_true', help='Print selection without downloading/installing')
    parser.add_argument('tools', nargs='+', choices=['containerlab', 'gnmic', 'opencode'])
    args = parser.parse_args()
    arch = architecture(args.arch or subprocess.check_output(['dpkg', '--print-architecture'], text=True).strip())
    selected = {tool: artifact(tool, arch) for tool in args.tools}
    if args.resolve:
        print(json.dumps({'architecture': arch, 'tools': selected}, indent=2))
        return
    if os.geteuid() != 0:
        parser.error('Installation requires root')
    # Resolve all artifacts before changing the guest; checksum failure stops installation.
    with tempfile.TemporaryDirectory(prefix='seminar-tools-') as directory:
        for tool, spec in selected.items():
            install(tool, spec, Path(directory))


if __name__ == '__main__':
    main()
