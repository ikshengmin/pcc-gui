"""mac_diff_app smoke truth test: compile the pcc-GUI diff app, run it, and
assert on the STRUCTURED output (not just the exit code — self backend used
to ignore main() return values, see module_lifecycle_lowering fix).

The app opens two fixed sample files, prints

    PCC_MAC_DIFF_SMOKE left_rows=N right_rows=M ops=K equal=.. deleted=.. inserted=..

then renders one declarative frame and exits through the app lifecycle.  This validates the
whole truth chain: file read -> line hash -> LCS diff -> statistics.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from gui_compiler import compiler_path
from gui_compiler import write_metal_render_bridge

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "examples" / "mac_diff_app" / "app.py"
LEFT = REPO / "examples" / "mac_diff_app" / "samples" / "left.txt"
RIGHT = REPO / "examples" / "mac_diff_app" / "samples" / "right.txt"


@pytest.fixture
def metal_bridge(tmp_path: Path) -> Path:
    source = write_metal_render_bridge(tmp_path)
    output = tmp_path / "libpcc_gui_metal.dylib"
    built = subprocess.run(
        ["xcrun", "--sdk", "macosx", "clang", "-fobjc-arc", "-framework", "Foundation", "-framework", "Metal",
         "-framework", "AppKit", "-framework", "QuartzCore", "-dynamiclib",
         str(source), "-o", str(output)], capture_output=True, text=True, timeout=120,
    )
    assert built.returncode == 0, built.stdout + built.stderr
    return output


@pytest.mark.skipif(sys.platform != "darwin", reason="requires AppKit/Metal window")
@pytest.mark.integration
def test_mac_diff_app_smoke_truth(tmp_path: Path, pcc_py_runtime_archive: Path, metal_bridge: Path) -> None:
    assert APP.is_file() and LEFT.is_file() and RIGHT.is_file()
    exe = tmp_path / "mac_diff_app"
    env = dict(os.environ)
    env["PCC_RUNTIME_ARCHIVE"] = str(pcc_py_runtime_archive)
    b = subprocess.run(
        [str(compiler_path()), "--backend", "self",
         "--python-libpython", "off", "--ir-scaffold", "on",
         str(APP), "-o", str(exe)],
        capture_output=True, text=True, timeout=300, env=env,
    )
    assert b.returncode == 0, b.stdout + b.stderr

    assert metal_bridge.parent == exe.parent

    r = subprocess.run(
        [str(exe), str(LEFT), str(RIGHT)],
        cwd=REPO,  # bridge discovery must not depend on the launch directory
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    out = r.stdout + r.stderr
    assert "PCC_MAC_DIFF_SMOKE" in out, out
    line = next(
        (ln for ln in out.splitlines() if "PCC_MAC_DIFF_SMOKE" in ln), ""
    )
    assert "left_rows= 5" in line, line
    assert "right_rows= 6" in line, line
    assert "ops= 6" in line, line
    assert "deleted= 0" in line, line
    assert "inserted= 1" in line, line
    assert "equal= 4" in line, line
    assert "changed= 1" in line, line
    assert "PCC_GUI_BRIDGE_ACK render_present= 0" in out
    assert "PCC_MAC_DIFF_DECLARATIVE_OK components=5" in out


@pytest.mark.skipif(sys.platform != "darwin", reason="requires AppKit/Metal window")
@pytest.mark.integration
def test_mac_diff_app_all_diff_cases(tmp_path: Path, pcc_py_runtime_archive: Path, metal_bridge: Path) -> None:
    """argv open with the all-cases fixture: equal/modify/delete/insert,
    consecutive deletes, tail diffs, empty lines, UTF-8, digits."""
    exe = tmp_path / "mac_diff_app"
    env = dict(os.environ)
    env["PCC_RUNTIME_ARCHIVE"] = str(pcc_py_runtime_archive)
    b = subprocess.run(
        [str(compiler_path()), "--backend", "self",
         "--python-libpython", "off", "--ir-scaffold", "on",
         str(APP), "-o", str(exe)],
        capture_output=True, text=True, timeout=300, env=env,
    )
    assert b.returncode == 0, b.stdout + b.stderr
    assert metal_bridge.parent == exe.parent
    a = REPO / "examples" / "mac_diff_app" / "samples" / "case_a.txt"
    bb = REPO / "examples" / "mac_diff_app" / "samples" / "case_b.txt"
    r = subprocess.run(
        [str(exe), str(a), str(bb)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    out = r.stdout + r.stderr
    line = next((ln for ln in out.splitlines() if "PCC_MAC_DIFF_SMOKE" in ln), "")
    assert "left_rows= 13" in line, line
    assert "right_rows= 12" in line, line
    assert "ops= 13" in line, line
    assert "equal= 7" in line, line
    assert "deleted= 1" in line, line
    assert "inserted= 0" in line, line
    assert "changed= 5" in line, line
    assert "PCC_GUI_BRIDGE_ACK render_present= 0" in out
    assert "PCC_MAC_DIFF_DECLARATIVE_OK components=5" in out
