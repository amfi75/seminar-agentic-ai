#!/opt/seminar-tools/bin/python
"""Exact human approval for bounded native device changes; no answer oracle."""
import os,sys,json,pathlib,subprocess,hashlib,fcntl,time,uuid,base64,pwd
sys.path.insert(0,'/opt/seminar-lab/management')
from native_payload import validate,loads,require
from device_api import configuration,native_apply,gnmi,STATE,unexpected_drift
ROOT=pathlib.Path('/opt/seminar-lab')
ENV={'PATH':'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin','HOME':'/root','LANG':'C.UTF-8'}
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()
def command(args,check=True,timeout=30):
 r=subprocess.run(args,capture_output=True,text=True,env=ENV,timeout=timeout)
 if check and r.returncode:raise RuntimeError('Command failed: '+args[0]+'; '+r.stderr[:500])
 return r

def epoch(phase=None):
 p=STATE/'epoch.json'
 if phase is not None or not p.exists():p.write_text(json.dumps({'epoch':uuid.uuid4().hex,'phase':phase or 'initial'}));p.chmod(0o600)
 return json.loads(p.read_text())
READ_SOURCE = """import os,sys,stat
root='/home/agent/workspace'
parts=sys.argv[1].split('/')
fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
for part in parts[:-1]:
 new=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=new
f=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd);os.close(fd)
assert stat.S_ISREG(os.fstat(f).st_mode)
b=os.read(f,65537);os.close(f)
assert len(b)<=65536
sys.stdout.buffer.write(b)
"""
def container_bytes(path,expected_id=None):
 base='/home/agent/workspace/'
 require(isinstance(path,str) and path.startswith(base),'Source must be inside management workspace')
 relative=path[len(base):];parts=relative.split('/')
 require(all(p not in ['', '.', '..'] for p in parts) and len(path)<1024,'Invalid workspace path')
 details=loads(command(['docker','inspect','clab-seminar-management']).stdout.encode())[0]
 identity=details['Id']
 require(expected_id is None or identity==expected_id,'Management container changed; import again')
 require(details['Config']['User']=='agent' and not details['HostConfig']['Privileged'],'Untrusted management identity')
 require(details['Config']['Labels'].get('containerlab')=='seminar','Wrong lab identity')
 r=subprocess.run(['docker','exec','--user','agent',identity,'/usr/bin/python3','-I','-S','-c',READ_SOURCE,relative],capture_output=True,env=ENV,timeout=30)
 require(r.returncode==0,'Source read refused: missing, symlink, nonregular or oversized file')
 raw=r.stdout;require(len(raw)<=65536,'Input exceeds64KiB')
 return raw,identity

def submission(meta,origin):
 require(set(meta)=={'target','protocol','reason'} and meta['target'] in ['r1','r2'] and meta['protocol'] in ['gnmi','netconf'],'Unknown target/protocol')
 require(isinstance(meta['reason'],str) and 1<=len(meta['reason'])<=2000,'Reason length1..2000')
 raw,identity=container_bytes(origin['path'],origin.get('container_id'))
 payload,writes=validate(meta['protocol'],raw)
 return {'metadata':meta,'metadata_sha256':hashlib.sha256(canonical(meta)).hexdigest(),'payload_sha256':hashlib.sha256(raw).hexdigest(),'native_payload':payload,'writes':writes,'origin':{'path':origin['path'],'container_id':identity}}

def import_candidate(target,protocol,path,reason):
 s=submission({'target':target,'protocol':protocol,'reason':reason},{'path':path})
 s['configuration']=configuration();s['epoch']=epoch()['epoch'];s['created_ns']=time.time_ns()
 identity=hashlib.sha256(canonical(s)).hexdigest();d=STATE/'candidates';d.mkdir(mode=0o700,exist_ok=True);p=d/(identity+'.json');p.write_bytes(canonical(s));p.chmod(0o600)
 result={'candidate':identity,'applied':False,'target':target,'protocol':protocol,'source':s['origin'],'writes':s['writes'],'message':'Imported only; separate human review and approval required'}
 audit('import',result);return result
