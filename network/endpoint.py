#!/usr/bin/env python3
"""Linux endpoint: ordinary unprivileged SSH diagnostics and actual listeners."""
import os,subprocess,threading,http.server,pathlib,time,socket
subprocess.run(['ssh-keygen','-A'],check=True)
keys=pathlib.Path('/run/lab-keys/authorized_keys').read_text()
ssh=pathlib.Path('/home/netops/.ssh');ssh.mkdir(mode=0o700,exist_ok=True)
(ssh/'authorized_keys').write_text(keys);(ssh/'authorized_keys').chmod(0o600)
subprocess.run(['chown','-R','netops:netops',str(ssh)],check=True)
ip=os.environ['MGMT_IP']
pathlib.Path('/etc/ssh/sshd_config').write_text(f'''ListenAddress {ip}
HostKey /run/lab-keys/ssh_host_ed25519_key
PermitRootLogin no
PasswordAuthentication no
PermitEmptyPasswords no
KbdInteractiveAuthentication no
AllowUsers netops
AllowTcpForwarding no
AllowStreamLocalForwarding no
AllowAgentForwarding no
X11Forwarding no
PermitTunnel no
Subsystem sftp internal-sftp
''')
def services():
 if not os.environ.get('SERVICE_IP'): return
 for attempt in range(100):
  probe=socket.socket()
  try: probe.bind((os.environ['SERVICE_IP'],0));probe.close();break
  except OSError: probe.close();time.sleep(.2)
 else: raise RuntimeError('Data address was not configured')
 class Handler(http.server.BaseHTTPRequestHandler):
  def do_GET(self):
   self.send_response(200);self.end_headers();self.wfile.write(b'seminar-service-ok\n')
  def log_message(self,*args):pass
 for port in [80,8081]:
  server=http.server.ThreadingHTTPServer((os.environ['SERVICE_IP'],port),Handler)
  threading.Thread(target=server.serve_forever,daemon=True).start()
 subprocess.Popen(['iperf3','-s','-B',os.environ['SERVICE_IP']])
 subprocess.Popen(['iperf3','-s','-p','5202','-B',os.environ['SERVICE_IP']])
def workload():
 if os.environ.get('WORKLOAD')!='true':return
 while True:
  try:
   if '10.78.1.10' in subprocess.check_output(['ip','-4','address','show','eth1'],text=True):break
  except subprocess.CalledProcessError:pass
  time.sleep(.2)
 subprocess.Popen(['python3','/usr/local/sbin/workload'])
threading.Thread(target=services,daemon=True).start()
threading.Thread(target=workload,daemon=True).start()
raise SystemExit(subprocess.call(['/usr/sbin/sshd','-D','-e']))
