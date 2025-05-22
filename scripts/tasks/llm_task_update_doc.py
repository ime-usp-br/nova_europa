# -*- coding: utf-8 -*-
"""
Script para a tarefa 'update-doc' de interação com LLM.
Atualiza arquivos de documentação com base nas mudanças de uma Issue.
"""

import sys
import os
import argparse
import traceback
import json # Não usado diretamente aqui, mas pode ser no futuro para contexto
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
from scripts.llm_core import io_utils # Usaremos para find_documentation_files e prompt_user_to_select_doc
from scripts.llm_core import utils as core_utils

from google.genai import types

TASK_NAME = "update-doc"
PROMPT_TEMPLATE_NAME = "prompt-update-doc.txt"
META_PROMPT_TEMPLATE_NAME = "meta-prompt-update-doc.txt"


def add_task_specific_args(parser: argparse.ArgumentParser):
    """Adiciona argumentos específicos da tarefa 'update-doc' ao parser."""
    parser.add_argument(
        "-i", "--issue", required=True, help="Número da Issue GitHub (obrigatório)."
    )
    parser.add_argument(
        "-d",
        "--doc-file",
        help="Caminho do arquivo de documentação alvo (relativo à raiz do projeto). Se omitido, será solicitado.",
        default=None, # Opcional no parser, lógica da task trata
    )
    # O argumento -o/--observation já é adicionado pelo get_common_arg_parser


