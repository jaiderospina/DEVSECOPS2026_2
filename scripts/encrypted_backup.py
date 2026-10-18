"""Authenticated encrypted PostgreSQL backup; restore only into an empty lab DB."""
import argparse
import os
from pathlib import Path
import re
import subprocess

from cryptography.fernet import Fernet

MAX_BYTES = 64 * 1024 * 1024


def encrypt_dump(data, key):
    if not data.startswith(b"PGDMP") or len(data) > MAX_BYTES:
        raise ValueError("Expected a bounded PostgreSQL custom-format backup")
    return Fernet(key).encrypt(data)


def decrypt_dump(data, key):
    if len(data) > MAX_BYTES * 2:
        raise ValueError("Encrypted backup exceeds laboratory limit")
    plain = Fernet(key).decrypt(data)
    if not plain.startswith(b"PGDMP") or len(plain) > MAX_BYTES:
        raise ValueError("Invalid PostgreSQL backup format")
    return plain


def docker_pg(container, command, *, bounded=False, **kwargs):
    if not re.fullmatch(r"iam-[a-z0-9_-]+", container):
        raise ValueError("Use an explicitly named IAM PostgreSQL container")
    if not os.environ.get("PGPASSWORD"):
        raise ValueError("Supply the database credential through PGPASSWORD")
    args = ["docker", "exec", "-e", "PGPASSWORD", "-i", container, *command]
    if bounded:
        with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as process:
            data = process.stdout.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                process.kill()
                raise ValueError("Database exceeds the 64 MiB laboratory backup limit")
            if process.wait(timeout=120):
                raise RuntimeError("PostgreSQL backup failed; credential output suppressed")
            return data
    result = subprocess.run(args, capture_output=True, timeout=120, **kwargs)
    if result.returncode:
        raise RuntimeError("PostgreSQL operation failed; credential output suppressed")
    return result.stdout


def backup(container, database, key_path, output):
    if not re.fullmatch(r"iam_[a-z0-9_]+", database):
        raise ValueError("Use a named IAM database")
    key_path, output = Path(key_path).absolute(), Path(output).absolute()
    if output.exists() or output.parent == key_path.parent or key_path.is_relative_to(output.parent):
        raise ValueError("Store a new backup separately from its encryption key")
    if any(parent.is_symlink() for parent in [output, *output.parents, key_path]):
        raise ValueError("Symbolic links are not accepted for keys or output")
    data = docker_pg(container, ["pg_dump", "-h", "127.0.0.1", "-U", "iam_backup", "-d", database,
                                 "--format=custom", "--no-owner", "--no-acl"], bounded=True)
    encrypted = encrypt_dump(data, key_path.read_bytes())
    output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(encrypted)
    return {"encrypted": True, "bytes": len(encrypted), "plaintext_written": False}


def restore(container, database, key_path, source):
    if not re.fullmatch(r"iam_restore_[a-z0-9_]+", database):
        raise ValueError("Restore requires a separate iam_restore_* database")
    data = decrypt_dump(Path(source).read_bytes(), Path(key_path).read_bytes())
    count = docker_pg(container, ["psql", "-h", "127.0.0.1", "-U", "postgres", "-d", database,
        "-Atq", "-v", "ON_ERROR_STOP=1", "-c",
        "SELECT count(*) FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema')"])
    if count.strip() != b"0":
        raise ValueError("Restore target is not empty")
    docker_pg(container, ["pg_restore", "-h", "127.0.0.1", "-U", "postgres", "-d", database,
        "--no-owner", "--no-acl", "--exit-on-error", "--single-transaction"], input=data)
    # Reapply the versioned ACL policy before treating restored data as usable.
    policy = Path(__file__).resolve().parents[1] / "postgres-init/13-runtime-roles.sql"
    docker_pg(container, ["psql", "-h", "127.0.0.1", "-U", "postgres", "-d", database,
        "-q", "-v", "ON_ERROR_STOP=1"], input=policy.read_bytes())
    return {"restored": True, "acl_policy_reapplied": True, "normal_database_used": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["backup", "restore"])
    parser.add_argument("--container", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--key-file", required=True)
    parser.add_argument("--file", required=True)
    args = parser.parse_args()
    function = backup if args.mode == "backup" else restore
    import json
    print(json.dumps(function(args.container, args.database, args.key_file, args.file)))
