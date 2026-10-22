#!/usr/bin/env bash
set -euo pipefail
getent group lab-readers >/dev/null || groupadd lab-readers
usermod -aG lab-readers agent
id lab-observer >/dev/null 2>&1 || useradd --system --home-dir /var/lib/seminar-observer --create-home --shell /usr/sbin/nologin lab-observer
usermod -aG lab-readers syslog
install -d -o root -g lab-readers -m 0750 /var/log/seminar-lab
setfacl -m u:syslog:rwx,u:lab-observer:rwx /var/log/seminar-lab
cat > /etc/rsyslog.d/40-seminar.conf <<'CONF'
module(load="imudp")
template(name="SeminarJSON" type="string" string="{\"received\":\"%timegenerated:::date-rfc3339%\",\"device_time\":\"%timereported:::date-rfc3339%\",\"source\":\"%fromhost-ip%\",\"host\":\"%hostname:::json%\",\"message\":\"%msg:::json%\"}\n")
ruleset(name="seminar") {
 if ($fromhost-ip == "10.79.0.12" or $fromhost-ip == "10.79.0.13") then {
  action(type="omfile" file="/var/log/seminar-lab/syslog.jsonl" template="SeminarJSON" fileOwner="syslog" fileGroup="lab-readers" fileCreateMode="0640")
 }
 stop
}
input(type="imudp" address="10.79.0.1" port="5514" ruleset="seminar")
CONF
rsyslogd -N1 >/dev/null
systemctl restart rsyslog
cat > /etc/logrotate.d/seminar-lab <<'CONF'
/var/log/seminar-lab/*.jsonl {
 size 5M
 rotate 3
 copytruncate
 missingok
 notifempty
 su root root
 create 0640 lab-observer lab-readers
}
CONF
cat > /etc/systemd/system/seminar-logrotate.service <<'UNIT'
[Unit]
Description=Bound seminar observation logs
[Service]
Type=oneshot
ExecStart=/usr/sbin/logrotate --state /var/lib/seminar-lab/logrotate.status /etc/logrotate.d/seminar-lab
UNIT
cat > /etc/systemd/system/seminar-logrotate.timer <<'UNIT'
[Unit]
Description=Check bounded seminar log retention each minute
[Timer]
OnBootSec=60
OnUnitActiveSec=60
[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload
systemctl enable --now seminar-logrotate.timer
