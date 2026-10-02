"""Production lifecycle lowering only, separate from native execution gates."""

from pathlib import Path

import pytest


PACKAGE = Path(__file__).resolve().parents[1] / "pcc_gui"


@pytest.mark.parametrize("target", ["x86_64-unknown-linux-gnu", "arm64-apple-darwin"])
@pytest.mark.parametrize("module", ["pcc_gui_app_lifecycle", "pcc_gui_events"])
def test_lifecycle_owned_object_emission(tmp_path, target, module):
    from pcc.frontends.python.pipeline import compile_python
    from pcc.backend.owned_object_emit import emit_owned_object

    output = tmp_path / (module + ".ll")
    compile_python(
        str(PACKAGE / (module + ".py")), str(output), emit_llvm_only=True, python_library=True,
        libpython_mode="off", backend="self", target_triple=target,
    )
    ir = output.read_text(encoding="utf-8")
    if module == "pcc_gui_app_lifecycle":
        assert "pcc_gui_app_lifecycle_processing" in ir
        assert "pcc_gui_app_lifecycle_native_event" in ir
        assert "pcc_gui_app_lifecycle_drain" in ir
    else:
        assert "pcc_gui_events_shutdown" in ir
        assert "pcc_gui_events_drain_passive" in ir
    data = emit_owned_object(ir, target)
    (tmp_path / (module + ".o")).write_bytes(data)
    assert len(data) > 0
