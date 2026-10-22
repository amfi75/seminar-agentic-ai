#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -eq 0 ]] || exit 1
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq acl snmp snmpd rsyslog iperf3 python3-venv python3-lxml python3-ncclient openssl iproute2 jq iputils-ping tcpdump linux-modules-extra-$(uname -r)
modprobe sch_netem
python3 /opt/seminar-lab/network/install-tools.py containerlab gnmic opencode
python3 -m venv /opt/seminar-tools
/opt/seminar-tools/bin/pip -q install -r /opt/seminar-lab/network/python-requirements.txt
/opt/seminar-tools/bin/pip freeze > /var/tmp/seminar-python-versions.txt
containerlab version
gnmic version

