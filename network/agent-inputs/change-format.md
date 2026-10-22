# Exact native request for human approval

Create `proposal.json` with exactly `target` (r1 or r2), `protocol` (gnmi or
netconf), and `reason` (1–2000 characters supported by observations).

For gnmi create `change.json`: the standard protobuf JSON representation of
gNMI SetRequest. Supported fields: prefix, update, replace, delete. Paths use
`elem` entries with `name` and optional `key`; values use TypedValue
`jsonIetfVal` containing base64-encoded JSON. No origin, target, extensions or
shell commands. Prefix plus relative path is interpreted as a full native path.

For netconf create `change.xml`: a NETCONF `<config>` element, not an RPC.
Namespace for config/operation: `urn:ietf:params:xml:ns:netconf:base:1.0`.
Native model namespaces:

- interface: `urn:nokia.com:srlinux:chassis:interfaces`
- network-instance: `urn:nokia.com:srlinux:net-inst:network-instance`
- static-routes: `urn:nokia.com:srlinux:static-route:static-routes`

Both protocols permit only these configuration scopes:

- `/interface[name=ethernet-1/1 or ethernet-1/2]/admin-state`: enable or disable.
- `/network-instance[name=default]/static-routes/route[prefix=10.78.1.0/24 or 10.78.2.0/24]`:
  route entry update/delete, admin-state enable/disable and next-hop-group transit.

No parent replacement, AAA, management-interface, ACL or arbitrary RPC writes.
The validator checks scope and request safety, not whether the proposal solves
the incident. A valid but wrong change can be approved and fail service tests.
Each file is limited to 64KiB. Run `sudo /usr/local/sbin/labctl submit` and stop.
