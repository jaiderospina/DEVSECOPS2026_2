"""Security checks for Compose JSON (Checkov does not scan Compose)."""
import argparse
import copy
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from safe_paths import REPOSITORY, artifact_roots, confined_path, write_json

EXPECTED = {
    "postgres", "identity", "permissions", "audit-service", "sync-worker",
    "audit-dispatcher", "frontend", "permissions-grid", "bootstrap-admin",
}

def validate(spec):
    services = spec["services"]
    assert set(services) == EXPECTED, "Unexpected deployment services"
    assert spec["networks"]["data"]["internal"] is True, "Database network is external"
    assert "edge" not in services["postgres"]["networks"], "Postgres on edge network"
    assert not services["postgres"].get("ports"), "Postgres is published"
    for name, service in services.items():
        assert re.fullmatch(r"[^@\s]+@sha256:[0-9a-f]{64}", service["image"]), f"{name}: unpinned image"
        assert "build" not in service, f"{name}: builds are forbidden"
        assert not service.get("privileged"), f"{name}: privileged container"
        assert service.get("read_only") is True, f"{name}: writable root"
        assert service.get("cap_drop") == ["ALL"], f"{name}: capabilities"
        assert "no-new-privileges:true" in service.get("security_opt", []), f"{name}: privilege escalation"
        assert service.get("user", "image-user") not in ("root", "0", "0:0"), f"{name}: root override"
        assert 1 <= service.get("pids_limit", 0) <= 256, f"{name}: pids limit"
        assert service.get("mem_limit"), f"{name}: memory limit"
        assert service.get("init") is True, f"{name}: PID 1 reaping"
        assert service["logging"]["options"]["max-size"], f"{name}: unlimited logs"
        assert all(port.startswith("127.0.0.1:") for port in service.get("ports", [])), f"{name}: public port"
        assert not service.get("network_mode") and not service.get("pid"), f"{name}: host namespace"
        assert not service.get("cap_add") and not service.get("devices"), f"{name}: added privileges"
        assert not any("docker.sock" in volume for volume in service.get("volumes", [])), f"{name}: Docker socket"
        for key, value in service.get("environment", {}).items():
            if key in {"DB_PASSWORD", "POSTGRES_PASSWORD", "JWT_SECRET", "MFA_ENCRYPTION_KEY", "AUDIT_INTERNAL_TOKEN", "BOOTSTRAP_ADMIN_TI_PASSWORD", "SMTP_PASSWORD"}:
                assert isinstance(value, str) and value.startswith(chr(36) + "{"), f"{name}: literal secret"
    assert services["identity"]["environment"]["SESSION_INACTIVITY_MINUTES"] == "5"
    assert services["bootstrap-admin"]["profiles"] == ["bootstrap"]
    assert services["postgres"]["user"] == "postgres", "Postgres must start non-root"
    assert services["postgres"].get("group_add") == ["${IAM_SQL_READ_GID:?required}"], "SQL read group must come from the operator's runtime configuration"

def negative_tests(spec):
    mutations = [
        ("unfrozen image", lambda s: s["services"]["identity"].update(image="iam:latest")),
        ("root override", lambda s: s["services"]["identity"].update(user="0")),
        ("privileged", lambda s: s["services"]["identity"].update(privileged=True)),
        ("writable root", lambda s: s["services"]["frontend"].update(read_only=False)),
        ("public database", lambda s: s["services"]["postgres"].update(ports=["5432:5432"])),
        ("public API", lambda s: s["services"]["identity"].update(ports=["0.0.0.0:8003:8003"])),
        ("literal secret", lambda s: s["services"]["identity"]["environment"].update(JWT_SECRET="unsafe-placeholder")),
        ("host socket", lambda s: s["services"]["frontend"].update(volumes=["/var/run/docker.sock:/var/run/docker.sock"])),
        ("root SQL group", lambda s: s["services"]["postgres"].update(group_add=["0"])),
    ]
    for label, mutate in mutations:
        candidate = copy.deepcopy(spec)
        mutate(candidate)
        try:
            validate(candidate)
        except AssertionError:
            continue
        raise AssertionError(f"Security gate accepted: {label}")
    return len(mutations)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--compose", default="orquestacion/compose.simulated.json")
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    source = confined_path(args.compose, [REPOSITORY / "orquestacion", *artifact_roots()])
    target = confined_path(args.report, artifact_roots())
    spec = json.loads(source.read_text(encoding="utf-8"))
    validate(spec)
    report = {"compose_security": "passed", "services": len(spec["services"]),
              "negative_gate_tests": negative_tests(spec), "secrets_printed": False}
    write_json(target, report)
    print(json.dumps(report))

if __name__ == "__main__":
    main()
