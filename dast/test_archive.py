import hashlib,json,re,unittest
from pathlib import Path
from cleanup import eligible
ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'docs/evidencias/2026-10-11/dast-active-readonly'
class ClosureTests(unittest.TestCase):
    def test_cleanup_requires_exact_project_label(self):
        self.assertFalse(eligible(None,'iam-zap-test'))
        self.assertFalse(eligible({'com.docker.compose.project':'normal'},'iam-zap-test'))
        self.assertTrue(eligible({'com.docker.compose.project':'iam-zap-test'},'iam-zap-test'))
    def test_archive_integrity_and_no_credentials(self):
        manifest=json.loads((ARCHIVE/'manifest.json').read_text())
        self.assertEqual(len(manifest['artifacts']),25)
        for artifact in manifest['artifacts']:
            path=ARCHIVE/artifact['path'];raw=path.read_bytes();text=raw.decode()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),artifact['sha256'])
            self.assertNotRegex(text,r'eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}')
            self.assertNotRegex(text,r'(?im)^\s*Authorization\s*:')
            self.assertNotIn('/Users/',text)
            self.assertNotIn('$argon2',text)
        self.assertFalse(list(ARCHIVE.rglob('zap.env')))
        self.assertFalse(list(ARCHIVE.rglob('*.html')))
        self.assertEqual({a['path'] for a in manifest['artifacts']},{str(p.relative_to(ARCHIVE)) for p in ARCHIVE.rglob('*') if p.is_file() and p.name!='manifest.json'})
    def test_db_comparison_matches_archived_digests(self):
        pre=json.loads((ARCHIVE/'database/pre.json').read_text())
        post=json.loads((ARCHIVE/'database/post-frozen.json').read_text())
        changed=[t for t in pre if pre[t]['sha256']!=post[t]['sha256']]
        self.assertEqual(changed,['sesiones'])
        self.assertTrue(all(pre[t]['count']==post[t]['count'] for t in pre))
        comparison=json.loads((ARCHIVE/'database-comparison.json').read_text())
        self.assertEqual(comparison['unexpected_tables'],[])
if __name__=='__main__':unittest.main()
