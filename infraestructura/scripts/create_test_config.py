"""Generate disposable CI credentials outside Git; never print them."""
import argparse
import base64
import json
import os
from pathlib import Path
import sys
import secrets

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from safe_paths import confined_path, deployment_path, project_name, runner_root

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--deploy-dir", required=True)
    parser.add_argument("--project", required=True)
    args = parser.parse_args()
    project_name(args.project, ci_only=True)
    deploy_dir = deployment_path(args.deploy_dir)
    target = confined_path(args.output, [runner_root()])
    config = {
        "iam_deploy_dir": str(deploy_dir),
        "iam_project_name": args.project,
        "iam_postgres_password": secrets.token_hex(32),
        "iam_jwt_secret": secrets.token_hex(48),
        "iam_audit_token": secrets.token_hex(32),
        "iam_mfa_key": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
        "iam_admin_password": "Aa1!" + secrets.token_hex(24),
        "iam_bootstrap_admin": True,
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target = confined_path(target, [runner_root()])
    # Exclusive creation prevents accidentally replacing deployed secrets.
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(config, stream)
    print("Disposable configuration created; values omitted.")

if __name__ == "__main__":
    main()
