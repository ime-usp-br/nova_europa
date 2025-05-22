# tests/python/tasks/test_llm_task_create_test_sub_issue.py
import pytest
import argparse
from unittest.mock import patch, MagicMock

# Adiciona o diretório raiz do projeto ao sys.path para importações corretas
import sys
from pathlib import Path

_project_root_dir_for_task_test = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root_dir_for_task_test) not in sys.path:
    sys.path.insert(0, str(_project_root_dir_for_task_test))

from scripts.tasks import llm_task_create_test_sub_issue
from scripts.llm_core import config as task_core_config


def test_add_task_specific_args():
    """Testa se os argumentos específicos da tarefa 'create-test-sub-issue' são adicionados ao parser."""
    parser = argparse.ArgumentParser()
    llm_task_create_test_sub_issue.add_task_specific_args(parser)

    action_dests = [action.dest for action in parser._actions]
    assert "issue" in action_dests  # --issue é obrigatório
    assert "ac" in action_dests  # --ac é opcional

    # Verifica se --issue é obrigatório
    with pytest.raises(SystemExit):
        parser.parse_args(["--ac", "1"])  # Falta --issue

    # Verifica defaults e se funciona com --issue
    try:
        args_minimal = parser.parse_args(["--issue", "123"])
        assert args_minimal.issue == "123"
        assert args_minimal.ac == ""  # Default para string vazia

        args_full = parser.parse_args(["--issue", "456", "--ac", "3"])
        assert args_full.issue == "456"
        assert args_full.ac == "3"
    except SystemExit as e:
        pytest.fail(
            f"Argumentos específicos da tarefa não foram corretamente definidos. Erro: {e}"
        )


@patch(
    "scripts.tasks.llm_task_create_test_sub_issue.core_args_module.get_common_arg_parser"
)
@patch("scripts.tasks.llm_task_create_test_sub_issue.api_client.startup_api_resources")
@patch("scripts.tasks.llm_task_create_test_sub_issue.api_client.execute_gemini_call")
@patch(
    "scripts.tasks.llm_task_create_test_sub_issue.core_context.prepare_context_parts"
)
@patch(
    "scripts.tasks.llm_task_create_test_sub_issue.core_prompts_module.load_and_fill_template"
)
@patch("scripts.tasks.llm_task_create_test_sub_issue.io_utils.save_llm_response")
@patch("scripts.tasks.llm_task_create_test_sub_issue.io_utils.confirm_step")
@patch("scripts.tasks.llm_task_create_test_sub_issue.api_client.shutdown_api_resources")
def test_main_create_test_sub_issue_direct_flow_success(
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
    """Testa o fluxo principal da tarefa create-test-sub-issue (direto, com sucesso)."""
    mock_parser_instance = MagicMock()
    mock_get_common_parser.return_value = mock_parser_instance

    args = argparse.Namespace(
        task=llm_task_create_test_sub_issue.TASK_NAME,
        issue="789",
        ac="10",
        observation="Generate test sub-issue for this AC.",
        two_stage=False,
        verbose=False,
        web_search=False,
        generate_context=False,
        select_context=False,
        exclude_context=[],
        only_meta=False,
        only_prompt=False,
        yes=True,  # Auto-confirma intermediate steps
        doc_file=None,
        target_branch=None,
        draft=False,
        manifest_path=None,
        force_summary=None,
        max_files_per_call=10,
    )
    mock_parser_instance.parse_args.return_value = args

    mock_startup_api.return_value = True
    mock_load_template.return_value = "Template para sub-issue de teste da issue __PARENT_ISSUE_NUMBER__ AC __PARENT_AC_NUMBER__."
    mock_prepare_context.return_value = [MagicMock(spec=Path)]
    mock_execute_gemini.return_value = (
        "TITLE: Test Sub-Issue Content\nTYPE: test\n..."  # Conteúdo simulado da issue
    )
    mock_confirm_step.return_value = ("y", None)

    original_template_dir = task_core_config.TEMPLATE_DIR
    original_meta_prompt_dir = task_core_config.META_PROMPT_DIR
    original_project_root = task_core_config.PROJECT_ROOT

    monkeypatch.setattr(task_core_config, "TEMPLATE_DIR", tmp_path)
    monkeypatch.setattr(
        task_core_config, "META_PROMPT_DIR", tmp_path
    )  # Também para o caso de --two-stage
    monkeypatch.setattr(task_core_config, "PROJECT_ROOT", tmp_path)

    (tmp_path / llm_task_create_test_sub_issue.PROMPT_TEMPLATE_NAME).write_text(
        "Template content for test sub-issue"
    )

    try:
        llm_task_create_test_sub_issue.main_create_test_sub_issue()
    finally:
        monkeypatch.setattr(task_core_config, "TEMPLATE_DIR", original_template_dir)
        monkeypatch.setattr(
            task_core_config, "META_PROMPT_DIR", original_meta_prompt_dir
        )
        monkeypatch.setattr(task_core_config, "PROJECT_ROOT", original_project_root)

    mock_get_common_parser.assert_called_once()
    mock_startup_api.assert_called_once()
    mock_load_template.assert_called_once_with(
        tmp_path / llm_task_create_test_sub_issue.PROMPT_TEMPLATE_NAME,
        {
            "PARENT_ISSUE_NUMBER": "789",
            "PARENT_AC_NUMBER": "10",
            "OBSERVACAO_ADICIONAL": "Generate test sub-issue for this AC.",
        },
    )
    mock_prepare_context.assert_called_once()
    mock_execute_gemini.assert_called_once()
    # O modelo usado para esta task é GENERAL_TASKS
    assert (
        mock_execute_gemini.call_args[0][0]
        == task_core_config.GEMINI_MODEL_GENERAL_TASKS
    )
    mock_save_response.assert_called_once_with(
        llm_task_create_test_sub_issue.TASK_NAME,
        mock_execute_gemini.return_value.strip(),
    )
    mock_shutdown_api.assert_called_once()


# Poderiam ser adicionados mais testes para:
# - Fluxo de duas etapas (--two-stage)
# - Argumento --ac opcional (string vazia)
# - --only-meta, --only-prompt
# - Erros na API
# - Interação do usuário (não usar --yes)
# - Geração de contexto
# - Seleção de contexto
