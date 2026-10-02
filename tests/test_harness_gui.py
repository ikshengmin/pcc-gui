"""Focused gates for the PCC-native Harness GUI shell."""

from __future__ import annotations

import ast
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

import pytest

from gui_compiler import compiler_path


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "examples" / "harness"


def _load_model():
    sys.path.insert(0, str(PROJECT))
    try:
        spec = importlib.util.spec_from_file_location(
            "pcc_harness_gui_model", PROJECT / "gui_model.py"
        )
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(PROJECT))


def test_gui_state_projects_the_logged_agent_turn() -> None:
    model = _load_model()
    state = model.HarnessGuiState()

    assert state.phase == "hero"
    assert state.visible_regions() == [
        "sidebar",
        "session-navigation",
        "trajectory",
        "composer",
        "status",
        "settings",
    ]

    response = state.submit_sample()

    assert response == "PCC harness is running. You said: hello from pcc gui"
    assert state.phase == "active"
    assert state.transcript() == [
        "user: hello from pcc gui",
        "assistant: PCC harness is running. You said: hello from pcc gui",
    ]
    assert state.agent.session.count() == 8


def test_gui_source_uses_pcc_declarative_and_command_owners() -> None:
    source = (PROJECT / "gui_app.py").read_text(encoding="utf-8")
    bridge = (PROJECT / "gui_bridge.py").read_text(encoding="utf-8")
    launcher = (PROJECT / "harness").read_text(encoding="utf-8")

    assert '"pcc_kit_create"' in source
    assert '"pcc_kit_render"' in source
    assert '"pcc_gui_commands_register"' in source
    assert "pcc_gui_metal_window_create" in bridge
    assert 'for SOURCE in "$PROJECT_DIR"/*.py' in launcher
    assert '[ "$SOURCE" -nt "$OUTPUT" ]' in launcher
    assert "WebView" not in source + bridge
    assert "Electron" not in source + bridge


def test_gui_static_text_lengths_match_utf8_payloads() -> None:
    tree = ast.parse((PROJECT / "gui_app.py").read_text(encoding="utf-8"))
    checked = 0
    projected = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id == "_projected_text":
            # Dynamic payload byte lengths are checked through the real
            # drawing path in test_gui_state_lifecycle.py. Do not require
            # hardcoded transcript literals merely to meet this scan floor.
            projected += 1
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "_text":
            continue
        payload = node.args[3]
        length = node.args[4]
        if (
            isinstance(payload, ast.Call)
            and isinstance(payload.func, ast.Name)
            and payload.func.id == "cstr"
            and isinstance(payload.args[0], ast.Constant)
            and isinstance(payload.args[0].value, str)
            and isinstance(length, ast.Constant)
            and isinstance(length.value, int)
        ):
            assert len(payload.args[0].value.encode("utf-8")) == length.value
            checked += 1
    assert checked > 0
    assert checked + projected >= 20


@pytest.mark.integration
@pytest.mark.skipif(sys.platform != "darwin", reason="requires Mach-O pcc1")
def test_current_pcc1_native_harness_gui() -> None:
    pcc1 = compiler_path()
    env = dict(os.environ)
    env["PCC1"] = str(pcc1)
    env.pop("LC_ALL", None)

    built = subprocess.run(
        [str(PROJECT / "build.sh")],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert built.returncode == 0, built.stdout + built.stderr

    artifact = PROJECT / "build" / "harness-core"
    checked = subprocess.run(
        [str(artifact), "--gui-self-check"],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert checked.returncode == 0, checked.stdout + checked.stderr
    assert checked.stdout == "HARNESS_GUI_SELF_CHECK_OK\n"

    linkage = subprocess.run(
        ["otool", "-L", str(artifact)],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert "libpython" not in linkage.stdout.lower()


@pytest.mark.integration
def test_current_pcc1_native_harness_headless(
    tmp_path: Path, pcc_py_runtime_archive: Path
) -> None:
    """Compile the production entrypoint and run its real CLI branch on Linux/Darwin.

    No bridge build, archive rebuild, temporary app rewrite or host fallback.
    Window/render acceptance remains in the separate Darwin integration gate.
    """
    env = dict(os.environ)
    env.pop("LC_ALL", None)
    env["PCC_RUNTIME_ARCHIVE"] = str(pcc_py_runtime_archive)
    artifact = tmp_path / "harness-core"
    built = subprocess.run(
        [str(compiler_path()), "--backend", "self", "--python-libpython=off",
         "--ir-scaffold=on", str(PROJECT / "app.py"), "-o", str(artifact)],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=300,
    )
    assert built.returncode == 0, built.stdout + built.stderr
    for arguments, marker in [
        (["--self-check"], "HARNESS_RUNTIME_SELF_CHECK_OK"),
        (["hello"], "assistant: PCC harness is running. You said: hello"),
        (["/tool echo native pcc"], "assistant: Tool returned: native pcc"),
    ]:
        ran = subprocess.run([str(artifact), *arguments], cwd=tmp_path, env=env,
                             text=True, capture_output=True, timeout=30)
        assert ran.returncode == 0, ran.stdout + ran.stderr
        assert marker in ran.stdout
    failed = subprocess.run([str(artifact), "--unknown-option"], cwd=tmp_path,
                            env=env, text=True, capture_output=True, timeout=30)
    assert failed.returncode != 0, failed.stdout + failed.stderr
