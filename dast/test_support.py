"""Offline safety tests using archived evidence and disposable test configuration."""
import json,os,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from dc import compose_command
from prepare import create_runtime
ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'docs/evidencias/2026-10-11/dast-active-readonly'
class SafetyTests(unittest.TestCase):
    def test_contracts_reject_write_operations(self):
        for name,count in {'identity':9,'permissions':5,'audit':1}.items():
            s=json.loads((ARCHIVE/'openapi'/f'{name}-readonly.openapi.json').read_text())
            self.assertEqual(len(s['paths']),count)
            self.assertTrue(all(set(v)=={'get'} for v in s['paths'].values()))
            self.assertFalse(any('/cargas' in p or '/mfa/' in p or '/password' in p or p=='/eventos' for p in s['paths']))
            self.assertNotIn('webhooks',s)
            self.assertEqual(len(s['servers']),1)
            self.assertIn(s['servers'][0]['url'],('http://identity:8003','http://permissions:8005','http://audit-service:8004'))
    def test_parent_env_cannot_override_project_or_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime=create_runtime(Path(tmp)/'test-runtime')
            with patch.dict(os.environ,COMPOSE_PROJECT_NAME='normal',COMPOSE_FILE='docker-compose.yml',POSTGRES_PASSWORD='NORMAL_SENTINEL',JWT_SECRET='NORMAL_SENTINEL',DB_NAME='normal'):
                cmd,env=compose_command(runtime,['config','--format','json'])
                r=subprocess.run(cmd,env=env,capture_output=True,text=True,check=True)
            self.assertNotIn('NORMAL_SENTINEL',r.stdout)
            c=json.loads(r.stdout)
            self.assertTrue(c['name'].startswith('iam-zap-'))
            for name,s in c['services'].items():
                self.assertFalse(s.get('ports'))
                self.assertNotIn('container_name',s)
                if name!='postgres':self.assertEqual(s['environment']['DB_NAME'],'iam_zap')
            self.assertTrue(c['networks']['dast']['internal'])
    def test_secrets_are_outside_checkout_and_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime=create_runtime(Path(tmp)/'test-runtime')
            self.assertNotIn(ROOT,runtime.parents)
            self.assertEqual(runtime.stat().st_mode & 0o777,0o700)
            self.assertEqual((runtime/'zap.env').stat().st_mode & 0o777,0o600)
if __name__=='__main__':unittest.main()
