"""Build the CI artifact from a strict report allowlist; enforce DAST results."""
import base64
import hashlib
import json
import re
from pathlib import Path

PATTERNS = [
    re.compile(r'eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}'),
    re.compile(r'(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}'),
    re.compile(r'(?im)^\s*(?:proxy-)?authorization\s*:\s*\S+.*$'),
    re.compile(r'otpauth://[^\s"<>]+'),
    re.compile(r'\$argon2(?:id|i|d)\$[^\s"<>]+'),
    re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
]


def private_values(runtime):
    values = []
    env = runtime / 'zap.env'
    if env.exists():
        for line in env.read_text(encoding='utf-8').splitlines():
            key, value = line.split('=', 1)
            if any(word in key for word in ('PASSWORD', 'SECRET', 'KEY', 'TOKEN')):
                values.append(value)
    fixture = runtime / 'phase2/fixtures.json'
    if fixture.exists():
        for token in json.loads(fixture.read_text(encoding='utf-8'))['tokens'].values():
            values.append(token)
            payload = token.split('.')[1]
            claims = json.loads(base64.urlsafe_b64decode(payload + '=' * (-len(payload) % 4)))
            values.append(claims['jti'])
    return values


def sanitize(text, values, roots=()):
    for value in sorted(values, key=len, reverse=True):
        if value:
            text = text.replace(value, '[REDACTED]')
    for pattern in PATTERNS:
        text = pattern.sub('[REDACTED]', text)
    for root in roots:
        text = text.replace(str(root), '<WORKSPACE>')
    if any(value and value in text for value in values):
        raise RuntimeError('Sensitive value remains in artifact')
    return text


def result(summary, reports):
    runs = summary.get('runs', [])
    expected = {'identity-admin_ti': 9, 'identity-admin_soporte': 9,
                'permissions-admin_soporte': 5, 'permissions-lider_facturacion': 5,
                'permissions-lider_logistica': 5, 'permissions-lider_gestion_humana': 5,
                'audit-public': 1}
    if len(runs) != 7 or summary.get('api_role_operations') != 39:
        raise RuntimeError('Incomplete API/role scan coverage')
    if {run['run'] for run in runs} != set(expected):
        raise RuntimeError('Missing or repeated API/role scans')
    if summary.get('unexpected_database_changes'):
        raise RuntimeError('Unexpected staging database mutation')
    if set(summary.get('forwarded_methods', {})) != {'GET'}:
        raise RuntimeError('Unexpected forwarded scan method')
    findings = []
    for run in runs:
        if len(run['coverage']) != expected[run['run']]:
            raise RuntimeError('Missing API/role operations')
        if set(run.get('rules', [])) != {'6', '40003', '40018', '90019', '90020'} or run.get('strength') != 'LOW':
            raise RuntimeError('Incomplete active scan policy')
        if set(run.get('methods', {})) != {'GET'} or run['zap_recorded_requests'] <= 0:
            raise RuntimeError('No recorded GET scan traffic')
        if run['run'] not in reports:
            raise RuntimeError('Missing ZAP report')
        if any(not op.get('scan_completed') for op in run['coverage']):
            raise RuntimeError('Incomplete active operation')
        if not any(op.get('successful_application_access') for op in run['coverage']):
            raise RuntimeError('No application access for a scan role')
        for site in reports[run['run']].get('site', []):
            for alert in site.get('alerts', []):
                risk = int(alert['riskcode'])
                if risk not in range(4):
                    raise RuntimeError('Unknown ZAP risk code')
                findings.append({'run': run['run'], 'id': alert.get('pluginid'),
                                 'name': alert.get('alert'), 'risk': risk})
    blockers = [item for item in findings if item['risk'] >= 2]
    return {'passed': not blockers, 'policy': 'fail on MEDIUM/HIGH; no ignored alerts',
            'runs': 7, 'api_role_operations': 39,
            'zap_recorded_requests': sum(r['zap_recorded_requests'] for r in runs),
            'findings': findings, 'blockers': blockers}


def archive(runtime, output, source_commit, source_repository):
    phase = runtime / 'phase2'
    marker = phase / 'latest-attempt.txt'
    if not marker.exists():
        raise RuntimeError('No active scan attempt to archive')
    name = marker.read_text(encoding='utf-8').strip()
    if not re.fullmatch(r'attempt-\d{8}-\d{6}', name):
        raise RuntimeError('Invalid scan attempt path')
    attempt = phase / name
    values = private_values(runtime)
    summary = json.loads((attempt / 'summary.json').read_text(encoding='utf-8'))
    reports = {}
    for run in summary['runs']:
        if not re.fullmatch(r'(identity|permissions|audit)-[a-z_]+', run['run']):
            raise RuntimeError('Invalid scan report path')
        reports[run['run']] = json.loads((attempt / run['run'] / 'report.json').read_text(encoding='utf-8'))
    gate = result(summary, reports)
    output.mkdir(parents=True, exist_ok=True)
    manifest = []

    def save(relative, content):
        text = sanitize(content, values, (runtime.parent,))
        data = text.encode('utf-8')
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        manifest.append({'path': relative, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})

    for run in summary['runs']:
        if not re.fullmatch(r'(identity|permissions|audit)-[a-z_]+', run['run']):
            raise RuntimeError('Invalid scan report path')
        for file in ('report.json', 'report.html', 'coverage.json'):
            save(run['run'] + '/' + file, (attempt / run['run'] / file).read_text(encoding='utf-8'))
    for file in ('database-comparison.json', 'postflight-isolation.json'):
        save(file, (attempt / file).read_text(encoding='utf-8'))
    for file in ('pre.json', 'post-frozen.json'):
        data = json.loads((attempt / file).read_text(encoding='utf-8'))
        reduced = {table: {'count': row['count'], 'sha256': row['sha256']} for table, row in data.items()}
        save('database/' + file, json.dumps(reduced, indent=2))
    limits = ['GET-only active scan through scope gateway, five rules at LOW strength',
              'Synthetic sessions; no login, MFA enrolment, XLSX or write operations',
              '403 and gateway-rejected inputs do not cover protected business logic',
              'No frontend spider or complete application DAST coverage',
              'Fresh application builds; no use of normal Compose or local database']
    summary.pop('limitations', None)
    summary.pop('no_cleanup', None)
    summary.pop('no_commits_or_push', None)
    summary.update({'limitations': limits, 'source_commit': source_commit,
                    'source_repository': source_repository, 'gate': gate})
    save('summary.json', json.dumps(summary, indent=2))
    save('gate.json', json.dumps(gate, indent=2))
    lines = ['# Automated ZAP staging', '', f'Commit: {source_commit}',
             f'Repository: {source_repository}', '',
             f"7 scans; 39 API/role operations; {gate['zap_recorded_requests']} recorded requests.",
             f"Alert gate: {'PASS' if gate['passed'] else 'FAIL'} (MEDIUM/HIGH).", '',
             '| API / role | Requests | Alerts |', '|---|---:|---:|']
    for run in summary['runs']:
        lines.append(f"| {run['api']} / {run['role']} | {run['zap_recorded_requests']} | {len(run['alerts'])} |")
    lines.extend(['', '## Scope', '', *['- ' + limit for limit in limits]])
    save('SUMMARY.md', '\n'.join(lines) + '\n')
    (output / 'manifest.json').write_text(json.dumps({'artifacts': manifest}, indent=2), encoding='utf-8')
    return gate
