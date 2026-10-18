"""Create private runtime configuration; never read the normal .env."""
import base64, secrets
from pathlib import Path
from runtime import ROOT, RUNTIME
def create_runtime(runtime):
    runtime.mkdir(mode=0o700,exist_ok=False)
    env={
        'ZAP_PROJECT':'iam-zap-'+secrets.token_hex(6),
        'POSTGRES_PASSWORD':secrets.token_hex(32),
        'JWT_SECRET':secrets.token_hex(32),
        'MFA_ENCRYPTION_KEY':base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
        'AUDIT_INTERNAL_TOKEN':secrets.token_hex(32),
    }
    p=runtime/'zap.env'
    p.write_text(''.join(f'{k}={v}\n' for k,v in env.items()))
    p.chmod(0o600)
    (runtime/'openapi').mkdir(mode=0o700)
    return runtime
if __name__=='__main__':
    print('Created private runtime:',create_runtime(RUNTIME))
