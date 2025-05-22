# tests/python/test_llm_core_utils.py
import pytest
import subprocess
from unittest.mock import patch, MagicMock
from pathlib import Path

from scripts.llm_core import utils as core_utils
from scripts.llm_core import config as core_config  # Para PROJECT_ROOT


@patch("shutil.which")
def test_command_exists(mock_which):
    mock_which.return_value = "/usr/bin/test_cmd"
    assert core_utils.command_exists("test_cmd") is True
    mock_which.assert_called_once_with("test_cmd")

    mock_which.return_value = None
    assert core_utils.command_exists("non_existent_cmd") is False


def test_suggest_install():
    # Teste básico, verifica se retorna uma string
    suggestion = core_utils.suggest_install("mycmd", "my-package")
    assert isinstance(suggestion, str)
    assert "AVISO: Comando 'mycmd' não encontrado." in suggestion
    assert "tente instalar o pacote 'my-package'" in suggestion

    # Teste sem pkg_name
    suggestion_no_pkg = core_utils.suggest_install("anothercmd")
    assert "tente instalar o pacote 'anothercmd'" in suggestion_no_pkg


@patch("subprocess.run")
def test_run_command_success(mock_subprocess_run):
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = "Success output"
    mock_process.stderr = ""
    mock_subprocess_run.return_value = mock_process

    cmd = ["echo", "hello"]
    # Usa core_config.PROJECT_ROOT para consistência, embora para 'echo' não seja crítico
    exit_code, stdout, stderr = core_utils.run_command(
        cmd, cwd=core_config.PROJECT_ROOT, check=True
    )

    assert exit_code == 0
    assert stdout == "Success output"
    assert stderr == ""
    mock_subprocess_run.assert_called_once()

    args_call, kwargs_call = mock_subprocess_run.call_args
    assert args_call[0] == cmd
    assert kwargs_call.get("cwd") == core_config.PROJECT_ROOT


@patch("subprocess.run")
def test_run_command_failure_check_true(mock_subprocess_run):
    # mock_process = MagicMock(spec=subprocess.CompletedProcess) # spec não é estritamente necessário aqui
    # mock_process.returncode = 1
    # mock_process.stdout = ""
    # mock_process.stderr = "Error output"

    # Simula o comportamento de check=True, onde CalledProcessError seria levantada
    # e run_command a capturaria e retornaria os detalhes.
    mock_subprocess_run.side_effect = subprocess.CalledProcessError(
        returncode=1,
        cmd=["failing_cmd"],
        output="",
        stderr="Error output from CalledProcessError",
    )

    cmd = ["failing_cmd"]
    exit_code, stdout, stderr = core_utils.run_command(cmd, check=True)

    assert exit_code == 1
    assert stdout == ""
    assert stderr == "Error output from CalledProcessError"


@patch("subprocess.run")
def test_run_command_failure_check_false(mock_subprocess_run):
    mock_process = MagicMock()
    mock_process.returncode = 1
    mock_process.stdout = "Some output despite error"
    mock_process.stderr = "Error occurred"
    mock_subprocess_run.return_value = mock_process

    cmd = ["cmd_that_fails"]
    exit_code, stdout, stderr = core_utils.run_command(cmd, check=False)

    assert exit_code == 1
    assert stdout == "Some output despite error"
    assert stderr == "Error occurred"


@patch("subprocess.run", side_effect=FileNotFoundError("Mock: Comando não existe"))
def test_run_command_file_not_found(mock_subprocess_run):
    cmd = ["non_existent_cmd"]
    exit_code, stdout, stderr = core_utils.run_command(cmd)

    assert exit_code == 1
    assert stdout == ""
    # Correção: Verifica a mensagem de erro em português gerada pela função
    assert "Comando não encontrado: non_existent_cmd" in stderr


@patch(
    "subprocess.run",
    side_effect=subprocess.TimeoutExpired(cmd="timeout_cmd", timeout=10),
)
def test_run_command_timeout(mock_subprocess_run):
    cmd = ["timeout_cmd"]
    exit_code, stdout, stderr = core_utils.run_command(cmd, timeout=10)

    assert exit_code == 1
    assert stdout == ""
    # Correção: Verifica a mensagem de erro em português gerada pela função
    assert "Comando excedeu o tempo limite de 10 segundos: timeout_cmd" in stderr
