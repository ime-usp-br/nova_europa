# tests/python/tasks/test_llm_task_update_doc.py
import pytest
import argparse
from unittest.mock import patch, MagicMock, call

import sys
from pathlib import Path

_project_root_dir_for_task_test = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root_dir_for_task_test) not in sys.path:
    sys.path.insert(0, str(_project_root_dir_for_task_test))

from scripts.tasks import llm_task_update_doc
from scripts.llm_core import config as task_core_config


def test_add_task_specific_args():
    """Testa se os argumentos específicos da tarefa 'update-doc' são adicionados ao parser."""
    parser = argparse.ArgumentParser()
    llm_task_update_doc.add_task_specific_args(parser)

    action_dests = [action.dest for action in parser._actions]
    assert "issue" in action_dests
    assert "doc_file" in action_dests

    # Verifica se --issue é obrigatório
    with pytest.raises(SystemExit):
        parser.parse_args(["--doc-file", "README.md"])  # Falta --issue

    # Verifica se --doc-file é opcional (default None)
    args_no_doc = parser.parse_args(["--issue", "123"])
    assert args_no_doc.issue == "123"
    assert args_no_doc.doc_file is None

    args_with_doc = parser.parse_args(["--issue", "456", "-d", "docs/guide.md"])
    assert args_with_doc.issue == "456"
    assert args_with_doc.doc_file == "docs/guide.md"


@patch("scripts.tasks.llm_task_update_doc.core_args_module.get_common_arg_parser")
@patch("scripts.tasks.llm_task_update_doc.api_client.startup_api_resources")
@patch("scripts.tasks.llm_task_update_doc.api_client.execute_gemini_call")
@patch("scripts.tasks.llm_task_update_doc.core_context.prepare_context_parts")
@patch("scripts.tasks.llm_task_update_doc.core_prompts_module.load_and_fill_template")
@patch("scripts.tasks.llm_task_update_doc.io_utils.save_llm_response")
@patch("scripts.tasks.llm_task_update_doc.io_utils.confirm_step")
@patch("scripts.tasks.llm_task_update_doc.api_client.shutdown_api_resources")
@patch(
    "scripts.tasks.llm_task_update_doc.io_utils.find_documentation_files"
)  # Mock da nova função
@patch(
    "scripts.tasks.llm_task_update_doc.io_utils.prompt_user_to_select_doc"
)  # Mock da nova função
def test_main_update_doc_direct_flow_with_doc_file_arg(
    mock_prompt_select_doc,  # Mock para seleção interativa
    mock_find_docs,  # Mock para encontrar docs
    mock_shutdown_api,
    mock_confirm_step,
    mock_save_response,
    mock_load_template,
    mock_prepare_context,
    mock_execute_gemini,
    mock_startup_api,
    mock_get_common_parser,
    tmp_path: Path,  # Usado para simular PROJECT_ROOT
    monkeypatch,
):
    """Testa o fluxo principal da tarefa update-doc (direto, com --doc-file fornecido)."""
    mock_parser_instance = MagicMock()
    mock_get_common_parser.return_value = mock_parser_instance

    doc_file_relative_path = "README.md"
    doc_file_absolute_path = tmp_path / doc_file_relative_path
    doc_file_absolute_path.write_text("Old readme content.")  # Cria o arquivo mock

    args = argparse.Namespace(
        task=llm_task_update_doc.TASK_NAME,
        issue="101",
        ac=None,
        doc_file=doc_file_relative_path,  # --doc-file fornecido
        observation="Update based on new feature.",
        two_stage=False,  # Fluxo direto
        verbose=False,
        web_search=False,
        generate_context=False,
        select_context=False,
        exclude_context=[],
        only_meta=False,
        only_prompt=False,
        yes=True,
        target_branch=None,
        draft=False,
        manifest_path=None,
        force_summary=None,
        max_files_per_call=10,
    )
    mock_parser_instance.parse_args.return_value = args

    mock_startup_api.return_value = True
    mock_load_template.return_value = (
        "Template preenchido para __NUMERO_DA_ISSUE__ doc __ARQUIVO_DOC_ALVO__."
    )
    mock_prepare_context.return_value = [
        MagicMock(spec=Path)
    ]  # Simula partes de contexto
    mock_execute_gemini.return_value = "--- START OF FILE README.md ---\nNew readme content.\n--- END OF FILE README.md ---"
    mock_confirm_step.return_value = ("y", None)  # Auto-confirma o salvamento

    # Monkeypatch as constantes de diretório
    original_template_dir = task_core_config.TEMPLATE_DIR
    original_project_root = task_core_config.PROJECT_ROOT

    # Define o diretório de templates mockado
    mocked_template_dir = tmp_path / "templates" / "prompts"
    mocked_template_dir.mkdir(parents=True, exist_ok=True)
    (mocked_template_dir / llm_task_update_doc.PROMPT_TEMPLATE_NAME).write_text(
        "Template content for update doc"
    )

    monkeypatch.setattr(task_core_config, "TEMPLATE_DIR", mocked_template_dir)
    monkeypatch.setattr(task_core_config, "PROJECT_ROOT", tmp_path)

    try:
        llm_task_update_doc.main_update_doc()
    finally:
        monkeypatch.setattr(task_core_config, "TEMPLATE_DIR", original_template_dir)
        monkeypatch.setattr(task_core_config, "PROJECT_ROOT", original_project_root)

    mock_get_common_parser.assert_called_once()
    mock_startup_api.assert_called_once()
    mock_find_docs.assert_not_called()
    mock_prompt_select_doc.assert_not_called()

    mock_load_template.assert_called_once_with(
        mocked_template_dir / llm_task_update_doc.PROMPT_TEMPLATE_NAME,
        {
            "NUMERO_DA_ISSUE": "101",
            "ARQUIVO_DOC_ALVO": doc_file_relative_path,
            "OBSERVACAO_ADICIONAL": "Update based on new feature.",
        },
    )
    mock_prepare_context.assert_called_once()
    mock_execute_gemini.assert_called_once()
    assert (
        mock_execute_gemini.call_args[0][0]
        == task_core_config.GEMINI_MODEL_GENERAL_TASKS
    )
    mock_save_response.assert_called_once_with(
        llm_task_update_doc.TASK_NAME, mock_execute_gemini.return_value.strip()
    )
    mock_shutdown_api.assert_called_once()


