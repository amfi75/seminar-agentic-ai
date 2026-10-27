#!/usr/bin/python3
"""Restore reference veth links after cold namespace recreation, without device reset."""
import subprocess


def run(*args, check=True):
    return subprocess.run(args,check=check,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)


links = [('client','eth1','r1','e1-1'), ('r1','e1-2','r2','e1-1'), ('r2','e1-2','server','eth1')]
for left, li, right, ri in links:
    a,b='clab-seminar-'+left,'clab-seminar-'+right
    has_a=run('docker','exec',a,'ip','link','show',li,check=False).returncode==0
    has_b=run('docker','exec',b,'ip','link','show',ri,check=False).returncode==0
    if has_a != has_b:
        raise SystemExit('Partial data link preserved; use explicit Recover devices')
    if not has_a:
        run('containerlab','tools','veth','create','-a',a+':'+li,'-b',b+':'+ri)
# Endpoint L3 addresses/routes are OS runtime state, provisioned by topology exec
# on initial deploy; Docker start alone does not rerun those commands.
for node,address,prefix,gateway in [('client','10.78.1.10/24','10.78.2.0/24','10.78.1.254'),
                                    ('server','10.78.2.10/24','10.78.1.0/24','10.78.2.254')]:
    target='clab-seminar-'+node
    run('docker','exec',target,'ip','link','set','eth1','up')
    run('docker','exec',target,'ip','address','replace',address,'dev','eth1')
    run('docker','exec',target,'ip','route','replace',prefix,'via',gateway)
print('Reference data links restored; router configuration unchanged')
