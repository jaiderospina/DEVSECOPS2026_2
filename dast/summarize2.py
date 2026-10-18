"""Freeze DB evidence and summarize completed scan coverage without secrets."""
import json,re,sys,subprocess
from pathlib import Path
from collections import Counter
from runtime import ROOT, RUNTIME
PHASE=RUNTIME/'phase2'
attempt=PHASE/(PHASE/'latest-attempt.txt').read_text()
r=subprocess.run([sys.executable,str(ROOT/'dast/dc.py'),'run','--rm','-T','support','/support/snapshot.py'],capture_output=True,text=True,check=True)
post=json.loads(r.stdout);(attempt/'post-frozen.json').write_text(json.dumps(post,indent=2))
pre=json.loads((attempt/'pre.json').read_text())
comparison=[];unexpected=[]
for table in sorted(set(pre)|set(post)):
 a,b=pre[table],post[table]
 changes=[]
 for row in sorted(set(a['cells'])|set(b['cells'])):
  old,new=a['cells'].get(row),b['cells'].get(row)
  if old is None or new is None:
   changes.append({'row':row,'type':'inserted' if old is None else 'deleted'});continue
  columns=[k for k in set(old)|set(new) if old.get(k)!=new.get(k)]
  if columns:changes.append({'row':row,'columns':sorted(columns)})
 expected=all(table=='sesiones' and c.get('columns')==['ultima_actividad'] for c in changes)
 if changes and not expected:unexpected.append(table)
 comparison.append({'table':table,'pre_rows':a['count'],'post_rows':b['count'],'same_digest':a['sha256']==b['sha256'],'changes':changes,'only_expected_changes':expected})
(attempt/'database-comparison.json').write_text(json.dumps({'unexpected_tables':unexpected,'tables':comparison},indent=2))
logs=[json.loads(x) for x in (PHASE/'gateway.jsonl').read_text().splitlines()]
runs=[]
for file in sorted(attempt.glob('*/coverage.json')):
 c=json.loads(file.read_text());job=json.loads((file.parent/'job.json').read_text());report=json.loads((file.parent/'report.json').read_text())
 alerts=[a for site in report.get('site',[]) for a in site.get('alerts',[])]
 records=[r for r in logs if r['run']==job['name'] and r['allowed']]
 ops=[]
 for op in c['operations']:
  concrete=op['url'].split(job['base'],1)[1]
  responses=Counter(str(r['status']) for r in records if r['path']==concrete)
  # Counts include import/setup probes; status=200 means successful application access at this concrete path.
  ops.append({'operation':op['operation'],'scan_completed':op['progress']=='100','responses_at_concrete_path':dict(responses),'successful_application_access':'200' in responses})
 runs.append({'run':job['name'],'api':c['api'],'role':c['role'],'operations':len(ops),'zap_recorded_requests':sum(c['methods'].values()),'methods':c['methods'],'rules':c['rules'],'strength':c['strength'],'alerts':[{'id':a.get('pluginid'),'name':a.get('alert'),'risk':a.get('riskdesc')} for a in alerts],'coverage':ops})
allowed=[r for r in logs if r['allowed']]
assert all(r['method']=='GET' for r in allowed)
assert all(not r['path'].startswith('/usuarios/cargas') for r in allowed)
assert len(runs)==7 and sum(r['operations'] for r in runs)==39
summary={'unique_contract_operations':15,'api_role_operations':39,'runs':runs,'unexpected_database_changes':unexpected,'forwarded_methods':dict(Counter(r['method'] for r in allowed)),'gateway_blocked_requests':dict(Counter(r['method'] for r in logs if not r['allowed'])),'no_cleanup':True,'no_commits_or_push':True,'limitations':['Five selected active rules at LOW strength; not all ZAP rules','403 responses do not cover protected business logic','Synthetic sessions; no login/MFA flow executed','Gateway rejects out-of-scope mutated URLs; those inputs do not reach the API','Preflight negative method probes were rejected before the pre-scan snapshot','First setup attempt imported the filtered Identity contract but failed before any active scan; preserved separately']}
(attempt/'summary.json').write_text(json.dumps(summary,indent=2))
lines=['# Read-only active scan — phase 2','', 'ZAP 2.17.0; 15 unique GET operations, 39 API/role operations, 7 runs.','No spider/AJAX spider. Only filtered local contracts were imported.','Policy: Path Traversal (6), SQL Injection (40018), Server Side Code Injection (90019), Remote OS Command Injection (90020), CRLF Injection (40003), all LOW.','','| API / role | GET operations | ZAP recorded requests | Alerts |','|---|---:|---:|---:|']
for run in runs:lines.append(f"| {run['api']} / {run['role']} | {run['operations']} | {run['zap_recorded_requests']} | {len(run['alerts'])} |")
lines+=['','## Database comparison','','| Table | Before | After | Result |','|---|---:|---:|---|']
for t in comparison:lines.append(f"| {t['table']} | {t['pre_rows']} | {t['post_rows']} | {'identical' if t['same_digest'] else 'expected session activity only' if t['only_expected_changes'] else 'UNEXPECTED CHANGE'} |")
lines+=['','## Coverage limits','']+['- '+s for s in summary['limitations']]
lines+=['','## Reports','']
for run in runs:
 name=run['run'];lines.append(f'- {name}: [JSON]({name}/report.json), [HTML]({name}/report.html), [coverage]({name}/coverage.json), [context]({name}/scope.context)')
lines+=['','Evidence: pre.json, post.json (immediate), post-frozen.json (gateway stopped), database-comparison.json, summary.json.','Gateway and scan containers are stopped and preserved. Database/API containers remain running. No resources cleaned up.']
(attempt/'SUMMARY.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'runs':[{k:r[k] for k in ('run','operations','zap_recorded_requests','alerts')} for r in runs],'unexpected_database_changes':unexpected,'changed_tables':[{'table':t['table'],'changed_rows':len(t['changes']),'only_expected_changes':t['only_expected_changes']} for t in comparison if not t['same_digest']],'summary_path':str(attempt/'SUMMARY.md')},indent=2))
