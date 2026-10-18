"""Non-destructive connection checks; no HTTP to normal services."""
import json, socket, sys
results=[]
for host,port in [('1.1.1.1',443),('host.docker.internal',5433),('host.docker.internal',8003),('host.docker.internal',8004),('host.docker.internal',8005),*[(ip,port) for ip in sys.argv[1:] for port in (5432,8003,8004,8005)]]:
    reachable=False
    try:
        with socket.create_connection((host,port),timeout=1): reachable=True
    except OSError: pass
    results.append({'host':host,'port':port,'reachable':reachable})
print(json.dumps(results))
assert not any(r['reachable'] for r in results), 'Isolation failure: stop before scanning'
