#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ==============================================================================
# llm_interact.py (v3.0.0 - Modularized)
#
# Script principal para interagir com a API Gemini.
# Atua como um dispatcher para scripts de tarefas individuais localizados em scripts/tasks/.
# Gerencia argumentos comuns e descobre tarefas disponíveis.
#
# Esta versão foi refatorada para usar o llm_core e invocar scripts de tarefa.
# ==============================================================================

import argparse
import os
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Optional

from llm_core import config as core_config
from llm_core import args as core_args_module  # Renomeado para evitar conflito
from llm_core import utils as core_utils
from llm_core import prompts as core_prompts_module  # Renomeado
from llm_core import api_client as core_api_client  # Renomeado


def find_task_scripts(tasks_dir: Path) -> Dict[str, Path]:
    """Descobre scripts de tarefa disponíveis no diretório especificado."""
    task_scripts = {}
    if not tasks_dir.is_dir():
        return task_scripts
    for filepath in tasks_dir.glob("llm_task_*.py"):
        if filepath.is_file() and os.access(
            filepath, os.X_OK
        ):  # Verifica se é executável
            task_name = filepath.stem.replace("llm_task_", "").replace("_", "-")
            if task_name:
                task_scripts[task_name] = filepath
    return task_scripts


def main():
    # Descobrir tarefas disponíveis a partir de scripts/tasks/
    available_task_scripts = find_task_scripts(
        core_config.PROJECT_ROOT / "scripts" / "tasks"
    )
    available_task_names = list(available_task_scripts.keys())

    # Configurar parser de argumentos base (ainda sem o argumento 'task')
    # A descrição será mais genérica para o dispatcher
    parser = core_args_module.get_common_arg_parser(
        description="Dispatcher para tarefas de interação com LLM."
    )

    # Adicionar o argumento posicional 'task' com as escolhas descobertas
    task_choices_str = (
        ", ".join(available_task_names)
        if available_task_names
        else "Nenhuma tarefa encontrada"
    )
    parser.add_argument(
        "task",
        nargs="?",  # Tarefa é opcional, para permitir seleção interativa
        choices=available_task_names if available_task_names else None,
        help=f"Tarefa a ser executada. Se omitido, será solicitado. Disponíveis: {task_choices_str}",
        metavar="TASK_NAME",
    )

    # Adicionar epílogo com exemplos de como chamar tarefas específicas
    script_name = Path(sys.argv[0]).name if sys.argv else "llm_interact.py"
    epilog_lines = [
        "\nExemplos de uso (invocando tarefas diretamente):",
        f"  python scripts/tasks/llm_task_resolve_ac.py -i 123 -a 1",
        f"  python scripts/tasks/llm_task_commit_mesage.py -i 123 -g",
        "\nExemplos de uso (usando este dispatcher):",
        f"  python {script_name} resolve-ac -i 123 -a 1",
        f"  python {script_name} # Para seleção interativa da tarefa",
    ]
    parser.epilog = "\n".join(epilog_lines)

    try:
        args, unknown_args = (
            parser.parse_known_args()
        )  # Permite que scripts de tarefa tenham seus próprios args
    except SystemExit as e:
        sys.exit(e.code)

    selected_task_name = args.task
    if not selected_task_name:
        if not available_task_names:
            print(
                "Erro: Nenhuma tarefa LLM (scripts/tasks/llm_task_*.py) encontrada ou executável.",
                file=sys.stderr,
            )
            sys.exit(1)
        # Usa a função de prompt do core (adaptada)
        # Para isso, precisamos passar o dicionário de scripts, não só nomes
        selected_task_name = core_prompts_module.prompt_user_to_select_task(
            available_task_scripts
        )
        if not selected_task_name:
            print("Nenhuma tarefa selecionada. Saindo.")
            sys.exit(0)

    if selected_task_name not in available_task_scripts:
        print(
            f"Erro: Tarefa '{selected_task_name}' desconhecida. Tarefas disponíveis: {', '.join(available_task_names)}",
            file=sys.stderr,
        )
        parser.print_help()
        sys.exit(1)

    task_script_path = available_task_scripts[selected_task_name]

    # Montar o comando para executar o script da tarefa
    # O primeiro argumento é o Python interpreter, seguido pelo script da tarefa
    # Depois, passamos todos os argumentos que foram parseados por este dispatcher
    # E quaisquer argumentos desconhecidos que podem ser para o script da tarefa

    # Recriar a lista de argumentos para o subprocesso
    # Começa com os argumentos que o dispatcher reconheceu e deve repassar
    # Filtra o argumento 'task' pois ele já foi usado para selecionar o script
    forwarded_args_list = []
    for arg_name, arg_value in vars(args).items():
        if (
            arg_name == "task"
        ):  # Não repassa o nome da tarefa como argumento para o script da tarefa
            continue
        if isinstance(arg_value, bool):
            if arg_value:  # Adiciona flags booleanas apenas se True
                forwarded_args_list.append(f"--{arg_name.replace('_', '-')}")
        elif isinstance(arg_value, list):  # Para argumentos 'append'
            for item in arg_value:
                forwarded_args_list.append(f"--{arg_name.replace('_', '-')}")
                forwarded_args_list.append(str(item))
        elif arg_value is not None:  # Para argumentos com valor
            forwarded_args_list.append(f"--{arg_name.replace('_', '-')}")
            forwarded_args_list.append(str(arg_value))

    # Adiciona quaisquer argumentos não reconhecidos pelo dispatcher
    # Estes são presumivelmente para o script da tarefa
    final_task_cmd = (
        [sys.executable, str(task_script_path)] + forwarded_args_list + unknown_args
    )

    print(
        f"\nInvocando script da tarefa '{selected_task_name}': {' '.join(shlex.quote(str(s)) for s in final_task_cmd)}"
    )

    try:
        # Não captura a saída aqui, deixa o script da tarefa imprimir diretamente
        process = subprocess.Popen(final_task_cmd, cwd=core_config.PROJECT_ROOT)
        process.wait()  # Espera o script da tarefa terminar
        print(
            f"\nScript da tarefa '{selected_task_name}' finalizado com código de saída: {process.returncode}"
        )
        sys.exit(process.returncode)
    except FileNotFoundError:
        print(
            f"Erro: Script da tarefa '{task_script_path}' não encontrado.",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as e:
        print(
            f"Erro ao executar o script da tarefa '{selected_task_name}': {e}",
            file=sys.stderr,
        )
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
