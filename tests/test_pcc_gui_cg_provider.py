"""Opt-in production-runtime CG call tests using named fake platform providers.

The Linux arm executes no graphics. It preserves the real GUI source and real
provenance-checked runtime, and checks it against an independent SysV assembly
callee. A matching explicit runtime archive is required; never build one here.
"""

from pathlib import Path
import platform
import struct
import subprocess
import sys

import pytest

from test_pcc_gui_cg_abi import ROOT, LINUX, _compile_gui


FIXTURES = ROOT / "tests" / "fixtures"
STATE = "pcc_gui_cg_probe_state"


def _store(offset, value):
    return f" mov rax, {value}\n lea r10, {STATE}[rip]\n mov QWORD PTR [r10 + {offset}], rax\n"


def _ensure(offset):
    return (
        " call pcc_gui_cg_ensure\n movsxd rax, eax\n"
        f" lea r10, {STATE}[rip]\n mov QWORD PTR [r10 + {offset}], rax\n"
    )


def _create(width, height, offset):
    return (
        f" mov rdi, {width}\n mov rsi, {height}\n"
        " call pcc_gui_cg_context_create\n"
        f" lea r10, {STATE}[rip]\n mov QWORD PTR [r10 + {offset}], rax\n"
    )


def _runner(scenario):
    code = ".intel_syntax noprefix\n.text\n.globl main\nmain:\n push r12\n call pcc_gui_cg_probe_setup\n"
    if scenario == "open-retry":
        code += _store(0, 1) + _ensure(360) + _store(0, 0) + _ensure(368)
    else:
        if scenario == "color-fail":
            code += _store(16, 1)
        elif scenario == "bitmap-fail":
            code += _store(24, 1)
        elif scenario.startswith("missing-"):
            code += _store(8, int(scenario[8:]))
        code += _ensure(360) + _ensure(368) + _create(8, 6, 376)
        code += " mov r12, rax\n"
        code += " mov rdi, r12\n mov rsi, 255\n mov rdx, 128\n mov rcx, 0\n mov r8, 64\n call pcc_gui_cg_set_fill\n"
        code += " mov rdi, r12\n mov rsi, -3\n mov rdx, 5\n mov rcx, 19\n mov r8, 23\n call pcc_gui_cg_fill_rect\n"
        code += " mov rdi, r12\n mov rsi, 2\n mov rdx, -4\n mov rcx, 17\n mov r8, 31\n call pcc_gui_cg_stroke_line\n"
        code += " mov rdi, r12\n call pcc_gui_cg_context_release\n"
        # Null release/draw and invalid dimensions must never call the provider.
        code += " xor edi, edi\n call pcc_gui_cg_context_release\n"
        for function in ("set_fill", "fill_rect", "stroke_line"):
            code += f" xor edi, edi\n xor esi, esi\n xor edx, edx\n xor ecx, ecx\n xor r8d, r8d\n call pcc_gui_cg_{function}\n"
        code += _create(0, 6, 392) + _create(-1, 6, 400)
        code += _create(2305843009213693952, 1, 408)
        code += _create(1, 9223372036854775807, 416)
    code += f" mov eax, 1\n mov edi, 1\n lea rsi, {STATE}[rip]\n mov edx, 512\n syscall\n xor eax, eax\n pop r12\n ret\n"
    return code


@pytest.fixture(scope="module")
def native_cg_inputs(tmp_path_factory, pcc_py_runtime_archive):
    from pcc.backend.owned_object_emit import emit_owned_object
    from pcc.backend.target_objects import encode_assembly_object

    output = tmp_path_factory.mktemp("cg-native-inputs")
    gui_ir = _compile_gui(output, LINUX)
    gui_object = emit_owned_object(gui_ir, LINUX)
    fake_source = (FIXTURES / "coregraphics_fake_sysv.s").read_text()
    fake_object = encode_assembly_object(fake_source, LINUX)
    (output / "pcc_gui_cg.o").write_bytes(gui_object)
    (output / "coregraphics_fake_sysv.o").write_bytes(fake_object)
    return gui_object, fake_object, pcc_py_runtime_archive


