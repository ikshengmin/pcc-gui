"""Private notification ownership; no OS power transition or PCC1 claim."""
from pathlib import Path
import os
import subprocess
import sys
import pytest

REPO = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.integration


@pytest.mark.skipif(sys.platform != "darwin", reason="AppKit power notifications")
def test_native_power_ownership(tmp_path: Path) -> None:
    env = dict(os.environ)
    env.pop("LC_ALL", None)
    executable = tmp_path / "power"
    build = subprocess.run(
        ["xcrun", "--sdk", "macosx", "clang", "-fobjc-arc", "-pthread",
         "-framework", "Foundation", "-framework", "AppKit", "-framework", "Metal",
         "-framework", "QuartzCore", "-framework", "CoreGraphics",
         str(REPO / "tests/fixtures/native_power.m"), "-o", str(executable)],
        env=env, capture_output=True, text=True, timeout=120,
    )
    assert build.returncode == 0, build.stdout + build.stderr
    run = subprocess.run([str(executable)], env=env, capture_output=True,
                         text=True, timeout=40)
    assert run.returncode == 0, run.stdout + run.stderr
    assert run.stdout == "PCC_NATIVE_POWER_OK worker=1 order=1 failure=2 races=64 overflow=1 sequence=1 capacity=1 stale=1 counts=0\n"
