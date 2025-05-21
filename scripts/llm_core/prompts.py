# -*- coding: utf-8 -*-
"""
LLM Core Prompts and Tasks Module.
"""
import re
import sys
from pathlib import Path
from typing import Dict, Optional, Match

from . import config as core_config  # Import the core config


def load_and_fill_template(template_path: Path, variables: Dict[str, str]) -> str:
    """
    Carrega um template de prompt/meta-prompt de um arquivo e substitui
    placeholders no formato __NOME_DA_VARIAVEL__ pelos valores fornecidos.
    """
    try:
        content = template_path.read_text(encoding="utf-8")

        def replace_match(match: Match[str]) -> str:
            var_name = match.group(1)
            return str(variables.get(var_name, ""))

        filled_content = re.sub(r"__([A-Z0-9_]+)__", replace_match, content)
        return filled_content
    except FileNotFoundError:
        print(
            f"Erro: Arquivo de template não encontrado: {template_path}",
            file=sys.stderr,
        )
        return ""
    except Exception as e:
        print(f"Erro ao ler/processar template {template_path}: {e}", file=sys.stderr)
        return ""


def modify_prompt_with_observation(
    original_prompt: str, observation: Optional[str]
) -> str:
    """Appends user observation to the prompt for retrying, if observation is provided."""
    if not observation:
        return original_prompt
    modified_prompt = f"{original_prompt}\n\n--- USER FEEDBACK FOR RETRY ---\n{observation}\n--- END FEEDBACK ---"
    print("\n  >>> Prompt modificado com observação para nova tentativa <<<")
    return modified_prompt


def find_context_selector_prompt(
    task_name: str, two_stage_flow: bool
) -> Optional[Path]:
    """Finds the context selector prompt file for a given task and flow."""
    suffix = "-2stages" if two_stage_flow else "-1stage"

    # Determine the filename based on whether the task name already implies a stage
    # This handles cases where a task might ONLY have a 1-stage or 2-stage selector
    # or if the task name itself is generic and needs the suffix.
    if task_name.endswith(
        ("-1stage", "-2stages")
    ):  # If task_name already has stage suffix
        # Use task_name as is if it explicitly includes a stage,
        # but still ensure it matches the current flow intent if strictness is needed.
        # For now, assume if it has a stage, it's the one intended.
        # Or, better, strip any existing stage and re-apply the correct one.
        base_task_name = task_name.removesuffix("-1stage").removesuffix("-2stages")
        filename = f"select-context-for-{base_task_name}{suffix}.txt"
    else:
        filename = f"select-context-for-{task_name}{suffix}.txt"

    # core_config.CONTEXT_SELECTORS_DIR é o diretório base para os seletores
    # (e.g., PROJECT_ROOT / "templates" / "context_selectors")
    # Este valor é mockado nos testes pela fixture setup_selector_prompts_env
    prompt_path = core_config.CONTEXT_SELECTORS_DIR / filename

    if prompt_path.is_file():
        # core_config.PROJECT_ROOT também é mockado nos testes para tmp_path
        # para que relative_to funcione corretamente.
        print(
            f"  Encontrado prompt seletor de contexto: {prompt_path.relative_to(core_config.PROJECT_ROOT)}"
        )
        return prompt_path
    else:
        # Fallback: Try without stage suffix if stage-specific not found
        fallback_filename = f"select-context-for-{task_name}.txt"
        fallback_path = core_config.CONTEXT_SELECTORS_DIR / fallback_filename
        if fallback_path.is_file():
            print(
                f"  Aviso: Prompt seletor específico de estágio '{filename}' não encontrado. Usando fallback: {fallback_path.relative_to(core_config.PROJECT_ROOT)}",
                file=sys.stderr,
            )
            return fallback_path
        else:
            print(
                f"Erro: Prompt seletor de contexto não encontrado para tarefa '{task_name}' (tentado '{filename}' e fallback '{fallback_filename}')",
                file=sys.stderr,
            )
            return None
