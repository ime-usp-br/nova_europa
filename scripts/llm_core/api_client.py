# -*- coding: utf-8 -*-
"""
LLM Core API Client Module.
"""
import os
import sys
import time
import traceback
import concurrent.futures
from typing import List, Optional, Dict, Any, Union, Callable

from google import genai
from google.genai import types
from google.genai import errors as google_genai_errors
from google.api_core import exceptions as google_api_core_exceptions
from dotenv import load_dotenv
from tqdm import tqdm

from . import config as core_config

# Module-level globals for API client and state
GEMINI_API_KEYS_LIST: List[str] = []
current_api_key_index: int = 0
genai_client: Optional[genai.Client] = None
api_executor: Optional[concurrent.futures.ThreadPoolExecutor] = None
api_key_loaded_successfully: bool = False
gemini_initialized_successfully: bool = False


def load_api_keys(verbose: bool = False) -> bool:
    """Loads API keys from .env file or environment variables."""
    global GEMINI_API_KEYS_LIST, api_key_loaded_successfully, current_api_key_index

    if api_key_loaded_successfully:  # Evita recarregar se já carregado
        return True

    # Prioriza variáveis de ambiente do sistema
    api_key_string = os.getenv("GEMINI_API_KEY")

    # Se não encontrar no ambiente, tenta carregar do .env
    if not api_key_string:
        dotenv_path = core_config.PROJECT_ROOT / ".env"
        if dotenv_path.is_file():
            if verbose:
                print(
                    f"  Tentando carregar variáveis de ambiente de: {dotenv_path.relative_to(core_config.PROJECT_ROOT)}"
                )
            load_dotenv(dotenv_path=dotenv_path, verbose=verbose, override=True)
            api_key_string = os.getenv("GEMINI_API_KEY")
        elif verbose:
            print(
                f"  Arquivo .env não encontrado em {dotenv_path}. Usando apenas variáveis de ambiente do sistema (se houver)."
            )

    if not api_key_string:
        if verbose:  # Adiciona verbose aqui para o caso de falha
            print(
                "Erro: Variável de ambiente GEMINI_API_KEY não encontrada no sistema nem no arquivo .env.",
                file=sys.stderr,
            )
        api_key_loaded_successfully = False
        return False

    GEMINI_API_KEYS_LIST = [
        key.strip() for key in api_key_string.split("|") if key.strip()
    ]

    if not GEMINI_API_KEYS_LIST:
        print(
            "Erro: Formato da GEMINI_API_KEY inválido ou vazio. Use '|' para separar múltiplas chaves.",
            file=sys.stderr,
        )
        api_key_loaded_successfully = False
        return False

    current_api_key_index = 0
    api_key_loaded_successfully = True
    if verbose:
        print(f"  {len(GEMINI_API_KEYS_LIST)} Chave(s) de API GEMINI carregadas.")
    return True


def initialize_genai_client(verbose: bool = False) -> bool:
    """Initializes or reinitializes the global genai_client using the current API key."""
    global genai_client, gemini_initialized_successfully, GEMINI_API_KEYS_LIST, current_api_key_index

    # Garante que as chaves sejam carregadas antes de tentar inicializar o cliente
    if not api_key_loaded_successfully:
        if not load_api_keys(verbose):
            return False  # Falha ao carregar chaves, não pode inicializar

    if not GEMINI_API_KEYS_LIST or not (
        0 <= current_api_key_index < len(GEMINI_API_KEYS_LIST)
    ):
        if verbose:
            print(
                "  Aviso: Chaves de API não carregadas ou índice inválido. Impossível inicializar Gemini."
            )
        gemini_initialized_successfully = False
        return False

    active_key = GEMINI_API_KEYS_LIST[current_api_key_index]
    try:
        if verbose:
            print(
                f"  Inicializando Google GenAI Client com Key Index {current_api_key_index}..."
            )
        genai_client = genai.Client(
            api_key=active_key
        )  # Usa o genai importado globalmente
        if verbose:
            print("  Google GenAI Client inicializado com sucesso.")
        gemini_initialized_successfully = True
        return True
    except Exception as e:
        print(
            f"Erro ao inicializar Google GenAI Client com Key Index {current_api_key_index}: {e}",
            file=sys.stderr,
        )
        if verbose:
            traceback.print_exc(file=sys.stderr)
        gemini_initialized_successfully = False
        return False


