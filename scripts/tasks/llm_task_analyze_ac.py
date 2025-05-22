# -*- coding: utf-8 -*-
"""
Script para a tarefa 'analyze-ac' de interação com LLM.
Analisa um Critério de Aceite (AC) específico de uma Issue GitHub e gera uma mensagem de conclusão.
"""

import sys
import os
import argparse
import traceback
import json
from pathlib import Path
from typing import List, Dict, Optional, Any

# Adiciona o diretório raiz do projeto (PROJECT_ROOT) ao sys.path
_project_root_dir_for_task = Path(__file__).resolve().parent.parent.parent
if str(_project_root_dir_for_task) not in sys.path:
    sys.path.insert(0, str(_project_root_dir_for_task))

from scripts.llm_core import config as core_config
from scripts.llm_core import args as core_args_module
from scripts.llm_core import api_client
from scripts.llm_core import context as core_context
from scripts.llm_core import prompts as core_prompts_module
from scripts.llm_core import io_utils
from scripts.llm_core import utils as core_utils

from google.genai import types

TASK_NAME = "analyze-ac"
PROMPT_TEMPLATE_NAME = "prompt-analyze-ac.txt"
META_PROMPT_TEMPLATE_NAME = "meta-prompt-analyze-ac.txt"


def add_task_specific_args(parser: argparse.ArgumentParser):
    """Adiciona argumentos específicos da tarefa 'analyze-ac' ao parser."""
    parser.add_argument(
        "-i", "--issue", required=True, help="Número da Issue GitHub (obrigatório)."
    )
    parser.add_argument(
        "-a",
        "--ac",
        required=True,
        help="Número do Critério de Aceite (AC) a ser analisado (obrigatório).",
    )


