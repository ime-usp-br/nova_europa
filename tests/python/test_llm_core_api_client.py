# tests/python/test_llm_core_api_client.py
import pytest
import os
from unittest.mock import patch, MagicMock, call
import sys
from scripts.llm_core import api_client
from google.genai import errors as google_genai_errors
from google.api_core import exceptions as google_api_core_exceptions
from google.genai import types as genai_types
from scripts.llm_core import config as core_config_module
import traceback
import concurrent.futures  # Adicionado para o teste de TimeoutError
import time  # Adicionado para mockar time.monotonic e time.sleep


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
    original_last_call_timestamps = dict(api_client.last_call_timestamps)

    api_client.GEMINI_API_KEYS_LIST = []
    api_client.current_api_key_index = 0
    api_client.genai_client = None
    if api_client.api_executor:
        # Shutdown an existing executor if it exists, but don't wait indefinitely
        # as some tests might mock it in a way that makes shutdown hang.
        try:
            api_client.api_executor.shutdown(wait=True, cancel_futures=True)
        except Exception:
            pass  # Ignore errors during shutdown in test cleanup
        api_client.api_executor = None
    api_client.api_key_loaded_successfully = False
    api_client.gemini_initialized_successfully = False
    api_client.last_call_timestamps.clear()

    with patch("scripts.llm_core.api_client.load_dotenv") as mock_load_dotenv_fixture:
        mock_load_dotenv_fixture.return_value = True
        yield mock_load_dotenv_fixture

    api_client.GEMINI_API_KEYS_LIST = original_keys
    api_client.current_api_key_index = original_index
    api_client.genai_client = original_client
    api_client.api_executor = original_executor
    api_client.api_key_loaded_successfully = original_key_loaded
    api_client.gemini_initialized_successfully = original_gemini_init
    api_client.last_call_timestamps = original_last_call_timestamps


# Testes para load_api_keys
@patch.dict(os.environ, {"GEMINI_API_KEY": "env_key1|env_key2"}, clear=True)
def test_load_api_keys_success(reset_module_globals_for_each_test):
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
            if getenv_side_effect.call_count == 1:  # type: ignore
                getenv_side_effect.call_count += 1  # type: ignore
                return None
            return "dotenv_key_A|dotenv_key_B"
        return os.environ.get(key, default)

    getenv_side_effect.call_count = 1  # type: ignore

    with patch("scripts.llm_core.api_client.os.getenv", side_effect=getenv_side_effect):
        assert api_client.load_api_keys(verbose=True) is True
    assert api_client.GEMINI_API_KEYS_LIST == ["dotenv_key_A", "dotenv_key_B"]
    assert api_client.api_key_loaded_successfully is True
    mock_dotenv_load_fixture.assert_called_once()


# Testes para initialize_genai_client (AC2 da Issue #48)
@patch("scripts.llm_core.api_client.genai.Client")
@patch.dict(os.environ, {"GEMINI_API_KEY": "env_init_key_for_ac2_test"}, clear=True)
def test_initialize_genai_client_success(
    mock_genai_client_constructor, reset_module_globals_for_each_test
):
    mock_dotenv_load_fixture = reset_module_globals_for_each_test
    mock_client_instance = MagicMock()
    mock_genai_client_constructor.return_value = mock_client_instance

    initialization_success = api_client.initialize_genai_client(verbose=True)

    assert initialization_success is True
    mock_genai_client_constructor.assert_called_once_with(
        api_key="env_init_key_for_ac2_test"
    )
    assert api_client.genai_client == mock_client_instance
    assert api_client.api_key_loaded_successfully is True
    assert api_client.gemini_initialized_successfully is True
    mock_dotenv_load_fixture.assert_not_called()


@pytest.fixture
def mock_gemini_services_for_execute_call(
    reset_module_globals_for_each_test, monkeypatch
):
    mock_dotenv_load_fixture = reset_module_globals_for_each_test

    monkeypatch.setattr(
        api_client, "GEMINI_API_KEYS_LIST", ["test_api_key_for_execute_call"]
    )
    monkeypatch.setattr(api_client, "api_key_loaded_successfully", True)
    monkeypatch.setattr(api_client, "current_api_key_index", 0)

    mock_client_instance = MagicMock(spec=api_client.genai.Client)

    mock_generate_content_on_models = MagicMock(spec=mock_client_instance.models.generate_content)  # type: ignore

    mock_response_obj = MagicMock(spec=genai_types.GenerateContentResponse)
    mock_response_obj.text = "Mocked LLM Response for execute_gemini_call"
    mock_response_obj.prompt_feedback = None
    mock_response_obj.candidates = [
        MagicMock(finish_reason=genai_types.FinishReason.STOP)
    ]
    mock_generate_content_on_models.return_value = mock_response_obj

    mock_client_instance.models = MagicMock()
    mock_client_instance.models.generate_content = mock_generate_content_on_models

    mock_executor_instance = MagicMock(spec=concurrent.futures.ThreadPoolExecutor)
    mock_executor_instance.submit = MagicMock()

    def immediate_submit(func, *args_func, **kwargs_func):
        future = MagicMock(spec=concurrent.futures.Future)
        try:
            result = func(*args_func, **kwargs_func)
            future.result.return_value = (
                result  # Se a função da task retorna normalmente
            )
            future.exception.return_value = None
        except Exception as e:
            future.result.side_effect = e  # Se a função da task levanta exceção
            future.exception.return_value = e
        return future  # O mock_executor_instance.submit retorna este future mockado

    mock_executor_instance.submit.side_effect = immediate_submit

    with patch(
        "scripts.llm_core.api_client.genai.Client", return_value=mock_client_instance
    ) as mock_gen_client_ctor, patch(
        "scripts.llm_core.api_client.concurrent.futures.ThreadPoolExecutor",
        return_value=mock_executor_instance,
    ) as mock_thread_pool_ctor:

        api_client.genai_client = None
        api_client.gemini_initialized_successfully = False
        api_client.api_executor = None

        startup_success = api_client.startup_api_resources(verbose=False)
        assert (
            startup_success
        ), "Falha no setup da fixture mock_gemini_services_for_execute_call: startup_api_resources falhou."

        yield mock_generate_content_on_models


