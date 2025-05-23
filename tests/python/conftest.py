import pytest
import os
from dotenv import load_dotenv
from pathlib import Path

# Carrega variáveis de ambiente do arquivo .env na raiz do projeto, se existir.
# Isso é útil para rodar testes localmente que podem depender de GEMINI_API_KEY.
# Em CI, espera-se que as variáveis sejam configuradas diretamente no ambiente.
dotenv_path = Path(__file__).resolve().parent.parent.parent / ".env"
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
        "live: mark test to run only when --live is provided and GEMINI_API_KEY is set",
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
