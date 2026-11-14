"""Locate the optional standalone Harness integration checkout."""

import os
from pathlib import Path

import pytest


def harness_project_root() -> Path:
    configured = os.environ.get("PCC_HARNESS_ROOT")
    root = Path(configured or Path(__file__).resolve().parents[2] / "harness").resolve()
    if not (root / "harness" / "__init__.py").is_file():
        if configured:
            raise FileNotFoundError(f"PCC_HARNESS_ROOT has no harness package: {root}")
        pytest.skip(
            "Standalone Harness is optional; clone it adjacent to pcc-gui or set PCC_HARNESS_ROOT",
            allow_module_level=True,
        )
    return root