# Testes para execute_gemini_call (AC3 da Issue #48) - Modo Mock
def test_execute_gemini_call_simple_payload(mock_gemini_services_for_execute_call):
    mock_generate_content_method = mock_gemini_services_for_execute_call
    model_name = "gemini-test-simple"
    contents = [genai_types.Part(text="Simple test")]

    response_text = api_client.execute_gemini_call(
        model_name, contents, config=None, verbose=False
    )

    assert response_text == "Mocked LLM Response for execute_gemini_call"
    mock_generate_content_method.assert_called_once_with(
        model=model_name, contents=contents, config=None
    )


def test_execute_gemini_call_with_generate_content_config_obj(
    mock_gemini_services_for_execute_call,
):
    mock_generate_content_method = mock_gemini_services_for_execute_call
    model_name = "gemini-test-gcc-obj"
    contents = [genai_types.Part(text="Test with GCC obj")]
    config_obj = genai_types.GenerateContentConfig(temperature=0.8)

    api_client.execute_gemini_call(
        model_name, contents, config=config_obj, verbose=False
    )

    mock_generate_content_method.assert_called_once_with(
        model=model_name, contents=contents, config=config_obj
    )


def test_execute_gemini_call_with_generation_config_obj(
    mock_gemini_services_for_execute_call,
):
    mock_generate_content_method = mock_gemini_services_for_execute_call
    model_name = "gemini-test-gc-obj"
    contents = [genai_types.Part(text="Test with GenConf obj")]
    gen_config_obj = genai_types.GenerationConfig(temperature=0.6, max_output_tokens=50)

    expected_api_config = genai_types.GenerateContentConfig(
        temperature=0.6, max_output_tokens=50
    )

    api_client.execute_gemini_call(
        model_name, contents, config=gen_config_obj, verbose=False
    )

    called_args, called_kwargs = mock_generate_content_method.call_args
    assert called_kwargs["model"] == model_name
    assert called_kwargs["contents"] == contents
    assert isinstance(called_kwargs["config"], genai_types.GenerateContentConfig)
    assert called_kwargs["config"].temperature == expected_api_config.temperature
    assert (
        called_kwargs["config"].max_output_tokens
        == expected_api_config.max_output_tokens
    )


def test_execute_gemini_call_with_dict_config(mock_gemini_services_for_execute_call):
    mock_generate_content_method = mock_gemini_services_for_execute_call
    model_name = "gemini-test-dict-conf"
    contents = [genai_types.Part(text="Test with dict config")]
    config_dict = {"temperature": 0.3, "top_p": 0.7}
    expected_api_config = genai_types.GenerateContentConfig(temperature=0.3, top_p=0.7)

    api_client.execute_gemini_call(
        model_name, contents, config=config_dict, verbose=False
    )

    called_args, called_kwargs = mock_generate_content_method.call_args
    assert isinstance(called_kwargs["config"], genai_types.GenerateContentConfig)
    assert called_kwargs["config"].temperature == expected_api_config.temperature
    assert called_kwargs["config"].top_p == expected_api_config.top_p


def test_execute_gemini_call_with_tools(mock_gemini_services_for_execute_call):
    mock_generate_content_method = mock_gemini_services_for_execute_call
    model_name = "gemini-test-tools"
    contents = [genai_types.Part(text="Test with tools")]
    tool_search = genai_types.Tool(
        google_search_retrieval=genai_types.GoogleSearchRetrieval()
    )
    config_with_tools_dict = {"tools": [tool_search]}

    api_client.execute_gemini_call(
        model_name, contents, config=config_with_tools_dict, verbose=False
    )

    called_args, called_kwargs = mock_generate_content_method.call_args
    assert isinstance(called_kwargs["config"], genai_types.GenerateContentConfig)
    assert called_kwargs["config"].tools is not None
    assert len(called_kwargs["config"].tools) == 1
    assert isinstance(called_kwargs["config"].tools[0], genai_types.Tool)
    assert called_kwargs["config"].tools[0].google_search_retrieval is not None


