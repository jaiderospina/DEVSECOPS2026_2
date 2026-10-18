"""Validate isolation from Docker metadata without disclosing container secrets."""
import json, os, subprocess, sys
from pathlib import Path
from runtime import ROOT as root, RUNTIME as runtime, mount_source
p=dict(l.split('=',1) for l in (runtime/'zap.env').read_text().splitlines())['ZAP_PROJECT']
def docker(*args):
    return subprocess.check_output(['docker',*args],text=True)
containers=json.loads(docker('inspect',*docker('ps','-aq','--filter',f'label=com.docker.compose.project={p}').split()))
assert len(containers)==4
network=json.loads(docker('network','inspect',p+'_dast'))[0]
volume=json.loads(docker('volume','inspect',p+'_pgdata'))[0]
assert network['Internal'] and network['Labels']['com.docker.compose.project']==p
assert volume['Labels']['com.docker.compose.project']==p
summary=[]
for c in containers:
    assert set(c['NetworkSettings']['Networks'])=={p+'_dast'}
    assert not c['HostConfig']['PortBindings']
    assert not c['HostConfig']['Privileged']
    service=c['Config']['Labels']['com.docker.compose.service']
    assert c['State']['Health']['Status']=='healthy'
    for mount in c['Mounts']:
        if mount['Type']=='volume': assert mount['Name']==p+'_pgdata' and service=='postgres'
        else: assert mount_source(mount['Source'])==mount_source(str(root/'postgres-init')) and not mount['RW']
    env=dict(v.split('=',1) for v in c['Config']['Env'] if '=' in v)
    assert 'SMTP_PASSWORD' not in env
    if service!='postgres': assert env['DB_HOST']=='postgres' and env['DB_NAME']=='iam_zap'
    summary.append({'service':service,'healthy':True,'published_ports':[],'networks':[p+'_dast']})
# No unrelated container may join this network or mount this volume.
all_ids=docker('ps','-aq').split()
for c in json.loads(docker('inspect',*all_ids)):
    if c['Config'].get('Labels',{}).get('com.docker.compose.project')==p: continue
    assert p+'_dast' not in c['NetworkSettings']['Networks']
    assert not any(m.get('Name')==p+'_pgdata' for m in c['Mounts'])
report={'project':p,'internal_network':True,'dedicated_volume':p+'_pgdata','containers':summary,'normal_resources_shared':False,'active_scan_executed':False}
(runtime/'isolation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
