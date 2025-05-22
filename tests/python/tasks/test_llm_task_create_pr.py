# tests/python/tasks/test_llm_task_create_pr.py
import pytest
import argparse
from unittest.mock import patch, MagicMock, call

# Adiciona o diretório raiz do projeto ao sys.path para importações corretas
import sys
from pathlib import Path

_project_root_dir_for_task_test = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root_dir_for_task_test) not in sys.path:
    sys.path.insert(0, str(_project_root_dir_for_task_test))

from scripts.tasks import llm_task_create_pr
from scripts.llm_core import (
    config as task_core_config,
)  # task_core_config é o alias usado no script
from scripts.llm_core import utils as core_utils  # Para mockar run_command


def test_add_task_specific_args():
    """Testa se os argumentos específicos da tarefa 'create-pr' são adicionados ao parser."""
    parser = argparse.ArgumentParser()
    llm_task_create_pr.add_task_specific_args(parser)

    action_dests = [action.dest for action in parser._actions]
    assert "issue" in action_dests
    assert "target_branch" in action_dests
    assert "draft" in action_dests

    # Verifica se --issue é obrigatório
    with pytest.raises(SystemExit):
        parser.parse_args(["--target-branch", "develop"])  # Falta --issue

    # Verifica defaults
    args_minimal = parser.parse_args(["--issue", "123"])
    assert args_minimal.issue == "123"
    assert args_minimal.target_branch == task_core_config.DEFAULT_TARGET_BRANCH
    assert args_minimal.draft is False

    args_full = parser.parse_args(["--issue", "456", "-b", "feature-branch", "--draft"])
    assert args_full.issue == "456"
    assert args_full.target_branch == "feature-branch"
    assert args_full.draft is True


@patch("scripts.tasks.llm_task_create_pr.core_utils.run_command")
def test_get_current_branch_success(mock_run_command):
    mock_run_command.return_value = (0, "feature/abc\n", "")
    branch = llm_task_create_pr.get_current_branch(verbose=True)
    assert branch == "feature/abc"
    mock_run_command.assert_called_once_with(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], check=False
    )


@patch("scripts.tasks.llm_task_create_pr.core_utils.run_command")
def test_get_current_branch_failure(mock_run_command):
    mock_run_command.return_value = (1, "", "git error")
    branch = llm_task_create_pr.get_current_branch(verbose=True)
    assert branch is None


@patch("scripts.tasks.llm_task_create_pr.core_utils.run_command")
def test_check_new_commits_found(mock_run_command):
    # Simula 'git fetch' e 'git show-ref' (opcional) sucedendo
    # Simula 'git rev-list --count' retornando > 0
    mock_run_command.side_effect = [
        (0, "", ""),  # git fetch
        (
            0,
            "refs/remotes/origin/main",
            "",
        ),  # git show-ref (base branch exists remotely)
        (0, "3\n", ""),  # git rev-list --count
    ]
    assert (
        llm_task_create_pr.check_new_commits("main", "feature/xyz", verbose=True)
        is True
    )
    assert mock_run_command.call_count == 3
    mock_run_command.assert_any_call(
        ["git", "fetch", "origin", "feature/xyz", "main"], check=False
    )
    mock_run_command.assert_any_call(
        ["git", "show-ref", "--verify", "refs/remotes/origin/main"], check=False
    )
    mock_run_command.assert_any_call(
        ["git", "rev-list", "--count", "origin/main..feature/xyz"], check=False
    )


@patch("scripts.tasks.llm_task_create_pr.core_utils.run_command")
def test_check_new_commits_not_found(mock_run_command):
    mock_run_command.side_effect = [
        (0, "", ""),  # git fetch
        (1, "", "not found"),  # git show-ref (base branch does NOT exist remotely)
        (0, "0\n", ""),  # git rev-list --count (0 commits)
    ]
    assert (
        llm_task_create_pr.check_new_commits("main", "feature/xyz", verbose=True)
        is False
    )


@patch(
    "scripts.tasks.llm_task_create_pr.core_utils.command_exists", return_value=True
)  # Assume gh exists
@patch("scripts.tasks.llm_task_create_pr.core_utils.run_command")
def test_create_github_pr_success(
    mock_run_command, mock_command_exists_true
):  # Renomeado para evitar conflito
    mock_run_command.return_value = (0, "https://github.com/owner/repo/pull/1", "")
    success = llm_task_create_pr.create_github_pr(
        "Test PR Title", "Test PR Body", "feature/xyz", "main", False, verbose=True
    )
    assert success is True
    mock_run_command.assert_called_once_with(
        [
            "gh",
            "pr",
            "create",
            "--title",
            "Test PR Title",
            "--body",
            "Test PR Body",
            "--head",
            "feature/xyz",
            "--base",
            "main",
        ],
        check=False,
    )


@patch(
    "scripts.tasks.llm_task_create_pr.core_utils.command_exists", return_value=True
)  # Assume gh exists
@patch("scripts.tasks.llm_task_create_pr.core_utils.run_command")
def test_create_github_pr_draft_success(
    mock_run_command, mock_command_exists_true
):  # Renomeado
    mock_run_command.return_value = (0, "https://github.com/owner/repo/pull/2", "")
    success = llm_task_create_pr.create_github_pr(
        "Draft PR", "Draft Body", "feature/draft", "develop", True, verbose=True
    )
    assert success is True
    mock_run_command.assert_called_once_with(
        [
            "gh",
            "pr",
            "create",
            "--title",
            "Draft PR",
            "--body",
            "Draft Body",
            "--head",
            "feature/draft",
            "--base",
            "develop",
            "--draft",
        ],
        check=False,
    )


