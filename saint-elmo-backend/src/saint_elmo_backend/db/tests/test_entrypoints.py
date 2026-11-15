"""
Standalone `python -m` entrypoints must load every model on their own.

In-process tests can't catch a missing model, because conftest already imported the app,
so each check runs in a fresh interpreter.
"""

import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "module",
    ["saint_elmo_backend.db.seeders.runner", "saint_elmo_backend.agents.command"],
)
def test_entrypoint_configures_all_mappers(module):
    code = f"import {module}\nfrom sqlalchemy.orm import configure_mappers\nconfigure_mappers()\n"

    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
