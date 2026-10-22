"""Validate native management requests by their effective bounded write set."""
import base64,json,re
from defusedxml import ElementTree as ET
NC='urn:ietf:params:xml:ns:netconf:base:1.0'
IF='urn:nokia.com:srlinux:chassis:interfaces'
NI='urn:nokia.com:srlinux:net-inst:network-instance'
ST='urn:nokia.com:srlinux:static-route:static-routes'
class Rejected(ValueError):pass
def require(ok,message):
 if not ok:raise Rejected(message)
def loads(raw):
 def unique(pairs):
  out={}
  for k,v in pairs:
   require(k not in out,'Duplicate JSON key');out[k]=v
  return out
 return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda v:(_ for _ in ()).throw(Rejected('Nonfinite JSON')))
def path_elements(path):
 require(isinstance(path,dict) and set(path)<= {'elem'},'Only native elem paths without origin/target supported')
 out=[]
 for e in path.get('elem',[]):
  require(isinstance(e,dict) and set(e)<= {'name','key'} and isinstance(e.get('name'),str),'Invalid path element')
  name=e['name'];require(re.fullmatch('[a-z][a-z0-9-]*',name) is not None,'Unqualified native element required')
  keys=e.get('key',{});require(isinstance(keys,dict) and all(isinstance(k,str) and isinstance(v,str) for k,v in keys.items()),'Invalid key')
  out.append((name,keys))
 return out
def allowed(path,operation,value=None):
 # Native YANG leaves only; parent replacement cannot remove protected siblings.
 if len(path)==2 and path[0][0]=='interface' and path[0][1] in [{'name':'ethernet-1/1'},{'name':'ethernet-1/2'}] and path[1]==('admin-state',{}):
  require(operation!='delete' and value in ['enable','disable'],'Interface admin-state value');return
 require(len(path) in [3,4] and path[0]==('network-instance',{'name':'default'}) and path[1]==('static-routes',{}),'Outside permitted native configuration paths')
 require(path[2][0]=='route' and set(path[2][1])=={'prefix'} and path[2][1]['prefix'] in ['10.78.1.0/24','10.78.2.0/24'],'Route outside inventory')
 if len(path)==4:
  require(operation!='delete','Leaf deletion unsupported')
  if path[3]==('admin-state',{}):require(value in ['enable','disable'],'Route admin-state value')
  elif path[3]==('next-hop-group',{}):require(value=='transit','Next-hop group outside inventory')
  else:raise Rejected('Unsupported route leaf')
 else:
  require(operation!='replace','Route parent replacement unsupported')
  if operation=='delete':return
  require(isinstance(value,dict) and set(value)<= {'prefix','admin-state','next-hop-group'} and value.get('prefix')==path[2][1]['prefix'],'Invalid route entry')
  require(value.get('admin-state','enable') in ['enable','disable'] and value.get('next-hop-group')=='transit','Invalid route values')
def describe(path):return '/'+ '/'.join(n+''.join('['+k+'='+v+']' for k,v in sorted(keys.items())) for n,keys in path)
def gnmi(raw):
 request=loads(raw);require(isinstance(request,dict) and set(request)<= {'prefix','update','replace','delete'},'Unsupported SetRequest field')
 prefix=path_elements(request.get('prefix',{}));writes=[]
 for op in ['update','replace','delete']:
  entries=request.get(op,[]);require(isinstance(entries,list),'Expected operation list')
  for item in entries:
   if op=='delete':path=prefix+path_elements(item);value=None
   else:
    require(isinstance(item,dict) and set(item)=={'path','val'},'Invalid native Update')
    path=prefix+path_elements(item['path']);val=item['val'];require(isinstance(val,dict) and len(val)==1,'Invalid TypedValue')
    if 'jsonIetfVal' in val:
     value=loads(base64.b64decode(val['jsonIetfVal'],validate=True))
    elif 'stringVal' in val: value=val['stringVal'];require(isinstance(value,str),'Invalid stringVal')
    else:raise Rejected('Use JSON_IETF or string TypedValue')
   allowed(path,op,value);writes.append({'operation':op,'path':describe(path),'value':value})
 require(1<=len(writes)<=8,'Expected 1..8 bounded writes')
 paths=[w['path'] for w in writes];require(len(paths)==len(set(paths)),'Duplicate writes')
 for p in paths:
  require(not any(q!=p and q.startswith(p+'/') for q in paths),'Overlapping parent and child writes')
 return request,writes

