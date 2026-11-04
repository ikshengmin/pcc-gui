"""Exercise the desktop shell ABI without launching Finder or a browser."""
import os
from pathlib import Path
import subprocess
import sys

import pytest


REPO = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.integration


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS workspace selectors")
def test_native_shell_requests_and_reveal(tmp_path: Path) -> None:
    env = dict(os.environ)
    env.pop("LC_ALL", None)
    executable = tmp_path / "shell"
    build = subprocess.run(
        ["xcrun", "--sdk", "macosx", "clang", "-fobjc-arc", "-pthread",
         "-framework", "Foundation", "-framework", "AppKit", "-framework", "Metal",
         "-framework", "QuartzCore", "-framework", "CoreGraphics",
         str(REPO / "tests/fixtures/native_shell.m"), "-o", str(executable)],
        env=env, capture_output=True, text=True, timeout=120,
    )
    assert build.returncode == 0, build.stdout + build.stderr
    run = subprocess.run([str(executable)], cwd=tmp_path, env=env,
                         capture_output=True, text=True, timeout=40)
    assert run.returncode == 0, run.stdout + run.stderr
    assert run.stdout == (
        "PCC_NATIVE_SHELL_OK selectors=3 async=1 success=1 missing=1 failure=1 cancel=1 "
        "retire=1 reentry=1 counts=0 external_launches=0\n"
    )
    print(run.stdout, end="")
