"""Project-only cleanup. Default is a read-only plan; execute only after approval."""
import argparse,json,os,re,subprocess,sys
from pathlib import Path
from runtime import ROOT, RUNTIME, clean_environment
ENV=clean_environment()
def eligible(labels,project):
    return bool(labels) and labels.get('com.docker.compose.project')==project

def run(*args):
    return subprocess.check_output(list(args),env=ENV,text=True).strip()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    values=dict(l.split('=',1) for l in (RUNTIME/'zap.env').read_text().splitlines())
    project=values['ZAP_PROJECT']
    if not re.fullmatch(r'iam-zap-[a-f0-9]{12}',project):raise RuntimeError('Unexpected project identity')
    filt='label=com.docker.compose.project='+project
    def listing(kind):
        prefix=['docker',kind,'ls'] if kind!='container' else ['docker','ps','-a']
        return run(*prefix,'-q','--filter',filt).split()
    containers=listing('container');networks=listing('network');volumes=listing('volume')
    # Refuse to remove lab storage/networks if any unrelated container shares them.
    all_ids=run('docker','ps','-aq').split()
    all_containers=json.loads(run('docker','inspect',*all_ids)) if all_ids else []
    for c in all_containers:
        if eligible(c['Config'].get('Labels'),project):continue
        if set(c['NetworkSettings']['Networks']) & {project+'_dast',project+'_scan'}:raise RuntimeError('Network shared with unrelated container')
        if any(m.get('Name') in volumes for m in c['Mounts']):raise RuntimeError('Volume shared with unrelated container')
    plan={'project':project,'containers':containers,'networks':networks,'volumes':volumes,'execute':args.execute}
    if not args.execute:
        print(json.dumps(plan,indent=2));return
    # The explicit standalone Compose and sanitized environment come from dc.py.
    subprocess.run([sys.executable,str(ROOT/'dast/dc.py'),'down','--volumes','--remove-orphans'],env=ENV,check=True)
    # Remove only any labelled leftovers (manual ZAP/gateway and scan network).
    for kind,action in [('container','rm'),('network','rm'),('volume','rm')]:
        remaining=listing(kind)
        if remaining:
            prefix=['docker',kind,action]
            if kind=='container':prefix+=['-f']
            run(*prefix,*remaining)
    after={kind:listing(kind) for kind in ('container','network','volume')}
    if any(after.values()):raise RuntimeError('DAST resource cleanup incomplete')
    # Remove project image tags only; never prune shared bases, cache or other tags.
    for service in ('identity','audit-service','permissions','support'):
        tag=project+'-'+service+':latest'
        r=subprocess.run(['docker','image','inspect',tag],env=ENV,capture_output=True,text=True)
        if r.returncode==0:run('docker','image','rm',tag)
    # Preserve sanitized and raw non-secret evidence; remove ephemeral secret files.
    deleted=[]
    for path in (RUNTIME/'zap.env',RUNTIME/'phase2/fixtures.json',RUNTIME/'phase2/config.json',RUNTIME/'phase2/config.new'):
        if path.exists():path.unlink();deleted.append(path.name)
    result={'project':project,'remaining':after,'project_images_removed':True,'secret_files_removed':deleted,'normal_compose_used':False}
    (RUNTIME/'cleanup.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
