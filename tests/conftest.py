"""Pytest fixtures for the helios_store wrapper tests.

Puts the repo root on sys.path so ``import ai_scientist.treesearch.helios_store``
resolves regardless of pytest's import mode, and provides a session-scoped
``helios_bin`` fixture that builds the CLI from HEAD (never the broken tracked
binary). If go is absent or the build fails, helios-marked tests skip while the
pure-Python tests still run.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_EVIDENCE_DIR = os.path.join(_REPO_ROOT, ".supergoal", "evidence", "M2")
os.makedirs(_EVIDENCE_DIR, exist_ok=True)


@pytest.fixture(scope="session")
def repo_root():
    return _REPO_ROOT


@pytest.fixture(scope="session")
def evidence_dir():
    return _EVIDENCE_DIR


@pytest.fixture(scope="session")
def helios_bin(tmp_path_factory):
    """Build the helios CLI from HEAD once per session.

    Prefer Phase 1's ``scripts/build_helios.sh`` (which also self-tests that the
    binary actually writes files); fall back to a plain ``go build``. Skip every
    helios-marked test if neither yields a working binary -- never fall back to
    the git-tracked ./helios-cli, which silently no-ops.
    """
    out = str(tmp_path_factory.mktemp("helios_bin") / "helios")
    diags = []

    script = os.path.join(_REPO_ROOT, "scripts", "build_helios.sh")
    if os.path.isfile(script):
        proc = subprocess.run(["bash", script, out], capture_output=True, text=True)
        if proc.returncode == 0 and os.access(out, os.X_OK):
            return out
        diags.append(
            "build_helios.sh rc=%d stderr=%r"
            % (proc.returncode, (proc.stderr or proc.stdout or "")[-400:])
        )

    go = os.environ.get("GO", "/usr/local/go/bin/go")
    helios_src = os.environ.get("HELIOS_SRC", "/home/admin/gh/helios")
    go_exe = go if os.path.isfile(go) else shutil.which(go)
    if go_exe and os.path.isdir(helios_src):
        proc = subprocess.run(
            [go_exe, "build", "-o", out, "./cmd/helios-cli"],
            cwd=helios_src,
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0 and os.access(out, os.X_OK):
            return out
        diags.append(
            "go build rc=%d stderr=%r" % (proc.returncode, (proc.stderr or "")[-400:])
        )
    else:
        diags.append("go not found (go_exe=%r, helios_src=%r)" % (go_exe, helios_src))

    pytest.skip(
        "helios binary unbuildable: " + " | ".join(diags), allow_module_level=False
    )


@pytest.fixture
def store_dir(tmp_path):
    """A fresh, absolute store dir path (created lazily by HeliosStore)."""
    return str(tmp_path / "store")


@pytest.fixture
def store(helios_bin, store_dir):
    from ai_scientist.treesearch.helios_store import HeliosStore

    return HeliosStore(helios_bin, store_dir)
