#!/opt/seminar-tools/bin/python
"""Generate private human startup snippets; Containerlab supplies fresh TLS."""
import pathlib,json,pwd,os,shutil,sys
s=pathlib.Path('/var/lib/seminar-lab');home=pathlib.Path('/home/student');u=pwd.getpwnam('student')
assert home.is_dir() and not home.is_symlink()
assert sys.argv[1:] in [[],['--refresh-startup']]
refresh=bool(sys.argv[1:])
d=home/'labs';d.mkdir(mode=0o700,exist_ok=True);assert not d.is_symlink()
d=d/'ui';d.mkdir(mode=0o700,exist_ok=True);assert not d.is_symlink()
if not refresh:assert not any(d.iterdir()),'Preserve your UI work before generating a new exercise'
c=json.loads((s/'device-credentials.json').read_text())
for node in ['r1','r2','r3']:
 target=d/(node+'.cli');assert not target.exists(),'Preserve existing startup edits before regeneration'
 text=(pathlib.Path('/opt/seminar-lab/network/ui')/(node+'.cli')).read_text()
 # Native partial CLI is applied after fresh Containerlab defaults/TLS creation.
 # No observer identity is created in this separate human topology.
 text += 'set / system aaa authentication admin-user password "'+c['disabled']+'"\n'
 text += 'set / system aaa authentication linuxadmin-user password "'+c['disabled']+'"\n'
 text += 'set / system aaa authentication user operator password "'+c['operator']+'"\n'
 text += 'set / system aaa authentication user operator superuser true\n'
 text += 'set / system json-rpc-server network-instance mgmt http admin-state disable\n'
 text += 'set / system grpc-server mgmt services [ gnmi ]\n'
 for server in ['insecure-mgmt','eda-discovery','eda-mgmt','eda-insecure-mgmt']:text += 'set / system grpc-server '+server+' admin-state disable\n'
 text += 'delete / system snmp access-group SNMPv2-RO-Community\n'
 target.write_text(text);target.chmod(0o600);os.chown(target,u.pw_uid,u.pw_gid)
if not refresh:
 shutil.copytree(s/'ssh/client',d/'keys/client');shutil.copytree(s/'ssh/server',d/'keys/server')
 text=pathlib.Path('/opt/seminar-lab/network/topology.clab.yml').read_text().replace('name: seminar\n','name: ui\n',1).replace('/var/lib/seminar-lab/ssh/',str(d)+'/keys/')
 # Human editing lab gets a separate home; it must never mount the reference agent profile.
 text=text.replace('seminar-management-home:/home/agent','seminar-ui-management-home:/home/agent')
 text=text.replace('    r1:\n      kind: nokia_srlinux','    r1:\n      startup-config: r1.cli\n      kind: nokia_srlinux').replace('    r2:\n      kind: nokia_srlinux','    r2:\n      startup-config: r2.cli\n      kind: nokia_srlinux')
 (d/'exercise.clab.yml').write_text(text)
 (d/'exercise.clab.yml.annotations.json').write_text(json.dumps({'nodeAnnotations':[
  {'id':'management','icon':'controller'}, {'id':'client','icon':'client'}, {'id':'server','icon':'server'}
 ]},indent=2)+'\n')
 (d/'README.txt').write_text('Human UI: remove the r1:e1-2 to r2:e1-1 link; add r3 (nokia_srlinux, ixr-d2l, same pinned image), management 10.79.0.15, startup-config r3.cli. Connect r1:e1-2 to r3:e1-1 and r3:e1-2 to r2:e1-1. Stop the reference first. Save/deploy and test client HTTP80 plus blocked8081. Destroy this topology before restoring the reference service. Startup files contain per-VM operator credentials; do not share them.\n')
for p in [home/'labs',d,*d.rglob('*')]:
 assert not p.is_symlink();os.chown(p,u.pw_uid,u.pw_gid);p.chmod(0o700 if p.is_dir() else 0o600)
print('Private native CLI startup templates prepared in /home/student/labs/ui')
