# tests/python/test_llm_core_api_client.py
import pytest
import os
from unittest.mock import patch, MagicMock
from scripts.llm_core import api_client
from google.genai import errors as google_genai_errors
from google.api_core import exceptions as google_api_core_exceptions
from google.genai import types as genai_types # Importação explícita
from scripts.llm_core import config as core_config_module # Para usar em teste live
import traceback # Para o teste live

# Fixture para garantir que load_dotenv seja mockado e globais resetados
@pytest.fixture(autouse=True)
def reset_module_globals_for_each_test(monkeypatch):
    """Reseta o estado global do módulo api_client e mocka load_dotenv antes de cada teste."""
    original_keys = list(api_client.GEMINI_API_KEYS_LIST)
    original_index = api_client.current_api_key_index
    original_client = api_client.genai_client
    original_executor = api_client.api_executor
    original_key_loaded = api_client.api_key_loaded_successfully
    original_gemini_init = api_client.gemini_initialized_successfully

    api_client.GEMINI_API_KEYS_LIST = []
    api_client.current_api_key_index = 0
    api_client.genai_client = None
    if api_client.api_executor:
        api_client.api_executor.shutdown(wait=False)
        api_client.api_executor = None
    api_client.api_key_loaded_successfully = False
    api_client.gemini_initialized_successfully = False

    with patch("scripts.llm_core.api_client.load_dotenv") as mock_load_dotenv_fixture:
        mock_load_dotenv_fixture.return_value = True
        yield mock_load_dotenv_fixture

    api_client.GEMINI_API_KEYS_LIST = original_keys
    api_client.current_api_key_index = original_index
    api_client.genai_client = original_client
    api_client.api_executor = original_executor
    api_client.api_key_loaded_successfully = original_key_loaded
    api_client.gemini_initialized_successfully = original_gemini_init

# Testes para load_api_keys
@patch.dict(os.environ, {"GEMINI_API_KEY": "env_key1|env_key2"}, clear=True)
def test_load_api_keys_success(reset_module_globals_for_each_test): # Fixture autouse já aplicada
    mock_dotenv_load_fixture = reset_module_globals_for_each_test
    assert api_client.load_api_keys(verbose=True) is True
    assert api_client.GEMINI_API_KEYS_LIST == ["env_key1", "env_key2"]
    assert api_client.api_key_loaded_successfully is True
    mock_dotenv_load_fixture.assert_not_called()

@patch.dict(os.environ, {}, clear=True)
def test_load_api_keys_no_env_var_but_dotenv_has_it(reset_module_globals_for_each_test):
    mock_dotenv_load_fixture = reset_module_globals_for_each_test
    def getenv_side_effect(key, default=None):
        if key == "GEMINI_API_KEY":
            if getenv_side_effect.call_count == 1: # type: ignore
                getenv_side_effect.call_count += 1 # type: ignore
                return None
            return "dotenv_key_A|dotenv_key_B"
        return os.environ.get(key, default)
    getenv_side_effect.call_count = 1 # type: ignore

    with patch("scripts.llm_core.api_client.os.getenv", side_effect=getenv_side_effect):
        assert api_client.load_api_keys(verbose=True) is True
    assert api_client.GEMINI_API_KEYS_LIST == ["dotenv_key_A", "dotenv_key_B"]
    assert api_client.api_key_loaded_successfully is True
    mock_dotenv_load_fixture.assert_called_once()


# Testes para initialize_genai_client (AC2 da Issue #48)
@patch('scripts.llm_core.api_client.genai.Client')
@patch.dict(os.environ, {"GEMINI_API_KEY": "env_init_key_for_ac2_test"}, clear=True)
def test_initialize_genai_client_success(mock_genai_client_constructor, reset_module_globals_for_each_test):
    mock_dotenv_load_fixture = reset_module_globals_for_each_test
    mock_client_instance = MagicMock()
    mock_genai_client_constructor.return_value = mock_client_instance

    initialization_success = api_client.initialize_genai_client(verbose=True)

    assert initialization_success is True
    mock_genai_client_constructor.assert_called_once_with(api_key="env_init_key_for_ac2_test")
    assert api_client.genai_client == mock_client_instance
    assert api_client.api_key_loaded_successfully is True
    assert api_client.gemini_initialized_successfully is True
    mock_dotenv_load_fixture.assert_not_called()


