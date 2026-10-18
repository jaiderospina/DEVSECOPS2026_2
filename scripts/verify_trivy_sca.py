"""Require Trivy package coverage and enforce HIGH/CRITICAL dependency findings."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from safe_paths import REPOSITORY, artifact_roots, confined_path, runner_root, write_json


def normalized(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def pinned_requirements(text):
    packages = {}
    for line_number, line in enumerate(text.lstrip("\ufeff").splitlines(), 1):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)(?:\[[A-Za-z0-9_,.-]+\])?==([^\s;]+)(?:[ \t]+--hash=sha256:[0-9a-f]{64})*", line)
        if not match:
            raise ValueError(f"SCA requires an exact resolved pin on line {line_number}")
        packages[normalized(match[1])] = match[2]
    if not packages:
        raise ValueError("Empty requirements inventory")
    return packages


def prepare(root, destination, resolved=None):
    expected = {}
    if resolved:
        sources = [(resolved, "requirements.txt")]
    else:
        sources = [(p, p.relative_to(root).as_posix()) for base in ("servicios", "infraestructura")
                   for p in sorted((root / base).rglob("requirements.txt"))]
        for relative in ("infraestructura/ansible/requirements-ci.lock", "tests/bulk_users/requirements-ci.lock", "tests/coverage/requirements-ci.lock"):
            lock = root / relative
            if lock.is_file():
                sources.append((lock, lock.parent.relative_to(root).as_posix() + "/ci-lock/requirements.txt"))
        if not sources:
            raise ValueError("No Python dependency manifests found")
        sources.append((root / "servicios/frontend/package-lock.json", "servicios/frontend/package-lock.json"))
    for source, relative in sources:
        source = confined_path(source, [resolved.parent if resolved else root])
        target = confined_path(destination / relative, [destination])
        raw = source.read_bytes()
        encoding = "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
        text = raw.decode(encoding).replace("\r\n", "\n").replace("\r", "\n")
        if source.name == "package-lock.json":
            manifest = json.loads(confined_path(source.parent / "package.json", [root]).read_text(encoding="utf-8"))
            lock = json.loads(text)
            for group in ("dependencies", "devDependencies"):
                if manifest.get(group, {}) != lock["packages"][""].get(group, {}):
                    raise ValueError(f"Frontend {group} and lock file disagree")
            packages = {}
            for name in {**manifest.get("dependencies", {}), **manifest.get("devDependencies", {})}:
                packages[normalized(name)] = lock["packages"]["node_modules/" + name]["version"]
            if not packages:
                raise ValueError("Empty frontend dependency inventory")
        else:
            packages = pinned_requirements(text)
            if source.suffix == ".lock":
                text = "\n".join(f"{name}=={version}" for name, version in packages.items()) + "\n"
        # Validate the inventory before staging; never echo invalid source contents.
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")
        if source.name == "package-lock.json":
            confined_path(target.parent / "package.json", [destination]).write_text(json.dumps(manifest), encoding="utf-8")
        expected[relative] = {"packages": packages, "source_sha256": hashlib.sha256(raw).hexdigest(),
                              "scan_sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
    return expected


def verify(report, expected):
    if report.get("SchemaVersion") != 2:
        raise ValueError("Unsupported or missing Trivy schema")
    results = report.get("Results", [])
    coverage = []
    counts = Counter()
    blockers = []
    for target, manifest in expected.items():
        matches = [r for r in results if r.get("Target", "").replace("\\", "/").endswith(target)]
        if len(matches) != 1:
            raise ValueError(f"Expected one Trivy result for {target}; got {len(matches)}")
        result = matches[0]
        if result.get("Class") != "lang-pkgs" or result.get("Type") not in ("pip", "npm"):
            raise ValueError(f"Unexpected dependency scanner for {target}")
        inventory = {(normalized(p["Name"]), p["Version"]) for p in result.get("Packages", [])}
        missing = [(name, version) for name, version in manifest["packages"].items()
                   if (name, version) not in inventory]
        if missing:
            raise ValueError(f"Incomplete Trivy package coverage for {target}: {missing}")
        coverage.append({"target": target, "type": result["Type"], "packages_detected": len(inventory),
                         "required_packages_verified": len(manifest["packages"])})
    # Enforce every finding, including unexpected extra results and unfixed CVEs.
    for result in results:
        for vulnerability in result.get("Vulnerabilities", []):
            severity = vulnerability.get("Severity", "UNKNOWN")
            counts[severity] += 1
            if severity in ("HIGH", "CRITICAL"):
                blockers.append({"target": result["Target"], "id": vulnerability["VulnerabilityID"],
                                 "package": vulnerability["PkgName"], "severity": severity,
                                 "installed": vulnerability["InstalledVersion"],
                                 "fixed": vulnerability.get("FixedVersion", "")})
    return {"coverage": coverage, "severity_counts": dict(counts), "blockers": blockers,
            "passed": not blockers, "policy": "HIGH/CRITICAL, including unfixed; no ignored CVEs"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    staging = sub.add_parser("prepare")
    staging.add_argument("--root", type=Path, default=Path("."))
    staging.add_argument("--destination", type=Path, required=True)
    staging.add_argument("--expected", type=Path, required=True)
    staging.add_argument("--resolved", type=Path)
    check = sub.add_parser("verify")
    check.add_argument("--report", type=Path, required=True)
    check.add_argument("--expected", type=Path, required=True)
    check.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            root = args.root.absolute()
            if ".." in root.parts:
                raise ValueError("Parent traversal is forbidden")
            allowed_inputs = artifact_roots()
            if root.resolve() != REPOSITORY:
                root = confined_path(root, [runner_root()])
            destination = confined_path(args.destination, artifact_roots())
            expected_path = confined_path(args.expected, artifact_roots())
            resolved = confined_path(args.resolved, allowed_inputs) if args.resolved else None
            expected = prepare(root, destination, resolved)
            write_json(expected_path, expected)
            print(f"Prepared {len(expected)} dependency manifests")
            return 0
        report_path = confined_path(args.report, artifact_roots())
        expected_path = confined_path(args.expected, artifact_roots())
        output = confined_path(args.output, artifact_roots())
        report = json.loads(report_path.read_text(encoding="utf-8"))
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        if not expected:
            raise ValueError("Empty expected inventory")
        summary = verify(report, expected)
        write_json(output, summary)
        print(json.dumps(summary))
        return 0 if summary["passed"] else 1
    except (ValueError, KeyError, OSError) as error:
        print(f"SCA verification failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
