"""Phase 2 controller; explicit prepare/run stages; secrets never printed."""
import json,os,re,subprocess,sys,hashlib,time
from pathlib import Path
from runtime import ROOT, RUNTIME, clean_environment
P=dict(l.split('=',1) for l in (RUNTIME/'zap.env').read_text().splitlines())['ZAP_PROJECT']
PHASE=RUNTIME/'phase2'
IMAGE='ghcr.io/zaproxy/zaproxy@sha256:7aaa659b0d43078febd82e29bad112285c370727e86ab8340444220e17d9f0d2'
ENV=clean_environment()
def command(args,**kw): return subprocess.run(args,env=ENV,check=True,text=True,**kw)
def dc(*args,capture=False):return command([sys.executable,str(ROOT/'dast/dc.py'),*args],capture_output=capture)
def support(script):return json.loads(dc('run','--rm','-T','support','/support/'+script,capture=True).stdout)
def config_for(job,fixtures):
    hosts={}
    for api,host,port in [('identity','identity',8003),('permissions','permissions',8005),('audit','audit-service',8004)]:
        spec=json.loads((RUNTIME/'openapi'/f'{api}-readonly.openapi.json').read_text())
        patterns=[re.sub(r'\\\{[^}]+\\\}',r'[^/]+',re.escape(p)) for p in spec['paths']]
        net=json.loads(command(['docker','inspect','--format','{{json .NetworkSettings.Networks}}',P+'-'+host+'-1'],capture_output=True).stdout)
        upstream=net[P+'_dast']['IPAddress']
        hosts[f'{host}:{port}']={'upstream':upstream,'port':port,'patterns':patterns if api==job['api'] else []}
    return {'run':job['name'],'hosts':hosts,'token':fixtures['tokens'].get(job.get('email')),'keepalive_tokens':list(fixtures['tokens'].values())}
def jobs(fixtures):
    runs=[('identity','ADMIN_TI','zap0@example.invalid'),('identity','ADMIN_SOPORTE','zap1@example.invalid'),('permissions','ADMIN_SOPORTE','zap1@example.invalid'),('permissions','LIDER_FACTURACION','zap2@example.invalid'),('permissions','LIDER_LOGISTICA','zap3@example.invalid'),('permissions','LIDER_GESTION_HUMANA','zap4@example.invalid'),('audit','PUBLIC',None)]
    result=[]
    codes={'LIDER_FACTURACION':'facturacion.aprobaciones.consultar','LIDER_LOGISTICA':'logistica.despachos.consultar','LIDER_GESTION_HUMANA':'gestion_humana.colaboradores.consultar'}
    for api,role,email in runs:
        spec=json.loads((RUNTIME/'openapi'/f'{api}-readonly.openapi.json').read_text())
        base=spec['servers'][0]['url']
        assert all(set(v)=={'get'} for v in spec['paths'].values())
        vals={'usuario_id':fixtures['users']['zap2@example.invalid'],'company_id':fixtures['company'],'compania_id':fixtures['company'],'code':codes.get(role,'facturacion.aprobaciones.consultar')}
        patterns=[re.escape(base)+re.sub(r'\\\{[^}]+\\\}',r'[^/?]+',re.escape(p))+r'(?:\?[^#]*)?' for p in spec['paths']]
        name=api+'-'+role.lower()
        result.append({'name':name,'api':api,'role':role,'email':email,'base':base,'patterns':patterns,'values':vals})
    return result
if sys.argv[1]=='prepare':
    PHASE.mkdir(mode=0o700,exist_ok=False)
    fixtures=support('scan_fixtures.py')
    # File is inside 0700 runtime; only the gateway receives this directory.
    (PHASE/'fixtures.json').write_text(json.dumps(fixtures));(PHASE/'fixtures.json').chmod(0o600)
    js=jobs(fixtures)
    (PHASE/'jobs.json').write_text(json.dumps(js,indent=2))
    (PHASE/'config.json').write_text(json.dumps(config_for(js[0],fixtures)))
    (PHASE/'gateway.jsonl').touch();(PHASE/'gateway.jsonl').chmod(0o666)
    command(['docker','network','create','--internal','--label',f'com.docker.compose.project={P}',P+'_scan'],capture_output=True)
    # Match the private bind directory owner; root with all capabilities dropped
    # cannot traverse the runner's 0700 directory on Linux.
    owner=PHASE.stat()
    command(['docker','run','-d','--name',P+'-gateway','--label',f'com.docker.compose.project={P}','--label','com.docker.compose.service=scan-gateway','--network',P+'_dast','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','256m','--user',f'{owner.st_uid}:{owner.st_gid}','--mount',f'type=bind,src={ROOT / "dast"},dst=/support,readonly','--mount',f'type=bind,src={PHASE},dst=/run/scan,readonly','--mount',f'type=bind,src={PHASE / "gateway.jsonl"},dst=/results/gateway.jsonl', '--entrypoint','python',P+'-support','/support/gateway.py'],capture_output=True)
    command(['docker','network','connect','--alias','identity','--alias','permissions','--alias','audit-service',P+'_scan',P+'-gateway'])
    print('Prepared synthetic sessions, strict gateway, scan-only internal network; no scan executed')
elif sys.argv[1]=='run':
    fixtures=json.loads((PHASE/'fixtures.json').read_text());js=json.loads((PHASE/'jobs.json').read_text())
    attempt=PHASE/('attempt-'+time.strftime('%Y%m%d-%H%M%S'));attempt.mkdir(mode=0o700)
    (PHASE/'latest-attempt.txt').write_text(attempt.name)
    (attempt/'pre.json').write_text(json.dumps(support('snapshot.py'),indent=2))
    try:
        for job in js:
            path=attempt/job['name'];path.mkdir(mode=0o777);path.chmod(0o777)
            spec=json.loads((RUNTIME/'openapi'/f'{job["api"]}-readonly.openapi.json').read_text())
            for item in spec['paths'].values():
                for param in item['get'].get('parameters',[]):
                    if param['name'] in job['values']:
                        param['example']=job['values'][param['name']]
                        param.setdefault('schema',{})['default']=job['values'][param['name']]
            (path/'readonly.openapi.json').write_text(json.dumps(spec))
            (path/'job.json').write_text(json.dumps(job))
            temp=PHASE/'config.new';temp.write_text(json.dumps(config_for(job,fixtures)));temp.replace(PHASE/'config.json')
            print('Starting '+job['name'],flush=True)
            command(['docker','run','--name',P+'-'+job['name']+'-'+attempt.name,'--label',f'com.docker.compose.project={P}','--label','com.docker.compose.service=zap','--network',P+'_scan','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','2g','--cpus','2','--mount',f'type=bind,src={ROOT / "dast"},dst=/support,readonly','--mount',f'type=bind,src={path},dst=/work','--entrypoint','python',IMAGE,'/support/zap_readonly.py'])
    finally:
        command(['docker','stop',P+'-gateway'],capture_output=True)
        (attempt/'post.json').write_text(json.dumps(support('snapshot.py'),indent=2))
        print('Post-scan database evidence saved',flush=True)
