#!/opt/seminar-tools/bin/python
"""Operator-only native provisioning; generated credentials never enter source."""
import pathlib,json,secrets,subprocess,os,contextlib,io,logging
logging.disable(logging.CRITICAL)
from pygnmi.client import gNMIclient
from network_access import role_updates
STATE=pathlib.Path('/var/lib/seminar-lab');STATE.mkdir(mode=0o700,exist_ok=True)
secrets_file=STATE/'device-credentials.json'
if secrets_file.exists(): creds=json.loads(secrets_file.read_text())
else:
 creds={k:secrets.token_hex(24) for k in ['operator','observer','disabled','snmp']};secrets_file.write_text(json.dumps(creds));secrets_file.chmod(0o600)
if 'netops' not in creds:
 creds['netops']=secrets.token_hex(24);secrets_file.write_text(json.dumps(creds));secrets_file.chmod(0o600)
lab=pathlib.Path('/home/ubuntu/clab-seminar')
# For the first pilot only; final provisioner passes the actual lab directory.
if os.environ.get('LAB_DIRECTORY'):lab=pathlib.Path(os.environ['LAB_DIRECTORY'])
for node in ['r1','r2']:
 idx=int(node[-1]);host=f'10.79.0.{11+idx}'
 user='operator';pwd=creds['operator']
 try:
  with gNMIclient(target=(host,57400),username=user,password=pwd,path_root=str(lab/'.tls/ca/ca.pem'),gnmi_timeout=5) as check:check.capabilities()
 except Exception:
  user='admin';pwd='NokiaSrl1!'
 def entry(path,val):return (path,json.dumps(val) if isinstance(val,str) else val)
 updates=[]
 updates += [entry('/system/aaa/authorization/role[rolename=observer]',{'rolename':'observer','services':['cli','gnmi','netconf','json-rpc'],'superuser':False,'cli':{'load-global-plugins':False,'load-user-plugins':False,'allow-command-list':['^info(?: [A-Za-z0-9_*/. =:-]+)?$','^quit$','^exit$']},'netconf':{'allowed-operations':['get','get-config','get-data','get-schema','close-session']}})]
 updates += [entry('/system/configuration/role[name=observer]',{'name':'observer','rule':[{'path-reference':'/','action':'deny'},{'path-reference':'interface ethernet-1/1','action':'read'},{'path-reference':'interface ethernet-1/2','action':'read'},{'path-reference':'network-instance default','action':'read'},{'path-reference':'system name','action':'read'},{'path-reference':'system information','action':'read'},{'path-reference':'acl','action':'read'}]})]
 updates += [entry('/system/aaa/authentication/user[username=observer]',{'username':'observer','password':creds['observer'],'role':['observer'],'superuser':False,'ssh-key':[(STATE/'ssh/agent_ed25519.pub').read_text().strip()]}),entry('/system/aaa/authentication/user[username=operator]',{'username':'operator','password':creds['operator'],'superuser':True})]
 updates += role_updates((STATE/'ssh/agent_ed25519.pub').read_text().strip(),creds['netops'])
 # Replace vendor/default credentials. Native admin remains operator-private.
 updates += [entry('/system/aaa/authentication/admin-user/password',creds['disabled']),entry('/system/aaa/authentication/linuxadmin-user/password',creds['disabled'])]
 # Two data interfaces and their routing network instance.
 addresses=['10.78.1.254/24','10.78.0.1/30'] if idx==1 else ['10.78.0.2/30','10.78.2.254/24']
 for port,address in enumerate(addresses,1):
  updates.append(entry(f'/interface[name=ethernet-1/{port}]',{'name':f'ethernet-1/{port}','admin-state':'enable','subinterface':[{'index':0,'admin-state':'enable','ipv4':{'admin-state':'enable','address':[{'ip-prefix':address}]}}]}))
 updates.append(entry('/network-instance[name=default]',{'name':'default','type':'default','admin-state':'enable','interface':[{'name':'ethernet-1/1.0'},{'name':'ethernet-1/2.0'}]}))
 prefix='10.78.2.0/24' if idx==1 else '10.78.1.0/24';gateway='10.78.0.2' if idx==1 else '10.78.0.1'
 updates.append(entry('/network-instance[name=default]/next-hop-groups/group[name=transit]',{'name':'transit','nexthop':[{'index':1,'ip-address':gateway}]}))
 updates.append(entry('/network-instance[name=default]/static-routes/route[prefix='+prefix+']',{'prefix':prefix,'admin-state':'enable','next-hop-group':'transit'}))
 updates.append(entry('/system/logging/remote-server[host=10.79.0.1]',{'host':'10.79.0.1','network-instance':'mgmt','transport':'udp','remote-port':5514,'facility':[{'facility-name':'local6','priority':{'match-above':'informational'}}]}))
 updates.append(entry('/system/json-rpc-server/network-instance[name=mgmt]/http/admin-state','disable'))
 updates.append(entry('/system/grpc-server[name=mgmt]/services',['gnmi']))
 updates.append(entry('/system/snmp/access-group[name=lab-read]',{'name':'lab-read','security-level':'no-auth-no-priv','community-entry':[{'name':'lab-read','community':creds['snmp'],'prefix-list':['10.79.0.1/32','10.79.0.20/32']}]}))
 if node=='r1':
  updates.append(entry('/acl/acl-filter[name=client-policy][type=ipv4]',{'name':'client-policy','type':'ipv4','entry':[{'sequence-id':10,'match':{'ipv4':{'protocol':'tcp','destination-ip':{'prefix':'10.78.2.10/32'}},'transport':{'destination-port':{'operator':'eq','value':8081}}},'action':{'drop':{}}},{'sequence-id':100,'action':{'accept':{}}}]}))
  updates.append(entry('/acl/interface[interface-id=ethernet-1/1.0]',{'interface-id':'ethernet-1/1.0','interface-ref':{'interface':'ethernet-1/1','subinterface':0},'input':{'acl-filter':[{'name':'client-policy','type':'ipv4'}]}}))
 with gNMIclient(target=(host,57400),username=user,password=pwd,path_root=str(lab/'.tls/ca/ca.pem'),gnmi_timeout=20) as g:
  try:
   with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    result=g.set(update=updates,delete=['/system/snmp/access-group[name=SNMPv2-RO-Community]']+['/system/grpc-server[name='+x+']' for x in ['insecure-mgmt','eda-discovery','eda-mgmt','eda-insecure-mgmt']]+['/system/logging/remote-server[host=10.79.0.1]/subsystem'],encoding='json_ietf')
  except Exception as e:
   raise SystemExit('Native provisioning rejected ('+type(e).__name__+'); details suppressed because payloads contain credentials') from None
  print(json.dumps({'node':node,'configured_updates':len(updates),'timestamp':result.get('timestamp')}))
 # Persist without exposing secret configuration in console output.
 subprocess.run(['docker','exec',f'clab-seminar-{node}','sr_cli','-d','tools system configuration save'],check=True,stdout=subprocess.DEVNULL)

# Capture the actual committed startup configuration privately for a complete reset.
startup={node:json.loads((lab/node/'config/config.json').read_text()) for node in ['r1','r2']}
(STATE/'startup-configs.json').write_text(json.dumps(startup));(STATE/'startup-configs.json').chmod(0o600)
