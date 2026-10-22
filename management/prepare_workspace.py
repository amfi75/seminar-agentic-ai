#!/usr/bin/python3
"""Preserve prior trials and install neutral inputs without following agent links."""
import pathlib,os,pwd,subprocess,uuid,tempfile,shutil,json,hashlib,sys
assert os.geteuid()==0
state=pathlib.Path('/var/lib/seminar-lab');home=pathlib.Path('/home/agent')
u=pwd.getpwnam('agent');marker=state/'workspace-v4.json'
assert home.is_dir() and not home.is_symlink()
assert sys.argv[1:] in [[],['--fresh-trial']]
if not marker.exists() or sys.argv[1:]==['--fresh-trial']:
 for p in pathlib.Path('/proc').iterdir():
  try:
   if p.name.isdigit() and p.stat().st_uid==u.pw_uid:raise RuntimeError('Stop active agent sessions first')
  except (FileNotFoundError,ProcessLookupError):pass
 archive=state/('prior-agent-'+uuid.uuid4().hex);home.rename(archive)
 home.mkdir(mode=0o700);os.chown(home,u.pw_uid,u.pw_gid)
 for name in ['.profile','.bashrc']:
  shutil.copyfile(pathlib.Path('/etc/skel')/name,home/name);os.chown(home/name,u.pw_uid,u.pw_gid)
 history=json.loads(marker.read_text()).get('archives',[]) if marker.exists() else []
 history.append(str(archive))
 marker.write_text(json.dumps({'prior_profile_preserved':True,'archives':history}));marker.chmod(0o600)
workspace=home/'experiment'
try:workspace.mkdir(mode=0o700);os.chown(workspace,u.pw_uid,u.pw_gid)
except FileExistsError:pass
fd=os.open(workspace,os.O_DIRECTORY|os.O_NOFOLLOW|os.O_RDONLY)
try:
 assert os.fstat(fd).st_uid==u.pw_uid
 with tempfile.TemporaryDirectory(dir=state) as t:
  for src in pathlib.Path('/opt/seminar-lab/network/agent-inputs').iterdir():
   staged=pathlib.Path(t)/src.name;shutil.copyfile(src,staged);staged.chmod(0o444)
   os.replace(staged,src.name,dst_dir_fd=fd)
finally:os.close(fd)
print('Neutral inputs installed; prior profile preserved privately')