@patch("scripts.tasks.llm_task_create_pr.core_utils.command_exists")
def test_create_github_pr_gh_not_found(
    mock_command_exists_param,
):  # Renomeado parâmetro
    def command_exists_side_effect(cmd):
        if cmd == "gh":
            return False
        # Para as chamadas dentro de suggest_install, podemos retornar True
        # ou mocká-las mais especificamente se necessário para o teste
        return True

    mock_command_exists_param.side_effect = command_exists_side_effect

    success = llm_task_create_pr.create_github_pr("Title", "Body", "h", "b", False)
    assert success is False

    # Verifica apenas a chamada para 'gh'
    assert mock_command_exists_param.call_args_list[0] == call("gh")


@patch("scripts.tasks.llm_task_create_pr.core_args_module.get_common_arg_parser")
@patch("scripts.tasks.llm_task_create_pr.api_client.startup_api_resources")
@patch("scripts.tasks.llm_task_create_pr.api_client.execute_gemini_call")
@patch("scripts.tasks.llm_task_create_pr.core_context.prepare_context_parts")
@patch("scripts.tasks.llm_task_create_pr.core_prompts_module.load_and_fill_template")
@patch("scripts.tasks.llm_task_create_pr.io_utils.confirm_step")
@patch("scripts.tasks.llm_task_create_pr.api_client.shutdown_api_resources")
@patch("scripts.tasks.llm_task_create_pr.get_current_branch")
@patch("scripts.tasks.llm_task_create_pr.check_new_commits")
@patch("scripts.tasks.llm_task_create_pr.create_github_pr")
@patch("scripts.tasks.llm_task_create_pr.io_utils.parse_pr_content")
def test_main_create_pr_direct_flow_success(
    mock_parse_pr_content,
    mock_create_gh_pr,
    mock_check_commits,
    mock_get_branch,
    mock_shutdown_api,
    mock_confirm_step,
    mock_load_template,
    mock_prepare_context,
    mock_execute_gemini,
    mock_startup_api,
    mock_get_common_parser,
    tmp_path,
    monkeypatch,
):
    """Testa o fluxo principal da tarefa create-pr (direto, com sucesso)."""
    mock_parser_instance = MagicMock()
    mock_get_common_parser.return_value = mock_parser_instance

    args = argparse.Namespace(
        task=llm_task_create_pr.TASK_NAME,
        issue="123",
        ac=None,
        observation="",
        two_stage=False,
        verbose=True,
        web_search=False,
        generate_context=False,
        select_context=False,
        exclude_context=[],
        only_meta=False,
        only_prompt=False,
        yes=False,  # Alterado para False para forçar ambas as confirmações
        doc_file=None,
        target_branch="main",
        draft=False,
        manifest_path=None,
        force_summary=None,
        max_files_per_call=10,
    )
    mock_parser_instance.parse_args.return_value = args

    mock_startup_api.return_value = True
    mock_load_template.return_value = "Template para PR da issue __NUMERO_DA_ISSUE__"
    mock_prepare_context.return_value = [MagicMock(spec=Path)]
    llm_response_pr = f"{task_core_config.PR_CONTENT_DELIMITER_TITLE}\nPR Gerado\n{task_core_config.PR_CONTENT_DELIMITER_BODY}\nCorpo do PR gerado.\n\nCloses #123"
    mock_execute_gemini.return_value = llm_response_pr
    mock_parse_pr_content.return_value = (
        "PR Gerado",
        "Corpo do PR gerado.\n\nCloses #123",
    )
    # CORREÇÃO: confirm_step é chamado para LLM response E para criar o PR
    mock_confirm_step.side_effect = [("y", None), ("y", None)]
    mock_get_branch.return_value = "feature/123-my-feature"
    mock_check_commits.return_value = True
    mock_create_gh_pr.return_value = True

    original_template_dir = task_core_config.TEMPLATE_DIR
    original_project_root = task_core_config.PROJECT_ROOT
    monkeypatch.setattr(task_core_config, "TEMPLATE_DIR", tmp_path)
    monkeypatch.setattr(task_core_config, "PROJECT_ROOT", tmp_path)
    (tmp_path / llm_task_create_pr.PROMPT_TEMPLATE_NAME).write_text("Template para PR")

    try:
        llm_task_create_pr.main_create_pr()
    finally:
        monkeypatch.setattr(task_core_config, "TEMPLATE_DIR", original_template_dir)
        monkeypatch.setattr(task_core_config, "PROJECT_ROOT", original_project_root)

    mock_get_common_parser.assert_called_once()
    mock_startup_api.assert_called_once()
    mock_load_template.assert_called_once()
    mock_prepare_context.assert_called_once()
    mock_execute_gemini.assert_called_once()
    mock_parse_pr_content.assert_called_once_with(llm_response_pr)
    mock_get_branch.assert_called_once()
    mock_check_commits.assert_called_once_with("main", "feature/123-my-feature", True)
    mock_create_gh_pr.assert_called_once_with(
        "PR Gerado",
        "Corpo do PR gerado.\n\nCloses #123",
        "feature/123-my-feature",
        "main",
        False,
        True,
    )
    assert mock_confirm_step.call_count == 2
    mock_shutdown_api.assert_called_once()
