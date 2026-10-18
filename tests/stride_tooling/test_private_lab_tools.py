"""Security failure paths: no credential injection, plaintext backup or key replacement."""
import importlib.util
import json
import os
from pathlib import Path
import secrets
import sys

from cryptography import x509
from cryptography.fernet import Fernet, InvalidToken
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import create_secure_lab_config as config
import encrypted_backup as encrypted
import provision_runtime_roles as roles
import validate_secure_lab as lab


@pytest.mark.parametrize("path_kind", ["outside", "traversal", "wrong-name"])
def test_role_file_read_is_confined_to_named_private_credentials(tmp_path, monkeypatch, path_kind):
    monkeypatch.setattr(roles,"REPOSITORY",tmp_path)
    private=tmp_path/".private";private.mkdir()
    paths={"outside":tmp_path/"roles.json", "traversal":private/".."/"roles.json",
           "wrong-name":private/"runtime.env"}
    paths[path_kind].write_text(json.dumps({role:secrets.token_hex(32) for role in roles.ROLES}))
    with pytest.raises(ValueError):
        roles.load_roles_file(paths[path_kind])


def test_role_file_uses_existing_private_schema(tmp_path, monkeypatch):
    monkeypatch.setattr(roles,"REPOSITORY",tmp_path)
    private=tmp_path/".private"/"fixture";private.mkdir(parents=True)
    values={role:secrets.token_hex(32) for role in roles.ROLES}
    path=private/"roles.json";path.write_text(json.dumps(values))
    assert roles.load_roles_file(path)==values


def test_role_file_size_is_bounded_before_reading_json(tmp_path, monkeypatch):
    monkeypatch.setattr(roles,"REPOSITORY",tmp_path)
    private=tmp_path/".private";private.mkdir()
    path=private/"roles.json";path.write_text("x"*16385)
    with pytest.raises(ValueError):
        roles.load_roles_file(path)


@pytest.mark.parametrize("values", [[], {}, {"iam_identity":"a"*64},
    {role:"a"*64 for role in roles.ROLES},
    {role:"';ALTER ROLE postgres SUPERUSER;--" for role in roles.ROLES},
    {role:[] for role in roles.ROLES}])
def test_role_credentials_cannot_change_sql_or_reuse_secrets(values):
    with pytest.raises(ValueError):
        roles.role_statement(values)


def test_runtime_sql_is_atomic_and_never_assigns_privileged_membership():
    values = {role:secrets.token_hex(32) for role in roles.ROLES}
    statement = roles.role_statement(values)
    assert statement.startswith(b"BEGIN;") and statement.endswith(b"COMMIT;\n")
    assert b"SET LOCAL log_statement='none'" in statement
    assert b"Runtime role membership requires operator review" in statement
    assert b"GRANT postgres" not in statement and b"SUPERUSER" not in statement


def test_private_config_has_distinct_secrets_and_scoped_certificate(tmp_path):
    target = tmp_path / "new-private-config"
    receipt = config.create(target)
    values = json.loads((target / "roles.json").read_text())
    assert set(values) == roles.ROLES and len(set(values.values())) == 6
    assert receipt["system_trust_modified"] is False
    cert = x509.load_pem_x509_certificate((target / "server.pem").read_bytes())
    assert cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca is False
    assert "localhost" in cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.DNSName)
    assert not (target / "ca.key").exists()
    assert b"ENCRYPTED PRIVATE KEY" in (target / "server.key").read_bytes()
    runtime = (target / "runtime.env").read_text()
    assert (target / "backup.key").read_text() not in runtime
    password = dict(line.split("=",1) for line in runtime.splitlines())["BOOTSTRAP_ADMIN_TI_PASSWORD"]
    assert len(password) >= 12
    assert any(char.isupper() for char in password) and any(char.islower() for char in password)
    assert any(char.isdigit() for char in password) and any(not char.isalnum() for char in password)
    if os.name != "nt":
        assert target.stat().st_mode & 0o077 == 0
        assert (target / "server.key").stat().st_mode & 0o077 == 0
    with pytest.raises(ValueError):
        config.create(target)


def test_exclusive_key_write_preserves_existing_material(tmp_path):
    path = tmp_path / "existing.key"
    path.write_bytes(b"existing-private-material")
    with pytest.raises(FileExistsError):
        config.private_write(path,b"replacement")
    assert path.read_bytes() == b"existing-private-material"


def test_backup_authenticated_encryption_rejects_tampering_and_wrong_key():
    key = Fernet.generate_key()
    plain = b"PGDMP-synthetic-private-fixture"
    blob = encrypted.encrypt_dump(plain,key)
    assert plain not in blob and encrypted.decrypt_dump(blob,key) == plain
    with pytest.raises(InvalidToken):
        encrypted.decrypt_dump(blob,Fernet.generate_key())
    with pytest.raises(InvalidToken):
        encrypted.decrypt_dump(blob[:-4]+b"AAAA",key)


@pytest.mark.parametrize("plain", [b"", b"password-secret", b"SQL instead of a custom dump"])
def test_non_postgresql_data_is_rejected(plain):
    with pytest.raises(ValueError):
        encrypted.encrypt_dump(plain,Fernet.generate_key())


def test_backup_size_limit_is_enforced_before_crypto(monkeypatch):
    monkeypatch.setattr(encrypted,"MAX_BYTES",5)
    with pytest.raises(ValueError):
        encrypted.encrypt_dump(b"PGDMPtoo-large",Fernet.generate_key())
    with pytest.raises(ValueError):
        encrypted.decrypt_dump(b"x"*11,Fernet.generate_key())


def test_restore_cannot_target_normal_database(monkeypatch, tmp_path):
    calls=[]
    monkeypatch.setattr(encrypted,"docker_pg",lambda *a,**k:calls.append((a,k)))
    with pytest.raises(ValueError):
        encrypted.restore("iam-secure-postgres","iam_secure",tmp_path/"key",tmp_path/"file")
    assert calls == []


def test_restore_rejects_nonempty_target_before_writing(monkeypatch,tmp_path):
    key=Fernet.generate_key();(tmp_path/"key").write_bytes(key)
    (tmp_path/"dump").write_bytes(encrypted.encrypt_dump(b"PGDMPfixture",key))
    calls=[]
    def run(*a,**k):
        calls.append((a,k));return b"1\n"
    monkeypatch.setattr(encrypted,"docker_pg",run)
    with pytest.raises(ValueError):
        encrypted.restore("iam-stride-fixture-postgres","iam_restore_fixture",tmp_path/"key",tmp_path/"dump")
    assert len(calls)==1 and "psql" in calls[0][0][1]


@pytest.mark.parametrize("container,database", [("unrelated-postgres","iam_secure"),
    ("iam-stride-fixture;rm","iam_secure"),("iam-stride-fixture","postgres;DROP DATABASE x")])
def test_provisioning_rejects_ambiguous_resources(container,database):
    with pytest.raises(ValueError):
        roles.provision(container,database,{})


@pytest.mark.parametrize("project", ["iam-secure", "normal-project", "iam-stride-../other"])
def test_lab_refuses_normal_or_ambiguous_project(project):
    with pytest.raises(ValueError):
        lab.validate(project,ROOT/"reports/rejected.json")


def test_lab_rejects_unsafe_report_path_before_any_docker_call(monkeypatch,tmp_path):
    monkeypatch.setattr(lab.subprocess,"check_output",lambda *a,**k:pytest.fail("Docker called before report confinement"))
    with pytest.raises(ValueError):
        lab.validate("iam-stride-fixture",tmp_path/"outside.json")