@pytest.fixture
def mock_gemini_services_for_execute_call(reset_module_globals_for_each_test, monkeypatch):
    mock_dotenv_load_fixture = reset_module_globals_for_each_test # Apenas para garantir que o mock de dotenv está ativo
    
    monkeypatch.setattr(api_client, "GEMINI_API_KEYS_LIST", ["test_api_key_for_execute_call"])
    monkeypatch.setattr(api_client, "api_key_loaded_successfully", True)
    monkeypatch.setattr(api_client, "current_api_key_index", 0)

    mock_client_instance = MagicMock(spec=api_client.genai.Client)
    
    # Mock para o método real que será chamado dentro de _api_call_task
    mock_generate_content_on_models = MagicMock(spec=mock_client_instance.models.generate_content)
    
    mock_response_obj = MagicMock(spec=genai_types.GenerateContentResponse)
    mock_response_obj.text = "Mocked LLM Response for execute_gemini_call"
    mock_response_obj.prompt_feedback = None
    mock_response_obj.candidates = [MagicMock(finish_reason=genai_types.FinishReason.STOP)]
    mock_generate_content_on_models.return_value = mock_response_obj
    
    # Configura o mock_client_instance para que .models.generate_content seja nosso mock
    mock_client_instance.models.generate_content = mock_generate_content_on_models
    
    mock_executor_instance = MagicMock(spec=api_client.concurrent.futures.ThreadPoolExecutor)
    def immediate_submit(func, *args_func, **kwargs_func): # Renomeado para evitar conflito com args do teste
        future = MagicMock(spec=api_client.concurrent.futures.Future)
        try:
            result = func(*args_func, **kwargs_func)
            future.result.return_value = result
            future.exception.return_value = None
        except Exception as e:
            future.result.side_effect = e 
            future.exception.return_value = e
        return future
    mock_executor_instance.submit.side_effect = immediate_submit

    with patch("scripts.llm_core.api_client.genai.Client", return_value=mock_client_instance) as mock_gen_client_ctor, \
         patch("scripts.llm_core.api_client.concurrent.futures.ThreadPoolExecutor", return_value=mock_executor_instance) as mock_thread_pool_ctor:
        
        api_client.genai_client = None 
        api_client.gemini_initialized_successfully = False
        api_client.api_executor = None 
            
        startup_success = api_client.startup_api_resources(verbose=False)
        assert startup_success
                
        yield mock_generate_content_on_models # O teste vai verificar este mock


# Testes para execute_gemini_call (AC3 da Issue #48) - Modo Mock
def test_execute_gemini_call_simple_payload(mock_gemini_services_for_execute_call):
    mock_generate_content_method = mock_gemini_services_for_execute_call
    model_name = "gemini-test-simple"
    contents = [genai_types.Part(text="Simple test")]
    
    response_text = api_client.execute_gemini_call(model_name, contents, config=None, verbose=False)
    
    assert response_text == "Mocked LLM Response for execute_gemini_call"
    mock_generate_content_method.assert_called_once_with(
        model=model_name,
        contents=contents,
        config=None 
    )

def test_execute_gemini_call_with_generate_content_config_obj(mock_gemini_services_for_execute_call):
    mock_generate_content_method = mock_gemini_services_for_execute_call
    model_name = "gemini-test-gcc-obj"
    contents = [genai_types.Part(text="Test with GCC obj")]
    config_obj = genai_types.GenerateContentConfig(temperature=0.8)

    api_client.execute_gemini_call(model_name, contents, config=config_obj, verbose=False)

    mock_generate_content_method.assert_called_once_with(
        model=model_name,
        contents=contents,
        config=config_obj
    )

def test_execute_gemini_call_with_generation_config_obj(mock_gemini_services_for_execute_call):
    mock_generate_content_method = mock_gemini_services_for_execute_call
    model_name = "gemini-test-gc-obj"
    contents = [genai_types.Part(text="Test with GenConf obj")]
    gen_config_obj = genai_types.GenerationConfig(temperature=0.6, max_output_tokens=50)
    
    expected_api_config = genai_types.GenerateContentConfig(
        temperature=0.6, max_output_tokens=50
    )

    api_client.execute_gemini_call(model_name, contents, config=gen_config_obj, verbose=False)
    
    called_args, called_kwargs = mock_generate_content_method.call_args
    assert called_kwargs['model'] == model_name
    assert called_kwargs['contents'] == contents
    assert isinstance(called_kwargs['config'], genai_types.GenerateContentConfig)
    assert called_kwargs['config'].temperature == expected_api_config.temperature
    assert called_kwargs['config'].max_output_tokens == expected_api_config.max_output_tokens

def test_execute_gemini_call_with_dict_config(mock_gemini_services_for_execute_call):
    mock_generate_content_method = mock_gemini_services_for_execute_call
    model_name = "gemini-test-dict-conf"
    contents = [genai_types.Part(text="Test with dict config")]
    config_dict = {"temperature": 0.3, "top_p": 0.7}
    expected_api_config = genai_types.GenerateContentConfig(temperature=0.3, top_p=0.7)

    api_client.execute_gemini_call(model_name, contents, config=config_dict, verbose=False)

    called_args, called_kwargs = mock_generate_content_method.call_args
    assert isinstance(called_kwargs['config'], genai_types.GenerateContentConfig)
    assert called_kwargs['config'].temperature == expected_api_config.temperature
    assert called_kwargs['config'].top_p == expected_api_config.top_p

