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
import google.genai as genai
from google.genai import types
from google.genai import errors # Importar o módulo de erros
from dotenv import load_dotenv
import traceback # Para depuração de erros inesperados

# --- Configuration ---
# Presume que o script está em /scripts e os templates em /project_templates/meta-prompts
BASE_DIR = Path(__file__).resolve().parent.parent
META_PROMPT_DIR = BASE_DIR / "project_templates/meta-prompts"
CONTEXT_DIR_BASE = BASE_DIR / "code_context_llm"
OUTPUT_DIR_BASE = BASE_DIR / "llm_outputs" # Diretório para salvar saídas, deve estar no .gitignore
TIMESTAMP_DIR_REGEX = r'^\d{8}_\d{6}$' # Regex para validar o formato do nome do diretório
# Modelo Gemini a ser usado (escolha um modelo apropriado para as tarefas)
GEMINI_MODEL = 'gemini-2.5-pro-exp-03-25'


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

def prepare_context_parts(context_dir: Path) -> list[types.Part]:
    """
    Lista arquivos de contexto (.txt, .json) e os prepara como types.Part.

    Args:
        context_dir: O Path para o diretório de contexto.

    Returns:
        Uma lista de objetos types.Part representando o conteúdo dos arquivos.
    """
    context_parts = []
    if not context_dir or not context_dir.is_dir():
        print(f"Warning: Invalid context directory provided: {context_dir}", file=sys.stderr)
        return context_parts

    print("  Loading context files...")
    for filepath in context_dir.glob("*.txt"):
        if filepath.is_file():
            try:
                print(f"    - Reading {filepath.name}")
                content = filepath.read_text(encoding='utf-8')
                # Adiciona o nome do arquivo no início do conteúdo para o LLM saber a origem
                # CORREÇÃO: Use o argumento keyword 'text='
                context_parts.append(types.Part.from_text(text=f"--- START OF FILE {filepath.name} ---\n{content}\n--- END OF FILE {filepath.name} ---"))
            except Exception as e:
                print(f"    - Warning: Could not read text file {filepath.name}: {e}", file=sys.stderr)
    for filepath in context_dir.glob("*.json"):
         if filepath.is_file():
            try:
                print(f"    - Reading {filepath.name}")
                content = filepath.read_text(encoding='utf-8')
                # Adiciona o nome do arquivo no início do conteúdo para o LLM saber a origem
                # CORREÇÃO: Use o argumento keyword 'text='
                context_parts.append(types.Part.from_text(text=f"--- START OF FILE {filepath.name} ---\n{content}\n--- END OF FILE {filepath.name} ---"))
            except Exception as e:
                print(f"    - Warning: Could not read json file {filepath.name}: {e}", file=sys.stderr)
    print(f"  Loaded {len(context_parts)} context files.")
    return context_parts


def parse_arguments(available_tasks: list[str]) -> argparse.Namespace:
    """
    Analisa os argumentos da linha de comando, incluindo exemplos no epílogo.

    Args:
        available_tasks: Uma lista dos nomes das tarefas disponíveis.

    Returns:
        Um objeto Namespace contendo os argumentos analisados.
    """
    script_name = Path(sys.argv[0]).name # Obtém o nome do script para usar nos exemplos

    # --- Constrói a string de exemplos (epilog) ---
    epilog_lines = ["\nExamples:"]
    sorted_tasks = sorted(available_tasks)

    for task_name in sorted_tasks:
        if task_name == "commit-mesage":
            example = f"  {script_name} {task_name} --issue 28"
            epilog_lines.append(example)
        elif task_name == "resolve-ac":
            example = f"  {script_name} {task_name} --issue 28 --ac 5 --suggestion \"Verificar se a API key está sendo lida do .env\""
            epilog_lines.append(example)
        elif task_name == "analise-ac":
            example = f"  {script_name} {task_name} --issue 28 --ac 4"
            epilog_lines.append(example)
        else:
            # Exemplo genérico para outras tarefas
            example = f"  {script_name} {task_name} [--issue ISSUE] [--ac AC] [--suggestion SUGGESTION]"
            epilog_lines.append(example)

    epilog_text = "\n".join(epilog_lines)

    # --- Cria o parser ---
    parser = argparse.ArgumentParser(
        description="Interact with Google Gemini using project context and meta-prompts.",
        epilog=epilog_text, # Adiciona os exemplos ao final da ajuda
        formatter_class=argparse.RawDescriptionHelpFormatter # Preserva formatação
    )

    task_choices_str = ", ".join(sorted_tasks)
    parser.add_argument(
        "task",
        choices=sorted_tasks,
        help=(f"The task to perform, based on available meta-prompts in "
              f"'{META_PROMPT_DIR.relative_to(BASE_DIR)}'.\nAvailable tasks: {task_choices_str}"),
        metavar="TASK"
    )
    # --- Argumentos para variáveis dos meta-prompts ---
    parser.add_argument("--issue", help="Issue number (e.g., 28). Fills __NUMERO_DA_ISSUE__.")
    parser.add_argument("--ac", help="Acceptance Criteria number (e.g., 3). Fills __NUMERO_DO_AC__.")
    parser.add_argument("--suggestion", help="Suggestion text for the task. Fills __COLOQUE_AQUI_SUA_SUGESTAO__.", default="")

    return parser.parse_args()

