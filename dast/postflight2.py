import json,subprocess
from pathlib import Path
from runtime import ROOT as root, RUNTIME as runtime, mount_source
phase=runtime/'phase2';attempt=phase/(phase/'latest-attempt.txt').read_text()
p=dict(l.split('=',1) for l in (runtime/'zap.env').read_text().splitlines())['ZAP_PROJECT']
def d(*a):return subprocess.check_output(['docker',*a],text=True)
networks={p+'_dast',p+'_scan'}
for n in networks:
 net=json.loads(d('network','inspect',n))[0];assert net['Internal']
assert json.loads(d('volume','inspect',p+'_pgdata'))[0]['Labels']['com.docker.compose.project']==p
result=[]
for c in json.loads(d('inspect',*d('ps','-aq').split())):
 labels=c['Config'].get('Labels') or {}
 ns=set(c['NetworkSettings']['Networks'])
 if labels.get('com.docker.compose.project')!=p:
  assert not ns&networks
  assert not any(m.get('Name')==p+'_pgdata' for m in c['Mounts'])
  continue
 service=labels['com.docker.compose.service']
 assert service in {'postgres','identity','audit-service','permissions','scan-gateway','zap'}
 assert not c['HostConfig']['PortBindings']
 assert ns<=networks and ns
 if service=='zap':assert ns=={p+'_scan'} and not c['State']['Running']
 if service=='scan-gateway':assert ns==networks and not c['State']['Running']
 for m in c['Mounts']:
  if m['Type']=='volume': assert m['Name']==p+'_pgdata' and service=='postgres'
  else:
   source=mount_source(m['Source'])
   assert source.startswith(mount_source(str(root))+'/') or source.startswith(mount_source(str(runtime))+'/')
 if service in {'postgres','identity','audit-service','permissions'}: assert c['State']['Health']['Status']=='healthy'
 result.append({'name':c['Name'],'service':service,'state':c['State']['Status'],'exit_code':c['State']['ExitCode'],'networks':sorted(ns),'published_ports':[]})
report={'internal_networks':sorted(networks),'normal_resources_shared':False,'gateway_and_scanners_stopped':True,'preserved_containers':result}
(attempt/'postflight-isolation.json').write_text(json.dumps(report,indent=2))
print(f'Isolation verified; {len(result)} containers preserved; gateway and scanners stopped; four healthy lab services remain')
