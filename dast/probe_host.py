import json, subprocess, sys
from pathlib import Path
from runtime import ROOT as root, RUNTIME as runtime
p=dict(l.split('=',1) for l in (runtime/'zap.env').read_text().splitlines())['ZAP_PROJECT']
ids=subprocess.check_output(['docker','ps','-q'],text=True).split()
ips=[]
for c in json.loads(subprocess.check_output(['docker','inspect',*ids],text=True)):
    if c['Config'].get('Labels',{}).get('com.docker.compose.project')!=p:
        ips.extend(n['IPAddress'] for n in c['NetworkSettings']['Networks'].values() if n.get('IPAddress'))
r=subprocess.run([sys.executable,str(root/'dast/dc.py'),'run','--rm','-T','support','/support/probe.py',*sorted(set(ips))],capture_output=True,text=True)
if r.returncode:
    print(r.stdout); print(r.stderr); raise SystemExit(r.returncode)
data=json.loads(r.stdout)
(runtime/'network-probes.json').write_text(json.dumps(data,indent=2))
print(f'{len(data)} connection probes blocked; {len(set(ips))} unrelated container IPs checked')
