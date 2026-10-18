"""Negative controls for incomplete scans, blocking alerts and report redaction."""
import copy
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evidence import result, sanitize
from runtime import ROOT, clean_environment, runtime_directory
import ci


class CiSafetyTests(unittest.TestCase):
    def fixture(self):
        expected = {'identity-admin_ti': 9, 'identity-admin_soporte': 9,
                    'permissions-admin_soporte': 5, 'permissions-lider_facturacion': 5,
                    'permissions-lider_logistica': 5, 'permissions-lider_gestion_humana': 5,
                    'audit-public': 1}
        runs = [{'run': name, 'coverage': [
            {'scan_completed': True, 'successful_application_access': True} for _ in range(count)],
            'zap_recorded_requests': count, 'rules': ['6','40003','40018','90019','90020'],
            'strength': 'LOW', 'methods': {'GET': count}} for name, count in expected.items()]
        summary = {'runs': runs, 'api_role_operations': 39,
                   'unexpected_database_changes': [], 'forwarded_methods': {'GET': 7}}
        return summary, {run['run']: {'site': []} for run in runs}

    def test_medium_alert_blocks_without_ignores(self):
        summary, reports = self.fixture()
        reports['identity-admin_ti'] = {'site': [{'alerts': [{'riskcode': '2', 'pluginid': 'test', 'alert': 'fixture'}]}]}
        self.assertFalse(result(summary, reports)['passed'])
        self.assertEqual(len(result(summary, reports)['blockers']), 1)

    def test_incomplete_or_mutating_scan_fails_closed(self):
        summary, reports = self.fixture()
        for change in ('missing_report', 'partial_scan', 'no_access', 'missing_operation', 'missing_rule', 'mutation', 'method'):
            data, evidence = copy.deepcopy(summary), copy.deepcopy(reports)
            if change == 'missing_report': evidence.pop('identity-admin_ti')
            if change == 'partial_scan': data['runs'][0]['coverage'][0]['scan_completed'] = False
            if change == 'no_access':
                for operation in data['runs'][0]['coverage']: operation['successful_application_access'] = False
            if change == 'missing_operation': data['runs'][0]['coverage'].pop()
            if change == 'missing_rule': data['runs'][0]['rules'].pop()
            if change == 'mutation': data['unexpected_database_changes'] = ['usuarios_plataforma']
            if change == 'method': data['forwarded_methods']['POST'] = 1
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                result(data, evidence)

    def test_artifacts_redact_runtime_secrets_and_credentials(self):
        text = 'credential=ephemeral-sentinel\nAuthorization: Bearer secret-token-value\notpauth://totp/test?secret=ABC'
        redacted = sanitize(text, ['ephemeral-sentinel'])
        for value in ('ephemeral-sentinel', 'secret-token-value', 'otpauth://'):
            self.assertNotIn(value, redacted)

    def test_runtime_and_child_environment_are_confined(self):
        with patch.dict(os.environ, IAM_DAST_RUNTIME=str(ROOT/'reports/private'),
                        JWT_SECRET='normal', DB_NAME='normal', COMPOSE_FILE='docker-compose.yml'):
            with self.assertRaises(RuntimeError): runtime_directory()
            env = clean_environment()
            for name in ('JWT_SECRET', 'DB_NAME', 'COMPOSE_FILE'): self.assertNotIn(name, env)

    def test_cleanup_refuses_unowned_or_mismatched_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            with patch.object(ci, 'RUNTIME', runtime), patch.object(ci, 'script') as command:
                with self.assertRaises(RuntimeError): ci.cleanup()
                (runtime/'ci-owned.json').write_text('{"project":"iam-zap-000000000000"}')
                (runtime/'zap.env').write_text('ZAP_PROJECT=iam-zap-111111111111\n')
                with self.assertRaises(RuntimeError): ci.cleanup()
                command.assert_not_called()


if __name__ == '__main__': unittest.main()