# --- Main Execution ---
if __name__ == "__main__":
    # --- Carregar variáveis do .env ---
    dotenv_path = BASE_DIR / '.env'
    if dotenv_path.is_file():
        print(f"Loading environment variables from: {dotenv_path.relative_to(BASE_DIR)}")
        load_dotenv(dotenv_path=dotenv_path, verbose=True)
    else:
        print(f"Warning: .env file not found at {dotenv_path}. Relying on system environment variables.", file=sys.stderr)
    # --- Fim Carregar .env ---

    # --- AC5: Configurar Cliente GenAI com API Key ---
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set (checked both system env and .env file).", file=sys.stderr)
        print("Please set the GEMINI_API_KEY in your .env file or as a system environment variable.", file=sys.stderr)
        sys.exit(1)
    try:
        # Nota: Não especificamos 'vertexai=True', então usará a Gemini Developer API por padrão.
        genai_client = genai.Client(api_key=api_key)
        print("Google GenAI Client initialized successfully.")
    except Exception as e:
        print(f"Error initializing Google GenAI Client: {e}", file=sys.stderr)
        sys.exit(1)
    # --- Fim AC5 ---

    available_tasks_dict = find_available_tasks(META_PROMPT_DIR)
    available_task_names = list(available_tasks_dict.keys())

    if not available_task_names:
        print(f"Error: No meta-prompt files found in '{META_PROMPT_DIR}'. Exiting.", file=sys.stderr)
        sys.exit(1)

    try:
        # Agora parse_arguments usa a lista de tarefas para melhorar a ajuda
        args = parse_arguments(available_task_names)
        selected_task = args.task
        selected_meta_prompt_path = available_tasks_dict[selected_task]

        print(f"\nScript de Interação LLM") # Adiciona newline para separar da saída do dotenv
        print(f"========================")
        print(f"Tarefa Selecionada: {selected_task}")
        print(f"Usando Meta-Prompt: {selected_meta_prompt_path.relative_to(BASE_DIR)}")

        # --- AC4: Encontrar diretório de contexto mais recente ---
        context_dir = find_latest_context_dir(CONTEXT_DIR_BASE)
        if context_dir is None:
            print("Erro fatal: Não foi possível encontrar um diretório de contexto válido. Saindo.", file=sys.stderr)
            sys.exit(1)
        print(f"Diretório de Contexto: {context_dir.relative_to(BASE_DIR)}")
        # --- Fim AC4 ---

        # --- AC3: Coletar variáveis e preencher meta-prompt ---
        task_variables = {
            "NUMERO_DA_ISSUE": args.issue if args.issue else "",
            "NUMERO_DO_AC": args.ac if args.ac else "",
            "COLOQUE_AQUI_SUA_SUGESTAO": args.suggestion
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

        # --- AC6: Interação em Duas Etapas com Gemini API ---
        print("\nIniciando interação com Gemini API...")

        # Preparar partes de contexto (lendo arquivos .txt e .json)
        context_parts = prepare_context_parts(context_dir)
        if not context_parts:
             print("Warning: Nenhum arquivo de contexto carregado. A IA pode não ter informações suficientes.", file=sys.stderr)

        # --- Etapa 1: Meta-Prompt + Contexto -> Prompt Final ---
        print(f"Etapa 1: Enviando Meta-Prompt e Contexto para obter o Prompt Final (Modelo: {GEMINI_MODEL})...")
        prompt_final_content = None
        # CORREÇÃO: Passa o prompt como keyword argument 'text='
        contents_etapa1 = [types.Part.from_text(text=meta_prompt_content)] + context_parts
        try:
            # Converte a lista de Parts para o formato esperado por generate_content
            # A documentação (google-genai.md) sugere que uma lista de Parts
            # é convertida para um único UserContent.
            response_etapa1 = genai_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents_etapa1 # Passa a lista de parts diretamente
            )
            # Extrai o prompt final da resposta
            prompt_final_content = response_etapa1.text
            print("  Prompt Final recebido (primeiros 10000 caracteres):")
            print("  ```")
            print(prompt_final_content[:10000].strip() + ("..." if len(prompt_final_content) > 10000 else ""))
            print("  ```")
        except errors.APIError as e:
            print(f"  Erro na API Gemini (Etapa 1): Código {e.code} - {e.message}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"  Erro inesperado na Etapa 1: {e}", file=sys.stderr)
            traceback.print_exc()
            sys.exit(1)

        # --- Etapa 2: Prompt Final + Contexto -> Resposta Final ---
        resposta_final_content = None
        if prompt_final_content:
            print(f"\nEtapa 2: Enviando Prompt Final e Contexto para obter a Resposta Final (Modelo: {GEMINI_MODEL})...")
            # CORREÇÃO: Passa o prompt final como keyword argument 'text='
            contents_etapa2 = [types.Part.from_text(text=prompt_final_content)] + context_parts
            try:
                 response_etapa2 = genai_client.models.generate_content(
                     model=GEMINI_MODEL,
                     contents=contents_etapa2 # Passa a lista de parts diretamente
                 )
                 # Extrai a resposta final
                 resposta_final_content = response_etapa2.text
                 print("  Resposta Final recebida (primeiros 10000 caracteres):")
                 print("  ```")
                 print(resposta_final_content[:10000].strip() + ("..." if len(resposta_final_content) > 10000 else ""))
                 print("  ```")
            except errors.APIError as e:
                print(f"  Erro na API Gemini (Etapa 2): Código {e.code} - {e.message}", file=sys.stderr)
                sys.exit(1)
            except Exception as e:
                print(f"  Erro inesperado na Etapa 2: {e}", file=sys.stderr)
                traceback.print_exc()
                sys.exit(1)
        else:
            print("Erro: Não foi possível obter o prompt final da Etapa 1. Abortando Etapa 2.", file=sys.stderr)
            sys.exit(1)
        # --- Fim AC6 ---

        # Placeholder para AC que salva a saída
        if resposta_final_content:
            print("\nPlaceholder: Lógica para salvar 'resposta_final_content' em um arquivo ainda não implementada.")
            # AC futuro: Implementar salvamento em OUTPUT_DIR_BASE/<task_name>/<timestamp>.txt
            pass
        else:
             print("\nNenhuma resposta final foi gerada.", file=sys.stderr)


    except SystemExit as e:
        # Captura sys.exit() chamado pelo argparse em caso de erro ou -h
        # Evita imprimir o erro genérico "Erro inesperado" nesses casos
        if e.code != 0: # Se não foi uma saída normal (como -h)
             print(f"Argument parsing error.", file=sys.stderr)
        sys.exit(e.code) # Propaga o código de saída original
    except Exception as e:
        print(f"\nErro inesperado durante a execução: {e}", file=sys.stderr)
        traceback.print_exc() # Imprime o traceback completo
        sys.exit(1)