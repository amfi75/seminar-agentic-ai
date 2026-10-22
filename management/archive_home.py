#!/usr/bin/python3
"""Private exact profile preservation before an explicit fresh trial."""
import pathlib,tarfile,hashlib,json,sys,os
root=pathlib.Path(sys.argv[1]);archive=pathlib.Path(sys.argv[2]);assert not archive.exists()
inventory={}
with tarfile.open(archive,'w:gz',dereference=False) as t:
 for p in sorted(root.rglob('*')):
  rel=str(p.relative_to(root));t.add(p,arcname=rel,recursive=False)
  if p.is_file() and not p.is_symlink():inventory[rel]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
archive.chmod(0o600)
seen={}
with tarfile.open(archive,'r|gz') as t:
 for m in t:
  if m.isfile():
   b=t.extractfile(m).read();seen[m.name]={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
assert seen==inventory,'Profile archive verification failed; original retained'
p=archive.with_suffix('.verified.json');p.write_text(json.dumps({'verified':True,'files':len(seen),'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()},indent=2));p.chmod(0o600)
