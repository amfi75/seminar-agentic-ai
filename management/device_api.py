"""Pinned native device clients used by the human-authorized executor."""
import json,pathlib,logging,contextlib
from pygnmi.client import gNMIclient
from pygnmi.spec.v080 import gnmi_pb2,gnmi_pb2_grpc
from google.protobuf.json_format import ParseDict,MessageToDict
from ncclient import manager
import grpc
logging.disable(logging.CRITICAL)
STATE=pathlib.Path('/var/lib/seminar-lab')
LAB=STATE/'runtime/clab-seminar'
HOSTS={'r1':'10.79.0.12','r2':'10.79.0.13'}
def credentials():return json.loads((STATE/'device-credentials.json').read_text())
@contextlib.contextmanager
def gnmi(node,operator=True):
 c=credentials();user='operator' if operator else 'observer'
 with gNMIclient(target=(HOSTS[node],57400),username=user,password=c[user],path_root=str(LAB/'.tls/ca/ca.pem'),gnmi_timeout=15) as g:yield g

def configuration():
 out={}
 for node in HOSTS:
  with gnmi(node) as g:
   response=g.get(path=['/interface[name=ethernet-1/1]','/interface[name=ethernet-1/2]','/network-instance[name=default]','/acl/acl-filter[name=client-policy][type=ipv4]'] if node=='r1' else ['/interface[name=ethernet-1/1]','/interface[name=ethernet-1/2]','/network-instance[name=default]'],datatype='config',encoding='json_ietf')
   out[node]=sorted([{'path':u['path'],'value':u['val']} for n in response.get('notification',[]) for u in n.get('update',[])],key=lambda u:u['path'])
 return out

def native_apply(node,protocol,payload):
 c=credentials()
 if protocol=='gnmi':
  request=ParseDict(payload,gnmi_pb2.SetRequest(),ignore_unknown_fields=False)
  ca=(LAB/'.tls/ca/ca.pem').read_bytes()
  with grpc.secure_channel(HOSTS[node]+':57400',grpc.ssl_channel_credentials(root_certificates=ca)) as channel:
   reply=gnmi_pb2_grpc.gNMIStub(channel).Set(request,metadata=[('username','operator'),('password',c['operator'])],timeout=15)
  return {'request':MessageToDict(request,preserving_proto_field_name=False),'reply':MessageToDict(reply,preserving_proto_field_name=False)}
 # Native NETCONF over SSH, with a pinned host key obtained from the device filesystem.
 import paramiko
 keys=paramiko.HostKeys();keys.load(str(STATE/'operator-known-hosts'))
 def verify(unknown_host,fp):
  return any(k.get_fingerprint().hex().lower()==fp.replace(':','').lower() for k in keys.lookup('['+HOSTS[node]+']:830').values())
 with manager.connect(host=HOSTS[node],port=830,username='operator',password=c['operator'],allow_agent=False,look_for_keys=False,hostkey_verify=True,unknown_host_cb=verify,timeout=15) as n:
  assert any(':candidate:' in x for x in n.server_capabilities),'Candidate datastore unavailable'
  n.lock(target='candidate')
  edited=False
  try:
   # Do not overwrite a different operator's preexisting uncommitted candidate.
   from lxml import etree
   def canonical_config(r):
    el=r.data_ele
    return etree.tostring(el,method='c14n')
   if canonical_config(n.get_config(source='running'))!=canonical_config(n.get_config(source='candidate')):raise RuntimeError('Foreign pending NETCONF candidate')
   reply=n.edit_config(target='candidate',config=payload,default_operation='merge',test_option='test-then-set',error_option='rollback-on-error');edited=True
   validated=n.validate(source='candidate');committed=n.commit()
   return {'request':payload,'edit_reply':reply.xml,'validate_reply':validated.xml,'commit_reply':committed.xml}
  except Exception:
   if edited:n.discard_changes()
   raise
  finally:n.unlock(target='candidate')


def flattened(snapshot):
 import re
 out={}
 def walk(node,path,value):
  if isinstance(value,dict):
   for k,v in value.items():walk(node,path+'/'+k.split(':')[-1],v)
  elif isinstance(value,list):
   listname=path.rsplit('/',1)[-1]
   keys={'interface':['name'],'subinterface':['index'],'route':['prefix'],'group':['name'],'nexthop':['index'],'acl-filter':['name','type'],'entry':['sequence-id']}.get(listname)
   for i,v in enumerate(value):
    clean={k.split(':')[-1]:x for k,x in v.items()} if isinstance(v,dict) else {}
    suffix=''.join('['+k+'='+str(clean[k])+']' for k in keys) if keys and all(k in clean for k in keys) else '['+str(i)+']'
    walk(node,path+suffix,v)
  else:out[node+path]=value
 for node,updates in snapshot.items():
  for u in updates:
   path=re.sub(r'(?<=/)[A-Za-z_][A-Za-z0-9_-]*:','','/'+u['path'].lstrip('/'))
   walk(node,path,u['value'])
 return out

def unexpected_drift(before,after,target,writes):
 b,a=flattened(before),flattened(after);allowed=[target+w['path'] for w in writes]
 return sorted(p for p in set(b)|set(a) if b.get(p)!=a.get(p) and not any(p==scope or p.startswith(scope+'/') for scope in allowed))
