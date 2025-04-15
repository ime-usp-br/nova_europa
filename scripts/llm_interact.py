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
import re
import glob # Importado para listagem de diretórios

# --- Configuration ---
# Presume que o script está em /scripts e os templates em /project_templates/meta-prompts
BASE_DIR = Path(__file__).resolve().parent.parent
META_PROMPT_DIR = BASE_DIR / "project_templates/meta-prompts"
CONTEXT_DIR_BASE = BASE_DIR / "code_context_llm"
OUTPUT_DIR_BASE = BASE_DIR / "llm_outputs" # Diretório para salvar saídas, deve estar no .gitignore
TIMESTAMP_DIR_REGEX = r'^\d{8}_\d{6}$' # Regex para validar o formato do nome do diretório


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

def find_latest_context_dir(context_base_dir: Path) -> Path | None:
    """
    Encontra o diretório de contexto mais recente dentro do diretório base.

    Args:
        context_base_dir: O Path para o diretório base onde os diretórios
                          de contexto (com timestamp) estão localizados.

    Returns:
        Um objeto Path para o diretório mais recente encontrado, ou None se
        nenhum diretório válido for encontrado ou o diretório base não existir.
    """
    if not context_base_dir.is_dir():
        print(f"Error: Context base directory not found: {context_base_dir}", file=sys.stderr)
        return None

    valid_context_dirs = []
    for item in context_base_dir.iterdir():
        if item.is_dir() and re.match(TIMESTAMP_DIR_REGEX, item.name):
            valid_context_dirs.append(item)

    if not valid_context_dirs:
        print(f"Error: No valid context directories (YYYYMMDD_HHMMSS format) found in {context_base_dir}", file=sys.stderr)
        return None

    # Ordena os diretórios pelo nome (timestamp) em ordem decrescente
    latest_context_dir = sorted(valid_context_dirs, reverse=True)[0]
    return latest_context_dir


def load_and_fill_template(template_path: Path, variables: dict) -> str:
    """
    Carrega um template de meta-prompt e substitui os placeholders pelas variáveis fornecidas.

    Args:
        template_path: O Path para o arquivo de template.
        variables: Um dicionário onde as chaves são nomes de variáveis (sem __)
                   e os valores são os dados para substituição.

    Returns:
        O conteúdo do template com as variáveis substituídas.
        Retorna uma string vazia se o template não puder ser lido ou ocorrer erro.
    """
    try:
        content = template_path.read_text(encoding='utf-8')
        # Função auxiliar para lidar com a substituição
        def replace_match(match):
            var_name = match.group(1)
            # Retorna o valor da variável do dicionário ou uma string vazia se não existir
            # Garante que o valor seja uma string para substituição
            return str(variables.get(var_name, ''))

        # Regex para encontrar placeholders como __VARIAVEL_EXEMPLO__
        filled_content = re.sub(r'__([A-Z_]+)__', replace_match, content)
        return filled_content
    except FileNotFoundError:
        print(f"Error: Template file not found: {template_path}", file=sys.stderr)
        return ""
    except Exception as e:
        print(f"Error reading or processing template {template_path}: {e}", file=sys.stderr)
        return ""


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
    # --- Argumentos para variáveis dos meta-prompts (AC3) ---
    parser.add_argument("--issue", help="Issue number (e.g., 28). Used to fill __NUMERO_DA_ISSUE__.")
    parser.add_argument("--ac", help="Acceptance Criteria number (e.g., 3). Used to fill __NUMERO_DO_AC__.")
    parser.add_argument("--suggestion", help="Suggestion text for the task. Used to fill __COLOQUE_AQUI_SUA_SUGESTAO__.", default="")
    # Adicionar outros argumentos conforme necessário para diferentes meta-prompts

    # TODO: Adicionar argumento opcional para especificar diretório de contexto,
    # se não, usar o mais recente. (Parte do AC4) - [FEITO em AC4, mas argumento não adicionado ainda]

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

        # --- AC4: Encontrar diretório de contexto mais recente ---
        context_dir = find_latest_context_dir(CONTEXT_DIR_BASE)
        if context_dir is None:
            # A função find_latest_context_dir já imprime o erro específico.
            print("Erro: Não foi possível encontrar um diretório de contexto válido. Saindo.", file=sys.stderr)
            sys.exit(1)
        print(f"Diretório de Contexto: {context_dir.relative_to(BASE_DIR)}")
        # --- Fim AC4 ---

        # --- AC3: Coletar variáveis e preencher meta-prompt ---
        task_variables = {
            "NUMERO_DA_ISSUE": args.issue if args.issue else "",
            "NUMERO_DO_AC": args.ac if args.ac else "",
            "COLOQUE_AQUI_SUA_SUGESTAO": args.suggestion
            # Adicionar mapeamento para outras variáveis/argumentos aqui se necessário
        }
        print(f"Variáveis para o template: {task_variables}")

        meta_prompt_content = load_and_fill_template(selected_meta_prompt_path, task_variables)

        if not meta_prompt_content:
             print(f"Erro ao carregar ou preencher o meta-prompt. Saindo.", file=sys.stderr)
             sys.exit(1)

        print(f"------------------------")
        print(f"Meta-Prompt Preenchido (para verificação - máx 500 chars):")
        print(meta_prompt_content[:500] + ("..." if len(meta_prompt_content) > 500 else ""))
        print(f"------------------------")
        # --- Fim AC3 ---

        # Placeholder para a lógica principal que será desenvolvida
        # para atender aos outros Critérios de Aceite (ACs) da Issue #28.

        # 1. (AC4) Encontrar diretório de contexto mais recente - [FEITO ACIMA]

        # 2. (AC4, AC5) Carregar arquivos de contexto
        # context_files = load_context_files(context_dir)

        # 3. (AC5, AC6, AC7, AC10, AC11) Chamar API Gemini (Etapa 1: Meta-prompt -> Prompt Final)
        # gemini_client = initialize_gemini_client() # (AC5 - usar GEMINI_API_KEY)
        # final_prompt_text = execute_gemini_step(gemini_client, meta_prompt_content, context_files)
        # print(f"--- Prompt Final Gerado ---\n{final_prompt_text}\n---------------------------")
        # # (AC7, AC10, AC11) Loop de confirmação/refinamento aqui

        # 4. (AC6) Chamar API Gemini (Etapa 2: Prompt Final -> Resposta Final)
        # final_response = execute_gemini_step(gemini_client, final_prompt_text, context_files)
        # print(f"--- Resposta Final da IA ---\n{final_response}\n--------------------------")

        # 5. (AC8) Salvar resposta final
        # save_output(final_response, OUTPUT_DIR_BASE, selected_task)
        # (AC9 - garantir que OUTPUT_DIR_BASE está no .gitignore já foi feito manualmente)

        # 6. (AC9) Tratamento de erros em todo o processo
        print("\nPlaceholder: Lógica principal de interação com LLM ainda não implementada.")
        pass

    except Exception as e:
        print(f"\nErro inesperado durante a execução: {e}", file=sys.stderr)
        sys.exit(1)