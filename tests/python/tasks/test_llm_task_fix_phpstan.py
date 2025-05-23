# tests/python/tasks/test_llm_task_fix_phpstan.py
import pytest
import argparse
from unittest.mock import patch, MagicMock

import sys
from pathlib import Path

_project_root_dir_for_task_test = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root_dir_for_task_test) not in sys.path:
    sys.path.insert(0, str(_project_root_dir_for_task_test))

from scripts.tasks import llm_task_fix_phpstan
from scripts.llm_core import config as task_core_config


def test_add_task_specific_args():
    """Testa se a função add_task_specific_args funciona (mesmo que não adicione args)."""
    parser = argparse.ArgumentParser()
    llm_task_fix_phpstan.add_task_specific_args(parser)
    action_dests = [
        action.dest for action in parser._actions if action.dest not in ["help"]
    ]
    assert not action_dests


@patch("scripts.tasks.llm_task_fix_phpstan.core_args_module.get_common_arg_parser")
@patch("scripts.tasks.llm_task_fix_phpstan.api_client.startup_api_resources")
@patch("scripts.tasks.llm_task_fix_phpstan.api_client.execute_gemini_call")
@patch("scripts.tasks.llm_task_fix_phpstan.core_context.prepare_context_parts")
@patch("scripts.tasks.llm_task_fix_phpstan.core_prompts_module.load_and_fill_template")
@patch("scripts.tasks.llm_task_fix_phpstan.io_utils.save_llm_response")
@patch("scripts.tasks.llm_task_fix_phpstan.io_utils.confirm_step")
@patch("scripts.tasks.llm_task_fix_phpstan.api_client.shutdown_api_resources")
def test_main_fix_phpstan_direct_flow_success(
    mock_shutdown_api,
    mock_confirm_step,
    mock_save_response,
    mock_load_template,
    mock_prepare_context,
    mock_execute_gemini,
    mock_startup_api,
    mock_get_common_parser,
    tmp_path,
    monkeypatch,
):
    """Testa o fluxo principal da tarefa fix-phpstan (direto, com sucesso)."""
    mock_parser_instance = MagicMock()
    mock_get_common_parser.return_value = mock_parser_instance

    args = argparse.Namespace(
        task=llm_task_fix_phpstan.TASK_NAME,
        issue=None,  # Não é obrigatório para esta task
        ac=None,  # Não é obrigatório para esta task
        observation="Fix PHPStan errors.",
        two_stage=False,
        verbose=False,
        web_search=False,
        generate_context=False,
        select_context=False,
        exclude_context=[],
        only_meta=False,
        only_prompt=False,
        yes=True,
        doc_file=None,
        target_branch=None,
        draft=False,
        manifest_path=None,
        force_summary=None,
        max_files_per_call=10,
    )
    mock_parser_instance.parse_args.return_value = args

    mock_startup_api.return_value = True
    mock_load_template.return_value = (
        "Template para corrigir erros PHPStan com observação: __OBSERVACAO_ADICIONAL__."
    )
    mock_prepare_context.return_value = [MagicMock(spec=Path)]
    mock_execute_gemini.return_value = "--- START OF FILE app/Services/MyService.php ---\n<?php\n// Conteúdo PHPStan corrigido\n--- END OF FILE app/Services/MyService.php ---"
    mock_confirm_step.return_value = ("y", None)

    original_template_dir = task_core_config.TEMPLATE_DIR
    original_project_root = task_core_config.PROJECT_ROOT
    monkeypatch.setattr(task_core_config, "TEMPLATE_DIR", tmp_path)
    monkeypatch.setattr(task_core_config, "PROJECT_ROOT", tmp_path)

    (tmp_path / llm_task_fix_phpstan.PROMPT_TEMPLATE_NAME).write_text(
        "Template fix phpstan"
    )

    try:
        llm_task_fix_phpstan.main_fix_phpstan()
    finally:
        monkeypatch.setattr(task_core_config, "TEMPLATE_DIR", original_template_dir)
        monkeypatch.setattr(task_core_config, "PROJECT_ROOT", original_project_root)

    mock_get_common_parser.assert_called_once()
    mock_startup_api.assert_called_once()
    mock_load_template.assert_called_once_with(
        tmp_path / llm_task_fix_phpstan.PROMPT_TEMPLATE_NAME,
        {
            "OBSERVACAO_ADICIONAL": "Fix PHPStan errors.",
        },
    )
    mock_prepare_context.assert_called_once()
    mock_execute_gemini.assert_called_once()
    assert mock_execute_gemini.call_args[0][0] == task_core_config.GEMINI_MODEL_RESOLVE
    mock_save_response.assert_called_once_with(
        llm_task_fix_phpstan.TASK_NAME, mock_execute_gemini.return_value.strip()
    )
    mock_shutdown_api.assert_called_once()


# Adicionar mais testes para:
# - Fluxo de duas etapas
# - Seleção de contexto
# - Resposta vazia da LLM (sem correções)
# - Erros na API
# - Interação do usuário (sem --yes)