def candidate(identity):
 require(len(identity)==64 and all(c in '0123456789abcdef' for c in identity),'Invalid candidate ID')
 raw=(STATE/'candidates'/(identity+'.json')).read_bytes();require(hashlib.sha256(raw).hexdigest()==identity,'Candidate snapshot tampered');return loads(raw)
def show(identity):
 s=candidate(identity);return {'candidate':identity,'metadata':s['metadata'],'native_payload':s['native_payload'],'effective_writes':s['writes'],'prior_configuration':s['configuration'],'source':s['origin'],'applied':False}
def approve(identity):
 s=candidate(identity);current=submission(s['metadata'],s['origin'])
 require(current['metadata_sha256']==s['metadata_sha256'] and current['payload_sha256']==s['payload_sha256'],'Submitted source changed; submit again')
 require(epoch()['epoch']==s['epoch'],'Stale/replayed candidate')
 before=configuration();require(before==s['configuration'],'Device configuration drift; submit again')
 validate(s['metadata']['protocol'],canonical(s['native_payload']) if s['metadata']['protocol']=='gnmi' else s['native_payload'].encode())
 epoch('applying') # consume before external writes, including partial-failure paths
 try:
  reply=native_apply(s['metadata']['target'],s['metadata']['protocol'],s['native_payload'])
  after=configuration()
  require(not unexpected_drift(before,after,s['metadata']['target'],s['writes']),'Unexpected concurrent configuration changes; recovery required')
 except Exception as e:
  result={'candidate':identity,'applied':False,'requires_recovery':True,'error_type':type(e).__name__,'observed_configuration':configuration()};audit('apply-failed',result);return result
 result={'candidate':identity,'applied':True,'protocol':s['metadata']['protocol'],'target':s['metadata']['target'],'native_exchange':reply,'readback':after,'correctness':'not determined; run independent verification'}
 audit('approve',result);return result

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
 epoch('resetting');impairment();command(['python3','/opt/seminar-lab/management/network_boundary.py']);command(['docker','exec','clab-seminar-client','rm','-f','/run/workload-paused'])
 baseline=loads((STATE/'startup-configs.json').read_bytes())
 for node in ['r1','r2']:
  with gnmi(node) as g:g.set(replace=[('/',baseline[node])],encoding='json_ietf')
 for attempt in range(30):
  try:result=verify();epoch('baseline');return result
  except Exception:
   if attempt==29:raise
   time.sleep(1)
def fault():
 epoch('configuration-incident');mutate('r2','/network-instance[name=default]/static-routes/route[prefix=10.78.1.0/24]/admin-state','disable')
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
 if pathlib.Path(sys.argv[0]).name=='labctl':raise ValueError('Use human lab-admin import; no agent submission endpoint')
 else:require(caller in ['student','ubuntu','root'],'Human operation required')
 with (STATE/'control.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  if operation=='import':
   require(len(sys.argv)==6,'Use import TARGET PROTOCOL /home/agent/workspace/FILE REASON');result=import_candidate(*sys.argv[2:])
  elif operation=='workload':
   require(len(sys.argv)==3 and sys.argv[2] in ['pause','resume','status'],'Use workload pause/resume/status')
   action=sys.argv[2]
   if action!='status':command(['docker','exec','clab-seminar-client',*(['touch','/run/workload-paused'] if action=='pause' else ['rm','-f','/run/workload-paused'])])
   result={'paused':command(['docker','exec','clab-seminar-client','test','-f','/run/workload-paused'],check=False).returncode==0}
  elif operation in ['show','approve']:
   require(len(sys.argv)==3,'Provide candidate ID');result=show(sys.argv[2]) if operation=='show' else approve(sys.argv[2])
  else:
   require(len(sys.argv)==2,'No additional arguments accepted')
   if operation=='verify':result=verify()
   elif operation=='reset':result=reset()
   elif operation=='fault':result=fault()
   elif operation in ['delay','loss','rate']:
    epoch('performance-incident');result=impairment({'delay':['--delay','100ms','--jitter','10ms'],'loss':['--loss','10'],'rate':['--rate','128']}[operation])
   elif operation=='clear-impairment':epoch('cleared');result=impairment()
   else:raise ValueError('Unknown operation')
  print(json.dumps(result,indent=2))
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'error':str(e)[:1000],'type':type(e).__name__}),file=sys.stderr);sys.exit(1)