def startup_api_resources(verbose: bool = False) -> bool:
    """Initializes API keys, client, and executor."""
    global api_executor
    if not api_key_loaded_successfully:  # Tenta carregar chaves se ainda não o fez
        if not load_api_keys(verbose):
            return False
    if (
        not gemini_initialized_successfully
    ):  # Tenta inicializar cliente se ainda não o fez
        if not initialize_genai_client(verbose):
            return False
    if not api_executor:
        api_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        if verbose:
            print("  API ThreadPoolExecutor inicializado.")
    return True


def shutdown_api_resources(verbose: bool = False):
    """Shuts down the API ThreadPoolExecutor."""
    global api_executor
    if api_executor:
        if verbose:
            print("  Encerrando API ThreadPoolExecutor...")
        api_executor.shutdown(
            wait=False
        )  # Não espera por tarefas pendentes ao encerrar
        api_executor = None
        if verbose:
            print("  API ThreadPoolExecutor encerrado.")


def rotate_api_key_and_reinitialize(verbose: bool = False) -> bool:
    """Rotates to the next API key and reinitializes the client."""
    global current_api_key_index, GEMINI_API_KEYS_LIST, gemini_initialized_successfully
    if not GEMINI_API_KEYS_LIST or len(GEMINI_API_KEYS_LIST) <= 1:
        if verbose:
            print(
                "  Aviso: Não é possível rotacionar (apenas uma ou nenhuma chave disponível).",
                file=sys.stderr,
            )
        return False

    start_index = current_api_key_index
    current_api_key_index = (current_api_key_index + 1) % len(GEMINI_API_KEYS_LIST)
    print(
        f"\n---> Rotacionando Chave de API para Índice {current_api_key_index} <---\n"
    )
    gemini_initialized_successfully = (
        False  # Marca como não inicializado antes de tentar a nova chave
    )

    if current_api_key_index == start_index:
        print(
            "Aviso: Ciclo completo por todas as chaves de API. Limites de taxa podem persistir.",
            file=sys.stderr,
        )

    return initialize_genai_client(verbose)


GenerateContentConfigType = Union[
    types.GenerationConfig, types.GenerateContentConfig, Dict[str, Any], None
]


def calculate_max_input_tokens(
    model_name: str,
    estimated_output_tokens: Optional[int] = None,
    safety_buffer: Optional[int] = None,
    verbose: bool = False
) -> int:
    """
    Calcula o número máximo de tokens de entrada permitidos para uma chamada à API Gemini.

    Args:
        model_name: O nome do modelo Gemini a ser usado (ex: "gemini-1.5-flash-preview-0520").
        estimated_output_tokens: Uma estimativa de quantos tokens a resposta da API irá gerar.
                                 Se None, usa core_config.DEFAULT_OUTPUT_TOKEN_ESTIMATE.
        safety_buffer: Um buffer de segurança para subtrair do limite total.
                       Se None, usa core_config.DEFAULT_TOKEN_SAFETY_BUFFER.
        verbose: Se True, imprime informações detalhadas sobre o cálculo.

    Returns:
        O número máximo de tokens de entrada calculados. Retorna um valor mínimo (ex: 100)
        se o cálculo resultar em um valor não positivo.
    """
    model_total_limit = core_config.MODEL_INPUT_TOKEN_LIMITS.get(
        model_name, core_config.MODEL_INPUT_TOKEN_LIMITS.get("default", 30000)
    )

    output_estimate = (
        estimated_output_tokens
        if estimated_output_tokens is not None
        else core_config.DEFAULT_OUTPUT_TOKEN_ESTIMATE
    )
    buffer = (
        safety_buffer
        if safety_buffer is not None
        else core_config.DEFAULT_TOKEN_SAFETY_BUFFER
    )

    max_input = model_total_limit - output_estimate - buffer

    if verbose:
        print(f"  Cálculo MAX_INPUT_TOKENS_PER_CALL para modelo '{model_name}':")
        print(f"    Limite total do modelo: {model_total_limit}")
        print(f"    Estimativa de saída: -{output_estimate}")
        print(f"    Buffer de segurança: -{buffer}")
        print(f"    ------------------------------------")
        print(f"    MAX_INPUT_TOKENS_PER_CALL calculado: {max_input}")

    # Garante que o valor retornado seja pelo menos um mínimo razoável (ex: 100)
    # para evitar problemas se o buffer/estimativa de saída forem muito grandes.
    # Um valor mínimo também previne zero ou negativo se o limite do modelo for muito pequeno.
    calculated_max_input = max(100, max_input)

    if verbose and calculated_max_input != max_input:
        print(f"    MAX_INPUT_TOKENS_PER_CALL ajustado para mínimo: {calculated_max_input}")

    return calculated_max_input


