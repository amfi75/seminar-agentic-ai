#!/usr/bin/python3 -I
"""Fixed human-only sudo entry point. No arguments or interpreter permissions."""
import os
import sys

if os.geteuid() != 0 or len(sys.argv) != 1 or os.environ.get('SUDO_USER', 'root') not in ('student', 'ubuntu', 'root'):
    sys.exit('Use the human Start fresh trial task; arguments are not allowed.')
os.execve('/bin/bash', ['bash', '/opt/seminar-lab/management/fresh_management.sh'],
          {'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin', 'HOME': '/root', 'LANG': 'C.UTF-8'})
