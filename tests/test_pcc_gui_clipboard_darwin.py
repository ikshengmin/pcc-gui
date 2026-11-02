"""Private-pasteboard AppKit ABI checks, independent of PCC1 qualification."""
from pathlib import Path
import os
import subprocess
import sys
import pytest

REPO=Path(__file__).resolve().parents[1]
pytestmark=pytest.mark.integration

@pytest.mark.skipif(sys.platform!='darwin',reason='AppKit pasteboards')
def test_native_clipboard_snapshots_and_lifetime(tmp_path:Path)->None:
    executable=tmp_path/'clipboard'
    env=dict(os.environ);env.pop('LC_ALL',None)
    built=subprocess.run(['xcrun','--sdk','macosx','clang','-fobjc-arc','-pthread',
        '-framework','Foundation','-framework','AppKit','-framework','Metal','-framework','QuartzCore',
        str(REPO/'pcc_gui/native/pcc_gui_metal_render_bridge.m'),
        str(REPO/'tests/fixtures/native_clipboard.m'),'-o',str(executable)],
        env=env,capture_output=True,text=True,timeout=120)
    assert built.returncode==0,built.stdout+built.stderr
    ran=subprocess.run([str(executable)],env=env,capture_output=True,text=True,timeout=30)
    assert ran.returncode==0,ran.stdout+ran.stderr
    assert ran.stdout=='PCC_NATIVE_CLIPBOARD_OK cycles=32 snapshots=64 private_only=1 worker_rejected=1 stale_rejected=1\n'
