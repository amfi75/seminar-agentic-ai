#!/opt/seminar-tools/bin/python
"""Publish native network credentials and pinned public trust into the agent home."""
import pathlib,json,os,pwd,subprocess,tempfile,shutil,uuid,hashlib
assert os.geteuid()==0
state=pathlib.Path('/var/lib/seminar-lab');lab=state/'runtime/clab-seminar';c=json.loads((state/'device-credentials.json').read_text());u=pwd.getpwnam('agent')
home=pathlib.Path('/home/agent');assert home.is_dir() and not home.is_symlink()
stage=pathlib.Path(tempfile.mkdtemp(dir=state,prefix='observer-stage-'))
shutil.copyfile(lab/'.tls/ca/ca.pem',stage/'ca.pem')
(stage/'device-access.json').write_text(json.dumps({'username':'netops','password':c['netops'],'targets':{'r1':'10.79.0.12','r2':'10.79.0.13'}}))
(stage/'gnmic.yaml').write_text('username: netops\npassword: '+c['netops']+'\nencoding: json_ietf\nport: 57400\ntls-ca: /home/agent/.config/network/ca.pem\n')
(stage/'snmp.conf').write_text('defVersion 2c\ndefCommunity '+c['snmp']+'\nmibs :\n')
known=[]
for node,ip in [('r1','10.79.0.12'),('r2','10.79.0.13')]:
 for key in ['ed25519','ecdsa','rsa']:
  public=subprocess.check_output(['docker','exec','clab-seminar-'+node,'cat','/etc/ssh/ssh_host_'+key+'_key.pub'],text=True).strip()
  known.append(ip+' '+public);known.append('['+ip+']:830 '+public)
for node,ip in [('client','10.79.0.11'),('server','10.79.0.14')]:known.append(ip+' '+(state/'ssh'/node/'ssh_host_ed25519_key.pub').read_text().strip())
# Root-owned prior trust establishes legacy managed provenance, never a
# user-editable copy from inside the management home.
prior=state/'operator-known-hosts'
if prior.is_file():
 previous=state/'previous-device-trust.sha256';previous.write_text(hashlib.sha256(prior.read_bytes()).hexdigest());previous.chmod(0o600)
(state/'operator-known-hosts').write_text('\n'.join(known)+'\n');(state/'operator-known-hosts').chmod(0o600)
(stage/'known_hosts').write_text('\n'.join(known)+'\n')
for p in [stage,*stage.iterdir()]:
 os.chown(p,u.pw_uid,u.pw_gid,follow_symlinks=False);p.chmod(0o700 if p==stage else 0o600)
old=home/'.lab'
if os.path.lexists(old):old.rename(state/('previous-observer-'+uuid.uuid4().hex))
stage.rename(old)
# The .ssh directory is agent-controlled: pin it, replace only its known_hosts name.
fd=os.open(home/'.ssh',os.O_DIRECTORY|os.O_NOFOLLOW|os.O_RDONLY)
try:
 tmp='known-'+uuid.uuid4().hex
 f=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600,dir_fd=fd);os.write(f,('\n'.join(known)+'\n').encode());os.fchown(f,u.pw_uid,u.pw_gid);os.close(f)
 os.rename(tmp,'known_hosts',src_dir_fd=fd,dst_dir_fd=fd)
finally:os.close(fd)
# Expose native clients with convenience configuration, not a replacement API.
profile=pathlib.Path('/etc/profile.d/seminar-lab.sh')
profile.write_text('export GNMIC_CONFIG=/home/agent/.config/network/gnmic.yaml\nexport SNMPCONFPATH=/home/agent/.config/network\nexport PATH=/opt/seminar-tools/bin:$PATH\n')
profile.chmod(0o644)
print('Native device credentials and verified public trust installed')
