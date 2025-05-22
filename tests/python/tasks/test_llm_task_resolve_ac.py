# tests/python/tasks/test_llm_task_resolve_ac.py
import pytest
import argparse
from unittest.mock import patch, MagicMock

# Adiciona o diretório raiz do projeto ao sys.path para importações corretas
import sys
from pathlib import Path

_project_root_dir_for_task_test = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root_dir_for_task_test) not in sys.path:
    sys.path.insert(0, str(_project_root_dir_for_task_test))

from scripts.tasks import llm_task_resolve_ac

# Importar o módulo config que o script da tarefa usa, para poder mocká-lo
from scripts.llm_core import config as task_core_config
from scripts.llm_core import (
    config as core_config_test_scope,
)  # Para restaurar depois, se necessário


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
        if e.code != 0:
            pass


@patch("scripts.tasks.llm_task_resolve_ac.core_args_module.get_common_arg_parser")
@patch("scripts.tasks.llm_task_resolve_ac.api_client.startup_api_resources")
@patch("scripts.tasks.llm_task_resolve_ac.api_client.execute_gemini_call")
@patch("scripts.tasks.llm_task_resolve_ac.core_context.prepare_context_parts")
@patch("scripts.tasks.llm_task_resolve_ac.core_prompts_module.load_and_fill_template")
@patch("scripts.tasks.llm_task_resolve_ac.io_utils.save_llm_response")
@patch("scripts.tasks.llm_task_resolve_ac.io_utils.confirm_step")
@patch("scripts.tasks.llm_task_resolve_ac.api_client.shutdown_api_resources")
def test_main_resolve_ac_direct_flow_success(
    mock_shutdown_api,
    mock_confirm_step,
    mock_save_response,
    mock_load_template,
    mock_prepare_context,
    mock_execute_gemini,
    mock_startup_api,
    mock_get_common_parser,
    tmp_path,
    monkeypatch,  # Adicionado monkeypatch
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
    mock_prepare_context.return_value = [MagicMock(spec=Path)]
    mock_execute_gemini.return_value = "--- START OF FILE path/to/code.php ---\nConteúdo do código\n--- END OF FILE path/to/code.php ---"
    mock_confirm_step.return_value = ("y", None)

    # --- CORREÇÃO PRINCIPAL AQUI ---
    # Monkeypatch as constantes de diretório DENTRO do módulo config que o script da tarefa usa.
    original_template_dir = task_core_config.TEMPLATE_DIR
    original_project_root = task_core_config.PROJECT_ROOT

    monkeypatch.setattr(
        task_core_config, "TEMPLATE_DIR", tmp_path
    )  # Agora TEMPLATE_DIR aponta para tmp_path
    monkeypatch.setattr(
        task_core_config, "PROJECT_ROOT", tmp_path
    )  # PROJECT_ROOT também aponta para tmp_path

    (tmp_path / llm_task_resolve_ac.RESOLVE_AC_PROMPT_TEMPLATE_NAME).write_text(
        "Template content"
    )

    try:
        llm_task_resolve_ac.main_resolve_ac()
    finally:
        # Restaurar os valores originais para não afetar outros testes
        monkeypatch.setattr(task_core_config, "TEMPLATE_DIR", original_template_dir)
        monkeypatch.setattr(task_core_config, "PROJECT_ROOT", original_project_root)

    mock_get_common_parser.assert_called_once()
    mock_startup_api.assert_called_once()
    mock_load_template.assert_called_once_with(
        tmp_path / llm_task_resolve_ac.RESOLVE_AC_PROMPT_TEMPLATE_NAME,
        {"NUMERO_DA_ISSUE": "1", "NUMERO_DO_AC": "1", "OBSERVACAO_ADICIONAL": "obs"},
    )
    mock_prepare_context.assert_called_once()
    mock_execute_gemini.assert_called_once()
    mock_save_response.assert_called_once_with(
        llm_task_resolve_ac.TASK_NAME, mock_execute_gemini.return_value.strip()
    )
    mock_shutdown_api.assert_called_once()
