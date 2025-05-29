# -*- coding: utf-8 -*-
"""
Script para a tarefa 'create-pr' de interação com LLM.
Gera título e corpo para um Pull Request no GitHub.
"""

import sys
import os
import argparse
import traceback
import json
import shlex
from pathlib import Path
from typing import List, Dict, Optional, Tuple

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

TASK_NAME = "create-pr"
PROMPT_TEMPLATE_NAME = "prompt-create-pr.txt"
META_PROMPT_TEMPLATE_NAME = "meta-prompt-create-pr.txt"


def add_task_specific_args(parser: argparse.ArgumentParser):
    """Adiciona argumentos específicos da tarefa 'create-pr' ao parser."""
    parser.add_argument(
        "-i", "--issue", required=True, help="Número da Issue GitHub base para o PR."
    )
    parser.add_argument(
        "-b",
        "--target-branch",
        help=f"Branch alvo para o PR (padrão: {core_config.DEFAULT_TARGET_BRANCH}).",
        default=core_config.DEFAULT_TARGET_BRANCH,
    )
    parser.add_argument(
        "--draft", action="store_true", help="Criar o PR como rascunho."
    )


def get_current_branch(verbose: bool = False) -> Optional[str]:
    """Obtém o nome do branch Git atual."""
    if verbose:
        print("  Obtendo branch Git atual...")
    exit_code, stdout, stderr = core_utils.run_command(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], check=False
    )
    if exit_code == 0 and stdout:
        branch_name = stdout.strip()
        if verbose:
            print(f"    Branch atual: {branch_name}")
        return branch_name
    else:
        print(
            f"  Erro ao obter o branch Git atual. Stderr: {stderr.strip()}",
            file=sys.stderr,
        )
        return None


def check_new_commits(
    base_branch: str, head_branch: str, verbose: bool = False
) -> bool:
    """Verifica se existem commits novos no branch head em relação ao branch base."""
    if verbose:
        print(
            f"  Verificando novos commits em '{head_branch}' em relação a '{base_branch}'..."
        )
    core_utils.run_command(
        ["git", "fetch", "origin", head_branch, base_branch], check=False
    )

    base_ref_to_compare = base_branch
    exit_code_remote, _, _ = core_utils.run_command(
        ["git", "show-ref", "--verify", f"refs/remotes/origin/{base_branch}"],
        check=False,
    )
    if exit_code_remote == 0:
        base_ref_to_compare = f"origin/{base_branch}"
        if verbose:
            print(f"    Comparando com o branch remoto: {base_ref_to_compare}")
    else:
        if verbose:
            print(
                f"    Branch base remoto 'origin/{base_branch}' não encontrado. Comparando com branch local '{base_branch}'."
            )

    count_cmd = ["git", "rev-list", "--count", f"{base_ref_to_compare}..{head_branch}"]
    exit_code_count, stdout_count, stderr_count = core_utils.run_command(
        count_cmd, check=False
    )

    if exit_code_count == 0:
        try:
            commit_count = int(stdout_count.strip())
            if verbose:
                print(
                    f"    Encontrados {commit_count} novo(s) commit(s) em '{head_branch}' comparado a '{base_ref_to_compare}'."
                )
            return commit_count > 0
        except ValueError:
            print(
                f"  Erro ao parsear contagem de commits: '{stdout_count.strip()}'",
                file=sys.stderr,
            )
            return False
    else:
        print(
            f"  Erro ao verificar contagem de commits. Stderr: {stderr_count.strip()}",
            file=sys.stderr,
        )
        return False