def main_update_doc():
    """Função principal para a tarefa update-doc."""
    parser = core_args_module.get_common_arg_parser(
        description=f"Executa a tarefa '{TASK_NAME}' para atualizar documentação."
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
        print("Erro fatal: Falha ao inicializar recursos da API. Saindo.", file=sys.stderr)
        sys.exit(1)

    try:
        if args.generate_context:
            print(
                f"\nExecutando script de geração de contexto: {core_config.CONTEXT_GENERATION_SCRIPT.relative_to(core_config.PROJECT_ROOT)}..."
            )
            if not core_config.CONTEXT_GENERATION_SCRIPT.is_file() or not os.access(
                core_config.CONTEXT_GENERATION_SCRIPT, os.X_OK
            ):
                print(f"Erro: Script de contexto '{core_config.CONTEXT_GENERATION_SCRIPT.name}' não encontrado ou não executável.", file=sys.stderr)
                sys.exit(1)
            exit_code_ctx, _, stderr_ctx = core_utils.run_command(
                [sys.executable, str(core_config.CONTEXT_GENERATION_SCRIPT)],
                check=False,
                timeout=core_config.DEFAULT_CONTEXT_GENERATION_TIMEOUT,
            )
            if exit_code_ctx != 0:
                print(f"Erro: Geração de contexto falhou (código: {exit_code_ctx}). Stderr:\n{stderr_ctx}", file=sys.stderr)
                sys.exit(1)
            print("Script de geração de contexto concluído.")

        target_doc_file_str = args.doc_file
        if not target_doc_file_str:
            print("\nArgumento --doc-file não fornecido. Buscando arquivos de documentação...")
            found_docs = io_utils.find_documentation_files(core_config.PROJECT_ROOT)
            if not found_docs:
                print("Erro: Nenhum arquivo de documentação (.md na raiz ou em docs/) encontrado.", file=sys.stderr)
                sys.exit(1)
            
            selected_path_relative = io_utils.prompt_user_to_select_doc(found_docs)
            if not selected_path_relative:
                print("Seleção de arquivo de documentação cancelada pelo usuário. Saindo.")
                sys.exit(0)
            target_doc_file_str = str(selected_path_relative) # Convertendo Path para str
        
        if not target_doc_file_str: # Double check after potential prompt
            print("Erro: Arquivo de documentação alvo não foi especificado ou selecionado.", file=sys.stderr)
            sys.exit(1)

        # Validar se o arquivo alvo existe
        target_doc_file_path_abs = (core_config.PROJECT_ROOT / target_doc_file_str).resolve(strict=False)
        if not target_doc_file_path_abs.is_file():
            print(f"Erro: Arquivo de documentação alvo '{target_doc_file_str}' não encontrado em '{target_doc_file_path_abs}'.", file=sys.stderr)
            sys.exit(1)
        
        # Garantir que o target_doc_file_str seja relativo à raiz para o template
        target_doc_file_rel_str = str(target_doc_file_path_abs.relative_to(core_config.PROJECT_ROOT))


        task_variables: Dict[str, str] = {
            "NUMERO_DA_ISSUE": args.issue,
            "OBSERVACAO_ADICIONAL": args.observation,
            "ARQUIVO_DOC_ALVO": target_doc_file_rel_str,
        }

        if args.two_stage:
            template_path_to_load = core_config.META_PROMPT_DIR / META_PROMPT_TEMPLATE_NAME
            print(f"\nFluxo de Duas Etapas Selecionado")
        else:
            template_path_to_load = core_config.TEMPLATE_DIR / PROMPT_TEMPLATE_NAME
            print(f"\nFluxo Direto Selecionado")
        
        print(f"Usando Template: {template_path_to_load.relative_to(core_config.PROJECT_ROOT)}")
        GEMINI_MODEL_TO_USE = core_config.GEMINI_MODEL_GENERAL_TASKS # update-doc usa modelo geral

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
            print("Aviso: --only-meta é aplicável apenas com --two-stage.", file=sys.stderr)

        if args.only_prompt and not args.two_stage:
            print(f"\n--- Prompt Final (--only-prompt) ---")
            print(initial_prompt_content_current.strip())
            print("--- Fim ---")
            sys.exit(0)

        context_parts: List[types.Part] = []
        final_selected_files_for_context: Optional[List[str]] = None
        manifest_data_for_context_selection: Optional[Dict[str, Any]] = None
        load_default_context_after_selection_failure = False
        latest_context_dir_path = core_context.find_latest_context_dir(core_config.CONTEXT_DIR_BASE)

        if args.select_context:
            print("\nSeleção de Contexto Preliminar Habilitada...")
            latest_manifest_path = core_context.find_latest_manifest_json(core_config.MANIFEST_DATA_DIR)
            if not latest_manifest_path: sys.exit(1)
            manifest_data_for_context_selection = core_context.load_manifest(latest_manifest_path)
            if not manifest_data_for_context_selection or "files" not in manifest_data_for_context_selection: sys.exit(1)

            context_selector_prompt_path = core_prompts_module.find_context_selector_prompt(TASK_NAME, args.two_stage)
            if not context_selector_prompt_path: sys.exit(1)
            selector_prompt_content = core_prompts_module.load_and_fill_template(context_selector_prompt_path, task_variables)
            if not selector_prompt_content: sys.exit(1)

            all_manifest_files = manifest_data_for_context_selection.get("files", {})
            filtered_manifest_files_for_selection: Dict[str, Any] = {
                p: m for p, m in all_manifest_files.items()
                if isinstance(m, dict) and (m.get("token_count") is None or m.get("token_count", float('inf')) <= core_config.MANIFEST_MAX_TOKEN_FILTER)
            }
            if verbose: print(f"    Excluídos {len(all_manifest_files) - len(filtered_manifest_files_for_selection)} arquivos do manifesto para API seletora.")
            try:
                filtered_manifest_json = json.dumps({"files": filtered_manifest_files_for_selection}, indent=2, ensure_ascii=False)
                preliminary_api_input_content = f"{selector_prompt_content}\n\n```json\n{filtered_manifest_json}\n```"
            except Exception as e:
                print(f"Erro ao serializar manifesto filtrado: {e}", file=sys.stderr); sys.exit(1)
            
            suggested_files_from_api: List[str] = []
            try:
                response_prelim_str = api_client.execute_gemini_call(
                    core_config.GEMINI_MODEL_FLASH,
                    [types.Part.from_text(text=preliminary_api_input_content)],
                    config=types.GenerateContentConfig(tools=([types.Tool(google_search_retrieval=types.GoogleSearchRetrieval())] if args.web_search else [])),
                    verbose=verbose
                )
                cleaned_response_str = response_prelim_str.strip()
                if cleaned_response_str.startswith("```json"): cleaned_response_str = cleaned_response_str[7:].strip()
                if cleaned_response_str.endswith("```"): cleaned_response_str = cleaned_response_str[:-3].strip()
                parsed_response = json.loads(cleaned_response_str)
                if isinstance(parsed_response, dict) and "relevant_files" in parsed_response and isinstance(parsed_response["relevant_files"], list):
                    suggested_files_from_api = [str(item) for item in parsed_response["relevant_files"] if isinstance(item, str)]
                else: raise ValueError("Formato de 'relevant_files' inválido.")
            except Exception as e:
                print(f"\nErro fatal durante seleção de contexto preliminar: {type(e).__name__} - {e}", file=sys.stderr); sys.exit(1)

            if not suggested_files_from_api:
                if not core_context.prompt_user_on_empty_selection(): sys.exit(1)
                load_default_context_after_selection_failure = True
            else:
                final_selected_files_for_context = core_context.confirm_and_modify_selection(
                    suggested_files_from_api, manifest_data_for_context_selection, core_config.SUMMARY_TOKEN_LIMIT_PER_CALL
                )
                if final_selected_files_for_context is None:
                    load_default_context_after_selection_failure = True
        
        if final_selected_files_for_context is not None and not load_default_context_after_selection_failure:
            context_parts = core_context.prepare_context_parts(
                primary_context_dir=None, common_context_dir=None,
                exclude_list=args.exclude_context, manifest_data=manifest_data_for_context_selection,
                include_list=final_selected_files_for_context
            )
        else:
            if not latest_context_dir_path:
                print("Erro fatal: Nenhum diretório de contexto encontrado. Execute generate_context.py.", file=sys.stderr)
                sys.exit(1)
            context_parts = core_context.prepare_context_parts(
                primary_context_dir=latest_context_dir_path, common_context_dir=core_config.COMMON_CONTEXT_DIR,
                exclude_list=args.exclude_context, manifest_data=manifest_data_for_context_selection
            )
        if not context_parts and verbose:
            print("Aviso: Nenhuma parte de contexto carregada.", file=sys.stderr)

        final_prompt_to_send: Optional[str] = None
        if args.two_stage:
            print("\nExecutando Fluxo de Duas Etapas (Etapa 1: Meta -> Prompt Final)...")
            prompt_final_content: Optional[str] = None
            meta_prompt_current = initial_prompt_content_current
            while True:
                contents_step1 = [types.Part.from_text(text=meta_prompt_current)] + context_parts
                try:
                    prompt_final_content = api_client.execute_gemini_call(
                        GEMINI_MODEL_TO_USE, contents_step1,
                        config=types.GenerateContentConfig(tools=([types.Tool(google_search_retrieval=types.GoogleSearchRetrieval())] if args.web_search else [])),
                        verbose=verbose
                    )
                    print("\n--- Prompt Final Gerado (Etapa 1) ---")
                    print(prompt_final_content.strip())
                    print("---")
                    if args.yes: user_choice_step1, observation_step1 = "y", None
                    else: user_choice_step1, observation_step1 = io_utils.confirm_step("Usar este prompt gerado para a Etapa 2?")
                    if user_choice_step1 == "y": final_prompt_to_send = prompt_final_content; break
                    elif user_choice_step1 == "q": sys.exit(0)
                    elif user_choice_step1 == "n" and observation_step1:
                        meta_prompt_current = core_prompts_module.modify_prompt_with_observation(meta_prompt_current, observation_step1)
                    else: sys.exit(1)
                except Exception as e:
                    print(f"  Erro durante chamada API Etapa 1: {e}", file=sys.stderr)
                    if "Prompt bloqueado" in str(e): sys.exit(1)
                    retry_choice, _ = io_utils.confirm_step("Chamada API Etapa 1 falhou. Tentar novamente?")
                    if retry_choice != "y": sys.exit(1)
            if not final_prompt_to_send: sys.exit(1)
            if args.web_search and core_config.WEB_SEARCH_ENCOURAGEMENT_PT not in final_prompt_to_send:
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
            print(f"\n{step_name} Prompt Final + Contexto ({len(context_parts)} partes) para gerar conteúdo da documentação...")
            contents_final = [types.Part.from_text(text=final_prompt_current)] + context_parts
            try:
                final_response_content = api_client.execute_gemini_call(
                    GEMINI_MODEL_TO_USE, contents_final,
                    config=types.GenerateContentConfig(tools=([types.Tool(google_search_retrieval=types.GoogleSearchRetrieval())] if args.web_search else [])),
                    verbose=verbose
                )
                print("\n--- Resposta Final (Conteúdo da Documentação) ---")
                print(final_response_content.strip())
                print("---")
                if args.yes: user_choice_final, observation_final = "y", None
                else: user_choice_final, observation_final = io_utils.confirm_step("Prosseguir com esta resposta final?")
                if user_choice_final == "y": break
                elif user_choice_final == "q": sys.exit(0)
                elif user_choice_final == "n" and observation_final:
                    final_prompt_current = core_prompts_module.modify_prompt_with_observation(final_prompt_current, observation_final)
                else: sys.exit(1)
            except Exception as e:
                print(f"  Erro durante chamada API final: {e}", file=sys.stderr)
                if "Prompt bloqueado" in str(e): sys.exit(1)
                retry_choice_final, _ = io_utils.confirm_step("Chamada API final falhou. Tentar novamente?")
                if retry_choice_final != "y": sys.exit(1)

        if final_response_content is None:
            print("Erro: Nenhuma resposta final para a documentação obtida.", file=sys.stderr)
            sys.exit(1)

        if final_response_content.strip():
            save_confirm_choice, _ = io_utils.confirm_step("Confirmar salvamento desta resposta (documentação atualizada)?")
            if save_confirm_choice == "y":
                print("\nSalvando Resposta Final...")
                io_utils.save_llm_response(TASK_NAME, final_response_content.strip())
            else:
                print("Salvamento cancelado.")
                sys.exit(0)
        else:
            print("\nResposta final da LLM está vazia. Isso pode ser esperado se nenhuma atualização de documentação foi necessária.")
            print("Nenhum arquivo será salvo.")

    except Exception as e:
        print(f"Erro inesperado na tarefa '{TASK_NAME}': {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
    finally:
        api_client.shutdown_api_resources(verbose)

if __name__ == "__main__":
    main_update_doc()