def test_execute_gemini_call_with_empty_tools_list(
    mock_gemini_services_for_execute_call,
):
    mock_generate_content_method = mock_gemini_services_for_execute_call
    model_name = "gemini-test-empty-tools"
    contents = [genai_types.Part(text="Test with empty tools")]
    config_with_empty_tools = genai_types.GenerateContentConfig(tools=[])

    api_client.execute_gemini_call(
        model_name, contents, config=config_with_empty_tools, verbose=False
    )

    mock_generate_content_method.assert_called_once_with(
        model=model_name, contents=contents, config=config_with_empty_tools
    )
    assert mock_generate_content_method.call_args[1]["config"].tools == []


def test_execute_gemini_call_with_multiple_contents(
    mock_gemini_services_for_execute_call,
):
    mock_generate_content_method = mock_gemini_services_for_execute_call
    model_name = "gemini-test-multi-parts"
    contents_multiple = [
        genai_types.Part(text="First part."),
        genai_types.Part(text="Second part, more text."),
    ]
    api_client.execute_gemini_call(
        model_name, contents_multiple, config=None, verbose=False
    )
    mock_generate_content_method.assert_called_once_with(
        model=model_name, contents=contents_multiple, config=None
    )


# Teste para AC4 da Issue #48 - Modo Live
@pytest.mark.live
def test_execute_gemini_call_live_api_success(reset_module_globals_for_each_test):
    startup_success = api_client.startup_api_resources(verbose=True)
    if not startup_success:
        pytest.skip(
            "Falha ao inicializar recursos da API para teste live. Verifique GEMINI_API_KEY e conexão."
        )

    assert api_client.api_key_loaded_successfully
    assert api_client.gemini_initialized_successfully
    assert api_client.genai_client is not None
    assert api_client.api_executor is not None

    model_name = core_config_module.GEMINI_MODEL_FLASH
    contents = [
        genai_types.Part(text="Live test: Simply respond with the word 'TestOK'.")
    ]

    response_text = None
    try:
        response_text = api_client.execute_gemini_call(
            model_name=model_name, contents=contents, config=None, verbose=True
        )
    except Exception as e:
        pytest.fail(
            f"execute_gemini_call levantou uma exceção inesperada no modo live: {e}\n{traceback.format_exc()}"
        )

    assert response_text is not None
    assert isinstance(response_text, str)
    assert len(response_text.strip()) > 0
    assert "TestOK" in response_text
    print(f"\nResposta Live da API: '{response_text}'")


# Teste para AC5 da Issue #48
@patch("scripts.llm_core.api_client.time.sleep")
@patch("scripts.llm_core.api_client.concurrent.futures.ThreadPoolExecutor")
@patch("scripts.llm_core.api_client.genai.Client")
@patch.dict(os.environ, {"GEMINI_API_KEY": "key_limited|key_works"}, clear=True)
def test_execute_gemini_call_rotates_key_on_resource_exhausted(
    mock_genai_client_constructor: MagicMock,
    mock_thread_pool_executor_constructor: MagicMock,
    mock_time_sleep: MagicMock,
    reset_module_globals_for_each_test,
):
    mock_client_instance_key1 = MagicMock(spec=api_client.genai.Client)
    mock_client_instance_key1.models = MagicMock()

    mock_client_instance_key2 = MagicMock(spec=api_client.genai.Client)
    mock_client_instance_key2.models = MagicMock()

    mock_genai_client_constructor.side_effect = [
        mock_client_instance_key1,
        mock_client_instance_key2,
    ]

    mock_success_response = MagicMock(spec=genai_types.GenerateContentResponse)
    mock_success_response.text = "Success after key rotation"
    mock_success_response.prompt_feedback = None
    mock_success_response.candidates = [
        MagicMock(finish_reason=genai_types.FinishReason.STOP)
    ]

    mock_client_instance_key1.models.generate_content.side_effect = (
        google_api_core_exceptions.ResourceExhausted("Rate limit on key_limited")
    )

    mock_client_instance_key2.models.generate_content.return_value = (
        mock_success_response
    )

    mock_executor_instance = MagicMock(spec=concurrent.futures.ThreadPoolExecutor)
    mock_executor_instance.submit = MagicMock()

    def immediate_submit(func, *args_func_param, **kwargs_func_param):
        future = MagicMock(spec=concurrent.futures.Future)
        try:
            result = func(*args_func_param, **kwargs_func_param)
            future.result.return_value = result
            future.exception.return_value = None
        except Exception as e:
            future.result.side_effect = e
            future.exception.return_value = e
        return future

    mock_executor_instance.submit.side_effect = immediate_submit
    mock_thread_pool_executor_constructor.return_value = mock_executor_instance

    assert api_client.load_api_keys(verbose=True) is True
    assert api_client.GEMINI_API_KEYS_LIST == ["key_limited", "key_works"]
    assert api_client.current_api_key_index == 0

    assert api_client.startup_api_resources(verbose=True)

    model_name = "gemini-test-rotation"
    contents = [genai_types.Part(text="Test rotation")]

    response_text = api_client.execute_gemini_call(
        model_name, contents, config=None, verbose=True, sleep_on_retry=0.01
    )

    assert response_text == "Success after key rotation"

    assert mock_genai_client_constructor.call_count == 2
    calls_to_client_ctor = mock_genai_client_constructor.call_args_list
    assert calls_to_client_ctor[0] == call(api_key="key_limited")
    assert calls_to_client_ctor[1] == call(api_key="key_works")

    mock_client_instance_key1.models.generate_content.assert_called_once()
    mock_client_instance_key2.models.generate_content.assert_called_once()

    assert api_client.current_api_key_index == 1


