"""Confine automation files to the checkout's reports or private runner workspace."""

import json
import os
from pathlib import Path
import re
import tempfile

REPOSITORY = Path(__file__).resolve().parents[1]


def runner_root():
    value = os.environ.get("RUNNER_TEMP")
    if not value:
        raise ValueError("RUNNER_TEMP must identify the private automation workspace")
    root = Path(value)
    if not root.is_absolute() or not root.is_dir() or root.is_symlink():
        raise ValueError("RUNNER_TEMP must be an existing absolute directory without symlinks")
    root = root.resolve()
    if root == Path(root.anchor):
        raise ValueError("The filesystem root is not an automation workspace")
    return root


def artifact_roots():
    roots = [REPOSITORY / "reports"]
    if os.environ.get("RUNNER_TEMP"):
        roots.append(runner_root())
    return roots


def confined_path(value, roots):
    """Reject traversal, escapes and symlinks, including existing parent symlinks."""
    path = Path(value)
    if ".." in path.parts:
        raise ValueError("Parent traversal is forbidden")
    absolute = path.absolute()
    for root in roots:
        # Roots are supplied by code/environment, never inferred from the CLI path.
        root = Path(root).absolute()
        if not absolute.is_relative_to(root):
            continue
        for current in (absolute, *absolute.parents):
            if current.is_symlink():
                raise ValueError("Symlinks are forbidden for automation files")
            if current == root:
                break
        resolved_root = root.resolve()
        resolved = absolute.resolve()
        if resolved != resolved_root and resolved.is_relative_to(resolved_root):
            return resolved
    raise ValueError("Path is outside the allowed automation directories")


def deployment_path(value):
    # CI uses RUNNER_TEMP. An operator may explicitly allow one manual deployment.
    if os.environ.get("RUNNER_TEMP"):
        return confined_path(value, [runner_root()])
    allowed = os.environ.get("IAM_DEPLOY_DIR")
    if not allowed:
        raise ValueError("Manual verification requires IAM_DEPLOY_DIR")
    trusted = Path(allowed)
    if not trusted.is_absolute() or trusted.is_symlink() or not trusted.is_dir():
        raise ValueError("IAM_DEPLOY_DIR must identify an existing absolute deployment")
    candidate = confined_path(value, [trusted.parent])
    if candidate != trusted.resolve():
        raise ValueError("The CLI directory must match IAM_DEPLOY_DIR")
    return candidate


def project_name(value, ci_only=False):
    pattern = r"iam-ci-\d+-\d+" if ci_only else r"iam-[a-z0-9][a-z0-9-]{1,48}"
    if not re.fullmatch(pattern, value, flags=re.ASCII):
        raise ValueError("Invalid IAM project name")
    return value


def write_json(value, payload, roots=None):
    """Replace reports atomically; do not truncate a symlink or hardlink target."""
    roots = artifact_roots() if roots is None else roots
    target = confined_path(value, roots)
    target.parent.mkdir(parents=True, exist_ok=True)
    target = confined_path(target, roots)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=target.parent, delete=False) as output:
            temporary = Path(output.name)
            json.dump(payload, output, indent=2)
            output.write("\n")
        os.replace(temporary, target)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
