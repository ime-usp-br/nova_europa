#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
llm_interact.py: Script para interagir com a API Google Gemini usando o contexto do projeto.

Este script automatizará as interações com o LLM Gemini, utilizando arquivos de contexto
gerados por 'gerar_contexto_llm.sh' e meta-prompts para otimizar tarefas de
desenvolvimento como gerar mensagens de commit, analisar código, etc.
"""

import argparse
import os
import sys
from pathlib import Path

# --- Configuration ---
# Presume que o script está em /scripts e os templates em /project_templates/meta-prompts
BASE_DIR = Path(__file__).resolve().parent.parent
META_PROMPT_DIR = BASE_DIR / "project_templates/meta-prompts"
CONTEXT_DIR_BASE = BASE_DIR / "code_context_llm"
OUTPUT_DIR_BASE = BASE_DIR / "llm_outputs" # Diretório para salvar saídas, deve estar no .gitignore


def find_available_tasks(prompt_dir: Path) -> dict[str, Path]:
    """
    Encontra as tarefas disponíveis (meta-prompts) no diretório especificado.

    Args:
        prompt_dir: O Path para o diretório contendo os arquivos meta-prompt.

    Returns:
        Um dicionário mapeando nomes de tarefas para os Paths dos arquivos.
        Retorna um dicionário vazio se o diretório não existir ou não contiver prompts.
    """
    tasks = {}
    if not prompt_dir.is_dir():
        print(f"Error: Meta-prompt directory not found: {prompt_dir}", file=sys.stderr)
        return tasks
    # Padrão esperado: meta-prompt-task_name.txt
    for filepath in prompt_dir.glob("meta-prompt-*.txt"):
        if filepath.is_file():
            task_name = filepath.stem.replace("meta-prompt-", "")
            if task_name:
                tasks[task_name] = filepath
    return tasks


def parse_arguments(available_tasks: list[str]) -> argparse.Namespace:
    """
    Analisa os argumentos da linha de comando.

    Args:
        available_tasks: Uma lista dos nomes das tarefas disponíveis para usar
                         como opções de escolha.

    Returns:
        Um objeto Namespace contendo os argumentos analisados.
    """
    parser = argparse.ArgumentParser(
        description="Interact with Google Gemini using project context and meta-prompts.",
        formatter_class=argparse.RawDescriptionHelpFormatter # Preserva formatação no help
    )
    parser.add_argument(
        "task",
        choices=sorted(available_tasks), # Apresenta as opções em ordem alfabética
        help=f"The task to perform, based on available meta-prompts in {META_PROMPT_DIR}.",
        metavar="TASK"
    )
    # --- Argumentos para variáveis dos meta-prompts (AC3 - a ser implementado) ---
    parser.add_argument("--issue", help="Issue number (required by some tasks).")
    parser.add_argument("--ac", help="Acceptance Criteria number (required by some tasks).")
    parser.add_argument("--suggestion", help="Suggestion text (required by some tasks).")
    # Adicionar outros argumentos conforme necessário para diferentes meta-prompts

    # TODO: Adicionar argumento opcional para especificar diretório de contexto,
    # se não, usar o mais recente. (Parte do AC4)

    # TODO: Adicionar argumento opcional para especificar o diretório de saída.
    # (Parte do AC8)

    return parser.parse_args()

# --- Main Execution ---
if __name__ == "__main__":
    available_tasks_dict = find_available_tasks(META_PROMPT_DIR)
    available_task_names = list(available_tasks_dict.keys())

    if not available_task_names:
        print(f"Error: No meta-prompt files found in '{META_PROMPT_DIR}'. Exiting.", file=sys.stderr)
        sys.exit(1)

    try:
        args = parse_arguments(available_task_names)
        selected_task = args.task
        selected_meta_prompt_path = available_tasks_dict[selected_task]

        print(f"Script de Interação LLM")
        print(f"========================")
        print(f"Tarefa Selecionada: {selected_task}")
        print(f"Usando Meta-Prompt: {selected_meta_prompt_path.relative_to(BASE_DIR)}")
        print(f"------------------------")

        # Placeholder para a lógica principal que será desenvolvida
        # para atender aos outros Critérios de Aceite (ACs) da Issue #28.

        # 1. (AC4) Encontrar diretório de contexto mais recente
        # context_dir = find_latest_context_dir(CONTEXT_DIR_BASE)
        # print(f"Diretório de Contexto: {context_dir.relative_to(BASE_DIR) if context_dir else 'Não encontrado'}")

        # 2. (AC3) Coletar e validar variáveis necessárias para o meta-prompt
        # required_vars = get_required_vars(selected_meta_prompt_path)
        # task_variables = collect_task_variables(args, required_vars) # Coleta de args ou interativamente

        # 3. (AC5) Carregar meta-prompt e substituir variáveis
        # meta_prompt_content = load_and_fill_template(selected_meta_prompt_path, task_variables)

        # 4. (AC4, AC5) Carregar arquivos de contexto
        # context_files = load_context_files(context_dir)

        # 5. (AC5, AC6, AC7, AC10, AC11) Chamar API Gemini (Etapa 1: Meta-prompt -> Prompt Final)
        # gemini_client = initialize_gemini_client() # (AC5 - usar GEMINI_API_KEY)
        # final_prompt_text = execute_gemini_step(gemini_client, meta_prompt_content, context_files)
        # print(f"--- Prompt Final Gerado ---\n{final_prompt_text}\n---------------------------")
        # # (AC7, AC10, AC11) Loop de confirmação/refinamento aqui

        # 6. (AC6) Chamar API Gemini (Etapa 2: Prompt Final -> Resposta Final)
        # final_response = execute_gemini_step(gemini_client, final_prompt_text, context_files)
        # print(f"--- Resposta Final da IA ---\n{final_response}\n--------------------------")

        # 7. (AC8) Salvar resposta final
        # save_output(final_response, OUTPUT_DIR_BASE, selected_task)
        # (AC9 - garantir que OUTPUT_DIR_BASE está no .gitignore já foi feito manualmente)

        # 8. (AC9) Tratamento de erros em todo o processo
        print("\nPlaceholder: Lógica principal de interação com LLM ainda não implementada.")
        pass

    except Exception as e:
        print(f"\nErro inesperado durante a execução: {e}", file=sys.stderr)
        sys.exit(1)