# Novos Testes para AC6 da Issue #48
@patch("scripts.llm_core.api_client.time.sleep")
@patch("scripts.llm_core.api_client.concurrent.futures.ThreadPoolExecutor")
@patch("scripts.llm_core.api_client.genai.Client")
@patch.dict(
    os.environ, {"GEMINI_API_KEY": "key_server_error|key_works_server"}, clear=True
)
def test_execute_gemini_call_rotates_key_on_server_error(
    mock_genai_client_constructor: MagicMock,
    mock_thread_pool_executor_constructor: MagicMock,
    mock_time_sleep: MagicMock,
    reset_module_globals_for_each_test,
):
    mock_client_instance_key1 = MagicMock(spec=api_client.genai.Client)
    mock_client_instance_key1.models = MagicMock()
    mock_client_instance_key2 = MagicMock(spec=api_client.genai.Client)
    mock_client_instance_key2.models = MagicMock()
    mock_genai_client_constructor.side_effect = [
        mock_client_instance_key1,
        mock_client_instance_key2,
    ]

    mock_success_response = MagicMock(spec=genai_types.GenerateContentResponse)
    mock_success_response.text = "Success after server error"
    mock_success_response.prompt_feedback = None
    mock_success_response.candidates = [
        MagicMock(finish_reason=genai_types.FinishReason.STOP)
    ]

    simulated_response_json_for_server_error = {
        "error": {
            "code": 500,
            "message": "Simulated Server Error from test",
            "status": "INTERNAL_SERVER_ERROR",
        }
    }
    simulated_server_error_instance = google_genai_errors.ServerError(
        code=500, response_json=simulated_response_json_for_server_error, response=None
    )
    mock_client_instance_key1.models.generate_content.side_effect = (
        simulated_server_error_instance
    )
    mock_client_instance_key2.models.generate_content.return_value = (
        mock_success_response
    )

    mock_executor_instance = MagicMock(spec=concurrent.futures.ThreadPoolExecutor)
    mock_executor_instance.submit = MagicMock()

    def immediate_submit(func, *args, **kwargs):
        future = MagicMock(spec=concurrent.futures.Future)
        try:
            result = func(*args, **kwargs)
            future.result.return_value = result
            future.exception.return_value = None
        except Exception as e:
            future.result.side_effect = e
            future.exception.return_value = e
        return future

    mock_executor_instance.submit.side_effect = immediate_submit
    mock_thread_pool_executor_constructor.return_value = mock_executor_instance

    api_client.load_api_keys(verbose=True)
    api_client.startup_api_resources(verbose=True)

    response_text = api_client.execute_gemini_call(
        "gemini-test-server-error",
        [genai_types.Part(text="Test ServerError")],
        config=None,
        verbose=True,
        sleep_on_retry=0.01,
    )
    assert response_text == "Success after server error"
    assert mock_genai_client_constructor.call_count == 2
    assert mock_genai_client_constructor.call_args_list[0] == call(
        api_key="key_server_error"
    )
    assert mock_genai_client_constructor.call_args_list[1] == call(
        api_key="key_works_server"
    )
    mock_client_instance_key1.models.generate_content.assert_called_once()
    mock_client_instance_key2.models.generate_content.assert_called_once()
    assert api_client.current_api_key_index == 1


