# tests/python/tasks/test_llm_task_resolve_ac.py
import pytest
import argparse
from unittest.mock import patch, MagicMock
from io import StringIO

# Adiciona o diretório raiz do projeto ao sys.path para importações corretas
import sys
from pathlib import Path

_project_root_dir_for_task_test = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root_dir_for_task_test) not in sys.path:
    sys.path.insert(0, str(_project_root_dir_for_task_test))

from scripts.tasks import llm_task_resolve_ac
from scripts.llm_core import (
    config as task_core_config,
)  # Importa o config usado pela task
from scripts.llm_core import (
    context as core_context_module,
)  # Para mockar find_latest_context_dir
from scripts.llm_core import (
    prompts as core_prompts_module,
)  # Para mockar load_and_fill_template
from scripts.llm_core import io_utils as core_io_utils  # Para mockar io_utils
from scripts.llm_core import api_client as core_api_client  # Para mockar api_client


def test_add_task_specific_args():
    """Testa se os argumentos específicos da tarefa são adicionados ao parser."""
    parser = argparse.ArgumentParser()
    llm_task_resolve_ac.add_task_specific_args(parser)

    action_dests = [action.dest for action in parser._actions]
    assert "issue" in action_dests
    assert "ac" in action_dests

    with pytest.raises(SystemExit):
        parser.parse_args([])

    with pytest.raises(SystemExit):
        parser.parse_args(["--issue", "123"])

    with pytest.raises(SystemExit):
        parser.parse_args(["--ac", "1"])
    try:
        parser.parse_args(["--issue", "123", "--ac", "1"])
    except SystemExit as e:
        for action in parser._actions:
            if action.dest == "issue" and action.required:
                pytest.fail(
                    "Erro inesperado ao parsear com --issue e --ac, SystemExit ocorreu mas não deveria ser por falta destes."
                )
            if action.dest == "ac" and action.required:
                pytest.fail(
                    "Erro inesperado ao parsear com --issue e --ac, SystemExit ocorreu mas não deveria ser por falta destes."
                )
        if e.code != 0:  # type: ignore
            pass


@patch("scripts.tasks.llm_task_resolve_ac.core_args_module.get_common_arg_parser")
@patch("scripts.tasks.llm_task_resolve_ac.api_client.startup_api_resources")
@patch("scripts.tasks.llm_task_resolve_ac.api_client.execute_gemini_call")
@patch("scripts.tasks.llm_task_resolve_ac.core_context.prepare_context_parts")
@patch("scripts.tasks.llm_task_resolve_ac.core_prompts_module.load_and_fill_template")
@patch("scripts.tasks.llm_task_resolve_ac.io_utils.save_llm_response")
@patch("scripts.tasks.llm_task_resolve_ac.io_utils.confirm_step")
@patch("scripts.tasks.llm_task_resolve_ac.api_client.shutdown_api_resources")
@patch(
    "scripts.tasks.llm_task_resolve_ac.core_context.find_latest_context_dir"
)  # Mock para find_latest_context_dir
def test_main_resolve_ac_direct_flow_success(
    mock_find_latest_context_dir,  # Adicionado mock
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
    """Testa o fluxo principal da tarefa resolve-ac (direto, com sucesso)."""
    mock_parser = MagicMock()
    mock_get_common_parser.return_value = mock_parser

    args = argparse.Namespace(
        issue="1",
        ac="1",
        observation="obs",
        two_stage=False,
        verbose=False,
        web_search=False,
        generate_context=False,
        select_context=False,
        exclude_context=[],
        only_meta=False,
        only_prompt=False,
        yes=True,
    )
    mock_parser.parse_args.return_value = args

    mock_startup_api.return_value = True
    mock_load_template.return_value = "Template preenchido para __NUMERO_DO_AC__"
    mock_prepare_context.return_value = [MagicMock(spec=Path)]  # type: ignore
    mock_execute_gemini.return_value = "--- START OF FILE path/to/code.php ---\nConteúdo do código\n--- END OF FILE path/to/code.php ---"
    mock_confirm_step.return_value = ("y", None)

    # Configura o mock para find_latest_context_dir para retornar um caminho válido dentro de tmp_path
    mock_latest_context_dir = tmp_path / "context_llm" / "code" / "20230101_120000"
    mock_latest_context_dir.mkdir(parents=True, exist_ok=True)
    mock_find_latest_context_dir.return_value = mock_latest_context_dir

    original_template_dir = task_core_config.TEMPLATE_DIR
    original_project_root = task_core_config.PROJECT_ROOT
    original_context_dir_base = task_core_config.CONTEXT_DIR_BASE
    original_common_context_dir = task_core_config.COMMON_CONTEXT_DIR

    monkeypatch.setattr(
        task_core_config, "TEMPLATE_DIR", tmp_path / "templates" / "prompts"
    )
    monkeypatch.setattr(task_core_config, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        task_core_config, "CONTEXT_DIR_BASE", tmp_path / "context_llm" / "code"
    )
    monkeypatch.setattr(
        task_core_config, "COMMON_CONTEXT_DIR", tmp_path / "context_llm" / "common"
    )

    (tmp_path / "templates" / "prompts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "context_llm" / "common").mkdir(parents=True, exist_ok=True)

    (
        tmp_path
        / "templates"
        / "prompts"
        / llm_task_resolve_ac.RESOLVE_AC_PROMPT_TEMPLATE_NAME
    ).write_text("Template content")

    try:
        llm_task_resolve_ac.main_resolve_ac()
    finally:
        monkeypatch.setattr(task_core_config, "TEMPLATE_DIR", original_template_dir)
        monkeypatch.setattr(task_core_config, "PROJECT_ROOT", original_project_root)
        monkeypatch.setattr(
            task_core_config, "CONTEXT_DIR_BASE", original_context_dir_base
        )
        monkeypatch.setattr(
            task_core_config, "COMMON_CONTEXT_DIR", original_common_context_dir
        )

    mock_get_common_parser.assert_called_once()
    mock_startup_api.assert_called_once()
    mock_load_template.assert_called_once_with(
        tmp_path
        / "templates"
        / "prompts"
        / llm_task_resolve_ac.RESOLVE_AC_PROMPT_TEMPLATE_NAME,
        {"NUMERO_DA_ISSUE": "1", "NUMERO_DO_AC": "1", "OBSERVACAO_ADICIONAL": "obs"},
    )
    mock_prepare_context.assert_called_once()
    mock_execute_gemini.assert_called_once()
    mock_save_response.assert_called_once_with(
        llm_task_resolve_ac.TASK_NAME, mock_execute_gemini.return_value.strip()
    )
    mock_shutdown_api.assert_called_once()
