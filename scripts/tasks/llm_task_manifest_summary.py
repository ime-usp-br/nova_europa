# -*- coding: utf-8 -*-
"""
Script para a tarefa 'manifest-summary' de interação com LLM.
Gera resumos para arquivos listados no manifesto JSON do projeto.
"""

import sys
import os
import argparse
import traceback
import json
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple, Any  # Adicionado Set e Tuple

# Adiciona o diretório raiz do projeto (PROJECT_ROOT) ao sys.path
_project_root_dir_for_task = Path(__file__).resolve().parent.parent.parent
if str(_project_root_dir_for_task) not in sys.path:
    sys.path.insert(0, str(_project_root_dir_for_task))

from scripts.llm_core import config as core_config
from scripts.llm_core import args as core_args_module
from scripts.llm_core import api_client
from scripts.llm_core import (
    context as core_context,
)  # Pode não ser usado diretamente pela task, mas importado por consistência
from scripts.llm_core import prompts as core_prompts_module
from scripts.llm_core import io_utils
from scripts.llm_core import utils as core_utils
from scripts.llm_core.exceptions import MissingEssentialFileAbort


from google.genai import types

TASK_NAME = "manifest-summary"
PROMPT_TEMPLATE_NAME = "prompt-manifest-summary.txt"
META_PROMPT_TEMPLATE_NAME = "meta-prompt-manifest-summary.txt"


def add_task_specific_args(parser: argparse.ArgumentParser):
    """Adiciona argumentos específicos da tarefa 'manifest-summary' ao parser."""
    parser.add_argument(
        "--manifest-path",
        type=str,
        help="Caminho para o arquivo de manifesto JSON a ser processado (opcional, padrão: o mais recente em scripts/data/).",
        default=None,
    )
    parser.add_argument(
        "--force-summary",
        action="append",
        help="Força a geração de resumo para arquivos específicos (caminho relativo), mesmo que já exista. Pode ser usado múltiplas vezes.",
        default=[],
    )
    parser.add_argument(
        "--max-files-per-call",
        type=int,
        default=core_config.DEFAULT_MAX_FILES_PER_SUMMARY_CALL,
        help=f"Número máximo de arquivos a serem incluídos em uma única chamada à API para sumarização (padrão: {core_config.DEFAULT_MAX_FILES_PER_SUMMARY_CALL}).",
    )


def select_files_for_summary_batch(
    manifest_data: Dict[str, Any],
    all_candidates: List[str],
    processed_files: Set[str],
    max_files_per_call: int,
    max_input_tokens: int,
    est_tokens_per_summary_output: int,  # Renomeado para clareza
    verbose: bool = False,
) -> Tuple[List[str], int, int]:
    """Seleciona um lote de arquivos para sumarização, respeitando os limites de token."""
    batch_files: List[str] = []
    current_input_tokens_for_batch = 0
    current_estimated_output_tokens_for_batch = 0
    files_metadata = manifest_data.get("files", {})

    for filepath_str in all_candidates:
        if filepath_str in processed_files:
            continue
        if len(batch_files) >= max_files_per_call:
            if verbose:
                print(
                    f"    Atingido o limite de {max_files_per_call} arquivos para este lote."
                )
            break

        metadata = files_metadata.get(filepath_str)
        if not isinstance(metadata, dict):
            if verbose:
                print(
                    f"    Metadados ausentes ou inválidos para '{filepath_str}', pulando."
                )
            processed_files.add(filepath_str)  # Evita tentar processar novamente
            continue

        file_content_token_count = metadata.get("token_count")
        if (
            file_content_token_count is None
            or not isinstance(file_content_token_count, int)
            or file_content_token_count <= 0
        ):
            if verbose:
                print(
                    f"    Token count ausente, inválido ou zero para '{filepath_str}', pulando."
                )
            processed_files.add(filepath_str)
            continue

        # Verifica se o próprio arquivo excede o limite total de entrada
        if file_content_token_count > max_input_tokens:
            if verbose:
                print(
                    f"    Arquivo '{filepath_str}' ({file_content_token_count} tokens) excede o limite de entrada ({max_input_tokens}), pulando."
                )
            processed_files.add(filepath_str)
            continue

        potential_total_input_tokens = (
            current_input_tokens_for_batch + file_content_token_count
        )
        potential_total_output_tokens = (
            current_estimated_output_tokens_for_batch + est_tokens_per_summary_output
        )

        if potential_total_input_tokens <= max_input_tokens:
            batch_files.append(filepath_str)
            current_input_tokens_for_batch = potential_total_input_tokens
            current_estimated_output_tokens_for_batch = potential_total_output_tokens
        else:
            if verbose:
                print(
                    f"    Arquivo '{filepath_str}' ({file_content_token_count} tokens) excederia o limite de entrada do lote. Não adicionando a este lote."
                )
            break

    return (
        batch_files,
        current_input_tokens_for_batch,
        current_estimated_output_tokens_for_batch,
    )


