"""Import only filtered contract; explicit GET scans, no discovery jobs."""
import json,sys,time,re,subprocess,os
from pathlib import Path
from urllib.parse import urlsplit
from zapv2 import ZAPv2
job=json.loads(Path('/work/job.json').read_text())
out=Path('/work')
log=(out/'zap-daemon.log').open('w')
proc=subprocess.Popen(['/zap/zap.sh','-daemon','-host','127.0.0.1','-port','8090','-config','api.disablekey=true','-config','autoupdate.checkOnStart=false','-config','autoupdate.installAddonUpdates=false','-config','connection.timeoutInSecs=10'],stdout=log,stderr=subprocess.STDOUT)
z=ZAPv2(proxies={'http':'http://127.0.0.1:8090','https':'http://127.0.0.1:8090'})
def checked(value):
    if isinstance(value,dict) and ('code' in value or 'error' in value): raise RuntimeError(value)
    return value
try:
    for _ in range(90):
        try: version=z.core.version;break
        except Exception:time.sleep(1)
    else:raise RuntimeError('ZAP did not start')
    ctx=job['name']
    cid=checked(z.context.new_context(ctx))
    for pattern in job['patterns']:checked(z.context.include_in_context(ctx,pattern))
    checked(z.context.exclude_from_context(ctx,re.escape(job['base'])+r'/usuarios/cargas(?:[/?].*)?'))
    checked(z.context.set_context_in_scope(ctx,True))
    checked(z.core.set_mode('protect'))
    checked(z.context.export_context(ctx,'/work/scope.context'))
    checked(z.ascan.add_scan_policy('GET-only'))
    checked(z.ascan.disable_all_scanners(scanpolicyname='GET-only'))
    available=z.ascan.scanners(scanpolicyname='GET-only')
    selected=[s['id'] for s in available if s['id'] in ['6','40003','40018','90019','90020']]
    assert set(selected)=={'6','40003','40018','90019','90020'}, 'Required active rules unavailable'
    checked(z.ascan.enable_scanners(','.join(selected),scanpolicyname='GET-only'))
    checked(z.ascan.set_policy_attack_strength('GET-only','LOW'))
    checked(z.ascan.set_option_thread_per_host(1))
    checked(z.ascan.set_option_delay_in_ms(30))
    checked(z.ascan.set_option_max_rule_duration_in_mins(1))
    checked(z.ascan.set_option_max_scan_duration_in_mins(2))
    checked(z.ascan.set_option_add_query_param(True))
    checked(z.ascan.set_option_inject_plugin_id_in_header(True))
    # No remote contract fetch, no spider, no automatic scope expansion.
    imported=checked(z.openapi.import_file('/work/readonly.openapi.json',target=job['base'],contextid=cid))
    (out/'import.json').write_text(json.dumps(imported,indent=2))
    specs=json.loads((out/'readonly.openapi.json').read_text())
    assert all(set(v)=={'get'} for v in specs['paths'].values())
    coverage=[]
    for path in specs['paths']:
        concrete=path
        for k,v in job['values'].items():concrete=concrete.replace('{'+k+'}',str(v))
        url=job['base']+concrete
        assert not re.search(r'\{',url)
        assert any(re.fullmatch(p,url) for p in job['patterns'])
        # Seed the exact request with a harmless query input even for parameterless GETs.
        z.urlopen(url+'?zap_probe=baseline',allow_redirects=False)
        sid=checked(z.ascan.scan(url+'?zap_probe=baseline',recurse=False,inscopeonly=True,scanpolicyname='GET-only',method='GET',contextid=cid))
        deadline=time.monotonic()+160
        while int(z.ascan.status(sid))<100:
            if time.monotonic()>deadline:
                z.ascan.stop(sid); raise RuntimeError('Scan timed out: '+path)
            time.sleep(1)
        coverage.append({'operation':'GET '+path,'url':url,'scan_id':sid,'progress':z.ascan.status(sid),'requests':z.ascan.scan_progress(sid)})
        print(job['name']+' completed GET '+path,flush=True)
    deadline=time.monotonic()+60
    while int(z.pscan.records_to_scan)>0 and time.monotonic()<deadline:time.sleep(1)
    assert int(z.pscan.records_to_scan)==0, 'Passive scan queue did not complete'
    (out/'report.json').write_text(z.core.jsonreport())
    (out/'report.html').write_text(z.core.htmlreport())
    # No request headers or credentials are retained in coverage.
    messages=z.core.messages(baseurl=job['base'],start=0,count=100000)
    methods={}
    for m in messages:
        line=m['requestHeader'].splitlines()[0]
        method=line.split(' ',1)[0];methods[method]=methods.get(method,0)+1
    assert set(methods)<= {'GET'}, methods
    (out/'coverage.json').write_text(json.dumps({'api':job['api'],'role':job['role'],'zap_version':version,'rules':selected,'strength':'LOW','spider':False,'methods':methods,'operations':coverage},indent=2))
    print(job['name']+' report saved; '+json.dumps(methods),flush=True)
finally:
    try:z.core.shutdown()
    except Exception:proc.terminate()
    proc.wait(timeout=30)
