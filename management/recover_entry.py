#!/usr/bin/python3 -I
"""Explicit student-only out-of-band recovery, preserving the management volume."""
import os
import sys
import subprocess
import pathlib
if os.geteuid() != 0 or len(sys.argv) != 1 or os.environ.get('SUDO_USER','root') not in ('student','ubuntu','root'):
    sys.exit('Use the student Recover devices task; no arguments allowed.')
env={'PATH':'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin','HOME':'/root','LANG':'C.UTF-8'}
r=subprocess.run(['docker','top','clab-seminar-management','-eo','pid,comm'],capture_output=True,text=True,env=env)
if r.returncode == 0 and any(line.split()[-1].startswith('opencode') for line in r.stdout.splitlines()[1:] if line.split()):
    sys.exit('Stop OpenCode before recovery. Management home is unchanged.')
pathlib.Path('/var/lib/seminar-lab/rebuild-request').touch(mode=0o600)
os.execve('/bin/systemctl',['systemctl','restart','seminar-lab'],env)
