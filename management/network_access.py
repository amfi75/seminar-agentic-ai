"""Native device role: network configuration without device-host administration."""
# Use native RBAC, not an RPC proxy or a scenario-specific change allowlist.
# Longest matching SR Linux configuration rule wins.

def role_updates(public_key, password):
    authorization = {
        'rolename': 'network-admin', 'services': ['cli', 'gnmi', 'netconf', 'json-rpc'],
        'superuser': False,
        'cli': {'load-global-plugins': False, 'load-user-plugins': False,
                'allow-command-list': [
                    r'^(?:enter|set|delete|insert|move|info|show|commit|discard|diff|quit|exit|ping|traceroute)(?: .*)?$',
                    r'^tools system configuration save$']},
        'netconf': {'allowed-operations': ['get', 'get-config', 'get-data', 'get-schema',
                   'edit-config', 'lock', 'unlock', 'validate', 'commit', 'discard-changes',
                   'close-session']}}
    # Deny all system host/security administration; normal network trees remain writable.
    # Name and descriptive contact/location data are ordinary operational metadata.
    rules = [{'path-reference': '/', 'action': 'write'},
             {'path-reference': 'system', 'action': 'read'}]
    rules += [{'path-reference': 'system '+name, 'action': 'deny'}
              for name in ('aaa', 'configuration', 'app-management', 'boot')]
    rules += [{'path-reference': 'system '+name, 'action': 'write'}
              for name in ('name', 'information')]
    return [
        ('/system/aaa/authorization/role[rolename=network-admin]', authorization),
        ('/system/configuration/role[name=network-admin]', {'name': 'network-admin', 'rule': rules}),
        ('/system/aaa/authentication/user[username=netops]',
         {'username': 'netops', 'password': password, 'role': ['network-admin'],
          'superuser': False, 'ssh-key': [public_key]})]
