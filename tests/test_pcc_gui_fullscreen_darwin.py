"""AppKit fullscreen lease behavior without switching desktop Spaces."""

from pathlib import Path
import subprocess
import sys

import pytest

pytestmark = pytest.mark.integration
REPO = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(sys.platform != "darwin", reason="AppKit fullscreen")
def test_fullscreen_window_lifetime_and_notifications(tmp_path: Path) -> None:
    executable = tmp_path / "fullscreen"
    built = subprocess.run(
        ["xcrun", "--sdk", "macosx", "clang", "-fobjc-arc", "-fblocks", "-pthread", "-DPCC_GUI_FULLSCREEN_FIXTURE",
         "-framework", "Foundation", "-framework", "AppKit", "-framework", "Metal",
         "-framework", "QuartzCore", str(REPO / "pcc_gui/native/pcc_gui_metal_render_bridge.m"),
         str(REPO / "tests/fixtures/native_fullscreen.m"), "-o", str(executable)],
        capture_output=True, text=True, timeout=90,
    )
    assert built.returncode == 0, built.stdout + built.stderr
    run = subprocess.run([str(executable)], capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stdout + run.stderr
    assert run.stdout.startswith("PCC_FULLSCREEN_OK ") and "live=0 space_changes=0" in run.stdout