def prepare_api_content_for_summary(
    batch_files: List[str], base_summary_prompt: str, verbose: bool = False
) -> Tuple[List[types.Part], List[str]]:
    """Prepara a lista de conteúdos (prompt + arquivos) para a chamada API de sumarização."""
    contents_for_api: List[types.Part] = [
        types.Part.from_text(text=base_summary_prompt)
    ]
    successfully_read_paths: List[str] = []

    for filepath_str in batch_files:
        filepath_absolute = (core_config.PROJECT_ROOT / filepath_str).resolve(
            strict=False
        )
        try:
            content = filepath_absolute.read_text(encoding="utf-8", errors="ignore")
            part_text = f"{core_config.SUMMARY_CONTENT_DELIMITER_START}{filepath_str} ---\n{content}\n{core_config.SUMMARY_CONTENT_DELIMITER_END}{filepath_str} ---"
            contents_for_api.append(types.Part.from_text(text=part_text))
            successfully_read_paths.append(filepath_str)
            if verbose:
                print(
                    f"      Adicionado conteúdo de '{filepath_str}' para o lote da API."
                )
        except Exception as e:
            print(
                f"    Aviso: Não foi possível ler o arquivo '{filepath_str}' para o lote da API de sumarização: {e}",
                file=sys.stderr,
            )

    return contents_for_api, successfully_read_paths