def netconf(raw):
 require(len(raw)<=65536,'Payload too large')
 root=ET.fromstring(raw,forbid_dtd=True,forbid_entities=True,forbid_external=True);require(root.tag=='{'+NC+'}config' and not root.attrib,'Expected native NETCONF config')
 writes=[]
 def children(e,allowed_tags):
  require(all(c.tag in allowed_tags for c in e),'Unsupported XML element or namespace')
  require(not (e.text or '').strip(),'Mixed XML content unsupported')
  tags=[x.tag for x in e];require(len(tags)==len(set(tags)),'Duplicate XML element')
  for c in e:require(not (c.tail or '').strip(),'Mixed XML content unsupported')
 def leaf(e):require(not e.attrib and not list(e) and e.text is not None,'Invalid XML leaf');return e.text
 def attrs(e):
  require(set(e.attrib)<= {'{'+NC+'}operation'},'Unsupported XML attribute')
  op=e.attrib.get('{'+NC+'}operation','merge');require(op in ['merge','create','delete','remove'],'Parent replace/unsupported operation rejected');return op
 for parent in root:
  op=attrs(parent)
  if parent.tag=='{'+IF+'}interface':
   require(op=='merge','Interface parent operation must merge');children(parent,{'{'+IF+'}name','{'+IF+'}admin-state'})
   name=parent.find('{'+IF+'}name');state=parent.find('{'+IF+'}admin-state');require(name is not None and state is not None,'Expected interface name and admin-state')
   p=[('interface',{'name':leaf(name)}),('admin-state',{})];v=leaf(state);allowed(p,'update',v);writes.append({'operation':'update','path':describe(p),'value':v})
  elif parent.tag=='{'+NI+'}network-instance':
   require(op=='merge','Network-instance parent must merge');children(parent,{'{'+NI+'}name','{'+ST+'}static-routes'})
   name=parent.find('{'+NI+'}name');routes=parent.find('{'+ST+'}static-routes');require(name is not None and routes is not None and not routes.attrib,'Expected network-instance and routes')
   require(len(routes)>=1 and all(x.tag=='{'+ST+'}route' for x in routes),'Expected native route entries')
   for route in routes:
    rop=attrs(route);children(route,{'{'+ST+'}prefix','{'+ST+'}admin-state','{'+ST+'}next-hop-group'})
    values={c.tag.split('}')[1]:leaf(c) for c in route};require('prefix' in values,'Missing route prefix')
    p=[('network-instance',{'name':leaf(name)}),('static-routes',{}),('route',{'prefix':values['prefix']})]
    action='delete' if rop in ['delete','remove'] else 'update'
    require(action!='delete' or set(values)=={'prefix'},'Delete contains value changes');allowed(p,action,None if action=='delete' else values)
    writes.append({'operation':action,'path':describe(p),'value':None if action=='delete' else values})
  else:raise Rejected('Unsupported native configuration subtree')
 require(1<=len(writes)<=8,'Expected 1..8 changes');require(len({w['path'] for w in writes})==len(writes),'Duplicate writes')
 return raw.decode() if isinstance(raw,bytes) else raw,writes

def validate(protocol,raw):
 require(len(raw)<=65536,'Payload too large')
 return gnmi(raw) if protocol=='gnmi' else netconf(raw) if protocol=='netconf' else (_ for _ in ()).throw(Rejected('Unsupported protocol'))
