"""Run GET-only validation and save contract artifacts; do not invoke ZAP."""
import json, subprocess, sys
from pathlib import Path
from runtime import ROOT as root, RUNTIME as runtime
r=subprocess.run([sys.executable,str(root/'dast/dc.py'),'run','--rm','-T','support','/support/validate.py'],capture_output=True,text=True)
if r.returncode:
    print(r.stderr); print(r.stdout); raise SystemExit(r.returncode)
for line in r.stdout.splitlines():
    if line.startswith('OPENAPI '):
        _,name,data=line.split(' ',2)
        spec=json.loads(data)
        (runtime/'openapi'/f'{name}-readonly.openapi.json').write_text(json.dumps(spec,indent=2))
    elif line.startswith('RESULT '):
        data=json.loads(line[7:])
        (runtime/'validation.json').write_text(json.dumps(data,indent=2))
        print(json.dumps(data,indent=2))
