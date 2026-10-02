"""Actual Harness module emission, distinct from native execution acceptance."""

import hashlib
from pathlib import Path

import pytest


PROJECT = Path(__file__).resolve().parents[1] / "examples" / "harness"


@pytest.mark.parametrize("module", ["model_runtime", "agent_runtime", "loader_runtime"])
def test_harness_module_emits_owned_linux_object(tmp_path, module):
    from pcc.frontends.python.pipeline import compile_python
    from pcc.backend.owned_object_emit import emit_owned_object
    from pcc.backend.elf_x86_64 import parse_relocatable

    source = PROJECT / (module + ".py")
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    (tmp_path / "source-identity.txt").write_text(str(source) + "\n" + before + "\n")
    output = tmp_path / (module + ".ll")
    compile_python(
        str(source), str(output), emit_llvm_only=True, python_library=True,
        libpython_mode="off", backend="self", target_triple="x86_64-unknown-linux-gnu",
    )
    ir = output.read_text(encoding="utf-8")
    data = emit_owned_object(ir, "x86_64-unknown-linux-gnu")
    (tmp_path / (module + ".o")).write_bytes(data)
    parsed = parse_relocatable(data)
    assert any(symbol.section_index != 0 for symbol in parsed.symbols)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
