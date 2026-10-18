import importlib.util
import json
from pathlib import Path
import unittest
import tempfile

spec = importlib.util.spec_from_file_location("sca", Path(__file__).parents[2] / "scripts/verify_trivy_sca.py")
sca = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sca)


class TrivyGateTests(unittest.TestCase):
    def report(self, vulnerabilities=None, packages=None):
        return {"SchemaVersion": 2, "Results": [{"Target": "requirements.txt", "Class": "lang-pkgs",
                "Type": "pip", "Packages": packages if packages is not None else [{"Name": "PyJWT", "Version": "2.15.0"}],
                "Vulnerabilities": vulnerabilities or []}]}

    def test_clean_dependency_inventory(self):
        result = sca.verify(self.report(), {"requirements.txt": {"packages": {"pyjwt": "2.15.0"}}})
        self.assertTrue(result["passed"])

    def test_empty_or_missing_scan_fails(self):
        for report in ({"SchemaVersion": 2, "Results": []}, self.report(packages=[])):
            with self.subTest(report=report), self.assertRaises(ValueError):
                sca.verify(report, {"requirements.txt": {"packages": {"pyjwt": "2.15.0"}}})

    def test_wrong_version_fails(self):
        with self.assertRaises(ValueError):
            sca.verify(self.report(), {"requirements.txt": {"packages": {"pyjwt": "2.14.0"}}})

    def test_high_and_critical_unfixed_block(self):
        for severity in ("HIGH", "CRITICAL"):
            finding = {"VulnerabilityID": "CVE-test", "PkgName": "PyJWT", "InstalledVersion": "2.15.0", "Severity": severity}
            with self.subTest(severity=severity):
                self.assertFalse(sca.verify(self.report([finding]), {"requirements.txt": {"packages": {"pyjwt": "2.15.0"}}})["passed"])

    def test_medium_recorded_without_blocking(self):
        finding = {"Severity": "MEDIUM"}
        result = sca.verify(self.report([finding]), {"requirements.txt": {"packages": {"pyjwt": "2.15.0"}}})
        self.assertTrue(result["passed"])
        self.assertEqual(result["severity_counts"], {"MEDIUM": 1})

    def test_extras_and_bom_normalization(self):
        self.assertEqual(sca.pinned_requirements("\ufeffpwdlib[argon2]==0.3.1\npydantic_core==2.46.5\n"),
                         {"pwdlib": "0.3.1", "pydantic-core": "2.46.5"})

    def test_hashed_ci_pins_preserve_the_complete_inventory(self):
        text = "PyJWT==2.15.0 --hash=sha256:" + "a" * 64 + "\n"
        self.assertEqual(sca.pinned_requirements(text), {"pyjwt": "2.15.0"})

    def test_ci_locks_reject_malformed_hashes_and_pip_options(self):
        for suffix in ("--hash=sha256:bad", "--index-url=https://untrusted.invalid", "--hash=md5:" + "a" * 32):
            with self.subTest(suffix=suffix), self.assertRaises(ValueError):
                sca.pinned_requirements("PyJWT==2.15.0 " + suffix)

    def test_ci_locks_are_staged_for_trivy_without_mutating_hashed_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "servicios/frontend").mkdir(parents=True)
            (root / "infraestructura/ansible").mkdir(parents=True)
            (root / "tests/bulk_users").mkdir(parents=True)
            (root / "tests/coverage").mkdir(parents=True)
            (root / "infraestructura/ansible/requirements.txt").write_text("ansible-core==2.21.5\n")
            manifest = {"dependencies": {"react": "^19.2.8"}}
            lock = {"packages": {"": manifest, "node_modules/react": {"version": "19.2.8"}}}
            (root / "servicios/frontend/package.json").write_text(json.dumps(manifest))
            (root / "servicios/frontend/package-lock.json").write_text(json.dumps(lock))
            hashed = "PyJWT==2.15.0 --hash=sha256:" + "a" * 64 + "\n"
            for path in ("infraestructura/ansible/requirements-ci.lock", "tests/bulk_users/requirements-ci.lock"):
                source = root / path
                source.write_text(hashed)
            coverage_lock = "coverage==7.16.2 --hash=sha256:" + "b" * 64 + "\n"
            (root / "tests/coverage/requirements-ci.lock").write_text(coverage_lock)
            expected = sca.prepare(root, root / "stage")
            self.assertEqual(len(expected), 5)
            for parent in ("infraestructura/ansible", "tests/bulk_users"):
                target = parent + "/ci-lock/requirements.txt"
                self.assertEqual(expected[target]["packages"], {"pyjwt": "2.15.0"})
                self.assertEqual((root / "stage" / target).read_text(), "pyjwt==2.15.0\n")
                self.assertEqual((root / parent / "requirements-ci.lock").read_text(), hashed)
            target = "tests/coverage/ci-lock/requirements.txt"
            self.assertEqual(expected[target]["packages"], {"coverage": "7.16.2"})
            self.assertEqual((root / "stage" / target).read_text(), "coverage==7.16.2\n")
            self.assertEqual((root / "tests/coverage/requirements-ci.lock").read_text(), coverage_lock)

    def test_utf16_manifest_is_normalized_without_changing_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source-requirements.txt"
            source.write_text("fastapi==0.141.1\n", encoding="utf-16")
            original = source.read_bytes()
            expected = sca.prepare(root, root / "stage", source)
            self.assertEqual(expected["requirements.txt"]["packages"], {"fastapi": "0.141.1"})
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual((root / "stage/requirements.txt").read_text(encoding="utf-8"), "fastapi==0.141.1\n")

    def test_unpinned_requirements_fail(self):
        with self.assertRaises(ValueError):
            sca.pinned_requirements("requests>=2")


if __name__ == "__main__":
    unittest.main()
