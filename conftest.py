import pytest
import os
from dotenv import load_dotenv
from pathlib import Path

# Caminho para o .env na raiz do projeto, relativo a este conftest.py na raiz
# Correção: Este conftest.py está na raiz do projeto, o .env também.
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
    for fornecida e a GEMINI_API_KEY ou GH_TOKEN/GH_TEST_REPO estiverem configuradas no ambiente.
    """
    config.addinivalue_line(
        "markers",
        "live: mark test as live to run only when --live is provided and relevant API keys/tokens are set",
    )
    config.addinivalue_line( # Adiciona o marcador integration
        "markers", "integration: mark test as integration test"
    )


def pytest_collection_modifyitems(config, items):
    """
    Modifica a coleção de itens de teste antes da execução.
    - Se '--live' não for fornecido, pula testes marcados com 'live'.
    - Se '--live' for fornecido mas as chaves/tokens relevantes não estiverem configurados,
      pula testes marcados com 'live'.
    """
    run_live_tests = config.getoption("--live")
    # Verifica se alguma chave relevante para testes live está presente
    # Para este conftest, focamos nas chaves GitHub por enquanto
    # A chave Gemini é mais relevante para os testes de llm_interact
    gh_token_is_set = bool(os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN"))
    gh_test_repo_is_set = bool(os.getenv("GH_TEST_REPO"))
    can_run_gh_live_tests = gh_token_is_set or gh_test_repo_is_set

    # Adaptar para pular testes baseados em quais chaves/tokens estão faltando
    # Para este conftest.py na raiz, focamos nos testes de create_issue.py

    if not run_live_tests:
        skip_live_reason = "need --live option to run"
        for item in items:
            if "live" in item.keywords:
                item.add_marker(pytest.mark.skip(reason=skip_live_reason))
    elif not can_run_gh_live_tests:
        skip_gh_live_reason = (
            "GH_TOKEN/GITHUB_TOKEN or GH_TEST_REPO not set, skipping live GitHub tests"
        )
        for item in items:
            if "live" in item.keywords and "test_create_issue" in item.nodeid: # Escopo para create_issue
                item.add_marker(pytest.mark.skip(reason=skip_gh_live_reason))

# Fixture to make the --live flag available to tests
@pytest.fixture(scope="session")
def live_run(request):
    return request.config.getoption("--live")

# Fixture to get the test repository URL from environment variable
@pytest.fixture(scope="session")
def test_repo(request): # Adiciona request para usar config
    repo_env_var = os.getenv("GH_TEST_REPO")
    if request.config.getoption("--live") and not repo_env_var:
        # Se --live for passado mas GH_TEST_REPO não, falha explicitamente o setup da fixture
        pytest.fail("GH_TEST_REPO environment variable not set, but --live flag was used. Required for live GitHub tests.")
    if repo_env_var and ("/" not in repo_env_var or len(repo_env_var.split("/")) != 2):
         pytest.fail(f"Invalid GH_TEST_REPO format: '{repo_env_var}'. Expected 'owner/repo'.")
    return repo_env_var # Retorna o valor ou None

# Fixture to construct repo flags for gh commands
@pytest.fixture(scope="session")
def repo_flags(live_run, test_repo):
    if live_run and test_repo:
        return ["-R", test_repo]
    # Para modo mock, ou se test_repo não estiver definido mesmo com --live (embora agora isso falhe a fixture test_repo)
    # Se test_repo for None, mas live_run for True, a fixture test_repo já terá falhado.
    # Usar um placeholder se test_repo for None (para o caso de não ser estritamente necessário)
    return ["-R", test_repo if test_repo else "mock/repo"]


@pytest.fixture
def change_project_root(tmp_path: Path, monkeypatch):
    """ Temporarily change the PROJECT_ROOT for relevant modules. """
    original_update_project_base_dir = None
    if "scripts.update_project" in sys.modules:
        original_update_project_base_dir = sys.modules["scripts.update_project"].BASE_DIR
        monkeypatch.setattr(sys.modules["scripts.update_project"], "BASE_DIR", tmp_path)

    original_create_issue_base_dir = None
    original_create_issue_template_dir = None # Declarar antes do try
    if "scripts.create_issue" in sys.modules:
        original_create_issue_base_dir = sys.modules["scripts.create_issue"].BASE_DIR
        monkeypatch.setattr(sys.modules["scripts.create_issue"], "BASE_DIR", tmp_path)
        # Também é importante mockar o TEMPLATE_DIR se ele for calculado a partir de BASE_DIR
        if hasattr(sys.modules["scripts.create_issue"], "TEMPLATE_DIR"): # Verificar se existe
            original_create_issue_template_dir = sys.modules["scripts.create_issue"].TEMPLATE_DIR
            monkeypatch.setattr(sys.modules["scripts.create_issue"], "TEMPLATE_DIR", tmp_path / "templates" / "issue_bodies")


    yield tmp_path # O valor que a fixture provê

    # Teardown: restaura os valores originais
    if "scripts.update_project" in sys.modules and original_update_project_base_dir:
        monkeypatch.setattr(sys.modules["scripts.update_project"], "BASE_DIR", original_update_project_base_dir)
    if "scripts.create_issue" in sys.modules:
        if original_create_issue_base_dir:
            monkeypatch.setattr(sys.modules["scripts.create_issue"], "BASE_DIR", original_create_issue_base_dir)
        if original_create_issue_template_dir: # Garante que existia antes de tentar restaurar
            monkeypatch.setattr(sys.modules["scripts.create_issue"], "TEMPLATE_DIR", original_create_issue_template_dir)