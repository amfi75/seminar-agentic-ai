#!/usr/bin/python3
"""Human terminal tasks. Native authorization stays in lab-admin."""
import fcntl
import json
import os
from pathlib import Path
import pwd
import re
import subprocess
import sys

ADMIN = '/usr/local/sbin/lab-admin'
CONTAINER = 'clab-seminar-management'
SCENARIOS = {'1': ('fault', 'Routing incident'), '2': ('delay', 'Delay and jitter'),
             '3': ('loss', 'Packet loss'), '4': ('rate', 'Bandwidth limit'),
             '5': ('clear-impairment', 'Clear performance impairment')}


def run(args):
    result = subprocess.run(args, text=True, capture_output=True)
    if result.stdout:
        print(result.stdout, end='' if result.stdout.endswith('\n') else '\n')
    if result.returncode:
        raise RuntimeError((result.stderr or 'Command failed').strip())
    return result.stdout


def admin(*args):
    raw = run(['sudo', '-n', ADMIN, *args])
    result = json.loads(raw)
    if result.get('requires_recovery') or ('applied' in result and args[0] == 'approve' and not result['applied']):
        raise RuntimeError('Application failed; inspect the result and recover deliberately. No automatic reset was performed.')
    return result


def ask(prompt):
    value = input(prompt + ': ').strip()
    if not value:
        raise ValueError('Cancelled; nothing was applied.')
    return value


def confirm(message, token='yes'):
    if input(message + '\nType ' + token + ' to continue; anything else cancels: ').strip() != token:
        raise ValueError('Cancelled; nothing was applied.')


def active():
    result = subprocess.run(['docker', 'top', CONTAINER, '-eo', 'pid,comm'], text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError('Management is unavailable. Open the lab from your host first.')
    return any((x.split()[-1].startswith('opencode') if x.split() else False) for x in result.stdout.splitlines()[1:])


def start_agent():
    directory = Path.home() / '.local/state/seminar-lab'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (directory / 'opencode.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('An OpenCode terminal is already open. Return to that terminal or quit it first.')
        if active():
            raise RuntimeError('OpenCode is already running in management. Return to its terminal or quit it first.')
        identity = subprocess.check_output(['docker', 'exec', '--user', 'agent', CONTAINER, 'id', '-u'], text=True).strip()
        if identity != '1100':
            raise RuntimeError('Unexpected management identity; refusing to start the harness.')
        print('OpenCode runs as agent in management, from /home/agent.\nRead workspace/inventory.md and workspace/task.txt.\nUse /models to select an authorized model; no model is selected automatically.', flush=True)
        return subprocess.call(['docker', 'exec', '-it', '--user', 'agent', '-w', '/home/agent', CONTAINER, 'flock', '-n', '/tmp/seminar-opencode.lock', 'opencode'])


def dispatch(action):
    if action == 'agent':
        return start_agent()
    if action == 'check':
        print('Expected: client_80/server_80/server_8081 true; client_8081 false.\nA scenario outage is a failed application check, not a failed VS Code connection.')
        admin('verify')
    elif action == 'scenario':
        for key, (_, label) in SCENARIOS.items():
            print(key + '. ' + label)
        choice = ask('Choose scenario (blank cancels)')
        if choice not in SCENARIOS:
            raise ValueError('Unknown scenario; no action taken.')
        operation, label = SCENARIOS[choice]
        confirm('Human action: ' + label + '. This changes the reference network.')
        admin(operation)
    elif action == 'review':
        target = ask('Target router (r1 or r2)')
        protocol = ask('Native protocol (gnmi or netconf)')
        filename = ask('File relative to /home/agent/workspace')
        reason = ask('Your reason after reviewing the observations')
        if target not in ('r1', 'r2') or protocol not in ('gnmi', 'netconf'):
            raise ValueError('Choose r1/r2 and gnmi/netconf. No import performed.')
        parts = filename.split('/')
        if any(p in ('', '.', '..') for p in parts) or '\x00' in filename or len(filename) > 900:
            raise ValueError('Use a regular file within the management workspace.')
        if len(reason) > 2000:
            raise ValueError('Reason must be at most 2000 characters.')
        result = admin('import', target, protocol, '/home/agent/workspace/' + filename, reason)
        identity = result['candidate']
        admin('show', identity)
        print('\nImported and reviewed ONLY. No change applied.\nCandidate: ' + identity + '\nUse the separate Approve reviewed change task if you decide to approve it.')
    elif action == 'approve':
        identity = ask('Exact full candidate ID from your review')
        if not re.fullmatch('[0-9a-f]{64}', identity):
            raise ValueError('A full 64-character candidate ID is required. No approval performed.')
        admin('show', identity)
        confirm('Approve exactly this candidate? ' + identity, identity)
        admin('approve', identity)
        print('\nApplication/readback completed. Checking correctness independently:')
        admin('verify')
    elif action == 'reset':
        confirm('Reset restores device baseline, clears impairments, resumes workload, and invalidates candidates.\nIt PRESERVES OpenCode history; it does not make an independent fresh trial.')
        admin('reset')
    elif action == 'fresh':
        if active():
            raise RuntimeError('Stop OpenCode before making a fresh trial. Your profile is unchanged.')
        confirm('Fresh trial REPLACES the management home after privately archiving and verifying it.\nIt recreates the reference topology; stop all experiments first.\nProvider login/model selection may be needed again. This is different from network reset.', 'fresh trial')
        run(['sudo', '-n', '/usr/local/sbin/lab-fresh-trial'])
    elif action == 'traffic':
        print('1. Status\n2. Pause workload for an explicitly isolated measurement\n3. Resume workload')
        choice = ask('Choose workload action')
        operation = {'1': 'status', '2': 'pause', '3': 'resume'}.get(choice)
        if not operation:
            raise ValueError('Unknown workload action; no action taken.')
        if operation != 'status':
            confirm('Workload action: ' + operation)
        admin('workload', operation)
        if operation == 'pause':
            print('Wait 20 seconds before isolated measurements. Record that workload was paused, then resume it.')
    else:
        raise ValueError('Use agent, check, scenario, review, approve, reset, fresh, or traffic.')
    return 0


def main():
    if os.getuid() != pwd.getpwnam('student').pw_uid:
        raise PermissionError('This helper is for the human student VM account only.')
    if len(sys.argv) != 2:
        raise ValueError('Choose a named Lab task in VS Code.')
    return dispatch(sys.argv[1])


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (EOFError, KeyboardInterrupt):
        print('\nCancelled.', file=sys.stderr)
        sys.exit(1)
    except Exception as error:
        print('Lab task failed: ' + str(error), file=sys.stderr)
        sys.exit(1)