def main_analyze_ac():
    """Função principal para a tarefa analyze-ac."""
    parser = core_args_module.get_common_arg_parser(
        description=f"Executa a tarefa '{TASK_NAME}' para analisar um AC."
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
            print(
                f"\nExecutando script de geração de contexto: {core_config.CONTEXT_GENERATION_SCRIPT.relative_to(core_config.PROJECT_ROOT)}..."
            )
            if not core_config.CONTEXT_GENERATION_SCRIPT.is_file() or not os.access(
                core_config.CONTEXT_GENERATION_SCRIPT, os.X_OK
            ):
                print(
                    f"Erro: Script de contexto '{core_config.CONTEXT_GENERATION_SCRIPT.name}' não encontrado ou não executável.",
                    file=sys.stderr,
                )
                sys.exit(1)
            exit_code_ctx, _, stderr_ctx = core_utils.run_command(
                [sys.executable, str(core_config.CONTEXT_GENERATION_SCRIPT)],
                check=False,
                timeout=core_config.DEFAULT_CONTEXT_GENERATION_TIMEOUT,
            )
            if exit_code_ctx != 0:
                print(
                    f"Erro: Geração de contexto falhou (código: {exit_code_ctx}). Stderr:\n{stderr_ctx}",
                    file=sys.stderr,
                )
                sys.exit(1)
            print("Script de geração de contexto concluído.")

        task_variables: Dict[str, str] = {
            "NUMERO_DA_ISSUE": args.issue,
            "NUMERO_DO_AC": args.ac,
            "OBSERVACAO_ADICIONAL": args.observation,
        }

        if args.two_stage:
            template_path_to_load = (
                core_config.META_PROMPT_DIR / META_PROMPT_TEMPLATE_NAME
            )
            print(f"\nFluxo de Duas Etapas Selecionado")
            print(
                f"Usando Meta-Prompt: {template_path_to_load.relative_to(core_config.PROJECT_ROOT)}"
            )
            GEMINI_MODEL_STEP1 = core_config.GEMINI_MODEL_GENERAL_TASKS
            GEMINI_MODEL_STEP2 = core_config.GEMINI_MODEL_RESOLVE
        else:
            template_path_to_load = core_config.TEMPLATE_DIR / PROMPT_TEMPLATE_NAME
            print(f"\nFluxo Direto Selecionado")
            print(
                f"Usando Prompt: {template_path_to_load.relative_to(core_config.PROJECT_ROOT)}"
            )
            GEMINI_MODEL_STEP1 = core_config.GEMINI_MODEL_RESOLVE
            GEMINI_MODEL_STEP2 = core_config.GEMINI_MODEL_RESOLVE

        initial_prompt_content_original = core_prompts_module.load_and_fill_template(
            template_path_to_load, task_variables
        )
        if not initial_prompt_content_original:
            print(f"Erro ao carregar o prompt inicial. Saindo.", file=sys.stderr)
            sys.exit(1)

        initial_prompt_content_current = initial_prompt_content_original
        if args.web_search:
            initial_prompt_content_current += core_config.WEB_SEARCH_ENCOURAGEMENT_PT

        if args.only_meta and args.two_stage:
            print("\n--- Meta-Prompt Preenchido (--only-meta) ---")
            print(initial_prompt_content_current.strip())
            print("--- Fim ---")
            sys.exit(0)
        elif args.only_meta:
            print(
                "Aviso: --only-meta é aplicável apenas com --two-stage.",
                file=sys.stderr,
            )

        if args.only_prompt and not args.two_stage:
            print(f"\n--- Prompt Final (--only-prompt) ---")
            print(initial_prompt_content_current.strip())
            print("--- Fim ---")
            sys.exit(0)

        context_parts: List[types.Part] = []
        final_selected_files_for_context: Optional[List[str]] = None
        manifest_data_for_context_selection: Optional[Dict[str, Any]] = None
        load_default_context_after_selection_failure = False
        latest_context_dir_path = core_context.find_latest_context_dir(
            core_config.CONTEXT_DIR_BASE
        )

        if args.select_context:
            print("\nSeleção de Contexto Preliminar Habilitada...")
            latest_manifest_path = core_context.find_latest_manifest_json(
                core_config.MANIFEST_DATA_DIR
            )
            if not latest_manifest_path:
                print(
                    "Erro: Não foi possível encontrar o manifesto para seleção de contexto. Tente gerar o manifesto primeiro.",
                    file=sys.stderr,
                )
                sys.exit(1)
            manifest_data_for_context_selection = core_context.load_manifest(
                latest_manifest_path
            )
            if (
                not manifest_data_for_context_selection
                or "files" not in manifest_data_for_context_selection
            ):
                print(
                    "Erro: Manifesto inválido ou vazio para seleção de contexto.",
                    file=sys.stderr,
                )
                sys.exit(1)
            print(
                f"  Manifesto carregado: {latest_manifest_path.relative_to(core_config.PROJECT_ROOT)}"
            )

            context_selector_prompt_path = (
                core_prompts_module.find_context_selector_prompt(
                    TASK_NAME, args.two_stage
                )
            )
            if not context_selector_prompt_path:
                sys.exit(1)
            selector_prompt_content = core_prompts_module.load_and_fill_template(
                context_selector_prompt_path, task_variables
            )
            if not selector_prompt_content:
                print("Erro ao carregar prompt seletor de contexto.", file=sys.stderr)
                sys.exit(1)
            print(
                f"  Usando Prompt Seletor: {context_selector_prompt_path.relative_to(core_config.PROJECT_ROOT)}"
            )

            all_manifest_files = manifest_data_for_context_selection.get("files", {})
            # Correção da dict comprehension
            filtered_manifest_files_for_selection: Dict[str, Any] = {}
            excluded_count_filter = 0
            for path, metadata in all_manifest_files.items():
                if not isinstance(metadata, dict):
                    excluded_count_filter +=1 # Conta como excluído se não for dict
                    continue
                token_c = metadata.get("token_count")
                if isinstance(token_c, int) and token_c <= core_config.MANIFEST_MAX_TOKEN_FILTER:
                    filtered_manifest_files_for_selection[path] = metadata
                else:
                    excluded_count_filter += 1
            if verbose:
                print(
                    f"    Excluídos {excluded_count_filter} arquivos do manifesto para API seletora (limite de token ou token_count ausente/inválido)."
                )

            try:
                filtered_manifest_json = json.dumps(
                    {"files": filtered_manifest_files_for_selection},
                    indent=2,
                    ensure_ascii=False,
                )
                preliminary_api_input_content = f"{selector_prompt_content}\n\n```json\n{filtered_manifest_json}\n```"
                if verbose:
                    print(
                        f"    Payload para API seletora (início): {preliminary_api_input_content[:200]}..."
                    )
            except Exception as e:
                print(f"Erro ao serializar manifesto filtrado: {e}", file=sys.stderr)
                sys.exit(1)

            response_prelim_str: Optional[str] = None
            suggested_files_from_api: List[str] = []
            try:
                print(
                    f"  Chamando API preliminar ({core_config.GEMINI_MODEL_FLASH}) para seleção de contexto..."
                )
                response_prelim_str = api_client.execute_gemini_call(
                    core_config.GEMINI_MODEL_FLASH,
                    [types.Part.from_text(text=preliminary_api_input_content)],
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
                )
                cleaned_response_str = response_prelim_str.strip()
                if cleaned_response_str.startswith("```json"):
                    cleaned_response_str = cleaned_response_str[7:].strip()
                if cleaned_response_str.endswith("```"):
                    cleaned_response_str = cleaned_response_str[:-3].strip()
                parsed_response = json.loads(cleaned_response_str)
                if (
                    isinstance(parsed_response, dict)
                    and "relevant_files" in parsed_response
                    and isinstance(parsed_response["relevant_files"], list)
                ):
                    suggested_files_from_api = [
                        str(item)
                        for item in parsed_response["relevant_files"]
                        if isinstance(item, str)
                    ]
                else:
                    raise ValueError("Formato de 'relevant_files' inválido.")
                print(
                    f"    API preliminar retornou {len(suggested_files_from_api)} arquivos sugeridos."
                )

            except Exception as e:
                print(
                    f"\nErro fatal durante seleção de contexto preliminar: {type(e).__name__} - {e}",
                    file=sys.stderr,
                )
                if verbose:
                    traceback.print_exc()
                sys.exit(1)

            if not suggested_files_from_api:
                if not core_context.prompt_user_on_empty_selection():
                    sys.exit(1)
                load_default_context_after_selection_failure = True
            else:
                final_selected_files_for_context = (
                    core_context.confirm_and_modify_selection(
                        suggested_files_from_api,
                        manifest_data_for_context_selection,
                        core_config.SUMMARY_TOKEN_LIMIT_PER_CALL,
                    )
                )
                if final_selected_files_for_context is None:
                    load_default_context_after_selection_failure = True

        if (
            final_selected_files_for_context is not None
            and not load_default_context_after_selection_failure
        ):
            context_parts = core_context.prepare_context_parts(
                primary_context_dir=None,
                common_context_dir=None,
                exclude_list=args.exclude_context,
                manifest_data=manifest_data_for_context_selection,
                include_list=final_selected_files_for_context,
            )
        else:
            if not latest_context_dir_path:
                print(
                    "Erro fatal: Nenhum diretório de contexto encontrado para carregamento padrão. Execute generate_context.py.",
                    file=sys.stderr,
                )
                sys.exit(1)
            context_parts = core_context.prepare_context_parts(
                primary_context_dir=latest_context_dir_path,
                common_context_dir=core_config.COMMON_CONTEXT_DIR,
                exclude_list=args.exclude_context,
                manifest_data=manifest_data_for_context_selection,
            )
        if not context_parts and verbose:
            print(
                "Aviso: Nenhuma parte de contexto carregada. A LLM pode não ter informações suficientes.",
                file=sys.stderr,
            )

        final_prompt_to_send: Optional[str] = None
        if args.two_stage:
            print(
                "\nExecutando Fluxo de Duas Etapas (Etapa 1: Meta -> Prompt Final)..."
            )
            prompt_final_content: Optional[str] = None
            meta_prompt_current = initial_prompt_content_current
            while True:
                contents_step1 = [
                    types.Part.from_text(text=meta_prompt_current)
                ] + context_parts
                try:
                    prompt_final_content = api_client.execute_gemini_call(
                        GEMINI_MODEL_STEP1,
                        contents_step1,
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
                    )
                    print("\n--- Prompt Final Gerado (Etapa 1) ---")
                    print(prompt_final_content.strip())
                    print("---")
                    if args.yes:
                        user_choice_step1, observation_step1 = "y", None
                    else:
                        user_choice_step1, observation_step1 = io_utils.confirm_step(
                            "Usar este prompt gerado para a Etapa 2?"
                        )
                    if user_choice_step1 == "y":
                        final_prompt_to_send = prompt_final_content
                        break
                    elif user_choice_step1 == "q":
                        sys.exit(0)
                    elif user_choice_step1 == "n" and observation_step1:
                        meta_prompt_current = (
                            core_prompts_module.modify_prompt_with_observation(
                                meta_prompt_current, observation_step1
                            )
                        )
                    else:
                        sys.exit(1)
                except Exception as e:
                    print(f"  Erro durante chamada API Etapa 1: {e}", file=sys.stderr)
                    if "Prompt bloqueado" in str(e):
                        sys.exit(1)
                    retry_choice, _ = io_utils.confirm_step(
                        "Chamada API Etapa 1 falhou. Tentar novamente?"
                    )
                    if retry_choice != "y":
                        sys.exit(1)
            if not final_prompt_to_send:
                sys.exit(1)
            if (
                args.web_search
                and core_config.WEB_SEARCH_ENCOURAGEMENT_PT not in final_prompt_to_send
            ):
                final_prompt_to_send += core_config.WEB_SEARCH_ENCOURAGEMENT_PT
        else:
            final_prompt_to_send = initial_prompt_content_current

        if args.only_prompt:
            print(f"\n--- Prompt Final Para Envio (--only-prompt) ---")
            print(final_prompt_to_send.strip())
            print("--- Fim ---")
            sys.exit(0)

        final_response_content: Optional[str] = None
        final_prompt_current = final_prompt_to_send
        while True:
            step_name = "Etapa 2: Enviando" if args.two_stage else "Enviando"
            print(
                f"\n{step_name} Prompt Final + Contexto ({len(context_parts)} partes)..."
            )
            contents_final = [
                types.Part.from_text(text=final_prompt_current)
            ] + context_parts
            try:
                final_response_content = api_client.execute_gemini_call(
                    GEMINI_MODEL_STEP2,
                    contents_final,
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
                )
                print("\n--- Resposta Final ---")
                print(final_response_content.strip() if final_response_content else "")
                print("---")
                if args.yes:
                    user_choice_final, observation_final = "y", None
                else:
                    user_choice_final, observation_final = io_utils.confirm_step(
                        "Prosseguir com esta resposta final?"
                    )
                if user_choice_final == "y":
                    break
                elif user_choice_final == "q":
                    sys.exit(0)
                elif user_choice_final == "n" and observation_final:
                    final_prompt_current = (
                        core_prompts_module.modify_prompt_with_observation(
                            final_prompt_current, observation_final
                        )
                    )
                else:
                    sys.exit(1)
            except Exception as e:
                print(f"  Erro durante chamada API final: {e}", file=sys.stderr)
                if "Prompt bloqueado" in str(e):
                    sys.exit(1)
                retry_choice_final, _ = io_utils.confirm_step(
                    "Chamada API final falhou. Tentar novamente?"
                )
                if retry_choice_final != "y":
                    sys.exit(1)

        if final_response_content is None:
            print("Erro: Nenhuma resposta final obtida.", file=sys.stderr)
            sys.exit(1)

        if final_response_content.strip():
            save_confirm_choice, _ = io_utils.confirm_step(
                "Confirmar salvamento desta resposta?"
            )
            if save_confirm_choice == "y":
                print("\nSalvando Resposta Final...")
                io_utils.save_llm_response(TASK_NAME, final_response_content.strip())
            else:
                print("Salvamento cancelado.")
                sys.exit(0)
        else:
            print(
                "\nResposta final da LLM está vazia. Nenhum arquivo será salvo."
            ) # AC9 #57
            # Se a resposta é vazia, pode ser intencional pela IA, não salvamos.

    except Exception as e:
        print(f"Erro inesperado na tarefa '{TASK_NAME}': {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
    finally:
        api_client.shutdown_api_resources(verbose)


if __name__ == "__main__":
    main_analyze_ac()