# tests/python/test_llm_core_api_client.py
import pytest
import os
from unittest.mock import patch, MagicMock
from scripts.llm_core import api_client # Importa o módulo a ser testado
# from scripts.llm_core import config as core_config # Pode não ser necessário para este teste específico
from google.genai import errors as google_genai_errors
from google.api_core import exceptions as google_api_core_exceptions

# Fixture para garantir que load_dotenv seja mockado em todos os testes deste módulo
# para evitar I/O real de .env durante testes unitários de api_client.
@pytest.fixture(autouse=True)
def mock_dotenv_load_globally():
    with patch("scripts.llm_core.api_client.load_dotenv") as mock_load:
        mock_load.return_value = True # Simula que foi chamado, mas não faz nada
        yield mock_load

@pytest.fixture(autouse=True)
def reset_api_client_module_state():
    """Reseta o estado global do módulo api_client antes de cada teste."""
    api_client.GEMINI_API_KEYS_LIST = []
    api_client.current_api_key_index = 0
    api_client.genai_client = None
    api_client.api_executor = None
    api_client.api_key_loaded_successfully = False
    api_client.gemini_initialized_successfully = False
    yield

# Teste para a função load_api_keys
@patch.dict(os.environ, {"GEMINI_API_KEY": "env_key1|env_key2"}, clear=True)
def test_load_api_keys_success(mock_dotenv_load_globally): # mock_dotenv_load_globally é aplicado via autouse
    assert api_client.load_api_keys(verbose=True) is True
    assert api_client.GEMINI_API_KEYS_LIST == ["env_key1", "env_key2"]
    assert api_client.api_key_loaded_successfully is True
    mock_dotenv_load_globally.assert_not_called() # Não deve ser chamado se a chave está no env

@patch.dict(os.environ, {}, clear=True) # Limpa GEMINI_API_KEY do os.environ
def test_load_api_keys_no_env_var_but_dotenv_has_it(mock_dotenv_load_globally):
    # Simula que após o (mockado) load_dotenv, os.getenv encontrará a chave
    def getenv_side_effect(key, default=None):
        if key == "GEMINI_API_KEY":
            # A primeira chamada a os.getenv (antes de load_dotenv) retorna None.
            # A segunda chamada a os.getenv (depois de load_dotenv) retorna as chaves.
            if getenv_side_effect.call_count == 1: # type: ignore
                getenv_side_effect.call_count += 1 # type: ignore
                return None
            return "dotenv_key_A|dotenv_key_B"
        return os.environ.get(key, default) # Comportamento padrão para outras chaves
    getenv_side_effect.call_count = 1 # Inicializa o contador para a função side_effect # type: ignore

    with patch("scripts.llm_core.api_client.os.getenv", side_effect=getenv_side_effect):
        assert api_client.load_api_keys(verbose=True) is True
    assert api_client.GEMINI_API_KEYS_LIST == ["dotenv_key_A", "dotenv_key_B"]
    assert api_client.api_key_loaded_successfully is True
    mock_dotenv_load_globally.assert_called_once() # Deve ser chamado pois a chave não estava no env inicialmente

# Teste para initialize_genai_client (AC2 da Issue #48)
@patch('scripts.llm_core.api_client.genai.Client') # Mock o construtor
@patch.dict(os.environ, {"GEMINI_API_KEY": "env_init_key_for_ac2_test"}, clear=True) # Chave específica para o teste
def test_initialize_genai_client_success(mock_genai_client_constructor):
    """
    Verifica a inicialização correta do cliente Gemini (genai.Client)
    quando a API Key é carregada diretamente da variável de ambiente.
    Este teste cobre o Critério de Aceite 2 (AC2) da Issue #48.
    """
    # Arrange
    # A fixture autouse=True 'reset_api_client_module_state' já limpou o estado.
    # A fixture autouse=True 'mock_dotenv_load_globally' já mockou load_dotenv.
    mock_client_instance = MagicMock()
    mock_genai_client_constructor.return_value = mock_client_instance

    # Act
    # initialize_genai_client chamará load_api_keys, que usará a chave de os.environ
    initialization_success = api_client.initialize_genai_client(verbose=True)

    # Assert
    assert initialization_success is True, "A inicialização do cliente GenAI falhou."
    # Verifica se genai.Client() foi chamado com a chave correta do ambiente
    mock_genai_client_constructor.assert_called_once_with(api_key="env_init_key_for_ac2_test")
    assert api_client.genai_client == mock_client_instance, "O cliente global genai_client não foi definido corretamente."
    assert api_client.api_key_loaded_successfully is True, "api_key_loaded_successfully deveria ser True."
    assert api_client.gemini_initialized_successfully is True, "gemini_initialized_successfully deveria ser True."
    # Verifica que load_dotenv NÃO foi chamado, pois a chave foi encontrada em os.environ
    # mock_dotenv_load_globally é a fixture injetada pela autouse=True.
    # Se a chave estivesse no env, load_api_keys não chamaria self.load_dotenv.
    api_client.load_dotenv.assert_not_called() # Acessa o mock através do módulo api_client


@patch.object(api_client, "genai_client", MagicMock()) # Mock para o cliente global
@patch.object(api_client, "api_executor", MagicMock()) # Mock para o executor global
def test_execute_gemini_call_success(mock_dotenv_load_globally): # mock_dotenv_load_globally é aplicado via autouse
    # Setup
    mock_future = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Mocked LLM Response Text"
    mock_response.prompt_feedback = None # Simula sem bloqueio
    mock_response.candidates = [MagicMock(finish_reason=api_client.types.FinishReason.STOP)] # Simula finalização normal
    mock_future.result.return_value = mock_response
    api_client.api_executor.submit.return_value = mock_future # type: ignore
    api_client.gemini_initialized_successfully = True # Garante que está inicializado

    contents = [api_client.types.Part(text="Test content for call")] # Usando api_client.types
    response_text = api_client.execute_gemini_call(
        model_name="gemini-test-model-exec", contents=contents, verbose=True
    )

    assert response_text == "Mocked LLM Response Text"
    api_client.api_executor.submit.assert_called_once() # type: ignore
    # Para asserções mais detalhadas sobre a chamada a generate_content:
    # api_client.genai_client.models.generate_content.assert_called_once_with(
    #     model="gemini-test-model-exec",
    #     contents=contents,
    #     config= #verificar config
    # )

def teardown_module(module):
    """Garante que o executor de threads seja desligado após todos os testes do módulo."""
    api_client.shutdown_api_resources(verbose=False)
