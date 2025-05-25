import pytest
import os
from dotenv import load_dotenv
from pathlib import Path

# Caminho para o .env na raiz do projeto, relativo a este conftest.py na raiz
dotenv_path = Path(__file__).resolve().parent / ".env"
if dotenv_path.is_file():
    load_dotenv(dotenv_path=dotenv_path, verbose=True)


def pytest_addoption(parser):
    """
    Adiciona a opção de linha de comando '--live' ao pytest.
    Esta flag permite a execução de testes que interagem com APIs reais.
    """
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="run live API tests that require real API keys and may incur costs",
    )


def pytest_configure(config):
    """
    Registra o marcador 'live'.
    Testes marcados com '@pytest.mark.live' só serão executados se a flag '--live'
    for fornecida e a GEMINI_API_KEY estiver configurada no ambiente.
    """
    config.addinivalue_line(
        "markers",
        "live: mark test as live to run only when --live is provided and GEMINI_API_KEY is set",
    )


def pytest_collection_modifyitems(config, items):
    """
    Modifica a coleção de itens de teste antes da execução.
    - Se '--live' não for fornecido, pula testes marcados com 'live'.
    - Se '--live' for fornecido mas GEMINI_API_KEY não estiver configurada,
      pula testes marcados com 'live'.
    """
    run_live_tests = config.getoption("--live")
    api_key_is_set = bool(os.getenv("GEMINI_API_KEY"))

    if not run_live_tests:
        skip_live_reason = "need --live option to run"
        for item in items:
            if "live" in item.keywords:
                item.add_marker(pytest.mark.skip(reason=skip_live_reason))
    elif not api_key_is_set:
        skip_live_no_key_reason = (
            "GEMINI_API_KEY not set in environment, skipping live tests"
        )
        for item in items:
            if "live" in item.keywords:
                item.add_marker(pytest.mark.skip(reason=skip_live_no_key_reason))

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
