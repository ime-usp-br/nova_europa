import pytest
from pathlib import Path
import os
import sys
import argparse
from unittest.mock import patch, MagicMock, call

# Adiciona o diretório raiz do projeto ao sys.path para importações corretas
_project_root_dir_for_test = Path(__file__).resolve().parent.parent.parent
if str(_project_root_dir_for_test) not in sys.path:
    sys.path.insert(0, str(_project_root_dir_for_test))

# Importa as funções específicas e o main do módulo llm_interact
from scripts.llm_interact import find_task_scripts, main as llm_interact_main
from scripts.llm_core import config as core_config_module
from scripts.llm_core import args as core_args_module_for_main_mock


@pytest.fixture
def tasks_dir_structure(tmp_path: Path):
    """
    Cria uma estrutura de diretório 'tasks' simulada dentro de tmp_path.
    Retorna o caminho para este diretório 'tasks' simulado.
    """
    tasks_dir = tmp_path / "scripts" / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    return tasks_dir


@patch("os.access")
def test_find_task_scripts_no_tasks(
    mock_os_access: MagicMock, tasks_dir_structure: Path
):
    """Testa a descoberta quando não há scripts de tarefa."""
    mock_os_access.return_value = True
    assert find_task_scripts(tasks_dir_structure) == {}


@patch("os.access")
def test_find_task_scripts_one_valid_task(
    mock_os_access: MagicMock, tasks_dir_structure: Path
):
    """Testa a descoberta de um script de tarefa válido."""
    mock_os_access.return_value = True
    task_file = tasks_dir_structure / "llm_task_sample_task.py"
    task_file.write_text("#!/usr/bin/env python3\nprint('hello')")

    expected_task_name = "sample-task"
    result = find_task_scripts(tasks_dir_structure)

    assert len(result) == 1
    assert expected_task_name in result
    assert result[expected_task_name] == task_file


@patch("os.access")
def test_find_task_scripts_multiple_valid_tasks(
    mock_os_access: MagicMock, tasks_dir_structure: Path
):
    mock_os_access.return_value = True
    task_file1 = tasks_dir_structure / "llm_task_first_one.py"
    task_file1.write_text("content1")
    task_file2 = tasks_dir_structure / "llm_task_another_example_task.py"
    task_file2.write_text("content2")

    result = find_task_scripts(tasks_dir_structure)
    assert len(result) == 2
    assert "first-one" in result
    assert result["first-one"] == task_file1
    assert "another-example-task" in result
    assert result["another-example-task"] == task_file2


@patch("os.access")
def test_find_task_scripts_ignores_non_py_files(
    mock_os_access: MagicMock, tasks_dir_structure: Path
):
    mock_os_access.return_value = True
    task_file = tasks_dir_structure / "llm_task_valid.py"
    task_file.write_text("valid")
    (tasks_dir_structure / "llm_task_invalid.txt").write_text("text file")
    (tasks_dir_structure / "another_file.sh").write_text("shell script")

    result = find_task_scripts(tasks_dir_structure)
    assert len(result) == 1
    assert "valid" in result


@patch("os.access")
def test_find_task_scripts_ignores_non_task_py_files(
    mock_os_access: MagicMock, tasks_dir_structure: Path
):
    mock_os_access.return_value = True
    (tasks_dir_structure / "llm_task_my_job.py").write_text("job")
    (tasks_dir_structure / "helper_script.py").write_text("helper")
    (tasks_dir_structure / "not_a_task_llm.py").write_text("wrong prefix")

    result = find_task_scripts(tasks_dir_structure)
    assert len(result) == 1
    assert "my-job" in result


@patch("os.access")
def test_find_task_scripts_ignores_directories_named_as_tasks(
    mock_os_access: MagicMock, tasks_dir_structure: Path
):
    mock_os_access.return_value = True
    (tasks_dir_structure / "llm_task_a_real_task.py").write_text("real")
    dir_as_task = tasks_dir_structure / "llm_task_a_directory.py"
    dir_as_task.mkdir()

    result = find_task_scripts(tasks_dir_structure)
    assert len(result) == 1
    assert "a-real-task" in result
    assert "a-directory" not in result


