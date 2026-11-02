"""Resolve the installed compiler without starting a core bootstrap build."""

import os
from pathlib import Path
import shutil

import pcc


CORE_ROOT = Path(pcc.__file__).resolve().parents[1]


def compiler_path() -> Path:
    requested = os.environ.get("PCC1") or os.environ.get("PCC_CURRENT_PCC1") or "pcc1"
    executable = shutil.which(requested)
    if executable is None:
        raise RuntimeError(
            f"Compiler {requested!r} is not executable. Install pcc1 from the core "
            "checkout into ~/.local/bin, add that directory to PATH, or set "
            "PCC1=/absolute/path/to/pcc1. GUI tests never bootstrap the compiler."
        )
    return Path(executable).absolute()


METAL_BRIDGE_SOURCE = Path(__file__).resolve().parents[1] / "pcc_gui" / "native" / "pcc_gui_metal_render_bridge.m"


def write_metal_render_bridge(out_dir: str | Path) -> Path:
    """Stage the framework-owned native source for an isolated test build."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / METAL_BRIDGE_SOURCE.name
    output.write_bytes(METAL_BRIDGE_SOURCE.read_bytes())
    # The canonical bridge now owns transitive clipboard/dialog includes.
    # Preserve their exact bytes when staging an isolated consumer build.
    for source in sorted(METAL_BRIDGE_SOURCE.parent.iterdir()):
        if source.is_file() and source.suffix in {".h", ".inc"}:
            (out_dir / source.name).write_bytes(source.read_bytes())
    return output
