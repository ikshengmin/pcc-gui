"""Deterministic non-window entry for the canonical declarative app."""

import sys

import pcc_gui  # noqa: F401  pcc1 compiles the framework into this program's closure
from declarative_app import run_app


def main() -> int:
    status = run_app(0)
    if status != 0:
        print("pcc-gui: diff viewer failed with code", status)
    return status


sys.exit(main())
