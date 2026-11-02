"""Owned native alert interactions; independent of native PCC1 qualification."""
from pathlib import Path
import os
import subprocess
import sys
import pytest
REPO=Path(__file__).resolve().parents[1]
pytestmark=pytest.mark.integration
@pytest.mark.skipif(sys.platform!='darwin',reason='AppKit dialogs')
def test_native_message_box_ownership(tmp_path:Path)->None:
    env=dict(os.environ);env.pop('LC_ALL',None)
    executable=tmp_path/'dialog'
    build=subprocess.run(['xcrun','--sdk','macosx','clang','-fobjc-arc','-pthread','-framework','Foundation','-framework','AppKit','-framework','Metal','-framework','QuartzCore',str(REPO/'tests/fixtures/native_dialog.m'),'-o',str(executable)],env=env,capture_output=True,text=True,timeout=120)
    assert build.returncode==0,build.stdout+build.stderr
    run=subprocess.run([str(executable),str(tmp_path/'dialog.png')],env=env,capture_output=True,text=True,timeout=40)
    assert run.returncode==0,run.stdout+run.stderr
    assert run.stdout=='PCC_NATIVE_DIALOG_OK top_level=1 sheets=4 pending=1 stale=1 thread=1 parent_close=1 counts=0\n'