def test_execute_gemini_call_with_tools(mock_gemini_services_for_execute_call):
    mock_generate_content_method = mock_gemini_services_for_execute_call
    model_name = "gemini-test-tools"
    contents = [genai_types.Part(text="Test with tools")]
    tool_search = genai_types.Tool(google_search_retrieval=genai_types.GoogleSearchRetrieval())
    config_with_tools = genai_types.GenerateContentConfig(tools=[tool_search])

    api_client.execute_gemini_call(model_name, contents, config=config_with_tools, verbose=False)

    mock_generate_content_method.assert_called_once_with(
        model=model_name,
        contents=contents,
        config=config_with_tools
    )
    assert mock_generate_content_method.call_args[1]['config'].tools[0] == tool_search # type: ignore

def test_execute_gemini_call_with_empty_tools_list(mock_gemini_services_for_execute_call):
    mock_generate_content_method = mock_gemini_services_for_execute_call
    model_name = "gemini-test-empty-tools"
    contents = [genai_types.Part(text="Test with empty tools")]
    config_with_empty_tools = genai_types.GenerateContentConfig(tools=[])

    api_client.execute_gemini_call(model_name, contents, config=config_with_empty_tools, verbose=False)
    
    mock_generate_content_method.assert_called_once_with(
        model=model_name,
        contents=contents,
        config=config_with_empty_tools
    )
    assert mock_generate_content_method.call_args[1]['config'].tools == [] # type: ignore

def test_execute_gemini_call_with_multiple_contents(mock_gemini_services_for_execute_call):
    mock_generate_content_method = mock_gemini_services_for_execute_call
    model_name = "gemini-test-multi-parts"
    contents_multiple = [
        genai_types.Part(text="First part."),
        genai_types.Part(text="Second part, more text."),
    ]
    api_client.execute_gemini_call(model_name, contents_multiple, config=None, verbose=False)
    mock_generate_content_method.assert_called_once_with(
        model=model_name,
        contents=contents_multiple,
        config=None
    )

# Teste para AC4 da Issue #48 - Modo Live
@pytest.mark.live # Marcador para execução condicional via conftest.py
def test_execute_gemini_call_live_api_success(reset_module_globals_for_each_test):
    """
    Testa uma chamada real à API Gemini se a flag --live for fornecida
    e a GEMINI_API_KEY estiver configurada no ambiente.
    """
    # A fixture reset_module_globals_for_each_test é autouse e já rodou.
    # O conftest.py já deve ter carregado o .env para os.environ se existia.

    # Se este teste não for pulado pelo conftest.py, significa que:
    # 1. A flag --live FOI fornecida.
    # 2. A variável de ambiente GEMINI_API_KEY ESTÁ definida.

    # Inicializa os recursos da API (isso tentará carregar chaves e criar cliente real)
    startup_success = api_client.startup_api_resources(verbose=True)
    if not startup_success:
        pytest.skip("Falha ao inicializar recursos da API para teste live. Verifique GEMINI_API_KEY e conexão.")

    assert api_client.api_key_loaded_successfully, "API key deveria estar carregada para teste live."
    assert api_client.gemini_initialized_successfully, "Cliente Gemini deveria estar inicializado para teste live."
    assert api_client.genai_client is not None, "Instância do cliente Gemini não deveria ser None para teste live."
    assert api_client.api_executor is not None, "Executor da API não deveria ser None para teste live."

    model_name = core_config_module.GEMINI_MODEL_FLASH # Usar um modelo rápido e barato
    contents = [genai_types.Part(text="Live test: Simply respond with the word 'TestOK'.")]
    
    response_text = None
    try:
        response_text = api_client.execute_gemini_call(
            model_name=model_name,
            contents=contents,
            config=None, 
            verbose=True
        )
    except Exception as e:
        pytest.fail(f"execute_gemini_call levantou uma exceção inesperada no modo live: {e}\n{traceback.format_exc()}")

    assert response_text is not None, "Resposta do LLM não deveria ser None no modo live."
    assert isinstance(response_text, str), "Resposta do LLM deveria ser uma string no modo live."
    assert len(response_text.strip()) > 0, "Resposta do LLM não deveria estar vazia no modo live."
    
    # Para um teste live, é difícil prever a resposta exata, mas podemos verificar se a palavra-chave está presente.
    # O modelo pode adicionar formatação ou texto extra.
    assert "TestOK" in response_text, f"Resposta do LLM ('{response_text}') deveria conter 'TestOK' como solicitado no prompt live."

    print(f"\nResposta Live da API: '{response_text}'")


def teardown_module(module):
    """Desliga o executor da API após todos os testes no módulo."""
    api_client.shutdown_api_resources(verbose=False)