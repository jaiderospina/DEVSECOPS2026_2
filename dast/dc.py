"""Standalone Compose with private runtime and sanitized process environment."""
import os, subprocess, sys
from pathlib import Path
from runtime import ROOT, RUNTIME, clean_environment
def compose_command(runtime, arguments):
    values=dict(line.split('=',1) for line in (runtime/'zap.env').read_text().splitlines())
    assert values['ZAP_PROJECT'].startswith('iam-zap-')
    env=clean_environment()
    cmd=['docker','compose','-p',values['ZAP_PROJECT'],'--project-directory',str(ROOT),'--env-file',str(runtime/'zap.env'),'-f',str(ROOT/'compose.zap.yml'),*arguments]
    return cmd,env
if __name__=='__main__':
    cmd,env=compose_command(RUNTIME,sys.argv[1:])
    raise SystemExit(subprocess.call(cmd,env=env))
