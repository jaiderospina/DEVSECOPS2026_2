"""Paths and process environment for the disposable staging laboratory."""
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def runtime_directory():
    path = Path(os.environ.get('IAM_DAST_RUNTIME', ROOT.parent / 'dast-runtime')).resolve()
    if path == ROOT or ROOT in path.parents:
        raise RuntimeError('DAST runtime must be outside the checkout')
    return path


RUNTIME = runtime_directory()


def clean_environment():
    names = ('PATH', 'HOME', 'TMPDIR', 'TEMP', 'TMP', 'SystemRoot', 'WINDIR',
             'SYSTEMDRIVE', 'USERPROFILE', 'DOCKER_CONFIG', 'IAM_DAST_RUNTIME')
    return {key: os.environ[key] for key in names if key in os.environ}


def mount_source(source):
    """Normalize Docker Desktop bind paths without changing their scope."""
    value = source.replace('\\', '/')
    value = value.removeprefix('/host_mnt')
    prefix = '/run/desktop/mnt/host/'
    if value.startswith(prefix):
        value = '/' + value[len(prefix):]
    if os.name == 'nt' and re.match(r'^/[a-zA-Z]/', value):
        value = value[1].upper() + ':' + value[2:]
    return value.rstrip('/')
