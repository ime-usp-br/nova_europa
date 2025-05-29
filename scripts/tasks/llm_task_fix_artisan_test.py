# -*- coding: utf-8 -*-
"""
Script para a tarefa 'fix-artisan-test' de interação com LLM.
Analisa falhas de testes PHPUnit (Artisan Test) e tenta gerar correções.
"""

import sys
import os
import argparse
import traceback
import json
from pathlib import Path
from typing import List, Dict, Optional

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
from scripts.llm_core.exceptions import MissingEssentialFileAbort


from google.genai import types

TASK_NAME = "fix-artisan-test"
PROMPT_TEMPLATE_NAME = "prompt-fix-artisan-test.txt"
META_PROMPT_TEMPLATE_NAME = "meta-prompt-fix-artisan-test.txt"


def add_task_specific_args(parser: argparse.ArgumentParser):
    """Adiciona argumentos específicos da tarefa 'fix-artisan-test' ao parser."""
    # Esta tarefa, similar à fix-artisan-dusk, geralmente não precisa de argumentos
    # específicos além dos comuns, pois o contexto (phpunit_test_results.txt)
    # já guia a ação.
    # Se fosse necessário, por exemplo, focar em um teste específico:
    # parser.add_argument("--test-method", help="Nome específico do método de teste PHPUnit a ser focado.")
    pass


