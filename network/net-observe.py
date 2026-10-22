#!/usr/bin/python3
"""Bounded read-only observations; no user command strings are executed."""
import ipaddress
import json
import os
import re
import subprocess
import sys

env = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C.UTF-8'}
if os.geteuid() != 0:
    sys.exit('Use the documented sudo observation command')
args = sys.argv[1:]
if args == ['firewall']:
    sys.exit(subprocess.run(['/usr/sbin/iptables', '-S'], env=env).returncode)
if len(args) == 3 and args[0] == 'capture' and re.fullmatch(r'eth[0-9]+', args[1]):
    try:
        count = int(args[2])
        assert 1 <= count <= 20
        addresses = json.loads(subprocess.check_output(['/usr/sbin/ip', '-j', '-4', 'address'], env=env))
        assert any(i['ifname'] == args[1] and any(a.get('local', '').startswith('10.78.')
                   for a in i['addr_info']) for i in addresses)
    except (ValueError, AssertionError):
        sys.exit('Use an existing data interface and packet count 1..20')
    result = subprocess.run(['/usr/bin/timeout', '5', '/usr/bin/tcpdump', '-nn', '-l',
                             '-i', args[1], '-c', str(count)], env=env)
    sys.exit(0 if result.returncode in (0, 124) else result.returncode)
sys.exit('Unsupported observation')
