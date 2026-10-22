#!/opt/seminar-tools/bin/python
import pathlib,subprocess,json,os,pwd
s=pathlib.Path('/var/lib/seminar-lab');c=json.loads((s/'device-credentials.json').read_text());d=pathlib.Path('/var/lib/seminar-observer');u=pwd.getpwnam('lab-observer');d.mkdir(mode=0o700,exist_ok=True)
(d/'ca.pem').write_bytes((s/'runtime/clab-seminar/.tls/ca/ca.pem').read_bytes())
(d/'gnmic.yaml').write_text('username: observer\npassword: '+c['observer']+'\nencoding: json_ietf\ntls-ca: '+str(d/'ca.pem')+'\n')
(d/'snmp.conf').write_text('defVersion 2c\ndefCommunity '+c['snmp']+'\nmibs :\n')
for p in [d,*d.iterdir()]:os.chown(p,u.pw_uid,u.pw_gid);p.chmod(0o700 if p==d else 0o600)
# Install executable outside the operator source tree; it contains no faults or credentials.
subprocess.run(['install','-m','0755','/opt/seminar-lab/management/collect.py','/usr/local/bin/seminar-collect'],check=True)
unit=pathlib.Path('/etc/systemd/system/seminar-collect.service')
unit.write_text('''[Unit]
Description=Native SNMP and gNMI lab observations
After=docker.service
[Service]
User=lab-observer
Group=lab-readers
UMask=0027
ExecStart=/usr/local/bin/seminar-collect
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/var/log/seminar-lab
ProtectHome=true
PrivateTmp=true
[Install]
WantedBy=multi-user.target
''')
subprocess.run(['systemctl','daemon-reload'],check=True);subprocess.run(['systemctl','enable','--now','seminar-collect'],check=True)
