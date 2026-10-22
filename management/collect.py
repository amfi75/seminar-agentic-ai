#!/opt/seminar-tools/bin/python
"""Small timestamping/file wrapper around native SNMP and gnmic clients."""
import pathlib,json,subprocess,time,sys,os,threading
CONFIG=pathlib.Path('/var/lib/seminar-observer')
LOG=pathlib.Path('/var/log/seminar-lab')
HOSTS={'r1':'10.79.0.12','r2':'10.79.0.13'}
def append(filename,value):
 with (LOG/filename).open('a') as f:f.write(json.dumps({'received_ns':time.time_ns(),'monotonic_ns':time.monotonic_ns(),**value},sort_keys=True)+'\n')
def snmp(node,host):
 env={**os.environ,'SNMPCONFPATH':str(CONFIG)}
 names=subprocess.run(['snmpwalk','-v2c','-On','-t','1','-r','0',host,'.1.3.6.1.2.1.31.1.1.1.1'],capture_output=True,text=True,env=env,timeout=10).stdout
 indices={line.split(' = ')[0].rsplit('.',1)[-1]:line.split('STRING: ',1)[-1].strip('"') for line in names.splitlines() if 'ethernet-1/1"' in line or 'ethernet-1/2"' in line or line.endswith(('ethernet-1/1','ethernet-1/2'))}
 if len(indices)<2:raise RuntimeError('Data-interface discovery incomplete; retry')
 append('snmp.jsonl',{'node':node,'kind':'inventory','interfaces':indices})
 while True:
  start=time.monotonic();oids=['.1.3.6.1.2.1.1.5.0']
  for index in indices:
   oids += [p+'.'+index for p in ['.1.3.6.1.2.1.2.2.1.7','.1.3.6.1.2.1.2.2.1.8','.1.3.6.1.2.1.31.1.1.1.6','.1.3.6.1.2.1.31.1.1.1.10']]
  r=subprocess.run(['snmpget','-v2c','-On','-t','1','-r','0',host,*oids],capture_output=True,text=True,env=env,timeout=10)
  append('snmp.jsonl',{'node':node,'period_s':1,'returncode':r.returncode,'values':r.stdout.strip().splitlines()})
  if r.returncode:raise RuntimeError('SNMP polling failed; rediscover interfaces')
  time.sleep(max(.01,1-(time.monotonic()-start)))
def gnmi(node,host):
 while True:
  args=['gnmic','--config',str(CONFIG/'gnmic.yaml'),'-a',host+':57400','--format','event','subscribe','--mode','stream','--stream-mode','sample','--sample-interval','1s','--path','/interface[name=ethernet-1/1]/oper-state','--path','/interface[name=ethernet-1/1]/admin-state','--path','/interface[name=ethernet-1/1]/statistics','--path','/interface[name=ethernet-1/2]/oper-state','--path','/interface[name=ethernet-1/2]/statistics']
  p=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,bufsize=1)
  # gnmic's event output can span lines. Accumulate complete JSON values.
  buf='';decoder=json.JSONDecoder()
  for line in p.stdout:
   buf+=line
   try:value,end=decoder.raw_decode(buf.lstrip())
   except json.JSONDecodeError:continue
   append('gnmi.jsonl',{'node':node,'period_s':1,'event':value});buf=buf.lstrip()[end:].strip()
  append('gnmi.jsonl',{'node':node,'connection_exit':p.wait()});time.sleep(2)
for node,host in HOSTS.items():
 for fn in [snmp,gnmi]:
  def supervise(fn=fn,node=node,host=host):
   while True:
    try:fn(node,host)
    except Exception as exc:append(fn.__name__+'.jsonl',{'node':node,'worker_error':type(exc).__name__,'retry_s':2})
    time.sleep(2)
  threading.Thread(target=supervise,daemon=True).start()
while True:time.sleep(60)
