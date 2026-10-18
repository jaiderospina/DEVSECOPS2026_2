import subprocess,sys,json
from pathlib import Path
from runtime import ROOT as root, RUNTIME
r=subprocess.run([sys.executable,str(root/'dast/dc.py'),'run','--rm','-T','support','/support/verify_seed.py'],capture_output=True,text=True)
if r.returncode:
    print(r.stdout);print(r.stderr);raise SystemExit(r.returncode)
data=json.loads(r.stdout)
(RUNTIME/'schema-seed.json').write_text(json.dumps(data,indent=2))
print(json.dumps(data,indent=2))
