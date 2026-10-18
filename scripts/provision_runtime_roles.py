"""Enable narrow runtime logins without secrets in SQL files/argv/output."""
import argparse
import json
import os
import re
import subprocess

from safe_paths import REPOSITORY, confined_path

ROLES = {"iam_identity", "iam_permissions", "iam_sync", "iam_audit", "iam_dispatcher", "iam_backup"}


def load_roles_file(value):
    # A CLI must not be able to read arbitrary files on the operator's machine.
    # Generated runtime credentials live in this checkout's private directory.
    path = confined_path(value, [REPOSITORY / ".private"])
    if path.name != "roles.json" or not path.is_file() or path.stat().st_size > 16384:
        raise ValueError("Use a bounded roles.json in the private laboratory directory")
    values = json.loads(path.read_text(encoding="utf-8"))
    role_statement(values)
    return values


def role_statement(values):
    if not isinstance(values, dict) or set(values) != ROLES:
        raise ValueError("Six runtime credentials are required")
    if any(not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value) for value in values.values()):
        raise ValueError("Use independently generated 32-byte hexadecimal credentials")
    if len(set(values.values())) != len(ROLES):
        raise ValueError("Six distinct runtime credentials are required")
    # Both identifiers and values are validated fixed alphabets, never free SQL.
    # Abort on inherited memberships rather than enabling a potentially privileged login.
    names = ",".join("'" + role + "'" for role in sorted(ROLES))
    guard = f"""DO $$ BEGIN IF EXISTS (
        SELECT 1 FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member
        WHERE r.rolname IN ({names})) THEN
        RAISE EXCEPTION 'Runtime role membership requires operator review';
        END IF; END $$;\n"""
    return ("BEGIN;\nSET LOCAL log_statement='none';\n" + guard + "".join(
        f"ALTER ROLE {role} LOGIN PASSWORD '{values[role]}';\n" for role in sorted(ROLES)) + "COMMIT;\n").encode()


def provision(container, database, values):
    if not re.fullmatch(r"iam-[a-z0-9_-]+", container) or not re.fullmatch(r"iam_[a-z0-9_]+", database):
        raise ValueError("Use explicitly named IAM resources")
    # Password passed by environment name, never as a Docker argument value.
    env = {**os.environ, "PGPASSWORD": os.environ["POSTGRES_PASSWORD"]}
    result = subprocess.run(["docker", "exec", "-e", "PGPASSWORD", "-i", container,
        "psql", "-h", "127.0.0.1", "-U", "postgres", "-d", database, "-v", "ON_ERROR_STOP=1", "-q"],
        input=role_statement(values), env=env, capture_output=True)
    if result.returncode:
        raise RuntimeError("Runtime role provisioning failed; no credential output")
    return {"roles_provisioned": len(values), "secrets_in_argv": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--container", required=True)
    parser.add_argument("--database", default="iam_secure")
    parser.add_argument("--roles-file", required=True)
    args = parser.parse_args()
    values = load_roles_file(args.roles_file)
    print(json.dumps(provision(args.container, args.database, values)))