def create_github_pr(
    title: str,
    body: str,
    head_branch: str,
    base_branch: str,
    is_draft: bool,
    verbose: bool = False,
) -> bool:
    """Cria um Pull Request no GitHub usando o gh CLI."""
    if not core_utils.command_exists("gh"):
        print(
            core_utils.suggest_install("gh", "github-cli"),
            file=sys.stderr,
        )
        print("Erro: gh CLI não encontrado. Não é possível criar PR.", file=sys.stderr)
        return False

    cmd = [
        "gh",
        "pr",
        "create",
        "--title",
        title,
        "--body",
        body,
        "--head",
        head_branch,
        "--base",
        base_branch,
    ]
    if is_draft:
        cmd.append("--draft")

    if verbose:
        print(f"\n  Tentando criar Pull Request com comando: {shlex.join(cmd)}")

    exit_code, stdout, stderr = core_utils.run_command(cmd, check=False)

    if exit_code == 0:
        print("  Pull Request criado com sucesso!")
        if stdout:
            print(f"    URL: {stdout.strip()}")
        return True
    else:
        print(
            f"  Erro ao criar Pull Request (Código: {exit_code}). Stderr: {stderr.strip()}",
            file=sys.stderr,
        )
        return False


def main_create_pr():
    """Função principal para a tarefa create-pr."""
    parser = core_args_module.get_common_arg_parser(
        description=f"Executa a tarefa '{TASK_NAME}' para gerar título e corpo de um PR."
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
            "OBSERVACAO_ADICIONAL": args.observation,
        }

        if args.two_stage:
            template_path_to_load = (
                core_config.META_PROMPT_DIR / META_PROMPT_TEMPLATE_NAME
            )
            print(f"\nFluxo de Duas Etapas Selecionado")
        else:
            template_path_to_load = core_config.TEMPLATE_DIR / PROMPT_TEMPLATE_NAME
            print(f"\nFluxo Direto Selecionado")

        print(
            f"Usando Template: {template_path_to_load.relative_to(core_config.PROJECT_ROOT)}"
        )
        GEMINI_MODEL_STEP1 = core_config.GEMINI_MODEL_GENERAL_TASKS
        GEMINI_MODEL_STEP2 = core_config.GEMINI_MODEL_GENERAL_TASKS


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
        latest_dir_name_for_essentials = latest_context_dir_path.name if latest_context_dir_path else None

        max_tokens_for_main_call = api_client.calculate_max_input_tokens(GEMINI_MODEL_STEP2, verbose=verbose) # AC5.2


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
            
            preliminary_api_input_content = core_context.prepare_payload_for_selector_llm(
                TASK_NAME,
                args, 
                latest_dir_name_for_essentials,
                manifest_data_for_context_selection,
                selector_prompt_content,
                core_config.MAX_ESSENTIAL_TOKENS_FOR_SELECTOR_CALL,
                verbose 
            )

            suggested_files_from_api: List[str] = []
            try:
                if verbose: #AC5.2
                    print(f"  AC5.2: Chamando API Gemini. Modelo: {core_config.GEMINI_MODEL_FLASH}. MAX_INPUT_TOKENS_PER_CALL (para esta chamada seletora, não o principal): {core_config.SELECTOR_LLM_MAX_INPUT_TOKENS}")
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
                    max_input_tokens_for_this_call=core_config.SELECTOR_LLM_MAX_INPUT_TOKENS
                )
                # ... (parsing da resposta da API preliminar) ...
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
                        verbose=verbose 
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
                verbose=verbose
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
                verbose=verbose
            )

        if not context_parts and verbose:
            print("Aviso: Nenhuma parte de contexto carregada.", file=sys.stderr)

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
                    if verbose: #AC5.2
                         print(f"  AC5.2: Chamando API Gemini. Modelo: {GEMINI_MODEL_STEP1}. MAX_INPUT_TOKENS_PER_CALL: {api_client.calculate_max_input_tokens(GEMINI_MODEL_STEP1, verbose=False)}")
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
                        max_input_tokens_for_this_call=api_client.calculate_max_input_tokens(GEMINI_MODEL_STEP1, verbose=False)
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
            print(final_prompt_to_send.strip() if final_prompt_to_send else "Não houve resposta")
            print("--- Fim ---")
            sys.exit(0)

        final_response_content: Optional[str] = None
        final_prompt_current = final_prompt_to_send
        while True:
            step_name = "Etapa 2: Enviando" if args.two_stage else "Enviando"
            print(
                f"\n{step_name} Prompt Final + Contexto ({len(context_parts)} partes) para gerar título/corpo do PR..."
            )
            contents_final = [
                types.Part.from_text(text=final_prompt_current)
            ] + context_parts
            try:
                if verbose: #AC5.2
                    print(f"  AC5.2: Chamando API Gemini. Modelo: {GEMINI_MODEL_STEP2}. MAX_INPUT_TOKENS_PER_CALL: {max_tokens_for_main_call}")
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
                    max_input_tokens_for_this_call=max_tokens_for_main_call
                )
                print("\n--- Resposta da LLM (Título/Corpo do PR) ---")
                print(final_response_content.strip() if final_response_content else "")
                print("---")
                if args.yes:
                    user_choice_final, observation_final = "y", None
                    print("  Resposta da LLM auto-confirmada (--yes).") 
                else:
                    user_choice_final, observation_final = io_utils.confirm_step(
                        "Prosseguir com este título/corpo de PR?"
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
                print(f"  Erro durante chamada API para gerar PR: {e}", file=sys.stderr)
                if "Prompt bloqueado" in str(e):
                    sys.exit(1)
                retry_choice_final, _ = io_utils.confirm_step(
                    "Chamada API para PR falhou. Tentar novamente?"
                )
                if retry_choice_final != "y":
                    sys.exit(1)

        if final_response_content is None:
            print("Erro: Nenhuma resposta final para o PR obtida.", file=sys.stderr)
            sys.exit(1)

        print("\nParseando título e corpo do PR da resposta da LLM...")
        pr_title, pr_body = io_utils.parse_pr_content(final_response_content)

        if pr_title and pr_body is not None:
            current_branch = get_current_branch(verbose)
            if not current_branch:
                print(
                    "Erro: Não foi possível obter o branch Git atual. Abortando criação do PR.",
                    file=sys.stderr,
                )
                sys.exit(1)

            target_branch = args.target_branch
            print(f"  Branch Atual (Head): {current_branch}")
            print(f"  Branch Alvo (Base): {target_branch}")

            if not check_new_commits(target_branch, current_branch, verbose):
                print(
                    f"Erro: Nenhum commit novo no branch '{current_branch}' em relação a '{target_branch}'. Abortando criação do PR.",
                    file=sys.stderr,
                )
                sys.exit(1)

            issue_ref_str = f"Closes #{args.issue}"
            if issue_ref_str not in pr_body:
                print(f"  Adicionando '{issue_ref_str}' ao corpo do PR.")
                pr_body += f"\n\n{issue_ref_str}"

            pr_confirm_choice, _ = io_utils.confirm_step(
                f"Confirmar criação de {'RASCUNHO de ' if args.draft else ''}PR com o título:\n'{pr_title}'\nE corpo:\n{pr_body[:300]}... ?"
            )
            if pr_confirm_choice == "y":
                if create_github_pr(
                    pr_title,
                    pr_body,
                    current_branch,
                    target_branch,
                    args.draft,
                    verbose,
                ):
                    print("\nProcesso de criação de PR finalizado.")
                else:
                    print("\nCriação do PR falhou.", file=sys.stderr)
                    sys.exit(1)
            else:
                print("Criação do PR cancelada pelo usuário.")
                io_utils.save_llm_response(
                    TASK_NAME + "_user_cancelled_pr_creation", final_response_content
                )
        else:
            print(
                "Erro: Falha ao parsear o título/corpo do PR da resposta da LLM.",
                file=sys.stderr,
            )
            io_utils.save_llm_response(
                TASK_NAME + "_parsing_failed", final_response_content
            )
            sys.exit(1)
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
    main_create_pr()