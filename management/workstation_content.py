"""Ordinary workstation content and non-destructive managed-file updates."""
import hashlib

INVENTORY = """# Network inventory

This workstation has native management access to the following devices.

| Device | Management address | Platform | Data interfaces |
|---|---|---|---|
| client | 10.79.0.11 | Linux | eth1: 10.78.1.10/24 |
| r1 | 10.79.0.12 | Nokia SR Linux | ethernet-1/1: 10.78.1.254/24; ethernet-1/2: 10.78.0.1/30 |
| r2 | 10.79.0.13 | Nokia SR Linux | ethernet-1/1: 10.78.0.2/30; ethernet-1/2: 10.78.2.254/24 |
| server | 10.79.0.14 | Linux | eth1: 10.78.2.10/24 |

Application path: client — r1 — r2 — server. Client HTTP traffic goes to
10.78.2.10 TCP80; administrative TCP8081 is restricted from the client.
Management reachability is separate from application reachability.

SSH aliases: client, server, r1, r2. Router login is netops, with native network
configuration privileges over SSH/CLI, gNMI/TLS57400, NETCONF/SSH830 and HTTPS
JSON-RPC443. Device account/host administration is a separate role. Standard
clients are installed; you may also use normal shell and Python tools.

~/.config/network/device-access.json contains router access credentials;
~/.config/network/gnmic.yaml is the gNMI client configuration. TLS CA and SNMP
configuration are in the same directory. ~/.ssh/config and known_hosts pin SSH
identities. GNMIC_CONFIG and SNMPCONFPATH point to the client configuration.
Keep credential values out of reports and command transcripts.

Client/server SSH provides the netops account with ordinary Linux tools and
bounded privileged firewall/capture diagnostics through sudo net-observe.
HTTP, iperf3 TCP5201 and background UDP5202 traffic are independent services.
Timestamped received SNMP, gNMI and Syslog observations are in ~/observations.
SNMP traps are not configured. Observations can include earlier events.
"""

LEGACY_MODEL_POLICY_SHA256 = 'b2ff3ddf1401c9ebdfa814b003ffd4fb63fcb6d10d2b23543070e401f8706fcb'

LEGACY_HASHES = {'workspace/inventory.md': '697b8252d857d6f7e026b6c1d633ff7b72883a705ae183e696167da8dd1093ff', 'workspace/task.txt': '6cfe3a5e957468ec7d4e2c6761354bd4323e7fcdbc694b4d0755777e04d5f780', '.profile': 'd3d331346a3579302e11ae56596a045b9e792a1dcd12b8d1c5b5cb3fc70ed8cf', '.workstation-prepared': '2dd694ef30f6ef76bdac0a56eb384e37d0e349d75133bfae26b909601a066c7b'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def refresh_plan(existing, previous, generated):
    """Return managed writes/removals; refuse custom collisions before any write."""
    writes = {}
    removals = []
    managed = dict(LEGACY_HASHES)
    managed.update(previous)
    for name, data in generated.items():
        old = existing.get(name)
        if old is not None and old != data and digest(old) != managed.get(name):
            raise ValueError('Custom workstation file preserved; reconcile: '+name)
        if old != data:
            writes[name] = data
    for name in ('workspace/task.txt', '.workstation-prepared'):
        if name in existing:
            if digest(existing[name]) != managed.get(name):
                raise ValueError('Custom workstation file preserved; reconcile: '+name)
            removals.append(name)
    return writes, removals
