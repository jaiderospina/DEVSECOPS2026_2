import json,subprocess,sys
from pathlib import Path
from runtime import ROOT as root, RUNTIME
phase=RUNTIME/'phase2'
p=dict(l.split('=',1) for l in (RUNTIME/'zap.env').read_text().splitlines())['ZAP_PROJECT']
def d(*a):return subprocess.check_output(['docker',*a],text=True)
net=json.loads(d('network','inspect',p+'_scan'))[0];assert net['Internal']
g=json.loads(d('inspect',p+'-gateway'))[0]
assert not g['HostConfig']['PortBindings'] and set(g['NetworkSettings']['Networks'])=={p+'_dast',p+'_scan'}
ids=d('ps','-q').split();ips=[]
for c in json.loads(d('inspect',*ids)):
 if c['Name']!='/'+p+'-gateway':ips.extend(n['IPAddress'] for n in c['NetworkSettings']['Networks'].values() if n.get('IPAddress'))
r=subprocess.run(['docker','run','--rm','--network',p+'_scan','--mount',f'type=bind,src={root / "dast"},dst=/support,readonly','--entrypoint','python',p+'-support','/support/probe.py',*sorted(set(ips))],capture_output=True,text=True,check=True)
probes=json.loads(r.stdout)
code="""import urllib.request,urllib.error,json
out=[]
for method,path,expect in [('GET','/auth/me',200),('POST','/usuarios',403),('GET','/auth/login',403),('DELETE','/auth/sesiones/expiradas',403)]:
 req=urllib.request.Request('http://identity:8003'+path,method=method)
 try:
  with urllib.request.urlopen(req,timeout=5) as r: status=r.status
 except urllib.error.HTTPError as e: status=e.code
 assert status==expect,(method,path,status)
 out.append({'method':method,'path':path,'status':status})
print(json.dumps(out))
"""
r=subprocess.run(['docker','run','--rm','--network',p+'_scan','--entrypoint','python',p+'-support','-c',code],capture_output=True,text=True)
if r.returncode:
    print(r.stderr[-3000:])
    raise RuntimeError('Gateway preflight HTTP contract failed')
result={'scan_network_internal':True,'scan_network_direct_backend_blocked':True,'probes':probes,'gateway_tests':json.loads(r.stdout)}
(phase/'preflight.json').write_text(json.dumps(result,indent=2))
print(f'{len(probes)} scanner-network connections blocked; gateway tests passed; no active scan yet')
