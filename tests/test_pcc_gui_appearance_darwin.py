"""App-local native appearance ownership and dynamic colors; no system changes."""
from pathlib import Path
import os
import subprocess
import sys
import pytest

REPO = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.integration


@pytest.mark.skipif(sys.platform != "darwin", reason="AppKit appearance")
def test_native_appearance_ownership(tmp_path: Path) -> None:
    env = dict(os.environ)
    env.pop("LC_ALL", None)
    executable = tmp_path / "appearance"
    build = subprocess.run(
        ["xcrun", "--sdk", "macosx", "clang", "-fobjc-arc", "-pthread",
         "-framework", "Foundation", "-framework", "AppKit", "-framework", "Metal",
         "-framework", "QuartzCore", "-framework", "CoreGraphics",
         str(REPO / "tests/fixtures/native_appearance.m"), "-o", str(executable)],
        env=env, capture_output=True, text=True, timeout=120,
    )
    assert build.returncode == 0, build.stdout + build.stderr
    prefix = Path(os.environ.get("PCC_GUI_APPEARANCE_CAPTURE", str(tmp_path / "appearance")))
    run = subprocess.run([str(executable), str(prefix)], env=env, capture_output=True,
                         text=True, timeout=40)
    assert run.returncode == 0, run.stdout + run.stderr
    assert run.stdout == "PCC_NATIVE_APPEARANCE_OK registration=2 preflight_reentry=1 worker=1 snapshots=1 late=1 sampler_retirement=1 overflow=1 light_dark=1 colors=1 window_override=1 restore=1 foreign=1 thread=1 leases=0\n"
