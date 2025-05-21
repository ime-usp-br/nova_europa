# -*- coding: utf-8 -*-
"""
LLM Core General Utilities Module.
"""
import shutil
import subprocess
import sys
import time
import traceback
import shlex
from pathlib import Path
from typing import List, Optional, Tuple

from . import config as core_config


def find_command(primary: str, fallback: str) -> Optional[str]:
    """Finds an executable command, trying primary then fallback."""
    if shutil.which(primary):
        return primary
    if shutil.which(fallback):
        return fallback
    return None


PYTHON_CMD = find_command("python3", "python")
PIP_CMD = find_command("pip3", "pip")


def command_exists(cmd: str) -> bool:
    """Checks if a command exists on the system."""
    return shutil.which(cmd) is not None


def suggest_install(cmd_name: str, pkg_name: Optional[str] = None) -> str:
    """Generates installation suggestion message."""
    pkg = pkg_name or cmd_name
    suggestions = [f"AVISO: Comando '{cmd_name}' não encontrado."]
    suggestions.append(
        f" > Para usar esta funcionalidade, tente instalar o pacote '{pkg}'."
    )
    if command_exists("apt"):
        suggestions.append(
            f" > Sugestão (Debian/Ubuntu): sudo apt update && sudo apt install -y {pkg}"
        )
    elif command_exists("dnf"):
        suggestions.append(f" > Sugestão (Fedora): sudo dnf install -y {pkg}")
    elif command_exists("yum"):
        suggestions.append(f" > Sugestão (RHEL/CentOS): sudo yum install -y {pkg}")
    elif command_exists("pacman"):
        suggestions.append(f" > Sugestão (Arch): sudo pacman -Syu --noconfirm {pkg}")
    elif command_exists("brew"):
        suggestions.append(f" > Sugestão (macOS): brew install {pkg}")
    elif command_exists("zypper"):
        suggestions.append(f" > Sugestão (openSUSE): sudo zypper install -y {pkg}")
    else:
        suggestions.append(
            f" > Verifique o gerenciador de pacotes do seu sistema para instalar '{pkg}'."
        )
    return "\n".join(suggestions) + "\n"


def run_command(
    cmd_list: List[str],
    cwd: Path = core_config.PROJECT_ROOT,
    check: bool = True,
    capture: bool = True,
    input_data: Optional[str] = None,
    shell: bool = False,
    timeout: Optional[int] = 60,  # Default timeout 60s
) -> Tuple[int, str, str]:
    """Runs a subprocess command and returns exit code, stdout, stderr."""
    cmd_str = (
        shlex.join(cmd_list) if not shell else " ".join(map(shlex.quote, cmd_list))
    )
    print(f"    Executing: {cmd_str} (em {cwd})")  # Added print for visibility
    start_time = time.monotonic()
    try:
        process = subprocess.run(
            cmd_list if not shell else cmd_str,
            capture_output=capture,
            text=True,
            input=input_data,
            check=check,
            cwd=cwd,
            shell=shell,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        duration = time.monotonic() - start_time
        print(
            f"    Comando concluído em {duration:.2f}s com código {process.returncode}"
        )
        return process.returncode, process.stdout or "", process.stderr or ""
    except FileNotFoundError:
        error_msg = f"Comando não encontrado: {cmd_list[0]}"
        print(f"    ERRO: {error_msg}", file=sys.stderr)
        return 1, "", error_msg
    except subprocess.TimeoutExpired:
        error_msg = f"Comando excedeu o tempo limite de {timeout} segundos: {cmd_str}"
        print(f"    ERRO: {error_msg}", file=sys.stderr)
        return 1, "", error_msg
    except subprocess.CalledProcessError as e:  # Only happens if check=True
        error_msg = f"Comando falhou (Exit Code: {e.returncode})"
        stderr_content = e.stderr or ""
        stdout_content = e.stdout or ""
        print(
            f"    ERRO: {error_msg}. Stderr: {stderr_content.strip()}", file=sys.stderr
        )
        return e.returncode, stdout_content.strip(), stderr_content.strip()
    except Exception as e:
        error_msg = f"Erro inesperado ao executar '{cmd_str}': {e}"
        print(f"    ERRO: {error_msg}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1, "", str(e)
