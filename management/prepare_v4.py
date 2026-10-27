#!/usr/bin/python3
"""Prepare private per-VM state and generated lab SSH identities."""
from pathlib import Path
import subprocess,pwd,os,json,shutil,tempfile,uuid
assert os.geteuid()==0
state=Path('/var/lib/seminar-lab');state.mkdir(mode=0o700,exist_ok=True);state.chmod(0o700)
subprocess.run(['usermod','-aG','docker,clab_admins','student'],check=True)
agent=pwd.getpwnam('agent');student=pwd.getpwnam('student')
for home in ['/home/agent','/home/student']:
 p=Path(home);assert p.is_dir() and not p.is_symlink();p.chmod(0o700)
keys=state/'ssh';keys.mkdir(mode=0o700,exist_ok=True)
k=keys/'agent_ed25519'
if not k.exists():subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-f',str(k)],check=True)
for n in ['client','server']:
 d=keys/n;d.mkdir(mode=0o700,exist_ok=True)
 if not (d/'ssh_host_ed25519_key').exists():subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-f',str(d/'ssh_host_ed25519_key')],check=True)
 (d/'authorized_keys').write_text(k.with_suffix('.pub').read_text());(d/'authorized_keys').chmod(0o600)
# Replace the named .ssh entry itself; never follow any preexisting agent symlinks.
t=Path(tempfile.mkdtemp(dir=state,prefix='ssh-stage-'));shutil.copyfile(k,t/'id_ed25519');(t/'id_ed25519').chmod(0o600)
(t/'config').write_text('Host client\n  HostName 10.79.0.11\n  User netops\nHost server\n  HostName 10.79.0.14\n  User netops\nHost r1\n  HostName 10.79.0.12\n  User netops\nHost r2\n  HostName 10.79.0.13\n  User netops\nHost *\n  IdentityFile ~/.ssh/id_ed25519\n  IdentitiesOnly yes\n  StrictHostKeyChecking yes\n  UserKnownHostsFile ~/.ssh/known_hosts\n  ConnectTimeout 5\n  BatchMode yes\n  ForwardAgent no\n')
(t/'known_hosts').touch()
for p in [t,*t.iterdir()]:os.chown(p,agent.pw_uid,agent.pw_gid,follow_symlinks=False)
t.chmod(0o700)
old=Path('/home/agent/.ssh')
if os.path.lexists(old):old.rename(state/('previous-ssh-'+uuid.uuid4().hex))
t.rename(old)
print('Private state and SSH identities prepared')
