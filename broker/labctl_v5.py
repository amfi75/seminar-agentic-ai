#!/opt/seminar-tools/bin/python
"""Student-only experiment controls; devices are configured directly."""
import os,sys,json,pathlib,subprocess,fcntl,time
sys.path.insert(0,'/opt/seminar-lab/management')
def require(value,message):
 if not value:raise ValueError(message)
def loads(data):return json.loads(data)
from device_api import gnmi,STATE
ROOT=pathlib.Path('/opt/seminar-lab')
ENV={'PATH':'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin','HOME':'/root','LANG':'C.UTF-8'}
def command(args,check=True,timeout=30):
 r=subprocess.run(args,capture_output=True,text=True,env=ENV,timeout=timeout)
 if check and r.returncode:raise RuntimeError('Command failed: '+args[0]+'; '+r.stderr[:500])
 return r

def probe():
 out={}
 for node,port in [('client',80),('client',8081),('server',80),('server',8081)]:
  args=['docker','exec','clab-seminar-'+node,'curl','--noproxy','*','-fsS','--connect-timeout','2','--max-time','3']
  if node=='client':args+=['--interface','10.78.1.10']
  r=command(args+[f'http://10.78.2.10:{port}/'],check=False)
  out[node+'_'+str(port)]=r.returncode==0 and r.stdout=='seminar-service-ok\n'
 return out

def verify():
 p=probe();require(p=={'client_80':True,'client_8081':False,'server_80':True,'server_8081':True},'Data-path check failed: '+json.dumps(p));return p

def mutate(node,path,value):
 with gnmi(node) as g:return g.set(update=[(path,json.dumps(value))],encoding='json_ietf')
def impairment(params=None):
 args=['containerlab','tools','netem','set','-n','clab-seminar-r1','-i','e1-2']
 if params:args+=params
 r=command(args);return {'node':'r1','interface':'e1-2','direction':'egress r1 toward r2','parameters':params or [],'result':r.stdout}

def reset():
 impairment();command(['python3','/opt/seminar-lab/management/network_boundary.py']);command(['docker','exec','clab-seminar-client','rm','-f','/run/workload-paused'])
 baseline=loads((STATE/'startup-configs.json').read_bytes())
 for node in ['r1','r2']:
  with gnmi(node) as g:g.set(replace=[('/',baseline[node])],encoding='json_ietf')
 for attempt in range(30):
  try:result=verify();return result
  except Exception:
   if attempt==29:raise
   time.sleep(1)
def fault():
 mutate('r2','/network-instance[name=default]/static-routes/route[prefix=10.78.1.0/24]/admin-state','disable')
 for i in range(10):
  if not probe()['client_80']:return {'incident_ready':True}
  time.sleep(1)
 raise RuntimeError('Fault did not affect data path')
def audit(op,result):
 with (STATE/'audit.jsonl').open('a') as f:f.write(json.dumps({'at_ns':time.time_ns(),'caller':os.environ.get('SUDO_USER','root'),'operation':op,'result':result},sort_keys=True)+'\n')
 (STATE/'audit.jsonl').chmod(0o600)
def main():
 require(os.geteuid()==0,'Use authorized sudo command');STATE.mkdir(mode=0o700,exist_ok=True)
 operation=sys.argv[1] if len(sys.argv)>1 else '';caller=os.environ.get('SUDO_USER','root')
 require(caller in ['student','ubuntu','root'],'Student infrastructure operation required')
 with (STATE/'control.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  if operation=='workload':
   require(len(sys.argv)==3 and sys.argv[2] in ['pause','resume','status'],'Use workload pause/resume/status')
   action=sys.argv[2]
   if action!='status':command(['docker','exec','clab-seminar-client',*(['touch','/run/workload-paused'] if action=='pause' else ['rm','-f','/run/workload-paused'])])
   result={'paused':command(['docker','exec','clab-seminar-client','test','-f','/run/workload-paused'],check=False).returncode==0}
  else:
   require(len(sys.argv)==2,'No additional arguments accepted')
   if operation=='verify':result=verify()
   elif operation=='reset':result=reset()
   elif operation=='fault':result=fault()
   elif operation in ['delay','loss','rate']:
    result=impairment({'delay':['--delay','100ms','--jitter','10ms'],'loss':['--loss','10'],'rate':['--rate','128']}[operation])
   elif operation=='clear-impairment':result=impairment()
   else:raise ValueError('Unknown operation')
  print(json.dumps(result,indent=2))
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'error':str(e)[:1000],'type':type(e).__name__}),file=sys.stderr);sys.exit(1)
