"""Actual TLS/roles/MFA/backup/load lab. Own project and volume, no workstation data."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import secrets
import socket
import ssl
import subprocess
import time
from uuid import uuid4

from cryptography.fernet import Fernet
import httpx
import jwt
import pyotp
from pwdlib import PasswordHash

from create_secure_lab_config import create
from encrypted_backup import backup, restore
from provision_runtime_roles import provision
from safe_paths import write_json, confined_path, artifact_roots

ROOT = Path(__file__).resolve().parents[1]


def validate(project, output, keep=False):
    if not re.fullmatch(r"iam-stride-[a-z0-9][a-z0-9-]{1,35}", project):
        raise ValueError("Use a dedicated iam-stride-* laboratory project")
    output = confined_path(output, artifact_roots())
    existing = subprocess.check_output(["docker", "ps", "-aq", "--filter", "label=com.docker.compose.project=" + project], text=True).strip()
    if existing:
        raise ValueError("Existing lab requires explicit operator inspection")
    if subprocess.run(["docker", "volume", "inspect", project+"_secure_lab_data"],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        raise ValueError("Existing lab volume must be preserved and inspected")
    # Fixed loopback endpoints are intentional; never replace an occupied port.
    for port in (8443, 8444, 8445, 8446):
        with socket.socket() as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                raise ValueError("Laboratory TLS port already occupied")
    before = set(subprocess.check_output(["docker", "ps", "-q", "--no-trunc"], text=True).split())
    private = ROOT / ".private" / (project + "-" + uuid4().hex[:8])
    config_receipt = create(private)
    values = dict(line.split("=", 1) for line in (private / "runtime.env").read_text().splitlines())
    env = {**os.environ, **values, "IAM_LAB_PRIVATE_DIR": str(private).replace("\\", "/")}
    os.environ.update(values)
    roles = json.loads((private / "roles.json").read_text())
    compose = ["docker", "compose", "--project-name", project, "--project-directory", str(ROOT),
               "--env-file", str(private / "runtime.env"), "-f", str(ROOT / "orquestacion/compose.secure-lab.json")]
    def call(args, **kwargs):
        return subprocess.run(args, env=env, check=True, **kwargs)
    def pg(statement, database="iam_secure"):
        return call(compose + ["exec", "-T", "postgres", "psql", "-U", "postgres", "-d", database,
                               "-Atq", "-v", "ON_ERROR_STOP=1"], input=statement.encode(), capture_output=True).stdout.strip()
    result = {"project": project, "normal_compose_used": False, "normal_database_used": False,
              "certificate": config_receipt, "checks": {}, "cleanup_completed": False}
    result["source_commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    result["source_worktree_dirty"] = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    result["repository"] = os.environ.get("GITHUB_REPOSITORY", "local-worktree")
    result["measured_at_utc"] = datetime.now(timezone.utc).isoformat()
    started = False
    try:
        spec = json.loads(call(compose + ["config", "--format", "json"], capture_output=True, text=True).stdout)
        for name, service in spec["services"].items():
            if name != "gateway":
                assert not service.get("ports"), "A private backend published a port"
            if name != "postgres" and "DB_USER" in service.get("environment", {}):
                assert service["environment"]["DB_USER"] != "postgres"
        assert set(spec["services"]["gateway"].get("environment", {})).isdisjoint(values)
        result["checks"]["private_backends_and_separate_runtime_roles"] = True
        call(compose + ["build"], stdout=subprocess.DEVNULL)
        started = True
        call(compose + ["up", "-d", "--wait", "--wait-timeout", "90", "postgres"], stdout=subprocess.DEVNULL)
        pg_name = call(compose + ["ps", "-q", "postgres"], capture_output=True, text=True).stdout.strip()
        container = call(["docker", "inspect", pg_name, "--format", "{{.Name}}"], capture_output=True, text=True).stdout.strip().lstrip("/")
        result["roles"] = provision(container, "iam_secure", roles)
        call(compose+["run","--build","--rm","--no-deps","bootstrap-admin"], stdout=subprocess.DEVNULL)
        assert pg("SELECT count(*) FROM usuario_roles_plataforma ur JOIN roles_plataforma r ON r.id=ur.rol_id WHERE r.nombre='ADMIN_TI'") == b"1"
        result["checks"]["bootstrap_with_restricted_identity_role"] = True
        password = secrets.token_urlsafe(24)
        password_hash = PasswordHash.recommended().hash(password)
        target_jti = str(uuid4())
        mfa = {uid: pyotp.random_base32() for uid in [1, 2]}
        cipher = {uid: Fernet(values["MFA_ENCRYPTION_KEY"].encode()).encrypt(secret.encode()).decode()
                  for uid, secret in mfa.items()}
        # Synthetic fixture only, and psql output is not archived.
        pg(f"""
            TRUNCATE auditoria_outbox, usuarios_plataforma, companias RESTART IDENTITY CASCADE;
            INSERT INTO companias(id,codigo,nombre) VALUES (1,'TLS-LAB','Synthetic lab');
            INSERT INTO usuarios_plataforma(id,nombre,email) VALUES
                (1,'Synthetic Support','support@example.org'),(2,'Synthetic Leader','leader@example.org');
            INSERT INTO credenciales(usuario_id,password_hash,requiere_cambio_password,password_expira_en)
                VALUES (1,'{password_hash}',FALSE,NOW()+INTERVAL '1 day'),
                       (2,'{password_hash}',FALSE,NOW()+INTERVAL '1 day');
            INSERT INTO usuario_roles_plataforma(usuario_id,rol_id)
                SELECT 1,id FROM roles_plataforma WHERE nombre='ADMIN_SOPORTE';
            INSERT INTO usuario_roles_plataforma(usuario_id,rol_id)
                SELECT 2,id FROM roles_plataforma WHERE nombre='LIDER_FACTURACION';
            INSERT INTO usuario_companias_plataforma(usuario_id,compania_id) VALUES (1,1),(2,1);
            INSERT INTO mfa_totp(usuario_id,secreto_cifrado,activo) VALUES (1,'{cipher[1]}',TRUE),(2,'{cipher[2]}',TRUE);
            INSERT INTO sesiones(usuario_id,jti,fecha_expiracion) VALUES (2,'{target_jti}',NOW()+INTERVAL '1 hour');
            SELECT setval(pg_get_serial_sequence('usuarios_plataforma','id'),2);
            SELECT setval(pg_get_serial_sequence('companias','id'),1);
        """)
        call(compose + ["up", "-d"], stdout=subprocess.DEVNULL)
        container_ids = call(compose+["ps","-q"], capture_output=True, text=True).stdout.split()
        for owned_id in container_ids:
            uid = call(["docker","exec",owned_id,"id","-u"], capture_output=True, text=True).stdout.strip()
            assert int(uid)>0
        result["checks"]["runtime_containers_non_root"] = True
        context = ssl.create_default_context(cafile=str(private / "ca.pem"))
        with httpx.Client(verify=context, trust_env=False, timeout=15) as client:
            deadline = time.monotonic() + 90
            last_probe = "starting"
            while True:
                try:
                    statuses = [client.get(f"https://localhost:{port}/").status_code for port in [8443,8444,8445,8446]]
                    last_probe = str(statuses)
                    if all(status == 200 for status in statuses):
                        break
                except httpx.HTTPError as error:
                    # Readiness probes are public GET /, without credentials.
                    last_probe = type(error).__name__ + ": " + str(error)
                if time.monotonic() > deadline:
                    raise RuntimeError("TLS laboratory endpoints did not become ready: " + last_probe)
                time.sleep(1)
            result["checks"]["four_verified_https_endpoints"] = True
            with socket.create_connection(("127.0.0.1",8445),timeout=10) as raw:
                with context.wrap_socket(raw,server_hostname="localhost") as secure:
                    result["tls_version"] = secure.version()
                    assert secure.version() in ("TLSv1.2","TLSv1.3")
            try:
                with httpx.Client(trust_env=False,timeout=5) as untrusted:
                    untrusted.get("https://localhost:8445/")
            except httpx.ConnectError:
                result["checks"]["unknown_ca_rejected"] = True
            else:
                raise AssertionError("Client accepted an untrusted lab CA")
            assert client.get("http://localhost:8445/").status_code == 400
            assert client.get("https://localhost:8445/",headers={"Host":"unexpected.invalid"}).status_code == 403
            result["checks"]["plaintext_and_unknown_hosts_rejected"] = True
            login = client.post("https://localhost:8445/auth/login",json={"email":"support@example.org","password":password})
            assert login.status_code == 200, "First factor failed"
            assert "access_token" not in login.json()
            verified = client.post("https://localhost:8445/auth/mfa/verificar-login",json={
                "desafio":login.json()["desafio_mfa"],"codigo":pyotp.TOTP(mfa[1]).now()})
            assert verified.status_code == 200, "MFA failed"
            headers = {"Authorization":"Bearer "+verified.json()["access_token"]}
            assert client.get("https://localhost:8446/v1/companies",headers=headers).status_code == 200
            result["checks"]["real_mfa_and_restricted_permissions_https"] = True
            target_token = jwt.encode({"sub":"2","jti":target_jti,"exp":datetime.now(timezone.utc)+timedelta(hours=1)},values["JWT_SECRET"],algorithm="HS256")
            target_headers = {"Authorization":"Bearer "+target_token}
            assert client.get("https://localhost:8445/auth/me",headers=target_headers).status_code == 200
            reset = client.post("https://localhost:8445/usuarios/2/mfa/restablecer",headers=headers)
            assert reset.status_code == 200, "Restricted-role MFA reset failed"
            assert client.get("https://localhost:8445/auth/me",headers=target_headers).status_code == 401
            for _ in range(30):
                if pg("SELECT count(*) FROM auditoria_eventos WHERE evento='MFA_RESTABLECIDO_ADMIN'") == b"1":
                    break
                time.sleep(1)
            else:
                raise AssertionError("Reset event was not delivered to append-only audit")
            assert pg("SELECT count(*) FROM auditoria_outbox WHERE estado='FALLIDO'") == b"0"
            result["checks"]["reset_revocation_and_real_audit_delivery"] = True
            # Authentic encryption + actual restore into a separate fresh database.
            env["PGPASSWORD"] = os.environ["PGPASSWORD"] = roles["iam_backup"]
            encrypted = private / "backups" / "lab.dump.enc"
            result["backup"] = backup(container,"iam_secure",private/"backup.key",encrypted)
            pg("CREATE DATABASE iam_restore_stride",database="postgres")
            env["PGPASSWORD"] = os.environ["PGPASSWORD"] = values["POSTGRES_PASSWORD"]
            result["restore"] = restore(container,"iam_restore_stride",private/"backup.key",encrypted)
            for table in ["usuarios_plataforma","mfa_totp","credenciales","usuario_roles_plataforma"]:
                assert pg(f"SELECT count(*) FROM {table}") == pg(f"SELECT count(*) FROM {table}","iam_restore_stride")
            restored_cipher = pg("SELECT secreto_cifrado FROM mfa_totp WHERE usuario_id=1", "iam_restore_stride")
            assert Fernet(values["MFA_ENCRYPTION_KEY"].encode()).decrypt(restored_cipher) == mfa[1].encode()
            assert pg("SELECT count(*) FROM pg_auth_members WHERE member IN (SELECT oid FROM pg_roles WHERE rolname LIKE 'iam_%')") == b"0"
            result["checks"]["encrypted_backup_restored_and_acl_reapplied"] = True
            result["checks"]["restored_mfa_decryptable_with_preserved_key"] = True
            # A forged XFF must not bypass the gateway's real-client bucket.
            def attempt(index):
                response = client.post("https://localhost:8445/auth/login",headers={"X-Forwarded-For":f"192.0.2.{index+1}",
                    "Origin":"https://localhost:8443"},json={"email":"support@example.org","password":"invalid-synthetic-password"})
                if response.status_code == 429:
                    assert response.headers.get("retry-after") == "6"
                    assert response.headers.get("access-control-allow-origin") == "https://localhost:8443"
                    assert set(response.json()) == {"detail"}
                return response.status_code
            with ThreadPoolExecutor(max_workers=12) as pool:
                statuses = list(pool.map(attempt,range(30)))
            assert statuses.count(429) >= 20
            assert not any(status >= 500 for status in statuses)
            result["load"] = {"requests":len(statuses),"throttled":statuses.count(429),"server_errors":0,
                              "forged_forwarded_headers_used":True,"max_auth_connections":2}
            result["checks"]["auth_load_throttled_before_backend"] = True
        result["passed"] = True
    finally:
        if started and not keep:
            # Only this validated project/its own volume; never prune or normal Compose.
            call(compose+["down","--volumes","--remove-orphans"],stdout=subprocess.DEVNULL)
            after=set(subprocess.check_output(["docker","ps","-q","--no-trunc"],text=True).split())
            assert before.issubset(after), "An unrelated running container was removed"
            result["cleanup_completed"]=True
            result["unrelated_container_ids_preserved"]=True
        else:
            result["private_runtime_directory"] = str(private)
        write_json(output,result)
    return result


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--project",required=True)
    parser.add_argument("--output",default=str(ROOT/"reports/stride-secure-lab.json"))
    parser.add_argument("--keep",action="store_true")
    args=parser.parse_args()
    result=validate(args.project,args.output,args.keep)
    print(json.dumps({"passed":result["passed"],"checks":len(result["checks"]),"cleanup_completed":result["cleanup_completed"]}))