def main_manifest_summary():
    """Função principal para a tarefa manifest-summary."""
    parser = core_args_module.get_common_arg_parser(
        description=f"Executa a tarefa '{TASK_NAME}' para gerar resumos de arquivos do manifesto."
    )
    add_task_specific_args(parser)

    try:
        args = parser.parse_args()
    except SystemExit as e:
        sys.exit(e.code)

    verbose = args.verbose
    if verbose:
        print("Modo verbose ativado.")

    if not api_client.startup_api_resources(verbose):
        print(
            "Erro fatal: Falha ao inicializar recursos da API. Saindo.", file=sys.stderr
        )
        sys.exit(1)

    try:
        if args.generate_context:
            pass

        manifest_to_process_path: Optional[Path] = None
        if args.manifest_path:
            manifest_to_process_path = Path(args.manifest_path).resolve(strict=False)
            if not manifest_to_process_path.is_file():
                print(
                    f"Erro: Arquivo de manifesto especificado não encontrado: {args.manifest_path}",
                    file=sys.stderr,
                )
                sys.exit(1)
        else:
            manifest_to_process_path = core_context.find_latest_manifest_json(
                core_config.MANIFEST_DATA_DIR
            )
            if not manifest_to_process_path:
                print(
                    f"Erro: Não foi possível encontrar o arquivo de manifesto mais recente em {core_config.MANIFEST_DATA_DIR}.",
                    file=sys.stderr,
                )
                sys.exit(1)

        print(
            f"\nProcessando manifesto: {manifest_to_process_path.relative_to(core_config.PROJECT_ROOT)}"
        )
        manifest_data = core_context.load_manifest(manifest_to_process_path)
        if not manifest_data or "files" not in manifest_data:
            print(
                f"Erro: Manifesto inválido ou vazio: {manifest_to_process_path.name}",
                file=sys.stderr,
            )
            sys.exit(1)

        files_metadata_dict = manifest_data.get("files", {})
        candidates_for_summary: List[str] = []
        forced_files_set = set(args.force_summary) if args.force_summary else set()

        print("  Identificando arquivos que precisam de resumo...")
        for filepath_str, metadata in files_metadata_dict.items():
            if not isinstance(metadata, dict):
                continue
            is_binary = metadata.get("type", "").startswith("binary_")
            if is_binary:
                continue

            needs_summary = False
            if filepath_str in forced_files_set:
                needs_summary = True
                if verbose:
                    print(f"    -> Sumário forçado para '{filepath_str}'.")
            elif metadata.get("summary") is None:
                needs_summary = True

            if needs_summary:
                if (
                    metadata.get("token_count") is not None
                    and isinstance(metadata.get("token_count"), int)
                    and metadata.get("token_count", 0) > 0
                ):
                    candidates_for_summary.append(filepath_str)
                elif verbose:
                    print(
                        f"    Pulando '{filepath_str}' para sumarização: token_count ausente, inválido ou zero."
                    )

        if not candidates_for_summary:
            print(
                "  Nenhum arquivo encontrado que necessite de resumo (ou forçado) no manifesto."
            )
            sys.exit(0)

        print(
            f"  Encontrados {len(candidates_for_summary)} arquivos candidatos para sumarização."
        )

        if args.two_stage:
            template_path_to_load = (
                core_config.META_PROMPT_DIR / META_PROMPT_TEMPLATE_NAME
            )
        else:
            template_path_to_load = core_config.TEMPLATE_DIR / PROMPT_TEMPLATE_NAME

        if not template_path_to_load.is_file():
            print(
                f"Erro: Template de prompt para sumarização não encontrado em {template_path_to_load}",
                file=sys.stderr,
            )
            sys.exit(1)

        GEMINI_MODEL_TO_USE = core_config.GEMINI_MODEL_SUMMARY

        base_summary_prompt_content = core_prompts_module.load_and_fill_template(
            template_path_to_load, {"OBSERVACAO_ADICIONAL": args.observation}
        )
        if not base_summary_prompt_content:
            print(
                f"Erro ao carregar o template de sumarização. Saindo.", file=sys.stderr
            )
            sys.exit(1)

        if args.web_search:
            base_summary_prompt_content += core_config.WEB_SEARCH_ENCOURAGEMENT_PT

        processed_files_in_run: Set[str] = set()
        manifest_was_modified = False

        max_tokens_for_api_call = api_client.calculate_max_input_tokens(
            GEMINI_MODEL_TO_USE, verbose=verbose
        )  # AC5.2

        while True:
            batch_files, batch_input_tokens, batch_output_estimate = (
                select_files_for_summary_batch(
                    manifest_data,
                    candidates_for_summary,
                    processed_files_in_run,
                    args.max_files_per_call,
                    max_tokens_for_api_call,  # AC5.2: usa o limite calculado
                    core_config.ESTIMATED_TOKENS_PER_SUMMARY
                    * len(processed_files_in_run)
                    + core_config.ESTIMATED_TOKENS_PER_SUMMARY
                    * args.max_files_per_call,
                    verbose,
                )
            )

            if not batch_files:
                if verbose:
                    print("  Nenhum arquivo restante para processar em lotes.")
                break

            print(
                f"\n  Processando lote de {len(batch_files)} arquivos (Tokens de Entrada Aprox.: {batch_input_tokens}, Tokens de Saída Estimados Aprox.: {batch_output_estimate})..."
            )

            contents_for_api, processed_paths_in_batch = (
                prepare_api_content_for_summary(
                    batch_files, base_summary_prompt_content, verbose
                )
            )

            if not processed_paths_in_batch:
                print(
                    "    Lote vazio após tentativa de leitura dos arquivos. Pulando este lote."
                )
                processed_files_in_run.update(batch_files)
                continue

            print(
                f"    Enviando {len(processed_paths_in_batch)} arquivos para a API para sumarização..."
            )

            current_llm_response = ""

            try:
                if args.two_stage:
                    print(
                        "    Executando Fluxo de Duas Etapas (Etapa 1: Meta -> Prompt Final de Sumarização)..."
                    )
                    # AC5.2: Logging para chamada de meta-prompt
                    max_tokens_meta = api_client.calculate_max_input_tokens(
                        GEMINI_MODEL_TO_USE, verbose=False
                    )
                    final_summary_prompt_from_meta = api_client.execute_gemini_call(
                        GEMINI_MODEL_TO_USE,
                        contents_for_api,
                        config=types.GenerateContentConfig(
                            tools=(
                                [
                                    types.Tool(
                                        google_search_retrieval=types.GoogleSearchRetrieval()
                                    )
                                ]
                                if args.web_search
                                else []
                            )
                        ),
                        verbose=verbose,
                        max_input_tokens_for_this_call=max_tokens_meta,
                    )
                    print("    Prompt Final de Sumarização Gerado (Etapa 1 concluída).")
                    contents_for_api_step2, _ = prepare_api_content_for_summary(
                        processed_paths_in_batch,
                        final_summary_prompt_from_meta,
                        verbose,
                    )
                    print(
                        "    Executando Fluxo de Duas Etapas (Etapa 2: Prompt Final -> Sumários)..."
                    )
                    # AC5.2: Logging para chamada principal
                    current_llm_response = api_client.execute_gemini_call(
                        GEMINI_MODEL_TO_USE,
                        contents_for_api_step2,
                        config=types.GenerateContentConfig(
                            tools=(
                                [
                                    types.Tool(
                                        google_search_retrieval=types.GoogleSearchRetrieval()
                                    )
                                ]
                                if args.web_search
                                else []
                            )
                        ),
                        verbose=verbose,
                        max_input_tokens_for_this_call=max_tokens_for_api_call,
                    )
                else:  # Fluxo Direto
                    # AC5.2: Logging para chamada principal
                    current_llm_response = api_client.execute_gemini_call(
                        GEMINI_MODEL_TO_USE,
                        contents_for_api,
                        config=types.GenerateContentConfig(
                            tools=(
                                [
                                    types.Tool(
                                        google_search_retrieval=types.GoogleSearchRetrieval()
                                    )
                                ]
                                if args.web_search
                                else []
                            )
                        ),
                        verbose=verbose,
                        max_input_tokens_for_this_call=max_tokens_for_api_call,
                    )

                print("    Chamada API bem-sucedida.")
                parsed_summaries = io_utils.parse_summaries_from_response(
                    current_llm_response
                )
                print(f"    Parseados {len(parsed_summaries)} sumários da resposta.")

                updated_count_in_batch = 0
                for (
                    filepath_str_from_response,
                    summary_text,
                ) in parsed_summaries.items():
                    if filepath_str_from_response in files_metadata_dict:
                        files_metadata_dict[filepath_str_from_response][
                            "summary"
                        ] = summary_text.strip()
                        manifest_was_modified = True
                        updated_count_in_batch += 1
                    elif verbose:
                        print(
                            f"    Aviso: Caminho de arquivo '{filepath_str_from_response}' retornado pela LLM não encontrado no manifesto original. Sumário ignorado."
                        )
                print(
                    f"    Aplicados {updated_count_in_batch} novos sumários aos metadados do manifesto para este lote."
                )
            except Exception as e:
                print(f"  ERRO: Falha ao processar o lote: {e}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                print("  Pulando este lote devido ao erro.")
            processed_files_in_run.update(batch_files)

        if manifest_was_modified:
            if "files" not in manifest_data:
                manifest_data["files"] = {}
            manifest_data["files"].update(files_metadata_dict)
            if io_utils.update_manifest_file(manifest_to_process_path, manifest_data):
                print(
                    f"\nArquivo de manifesto '{manifest_to_process_path.name}' atualizado com sucesso com os novos sumários."
                )
            else:
                print(
                    f"\nErro: Falha ao atualizar o arquivo de manifesto '{manifest_to_process_path.name}'.",
                    file=sys.stderr,
                )
                sys.exit(1)
        else:
            print("\nNenhum sumário foi gerado ou modificado no manifesto.")
    except MissingEssentialFileAbort as e:
        print(f"\nErro: {e}", file=sys.stderr)
        print("Fluxo de seleção de contexto interrompido.")
        sys.exit(1)
    except Exception as e:
        print(f"Erro inesperado na tarefa '{TASK_NAME}': {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
    finally:
        api_client.shutdown_api_resources(verbose)


if __name__ == "__main__":
    main_manifest_summary()
