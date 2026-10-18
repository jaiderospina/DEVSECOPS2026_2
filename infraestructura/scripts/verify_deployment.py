"""Verify a real deployment; emit only allowlisted evidence, never Docker Env."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from safe_paths import artifact_roots, confined_path, deployment_path, project_name, write_json

SCHEMA_QUERY = "SELECT to_regclass('public.permisos_usuario_compania'), to_regclass('public.cargas_usuarios'), to_regclass('public.cargas_usuario_filas');"
ADMIN_QUERY = "SELECT count(*) FROM usuarios_plataforma WHERE id_externo='1051';"


def docker_probe_arguments(args):
    """Rebuild an independent, canonical vector; never execute the caller's list."""
    if not args:
        raise ValueError("Missing Docker operation")
    if args[0] == "inspect" and 1 < len(args) <= 10:
        if all(re.fullmatch(r"[0-9a-f]{64}", value) for value in args[1:]):
            return ["inspect", *args[1:]]
    if len(args) == 4 and args[0] == "exec" and args[2:] == ["id", "-u"]:
        if re.fullmatch(r"[0-9a-f]{64}", args[1]):
            return ["exec", args[1], "id", "-u"]
    if len(args) == 3 and args[:2] == ["image", "inspect"]:
        if re.fullmatch(r"sha256:[0-9a-f]{64}", args[2]):
            return ["image", "inspect", args[2]]
    if len(args) >= 11 and args[:2] == ["compose", "--project-name"]:
        project_name(args[2])
        root = deployment_path(args[4])
        prefix = ["compose", "--project-name", args[2], "--project-directory", str(root),
                  "--env-file", str(root / ".env"), "-f", str(root / "compose.simulated.json")]
        probes = [["ps", "-q"]]
        sql = ["exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "iam_secure", "-At"]
        probes += [sql + ["-v", "ON_ERROR_STOP=1", "-c", SCHEMA_QUERY], sql + ["-c", ADMIN_QUERY]]
        if args[:9] == prefix:
            for probe in probes:
                if args[9:] == probe:
                    return prefix + probe
    raise ValueError("Docker arguments are outside the verifier's read/probe allowlist")


def validate_docker_arguments(args):
    docker_probe_arguments(args)


def command(args):
    canonical = docker_probe_arguments(args)
    executable = shutil.which("docker")
    if not executable:
        raise ValueError("Docker executable not found")
    # The executable is fixed; no shell, CLI-supplied executable, or arbitrary subcommand.
    result = subprocess.run([executable, *canonical], check=True, text=True,
                            capture_output=True, timeout=60, shell=False)
    return result.stdout.strip()

def http_status(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--deploy-dir", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--expect", help="Earlier evidence for persistence verification")
    args = parser.parse_args()
    project_name(args.project)
    root = deployment_path(args.deploy_dir)
    env = confined_path(root / ".env", [root])
    source = confined_path(root / "compose.simulated.json", [root])
    target = confined_path(args.report, artifact_roots())
    previous_path = confined_path(args.expect, artifact_roots()) if args.expect else None
    assert env.stat().st_mode & 0o777 == 0o600, "Runtime secrets must be private"
    spec = json.loads(source.read_text())
    compose = ["compose", "--project-name", args.project,
               "--project-directory", str(root), "--env-file", str(env),
               "-f", str(root / "compose.simulated.json")]
    ids = command(compose + ["ps", "-q"]).splitlines()
    records = json.loads(command(["inspect", *ids]))
    expected = set(spec["services"]) - {"bootstrap-admin"}
    assert len(records) == len(expected), "Unexpected active container count"
    evidence = []
    found = set()
    for container in records:
        name = container["Config"]["Labels"]["com.docker.compose.service"]
        assert name in expected and name not in found
        found.add(name)
        state = container["State"]
        host = container["HostConfig"]
        assert state["Running"] and container["RestartCount"] == 0, f"{name}: unstable"
        if "healthcheck" in spec["services"][name]:
            assert state["Health"]["Status"] == "healthy", f"{name}: unhealthy"
        assert host["ReadonlyRootfs"] and "ALL" in host["CapDrop"], f"{name}: root filesystem/capabilities"
        assert "no-new-privileges:true" in host["SecurityOpt"], f"{name}: escalation"
        assert not host["Privileged"] and host["PidsLimit"] > 0 and host["Memory"] > 0
        for bindings in (host["PortBindings"] or {}).values():
            assert all(binding["HostIp"] == "127.0.0.1" for binding in bindings), f"{name}: exposed port"
        if name == "postgres":
            assert not host["PortBindings"], "Postgres is exposed"
            groups = host.get("GroupAdd", [])
            assert len(groups) == 1 and re.fullmatch(r"[1-9][0-9]*", str(groups[0])), "Postgres SQL group must be non-root"
            assert any(m["Type"] == "volume" and m["Destination"] == "/var/lib/postgresql/data" for m in container["Mounts"])
        uid = int(command(["exec", container["Id"], "id", "-u"]))
        assert uid > 0, f"{name}: effective root UID"
        image = json.loads(command(["image", "inspect", container["Image"]]))[0]
        digest = spec["services"][name]["image"].split("@")[1]
        assert any(d.endswith("@" + digest) for d in image["RepoDigests"]), f"{name}: digest mismatch"
        evidence.append({"service": name, "running": True, "health": state.get("Health", {}).get("Status", "not applicable"),
                         "effective_uid": uid, "restart_count": container["RestartCount"],
                         "read_only": True, "capabilities_dropped": True, "image_digest": digest})
    assert found == expected
    schema = command(compose + ["exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "iam_secure", "-At", "-v", "ON_ERROR_STOP=1", "-c",
        SCHEMA_QUERY])
    assert schema == "permisos_usuario_compania|cargas_usuarios|cargas_usuario_filas"
    admin_count = command(compose + ["exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "iam_secure", "-At", "-c",
        ADMIN_QUERY])
    assert admin_count == "1", "Bootstrap must create exactly one academic ADMIN_TI"
    urls = [
        ("frontend", "http://127.0.0.1:5173/", 200),
        ("grid", "http://127.0.0.1:5176/", 200),
        ("identity", "http://127.0.0.1:8003/", 200),
        ("permissions", "http://127.0.0.1:8005/", 200),
        ("audit", "http://127.0.0.1:8004/health", 200),
        ("identity_auth_gate", "http://127.0.0.1:8003/auth/me", 401),
        ("bulk_auth_gate", "http://127.0.0.1:8003/usuarios/cargas?compania_id=1", 401),
        ("permissions_auth_gate", "http://127.0.0.1:8005/v1/companies", 401),
    ]
    http = []
    for label, url, expected_status in urls:
        actual = http_status(url)
        assert actual == expected_status, f"{label}: expected {expected_status}, got {actual}"
        http.append({"check": label, "status": actual})
    report = {"project": args.project, "containers": sorted(evidence, key=lambda x:x["service"]),
              "http_checks": http, "schema": schema.split("|"), "bootstrap_admin_count": int(admin_count),
              "runtime_env_mode": "0600", "secrets_in_evidence": False,
              "persistence_verified": bool(args.expect)}
    if args.expect:
        previous = json.loads(previous_path.read_text())
        assert previous["project"] == args.project
        assert previous["schema"] == report["schema"]
        assert previous["bootstrap_admin_count"] == report["bootstrap_admin_count"]
    write_json(target, report)
    print("Runtime verification passed: 8 containers, 8 HTTP checks; no secrets emitted.")

if __name__ == "__main__":
    main()
