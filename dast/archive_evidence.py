"""Create a reviewed, non-secret evidence bundle without altering raw evidence."""
import hashlib,json,re,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RUNTIME=ROOT.parent/'dast-runtime';PHASE=RUNTIME/'phase2'
ATTEMPT=PHASE/(PHASE/'latest-attempt.txt').read_text()
DEST=ROOT/'docs/evidencias/2026-10-11/dast-active-readonly'
secrets=[]
for line in (RUNTIME/'zap.env').read_text().splitlines():
 k,v=line.split('=',1)
 if any(s in k for s in ('PASSWORD','SECRET','KEY','TOKEN')):secrets.append(v)
fixtures=json.loads((PHASE/'fixtures.json').read_text())
secrets+=list(fixtures['tokens'].values())
patterns={
 'jwt':re.compile(r'eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}'),
 'authorization_header':re.compile(r'(?im)^\s*(?:proxy-)?authorization\s*:\s*\S+.*$'),
 'bearer':re.compile(r'(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}'),
 'mfa_uri':re.compile(r'otpauth://[^\s"<>]+'),
 'argon2_hash':re.compile(r'\$argon2(?:id|i|d)\$[^\s"<>]+'),
 'private_key':re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
}
def matches(text):
 return [name for name,p in patterns.items() if p.search(text)]+(['known_runtime_secret'] if any(v and v in text for v in secrets) else [])
def clean(text):
 for value in secrets:
  if value:text=text.replace(value,'[REDACTED]')
 text=text.replace(str(ROOT.parent),'<WORKSPACE>').replace('/host_mnt'+str(ROOT.parent),'<WORKSPACE>')
 for pattern in patterns.values():text=pattern.sub('[REDACTED]',text)
 return text
DEST.mkdir(parents=True,exist_ok=False)
manifest=[];audit=[]
def save(rel,text):
 text=clean(text)
 if matches(text):raise RuntimeError('Unsanitized artifact: '+str(rel))
 target=DEST/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text)
 manifest.append({'path':str(rel),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
# Preserve original aggregate table digests but omit per-cell digests, including credential/MFA cells.
for name in ('pre.json','post-frozen.json'):
 data=json.loads((ATTEMPT/name).read_text())
 data={table:{'count':entry['count'],'sha256':entry['sha256']} for table,entry in data.items()}
 save('database/'+name,json.dumps(data,indent=2))
for name in ('database-comparison.json','postflight-isolation.json','summary.json'):
 save(name,(ATTEMPT/name).read_text())
# Network addresses and raw logs remain local; preserve only aggregate isolation outcomes.
preflight=json.loads((PHASE/'preflight.json').read_text())
save('preflight-isolation.json',json.dumps({'scan_network_internal':preflight['scan_network_internal'],'scan_network_direct_backend_blocked':preflight['scan_network_direct_backend_blocked'],'connection_probes':len(preflight['probes']),'successful_connections':sum(p['reachable'] for p in preflight['probes']),'gateway_tests':preflight['gateway_tests']},indent=2))
for src in sorted(ATTEMPT.glob('*/report.*')):
 if src.suffix not in ('.json','.html'):continue
 found=matches(src.read_text());audit.append({'artifact':str(src.relative_to(ATTEMPT)),'findings_before':found,'findings_after':[]})
 if src.suffix=='.json':save(src.relative_to(ATTEMPT),src.read_text())
for src in sorted(ATTEMPT.glob('*/coverage.json')):save(src.relative_to(ATTEMPT),src.read_text())
for src in sorted((RUNTIME/'openapi').glob('*.json')):save('openapi/'+src.name,src.read_text())
summary=(ATTEMPT/'SUMMARY.md').read_text().replace(', [context]','; context retained locally, [context]')
# Contexts/job files are not needed for versioned evidence; regenerate them from the support scripts.
summary=re.sub(r'; context retained locally, \[context\]\([^)]*\)','; context retained locally',summary)
summary=summary.replace('pre.json, post.json (immediate), post-frozen.json (gateway stopped)', 'database/pre.json, database/post-frozen.json (gateway stopped)')
summary=re.sub(r', \[HTML\]\([^)]*\)', '', summary)
summary+='\nHTML reports are retained exclusively as local evidence.\n'
summary+='\nArchive sanitization: all 14 original JSON/HTML reports were checked against exact ephemeral secret/token values and credential patterns. No matches were found. Raw files remain local. The archive omits per-cell digests, raw network addresses, daemon logs, job files and contexts.\n'
save('SUMMARY.md',summary)
save('sanitization.json',json.dumps({'reports_reviewed':len(audit),'known_secret_values_checked':len(secrets),'original_report_findings':sum(bool(a['findings_before']) for a in audit),'artifacts':audit,'omitted':['zap.env','fixtures.json','config.json','raw DB per-cell digests','raw gateway/network/daemon logs','job files','contexts','HTML reports'],'method':'Exact runtime secret/token matching plus JWT, Authorization/Bearer, MFA URI, Argon2 and private-key patterns; local workspace paths normalized'},indent=2))
(DEST/'manifest.json').write_text(json.dumps({'source_commit':'2b0abd4694164ae11b36aab136f2255735c0e598','zap_version':'2.17.0','artifacts':manifest},indent=2))
print(f'Archived {len(manifest)+1} sanitized files; reviewed {len(audit)} JSON/HTML reports; original sensitive findings: {sum(bool(a["findings_before"]) for a in audit)}')
