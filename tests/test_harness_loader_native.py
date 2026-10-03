"""Native Loader execution with all five GC selectors, separate from GUI parity."""

import os
from pathlib import Path
import subprocess

import pytest

from gui_compiler import compiler_path


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "examples" / "harness"
SOURCE = ROOT / "tests" / "fixtures" / "harness_loader_keyed.py"


@pytest.mark.integration
def test_current_pcc1_keyed_loader_all_gc(tmp_path, pcc_py_runtime_archive):
    env = dict(os.environ)
    env.pop("LC_ALL", None)
    env["PCC_SELF_OBJ"] = "pcc"
    env["PCC_SELF_LINK"] = "pcc"
    env["PCC_NO_AUTO_PCC1"] = "1"
    env["PCC_RUNTIME_ARCHIVE"] = str(pcc_py_runtime_archive)
    env["PCC_PACKAGE_SITE"] = os.pathsep.join(
        [str(PROJECT), str(ROOT), env.get("PCC_PACKAGE_SITE", "")]
    )
    artifact = tmp_path / "harness-keyed-loader"
    built = subprocess.run(
        [str(compiler_path()), "--backend", "self", "--python-libpython=off",
         "--ir-scaffold=on", str(SOURCE), "-o", str(artifact)],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=300,
    )
    (tmp_path / "compile.log").write_text(built.stdout + built.stderr)
    assert built.returncode == 0, built.stdout + built.stderr
    env["PATH"] = "/nonexistent"
    for gc in range(5):
        env["PCC_GC_BACKEND"] = str(gc)
        ran = subprocess.run([str(artifact)], cwd=tmp_path, env=env,
                             text=True, capture_output=True, timeout=30)
        (tmp_path / ("gc" + str(gc) + ".log")).write_text(ran.stdout + ran.stderr)
        assert ran.returncode == 0, "GC " + str(gc) + ": " + ran.stdout + ran.stderr
        assert ran.stdout == "HARNESS_KEYED_LOADER_OK\n"
