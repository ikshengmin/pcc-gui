"""Real GUI-module ABI emission; these gates do not execute CoreGraphics."""

from pathlib import Path
import re
import struct


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "pcc_gui" / "pcc_gui_cg.py"
LINUX = "x86_64-unknown-linux-gnu"
DARWIN = "arm64-apple-darwin"


def _compile_gui(tmp_path, target):
    from pcc.frontends.python.pipeline import compile_python

    output = tmp_path / "pcc_gui_cg.ll"
    compile_python(
        str(SOURCE), str(output), emit_llvm_only=True, python_library=True,
        libpython_mode="off", backend="self", target_triple=target,
    )
    return output.read_text(encoding="utf-8")


def _function_body(ir, symbol):
    return ir.split("@" + symbol + "(", 1)[1].split("\n}", 1)[0]


def test_coregraphics_calls_use_exact_scalar_and_structural_ir(tmp_path):
    text = _compile_gui(tmp_path, LINUX)
    calls = [line for line in text.splitlines() if " call " in line]
    assert any("call ptr (ptr, i64, i64, i64, i64, ptr, i32) %" in line for line in calls)
    assert any("call void (ptr, double, double, double, double) %" in line for line in calls)
    assert any("call void (ptr, { { double, double }, { double, double } }) %" in line for line in calls)
    assert any("call void (ptr, ptr, i64) %" in line for line in calls)
    assert len([line for line in calls if re.search(r"call (?:void|ptr) \([^@]*\) %", line)]) == 7
    for export in (
        "pcc_gui_cg_ensure", "pcc_gui_cg_context_create", "pcc_gui_cg_context_release",
        "pcc_gui_cg_set_fill", "pcc_gui_cg_fill_rect", "pcc_gui_cg_stroke_line",
    ):
        assert re.search(r"^define .*@" + export + r"\(", text, re.M)
    assert "@pcc_gui_cg_framework = global ptr null" in text
    cstrings = {
        re.sub(r"\\([0-9a-fA-F]{2})", lambda match: chr(int(match.group(1), 16)), payload).rstrip("\0")
        for payload in re.findall(r'c"([^"]*)"', text)
    }
    assert {
        "CGContextSetRGBFillColor", "CGContextFillRect", "CGBitmapContextCreate",
        "CGColorSpaceCreateDeviceRGB", "CGColorSpaceRelease", "CGContextRelease",
        "CGContextStrokeLineSegments",
    } <= cstrings
    assert "CGContextSetFillColorWithColor" not in cstrings
    assert "call_void_ptr5" not in text
    assert any("trunc i64 16385 to i32" in line for line in text.splitlines())
    stroke = _function_body(text, "pcc_gui_cg_stroke_line")
    assert stroke.count("store double") >= 4
    assert any("store i64 2," in line for line in stroke.splitlines())
    fill = _function_body(text, "pcc_gui_cg_set_fill")
    assert fill.count("fdiv double") == 4


def test_coregraphics_owned_linux_object_preserves_platform_imports(tmp_path):
    from pcc.backend.elf_x86_64 import parse_relocatable
    from pcc.backend.owned_object_emit import emit_owned_object

    text = _compile_gui(tmp_path, LINUX)
    data = emit_owned_object(text, LINUX)
    (tmp_path / "pcc_gui_cg.o").write_bytes(data)
    obj = parse_relocatable(data)
    names = {symbol.name for symbol in obj.symbols}
    assert "dlopen" in names
    assert "dlsym" in names
    assert "pcc_gui_cg_fill_rect" in names
    assert "pcc_gui_cg_stroke_line" in names


def test_coregraphics_owned_darwin_object_passes_rect_in_hfa_registers(tmp_path):
    from pcc.backend.macho_spec import CPU_TYPE_ARM64, MH_OBJECT, parse_object
    from pcc.backend.owned_object_emit import emit_owned_object
    from pcc.backend.self_backend import emit_aarch64_darwin_asm

    text = _compile_gui(tmp_path, DARWIN)
    assembly = emit_aarch64_darwin_asm(text)
    data = emit_owned_object(text, DARWIN)
    (tmp_path / "pcc_gui_cg.s").write_text(assembly, encoding="utf-8")
    (tmp_path / "pcc_gui_cg.o").write_bytes(data)
    obj = parse_object(data)
    assert obj.header["cputype"] == CPU_TYPE_ARM64
    assert obj.header["filetype"] == MH_OBJECT
    rect = assembly.split("_pcc_gui_cg_fill_rect:", 1)[1].split("\n.globl", 1)[0]
    before_call = rect.split("blr ", 1)[0]
    for lane in range(4):
        assert re.search(r"ldu?r d" + str(lane) + r",", before_call)
    text_section = next(
        section for section in obj.sections()
        if section["sectname"].rstrip(b"\0") == b"__text"
    )
    code = data[text_section["offset"]:text_section["offset"] + text_section["size"]]
    words = [word[0] for word in struct.iter_unpack("<I", code)]
    assert sum(word & 0xFFFFFC1F == 0xD63F0000 for word in words) == 7


def test_coregraphics_fake_provider_assembles_without_core_runtime_stubs(tmp_path):
    from pcc.backend.elf_x86_64 import parse_relocatable
    from pcc.backend.target_objects import encode_assembly_object

    source = (ROOT / "tests" / "fixtures" / "coregraphics_fake_sysv.s").read_text()
    data = encode_assembly_object(source, LINUX)
    (tmp_path / "coregraphics_fake_sysv.o").write_bytes(data)
    obj = parse_relocatable(data)
    defined = {symbol.name for symbol in obj.symbols if symbol.section_index != 0}
    assert {"dlopen", "dlsym", "CGContextFillRect", "CGContextStrokeLineSegments"} <= defined
    assert not any(name.startswith(("py_", "pcc_gc_")) for name in defined)


def test_coregraphics_fake_probe_runners_assemble_for_all_scenarios(tmp_path):
    from pcc.backend.elf_x86_64 import parse_relocatable
    from pcc.backend.target_objects import encode_assembly_object
    from test_pcc_gui_cg_provider import _runner

    scenarios = ["normal", "open-retry", "color-fail", "bitmap-fail"]
    scenarios += [f"missing-{i}" for i in range(1, 8)]
    for scenario in scenarios:
        source = _runner(scenario)
        data = encode_assembly_object(source, LINUX)
        (tmp_path / (scenario + ".s")).write_text(source)
        (tmp_path / (scenario + ".o")).write_bytes(data)
        obj = parse_relocatable(data)
        assert "main" in {symbol.name for symbol in obj.symbols if symbol.section_index != 0}
