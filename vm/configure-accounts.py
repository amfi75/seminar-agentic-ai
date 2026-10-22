#!/usr/bin/python3
"""Separate the human operator from the agent; preserve legacy agent data."""
import hashlib
import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import tempfile


def run(*args):
    subprocess.run(args, check=True)


def signature(directory):
    result = {}
    for current, directories, files in os.walk(directory, followlinks=False):
        for name in directories + files:
            path = Path(current) / name
            relative = str(path.relative_to(directory))
            if path.is_symlink():
                result[relative] = ('symlink', os.readlink(path))
            elif path.is_file():
                result[relative] = ('file', hashlib.sha256(path.read_bytes()).hexdigest())
            else:
                result[relative] = ('directory',)
    return result


assert os.geteuid() == 0, 'Run as administrator'
try:
    agent = pwd.getpwnam('agent')
except KeyError:
    run('/usr/sbin/useradd', '--create-home', '--shell', '/bin/bash',
        '--comment', 'Restricted seminar agent', 'agent')
    agent = pwd.getpwnam('agent')
try:
    student = pwd.getpwnam('student')
except KeyError:
    run('/usr/sbin/useradd', '--create-home', '--shell', '/bin/bash',
        '--comment', 'Human seminar student', 'student')
    student = pwd.getpwnam('student')

agent_home = Path('/home/agent')
assert agent.pw_dir == str(agent_home) and not agent_home.is_symlink()
state = Path('/var/lib/seminar-lab')
state.mkdir(mode=0o700, exist_ok=True)
marker = state / 'account-migration-v2.json'
legacy = student.pw_gecos == 'Seminar agent account'
if legacy:
    # Never grant Docker to an account while its old model process is running.
    for entry in Path('/proc').iterdir():
        if entry.name.isdigit():
            try:
                if entry.stat().st_uid == student.pw_uid:
                    name = (entry / 'comm').read_text().strip()
                    assert not name.startswith('opencode'), 'Close legacy OpenCode before migration'
            except (FileNotFoundError, ProcessLookupError):
                pass
    source = Path(student.pw_dir)
    paths = ['experiment', '.config/opencode', '.local/share/opencode',
             '.local/state/opencode', '.cache/opencode']
    migrated = []
    count = 0
    for relative in paths:
        origin, target = source / relative, agent_home / relative
        if not origin.exists():
            continue
        assert origin.is_dir() and not origin.is_symlink(), 'Unexpected legacy data path'
        for parent in [target, *target.parents]:
            assert not parent.is_symlink(), 'Unexpected target symlink'
        expected = signature(origin)
        if target.exists():
            # An interrupted earlier migration can resume, but never overwrite
            # different work belonging to an existing agent account.
            assert signature(target) == expected, 'Agent data collision; original preserved'
        else:
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with tempfile.TemporaryDirectory(prefix='.migration-', dir=agent_home) as temp:
                staged = Path(temp) / 'data'
                shutil.copytree(origin, staged, symlinks=True)
                assert signature(staged) == expected, 'Copy verification failed'
                staged.rename(target)
        migrated.append(relative)
        count += sum(value[0] == 'file' for value in expected.values())
    marker.write_text(json.dumps({'legacy_migration': True, 'verified': True,
                                 'copied_paths': migrated, 'verified_files': count,
                                 'originals_preserved': True}, indent=2) + '\n')
elif not marker.exists():
    marker.write_text(json.dumps({'legacy_migration': False, 'verified': True,
                                 'originals_preserved': True}, indent=2) + '\n')
marker.chmod(0o600)

# lchown preserves symlink targets; no recursive traversal through symlinks.
os.chown(agent_home, agent.pw_uid, agent.pw_gid)
agent_home.chmod(0o700)
for current, directories, files in os.walk(agent_home, followlinks=False):
    for name in directories + files:
        os.chown(Path(current) / name, agent.pw_uid, agent.pw_gid, follow_symlinks=False)
run('/usr/sbin/usermod', '--groups', '', 'agent')
run('/usr/sbin/usermod', '--append', '--groups', 'docker', '--comment',
    'Human seminar student', 'student')
print('Accounts configured; legacy data verified when present. Originals retained.')
