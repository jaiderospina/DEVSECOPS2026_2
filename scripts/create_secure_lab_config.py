"""Private, fresh credentials and a local CA; never import workstation secrets."""
import argparse
from datetime import datetime, timedelta, timezone
import ipaddress
import json
import os
from pathlib import Path
import secrets
import subprocess

from cryptography import x509
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

ROLE_VARIABLES = {
    "iam_identity": "IDENTITY_DB_PASSWORD", "iam_permissions": "PERMISSIONS_DB_PASSWORD",
    "iam_sync": "SYNC_DB_PASSWORD", "iam_audit": "AUDIT_DB_PASSWORD",
    "iam_dispatcher": "DISPATCHER_DB_PASSWORD", "iam_backup": "BACKUP_DB_PASSWORD",
}


def private_write(path, data):
    # Exclusive creation avoids replacing any existing key/configuration.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)


def create(directory):
    if hasattr(os, "getuid") and os.getuid() == 0:
        raise ValueError("Create private TLS configuration as a non-root operator")
    directory = Path(directory).absolute()
    if directory.exists() or any(parent.is_symlink() for parent in [directory, *directory.parents]):
        raise ValueError("Use a new directory without symbolic links")
    directory.mkdir(mode=0o700, parents=True)
    if os.name == "nt":
        # chmod alone does not enforce Windows ACL confidentiality.
        sid = subprocess.check_output(["whoami", "/user", "/fo", "csv", "/nh"], text=True).strip().split(",")[-1].strip('"')
        subprocess.run(["icacls", str(directory), "/inheritance:r", "/grant:r", f"*{sid}:(OI)(CI)F"], check=True, capture_output=True)
    roles = {role: secrets.token_hex(32) for role in ROLE_VARIABLES}
    values = {variable: roles[role] for role, variable in ROLE_VARIABLES.items()}
    values.update(POSTGRES_PASSWORD=secrets.token_hex(32), JWT_SECRET=secrets.token_hex(32),
                  MFA_ENCRYPTION_KEY=Fernet.generate_key().decode(), AUDIT_INTERNAL_TOKEN=secrets.token_hex(32),
                  BOOTSTRAP_ADMIN_TI_PASSWORD=secrets.token_hex(32) + "Aa1!",
                  GATEWAY_UID=str(os.getuid() if hasattr(os, "getuid") else 101),
                  GATEWAY_GID=str(os.getgid() if hasattr(os, "getgid") else 101))
    private_write(directory / "roles.json", json.dumps(roles).encode())
    private_write(directory / "runtime.env", "".join(f"{key}={value}\n" for key, value in values.items()).encode())
    private_write(directory / "backup.key", Fernet.generate_key())
    # Issue only localhost/loopback. No system trust-store changes or CA key saved.
    now = datetime.now(timezone.utc)
    ca_key = ec.generate_private_key(ec.SECP256R1())
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "IAM Secure laboratory CA")])
    ca = (x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name)
          .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
          .not_valid_before(now - timedelta(minutes=1)).not_valid_after(now + timedelta(days=31))
          .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
          .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), critical=True)
          .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
          .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
          .sign(ca_key, hashes.SHA256()))
    leaf_key = ec.generate_private_key(ec.SECP256R1())
    leaf_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    leaf = (x509.CertificateBuilder().subject_name(leaf_name).issuer_name(ca_name)
            .public_key(leaf_key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=1)).not_valid_after(now + timedelta(days=30))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), critical=False)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
            .add_extension(x509.KeyUsage(True, False, False, False, False, False, False, False, False), critical=True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(leaf_key.public_key()), critical=False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
            .sign(ca_key, hashes.SHA256()))
    private_write(directory / "ca.pem", ca.public_bytes(serialization.Encoding.PEM))
    private_write(directory / "server.pem", leaf.public_bytes(serialization.Encoding.PEM))
    tls_password = secrets.token_hex(32).encode()
    private_write(directory / "server.pass", tls_password + b"\n")
    private_write(directory / "server.key", leaf_key.private_bytes(serialization.Encoding.PEM,
                  serialization.PrivateFormat.PKCS8, serialization.BestAvailableEncryption(tls_password)))
    if os.environ.get("GITHUB_ACTIONS") == "true":
        for value in [*roles.values(), values["POSTGRES_PASSWORD"], values["JWT_SECRET"],
                      values["MFA_ENCRYPTION_KEY"], values["AUDIT_INTERNAL_TOKEN"], values["BOOTSTRAP_ADMIN_TI_PASSWORD"]]:
            print("::add-mask::" + value)
    return {"certificate_sha256": leaf.fingerprint(hashes.SHA256()).hex(),
            "ca_sha256": ca.fingerprint(hashes.SHA256()).hex(), "roles": sorted(roles),
            "certificate_days": 30, "secrets_written": True, "system_trust_modified": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory")
    args = parser.parse_args()
    print(json.dumps(create(args.directory)))
