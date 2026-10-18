import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import safe_paths


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "infraestructura/scripts" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runtime = load_script("verify_deployment")


class AutomationBoundaries(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.workspace = self.root / "private-runner"
        self.workspace.mkdir()
        self.environment = patch.dict(os.environ, {"RUNNER_TEMP": str(self.workspace)})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.victim = self.root / "victim.json"
        self.victim.write_text("untouched", encoding="utf-8")

    def cli(self, script, *arguments):
        return subprocess.run([sys.executable, str(ROOT / script), *map(str, arguments)],
                              cwd=ROOT, capture_output=True, text=True, check=False, timeout=10)

    def symlink(self, target, link):
        try:
            link.symlink_to(target, target_is_directory=target.is_dir())
        except (OSError, NotImplementedError) as error:
            self.skipTest("Symlink creation unavailable: " + str(error))

    def test_parent_traversal_is_rejected_even_when_it_returns_inside(self):
        with self.assertRaises(ValueError):
            safe_paths.confined_path(self.workspace / "nested/../report.json", [self.workspace])

    def test_absolute_escape_and_similar_prefix_are_rejected(self):
        for candidate in (self.victim, self.root / "private-runner-other/report.json"):
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                safe_paths.confined_path(candidate, [self.workspace])

    def test_report_symlink_does_not_overwrite_victim(self):
        link = self.workspace / "report.json"
        self.symlink(self.victim, link)
        with self.assertRaises(ValueError):
            safe_paths.write_json(link, {"changed": True})
        self.assertEqual(self.victim.read_text(), "untouched")

    def test_parent_symlink_does_not_escape(self):
        link = self.workspace / "linked-parent"
        self.symlink(self.root, link)
        with self.assertRaises(ValueError):
            safe_paths.write_json(link / "victim.json", {"changed": True})
        self.assertEqual(self.victim.read_text(), "untouched")

    def test_atomic_report_replacement_does_not_modify_hardlink_source(self):
        link = self.workspace / "report.json"
        try:
            os.link(self.victim, link)
        except PermissionError:
            if os.name == "nt":
                self.skipTest("Windows sandbox does not permit hardlink creation")
            raise
        safe_paths.write_json(link, {"passed": True})
        self.assertEqual(self.victim.read_text(), "untouched")
        self.assertTrue(json.loads(link.read_text())["passed"])

    def test_config_escape_fails_before_creating_secret_file(self):
        result = self.cli("infraestructura/scripts/create_test_config.py", "--output", self.victim,
                          "--deploy-dir", self.workspace / "deployment", "--project", "iam-ci-123-1")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.victim.read_text(), "untouched")

    def test_config_is_private_exclusive_and_not_printed(self):
        output = self.workspace / "vars.json"
        arguments = ("--output", output, "--deploy-dir", self.workspace / "deployment", "--project", "iam-ci-123-1")
        first = self.cli("infraestructura/scripts/create_test_config.py", *arguments)
        self.assertEqual(first.returncode, 0, first.stderr)
        original = output.read_bytes()
        config = json.loads(original)
        self.assertNotIn(config["iam_postgres_password"], first.stdout + first.stderr)
        self.assertEqual(config["iam_deploy_dir"], str(self.workspace / "deployment"))
        if os.name != "nt":
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        second = self.cli("infraestructura/scripts/create_test_config.py", *arguments)
        self.assertNotEqual(second.returncode, 0)
        self.assertEqual(output.read_bytes(), original)

    def test_invalid_project_cannot_become_docker_option_or_shell(self):
        for project in ("--help", "iam-ci-1-1;touch /tmp/victim", "iam-ci-١-١"):
            with self.subTest(project=project), self.assertRaises(ValueError):
                safe_paths.project_name(project, ci_only=True)

    def test_docker_rejects_other_programs_subcommands_and_option_ids(self):
        candidates = [["sh", "-c", "touch victim"], ["rm", "-f", "victim"],
                      ["inspect", "--format=malicious"], ["exec", "--privileged", "id", "-u"],
                      ["image", "inspect", "--help"]]
        with patch.object(runtime.subprocess, "run") as execute:
            for candidate in candidates:
                with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                    runtime.command(candidate)
            execute.assert_not_called()

    def test_docker_valid_probe_uses_fixed_executable_and_no_shell(self):
        container = "a" * 64
        with patch.object(runtime.shutil, "which", return_value="/usr/bin/docker"), \
                patch.object(runtime.subprocess, "run") as execute:
            execute.return_value.stdout = "1001\n"
            self.assertEqual(runtime.command(["exec", container, "id", "-u"]), "1001")
            self.assertEqual(execute.call_args.args[0], ["/usr/bin/docker", "exec", container, "id", "-u"])
            self.assertFalse(execute.call_args.kwargs["shell"])

    def test_docker_executes_validated_snapshot_even_if_caller_changes_arguments(self):
        arguments = ["exec", "a" * 64, "id", "-u"]

        def executable(_name):
            arguments[:] = ["rm", "-f", "victim"]
            return "/usr/bin/docker"

        with patch.object(runtime.shutil, "which", side_effect=executable), \
                patch.object(runtime.subprocess, "run") as execute:
            execute.return_value.stdout = "1001"
            runtime.command(arguments)
            self.assertEqual(execute.call_args.args[0], ["/usr/bin/docker", "exec", "a" * 64, "id", "-u"])

    def test_compose_canonical_vector_only_allows_the_three_fixed_probes(self):
        deployed = self.workspace / "deployment"
        prefix = ["compose", "--project-name", "iam-ci-123-1", "--project-directory", str(deployed),
                  "--env-file", str(deployed / ".env"), "-f", str(deployed / "compose.simulated.json")]
        sql = ["exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "iam_secure", "-At"]
        for probe in (["ps", "-q"], sql + ["-c", runtime.ADMIN_QUERY],
                      sql + ["-v", "ON_ERROR_STOP=1", "-c", runtime.SCHEMA_QUERY]):
            arguments = prefix + probe
            canonical = runtime.docker_probe_arguments(arguments)
            self.assertEqual(canonical, arguments)
            self.assertIsNot(canonical, arguments)
        for probe in (["down"], ["ps", "-q", "--all"], sql + ["-c", "DROP DATABASE iam_secure;"]):
            with self.assertRaises(ValueError):
                runtime.docker_probe_arguments(prefix + probe)

    def test_compose_blocks_input_and_output_outside_allowed_roots(self):
        source = self.workspace / "compose.json"
        source.write_bytes((ROOT / "orquestacion/compose.simulated.json").read_bytes())
        result = self.cli("infraestructura/scripts/check_compose.py", "--compose", source, "--report", self.victim)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.victim.read_text(), "untouched")
        outside = self.root / "compose.json"
        outside.write_bytes(source.read_bytes())
        result = self.cli("infraestructura/scripts/check_compose.py", "--compose", outside,
                          "--report", self.workspace / "report.json")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.workspace / "report.json").exists())

    def test_compose_security_regressions_still_pass(self):
        output = self.workspace / "iac/report.json"
        result = self.cli("infraestructura/scripts/check_compose.py", "--report", output)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(output.read_text())
        self.assertEqual(report["negative_gate_tests"], 9)
        self.assertEqual(report["services"], 9)

    def test_trivy_cannot_read_outside_or_overwrite_outside(self):
        result = self.cli("scripts/verify_trivy_sca.py", "verify", "--report", self.victim,
                          "--expected", self.workspace / "expected.json", "--output", self.workspace / "summary.json")
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.workspace / "summary.json").exists())
        result = self.cli("scripts/verify_trivy_sca.py", "prepare", "--destination", self.workspace / "stage",
                          "--expected", self.victim, "--resolved", self.workspace / "requirements.txt")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.victim.read_text(), "untouched")

    def test_trivy_prepare_preserves_legitimate_runner_inventory(self):
        source = self.workspace / "requirements.txt"
        source.write_text("PyJWT==2.15.0\n", encoding="utf-16")
        original = source.read_bytes()
        result = self.cli("scripts/verify_trivy_sca.py", "prepare", "--destination", self.workspace / "stage",
                          "--expected", self.workspace / "expected.json", "--resolved", source)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(source.read_bytes(), original)
        self.assertEqual((self.workspace / "stage/requirements.txt").read_text(), "PyJWT==2.15.0\n")

    def test_trivy_cli_still_emits_a_blocking_summary_for_high_unfixed(self):
        report = self.workspace / "trivy.json"
        expected = self.workspace / "expected.json"
        output = self.workspace / "nested/summary.json"
        report.write_text(json.dumps({"SchemaVersion": 2, "Results": [{"Target": "requirements.txt",
            "Class": "lang-pkgs", "Type": "pip", "Packages": [{"Name": "PyJWT", "Version": "2.15.0"}],
            "Vulnerabilities": [{"VulnerabilityID": "CVE-test", "PkgName": "PyJWT",
                                 "InstalledVersion": "2.15.0", "Severity": "HIGH"}]}]}))
        expected.write_text(json.dumps({"requirements.txt": {"packages": {"pyjwt": "2.15.0"}}}))
        result = self.cli("scripts/verify_trivy_sca.py", "verify", "--report", report,
                          "--expected", expected, "--output", output)
        self.assertEqual(result.returncode, 1, result.stderr)
        summary = json.loads(output.read_text())
        self.assertFalse(summary["passed"])
        self.assertEqual(summary["blockers"][0]["fixed"], "")

    def test_invalid_inventory_is_not_echoed_or_staged(self):
        source = self.workspace / "requirements.txt"
        marker = "never-echo-invalid-source-content"
        source.write_text("SECRET=" + marker)
        stage = self.workspace / "stage"
        result = self.cli("scripts/verify_trivy_sca.py", "prepare", "--destination", stage,
                          "--expected", self.workspace / "expected.json", "--resolved", source)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn(marker, result.stdout + result.stderr)
        self.assertFalse((stage / "requirements.txt").exists())

    def test_verifier_rejects_unsafe_report_before_docker(self):
        with patch.object(sys, "argv", ["verify", "--deploy-dir", str(self.workspace / "deployment"),
                                       "--project", "iam-ci-123-1", "--report", str(self.victim)]), \
                patch.object(runtime, "command") as execute:
            with self.assertRaises(ValueError):
                runtime.main()
            execute.assert_not_called()
        self.assertEqual(self.victim.read_text(), "untouched")

    def test_manual_deployment_requires_explicit_matching_operator_directory(self):
        deployed = self.root / "manual-deployment"
        deployed.mkdir()
        with patch.dict(os.environ, {"RUNNER_TEMP": "", "IAM_DEPLOY_DIR": str(deployed)}):
            self.assertEqual(safe_paths.deployment_path(deployed), deployed.resolve())
            with self.assertRaises(ValueError):
                safe_paths.deployment_path(self.workspace)

    def test_runtime_probes_and_persistence_reports_keep_their_contract(self):
        deployed = self.workspace / "deployment"
        deployed.mkdir()
        env = deployed / ".env"
        env.write_text("SECRET=never-record-this\n")
        env.chmod(0o600)
        spec = json.loads((ROOT / "orquestacion/compose.simulated.json").read_text())
        (deployed / "compose.simulated.json").write_text(json.dumps(spec))
        records = []
        images = {}
        for index, name in enumerate(sorted(set(spec["services"]) - {"bootstrap-admin"}), 1):
            identifier = f"{index:064x}"
            image = "sha256:" + identifier
            images[image] = [{"RepoDigests": [spec["services"][name]["image"]]}]
            records.append({"Id": identifier, "Image": image, "Config": {"Labels": {"com.docker.compose.service": name}},
                            "State": {"Running": True, "Health": {"Status": "healthy"}}, "RestartCount": 0,
                            "HostConfig": {"ReadonlyRootfs": True, "CapDrop": ["ALL"], "SecurityOpt": ["no-new-privileges:true"],
                                           "Privileged": False, "PidsLimit": 128, "Memory": 1024, "PortBindings": None,
                                           "GroupAdd": ["1000"] if name == "postgres" else []},
                            "Mounts": [{"Type": "volume", "Destination": "/var/lib/postgresql/data"}]})

        def probe(arguments):
            runtime.validate_docker_arguments(arguments)
            if arguments[0] == "inspect":
                return json.dumps(records)
            if arguments[0] == "exec":
                return "1001"
            if arguments[0] == "image":
                return json.dumps(images[arguments[2]])
            if arguments[-2:] == ["ps", "-q"]:
                return "\n".join(record["Id"] for record in records)
            if arguments[-1] == runtime.SCHEMA_QUERY:
                return "permisos_usuario_compania|cargas_usuarios|cargas_usuario_filas"
            return "1"

        def status(url):
            return 401 if any(path in url for path in ("/auth/me", "/usuarios/cargas", "/v1/companies")) else 200

        if os.name == "nt":
            self.skipTest("Runtime .env POSIX mode contract is verified on Linux")
        first = self.workspace / "first.json"
        final = self.workspace / "final.json"
        with patch.object(runtime, "command", side_effect=probe), patch.object(runtime, "http_status", side_effect=status):
            arguments = ["verify", "--deploy-dir", str(deployed), "--project", "iam-ci-123-1", "--report", str(first)]
            with patch.object(sys, "argv", arguments):
                runtime.main()
            with patch.object(sys, "argv", arguments[:-1] + [str(final), "--expect", str(first)]):
                runtime.main()
        evidence = json.loads(final.read_text())
        self.assertTrue(evidence["persistence_verified"])
        self.assertEqual(len(evidence["containers"]), 8)
        self.assertEqual(len(evidence["http_checks"]), 8)
        self.assertNotIn("never-record-this", final.read_text())


if __name__ == "__main__":
    unittest.main()
