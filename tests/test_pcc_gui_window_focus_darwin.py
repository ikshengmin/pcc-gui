"""AppKit bridge focus facts; this clang oracle does not qualify PCC1."""

from pathlib import Path
import subprocess
import sys

import pytest

pytestmark = pytest.mark.integration
REPO = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(sys.platform != "darwin", reason="AppKit window focus")
def test_native_window_focus_state_and_thread_boundary(tmp_path: Path) -> None:
    executable = tmp_path / "window-focus"
    built = subprocess.run(
        ["xcrun", "--sdk", "macosx", "clang", "-fobjc-arc", "-pthread",
         "-framework", "Foundation", "-framework", "AppKit", "-framework", "Metal",
         "-framework", "QuartzCore",
         str(REPO / "pcc_gui/native/pcc_gui_metal_render_bridge.m"),
         str(REPO / "tests/fixtures/native_window_focus.m"), "-o", str(executable)],
        capture_output=True, text=True, timeout=120,
    )
    assert built.returncode == 0, built.stdout + built.stderr
    result = subprocess.run([str(executable)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == "PCC_NATIVE_WINDOW_FOCUS_OK cycles=3 windows=6 rejected_worker=1 outputs_preserved=1\n"
