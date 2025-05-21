# tests/python/test_llm_core_api_client.py
import pytest
import os
from unittest.mock import patch, MagicMock
from scripts.llm_core import api_client
from scripts.llm_core import config as core_config
from google.genai import errors as google_genai_errors
from google.api_core import exceptions as google_api_core_exceptions


@pytest.fixture(autouse=True)
def mock_dotenv_load_fixture():
    # Este mock agora é para a importação de `load_dotenv` DENTRO do módulo api_client
    with patch("scripts.llm_core.api_client.load_dotenv") as mock_load_dotenv:
        mock_load_dotenv.return_value = True
        yield mock_load_dotenv


@patch.dict(os.environ, {"GEMINI_API_KEY": "test_key_1|test_key_2"}, clear=True)
def test_load_api_keys_success(mock_dotenv_load_fixture):
    api_client.api_key_loaded_successfully = False
    api_client.GEMINI_API_KEYS_LIST = []
    api_client.current_api_key_index = 0
    assert api_client.load_api_keys(verbose=True) is True
    assert len(api_client.GEMINI_API_KEYS_LIST) == 2
    assert api_client.GEMINI_API_KEYS_LIST[0] == "test_key_1"
    assert api_client.current_api_key_index == 0
    assert api_client.api_key_loaded_successfully is True
    # `load_dotenv` DENTRO de `load_api_keys` não deve ser chamado se GEMINI_API_KEY já está no os.environ
    mock_dotenv_load_fixture.assert_not_called()


@patch.dict(os.environ, {}, clear=True)
def test_load_api_keys_no_env_var_but_dotenv_has_it(mock_dotenv_load_fixture):
    api_client.api_key_loaded_successfully = False
    api_client.GEMINI_API_KEYS_LIST = []
    api_client.current_api_key_index = 0

    # Simula que após load_dotenv (mockado), os.getenv encontrará a chave
    # A fixture mock_dotenv_load_fixture já mocka load_dotenv.
    # Precisamos mockar os.getenv para simular que após a chamada (mockada) de load_dotenv,
    # a variável de ambiente está disponível.

    # Este side_effect será para a chamada a `os.getenv` DENTRO de `api_client.load_api_keys`
    def getenv_side_effect(key, default=None):
        if key == "GEMINI_API_KEY":
            # A primeira chamada a os.getenv (antes de load_dotenv) retorna None.
            # A segunda chamada a os.getenv (depois de load_dotenv) retorna as chaves.
            if getenv_side_effect.call_count == 1:
                getenv_side_effect.call_count += 1
                return None  # Simula que não estava no ambiente inicialmente
            return "dotenv_key_1|dotenv_key_2"
        return os.environ.get(key, default)  # Para outras chaves, comportamento padrão

    getenv_side_effect.call_count = 1  # Inicializa contador

    with patch(
        "scripts.llm_core.api_client.os.getenv", side_effect=getenv_side_effect
    ) as mock_os_getenv:
        assert api_client.load_api_keys(verbose=True) is True
        assert api_client.api_key_loaded_successfully is True
        assert len(api_client.GEMINI_API_KEYS_LIST) == 2
        assert api_client.GEMINI_API_KEYS_LIST[0] == "dotenv_key_1"

        # Verifica se load_dotenv foi chamado DENTRO de load_api_keys
        mock_dotenv_load_fixture.assert_called_once()

        # Verifica se os.getenv foi chamado pelo menos duas vezes para GEMINI_API_KEY
        # (uma antes de load_dotenv, uma depois)
        assert mock_os_getenv.call_count >= 2
        # Verifica a primeira chamada para GEMINI_API_KEY (deve ter sido chamada)
        mock_os_getenv.assert_any_call("GEMINI_API_KEY")


@patch.object(api_client.genai, "Client")
@patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}, clear=True)
def test_initialize_genai_client_success(
    mock_genai_client_constructor, mock_dotenv_load_fixture
):
    api_client.api_key_loaded_successfully = False
    api_client.gemini_initialized_successfully = False
    api_client.GEMINI_API_KEYS_LIST = []
    api_client.current_api_key_index = 0

    mock_client_instance = MagicMock()
    mock_genai_client_constructor.return_value = mock_client_instance

    assert api_client.initialize_genai_client(verbose=True) is True
    mock_genai_client_constructor.assert_called_once_with(api_key="fake_key")
    assert api_client.genai_client == mock_client_instance
    assert api_client.gemini_initialized_successfully is True


@patch.object(api_client, "genai_client")
@patch.object(api_client, "api_executor")
def test_execute_gemini_call_success(
    mock_executor, mock_client, mock_dotenv_load_fixture
):
    mock_future = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Mocked LLM Response"
    mock_response.prompt_feedback = None
    mock_response.candidates = [
        MagicMock(finish_reason=api_client.types.FinishReason.STOP)
    ]

    mock_future.result.return_value = mock_response
    mock_executor.submit.return_value = mock_future

    api_client.gemini_initialized_successfully = True
    api_client.genai_client = mock_client
    api_client.api_executor = mock_executor

    contents = [api_client.types.Part(text="Test content")]
    response_text = api_client.execute_gemini_call(
        model_name="gemini-test-model", contents=contents, verbose=True
    )

    assert response_text == "Mocked LLM Response"
    mock_executor.submit.assert_called_once()


def teardown_module(module):
    api_client.shutdown_api_resources(verbose=False)
