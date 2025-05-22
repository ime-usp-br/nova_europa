# tests/python/tasks/test_llm_task_commit_mesage.py
import pytest
import argparse
from unittest.mock import patch, MagicMock

# Adiciona o diretório raiz do projeto ao sys.path para importações corretas
import sys
from pathlib import Path

_project_root_dir_for_task_test = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root_dir_for_task_test) not in sys.path:
    sys.path.insert(0, str(_project_root_dir_for_task_test))

from scripts.tasks import llm_task_commit_mesage
from scripts.llm_core import config as task_core_config
from scripts.llm_core import config as core_config_test_scope  # Para restaurar depois


def test_add_task_specific_args():
    """Testa se os argumentos específicos da tarefa 'commit-mesage' são adicionados ao parser."""
    parser = argparse.ArgumentParser()
    llm_task_commit_mesage.add_task_specific_args(parser)

    action_dests = [action.dest for action in parser._actions]
    assert "issue" in action_dests

    # Verifica se --issue é opcional (não deve dar SystemExit por falta dele)
    try:
        args_only_issue = parser.parse_args(["--issue", "123"])
        assert args_only_issue.issue == "123"
        args_no_issue = parser.parse_args([])
        assert args_no_issue.issue is None  # Default é None
    except SystemExit as e:
        pytest.fail(
            f"Argumentos específicos da tarefa não foram corretamente definidos como opcionais. Erro: {e}"
        )


@patch("scripts.tasks.llm_task_commit_mesage.core_args_module.get_common_arg_parser")
@patch("scripts.tasks.llm_task_commit_mesage.api_client.startup_api_resources")
@patch("scripts.tasks.llm_task_commit_mesage.api_client.execute_gemini_call")
@patch("scripts.tasks.llm_task_commit_mesage.core_context.prepare_context_parts")
@patch(
    "scripts.tasks.llm_task_commit_mesage.core_prompts_module.load_and_fill_template"
)
@patch("scripts.tasks.llm_task_commit_mesage.io_utils.save_llm_response")
@patch("scripts.tasks.llm_task_commit_mesage.io_utils.confirm_step")
@patch("scripts.tasks.llm_task_commit_mesage.api_client.shutdown_api_resources")
def test_main_commit_mesage_direct_flow_success(
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
    """Testa o fluxo principal da tarefa commit-mesage (direto, com sucesso)."""
    mock_parser_instance = MagicMock()
    mock_get_common_parser.return_value = mock_parser_instance

    args = argparse.Namespace(
        task=llm_task_commit_mesage.TASK_NAME,  # Adicionado para simular a chamada via dispatcher
        issue="789",  # Testando com issue opcional
        ac=None,  # commit-mesage não usa AC
        observation="Test commit message observation",
        two_stage=False,  # Fluxo direto
        verbose=False,
        web_search=False,
        generate_context=False,
        select_context=False,
        exclude_context=[],
        only_meta=False,
        only_prompt=False,
        yes=True,  # Auto-confirma intermediate steps
        doc_file=None,  # Não usado por commit-mesage
        target_branch=None,  # Não usado por commit-mesage
        draft=False,  # Não usado por commit-mesage
        manifest_path=None,  # Não usado por commit-mesage
        force_summary=None,  # Não usado por commit-mesage
        max_files_per_call=10,  # Não usado diretamente por commit-mesage
    )
    mock_parser_instance.parse_args.return_value = args

    mock_startup_api.return_value = True
    mock_load_template.return_value = (
        "Template de commit preenchido para issue __NUMERO_DA_ISSUE__"
    )
    mock_prepare_context.return_value = [MagicMock(spec=Path)]
    mock_execute_gemini.return_value = "feat(test): Mensagem de commit gerada"
    mock_confirm_step.return_value = ("y", None)

    original_template_dir = task_core_config.TEMPLATE_DIR
    original_project_root = task_core_config.PROJECT_ROOT
    monkeypatch.setattr(task_core_config, "TEMPLATE_DIR", tmp_path)
    monkeypatch.setattr(task_core_config, "PROJECT_ROOT", tmp_path)

    (tmp_path / llm_task_commit_mesage.PROMPT_TEMPLATE_NAME).write_text(
        "Template content for commit"
    )

    try:
        llm_task_commit_mesage.main_commit_mesage()
    finally:
        monkeypatch.setattr(task_core_config, "TEMPLATE_DIR", original_template_dir)
        monkeypatch.setattr(task_core_config, "PROJECT_ROOT", original_project_root)

    mock_get_common_parser.assert_called_once()
    mock_startup_api.assert_called_once()
    mock_load_template.assert_called_once_with(
        tmp_path / llm_task_commit_mesage.PROMPT_TEMPLATE_NAME,
        {
            "NUMERO_DA_ISSUE": "789",
            "OBSERVACAO_ADICIONAL": "Test commit message observation",
        },
    )
    mock_prepare_context.assert_called_once()
    mock_execute_gemini.assert_called_once()
    # Verifica se o modelo correto foi usado (deve ser GENERAL_TASKS para commit-mesage)
    assert (
        mock_execute_gemini.call_args[0][0]
        == task_core_config.GEMINI_MODEL_GENERAL_TASKS
    )
    mock_save_response.assert_called_once_with(
        llm_task_commit_mesage.TASK_NAME, mock_execute_gemini.return_value.strip()
    )
    mock_shutdown_api.assert_called_once()


# Poderiam ser adicionados mais testes para:
# - Fluxo de duas etapas (--two-stage)
# - --only-meta, --only-prompt
# - Erros na API
# - Interação do usuário (não usar --yes)
# - Geração de contexto
# - Seleção de contexto
# - etc.