@patch("scripts.llm_core.api_client.time.sleep")
@patch("scripts.llm_core.api_client.concurrent.futures.ThreadPoolExecutor")
@patch("scripts.llm_core.api_client.genai.Client")
@patch.dict(
    os.environ, {"GEMINI_API_KEY": "key_deadline|key_works_deadline"}, clear=True
)
def test_execute_gemini_call_rotates_key_on_deadline_exceeded(
    mock_genai_client_constructor: MagicMock,
    mock_thread_pool_executor_constructor: MagicMock,
    mock_time_sleep: MagicMock,
    reset_module_globals_for_each_test,
):
    mock_client_instance_key1 = MagicMock(spec=api_client.genai.Client)
    mock_client_instance_key1.models = MagicMock()
    mock_client_instance_key2 = MagicMock(spec=api_client.genai.Client)
    mock_client_instance_key2.models = MagicMock()
    mock_genai_client_constructor.side_effect = [
        mock_client_instance_key1,
        mock_client_instance_key2,
    ]

    mock_success_response = MagicMock(spec=genai_types.GenerateContentResponse)
    mock_success_response.text = "Success after deadline exceeded"
    mock_success_response.prompt_feedback = None
    mock_success_response.candidates = [
        MagicMock(finish_reason=genai_types.FinishReason.STOP)
    ]

    mock_client_instance_key1.models.generate_content.side_effect = (
        google_api_core_exceptions.DeadlineExceeded("Simulated DeadlineExceeded")
    )
    mock_client_instance_key2.models.generate_content.return_value = (
        mock_success_response
    )

    mock_executor_instance = MagicMock(spec=concurrent.futures.ThreadPoolExecutor)
    mock_executor_instance.submit = MagicMock()

    def immediate_submit(func, *args, **kwargs):
        future = MagicMock(spec=concurrent.futures.Future)
        try:
            result = func(*args, **kwargs)
            future.result.return_value = result
            future.exception.return_value = None
        except Exception as e:
            future.result.side_effect = e
            future.exception.return_value = e
        return future

    mock_executor_instance.submit.side_effect = immediate_submit
    mock_thread_pool_executor_constructor.return_value = mock_executor_instance

    api_client.load_api_keys(verbose=True)
    api_client.startup_api_resources(verbose=True)

    response_text = api_client.execute_gemini_call(
        "gemini-test-deadline",
        [genai_types.Part(text="Test DeadlineExceeded")],
        config=None,
        verbose=True,
        sleep_on_retry=0.01,
    )
    assert response_text == "Success after deadline exceeded"
    assert mock_genai_client_constructor.call_count == 2
    assert mock_genai_client_constructor.call_args_list[0] == call(
        api_key="key_deadline"
    )
    assert mock_genai_client_constructor.call_args_list[1] == call(
        api_key="key_works_deadline"
    )
    mock_client_instance_key1.models.generate_content.assert_called_once()
    mock_client_instance_key2.models.generate_content.assert_called_once()
    assert api_client.current_api_key_index == 1


# Novo Teste para AC7 da Issue #48
def test_execute_gemini_call_handles_prompt_blocked_by_safety(
    mock_gemini_services_for_execute_call,
):
    mock_generate_content_method = mock_gemini_services_for_execute_call

    mock_blocked_response = MagicMock(spec=genai_types.GenerateContentResponse)
    mock_blocked_response.text = ""

    mock_prompt_feedback = MagicMock(
        spec=genai_types.GenerateContentResponsePromptFeedback
    )
    mock_prompt_feedback.block_reason = genai_types.BlockedReason.SAFETY
    mock_prompt_feedback.block_reason_message = "Blocked due to safety concerns."

    mock_blocked_response.prompt_feedback = mock_prompt_feedback
    mock_blocked_response.candidates = []

    mock_generate_content_method.return_value = mock_blocked_response

    model_name = "gemini-test-safety-block"
    contents = [genai_types.Part(text="Potentially unsafe prompt")]

    with pytest.raises(RuntimeError) as excinfo:
        api_client.execute_gemini_call(model_name, contents, config=None, verbose=True)

    expected_block_reason_name = genai_types.BlockedReason(
        genai_types.BlockedReason.SAFETY
    ).name
    assert str(excinfo.value) == f"Prompt bloqueado: {expected_block_reason_name}"

    mock_generate_content_method.assert_called_once_with(
        model=model_name, contents=contents, config=None
    )


# Teste para AC8 da Issue #48
@patch("scripts.llm_core.api_client.time.sleep")
@patch("scripts.llm_core.api_client.concurrent.futures.ThreadPoolExecutor")
@patch("scripts.llm_core.api_client.genai.Client")
@patch.dict(
    os.environ, {"GEMINI_API_KEY": "key_apierror_429|key_works_apierror"}, clear=True
)
def test_execute_gemini_call_rotates_key_on_api_error_429_by_message(
    mock_genai_client_constructor: MagicMock,
    mock_thread_pool_executor_constructor: MagicMock,
    mock_time_sleep: MagicMock,
    reset_module_globals_for_each_test,
):
    mock_client_instance_key1 = MagicMock(spec=api_client.genai.Client)
    mock_client_instance_key1.models = MagicMock()
    mock_client_instance_key2 = MagicMock(spec=api_client.genai.Client)
    mock_client_instance_key2.models = MagicMock()
    mock_genai_client_constructor.side_effect = [
        mock_client_instance_key1,
        mock_client_instance_key2,
    ]

    mock_success_response = MagicMock(spec=genai_types.GenerateContentResponse)
    mock_success_response.text = "Success after APIError 429 (message) rotation"
    mock_success_response.prompt_feedback = None
    mock_success_response.candidates = [
        MagicMock(finish_reason=genai_types.FinishReason.STOP)
    ]

    simulated_response_json_for_api_error = {
        "error": {
            "code": 429,
            "message": "Quota limit exceeded for this API key.",
            "status": "RESOURCE_EXHAUSTED",
        }
    }
    api_error_to_raise = google_genai_errors.APIError(
        code=500, response_json=simulated_response_json_for_api_error, response=None
    )

    mock_client_instance_key1.models.generate_content.side_effect = api_error_to_raise
    mock_client_instance_key2.models.generate_content.return_value = (
        mock_success_response
    )

    mock_executor_instance = MagicMock(spec=concurrent.futures.ThreadPoolExecutor)
    mock_executor_instance.submit = MagicMock()  # Garante que 'submit' é um mock

    def immediate_submit(func, *args_func_param, **kwargs_func_param):
        future = MagicMock(spec=concurrent.futures.Future)
        try:
            result = func(*args_func_param, **kwargs_func_param)
            future.result.return_value = result
            future.exception.return_value = None
        except Exception as e_submit:
            future.result.side_effect = e_submit
            future.exception.return_value = e_submit
        return future

    mock_executor_instance.submit.side_effect = immediate_submit
    mock_thread_pool_executor_constructor.return_value = mock_executor_instance

    api_client.load_api_keys(verbose=True)
    api_client.startup_api_resources(verbose=True)

    response_text = api_client.execute_gemini_call(
        "gemini-test-api-error-msg-rotation",
        [genai_types.Part(text="Test APIError by message")],
        config=None,
        verbose=True,
        sleep_on_retry=0.01,
    )

    assert response_text == "Success after APIError 429 (message) rotation"
    assert mock_genai_client_constructor.call_count == 2
    assert mock_genai_client_constructor.call_args_list[0] == call(
        api_key="key_apierror_429"
    )
    assert mock_genai_client_constructor.call_args_list[1] == call(
        api_key="key_works_apierror"
    )
    mock_client_instance_key1.models.generate_content.assert_called_once()
    mock_client_instance_key2.models.generate_content.assert_called_once()
    assert api_client.current_api_key_index == 1


