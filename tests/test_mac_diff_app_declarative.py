"""End-to-end acceptance for the canonical declarative mac diff source."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from gui_compiler import compiler_path


REPO = Path(__file__).resolve().parents[1]
PROJECT = REPO / "examples" / "mac_diff_app"
ENTRY = PROJECT / "declarative_headless.py"
MODEL = PROJECT / "declarative_app.py"
APP = PROJECT / "app.py"
CASE_A = PROJECT / "samples" / "case_a.txt"
CASE_B = PROJECT / "samples" / "case_b.txt"


def _assert_trace(output: str, gc_backend: str) -> None:
    smoke = next(
        line for line in output.splitlines() if "PCC_MAC_DIFF_SMOKE" in line
    )
    assert "left_rows= 13" in smoke
    assert "right_rows= 12" in smoke
    assert "ops= 13" in smoke
    assert "equal= 7" in smoke
    assert "deleted= 1" in smoke
    assert "inserted= 0" in smoke
    assert "changed= 5" in smoke
    assert "PCC_MAC_DIFF_DECLARATIVE_OK components=5" in output
    if gc_backend:
        assert gc_backend in {"0", "1", "2", "3", "4"}
        assert "gc-backend= " + gc_backend in output


def test_canonical_entry_has_no_manual_frame_node_mutation() -> None:
    entry = APP.read_text(encoding="utf-8")
    model = MODEL.read_text(encoding="utf-8")
    build = (PROJECT / "build.sh").read_text(encoding="utf-8")
    assert "from declarative_app import run_app" in entry
    assert '"$APP_DIR/app.py"' in build
    assert "kit_window.py" not in build
    assert "while gui.running()" not in entry
    assert "while gui.running()" not in model
    assert "pcc_gui_component_render_commit" not in entry
    for boundary in (
        "pcc_gui_components_init",
        "pcc_gui_scheduler_run_budgeted",
        "pcc_gui_events_dispatch",
        "pcc_gui_style_apply_class",
        "pcc_gui_managed_state_set",
        "pcc_gui_managed_binding_add",
        "pcc_gui_commands_invoke",
        "pcc_gui_app_lifecycle_post",
    ):
        assert boundary in model
    assert "LINES_L" in model and "LINES_R" in model
    assert "_repair_ops" in model
    for canary_edge in (
        'enqueue_reduce(toolbar, 3',
        "restart_count(toolbar)",
        'cstr("bg-accent/50 -x-3/[dense]")',
        "managed_state_get(status, 1, managed)",
        "_invoke_command(1, toolbar",
        "_invoke_command(2, toolbar",
        'app_post(7, 1, null(), 0, 1, 0)',
        'function_addr("mac_diff_root_release")',
    ):
        assert canary_edge in model


@pytest.mark.integration
def test_declarative_canary_host_pcc(
    tmp_path: Path, pcc_py_runtime_archive: Path
) -> None:
    exe = tmp_path / "mac_diff_declarative_host"
    env = dict(os.environ)
    env.pop("LC_ALL", None)
    env["PCC_RUNTIME_ARCHIVE"] = str(pcc_py_runtime_archive)
    built = subprocess.run(
        [
            str(REPO / ".venv" / "bin" / "pcc"),
            "--backend",
            "self",
            "--python-libpython=off",
            "--ir-scaffold=on",
            str(ENTRY),
            "-o",
            str(exe),
        ],
        cwd=PROJECT,
        env=env,
        text=True,
        capture_output=True,
        timeout=600,
    )
    assert built.returncode == 0, built.stdout + built.stderr
    ran = subprocess.run(
        [str(exe), str(CASE_A), str(CASE_B)],
        cwd=PROJECT,
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert ran.returncode == 0, ran.stdout + ran.stderr
    _assert_trace(ran.stdout, "")

    missing = subprocess.run(
        [str(exe), str(tmp_path / "missing.txt"), str(CASE_B)],
        cwd=PROJECT, env=env, text=True, capture_output=True, timeout=30,
    )
    assert missing.returncode == 1, missing.stdout + missing.stderr
    assert "diff viewer failed with code 1" in missing.stdout


@pytest.mark.integration
@pytest.mark.pcc_gate(probe="pcc1")
@pytest.mark.parametrize("gc_backend", ["0", "1", "2", "3", "4"])
def test_declarative_canary_current_pcc1_gc0_to_gc4(
    tmp_path: Path,
    pcc_py_runtime_archive: Path,
    gc_backend: str,
) -> None:
    pcc1 = compiler_path()
    if pcc1 is None:
        pytest.fail("current pcc1 is required for the declarative GUI canary")
    exe = tmp_path / f"mac_diff_declarative_pcc1_gc{gc_backend}"
    env = dict(os.environ)
    env.pop("LC_ALL", None)
    env["PCC_RUNTIME_ARCHIVE"] = str(pcc_py_runtime_archive)
    env["PCC_GC_BACKEND"] = gc_backend
    built = subprocess.run(
        [
            str(pcc1),
            "--backend",
            "self",
            "--python-libpython=off",
            "--ir-scaffold=on",
            str(ENTRY),
            "-o",
            str(exe),
        ],
        cwd=PROJECT,
        env=env,
        text=True,
        capture_output=True,
        timeout=600,
    )
    assert built.returncode == 0, built.stdout + built.stderr
    ran = subprocess.run(
        [str(exe), str(CASE_A), str(CASE_B)],
        cwd=PROJECT,
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert ran.returncode == 0, ran.stdout + ran.stderr
    _assert_trace(ran.stdout, gc_backend)


@pytest.mark.integration
def test_scene_text_slots_retire_and_propagate_capacity_errors(tmp_path: Path) -> None:
    source = tmp_path / "scene_text_slots.py"
    source.write_text('''import pcc_gui
import pcc_gui_high as gui
from pcc.extern import c_abi_typed_export
from pcc.unsafe import calloc, cstr, define_global_i64, function_addr, global_addr, load_i64, ptr_to_int, store_i64

define_global_i64("scene_render_calls", 0)
define_global_i64("scene_last_slot", -1)
define_global_i64("scene_hidden", 0)

@c_abi_typed_export("scene_render", "i64", ("ptr", "ptr", "ptr", "i64", "i64", "i64"))
def render(window, rects, colors, count: int, width: int, height: int) -> int:
    store_i64(global_addr("scene_render_calls"), 0, load_i64(global_addr("scene_render_calls"), 0) + 1)
    return 0

@c_abi_typed_export("scene_text", "i64", ("ptr", "ptr", "ptr", "i64", "i64", "i64"))
def text(window, value, params, length: int, font: int, color: int) -> int:
    slot = load_i64(params, 0)
    if slot < 0 or slot >= 512:
        return 2
    if length > 0:
        store_i64(global_addr("scene_last_slot"), 0, slot)
    else:
        if slot < 2 or slot >= 20:
            return 3
        store_i64(global_addr("scene_hidden"), 0, load_i64(global_addr("scene_hidden"), 0) + 1)
    return 0

@c_abi_typed_export("scene_reject_text", "i64", ("ptr", "ptr", "ptr", "i64", "i64", "i64"))
def reject_text(window, value, params, length: int, font: int, color: int) -> int:
    return 7

def main() -> int:
    gui._setg(8, ptr_to_int(function_addr("scene_render")))
    gui._setg(120, ptr_to_int(function_addr("scene_text")))
    records = calloc(20, 48)
    rects = calloc(1, 32)
    colors = calloc(1, 4)
    i = 0
    while i < 20:
        store_i64(records, i * 48 + 16, 1)
        store_i64(records, i * 48 + 24, 12)
        store_i64(records, i * 48 + 40, ptr_to_int(cstr("x")))
        i += 1
    gui.render_scene(ptr_to_int(rects), ptr_to_int(colors), 1, ptr_to_int(records), 20, 64, 64)
    if gui.render_ack() != 0 or load_i64(global_addr("scene_last_slot"), 0) != 19:
        return 1
    gui.render_scene(ptr_to_int(rects), ptr_to_int(colors), 1, ptr_to_int(records), 2, 64, 64)
    if gui.render_ack() != 0 or load_i64(global_addr("scene_hidden"), 0) != 18:
        return 2
    gui._setg(120, ptr_to_int(function_addr("scene_reject_text")))
    gui.render_scene(ptr_to_int(rects), ptr_to_int(colors), 1, ptr_to_int(records), 2, 64, 64)
    if gui.render_ack() != 7:
        return 3
    gui.render_scene(ptr_to_int(rects), ptr_to_int(colors), 1, ptr_to_int(records), 513, 64, 64)
    if gui.render_ack() != 2 or load_i64(global_addr("scene_render_calls"), 0) != 3:
        return 4
    print("PCC_SCENE_TEXT_SLOTS_OK")
    return 0

main()
''', encoding="utf-8")
    env = dict(os.environ)
    env["PCC_PACKAGE_SITE"] = os.pathsep.join([str(PROJECT), str(REPO)])
    exe = tmp_path / "scene_text_slots"
    built = subprocess.run(
        [str(compiler_path()), "--backend", "self", "--python-libpython", "off",
         str(source), "-o", str(exe)], env=env, cwd=REPO,
        capture_output=True, text=True, timeout=120,
    )
    assert built.returncode == 0, built.stdout + built.stderr
    ran = subprocess.run([str(exe)], env=env, capture_output=True, text=True, timeout=30)
    assert ran.returncode == 0, ran.stdout + ran.stderr
    assert "PCC_SCENE_TEXT_SLOTS_OK" in ran.stdout