def main_fix_artisan_test():
    """Função principal para a tarefa fix-artisan-test."""
    parser = core_args_module.get_common_arg_parser(
        description=f"Executa a tarefa '{TASK_NAME}' para corrigir falhas de testes PHPUnit (Artisan test)."
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
            "OBSERVACAO_ADICIONAL": args.observation,
        }

        if args.two_stage:
            template_path_to_load = (
                core_config.META_PROMPT_DIR / META_PROMPT_TEMPLATE_NAME
            )
            print(f"\nFluxo de Duas Etapas Selecionado")
            GEMINI_MODEL_STEP1 = core_config.GEMINI_MODEL_GENERAL_TASKS
        else:
            template_path_to_load = core_config.TEMPLATE_DIR / PROMPT_TEMPLATE_NAME
            print(f"\nFluxo Direto Selecionado")
            GEMINI_MODEL_STEP1 = core_config.GEMINI_MODEL_RESOLVE  # Não usado
        print(
            f"Usando Template: {template_path_to_load.relative_to(core_config.PROJECT_ROOT)}"
        )
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
        latest_dir_name_for_essentials = (
            latest_context_dir_path.name if latest_context_dir_path else None
        )

        max_tokens_for_main_call = api_client.calculate_max_input_tokens(
            GEMINI_MODEL_STEP2, verbose=verbose
        )  # AC5.2

        if args.select_context:
            print("\nSeleção de Contexto Preliminar Habilitada...")
            latest_manifest_path = core_context.find_latest_manifest_json(
                core_config.MANIFEST_DATA_DIR
            )
            if not latest_manifest_path:
                sys.exit(1)
            manifest_data_for_context_selection = core_context.load_manifest(
                latest_manifest_path
            )
            if (
                not manifest_data_for_context_selection
                or "files" not in manifest_data_for_context_selection
            ):
                sys.exit(1)
            if verbose:
                print(
                    f"  AC5.1: Manifesto carregado para seleção: {latest_manifest_path.relative_to(core_config.PROJECT_ROOT)}"
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
                sys.exit(1)
            if verbose:
                print(
                    f"  AC5.1: Usando Prompt Seletor: {context_selector_prompt_path.relative_to(core_config.PROJECT_ROOT)}"
                )

            preliminary_api_input_content = (
                core_context.prepare_payload_for_selector_llm(
                    TASK_NAME,
                    args,
                    latest_dir_name_for_essentials,
                    manifest_data_for_context_selection,
                    selector_prompt_content,
                    core_config.MAX_ESSENTIAL_TOKENS_FOR_SELECTOR_CALL,
                    verbose,
                )
            )

            suggested_files_from_api: List[str] = []
            try:
                if verbose:  # AC5.2
                    print(
                        f"  AC5.2: Chamando API Gemini. Modelo: {core_config.GEMINI_MODEL_FLASH}. MAX_INPUT_TOKENS_PER_CALL (para esta chamada seletora, não o principal): {core_config.SELECTOR_LLM_MAX_INPUT_TOKENS}"
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
                    max_input_tokens_for_this_call=core_config.SELECTOR_LLM_MAX_INPUT_TOKENS,
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
            except Exception as e:
                print(
                    f"\nErro fatal durante seleção de contexto preliminar: {type(e).__name__} - {e}",
                    file=sys.stderr,
                )
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
                        max_tokens_for_main_call,
                        verbose=verbose,
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
                max_input_tokens_for_call=max_tokens_for_main_call,
                task_name_for_essentials=TASK_NAME,
                cli_args_for_essentials=args,
                latest_dir_name_for_essentials=latest_dir_name_for_essentials,
                verbose=verbose,
            )
        else:
            if not latest_context_dir_path:
                print(
                    "Erro fatal: Nenhum diretório de contexto encontrado. Execute generate_context.py.",
                    file=sys.stderr,
                )
                sys.exit(1)
            context_parts = core_context.prepare_context_parts(
                primary_context_dir=latest_context_dir_path,
                common_context_dir=core_config.COMMON_CONTEXT_DIR,
                exclude_list=args.exclude_context,
                manifest_data=manifest_data_for_context_selection,
                max_input_tokens_for_call=max_tokens_for_main_call,
                task_name_for_essentials=TASK_NAME,
                cli_args_for_essentials=args,
                latest_dir_name_for_essentials=latest_dir_name_for_essentials,
                verbose=verbose,
            )
        if not context_parts and verbose:
            print("Aviso: Nenhuma parte de contexto carregada.", file=sys.stderr)

        final_prompt_to_send: Optional[str] = None
        if args.two_stage:
            # ... (lógica de duas etapas, igual a outras tasks) ...
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
                    if verbose:  # AC5.2
                        print(
                            f"  AC5.2: Chamando API Gemini. Modelo: {GEMINI_MODEL_STEP1}. MAX_INPUT_TOKENS_PER_CALL: {api_client.calculate_max_input_tokens(GEMINI_MODEL_STEP1, verbose=False)}"
                        )
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
                        max_input_tokens_for_this_call=api_client.calculate_max_input_tokens(
                            GEMINI_MODEL_STEP1, verbose=False
                        ),
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
            print(final_prompt_to_send.strip() if final_prompt_to_send else "")
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
                if verbose:  # AC5.2
                    print(
                        f"  AC5.2: Chamando API Gemini. Modelo: {GEMINI_MODEL_STEP2}. MAX_INPUT_TOKENS_PER_CALL: {max_tokens_for_main_call}"
                    )
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
                    max_input_tokens_for_this_call=max_tokens_for_main_call,
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
            print(
                "Erro: Nenhuma resposta final para correção dos testes PHPUnit obtida.",
                file=sys.stderr,
            )
            sys.exit(1)

        if final_response_content.strip():
            save_confirm_choice, _ = io_utils.confirm_step(
                "Confirmar salvamento desta resposta (código corrigido)?"
            )
            if save_confirm_choice == "y":
                print("\nSalvando Resposta Final...")
                io_utils.save_llm_response(TASK_NAME, final_response_content.strip())
            else:
                print("Salvamento cancelado.")
                sys.exit(0)
        else:
            print(
                "\nResposta final da LLM está vazia. Isso pode indicar que nenhuma correção foi sugerida ou que os erros não puderam ser resolvidos."
            )
            print("Nenhum arquivo será salvo.")
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
    main_fix_artisan_test()
