#!/usr/bin/python3
"""Expose the running graph to the human operator without exposing it to agent."""
import json
import os
import pathlib
import pwd
import subprocess

assert os.geteuid() == 0
state = pathlib.Path('/var/lib/seminar-lab')
runtime = state / 'runtime'
topology = runtime / 'topology.clab.yml'
if not topology.is_file():
    raise SystemExit('Reference topology is not ready')
for directory in [state, runtime, state / 'ssh']:
    assert directory.is_dir() and not directory.is_symlink()
    # Named human ACL only. Agent remains unable to traverse private state.
    access = 'rwx' if directory == runtime else '--x'
    subprocess.run(['setfacl', '-m', 'u:student:' + access, str(directory)], check=True)
subprocess.run(['setfacl', '-m', 'u:student:r--', str(topology)], check=True)

# Containerlab's Mermaid/DOT exporters expect a preexisting writable graph directory.
lab_runtime = runtime / 'clab-seminar'
assert lab_runtime.is_dir() and not lab_runtime.is_symlink()
graph = lab_runtime / 'graph'
if not graph.exists():
    graph.mkdir(mode=0o700)
assert graph.is_dir() and not graph.is_symlink()
subprocess.run(['setfacl', '-m', 'u:student:rwx', str(graph)], check=True)

# TopoViewer uses a presentation sidecar; device configuration is unchanged.
# Preserve existing user layout and icons. Never follow a preexisting symlink.
annotation = pathlib.Path(str(topology) + '.annotations.json')
defaults = {'nodeAnnotations': [
    {'id': 'management', 'icon': 'controller', 'position': {'x': 360, 'y': -180}},
    {'id': 'client', 'icon': 'client', 'position': {'x': 0, 'y': 0}},
    {'id': 'r1', 'icon': 'pe', 'position': {'x': 240, 'y': 0}},
    {'id': 'r2', 'icon': 'pe', 'position': {'x': 480, 'y': 0}},
    {'id': 'server', 'icon': 'server', 'position': {'x': 720, 'y': 0}},
]}
try:
    fd = os.open(annotation, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
except FileExistsError:
    # Merge only the newly added node, as the human user; preserve custom layout.
    code = """import os,sys,json,uuid
p=sys.argv[1];fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
with os.fdopen(fd) as f:d=json.load(f)
items=d.setdefault('nodeAnnotations',[])
if not any(x.get('id')=='management' for x in items):
 items.append({'id':'management','icon':'controller','position':{'x':360,'y':-180}})
 tmp=p+'.'+uuid.uuid4().hex
 fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'w') as f:json.dump(d,f,indent=2);f.write('\\n')
 os.replace(tmp,p)
"""
    subprocess.run(['runuser','-u','student','--','/usr/bin/python3','-I','-S','-c',code,str(annotation)],check=True)
else:
    student = pwd.getpwnam('student')
    with os.fdopen(fd, 'w') as stream:
        os.fchown(stream.fileno(), student.pw_uid, student.pw_gid)
        json.dump(defaults, stream, indent=2)
        stream.write('\n')
print('Human reference graph access and presentation defaults prepared')