# Novo Teste para APIError que não é de rate limit
@patch("scripts.llm_core.api_client.concurrent.futures.ThreadPoolExecutor")
@patch("scripts.llm_core.api_client.genai.Client")
@patch.dict(
    os.environ, {"GEMINI_API_KEY": "key_generic_api_error_no_rotate"}, clear=True
)
def test_execute_gemini_call_reraises_non_rate_limit_api_error(
    mock_genai_client_constructor: MagicMock,
    mock_thread_pool_executor_constructor: MagicMock,
    reset_module_globals_for_each_test,
):
    mock_client_instance = MagicMock(spec=api_client.genai.Client)
    mock_client_instance.models = MagicMock()
    mock_genai_client_constructor.return_value = mock_client_instance

    simulated_response_json_for_generic_error = {
        "error": {
            "code": 400,
            "message": "Some other API error occurred, not related to rate limits.",
            "status": "INVALID_ARGUMENT",
        }
    }
    generic_api_error_to_raise = google_genai_errors.APIError(
        code=400, response_json=simulated_response_json_for_generic_error, response=None
    )
    mock_client_instance.models.generate_content.side_effect = (
        generic_api_error_to_raise
    )

    mock_executor_returned_by_constructor = MagicMock(
        spec=concurrent.futures.ThreadPoolExecutor
    )
    mock_executor_returned_by_constructor.submit = MagicMock()
    mock_thread_pool_executor_constructor.return_value = (
        mock_executor_returned_by_constructor
    )

    def immediate_submit_for_test(func_to_call, *call_args, **call_kwargs):
        future = MagicMock(spec=concurrent.futures.Future)
        try:
            result = func_to_call(*call_args, **call_kwargs)
            future.result.return_value = result
            future.exception.return_value = None
        except Exception as e_call:
            future.result.side_effect = e_call
            future.exception.return_value = e_call
        return future

    mock_executor_returned_by_constructor.submit.side_effect = immediate_submit_for_test

    api_client.load_api_keys(verbose=True)
    api_client.startup_api_resources(verbose=True)

    model_name = "gemini-test-generic-api-error-no-rotate"
    contents = [genai_types.Part(text="Test generic APIError no rotate")]

    with pytest.raises(google_genai_errors.APIError) as excinfo:
        api_client.execute_gemini_call(model_name, contents, config=None, verbose=True)

    assert excinfo.value == generic_api_error_to_raise
    mock_genai_client_constructor.assert_called_once_with(
        api_key="key_generic_api_error_no_rotate"
    )
    mock_client_instance.models.generate_content.assert_called_once()
    assert api_client.current_api_key_index == 0