def execute_gemini_call(
    model_name: str,
    contents: List[types.Part],
    config: Optional[GenerateContentConfigType] = None,
    sleep_on_retry: float = core_config.DEFAULT_RATE_LIMIT_SLEEP,
    timeout_seconds: int = core_config.DEFAULT_API_TIMEOUT_SECONDS,
    verbose: bool = False,
) -> str:
    """
    Executes a call to the Gemini API with provided model, contents, and config.
    Handles rate limiting with key rotation and timeouts.
    """
    global genai_client, api_executor

    if not gemini_initialized_successfully or not genai_client:
        if not startup_api_resources(verbose):
            raise RuntimeError(
                "GenAI client ou executor não pôde ser inicializado. Verifique as chaves de API e a conexão."
            )
    if not api_executor:
        raise RuntimeError(
            "API Executor não inicializado. Chame startup_api_resources() primeiro ou verifique a inicialização."
        )

    initial_key_index = current_api_key_index
    keys_tried_in_this_call = {initial_key_index}

    while True:

        def _api_call_task() -> types.GenerateContentResponse:
            if not genai_client:
                raise RuntimeError("Gemini client tornou-se não inicializado na task.")

            api_config_obj: Optional[types.GenerateContentConfig] = None
            if isinstance(config, dict):
                tools_list_from_dict = []
                if "tools" in config and config["tools"] is not None:
                    # Ensure tools are correctly formatted for GenerateContentConfig
                    for tool_item_config in config["tools"]:  # type: ignore
                        if isinstance(tool_item_config, types.Tool):
                            tools_list_from_dict.append(tool_item_config)
                        elif isinstance(tool_item_config, dict) and "google_search_retrieval" in tool_item_config:  # type: ignore
                            tools_list_from_dict.append(types.Tool(google_search_retrieval=types.GoogleSearchRetrieval(**tool_item_config["google_search_retrieval"])))  # type: ignore
                        # Add other tool types if necessary

                config_copy = config.copy()
                if tools_list_from_dict or (
                    "tools" in config and config["tools"] is None
                ):  # Only set if tools were processed or explicitly None
                    config_copy["tools"] = (
                        tools_list_from_dict if tools_list_from_dict else None
                    )

                api_config_obj = types.GenerateContentConfig(**config_copy)  # type: ignore

            elif isinstance(config, types.GenerateContentConfig):
                api_config_obj = config
            elif isinstance(config, types.GenerationConfig):
                api_config_obj = types.GenerateContentConfig(
                    candidate_count=config.candidate_count,
                    stop_sequences=config.stop_sequences,
                    max_output_tokens=config.max_output_tokens,
                    temperature=config.temperature,
                    top_p=config.top_p,
                    top_k=config.top_k,
                )

            try:
                if verbose:
                    print(
                        f"      -> Enviando para o modelo '{model_name}' com config: {api_config_obj}"
                    )
                return genai_client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=api_config_obj,
                )
            except Exception as inner_e:
                if verbose:
                    print(
                        f"      -> Erro interno na task API ({type(inner_e).__name__}): {inner_e}",
                        file=sys.stderr,
                    )
                raise inner_e

        future = None
        try:
            if verbose:
                print(
                    f"        -> Tentando chamada API com Key Index {current_api_key_index}, Timeout {timeout_seconds}s"
                )

            future = api_executor.submit(_api_call_task)
            response = future.result(timeout=timeout_seconds)

            if response.prompt_feedback and response.prompt_feedback.block_reason:
                block_reason_name = types.BlockedReason(
                    response.prompt_feedback.block_reason
                ).name
                print(
                    f"  Aviso: Prompt bloqueado devido a {block_reason_name}.",
                    file=sys.stderr,
                )
                raise RuntimeError(f"Prompt bloqueado: {block_reason_name}")

            if response.candidates:
                for candidate in response.candidates:
                    if hasattr(
                        candidate, "finish_reason"
                    ) and candidate.finish_reason not in (
                        types.FinishReason.STOP,
                        types.FinishReason.FINISH_REASON_UNSPECIFIED,
                        types.FinishReason.MAX_TOKENS,
                    ):
                        reason_name = types.FinishReason(candidate.finish_reason).name
                        print(
                            f"  Aviso: Candidato finalizado com razão: {reason_name}",
                            file=sys.stderr,
                        )
                        if (
                            hasattr(candidate, "finish_message")
                            and candidate.finish_message
                        ):
                            print(
                                f"  Mensagem de finalização: {candidate.finish_message}",
                                file=sys.stderr,
                            )

            try:
                return response.text
            except (ValueError, AttributeError) as e:
                print(
                    f"Aviso: Não foi possível extrair texto da resposta. Resposta: {response}. Erro: {e}",
                    file=sys.stderr,
                )
                return ""

        except concurrent.futures.TimeoutError:
            print(
                f"  Chamada API excedeu o tempo limite de {timeout_seconds}s. Erro para a tarefa atual.",
                file=sys.stderr,
            )
            raise TimeoutError
        except (
            google_api_core_exceptions.ResourceExhausted,
            google_genai_errors.ServerError,
            google_api_core_exceptions.DeadlineExceeded,
        ) as e:
            print(
                f"  Erro de API ({type(e).__name__}) com Key Index {current_api_key_index}. Aguardando {sleep_on_retry:.1f}s e rotacionando chave...",
                file=sys.stderr,
            )
            if verbose:
                print(f"    Detalhes do erro: {e}")

            for _ in tqdm(
                range(int(sleep_on_retry * 10)),
                desc="Aguardando para nova tentativa/rotação de cota",
                unit="ds",
                leave=False,
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}",
            ):
                time.sleep(0.1)

            if not rotate_api_key_and_reinitialize(verbose):
                print(
                    "Erro: Não foi possível rotacionar a chave de API. Relançando erro original.",
                    file=sys.stderr,
                )
                raise e

            if current_api_key_index in keys_tried_in_this_call:
                print(
                    f"Erro: Ciclo completo de chaves API. Limite/Erro persistente. Relançando erro original.",
                    file=sys.stderr,
                )
                raise e

            keys_tried_in_this_call.add(current_api_key_index)
            if verbose:
                print(
                    f"        -> Tentando novamente chamada API com nova Key Index {current_api_key_index}"
                )
            continue

        except google_genai_errors.APIError as e:
            print(
                f"  Erro de API GenAI ({type(e).__name__}) com Key Index {current_api_key_index}: {e}",
                file=sys.stderr,
            )

            is_rate_limit_error = False
            # A verificação de e.response.status_code pode não ser aplicável a todas as APIError
            # Por isso, usamos hasattr para checagem segura.
            if hasattr(e, "response") and e.response and hasattr(e.response, "status_code") and e.response.status_code == 429:  # type: ignore
                is_rate_limit_error = True
            elif (
                hasattr(e, "message")
                and isinstance(e.message, str)
                and (
                    "429" in e.message
                    or "resource has been exhausted" in e.message.lower()
                    or "quota" in e.message.lower()
                )
            ):
                is_rate_limit_error = True

            if is_rate_limit_error:
                print(
                    f"  Erro 429 (Rate Limit) detectado. Aguardando {sleep_on_retry:.1f}s e rotacionando chave...",
                    file=sys.stderr,
                )
                if not rotate_api_key_and_reinitialize(verbose):
                    raise e
                if current_api_key_index in keys_tried_in_this_call:
                    raise e
                keys_tried_in_this_call.add(current_api_key_index)
                continue
            raise e

        except Exception as e:
            print(f"Erro inesperado durante a chamada API: {e}", file=sys.stderr)
            traceback.print_exc()
            raise