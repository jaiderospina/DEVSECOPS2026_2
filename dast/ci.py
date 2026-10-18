"""Automated disposable staging: active GET scans, report gate, owned cleanup."""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from runtime import ROOT, RUNTIME, clean_environment
from prepare import create_runtime
from evidence import archive, private_values, sanitize


def execute(arguments):
    completed = subprocess.run(arguments, env=clean_environment(), text=True,
                               encoding='utf-8', errors='replace', stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    output = sanitize(completed.stdout, private_values(RUNTIME), (ROOT.parent,))
    if completed.returncode:
        print(output[-8000:], flush=True)
        if Path(arguments[1]).name == 'preflight2.py':
            gateway = marker()['project'] + '-gateway'
            diagnostic = subprocess.run(['docker', 'logs', '--tail', '40', gateway],
                                        env=clean_environment(), capture_output=True, text=True)
            print(sanitize(diagnostic.stdout + diagnostic.stderr, private_values(RUNTIME), (ROOT.parent,))[-6000:], flush=True)
        raise RuntimeError('DAST stage failed: ' + str(Path(arguments[1]).name))
    print(output[-2400:], flush=True)
    return output


def script(name, *args):
    return execute([sys.executable, str(ROOT / 'dast' / name), *args])


def marker():
    file = RUNTIME / 'ci-owned.json'
    if not file.exists():
        raise RuntimeError('Refusing cleanup of a runtime not owned by this CI runner')
    data = json.loads(file.read_text(encoding='utf-8'))
    if not re.fullmatch(r'iam-zap-[a-f0-9]{12}', data['project']):
        raise RuntimeError('Invalid owned project')
    env = RUNTIME / 'zap.env'
    if env.exists():
        values = dict(line.split('=', 1) for line in env.read_text(encoding='utf-8').splitlines())
        if values['ZAP_PROJECT'] != data['project']:
            raise RuntimeError('Runtime ownership mismatch')
    return data


def cleanup():
    if not RUNTIME.exists():
        return
    marker()
    if not (RUNTIME / 'zap.env').exists():
        if (RUNTIME / 'cleanup.json').exists():
            data = json.loads((RUNTIME / 'cleanup.json').read_text(encoding='utf-8'))
            if any(data['remaining'].values()):
                raise RuntimeError('Incomplete prior cleanup')
            return
        raise RuntimeError('Missing runtime configuration before cleanup')
    script('cleanup.py', '--execute')


def run(output):
    if ROOT != output and ROOT not in output.parents:
        raise RuntimeError('Artifact output must be inside the checkout')
    if output == ROOT or output.is_symlink():
        raise RuntimeError('Unsafe artifact output path')
    if not os.environ.get('IAM_DAST_RUNTIME'):
        raise RuntimeError('CI requires an explicit runtime outside the checkout')
    if output.exists():
        raise RuntimeError('Artifact output already exists; use a fresh run directory')
    source = os.environ.get('GITHUB_SHA') or subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    repository = os.environ.get('GITHUB_REPOSITORY', 'local-validation')
    create_runtime(RUNTIME)
    project = dict(line.split('=', 1) for line in (RUNTIME / 'zap.env').read_text(encoding='utf-8').splitlines())['ZAP_PROJECT']
    (RUNTIME / 'ci-owned.json').write_text(json.dumps({'project': project}), encoding='utf-8')
    output.mkdir(parents=True, exist_ok=False)
    success = False
    clean = False
    try:
        image = 'ghcr.io/zaproxy/zaproxy@sha256:7aaa659b0d43078febd82e29bad112285c370727e86ab8340444220e17d9f0d2'
        execute(['docker', 'pull', image])
        script('dc.py', 'build', 'identity', 'audit-service', 'permissions', 'support')
        script('dc.py', 'up', '-d', '--wait', '--wait-timeout', '120', 'postgres')
        script('dc.py', 'run', '--rm', '-T', 'support', '/support/seed.py')
        script('dc.py', 'up', '-d', '--wait', '--wait-timeout', '120', 'identity', 'audit-service', 'permissions')
        for name in ('export.py', 'probe_host.py', 'check.py', 'record_seed.py'):
            script(name)
        script('phase2.py', 'prepare')
        script('preflight2.py')
        script('phase2.py', 'run')
        script('summarize2.py')
        script('postflight2.py')
        gate = archive(RUNTIME, output, source, repository)
        if not gate['passed']:
            raise RuntimeError('ZAP MEDIUM/HIGH alert gate failed; sanitized reports preserved')
        success = True
    finally:
        try:
            cleanup()
            clean = True
        finally:
            (output / 'lifecycle.json').write_text(json.dumps({
                'source_commit': source, 'repository': repository,
                'scan_and_gate_passed': success, 'cleanup_completed': clean,
                'runtime_secrets_uploaded': False,
                'normal_compose_used': False, 'normal_database_used': False,
            }, indent=2), encoding='utf-8')
    print('Staging DAST passed; sanitized HTML/JSON saved and ephemeral resources removed', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['run', 'cleanup'])
    parser.add_argument('--output', type=Path, default=ROOT / 'reports/zap-staging')
    args = parser.parse_args()
    if args.action == 'cleanup':
        cleanup()
    else:
        run(args.output.resolve())


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(sanitize(type(exc).__name__ + ': ' + str(exc), private_values(RUNTIME), (ROOT.parent,)), file=sys.stderr)
        raise SystemExit(1)
