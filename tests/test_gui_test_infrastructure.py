"""Host-only checks for compiler/archive selection without native builds."""

import importlib.util
from pathlib import Path

import pytest

import gui_compiler


def _gui_fixtures():
    path = Path(__file__).with_name("conftest.py")
    spec = importlib.util.spec_from_file_location("gui_test_fixtures", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_archive_fixture_reuses_current_core_provenance_owner():
    from tests.conftest import pcc_runtime_archive

    fixtures = _gui_fixtures()
    assert fixtures.pcc_runtime_archive is pcc_runtime_archive
    assert not hasattr(fixtures, "pytest_plugins")


def test_archive_fixture_requires_explicit_archive_before_request(monkeypatch):
    monkeypatch.delenv("PCC_RUNTIME_ARCHIVE", raising=False)

    class Request:
        def getfixturevalue(self, name):
            pytest.fail("archive fixture must not run without an explicit archive")

    fixtures = _gui_fixtures()
    with pytest.raises(pytest.fail.Exception, match="Set PCC_RUNTIME_ARCHIVE"):
        fixtures.pcc_py_runtime_archive.__wrapped__(Request())


def test_archive_fixture_delegates_explicit_archive_to_core(monkeypatch, tmp_path):
    archive = tmp_path / "libpy_runtime_pcc_py.a"
    monkeypatch.setenv("PCC_RUNTIME_ARCHIVE", str(archive))
    requested = []

    class Request:
        def getfixturevalue(self, name):
            requested.append(name)
            return archive

    fixtures = _gui_fixtures()
    assert fixtures.pcc_py_runtime_archive.__wrapped__(Request()) == archive
    assert requested == ["pcc_runtime_archive"]


def test_archive_fixture_rejects_unverified_explicit_archive(monkeypatch, tmp_path):
    from pcc.tools.runtime_archive_provenance import ProvenanceError

    fixtures = _gui_fixtures()
    archive = tmp_path / "libpy_runtime_pcc_py.a"
    archive.write_bytes(b"unverified archive")
    monkeypatch.setenv("PCC_RUNTIME_ARCHIVE", str(archive))

    class Request:
        def getfixturevalue(self, name):
            assert name == "pcc_runtime_archive"
            return fixtures.pcc_runtime_archive.__wrapped__(None)

    with pytest.raises(ProvenanceError, match="cannot read provenance JSON"):
        fixtures.pcc_py_runtime_archive.__wrapped__(Request())


def test_missing_compiler_is_an_installation_error(monkeypatch):
    monkeypatch.setenv("PCC1", "/missing/pcc1")
    monkeypatch.setattr(gui_compiler.shutil, "which", lambda requested: None)
    with pytest.raises(RuntimeError, match="GUI tests never bootstrap"):
        gui_compiler.compiler_path()
