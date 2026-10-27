#!/usr/bin/python3
"""Provision ordinary native device access; preserve user profiles and work."""
import base64
import hashlib
import json
import pathlib
import subprocess
from workstation_content import INVENTORY, LEGACY_HASHES, LEGACY_MODEL_POLICY_SHA256, refresh_plan

STATE = pathlib.Path('/var/lib/seminar-lab')
NAME = 'clab-seminar-management'


def call(args, data=None):
    return subprocess.check_output(['docker', 'exec', '--user', 'agent',
                                    *(['-i'] if data is not None else []), NAME, *args], input=data)


volume = json.loads(subprocess.check_output(['docker', 'volume', 'inspect', 'seminar-management-home']))[0]
identity = {'name': volume['Name'], 'created': volume['CreatedAt']}
marker = STATE/'management-home-identity.json'
previous = json.loads(marker.read_text()) if marker.exists() else {}
same_home = all(previous.get(k) == v for k, v in identity.items())
files = {'workspace/inventory.md': INVENTORY.encode(),
         '.profile': b'export PATH=/opt/clients/bin:/usr/local/bin:/usr/bin:/bin\nexport GNMIC_CONFIG=/home/agent/.config/network/gnmic.yaml\nexport SNMPCONFPATH=/home/agent/.config/network\n'}
# All generated access paths are managed too: preserve custom SSH/client edits.
for folder, target in (('.ssh','.ssh'),('.lab','.config/network')):
    for p in (pathlib.Path('/home/agent')/folder).iterdir():
        if p.is_file() and not p.is_symlink():
            files[target+'/'+p.name] = p.read_bytes()
# Read/write only as the ordinary account. No user-controlled path is traversed by root.
snapshot_code = '''import base64,hashlib,json,pathlib,sys
h=pathlib.Path('/home/agent'); names=json.loads(sys.argv[1]);out={}
for name in names:
 p=h/name
 for q in (p,*list(p.parents)[:-1]):
  if q.is_symlink():raise SystemExit('Linked workstation path: '+name)
 if p.exists():
  if not p.is_file():raise SystemExit('Nonregular workstation file: '+name)
  out[name]=base64.b64encode(p.read_bytes()).decode()
# Old harness policy is not silently deleted or applied to the new workstation.
for name in ('AGENTS.md','.config/opencode/opencode.json','opencode.json'):
 p=h/name
 if p.is_file():
  text=p.read_text()
  if hashlib.sha256(p.read_bytes()).hexdigest()==sys.argv[2]:
   raise SystemExit('Legacy generated model permission policy preserved: '+name+'; archive/remove explicitly before update')
  if any(x in text for x in ('labctl','observer-only','observer credentials only','teaching.plugin','gate.plugin')):
   raise SystemExit('Legacy harness restriction preserved: '+name+'; archive/remove explicitly before update')
print(json.dumps(out))
'''
names = [*files, 'workspace/task.txt', '.workstation-prepared']
existing = {k: base64.b64decode(v) for k,v in json.loads(call(
    ['/usr/bin/python3','-I','-S','-c',snapshot_code,json.dumps(names),LEGACY_MODEL_POLICY_SHA256])).items()}
# Docker ENV supplies ordinary native-client configuration. Never overwrite a
# pristine skeleton or a user's custom shell profile merely to add convenience.
profile = existing.get('.profile')
known_profile = previous.get('managed',{}).get('.profile') or LEGACY_HASHES.get('.profile')
if profile is not None and hashlib.sha256(profile).hexdigest() != known_profile:
    if b'/home/agent/.lab' in profile:
        raise ValueError('Custom .profile preserved; update old native-client paths explicitly')
    files.pop('.profile')
managed = dict(previous.get('managed',{})) if same_home else {}
# Recognize the exact previous generated SSH alias config during v5 migration.
legacy_ssh = files['.ssh/config'].replace(b'HostName 10.79.0.12\n  User netops',b'HostName 10.79.0.12\n  User observer').replace(b'HostName 10.79.0.13\n  User netops',b'HostName 10.79.0.13\n  User observer')
managed.setdefault('.ssh/config',hashlib.sha256(legacy_ssh).hexdigest())
# Only VM-owned prior trust can establish legacy generated-file ownership.
prior_trust = STATE/'previous-device-trust.sha256'
if prior_trust.is_file():
    managed.setdefault('.ssh/known_hosts',prior_trust.read_text().strip())
writes, removals = refresh_plan(existing, managed, files)
# The content is transferred over stdin, never emitted in a command or report.
apply_code = '''import os,pathlib,sys,json,base64
h=pathlib.Path('/home/agent');data=json.load(sys.stdin)
for name in list(data['writes'])+data['remove']:
 p=h/name
 for q in (p,*list(p.parents)[:-1]):
  if q.is_symlink():raise SystemExit('Linked workstation path: '+name)
 if p.exists() and not p.is_file():raise SystemExit('Nonregular workstation path: '+name)
for name,value in data['writes'].items():
 p=h/name;p.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
 tmp=p.with_name(p.name+'.refresh')
 fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write(base64.b64decode(value))
 os.replace(tmp,p)
for name in data['remove']:(h/name).unlink()
for name in ('.ssh','.config/network','workspace'):(h/name).chmod(0o700)
'''
payload = json.dumps({'writes':{k:base64.b64encode(v).decode() for k,v in writes.items()},'remove':removals}).encode()
call(['/usr/bin/python3','-I','-S','-c',apply_code], payload)
identity['managed'] = {k:hashlib.sha256(v).hexdigest() for k,v in files.items()}
marker.write_text(json.dumps(identity));marker.chmod(0o600)
print(json.dumps({'management_home':'preserved' if same_home else 'fresh','access':'native network administration','agent':'stock OpenCode'}))
