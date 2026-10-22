#!/usr/bin/python3
"""Install only the human convenience layer, never rebuild/reset the lab."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import sys
import time

STATE = Path('/var/lib/seminar-lab')
NAMES = {'clab-seminar-' + n for n in ('management', 'client', 'r1', 'r2', 'server')}


def probe():
    recognized = (STATE / 'management-home-identity.json').is_file() and Path('/opt/seminar-lab/broker/labctl_v5.py').is_file()
    result = subprocess.run(['docker', 'ps', '--format', '{{.Names}}'], capture_output=True, text=True)
    running = set(result.stdout.splitlines()) if result.returncode == 0 else set()
    service = subprocess.run(['systemctl', 'is-active', 'seminar-lab'], capture_output=True, text=True)
    top = subprocess.run(['docker', 'top', 'clab-seminar-management', '-eo', 'pid,comm'], capture_output=True, text=True)
    return {'recognized': recognized, 'ready': recognized and NAMES <= running and service.returncode == 0 and top.returncode == 0,
            'active_opencode': any((x.split()[-1].startswith('opencode') if x.split() else False) for x in top.stdout.splitlines()[1:]),
            'missing_nodes': sorted(NAMES - running)}


def safe_path(path):
    for parent in [path, *path.parents]:
        if parent.is_symlink():
            raise ValueError('Refusing linked installation path: ' + str(parent))


def install(source):
    status = probe()
    if not status['ready']:
        raise RuntimeError('Not a ready recognized v5 lab. Preserve the VM and diagnose it; no update/reset was run.')
    if status['active_opencode']:
        raise RuntimeError('Stop OpenCode before installing the convenience files. Profile unchanged.')
    student = pwd.getpwnam('student')
    group = student.pw_gid
    manifest_path = STATE / 'workflow-install.json'
    safe_path(manifest_path)
    old = json.loads(manifest_path.read_text()) if manifest_path.exists() else {'files': {}}
    control = Path('/home/student/labs/control')
    safe_path(control)
    tasks = []
    for label, action in [('Start OpenCode', 'agent'), ('Check network', 'check'), ('Choose scenario', 'scenario'),
                          ('Review proposed change', 'review'), ('Approve reviewed change', 'approve'),
                          ('Reset network', 'reset'), ('Start fresh trial', 'fresh'),
                          ('Advanced: workload controls', 'traffic')]:
        tasks.append({'label': 'Lab: ' + label, 'type': 'process', 'command': '/usr/local/bin/lab-workflow',
                      'args': [action], 'problemMatcher': [], 'presentation': {'reveal': 'always', 'focus': True, 'panel': 'dedicated'},
                      'runOptions': {'instanceLimit': 1}})
    workspace = {'folders': [{'name': 'Lab controls', 'path': '.'}, {'name': 'Topology editing (separate lab)', 'path': '../ui'}],
                 'tasks': {'version': '2.0.0', 'tasks': tasks},
                 'extensions': {'recommendations': ['srl-labs.vscode-containerlab']}}
    payloads = {
        Path('/usr/local/bin/lab-workflow'): ((source / 'workflow.py').read_bytes(), 0o750, 0, group),
        Path('/usr/local/sbin/lab-fresh-trial'): ((source / 'fresh_trial_entry.py').read_bytes(), 0o700, 0, 0),
        Path('/opt/seminar-lab/management/install_workflow.py'): (Path(__file__).read_bytes(), 0o700, 0, 0),
        control / 'lab.code-workspace': ((json.dumps(workspace, indent=2) + '\n').encode(), 0o600, student.pw_uid, group),
        control / 'START.md': ((source / 'workflow-start.md').read_bytes(), 0o600, student.pw_uid, group),
        Path('/etc/sudoers.d/seminar-workflow'): (b'student ALL=(root) NOPASSWD: /usr/local/sbin/lab-fresh-trial ""\n', 0o440, 0, 0),
    }
    # Validate all collisions before writing any payload.
    for path, (data, mode, uid, gid) in payloads.items():
        safe_path(path)
        if path.exists():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            expected = old['files'].get(str(path))
            if path == Path('/opt/seminar-lab/management/install_workflow.py') and path.read_bytes() == data:
                continue
            if expected is None or digest != expected:
                raise ValueError('Existing/unmanaged edits preserved; review collision: ' + str(path))
    for directory in [control.parent, control]:
        directory.mkdir(exist_ok=True, mode=0o700)
        os.chown(directory, student.pw_uid, group)
    files = {}
    for path, (data, mode, uid, gid) in payloads.items():
        if path.exists() and path.read_bytes() != data:
            backup = path.with_name(path.name + '.before-workflow-' + str(time.time_ns()))
            shutil.copy2(path, backup)
            os.chmod(backup, 0o600)
        temporary = path.with_name(path.name + '.workflow-new')
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            os.write(fd, data)
            os.fchmod(fd, mode)
            os.fchown(fd, uid, gid)
        finally:
            os.close(fd)
        if str(path).startswith('/etc/sudoers.d/'):
            subprocess.run(['visudo', '-cf', str(temporary)], check=True)
        os.replace(temporary, path)
        files[str(path)] = hashlib.sha256(data).hexdigest()
    subprocess.run(['visudo', '-c'], check=True, stdout=subprocess.DEVNULL)
    manifest_path.write_text(json.dumps({'version': 1, 'files': files}, indent=2) + '\n')
    manifest_path.chmod(0o600)
    print(json.dumps({'installed': True, 'workspace': str(control / 'lab.code-workspace'), 'network_recreated': False, 'profile_replaced': False}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--probe', action='store_true')
    parser.add_argument('--authorize-key')
    parser.add_argument('--source-dir', type=Path, default=Path(__file__).parent)
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise PermissionError('Use the Multipass technical account with sudo for installation.')
    if args.authorize_key:
        key = args.authorize_key.strip()
        import base64
        parts = key.split()
        if len(parts) < 2 or parts[0] != 'ssh-ed25519' or '\n' in key or '\r' in key:
            raise ValueError('Expected one Ed25519 public key.')
        base64.b64decode(parts[1], validate=True)
        if not probe()['recognized']:
            raise ValueError('Not a recognized v5 lab.')
        student = pwd.getpwnam('student')
        directory = Path('/home/student/.ssh')
        safe_path(directory)
        directory.mkdir(mode=0o700, exist_ok=True)
        path = directory / 'authorized_keys'
        safe_path(path)
        old = path.read_text() if path.exists() else ''
        known = [line.split()[:2] for line in old.splitlines()]
        if parts[:2] not in known:
            if path.exists():
                shutil.copy2(path, path.with_name('authorized_keys.before-workflow-' + str(time.time_ns())))
            with path.open('a') as stream:
                stream.write(('\n' if old and not old.endswith('\n') else '') + key + '\n')
        for target, mode in [(directory, 0o700), (path, 0o600)]:
            os.chown(target, student.pw_uid, student.pw_gid)
            target.chmod(mode)
        print('Student public key authorized; existing entries preserved.')
    elif args.probe:
        print(json.dumps(probe()))
    else:
        install(args.source_dir)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('Workflow installation failed: ' + str(error), file=sys.stderr)
        sys.exit(1)