@patch("os.access")
def test_find_task_scripts_handles_underscores_in_name(
    mock_os_access: MagicMock, tasks_dir_structure: Path
):
    mock_os_access.return_value = True
    task_file = tasks_dir_structure / "llm_task_process_data_input.py"
    task_file.write_text("content")

    result = find_task_scripts(tasks_dir_structure)
    assert "process-data-input" in result


@patch("os.access")
def test_find_task_scripts_file_not_executable(
    mock_os_access: MagicMock, tasks_dir_structure: Path
):
    task_file_no_exec = tasks_dir_structure / "llm_task_no_exec.py"
    task_file_no_exec.write_text("cannot run")
    task_file_exec = tasks_dir_structure / "llm_task_can_exec.py"
    task_file_exec.write_text("can run")

    def os_access_side_effect(path, mode):
        if path == task_file_no_exec and mode == os.X_OK:
            return False
        if path == task_file_exec and mode == os.X_OK:
            return True
        return os.path.exists(path)

    mock_os_access.side_effect = os_access_side_effect

    result = find_task_scripts(tasks_dir_structure)
    assert len(result) == 1
    assert "can-exec" in result
    assert "no-exec" not in result


@patch("os.access", return_value=True)
def test_find_task_scripts_empty_task_name_after_replace(
    mock_os_access: MagicMock, tasks_dir_structure: Path
):
    task_file = tasks_dir_structure / "llm_task_.py"
    task_file.write_text("content")
    result = find_task_scripts(tasks_dir_structure)
    assert not result


@patch("os.access", return_value=True)
def test_find_task_scripts_tasks_dir_does_not_exist(
    mock_os_access: MagicMock, tmp_path: Path
):
    non_existent_tasks_dir = tmp_path / "non_existent_tasks"
    result = find_task_scripts(non_existent_tasks_dir)
    assert result == {}


# --- Testes para AC4: Seleção Interativa de Tarefas ---
@patch("scripts.llm_interact.find_task_scripts")
@patch("scripts.llm_interact.core_args_module.get_common_arg_parser")
@patch("scripts.llm_interact.subprocess.run")
@patch("scripts.llm_interact.sys.exit")
@patch("builtins.input")
def test_interactive_task_selection_valid_numeric_choice(
    mock_input: MagicMock,
    mock_sys_exit: MagicMock,
    mock_subprocess_run: MagicMock,
    mock_get_common_parser: MagicMock,
    mock_find_tasks: MagicMock,
    monkeypatch,
    capsys,
):
    mock_find_tasks.return_value = {
        "task-alpha": Path("scripts/tasks/llm_task_task_alpha.py"),
        "task-beta": Path("scripts/tasks/llm_task_task_beta.py"),
    }
    mock_input.return_value = "2"
    mock_common_parser_instance = argparse.ArgumentParser()
    mock_get_common_parser.return_value = mock_common_parser_instance
    monkeypatch.setattr(sys, "argv", ["scripts/llm_interact.py"])
    mock_subprocess_run.return_value = MagicMock(returncode=0)
    mock_sys_exit.side_effect = lambda code=0: (_ for _ in ()).throw(SystemExit(code))

    with pytest.raises(SystemExit) as excinfo:
        llm_interact_main()

    assert excinfo.value.code == 0
    mock_find_tasks.assert_called_once()
    mock_input.assert_called_once_with("Selecione o número da tarefa: ")
    mock_subprocess_run.assert_called_once()
    called_script_path = str(mock_subprocess_run.call_args[0][0][1])
    assert "llm_task_task_beta.py" in called_script_path


