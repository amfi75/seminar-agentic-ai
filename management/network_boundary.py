#!/usr/bin/python3
"""Operator-owned namespace egress rules, including endpoint SSH pivot paths."""
import subprocess,json,pathlib,ipaddress
# Docker forwards embedded DNS through this namespace to the VM uplink resolver.
resolvers=[]
for line in pathlib.Path("/run/systemd/resolve/resolv.conf").read_text().splitlines():
 if line.startswith("nameserver "):
  value=line.split()[1]
  try:
   if ipaddress.ip_address(value).version==4:resolvers.append(value)
  except ValueError:pass
nodes=['management','client','server']
def rule(pid,ipv6,*args):
 subprocess.run(['nsenter','-t',str(pid),'-n','ip6tables' if ipv6 else 'iptables','-w',*args],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
for node in nodes:
 info=json.loads(subprocess.check_output(['docker','inspect','clab-seminar-'+node]))[0];pid=info['State']['Pid'];assert pid>0
 for ipv6 in [False,True]:
  chain='SEMINAR_EGRESS'
  subprocess.run(['nsenter','-t',str(pid),'-n','ip6tables' if ipv6 else 'iptables','-w','-N',chain],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  rule(pid,ipv6,'-F',chain)
  rule(pid,ipv6,'-A',chain,'-m','conntrack','--ctstate','ESTABLISHED,RELATED','-j','ACCEPT')
  rule(pid,ipv6,'-A',chain,'-o','lo','-j','ACCEPT')
  if not ipv6:
   for host in ['10.79.0.11','10.79.0.12','10.79.0.13','10.79.0.14']:
    ports='22,443,830,57400' if host.endswith(('.12','.13')) else '22'
    rule(pid,False,'-A',chain,'-d',host,'-p','tcp','-m','multiport','--dports',ports,'-j','ACCEPT')
    rule(pid,False,'-A',chain,'-d',host,'-p','icmp','-j','ACCEPT')
    if host.endswith(('.12','.13')):rule(pid,False,'-A',chain,'-d',host,'-p','udp','--dport','161','-j','ACCEPT')
   if node!='management':
    # Do not replace the native router ACL with a host-side TCP8081 deny.
    rule(pid,False,'-A',chain,'-d','10.78.0.0/16','-j','ACCEPT')
   if node=='management':
    for resolver in resolvers:
     for protocol in ['udp','tcp']:rule(pid,False,'-A',chain,'-d',resolver,'-p',protocol,'--dport','53','-j','ACCEPT')
    for scope in ['10.0.0.0/8','172.16.0.0/12','192.168.0.0/16','169.254.0.0/16','100.64.0.0/10','224.0.0.0/3']:
     rule(pid,False,'-A',chain,'-d',scope,'-j','REJECT')
    rule(pid,False,'-A',chain,'-p','tcp','--dport','443','-j','ACCEPT')
  rule(pid,ipv6,'-A',chain,'-j','REJECT')
  check=subprocess.run(['nsenter','-t',str(pid),'-n','ip6tables' if ipv6 else 'iptables','-w','-C','OUTPUT','-j',chain],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  if check.returncode:rule(pid,ipv6,'-I','OUTPUT','1','-j',chain)
print('Management and SSH-accessible endpoints restricted to authorized network paths')
