"""Native owned image/Tray interactions; independent of PCC1 and Windows parity."""
from pathlib import Path
import os
import subprocess
import sys
import pytest

REPO = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.integration


@pytest.mark.skipif(sys.platform != "darwin", reason="AppKit status items")
def test_native_image_tray_ownership(tmp_path: Path) -> None:
    env = dict(os.environ)
    env.pop("LC_ALL", None)
    executable = tmp_path / "tray"
    image = Path(os.environ["PCC_GUI_TRAY_TEST_IMAGE"])
    build = subprocess.run(
        ["xcrun", "--sdk", "macosx", "clang", "-fobjc-arc", "-pthread",
         "-framework", "Foundation", "-framework", "AppKit", "-framework", "Metal",
         "-framework", "QuartzCore", "-framework", "CoreGraphics",
         str(REPO / "tests/fixtures/native_tray.m"), "-o", str(executable)],
        env=env, capture_output=True, text=True, timeout=120,
    )
    assert build.returncode == 0, build.stdout + build.stderr
    capture = Path(os.environ.get("PCC_GUI_TRAY_TEST_CAPTURE", str(tmp_path / "tray.png")))
    run = subprocess.run([str(executable), str(capture), str(image)],
                         env=env, capture_output=True, text=True, timeout=40)
    assert run.returncode == 0, run.stdout + run.stderr
    assert run.stdout == "PCC_NATIVE_IMAGE_TRAY_OK copy=1 init_failure=1 path=1 image_lease=1 menu_owner=1 click=1 popup=1 deferred_release=1 window_lifetime=1 overflow=1 thread=1 counts=0\n"
