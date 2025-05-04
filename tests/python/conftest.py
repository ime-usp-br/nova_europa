# -*- coding: utf-8 -*-
"""
Pytest configuration file for shared fixtures and hooks.

Defines the --live flag and related fixtures for integration tests.
"""

import pytest
import os
from pathlib import Path

# Fixture to make the --live flag available to tests
@pytest.fixture(scope="session")
def live_run(request):
    return request.config.getoption("--live")

# Fixture to get the test repository URL from environment variable
@pytest.fixture(scope="session")
def test_repo():
    repo = os.getenv("GH_TEST_REPO")
    if not repo:
        # Skip tests marked 'live' if the environment variable is not set
        pytest.skip("GH_TEST_REPO environment variable not set. Skipping live tests.")
    # Basic validation - should be in owner/repo format
    if "/" not in repo or len(repo.split("/")) != 2:
         pytest.fail(f"Invalid GH_TEST_REPO format: '{repo}'. Expected 'owner/repo'.")
    return repo

# Fixture to construct repo flags for gh commands
@pytest.fixture(scope="session")
def repo_flags(live_run, test_repo):
    if live_run:
        return ["-R", test_repo]
    else:
        # In mock mode, repo flags are not strictly needed for command execution,
        # but we might pass them to verify the command construction.
        # Use a placeholder or the actual test_repo if available for verification.
        return ["-R", test_repo if test_repo else "mock/repo"]

# Fixture to change the project root for tests that write files
@pytest.fixture
def change_project_root(tmp_path: Path, monkeypatch):
    """ Temporarily change the BASE_DIR for file writing tests """
    monkeypatch.setattr("scripts.update_project.BASE_DIR", tmp_path)
    # Also patch for create_issue if it uses BASE_DIR for templates/output
    # (Assuming create_issue might need patching in the future for file ops)
    # monkeypatch.setattr("scripts.create_issue.BASE_DIR", tmp_path)
    return tmp_path


# Add the --live command line option
def pytest_addoption(parser):
    parser.addoption(
        "--live", action="store_true", default=False,
        help="Run live integration tests that interact with external services (e.g., GitHub API via gh)."
    )

# Skip tests marked with 'live' if --live is not provided
def pytest_configure(config):
    config.addinivalue_line("markers", "live: mark test as a live integration test")

def pytest_collection_modifyitems(config, items):
    if not config.getoption("--live"):
        skip_live = pytest.mark.skip(reason="need --live option to run")
        for item in items:
            if "live" in item.keywords:
                item.add_marker(skip_live)
