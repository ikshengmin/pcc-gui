"""Read-only AVFoundation status plus controlled native request completions."""
from pathlib import Path
import os
import re
import subprocess
import sys

import pytest


REPO = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.integration


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS microphone authorization")
def test_native_microphone_authorization(tmp_path: Path) -> None:
    env = dict(os.environ)
    env.pop("LC_ALL", None)
    executable = tmp_path / "media"
    build = subprocess.run(
        ["xcrun", "--sdk", "macosx", "clang", "-fobjc-arc", "-pthread",
         "-framework", "Foundation", "-framework", "AppKit", "-framework", "Metal",
         "-framework", "QuartzCore", "-framework", "CoreGraphics",
         str(REPO / "tests/fixtures/native_media.m"), "-o", str(executable)],
        env=env, capture_output=True, text=True, timeout=120,
    )
    assert build.returncode == 0, build.stdout + build.stderr
    run = subprocess.run([str(executable)], env=env, capture_output=True, text=True, timeout=40)
    assert run.returncode == 0, run.stdout + run.stderr
    assert re.fullmatch(
        r"PCC_NATIVE_MEDIA_OK readonly_status=[0-4] injected_ask=1 worker=1 duplicate=1 "
        r"failure=1 cancel=1 retire=1 capacity=1 counts=0 real_asks=0\n", run.stdout,
    ), run.stdout
    print(run.stdout, end="")