# Teste para AC9 da Issue #48
@patch("scripts.llm_core.api_client.time.sleep")
def test_execute_gemini_call_handles_concurrent_futures_timeout(
    mock_time_sleep: MagicMock,
    reset_module_globals_for_each_test,
    mock_gemini_services_for_execute_call,  # Fixture que já mocka Client e ThreadPoolExecutor
):
    # O fixture mock_gemini_services_for_execute_call já fez startup_api_resources
    # e configurou api_client.api_executor para ser um mock.

    mock_future_that_timeouts = MagicMock(spec=concurrent.futures.Future)
    # Configura o método result() do mock_future_that_timeouts para levantar TimeoutError
    # quando chamado com timeout.
    mock_future_that_timeouts.result.side_effect = concurrent.futures.TimeoutError(
        "Simulated future.result() timeout"
    )

    # Sobrescreve o side_effect do método submit do api_executor mockado
    # para retornar nosso future especificamente configurado.
    api_client.api_executor.submit.side_effect = (
        lambda func, *args, **kwargs: mock_future_that_timeouts
    )

    model_name = "gemini-test-concurrent-timeout"
    contents = [genai_types.Part(text="Test content that should lead to timeout")]
    test_timeout_seconds = (
        0.01  # Um timeout muito curto para garantir que seja atingido no mock
    )

    with pytest.raises(TimeoutError) as excinfo:  # Esperamos a built-in TimeoutError
        api_client.execute_gemini_call(
            model_name,
            contents,
            config=None,
            timeout_seconds=test_timeout_seconds,  # Passa o timeout para execute_gemini_call
            verbose=True,
        )

    # Verifica se a mensagem impressa no stderr foi feita (isso requer capsys)
    # Opcional, mas bom para confirmar o log interno da função.
    # captured = capsys.readouterr()
    # assert f"Chamada API excedeu o tempo limite de {test_timeout_seconds}s" in captured.err

    # Verifica se o método submit do executor foi chamado (indicando que a task foi submetida)
    api_client.api_executor.submit.assert_called_once()
    # Pega a função que foi submetida (a _api_call_task interna)
    submitted_callable = api_client.api_executor.submit.call_args[0][0]
    assert callable(submitted_callable)

    # Verifica se o método result do future mockado foi chamado com o timeout correto
    mock_future_that_timeouts.result.assert_called_once_with(
        timeout=test_timeout_seconds
    )

    # Verifica se a rotação de chaves NÃO ocorreu, pois TimeoutError do future.result
    # não deve acionar a lógica de rotação de chave por ResourceExhausted/ServerError.
    assert api_client.current_api_key_index == 0  # Assumindo que começou em 0
    mock_time_sleep.assert_not_called()  # O sleep é para rotação de chave, não para este tipo de timeout


def test_calculate_max_input_tokens_default_values():
    """Testa o cálculo com valores padrão de config."""
    model_name = "gemini-1.5-flash-preview-0520"  # Modelo conhecido
    core_config_module.MODEL_INPUT_TOKEN_LIMITS[model_name] = 100000
    core_config_module.DEFAULT_OUTPUT_TOKEN_ESTIMATE = 5000
    core_config_module.DEFAULT_TOKEN_SAFETY_BUFFER = 1000

    expected = 100000 - 5000 - 1000
    assert api_client.calculate_max_input_tokens(model_name) == expected


def test_calculate_max_input_tokens_with_overrides():
    """Testa o cálculo com overrides para estimativa de saída e buffer."""
    model_name = "gemini-1.5-pro-preview-0520"  # Modelo conhecido
    core_config_module.MODEL_INPUT_TOKEN_LIMITS[model_name] = 200000

    expected = 200000 - 10000 - 2000  # 10k saida, 2k buffer
    assert (
        api_client.calculate_max_input_tokens(
            model_name, estimated_output_tokens=10000, safety_buffer=2000
        )
        == expected
    )


def test_calculate_max_input_tokens_unknown_model():
    """Testa o cálculo para um modelo não listado, usando o default do config."""
    model_name = "unknown-model-for-test"
    # Não está em MODEL_INPUT_TOKEN_LIMITS, então deve usar o "default"
    # Supondo que "default" seja 30000
    core_config_module.MODEL_INPUT_TOKEN_LIMITS["default"] = 30000
    core_config_module.DEFAULT_OUTPUT_TOKEN_ESTIMATE = 2000
    core_config_module.DEFAULT_TOKEN_SAFETY_BUFFER = 1000
    expected = 30000 - 2000 - 1000
    assert api_client.calculate_max_input_tokens(model_name) == expected


def test_calculate_max_input_tokens_prevents_non_positive():
    """Testa se o cálculo retorna um mínimo positivo se o resultado for <= 0."""
    model_name = "small-model"
    core_config_module.MODEL_INPUT_TOKEN_LIMITS[model_name] = 1000
    core_config_module.DEFAULT_OUTPUT_TOKEN_ESTIMATE = 800
    core_config_module.DEFAULT_TOKEN_SAFETY_BUFFER = 300  # 1000 - 800 - 300 = -100

    # Espera-se que retorne o mínimo (100, conforme definido na função)
    assert api_client.calculate_max_input_tokens(model_name) == 100

    # Teste com estimativa e buffer exatamente iguais ao limite
    core_config_module.MODEL_INPUT_TOKEN_LIMITS[model_name] = 1000
    core_config_module.DEFAULT_OUTPUT_TOKEN_ESTIMATE = 800
    core_config_module.DEFAULT_TOKEN_SAFETY_BUFFER = 200  # 1000 - 800 - 200 = 0
    assert api_client.calculate_max_input_tokens(model_name) == 100


# --- Testes para AC 2.3: Rate Limiter RPM ---
@patch("scripts.llm_core.api_client.time.monotonic")
@patch("scripts.llm_core.api_client.time.sleep")
def test_rpm_rate_limiter_first_call(
    mock_sleep, mock_monotonic, mock_gemini_services_for_execute_call
):
    mock_generate_content_method = mock_gemini_services_for_execute_call
    model_name = "gemini-2.5-flash-preview-05-20"  # RPM 10 -> interval 6s
    core_config_module.MODEL_RPM_LIMITS[model_name] = (
        60  # Forçar RPM 60 -> Intervalo 1s para facilitar teste
    )

    mock_monotonic.return_value = 100.0

    api_client.execute_gemini_call(
        model_name, [genai_types.Part(text="test")], verbose=True
    )

    mock_sleep.assert_not_called()  # Primeira chamada, sem sleep
    assert api_client.last_call_timestamps[model_name] == 100.0


