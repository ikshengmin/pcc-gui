"""Use the core's provenance-checked archives from this standalone checkout."""

import os
from pathlib import Path

import pytest

# Reuse only the fixture, not core's collection hooks or compiler provisioning.
from tests.conftest import pcc_runtime_archive


@pytest.fixture(scope="session")
def pcc_py_runtime_archive(request):
    """Verify an explicitly staged archive through the current core fixture."""
    if not os.environ.get("PCC_RUNTIME_ARCHIVE"):
        pytest.fail(
            "Set PCC_RUNTIME_ARCHIVE to an explicitly staged, provenance-checked "
            "libpy_runtime_pcc_py.a from the matching core checkout. "
            "GUI tests never build runtime archives."
        )
    return request.getfixturevalue("pcc_runtime_archive")


def pytest_configure(config):
    # Native probes live in pytest temporary directories, outside the package.
    root = str(Path(__file__).resolve().parents[1])
    sites = os.environ.get("PCC_PACKAGE_SITE", "").split(os.pathsep)
    os.environ["PCC_PACKAGE_SITE"] = os.pathsep.join(
        [root, *(site for site in sites if site and site != root)]
    )