@patch(
    "scripts.tasks.llm_task_update_doc.io_utils.find_documentation_files",
    return_value=[],
)
@patch("scripts.tasks.llm_task_update_doc.core_args_module.get_common_arg_parser")
@patch("scripts.tasks.llm_task_update_doc.api_client.startup_api_resources")
def test_main_update_doc_no_doc_files_found(
    mock_startup_api: MagicMock,
    mock_get_common_parser: MagicMock,
    mock_find_docs: MagicMock,
    tmp_path: Path,
    monkeypatch,
    capsys,
):
    """Testa o comportamento quando nenhum arquivo de documentação é encontrado e --doc-file não é fornecido."""
    mock_parser_instance = MagicMock()
    mock_get_common_parser.return_value = mock_parser_instance
    args_no_doc_file_no_found = argparse.Namespace(
        task=llm_task_update_doc.TASK_NAME,
        issue="303",
        ac=None,
        doc_file=None,
        observation="",
        two_stage=False,
        verbose=False,
        web_search=False,
        generate_context=False,
        select_context=False,
        exclude_context=[],
        only_meta=False,
        only_prompt=False,
        yes=True,
        target_branch=None,
        draft=False,
        manifest_path=None,
        force_summary=None,
        max_files_per_call=10,
    )
    mock_parser_instance.parse_args.return_value = args_no_doc_file_no_found
    mock_startup_api.return_value = True

    original_project_root = task_core_config.PROJECT_ROOT
    monkeypatch.setattr(task_core_config, "PROJECT_ROOT", tmp_path)

    with pytest.raises(SystemExit) as excinfo:
        llm_task_update_doc.main_update_doc()

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert (
        "Erro: Nenhum arquivo de documentação (.md na raiz ou em docs/) encontrado."
        in captured.err
    )

    monkeypatch.setattr(task_core_config, "PROJECT_ROOT", original_project_root)


@patch("scripts.tasks.llm_task_update_doc.io_utils.find_documentation_files")
@patch(
    "scripts.tasks.llm_task_update_doc.io_utils.prompt_user_to_select_doc",
    return_value=None,
)
@patch("scripts.tasks.llm_task_update_doc.core_args_module.get_common_arg_parser")
@patch("scripts.tasks.llm_task_update_doc.api_client.startup_api_resources")
def test_main_update_doc_user_quits_selection(
    mock_startup_api: MagicMock,
    mock_get_common_parser: MagicMock,
    mock_prompt_select_doc: MagicMock,
    mock_find_docs: MagicMock,
    tmp_path: Path,
    monkeypatch,
    capsys,
):
    """Testa o comportamento quando o usuário desiste da seleção interativa de arquivo."""
    mock_parser_instance = MagicMock()
    mock_get_common_parser.return_value = mock_parser_instance
    args_user_quits = argparse.Namespace(
        task=llm_task_update_doc.TASK_NAME,
        issue="404",
        ac=None,
        doc_file=None,
        observation="",
        two_stage=False,
        verbose=False,
        web_search=False,
        generate_context=False,
        select_context=False,
        exclude_context=[],
        only_meta=False,
        only_prompt=False,
        yes=True,
        target_branch=None,
        draft=False,
        manifest_path=None,
        force_summary=None,
        max_files_per_call=10,
    )
    mock_parser_instance.parse_args.return_value = args_user_quits
    mock_startup_api.return_value = True
    mock_find_docs.return_value = [Path("README.md")]

    original_project_root = task_core_config.PROJECT_ROOT
    monkeypatch.setattr(task_core_config, "PROJECT_ROOT", tmp_path)

    with pytest.raises(SystemExit) as excinfo:
        llm_task_update_doc.main_update_doc()

    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert (
        "Seleção de arquivo de documentação cancelada pelo usuário. Saindo."
        in captured.out
    )

    monkeypatch.setattr(task_core_config, "PROJECT_ROOT", original_project_root)
