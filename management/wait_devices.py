#!/opt/seminar-tools/bin/python
"""Wait for native management readiness without changing device configuration."""
import time
from device_api import gnmi
for attempt in range(45):
    try:
        for node in ('r1','r2'):
            with gnmi(node) as client:client.capabilities()
        break
    except Exception:
        if attempt==44:
            raise SystemExit('Native device management unavailable; use explicit Recover devices if needed') from None
        time.sleep(2)
print('Native device management ready; no baseline reset performed')