@patch("scripts.llm_core.api_client.time.monotonic")
@patch("scripts.llm_core.api_client.time.sleep")
def test_rpm_rate_limiter_waits_correctly(
    mock_sleep, mock_monotonic, mock_gemini_services_for_execute_call
):
    mock_generate_content_method = mock_gemini_services_for_execute_call
    model_name = "gemini-2.5-flash-preview-05-20"
    core_config_module.MODEL_RPM_LIMITS[model_name] = 60  # Intervalo de 1.0s

    # Primeira chamada:
    mock_monotonic.return_value = 200.0
    api_client.execute_gemini_call(
        model_name, [genai_types.Part(text="call1")], verbose=True
    )
    mock_sleep.assert_not_called()
    assert api_client.last_call_timestamps[model_name] == 200.0

    # Segunda chamada, 0.5s depois (deve esperar 0.5s)
    mock_monotonic.return_value = 200.5
    api_client.execute_gemini_call(
        model_name, [genai_types.Part(text="call2")], verbose=True
    )
    mock_sleep.assert_called_once()
    assert mock_sleep.call_args[0][0] == pytest.approx(0.5, abs=1e-3)
    # O timestamp da última chamada é atualizado para o momento *após* o sleep e *antes* da chamada API
    # current_time_mono (200.5) + wait_time (0.5) == 201.0 (se o tempo não passasse durante o sleep)
    # Na implementação real, o time.monotonic() é chamado novamente após o sleep.
    # Aqui, vamos verificar o valor que foi definido.
    # Se o mock_monotonic não mudar após o sleep, e last_call_timestamps for atualizado com current_time_mono (que não foi atualizado no mock)
    # o teste pode não ser ideal.
    # A lógica de atualização do timestamp em `execute_gemini_call` é:
    # last_call_timestamps[model_name] = time.monotonic() <- isso acontece *depois* do sleep
    # Então, se mock_monotonic ainda retorna 200.5, last_call_timestamps[model_name] será 200.5
    # Vamos precisar de um side_effect para mock_monotonic se quisermos simular a passagem do tempo *durante* o sleep
    # Para este teste, vamos assumir que o `time.monotonic()` após o sleep retornaria o tempo correto.
    # A verificação principal é que o sleep foi chamado com o valor correto.
    # O timestamp será o valor de mock_monotonic no momento da atribuição (após o sleep simulado).
    # Se o mock_monotonic não avançar, o timestamp será o mesmo: 200.5
    assert api_client.last_call_timestamps[model_name] == 200.5


@patch("scripts.llm_core.api_client.time.monotonic")
@patch("scripts.llm_core.api_client.time.sleep")
def test_rpm_rate_limiter_no_wait_if_interval_passed(
    mock_sleep, mock_monotonic, mock_gemini_services_for_execute_call
):
    mock_generate_content_method = mock_gemini_services_for_execute_call
    model_name = "gemini-1.5-pro"  # RPM 2 -> interval 30s
    core_config_module.MODEL_RPM_LIMITS[model_name] = 2

    mock_monotonic.return_value = 300.0
    api_client.execute_gemini_call(
        model_name, [genai_types.Part(text="call1 pro")], verbose=True
    )
    mock_sleep.assert_not_called()
    assert api_client.last_call_timestamps[model_name] == 300.0

    mock_monotonic.return_value = 330.1  # 30.1s depois
    api_client.execute_gemini_call(
        model_name, [genai_types.Part(text="call2 pro")], verbose=True
    )
    mock_sleep.assert_not_called()  # Não deve esperar
    assert api_client.last_call_timestamps[model_name] == 330.1


@patch("scripts.llm_core.api_client.time.monotonic")
@patch("scripts.llm_core.api_client.time.sleep")
def test_rpm_rate_limiter_uses_default_rpm(
    mock_sleep, mock_monotonic, mock_gemini_services_for_execute_call
):
    mock_generate_content_method = mock_gemini_services_for_execute_call
    model_name = "unknown-model-rpm-test"
    # RPM default é 5 -> interval 12s
    core_config_module.MODEL_RPM_LIMITS["default"] = 5

    mock_monotonic.return_value = 400.0
    api_client.execute_gemini_call(
        model_name, [genai_types.Part(text="call1 unknown")], verbose=True
    )
    assert api_client.last_call_timestamps[model_name] == 400.0

    mock_monotonic.return_value = 405.0  # 5s depois
    api_client.execute_gemini_call(
        model_name, [genai_types.Part(text="call2 unknown")], verbose=True
    )
    mock_sleep.assert_called_once()
    assert mock_sleep.call_args[0][0] == pytest.approx(7.0, abs=1e-3)  # 12 - 5 = 7
    assert api_client.last_call_timestamps[model_name] == 405.0


def teardown_module(module):
    api_client.shutdown_api_resources(verbose=False)
