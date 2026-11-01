"""Native byte-message replies reuse the canonical command lifecycle."""
from pathlib import Path
from test_pcc_gui_commands import _compile_run

def test_native_ipc_copies_retries_and_consumes_once(tmp_path, pcc_py_runtime_archive):
    source=(Path(__file__).parent/'fixtures/ipc_roundtrip.py').read_text()
    output=_compile_run(tmp_path,pcc_py_runtime_archive,'ipc_roundtrip',source)
    assert 'PCC_GUI_NATIVE_IPC_OK' in output
