# -*- coding: utf-8 -*-
"""
LLM Core Input/Output Utilities Module.
"""
import sys
import re
import datetime
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

from . import config as core_config  # Import the core config


def save_llm_response(
    task_name: str,
    response_content: str,
    output_dir_base_override: Optional[Path] = None,  # Novo argumento opcional
) -> None:
    """Saves the LLM's final response to a timestamped file within a task-specific directory."""

    current_output_dir_base = (
        output_dir_base_override
        if output_dir_base_override is not None
        else core_config.OUTPUT_DIR_BASE
    )

    try:
        task_output_dir = current_output_dir_base / task_name
        task_output_dir.mkdir(parents=True, exist_ok=True)
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{timestamp_str}.txt"
        output_filepath = task_output_dir / output_filename
        output_filepath.write_text(response_content, encoding="utf-8")
        print(
            f"  Resposta LLM salva em: {output_filepath.relative_to(core_config.PROJECT_ROOT)}"
        )
    except OSError as e:
        print(
            f"Erro ao criar diretório de saída {task_output_dir}: {e}", file=sys.stderr
        )
    except Exception as e:
        print(f"Erro ao salvar resposta LLM: {e}", file=sys.stderr)


def confirm_step(prompt_message: str) -> Tuple[str, Optional[str]]:
    """
    Asks the user for confirmation (Y/n/q).
    If 'n' is chosen, prompts for an observation/feedback.
    Returns a tuple: (user_choice, observation_or_none).
    """
    while True:
        response = (
            input(f"{prompt_message} (Y/n/q - Sim/Não+Feedback/Sair) [Y]: ")
            .lower()
            .strip()
        )
        if response in ["y", "yes", "s", "sim", ""]:
            return "y", None
        elif response in ["n", "no", "nao"]:
            observation = input(
                "Por favor, insira sua observação/regra para melhorar o passo anterior: "
            ).strip()
            if not observation:
                print(
                    "Observação não pode ser vazia se você deseja refazer. Tente novamente ou escolha 'y'/'q'."
                )
                continue
            return "n", observation
        elif response in ["q", "quit", "sair"]:
            return "q", None
        else:
            print(
                "Entrada inválida. Por favor, digite Y (ou S), n (ou nao), ou q (ou sair)."
            )


def parse_pr_content(llm_output: str) -> Tuple[Optional[str], Optional[str]]:
    """Parses the LLM output for create-pr task to extract PR title and body."""
    title: Optional[str] = None
    body: Optional[str] = None

    try:
        # Encontrar o início do título
        title_start_delimiter = core_config.PR_CONTENT_DELIMITER_TITLE
        title_start_index = llm_output.index(title_start_delimiter) + len(
            title_start_delimiter
        )

        # Encontrar o início do corpo (que é o fim do título)
        body_start_delimiter = core_config.PR_CONTENT_DELIMITER_BODY
        body_start_index = llm_output.index(body_start_delimiter, title_start_index)

        title = llm_output[title_start_index:body_start_index].strip()

        # O corpo começa após o delimitador do corpo
        body_content_start_index = body_start_index + len(body_start_delimiter)
        body = llm_output[body_content_start_index:].strip()

        if (
            not title or body is None
        ):  # Body pode ser string vazia, mas não None se delimitador presente
            # Se o título foi encontrado mas o corpo não (ou vice-versa de forma estranha), considera falha
            # Esta condição pode ser ajustada se um corpo vazio após o delimitador for válido
            # e title não for None. Se body for "" (string vazia), está OK.
            # O problema é se o DELIMITADOR do corpo não for encontrado.
            # A lógica acima com `index` já levantaria ValueError se os delimitadores não existissem.
            # A checagem `if not title or body is None` é mais para o caso de
            # os delimitadores existirem mas o conteúdo entre eles ser problemático
            # ou se um delimitador é encontrado mas o subsequente não,
            # o que seria pego pelo `except ValueError` abaixo.
            # Se chegamos aqui, ambos delimitadores foram encontrados.
            pass  # Ambos delimitadores foram encontrados, title e body foram extraídos.

    except ValueError:  # Ocorre se .index() não encontrar os delimitadores
        print(
            f"Erro: Não foi possível parsear a saída da LLM para o PR. Delimitadores '{core_config.PR_CONTENT_DELIMITER_TITLE}' ou '{core_config.PR_CONTENT_DELIMITER_BODY}' não encontrados ou formato incorreto.",
            file=sys.stderr,
        )
        return None, None

    return title, body


def parse_summaries_from_response(llm_response: str) -> Dict[str, str]:
    """Parses the LLM response to extract individual file summaries."""
    summaries: Dict[str, str] = {}
    pattern = re.compile(
        rf"^{re.escape(core_config.SUMMARY_CONTENT_DELIMITER_START)}(.*?){re.escape(' ---')}\n(.*?)\n^{re.escape(core_config.SUMMARY_CONTENT_DELIMITER_END)}\1{re.escape(' ---')}",
        re.MULTILINE | re.DOTALL,
    )
    matches = pattern.findall(llm_response)
    for filepath, summary in matches:
        summaries[filepath.strip()] = summary.strip()
    return summaries
