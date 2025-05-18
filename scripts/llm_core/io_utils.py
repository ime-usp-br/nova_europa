# -*- coding: utf-8 -*-
"""
LLM Core Input/Output Utilities Module.
"""
import sys
import re
import datetime
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

from . import config as core_config # Import the core config

def save_llm_response(task_name: str, response_content: str, output_dir_base: Path = core_config.OUTPUT_DIR_BASE) -> None:
    """Saves the LLM's final response to a timestamped file within a task-specific directory."""
    try:
        task_output_dir = output_dir_base / task_name
        task_output_dir.mkdir(parents=True, exist_ok=True)
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{timestamp_str}.txt"
        output_filepath = task_output_dir / output_filename
        output_filepath.write_text(response_content, encoding="utf-8")
        print(f"  Resposta LLM salva em: {output_filepath.relative_to(core_config.PROJECT_ROOT)}")
    except OSError as e:
        print(f"Erro ao criar diretório de saída {task_output_dir}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"Erro ao salvar resposta LLM: {e}", file=sys.stderr)
        # traceback.print_exc() # Uncomment for more detailed debug if needed

def confirm_step(prompt_message: str) -> Tuple[str, Optional[str]]:
    """
    Asks the user for confirmation (Y/n/q).
    If 'n' is chosen, prompts for an observation/feedback.
    Returns a tuple: (user_choice, observation_or_none).
    """
    while True:
        response = input(f"{prompt_message} (Y/n/q - Sim/Não+Feedback/Sair) [Y]: ").lower().strip()
        if response in ["y", "yes", "s", "sim", ""]: # Accept 's' and 'sim' for Yes
            return "y", None
        elif response in ["n", "no", "nao"]: # Accept 'nao' for No
            observation = input("Por favor, insira sua observação/regra para melhorar o passo anterior: ").strip()
            if not observation:
                print("Observação não pode ser vazia se você deseja refazer. Tente novamente ou escolha 'y'/'q'.")
                continue
            return "n", observation
        elif response in ["q", "quit", "sair"]: # Accept 'sair' for Quit
            return "q", None
        else:
            print("Entrada inválida. Por favor, digite Y (ou S), n (ou nao), ou q (ou sair).")

def parse_pr_content(llm_output: str) -> Tuple[Optional[str], Optional[str]]:
    """Parses the LLM output for create-pr task to extract PR title and body."""
    title = None
    body = None

    # Regex to capture title (everything after TITLE delimiter until BODY delimiter)
    # and body (everything after BODY delimiter)
    # Using re.DOTALL to make '.' match newlines as well.
    # Using re.MULTILINE for ^ and $ to match start/end of lines.
    title_match = re.search(
        rf"^{re.escape(core_config.PR_CONTENT_DELIMITER_TITLE)}\s*(.*?)\s*{re.escape(core_config.PR_CONTENT_DELIMITER_BODY)}",
        llm_output,
        re.DOTALL | re.MULTILINE
    )
    body_match = re.search(
        rf"{re.escape(core_config.PR_CONTENT_DELIMITER_BODY)}\s*(.*)",
        llm_output,
        re.DOTALL | re.MULTILINE
    )

    if title_match:
        title = title_match.group(1).strip()
    if body_match:
        body = body_match.group(1).strip()

    if title is None or body is None:
        print(f"Erro: Não foi possível parsear a saída da LLM para o PR. Delimitadores '{core_config.PR_CONTENT_DELIMITER_TITLE}' ou '{core_config.PR_CONTENT_DELIMITER_BODY}' não encontrados ou formato incorreto.", file=sys.stderr)
        return None, None

    return title, body

def parse_summaries_from_response(llm_response: str) -> Dict[str, str]:
    """Parses the LLM response to extract individual file summaries."""
    summaries: Dict[str, str] = {}
    # Regex to find blocks: --- START OF FILE (filepath) ---\n(summary_content)\n--- END OF FILE (filepath) ---
    # It captures the filepath (group 1) and the summary_content (group 2)
    # re.DOTALL allows '.' to match newlines within summary_content
    # re.MULTILINE allows '^' and '$' to match start/end of lines for delimiters
    pattern = re.compile(
        rf"^{re.escape(core_config.SUMMARY_CONTENT_DELIMITER_START)}(.*?){re.escape(' ---')}\n(.*?)\n^{re.escape(core_config.SUMMARY_CONTENT_DELIMITER_END)}\1{re.escape(' ---')}",
        re.MULTILINE | re.DOTALL
    )
    matches = pattern.findall(llm_response)
    for filepath, summary in matches:
        summaries[filepath.strip()] = summary.strip()
    return summaries