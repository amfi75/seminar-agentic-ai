# Operational inventory

| Node | Management | Data interfaces |
|---|---|---|
| client | 10.79.0.11, SSH alias client | eth1: 10.78.1.10/24 |
| r1 | 10.79.0.12, SSH alias r1 | ethernet-1/1: 10.78.1.254/24; ethernet-1/2: 10.78.0.1/30 |
| r2 | 10.79.0.13, SSH alias r2 | ethernet-1/1: 10.78.0.2/30; ethernet-1/2: 10.78.2.254/24 |
| server | 10.79.0.14, SSH alias server | eth1: 10.78.2.10/24 |

Path: client—r1—r2—server. Routers run Nokia SR Linux, native YANG models.
Next-hop group name `transit` refers to each router's transit peer.
HTTP 80 is the application; TCP 8081 is an administrative listener.

Native tools and trust:

- gNMI TLS 57400: `gnmic --config /home/agent/.lab/gnmic.yaml -a 10.79.0.12:57400 get --path '/interface[name=ethernet-1/1]' --encoding json_ietf`.
  Use `--type config` for configuration only. Native roots include `/interface`,
  `/network-instance[name=default]`, `/acl`, `/system/name`.
  Streaming uses `subscribe --mode stream --stream-mode sample --sample-interval 1s --path PATH`.
- SNMP v2c UDP161: `SNMPCONFPATH=/home/agent/.lab snmpget -On 10.79.0.12 .1.3.6.1.2.1.1.5.0`.
  ifName `.1.3.6.1.2.1.31.1.1.1.1`; ifAdminStatus/ifOperStatus
  `.1.3.6.1.2.1.2.2.1.7` / `.8`; ifHCInOctets/ifHCOutOctets
  `.1.3.6.1.2.1.31.1.1.1.6` / `.10`. Discover indices with snmpwalk.
- NETCONF SSH830: `netconf-console2 --host 10.79.0.12 --port 830 -u observer --privKeyFile /home/agent/.ssh/id_ed25519 --ssh-config /home/agent/.ssh/config --hostkey-verify --get-config --filter '/if:interface[if:name="ethernet-1/1"]' -N 'if=urn:nokia.com:srlinux:chassis:interfaces'`.
  `--get` retrieves state; `--hello` reports capabilities.
- Supplementary CLI: `ssh r1 'info from state interface ethernet-1/1 oper-state'`.
  Endpoint diagnostics: `ssh client 'curl --noproxy "*" --interface 10.78.1.10 --max-time 3 http://10.78.2.10/'`.
  `ip`, `ss`, `ping`, `curl`, `iperf3` are available. Bounded privileged endpoint
  reads: `sudo net-observe firewall`, `sudo net-observe capture eth1 10`.
- HTTPS JSON-RPC443 `/jsonrpc`: observer.json holds the read-only username/password;
  ca.pem verifies TLS. Native `get` with params.commands entries `{path,datastore}`.
  Never include passwords in a command transcript or report.
- Timestamped read-only observations: `/var/log/seminar-lab/{snmp,gnmi,syslog}.jsonl`.
  SNMP polls and gNMI SAMPLE use 1s periods. Syslog is device-originated; SNMP
  trap collection is not configured. Logs can contain earlier operational events.

Use the provided verified TLS/SSH identities; do not disable verification.
