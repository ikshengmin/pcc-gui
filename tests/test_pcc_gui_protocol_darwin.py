"""Native document request ownership. No UI, network or compiler bootstrap."""
from pathlib import Path
import os
import subprocess
import sys

import pytest


REPO = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.integration


@pytest.mark.skipif(sys.platform != "darwin", reason="canonical Darwin native bridge")
def test_native_document_request_ownership(tmp_path: Path) -> None:
    env = dict(os.environ)
    env.pop("LC_ALL", None)
    executable = tmp_path / "protocol"
    build = subprocess.run(
        ["xcrun", "--sdk", "macosx", "clang", "-fobjc-arc", "-pthread",
         "-framework", "Foundation", "-framework", "AppKit", "-framework", "Metal",
         "-framework", "QuartzCore", "-framework", "CoreGraphics",
         str(REPO / "tests/fixtures/native_protocol.m"), "-o", str(executable)],
        env=env, capture_output=True, text=True, timeout=120,
    )
    assert build.returncode == 0, build.stdout + build.stderr
    run = subprocess.run([str(executable)], env=env, capture_output=True, text=True, timeout=40)
    assert run.returncode == 0, run.stdout + run.stderr
    assert run.stdout == (
        "PCC_NATIVE_PROTOCOL_OK binary=1 fifo_workers=4 claim=1 retry=1 "
        "terminal_race=1 retire_race=1 stale=1 limits=1 allocations=0\n"
    )