@patch("scripts.llm_interact.find_task_scripts")
@patch("scripts.llm_interact.core_args_module.get_common_arg_parser")
@patch("scripts.llm_interact.subprocess.run")
@patch("scripts.llm_interact.sys.exit")
@patch("builtins.input")
def test_interactive_task_selection_invalid_then_valid_choice(
    mock_input: MagicMock,
    mock_sys_exit: MagicMock,
    mock_subprocess_run: MagicMock,
    mock_get_common_parser: MagicMock,
    mock_find_tasks: MagicMock,
    monkeypatch,
    capsys,
):
    mock_find_tasks.return_value = {
        "task-one": Path("scripts/tasks/llm_task_task_one.py")
    }
    mock_input.side_effect = ["invalid_text", "1"]
    mock_common_parser_instance = argparse.ArgumentParser()
    mock_get_common_parser.return_value = mock_common_parser_instance
    monkeypatch.setattr(sys, "argv", ["scripts/llm_interact.py"])
    mock_sys_exit.side_effect = lambda code=0: (_ for _ in ()).throw(SystemExit(code))

    with pytest.raises(SystemExit) as excinfo_main:
        llm_interact_main()

    assert (
        excinfo_main.value.code == 1
    )  # Espera-se que saia com 1 devido à entrada inválida
    assert mock_input.call_count == 1  # Só a primeira chamada a input() acontece
    captured_output = capsys.readouterr().out
    assert "Entrada inválida." in captured_output
    mock_subprocess_run.assert_not_called()


@patch("scripts.llm_interact.find_task_scripts")
@patch("scripts.llm_interact.core_args_module.get_common_arg_parser")
@patch("scripts.llm_interact.subprocess.run")
@patch("scripts.llm_interact.sys.exit")
@patch("builtins.input")
def test_interactive_task_selection_out_of_range_choice(
    mock_input: MagicMock,
    mock_sys_exit: MagicMock,
    mock_subprocess_run: MagicMock,
    mock_get_common_parser: MagicMock,
    mock_find_tasks: MagicMock,
    monkeypatch,
    capsys,
):
    mock_find_tasks.return_value = {
        "task-gamma": Path("scripts/tasks/llm_task_task_gamma.py")
    }
    mock_input.return_value = "5"
    mock_common_parser_instance = argparse.ArgumentParser()
    mock_get_common_parser.return_value = mock_common_parser_instance
    monkeypatch.setattr(sys, "argv", ["scripts/llm_interact.py"])
    mock_sys_exit.side_effect = lambda code=0: (_ for _ in ()).throw(SystemExit(code))

    with pytest.raises(SystemExit) as excinfo_main:
        llm_interact_main()

    assert excinfo_main.value.code == 1
    mock_input.assert_called_once()
    captured_output = capsys.readouterr().out
    assert "Seleção inválida." in captured_output
    mock_subprocess_run.assert_not_called()


@patch("scripts.llm_interact.find_task_scripts")
@patch("scripts.llm_interact.core_args_module.get_common_arg_parser")
@patch("scripts.llm_interact.subprocess.run")
@patch("scripts.llm_interact.sys.exit")
@patch("builtins.input")
def test_interactive_task_selection_no_tasks_available_exits(
    mock_input: MagicMock,
    mock_sys_exit: MagicMock,
    mock_subprocess_run: MagicMock,
    mock_get_common_parser: MagicMock,
    mock_find_tasks: MagicMock,
    monkeypatch,
    capsys,
):
    mock_find_tasks.return_value = {}
    mock_common_parser_instance = argparse.ArgumentParser()
    mock_get_common_parser.return_value = mock_common_parser_instance
    monkeypatch.setattr(sys, "argv", ["scripts/llm_interact.py"])
    mock_sys_exit.side_effect = lambda code=0: (_ for _ in ()).throw(SystemExit(code))

    with pytest.raises(SystemExit) as excinfo_main:
        llm_interact_main()

    assert excinfo_main.value.code == 1
    captured_output = capsys.readouterr().err
    assert (
        "Erro: Nenhuma tarefa LLM (scripts/tasks/llm_task_*.py) encontrada ou executável."
        in captured_output
    )
    mock_input.assert_not_called()
    mock_subprocess_run.assert_not_called()