@pytest.mark.integration
@pytest.mark.skipif(sys.platform != "linux" or platform.machine() != "x86_64", reason="Linux SysV native ABI oracle")
@pytest.mark.parametrize("scenario", ["normal", "open-retry", "color-fail", "bitmap-fail", *[f"missing-{i}" for i in range(1, 8)]])
def test_production_cg_against_fake_sysv_provider(tmp_path, native_cg_inputs, scenario):
    from pcc.backend.elf_x86_64 import link_static_executable, parse_relocatable, parse_static_executable
    from pcc.backend.target_objects import encode_assembly_object

    gui_object, fake_object, archive = native_cg_inputs
    runner = _runner(scenario)
    (tmp_path / "cg_probe.s").write_text(runner)
    runner_object = encode_assembly_object(runner, LINUX)
    # The production archive supplies startup, GC and all Python runtime owners.
    image = link_static_executable(
        [parse_relocatable(data) for data in (gui_object, fake_object, runner_object)],
        archives=[archive.read_bytes()],
    )
    parse_static_executable(image)
    executable = tmp_path / "cg-probe"
    executable.write_bytes(image)
    executable.chmod(0o755)
    result = subprocess.run([str(executable)], capture_output=True, timeout=15)
    (tmp_path / "native.stdout").write_bytes(result.stdout)
    (tmp_path / "native.stderr").write_bytes(result.stderr)
    assert result.returncode == 0, (result.returncode, result.stderr)
    assert len(result.stdout) == 512
    data = result.stdout
    q = lambda offset: struct.unpack_from("<q", data, offset)[0]
    assert q(104) == 0  # no wrong dlopen handle passed to dlsym
    assert q(312) == 2 and q(320) == 1  # RTLD_NOW; exact framework path
    if scenario == "open-retry":
        assert (q(360), q(368), q(32)) == (-1, 0, 2)
        return
    missing = int(scenario[8:]) if scenario.startswith("missing-") else 0
    expected_error = {0: 0, 1: -2, 2: -3, 3: -5, 4: -6, 5: -7, 6: -8, 7: -9}[missing]
    assert q(360) == q(368) == expected_error
    assert q(32) == 1  # successful framework open is cached
    assert all(q(offset) == 0 for offset in (392, 400, 408, 416))
    if missing in (3, 4, 5, 6):
        assert all(q(offset) == 0 for offset in (48, 56, 64, 72, 80, 88, 96, 376))
        return
    assert q(48) == 1
    if scenario == "color-fail":
        assert all(q(offset) == 0 for offset in (56, 64, 72, 80, 88, 96, 376))
        return
    assert q(56) == q(64) == 1
    assert q(352) == q(328) == q(152)  # temporary color space released once
    assert [q(offset) for offset in (112, 120, 128, 136, 144, 160)] == [0, 8, 6, 8, 32, 16385]
    if scenario == "bitmap-fail":
        assert all(q(offset) == 0 for offset in (72, 80, 88, 96, 376))
        return
    assert q(376) == q(336) == q(168) and q(72) == 1
    for symbol_id, count_offset in ((1, 80), (2, 88), (7, 96)):
        assert q(count_offset) == (0 if missing == symbol_id else 1)
    if missing != 1:
        assert q(176) == q(336)
        assert struct.unpack_from("<4d", data, 184) == pytest.approx((1.0, 128 / 255, 0.0, 64 / 255))
    if missing != 2:
        assert q(216) == q(336)
        assert struct.unpack_from("<4d", data, 224) == (-3.0, 5.0, 19.0, 23.0)
    if missing != 7:
        assert q(256) == q(336) and q(264) == 2 and q(272) == 0
        assert struct.unpack_from("<4d", data, 280) == (2.0, -4.0, 17.0, 31.0)


@pytest.mark.integration
@pytest.mark.skipif(sys.platform != "darwin", reason="requires actual Apple SDK headers")
def test_coregraphics_sdk_declarations_match_selected_abi():
    result = subprocess.run(
        ["xcrun", "--sdk", "macosx", "clang", "-std=c11", "-fsyntax-only", str(FIXTURES / "coregraphics_sdk_abi.c")],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
