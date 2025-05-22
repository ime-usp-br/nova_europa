import pytest
from pathlib import Path
import os
from unittest.mock import patch

# Adiciona o diretório raiz do projeto ao sys.path para importações corretas
import sys

_project_root_dir_for_test = Path(__file__).resolve().parent.parent.parent
if str(_project_root_dir_for_test) not in sys.path:
    sys.path.insert(0, str(_project_root_dir_for_test))

# Importa a função específica do módulo llm_interact
# Esta importação assume que `scripts` é um pacote reconhecível (devido ao pythonpath no pytest.ini)
from scripts.llm_interact import find_task_scripts

# Importa o módulo config para mockar PROJECT_ROOT se necessário,
# mas para find_task_scripts, o path é passado como argumento, então pode não ser necessário mockar aqui.
from scripts.llm_core import config as core_config_module


@pytest.fixture
def tasks_dir_structure(tmp_path: Path):
    """
    Cria uma estrutura de diretório 'tasks' simulada dentro de tmp_path.
    Retorna o caminho para este diretório 'tasks' simulado.
    """
    # Não precisamos mockar PROJECT_ROOT globalmente aqui, pois find_task_scripts
    # recebe o tasks_dir como argumento.
    tasks_dir = tmp_path / "tasks_test_dir"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    return tasks_dir


@patch("os.access")
def test_find_task_scripts_no_tasks(
    mock_os_access: patch, tasks_dir_structure: Path
):
    """Testa a descoberta quando não há scripts de tarefa."""
    mock_os_access.return_value = True  # Simula que todos os arquivos são executáveis
    assert find_task_scripts(tasks_dir_structure) == {}


@patch("os.access")
def test_find_task_scripts_one_valid_task(
    mock_os_access: patch, tasks_dir_structure: Path
):
    """Testa a descoberta de um script de tarefa válido."""
    mock_os_access.return_value = True
    task_file = tasks_dir_structure / "llm_task_sample_task.py"
    task_file.write_text("#!/usr/bin/env python3\nprint('hello')")
    # task_file.chmod(0o755) # Não necessário se os.access é mockado

    expected_task_name = "sample-task"
    result = find_task_scripts(tasks_dir_structure)

    assert len(result) == 1
    assert expected_task_name in result
    assert result[expected_task_name] == task_file


@patch("os.access")
def test_find_task_scripts_multiple_valid_tasks(
    mock_os_access: patch, tasks_dir_structure: Path
):
    """Testa a descoberta de múltiplos scripts de tarefa válidos."""
    mock_os_access.return_value = True
    task_file1 = tasks_dir_structure / "llm_task_first_one.py"
    task_file1.write_text("content1")
    # task_file1.chmod(0o755)

    task_file2 = tasks_dir_structure / "llm_task_another_example_task.py"
    task_file2.write_text("content2")
    # task_file2.chmod(0o755)

    result = find_task_scripts(tasks_dir_structure)
    assert len(result) == 2
    assert "first-one" in result
    assert result["first-one"] == task_file1
    assert "another-example-task" in result
    assert result["another-example-task"] == task_file2


@patch("os.access")
def test_find_task_scripts_ignores_non_py_files(
    mock_os_access: patch, tasks_dir_structure: Path
):
    """Testa se arquivos não-.py são ignorados."""
    mock_os_access.return_value = True
    task_file = tasks_dir_structure / "llm_task_valid.py"
    task_file.write_text("valid")
    # task_file.chmod(0o755)

    (tasks_dir_structure / "llm_task_invalid.txt").write_text("text file")
    (tasks_dir_structure / "another_file.sh").write_text("shell script")

    result = find_task_scripts(tasks_dir_structure)
    assert len(result) == 1
    assert "valid" in result


@patch("os.access")
def test_find_task_scripts_ignores_non_task_py_files(
    mock_os_access: patch, tasks_dir_structure: Path
):
    """Testa se arquivos .py que não seguem o padrão llm_task_*.py são ignorados."""
    mock_os_access.return_value = True
    (tasks_dir_structure / "llm_task_my_job.py").write_text("job")
    # (tasks_dir_structure / "llm_task_my_job.py").chmod(0o755)

    (tasks_dir_structure / "helper_script.py").write_text("helper")
    # (tasks_dir_structure / "helper_script.py").chmod(0o755)

    (tasks_dir_structure / "not_a_task_llm.py").write_text("wrong prefix")
    # (tasks_dir_structure / "not_a_task_llm.py").chmod(0o755)

    result = find_task_scripts(tasks_dir_structure)
    assert len(result) == 1
    assert "my-job" in result


@patch("os.access")
def test_find_task_scripts_ignores_directories_named_as_tasks(
    mock_os_access: patch, tasks_dir_structure: Path
):
    """Testa se diretórios com nomes de tarefa são ignorados."""
    mock_os_access.return_value = True  # Para arquivos que poderiam ser encontrados
    (tasks_dir_structure / "llm_task_a_real_task.py").write_text("real")
    # (tasks_dir_structure / "llm_task_a_real_task.py").chmod(0o755)

    dir_as_task = tasks_dir_structure / "llm_task_a_directory.py"
    dir_as_task.mkdir()  # Cria como diretório

    result = find_task_scripts(tasks_dir_structure)
    assert len(result) == 1
    assert "a-real-task" in result
    assert "a-directory" not in result  # Assegura que o diretório não foi pego


@patch("os.access")
def test_find_task_scripts_handles_underscores_in_name(
    mock_os_access: patch, tasks_dir_structure: Path
):
    """Testa se underscores no nome do arquivo são convertidos para hífens no nome da tarefa."""
    mock_os_access.return_value = True
    task_file = tasks_dir_structure / "llm_task_process_data_input.py"
    task_file.write_text("content")
    # task_file.chmod(0o755)

    result = find_task_scripts(tasks_dir_structure)
    assert "process-data-input" in result


@patch("os.access")
def test_find_task_scripts_file_not_executable(
    mock_os_access: patch, tasks_dir_structure: Path
):
    """Testa se um arquivo .py com nome correto mas sem permissão de execução é ignorado."""
    mock_os_access.return_value = False  # Simula que o arquivo não é executável
    task_file_no_exec = tasks_dir_structure / "llm_task_no_exec.py"
    task_file_no_exec.write_text("cannot run")

    mock_os_access.side_effect = lambda path, mode: mode == os.X_OK and str(
        path
    ) != str(task_file_no_exec)

    task_file_exec = tasks_dir_structure / "llm_task_can_exec.py"
    task_file_exec.write_text("can run")
    # task_file_exec.chmod(0o755) # A permissão real não importa devido ao mock

    result = find_task_scripts(tasks_dir_structure)
    assert len(result) == 1
    assert "can-exec" in result
    assert "no-exec" not in result


@patch("os.access", return_value=True)
def test_find_task_scripts_empty_task_name_after_replace(
    mock_os_access: patch, tasks_dir_structure: Path
):
    """Testa se um arquivo como 'llm_task_.py' (nome vazio após replace) é ignorado."""
    task_file = tasks_dir_structure / "llm_task_.py"
    task_file.write_text("content")

    result = find_task_scripts(tasks_dir_structure)
    assert not result  # Espera-se um dicionário vazio


@patch("os.access", return_value=True)
def test_find_task_scripts_tasks_dir_does_not_exist(
    mock_os_access: patch, tmp_path: Path
):
    """Testa o comportamento se o diretório de tarefas não existir."""
    non_existent_tasks_dir = tmp_path / "non_existent_tasks"
    result = find_task_scripts(non_existent_tasks_dir)
    assert result == {}