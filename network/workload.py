#!/usr/bin/python3
"""Ordinary root-operated curl/iperf workload, independent of the AI session."""
import json, pathlib, subprocess, time, threading, os
root=pathlib.Path('/var/log/workload');root.mkdir(mode=0o755,exist_ok=True)
def record(name,data):
 p=root/(name+'.jsonl')
 if p.exists() and p.stat().st_size>1024*1024:
  old=p.with_suffix('.jsonl.1');p.replace(old)
 with p.open('a') as f:f.write(json.dumps({'wall_ns':time.time_ns(),'monotonic_ns':time.monotonic_ns(),**data})+'\n')
 p.chmod(0o644)
def http():
 while True:
  if pathlib.Path('/run/workload-paused').exists():time.sleep(1);continue
  start=time.monotonic()
  r=subprocess.run(['curl','--noproxy','*','--interface','10.78.1.10','-fsS','--connect-timeout','2','--max-time','3','-w','%{time_total}','-o','/dev/null','http://10.78.2.10/'],capture_output=True,text=True)
  record('http',{'source':'10.78.1.10','destination':'10.78.2.10:80','success':r.returncode==0,'latency_s':float(r.stdout or 0),'exit_code':r.returncode})
  time.sleep(max(.1,2-(time.monotonic()-start)))
def flow():
 while True:
  if pathlib.Path('/run/workload-paused').exists():time.sleep(1);continue
  try:
   r=subprocess.run(['iperf3','-c','10.78.2.10','-B','10.78.1.10','-p','5202','-u','-b','64K','-l','512','-t','10','-J','--connect-timeout','2000'],capture_output=True,text=True,timeout=18)
   data=json.loads(r.stdout) if r.stdout else {}
   record('flow',{'source':'10.78.1.10','destination':'10.78.2.10:5202','exit_code':r.returncode,'measurement':data})
  except (subprocess.TimeoutExpired,json.JSONDecodeError) as e:record('flow',{'error_type':type(e).__name__})
  time.sleep(1)
threading.Thread(target=http,daemon=True).start()
flow()
