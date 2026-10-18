"""Verify orchestration and cleanup failure behavior without running Docker."""
import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ci


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name)
        self.root = base / 'checkout'
        self.root.mkdir()
        self.runtime = base / 'private-runtime'
        self.output = self.root / 'reports'
        for name, value in [('ROOT', self.root), ('RUNTIME', self.runtime)]:
            patcher = patch.object(ci, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        environment = patch.dict(os.environ, {'IAM_DAST_RUNTIME': str(self.runtime),
                                              'GITHUB_SHA': 'fixture-sha', 'GITHUB_REPOSITORY': 'fixture/repo'})
        environment.start()
        self.addCleanup(environment.stop)

    def prepare(self, directory):
        directory.mkdir()
        (directory / 'zap.env').write_text('ZAP_PROJECT=iam-zap-000000000000\nJWT_SECRET=fixture-private-canary\n')

    def test_success_runs_owned_cleanup_and_records_the_tested_revision(self):
        with patch.object(ci, 'create_runtime', side_effect=self.prepare), \
                patch.object(ci, 'execute') as execute, patch.object(ci, 'script') as script, \
                patch.object(ci, 'archive', return_value={'passed': True}) as archive, \
                contextlib.redirect_stdout(io.StringIO()):
            ci.run(self.output)
        execute.assert_called_once()
        self.assertEqual(execute.call_args.args[0][0:2], ['docker', 'pull'])
        self.assertEqual(script.call_args_list[-1].args, ('cleanup.py', '--execute'))
        archive.assert_called_once_with(self.runtime, self.output, 'fixture-sha', 'fixture/repo')
        result = json.loads((self.output / 'lifecycle.json').read_text())
        self.assertTrue(result['scan_and_gate_passed'])
        self.assertTrue(result['cleanup_completed'])
        self.assertFalse(result['runtime_secrets_uploaded'])

    def test_blocking_scan_still_cleans_and_records_failed_gate(self):
        with patch.object(ci, 'create_runtime', side_effect=self.prepare), \
                patch.object(ci, 'execute'), patch.object(ci, 'script') as script, \
                patch.object(ci, 'archive', return_value={'passed': False}):
            with self.assertRaisesRegex(RuntimeError, 'MEDIUM/HIGH'):
                ci.run(self.output)
        self.assertEqual(script.call_args_list[-1].args, ('cleanup.py', '--execute'))
        result = json.loads((self.output / 'lifecycle.json').read_text())
        self.assertFalse(result['scan_and_gate_passed'])
        self.assertTrue(result['cleanup_completed'])

    def test_cleanup_failure_is_not_reported_as_success(self):
        with patch.object(ci, 'create_runtime', side_effect=self.prepare), \
                patch.object(ci, 'execute'), patch.object(ci, 'script'), \
                patch.object(ci, 'archive', return_value={'passed': True}), \
                patch.object(ci, 'cleanup', side_effect=RuntimeError('fixture cleanup failed')):
            with self.assertRaisesRegex(RuntimeError, 'fixture cleanup failed'):
                ci.run(self.output)
        self.assertFalse(json.loads((self.output / 'lifecycle.json').read_text())['cleanup_completed'])

    def test_refuses_existing_or_outside_output_before_creating_runtime(self):
        with patch.object(ci, 'create_runtime') as create:
            for output in (self.root, self.root.parent / 'outside'):
                with self.assertRaises(RuntimeError):
                    ci.run(output)
            self.output.mkdir()
            with self.assertRaisesRegex(RuntimeError, 'already exists'):
                ci.run(self.output)
        create.assert_not_called()

    def test_refuses_absent_explicit_runtime(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(ci, 'create_runtime') as create:
            with self.assertRaisesRegex(RuntimeError, 'explicit runtime'):
                ci.run(self.output)
        create.assert_not_called()

    def test_completed_cleanup_is_idempotent_but_incomplete_cleanup_fails(self):
        self.prepare(self.runtime)
        (self.runtime / 'ci-owned.json').write_text('{"project":"iam-zap-000000000000"}')
        (self.runtime / 'zap.env').unlink()
        with patch.object(ci, 'script') as script:
            with self.assertRaisesRegex(RuntimeError, 'Missing runtime configuration'):
                ci.cleanup()
            result = self.runtime / 'cleanup.json'
            result.write_text('{"remaining":{"container":[],"network":[],"volume":[]}}')
            ci.cleanup()
            result.write_text('{"remaining":{"container":["fixture"],"network":[],"volume":[]}}')
            with self.assertRaisesRegex(RuntimeError, 'Incomplete prior cleanup'):
                ci.cleanup()
        script.assert_not_called()

    def test_child_output_is_redacted_on_success_and_failure(self):
        self.prepare(self.runtime)
        arguments = ['python', '/support/check.py']
        for code in (0, 1):
            output = io.StringIO()
            completed = subprocess.CompletedProcess(arguments, code, 'fixture-private-canary')
            with patch.object(ci.subprocess, 'run', return_value=completed), contextlib.redirect_stdout(output):
                if code:
                    with self.assertRaisesRegex(RuntimeError, 'DAST stage failed'):
                        ci.execute(arguments)
                else:
                    self.assertEqual(ci.execute(arguments), '[REDACTED]')
            self.assertNotIn('fixture-private-canary', output.getvalue())
