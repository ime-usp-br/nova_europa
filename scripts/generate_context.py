#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ==============================================================================
# generate_context.py (v1.8 - Add pytest execution)
#
# Coleta informações de contexto abrangentes de um projeto de desenvolvimento
# (com foco em Laravel/PHP e Python) e seu ambiente para auxiliar LLMs.
#
# Permite configurar diretório de saída, limites de listagem e detalhes
# do projeto GitHub via argumentos de linha de comando.
# Inclui execução opcional de Dusk tests.
# Trata ferramentas opcionais de forma elegante, registrando avisos se ausentes.
# NOVO: Copia o arquivo de manifesto JSON mais recente de scripts/data/ para o diretório de contexto.
#
# Dependencies Base:
#   - Python 3.10+
#   - Git
#   - PHP CLI
# Dependencies Opcionais:
#   - gh (GitHub CLI)
#   - jq
#   - tree
#   - cloc
#   - composer
#   - npm
#   - python3/python, pip3/pip (para info detalhada do ambiente Python)
#   - lsb_release (para info detalhada da distro Linux)
#   - scripts/generate_manifest.py (invocado para gerar o JSON que será copiado)
# ==============================================================================

import argparse
import datetime
import json
import os
import platform
import re  # Adicionado para regex de timestamp
import shlex
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

# --- Configuration Constants (Globally Accessible) ---
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_BASE_DIR = BASE_DIR / "context_llm/code"  # Default output base
EMPTY_TREE_COMMIT = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
PHPSTAN_BIN = BASE_DIR / "vendor/bin/phpstan"
ARTISAN_CMD = ["php", str(BASE_DIR / "artisan")]
PINT_BIN = BASE_DIR / "vendor/bin/pint"
GH_ISSUE_JSON_FIELDS = (
    "number,title,body,author,state,stateReason,assignees,labels,comments"
)
DEFAULT_TREE_DEPTH = 3
CLOC_EXCLUDE_REGEX = r"(vendor|node_modules|storage|public/build|\.git|\.idea|\.vscode|\.fleet|context_llm)"
TREE_IGNORE_PATTERN = "vendor|node_modules|storage/framework|storage/logs|public/build|.git|.idea|.vscode|.fleet|context_llm"
DEFAULT_GH_ISSUE_LIST_LIMIT = 500
DEFAULT_GIT_TAG_LIMIT = 10
DEFAULT_GH_RUN_LIST_LIMIT = 10
DEFAULT_GH_PR_LIST_LIMIT = 20
DEFAULT_GH_RELEASE_LIST_LIMIT = 10
DEFAULT_GH_PROJECT_NUMBER = os.getenv("GH_PROJECT_NUMBER", "1")
DEFAULT_GH_PROJECT_OWNER = os.getenv("GH_PROJECT_OWNER", "@me")
DEFAULT_GH_PROJECT_STATUS_FIELD_NAME = os.getenv(
    "GH_PROJECT_STATUS_FIELD_NAME", "Status"
)
MANIFEST_GENERATOR_SCRIPT = (
    BASE_DIR / "scripts/generate_manifest.py"
)  # Script que gera o JSON
MANIFEST_DATA_DIR = BASE_DIR / "scripts" / "data"  # Diretório onde o JSON é salvo
TIMESTAMP_MANIFEST_REGEX = (
    r"^\d{8}_\d{6}_manifest\.json$"  # Regex para validar nome do arquivo JSON
)

PHPUNIT_OUTPUT_FILE_NAME = "phpunit_test_results.txt"
DUSK_OUTPUT_FILE_NAME = "dusk_test_results.txt"
DUSK_INFO_FILE_NAME = "dusk_test_info.txt"

# Incrementado para incluir a nova etapa de cópia do manifesto JSON
TOTAL_STEPS = 18

# Habilita saída em caso de erro e falha em pipelines
# (No Python, handled via check=True or checking return codes)


# --- Find Commands (Helper) ---
def find_command(primary: str, fallback: str) -> Optional[str]:
    if shutil.which(primary):
        return primary
    if shutil.which(fallback):
        return fallback
    return None


PYTHON_CMD = find_command("python3", "python")
PIP_CMD = find_command("pip3", "pip")


# --- Helper Functions ---
def command_exists(cmd: str) -> bool:
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


def write_warning_to_file(output_file: Path, warning_message: str):
    """Writes a warning message to the specified output file."""
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(warning_message, encoding="utf-8")
        print(f"    {warning_message.splitlines()[0]}")  # Print first line of warning
    except Exception as e:
        print(
            f"    ERRO CRÍTICO: Não foi possível escrever o aviso em {output_file}: {e}",
            file=sys.stderr,
        )


def run_command(
    cmd_list: List[str],
    output_file: Path,
    cwd: Path = BASE_DIR,
    check: bool = False,
    shell: bool = False,
    timeout: Optional[int] = 300,
) -> Tuple[int, str, str]:
    """Runs a subprocess command and saves output/error to a file."""
    cmd_str = (
        shlex.join(cmd_list) if not shell else " ".join(map(shlex.quote, cmd_list))
    )  # Safer joining for display
    print(f"    Executing: {cmd_str}...")
    start_time = time.monotonic()
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        process = subprocess.run(
            cmd_list if not shell else cmd_str,  # Pass list unless shell=True
            capture_output=True,
            text=True,
            check=check,  # Let it raise error if check is True and fails
            cwd=cwd,
            shell=shell,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",  # Add encoding/error handling
        )
        end_time = time.monotonic()
        duration = end_time - start_time
        stdout = process.stdout or ""
        stderr = process.stderr or ""
        exit_code = process.returncode
        output_content = stdout
        if exit_code != 0:
            # Log non-zero exit even if check=False
            warning_msg = f"AVISO: Comando finalizado com código {exit_code} em {duration:.2f}s. Stderr: {stderr.strip()}"
            print(f"    {warning_msg}", file=sys.stderr)
            output_content += f"\n\n--- COMMAND FAILED (Exit Code: {exit_code}) ---\nStderr:\n{stderr}"

        # Ensure final newline
        if output_content and not output_content.endswith("\n"):
            output_content += "\n"

        output_file.write_text(output_content, encoding="utf-8")
        print(f"    Output saved to: {output_file.name} ({duration:.2f}s)")
        return exit_code, stdout.strip(), stderr.strip()

    except FileNotFoundError:
        error_msg = f"Comando não encontrado: {cmd_list[0]}"
        print(f"    ERRO: {error_msg}", file=sys.stderr)
        write_warning_to_file(output_file, f"ERRO: {error_msg}\n")
        return 1, "", error_msg
    except subprocess.TimeoutExpired:
        error_msg = f"Comando excedeu o tempo limite de {timeout} segundos: {cmd_str}"
        print(f"    ERRO: {error_msg}", file=sys.stderr)
        write_warning_to_file(output_file, f"ERRO: {error_msg}\n")
        return 1, "", error_msg
    except subprocess.CalledProcessError as e:  # Only happens if check=True
        error_msg = f"Comando falhou (Exit Code: {e.returncode})"
        stderr_content = e.stderr or ""
        stdout_content = e.stdout or ""
        print(
            f"    ERRO: {error_msg}. Stderr: {stderr_content.strip()}", file=sys.stderr
        )
        write_warning_to_file(
            output_file,
            f"ERRO: {error_msg}\nStderr:\n{stderr_content}\nStdout:\n{stdout_content}\n",
        )
        return e.returncode, stdout_content.strip(), stderr_content.strip()
    except Exception as e:
        error_msg = f"Erro inesperado ao executar '{cmd_str}': {e}"
        print(f"    ERRO: {error_msg}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        write_warning_to_file(
            output_file, f"ERRO: {error_msg}\n{traceback.format_exc()}\n"
        )
        return 1, "", str(e)


# --- Collection Functions (unchanged functions omitted for brevity) ---
def collect_env_info(output_dir: Path, step_num: int, total_steps: int):
    print(
        f"[{step_num}/{total_steps}] Coletando informações do Ambiente (SO, PHP, Node)..."
    )
    run_command(["uname", "-a"], output_dir / "env_uname.txt")

    # Distro Info - Handle missing lsb_release
    lsb_file = output_dir / "env_distro_info.txt"
    if command_exists("lsb_release"):
        run_command(["lsb_release", "-a"], lsb_file)
    else:
        warning_msg = suggest_install("lsb_release")
        fallback_info = ""
        if (Path("/etc/os-release")).is_file():
            try:
                fallback_info = Path("/etc/os-release").read_text(encoding="utf-8")
                warning_msg += "\nUsando fallback: /etc/os-release\n"
            except Exception as e:
                fallback_info = f"Erro ao ler /etc/os-release: {e}"
                warning_msg += f"\nFalha ao ler /etc/os-release: {e}\n"
        else:
            fallback_info = "Nenhuma informação da distro encontrada."
            warning_msg += "\nNenhuma informação da distro encontrada.\n"
        lsb_file.write_text(warning_msg + fallback_info, encoding="utf-8")

    # PHP Info - Check command existence
    php_version_file = output_dir / "env_php_version.txt"
    php_modules_file = output_dir / "env_php_modules.txt"
    if command_exists("php"):
        run_command(["php", "-v"], php_version_file)
        run_command(["php", "-m"], php_modules_file)
    else:
        warning_msg = suggest_install("php", "php-cli")
        write_warning_to_file(php_version_file, warning_msg)
        write_warning_to_file(php_modules_file, warning_msg)

    # Node/NPM Info - Check command existence
    node_version_file = output_dir / "env_node_version.txt"
    npm_version_file = output_dir / "env_npm_version.txt"
    if command_exists("node"):
        run_command(["node", "-v"], node_version_file)
    else:
        write_warning_to_file(node_version_file, suggest_install("node", "nodejs"))
    if command_exists("npm"):
        run_command(["npm", "-v"], npm_version_file)
    else:
        write_warning_to_file(npm_version_file, suggest_install("npm"))


def collect_python_env_info(output_dir: Path, step_num: int, total_steps: int):
    print(f"[{step_num}/{total_steps}] Coletando informações do Ambiente Python...")
    py_version_file = output_dir / "env_python_version.txt"
    py_which_file = output_dir / "env_python_which.txt"
    pip_version_file = output_dir / "env_pip_version.txt"
    pip_freeze_file = output_dir / "env_pip_freeze.txt"
    venv_file = output_dir / "env_python_venv_status.txt"

    # Check Python
    if PYTHON_CMD:
        run_command([PYTHON_CMD, "--version"], py_version_file)
        run_command(["which", PYTHON_CMD], py_which_file)
    else:
        warning_msg = suggest_install("python3 or python", "python3")
        write_warning_to_file(py_version_file, warning_msg)
        write_warning_to_file(py_which_file, warning_msg)

    # Check Pip
    if PIP_CMD:
        run_command([PIP_CMD, "--version"], pip_version_file)
        run_command([PIP_CMD, "freeze"], pip_freeze_file)
    else:
        warning_msg = suggest_install("pip3 or pip", "python3-pip")
        write_warning_to_file(pip_version_file, warning_msg)
        write_warning_to_file(pip_freeze_file, warning_msg)

    # Venv Check
    venv_status = (
        "Ambiente virtual Python ATIVO: " + os.environ["VIRTUAL_ENV"]
        if "VIRTUAL_ENV" in os.environ
        else "Nenhum ambiente virtual Python detectado (variável VIRTUAL_ENV não definida)."
    )
    write_warning_to_file(venv_file, venv_status + "\n")

    # Package Files - Unchanged, just checks existence
    print("  Coletando arquivos de gerenciamento de pacotes Python (se existirem)...")
    for pkg_file in [
        "requirements.txt",
        "requirements-dev.txt",
        "Pipfile",
        "pyproject.toml",
    ]:
        src_path = BASE_DIR / pkg_file
        if src_path.is_file():
            dest_path = output_dir / f"env_python_pkgfile_{pkg_file.replace('/', '_')}"
            try:
                shutil.copy2(src_path, dest_path)
                print(f"    Capturando {pkg_file}...")
            except Exception as e:
                print(f"    Erro ao copiar {pkg_file}: {e}", file=sys.stderr)
                write_warning_to_file(dest_path, f"Erro ao ler {pkg_file}: {e}\n")
        else:
            print(f"    Arquivo {pkg_file} não encontrado.")


# ... (collect_git_info, collect_gh_info, collect_gh_project_info, collect_artisan_info, collect_dependency_info, collect_structure_info, copy_project_files, collect_github_issue_details, run_quality_checks, run_tests, run_dusk_tests, create_dusk_note - unchanged) ...
def collect_git_info(
    output_dir: Path, args: argparse.Namespace, step_num: int, total_steps: int
):
    print(f"[{step_num}/{total_steps}] Coletando informações do Git...")
    git_log_format = (
        "commit %H%nAuthor: %an <%ae>%nDate:   %ad%n%n%w(0,4)%s%n%n%w(0,4,4)%b%n"
    )
    run_command(
        ["git", "log", f"--pretty=format:{git_log_format}"], output_dir / "git_log.txt"
    )
    run_command(
        ["git", "diff", f"{EMPTY_TREE_COMMIT}..HEAD"],
        output_dir / "git_diff_empty_tree_to_head.txt",
    )
    run_command(["git", "diff", "--cached"], output_dir / "git_diff_cached.txt")
    run_command(["git", "diff"], output_dir / "git_diff_unstaged.txt")
    run_command(["git", "status"], output_dir / "git_status.txt")
    run_command(["git", "ls-files"], output_dir / "git_ls_files.txt")
    tags_file = output_dir / "git_recent_tags.txt"
    exit_code, stdout, _ = run_command(
        ["git", "tag", "--sort=-creatordate"], tags_file, check=False
    )
    if exit_code == 0 and stdout:
        lines = stdout.strip().split("\n")
        tags_file.write_text("\n".join(lines[: args.tag_limit]) + "\n")
        print(f"    {min(len(lines), args.tag_limit)} tags recentes salvas.")
    elif exit_code == 0:
        tags_file.write_text("Nenhuma tag encontrada.\n")


def collect_gh_info(
    output_dir: Path, args: argparse.Namespace, step_num: int, total_steps: int
):
    print(
        f"[{step_num}/{total_steps}] Coletando contexto adicional do GitHub (Repo, Actions, Security)..."
    )
    if not command_exists("gh"):
        warning_msg = suggest_install("gh")
        print(f"  {warning_msg.splitlines()[0]} Pulando esta seção.", file=sys.stderr)
        for fname in [
            "gh_run_list.txt",
            "gh_workflow_list.txt",
            "gh_pr_list.txt",
            "gh_release_list.txt",
            "gh_secret_list.txt",
            "gh_variable_list.txt",
            "gh_repo_view.txt",
            "gh_ruleset_list.txt",
            "gh_codescanning_alert_list.txt",
            "gh_dependabot_alert_list.txt",
        ]:
            write_warning_to_file(output_dir / fname, warning_msg)
        return
    run_command(
        ["gh", "run", "list", "--limit", str(args.run_limit)],
        output_dir / "gh_run_list.txt",
    )
    run_command(["gh", "workflow", "list"], output_dir / "gh_workflow_list.txt")
    run_command(
        ["gh", "pr", "list", "--state", "all", "--limit", str(args.pr_limit)],
        output_dir / "gh_pr_list.txt",
    )
    run_command(
        ["gh", "release", "list", "--limit", str(args.release_limit)],
        output_dir / "gh_release_list.txt",
    )
    run_command(["gh", "secret", "list"], output_dir / "gh_secret_list.txt")
    run_command(["gh", "variable", "list"], output_dir / "gh_variable_list.txt")
    run_command(["gh", "repo", "view"], output_dir / "gh_repo_view.txt")
    run_command(["gh", "ruleset", "list"], output_dir / "gh_ruleset_list.txt")
    run_command(
        ["gh", "code-scanning", "alert", "list"],
        output_dir / "gh_codescanning_alert_list.txt",
    )
    run_command(
        ["gh", "dependabot", "alert", "list"],
        output_dir / "gh_dependabot_alert_list.txt",
    )


def collect_gh_project_info(
    output_dir: Path, args: argparse.Namespace, step_num: int, total_steps: int
):
    print(f"[{step_num}/{total_steps}] Coletando Status do GitHub Project...")
    status_file = output_dir / "gh_project_items_status.json"
    summary_file = output_dir / "gh_project_items_summary.json"
    project_num = args.gh_project_number
    project_owner = args.gh_project_owner
    status_field = args.gh_project_status_field

    if not command_exists("gh"):
        warning_msg = suggest_install("gh")
        print(f"  {warning_msg.splitlines()[0]} Pulando esta seção.", file=sys.stderr)
        write_warning_to_file(
            status_file, json.dumps({"error": "gh command not found"}) + "\n"
        )
        write_warning_to_file(
            summary_file, json.dumps({"error": "gh command not found"}) + "\n"
        )
        return

    if not project_num or not project_owner:
        msg = "Número ou proprietário do projeto GitHub não especificado via argumentos (--project-number, --project-owner)."
        print(f"  AVISO: {msg} Pulando esta seção.", file=sys.stderr)
        write_warning_to_file(status_file, json.dumps({"error": msg}) + "\n")
        write_warning_to_file(summary_file, json.dumps({"error": msg}) + "\n")
        return

    print(f"  Coletando itens do Projeto #{project_num} (Owner: {project_owner})...")
    cmd_list = [
        "gh",
        "project",
        "item-list",
        str(project_num),
        "--owner",
        project_owner,
        "--format",
        "json",
    ]
    exit_code, stdout_gh, stderr_gh = run_command(cmd_list, status_file, check=False)

    if exit_code != 0:
        print(
            f"  ERRO: Falha ao coletar itens do projeto (Código: {exit_code}). Erro salvo em {status_file.name}.",
            file=sys.stderr,
        )
        write_warning_to_file(
            summary_file,
            json.dumps(
                {
                    "error": f"Failed to list project items. Exit code: {exit_code}",
                    "stderr": stderr_gh,
                }
            )
            + "\n",
        )
        return

    if not command_exists("jq"):
        warning_msg = suggest_install("jq")
        print(
            f"  {warning_msg.splitlines()[0]} Não foi possível gerar o resumo {summary_file.name}.",
            file=sys.stderr,
        )
        write_warning_to_file(
            summary_file, warning_msg
        )  # Write warning to summary file
        return

    if not stdout_gh or stdout_gh.strip() == "null" or stdout_gh.strip() == "":
        error_msg = "Comando gh project item-list retornou vazio ou nulo. Não é possível gerar resumo."
        print(f"  AVISO: {error_msg}", file=sys.stderr)
        write_warning_to_file(summary_file, json.dumps({"error": error_msg}) + "\n")
        return

    print(
        f"  Gerando resumo de status dos itens (usando jq e campo '{status_field}')..."
    )
    jq_filter = f"""
    [ .items[] |
        {{
            type: .type,
            number: .content.number,
            title: .content.title,
            status: (try (.fieldValues[] | select(.field.name == "{status_field}") | .value) // "N/A"),
            assignees: [ .fieldValues[] | select(.field.name == "Assignees") | .users[].login ] | unique | join(", ") // "",
            labels: [ .fieldValues[] | select(.field.name == "Labels") | .labels[].name ] | unique | join(", ") // "",
            milestone: (try (.fieldValues[] | select(.field.name == "Milestone") | .milestone.title) // ""),
            repository: (try (.fieldValues[] | select(.field.name == "Repository") | .repository.nameWithOwner) // "")
        }}
    ]
    """
    try:
        jq_process = subprocess.run(
            ["jq", jq_filter],
            input=stdout_gh,
            text=True,
            check=True,
            capture_output=True,
        )
        summary_file.write_text(jq_process.stdout, encoding="utf-8")
        print(f"  Resumo gerado em {summary_file.name}.")
    except subprocess.CalledProcessError as e:
        error_msg = f"Falha ao processar JSON com jq (Código: {e.returncode})."
        print(
            f"  ERRO: {error_msg} Veja o erro completo no arquivo de log.",
            file=sys.stderr,
        )
        write_warning_to_file(
            summary_file,
            f"ERRO: {error_msg}\nStderr:\n{e.stderr}\nStdout:\n{e.stdout}\n",
        )
    except FileNotFoundError:
        warning_msg = suggest_install("jq")
        print(
            f"  {warning_msg.splitlines()[0]} Não foi possível gerar o resumo {summary_file.name}.",
            file=sys.stderr,
        )
        write_warning_to_file(summary_file, warning_msg)
    except Exception as e:
        error_msg = f"Erro inesperado ao processar com jq: {e}"
        print(f"  ERRO: {error_msg}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        write_warning_to_file(
            summary_file, f"ERRO: {error_msg}\n{traceback.format_exc()}\n"
        )


def collect_artisan_info(output_dir: Path, step_num: int, total_steps: int):
    print(f"[{step_num}/{total_steps}] Coletando informações do Laravel Artisan...")
    if not command_exists("php") or not (BASE_DIR / "artisan").is_file():
        print(
            "  AVISO: Comando 'php' ou arquivo 'artisan' não encontrado. Pulando comandos Artisan.",
            file=sys.stderr,
        )
        return
    code, _, _ = run_command(
        ARTISAN_CMD + ["route:list", "--json"], output_dir / "artisan_route_list.json"
    )
    if code != 0:
        run_command(ARTISAN_CMD + ["route:list"], output_dir / "artisan_route_list.txt")
    code, _, _ = run_command(
        ARTISAN_CMD + ["about", "--json"], output_dir / "artisan_about.json"
    )
    if code != 0:
        run_command(ARTISAN_CMD + ["about"], output_dir / "artisan_about.txt")
    code, _, _ = run_command(
        ARTISAN_CMD + ["db:show", "--json"], output_dir / "artisan_db_show.json"
    )
    if code != 0:
        run_command(ARTISAN_CMD + ["db:show"], output_dir / "artisan_db_show.txt")
    run_command(ARTISAN_CMD + ["channel:list"], output_dir / "artisan_channel_list.txt")
    run_command(ARTISAN_CMD + ["event:list"], output_dir / "artisan_event_list.txt")
    run_command(
        ARTISAN_CMD + ["permission:show"], output_dir / "artisan_permission_show.txt"
    )
    run_command(ARTISAN_CMD + ["queue:failed"], output_dir / "artisan_queue_failed.txt")
    run_command(
        ARTISAN_CMD + ["schedule:list"], output_dir / "artisan_schedule_list.txt"
    )
    run_command(ARTISAN_CMD + ["env"], output_dir / "artisan_env.txt")
    run_command(
        ARTISAN_CMD + ["migrate:status"], output_dir / "artisan_migrate_status.txt"
    )
    run_command(
        ARTISAN_CMD + ["config:show", "app"], output_dir / "artisan_config_show_app.txt"
    )
    run_command(
        ARTISAN_CMD + ["config:show", "database"],
        output_dir / "artisan_config_show_database.txt",
    )


def collect_dependency_info(output_dir: Path, step_num: int, total_steps: int):
    print(
        f"[{step_num}/{total_steps}] Coletando informações de Dependências (Composer, NPM)..."
    )
    composer_file = output_dir / "composer_show.txt"
    npm_file = output_dir / "npm_list_depth0.txt"
    if command_exists("composer"):
        run_command(["composer", "show"], composer_file)
    else:
        write_warning_to_file(composer_file, suggest_install("composer"))
    if command_exists("npm"):
        run_command(["npm", "list", "--depth=0"], npm_file)
    else:
        write_warning_to_file(npm_file, suggest_install("npm"))


def collect_structure_info(
    output_dir: Path, args: argparse.Namespace, step_num: int, total_steps: int
):
    print(
        f"[{step_num}/{total_steps}] Coletando informações da Estrutura do Projeto..."
    )
    tree_file = output_dir / f"project_tree_L{args.tree_depth}.txt"
    cloc_file = output_dir / "project_cloc.txt"
    if command_exists("tree"):
        run_command(
            ["tree", "-L", str(args.tree_depth), "-a", "-I", TREE_IGNORE_PATTERN],
            tree_file,
        )
    else:
        write_warning_to_file(tree_file, suggest_install("tree"))
    if command_exists("cloc"):
        run_command(
            ["cloc", ".", "--fullpath", f"--not-match-d={CLOC_EXCLUDE_REGEX}"],
            cloc_file,
        )
    else:
        write_warning_to_file(
            cloc_file, suggest_install("cloc", "cloc")
        )  # Package name is usually cloc


def copy_project_files(output_dir: Path, step_num: int, total_steps: int):
    print(f"[{step_num}/{total_steps}] Copiando Planos e Meta-Prompts...")
    dirs_to_copy = {
        "planos": BASE_DIR / "planos",
        "meta-prompts": BASE_DIR / "templates" / "meta-prompts",
    }
    for name, src_dir in dirs_to_copy.items():
        if src_dir.is_dir():
            print(f"  Copiando arquivos de '{src_dir.relative_to(BASE_DIR)}'...")
            copied_count = 0
            for src_file in src_dir.glob("*.txt"):  # Only copy .txt files
                if src_file.is_file():
                    try:
                        shutil.copy2(src_file, output_dir / src_file.name)
                        copied_count += 1
                    except Exception as e:
                        print(
                            f"    Erro ao copiar {src_file.name}: {e}", file=sys.stderr
                        )
            if copied_count == 0:
                print(f"    Nenhum arquivo .txt encontrado em {name}/")
        else:
            print(f"  Diretório '{src_dir.relative_to(BASE_DIR)}' não encontrado.")


def collect_github_issue_details(
    output_dir: Path, args: argparse.Namespace, step_num: int, total_steps: int
):
    print(f"[{step_num}/{total_steps}] Coletando detalhes das Issues do GitHub (gh)...")
    issues_dir = output_dir  # Save directly in the timestamped dir
    if not command_exists("gh"):
        warning_msg = suggest_install("gh")
        print(
            f"  {warning_msg.splitlines()[0]} Pulando coleta de issues.",
            file=sys.stderr,
        )
        write_warning_to_file(issues_dir / "github_issues_skipped.log", warning_msg)
        return
    if not command_exists("jq"):
        warning_msg_jq = suggest_install("jq")
        print(
            f"  {warning_msg_jq.splitlines()[0]} Coleta de issues pode falhar ou ser incompleta.",
            file=sys.stderr,
        )

    print(f"  Issues serão salvas em: {issues_dir.relative_to(BASE_DIR)}")
    print(
        f"  Listando e filtrando issues (limite: {args.issue_limit}, excluindo 'Closed as not planned')..."
    )
    list_cmd = [
        "gh",
        "issue",
        "list",
        "--state",
        "all",
        "--limit",
        str(args.issue_limit),
        "--json",
        "number,stateReason",
    ]
    try:
        list_process = subprocess.run(
            list_cmd, capture_output=True, text=True, check=True, cwd=BASE_DIR
        )
        if command_exists("jq"):
            jq_filter = '[.[] | select(.stateReason != "NOT_PLANNED") | .number]'
            jq_process = subprocess.run(
                ["jq", "-c", jq_filter],
                input=list_process.stdout,
                text=True,
                check=True,
                capture_output=True,
            )
            issue_numbers = json.loads(jq_process.stdout)
        else:
            print("    AVISO: Tentando parse simples sem jq (pode ser menos preciso).")
            issue_numbers = [
                int(line.split("\t")[0])
                for line in list_process.stdout.strip().split("\n")
                if line and "NOT_PLANNED" not in line
            ]

    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        json.JSONDecodeError,
        ValueError,
    ) as e:
        print(f"  AVISO: Falha ao listar/filtrar issues: {e}", file=sys.stderr)
        write_warning_to_file(
            issues_dir / "github_issues_error.log",
            f"Falha ao listar/filtrar issues: {e}\n",
        )
        return

    if not issue_numbers:
        print("  Nenhuma issue encontrada (após filtrar).")
        write_warning_to_file(
            issues_dir / "no_issues_found.json",
            '{ "message": "Nenhuma issue encontrada (após filtrar)." }\n',
        )
        return

    print(f"  Encontradas {len(issue_numbers)} issues para baixar detalhes...")
    downloaded_count = 0
    for issue_number in issue_numbers:
        print(f"    Coletando detalhes da Issue #{issue_number}...")
        issue_output_file = issues_dir / f"github_issue_{issue_number}_details.json"
        view_cmd = [
            "gh",
            "issue",
            "view",
            str(issue_number),
            "--json",
            GH_ISSUE_JSON_FIELDS,
        ]
        exit_code, _, stderr_view = run_command(
            view_cmd, issue_output_file, check=False
        )
        if exit_code == 0:
            downloaded_count += 1
        else:
            print(
                f"    AVISO: Falha ao coletar detalhes da Issue #{issue_number} (Código: {exit_code}).",
                file=sys.stderr,
            )
        time.sleep(0.2)
    print(f"  Coleta de {downloaded_count}/{len(issue_numbers)} issues concluída.")


def run_quality_checks(output_dir: Path, step_num: int, total_steps: int):
    print(f"[{step_num}/{total_steps}] Executando análise estática com PHPStan...")
    phpstan_file = output_dir / "phpstan_analysis.txt"
    if PHPSTAN_BIN.is_file() and os.access(PHPSTAN_BIN, os.X_OK):
        run_command(
            [str(PHPSTAN_BIN), "analyse", "--no-progress", "--memory-limit=2G"],
            phpstan_file,
        )
    else:
        warning_msg = suggest_install("PHPStan/Larastan", "larastan/larastan --dev")
        write_warning_to_file(
            phpstan_file,
            warning_msg
            + f"PHPStan não executado: Binário não encontrado ou não executável em {PHPSTAN_BIN}\n",
        )

    print(
        f"[{step_num+1}/{total_steps}] Verificando estilo de código com Pint..."
    )  # Ajuste o número total se necessário
    pint_file = output_dir / "pint_test_results.txt"
    if PINT_BIN.is_file() and os.access(PINT_BIN, os.X_OK):
        exit_code, _, _ = run_command([str(PINT_BIN), "--test"], pint_file)
        if exit_code != 0:
            with open(pint_file, "a", encoding="utf-8") as f:
                f.write(f"\n\n--- Pint Exit Code: {exit_code} ---\n")
            print(
                f"  AVISO: Verificação Pint falhou/encontrou problemas (Código: {exit_code}).",
                file=sys.stderr,
            )
    else:
        warning_msg = suggest_install("Laravel Pint", "laravel/pint --dev")
        write_warning_to_file(
            pint_file,
            warning_msg
            + f"Pint não executado: Binário não encontrado ou não executável em {PINT_BIN}\n",
        )


def run_tests(output_dir: Path, step_num: int, total_steps: int):
    print(f"[{step_num}/{total_steps}] Executando testes PHPUnit (php artisan test)...")
    phpunit_output_file = output_dir / PHPUNIT_OUTPUT_FILE_NAME
    if (BASE_DIR / "artisan").is_file() and command_exists("php"):
        exit_code, _, stderr = run_command(
            ARTISAN_CMD + ["test", "--env=testing"], phpunit_output_file, check=False
        )
        try:
            with open(phpunit_output_file, "a", encoding="utf-8") as f:
                f.write(f"\n\n--- PHPUnit Exit Code: {exit_code} ---")
                if exit_code != 0:
                    f.write(
                        f"\n  -> Revise o arquivo '{PHPUNIT_OUTPUT_FILE_NAME}' para detalhes da falha."
                    )
            if exit_code != 0:
                print(
                    f"  AVISO: Testes PHPUnit falharam (Código: {exit_code}). Veja {phpunit_output_file.name}.",
                    file=sys.stderr,
                )
            else:
                print(f"  Testes PHPUnit executados com sucesso (Código: 0).")
        except Exception as e:
            print(
                f"  ERRO: Não foi possível anexar o código de saída ao arquivo {phpunit_output_file.name}: {e}",
                file=sys.stderr,
            )
    else:
        warning_msg = (
            "Comando 'php artisan test' não executado: PHP ou artisan não encontrado.\n"
        )
        write_warning_to_file(phpunit_output_file, warning_msg)
        print(f"  {warning_msg.strip()}", file=sys.stderr)


def run_python_tests(output_dir: Path, step_num: int, total_steps: int):
    """Executa os testes Python usando pytest."""
    print(f"[{step_num}/{total_steps}] Executando testes Python (pytest)...")
    pytest_output_file = output_dir / "pytest_results.txt"  # Nome do arquivo de saída

    if not PYTHON_CMD:
        warning_msg = "Comando Python não encontrado. Pulando testes pytest."
        write_warning_to_file(pytest_output_file, warning_msg + "\n")
        print(f"  {warning_msg}", file=sys.stderr)
        return

    # Comando para executar pytest no diretório específico
    # Usar `python -m pytest` é geralmente mais robusto
    test_cmd = [PYTHON_CMD, "-m", "pytest", "-v", "tests/python"]

    # Executa o comando, check=False para capturar saída mesmo em falha
    exit_code, stdout, stderr = run_command(
        test_cmd, pytest_output_file, check=False  # Arquivo onde a saída será salva
    )

    # Adiciona o código de saída ao final do arquivo para referência
    try:
        if pytest_output_file.exists():
            with open(pytest_output_file, "a", encoding="utf-8") as f:
                f.write(f"\n\n--- pytest Exit Code: {exit_code} ---")
        if exit_code != 0:
            print(
                f"  AVISO: Testes pytest falharam ou não puderam ser executados (Código: {exit_code}). Veja {pytest_output_file.name}.",
                file=sys.stderr,
            )
        else:
            print(
                f"  Testes pytest executados (Código: 0). Veja {pytest_output_file.name}."
            )
    except Exception as e:
        print(
            f"  ERRO: Não foi possível anexar o código de saída ao arquivo {pytest_output_file.name}: {e}",
            file=sys.stderr,
        )


def run_dusk_tests(output_dir: Path, step_num: int, total_steps: int):
    print(f"[{step_num}/{total_steps}] Executando testes Dusk (php artisan dusk)...")
    dusk_output_file = output_dir / DUSK_OUTPUT_FILE_NAME
    dusk_env_file = BASE_DIR / ".env.dusk.local"
    if not (BASE_DIR / "artisan").is_file() or not command_exists("php"):
        warning_msg = (
            "Comando 'php artisan dusk' não executado: PHP ou artisan não encontrado.\n"
        )
        write_warning_to_file(dusk_output_file, warning_msg)
        print(f"  {warning_msg.strip()}", file=sys.stderr)
        return
    if not dusk_env_file.is_file():
        print(
            f"  AVISO: Arquivo de ambiente Dusk '{dusk_env_file.name}' não encontrado. Os testes Dusk podem falhar.",
            file=sys.stderr,
        )
    exit_code, _, stderr = run_command(
        ARTISAN_CMD + ["dusk"], dusk_output_file, check=False, timeout=600
    )
    try:
        with open(dusk_output_file, "a", encoding="utf-8") as f:
            f.write(
                f"\n\n--- COMMAND FAILED (Exit Code: {exit_code}) ---\nStderr:\n{stderr}\n"
            )
            f.write(f"\n\n--- Dusk Exit Code: {exit_code} ---")
            if exit_code != 0:
                f.write(
                    f"\n  -> Revise o arquivo '{DUSK_OUTPUT_FILE_NAME}' e os diretórios tests/Browser/screenshots/ e tests/Browser/console/ para detalhes da falha."
                )
        if exit_code != 0:
            print(
                f"  AVISO: Testes Dusk falharam (Código: {exit_code}). Veja {DUSK_OUTPUT_FILE_NAME}.",
                file=sys.stderr,
            )
        else:
            print(
                f"  Tentativa de execução Dusk concluída (Código: {exit_code}). Verifique {DUSK_OUTPUT_FILE_NAME} para saída."
            )
    except Exception as e:
        print(
            f"  ERRO: Não foi possível anexar o código de saída ao arquivo {dusk_output_file.name}: {e}",
            file=sys.stderr,
        )


def create_dusk_note(output_dir: Path, step_num: int, total_steps: int):
    print(
        f"[{step_num}/{total_steps}] Criando arquivo de informação sobre testes Dusk..."
    )
    dusk_info_file = output_dir / DUSK_INFO_FILE_NAME
    content = f"""
######################################################################
# NOTA IMPORTANTE SOBRE TESTES DUSK                                #
######################################################################

Este script ('{Path(__file__).name}') TENTA EXECUTAR os testes Laravel Dusk ('php artisan dusk') assumindo que o ChromeDriver e o servidor da aplicação estão rodando manualmente.

A saída desta tentativa de execução foi salva em '{DUSK_OUTPUT_FILE_NAME}'.

**Lembretes para execução manual (se necessário):**
1. Garanta que o servidor Laravel esteja rodando (ex: 'php artisan serve --port=8000').
2. Garanta que o ChromeDriver esteja rodando (ex: './vendor/laravel/dusk/bin/chromedriver-linux --port=9515').
3. Execute 'php artisan dusk' manualmente no terminal.
4. Execute '{Path(__file__).name}' DEPOIS, se precisar capturar o estado *após* essa execução manual.

Os artefatos de falha (screenshots, console logs) ainda estarão nos diretórios padrão do Dusk ('tests/Browser/screenshots', 'tests/Browser/console').

######################################################################
"""
    try:
        write_warning_to_file(dusk_info_file, content.strip() + "\n")
        print(f"  Arquivo '{DUSK_INFO_FILE_NAME}' criado com sucesso.")
    except Exception as e:
        print(f"  ERRO: Falha ao criar '{DUSK_INFO_FILE_NAME}': {e}", file=sys.stderr)


# --- NOVA FUNÇÃO: Encontrar o manifesto JSON mais recente ---
def find_latest_manifest_json(manifest_data_dir: Path) -> Optional[Path]:
    """Encontra o arquivo _manifest.json mais recente no diretório de dados."""
    if not manifest_data_dir.is_dir():
        print(
            f"  Aviso: Diretório de dados do manifesto '{manifest_data_dir.relative_to(BASE_DIR)}' não encontrado.",
            file=sys.stderr,
        )
        return None
    manifest_files = [
        f
        for f in manifest_data_dir.glob("*_manifest.json")
        if f.is_file() and re.match(TIMESTAMP_MANIFEST_REGEX, f.name)
    ]
    if not manifest_files:
        print(
            f"  Aviso: Nenhum arquivo de manifesto JSON encontrado em '{manifest_data_dir.relative_to(BASE_DIR)}'.",
            file=sys.stderr,
        )
        return None
    latest_manifest_path = sorted(manifest_files, reverse=True)[0]
    print(
        f"  Encontrado manifesto JSON mais recente: '{latest_manifest_path.relative_to(BASE_DIR)}'"
    )
    return latest_manifest_path


# --- NOVA FUNÇÃO: Copiar o manifesto JSON mais recente ---
def copy_latest_manifest_json(output_dir: Path, step_num: int, total_steps: int):
    """Copia o arquivo _manifest.json mais recente para o diretório de contexto."""
    print(
        f"[{step_num}/{total_steps}] Copiando manifesto JSON mais recente para o diretório de contexto..."
    )
    latest_manifest_path = find_latest_manifest_json(MANIFEST_DATA_DIR)
    if latest_manifest_path:
        try:
            dest_path = output_dir / latest_manifest_path.name
            shutil.copy2(latest_manifest_path, dest_path)
            print(
                f"  Manifesto '{latest_manifest_path.name}' copiado para '{dest_path.relative_to(BASE_DIR)}'."
            )
        except Exception as e:
            print(
                f"  ERRO: Falha ao copiar o manifesto JSON '{latest_manifest_path.name}': {e}",
                file=sys.stderr,
            )
    else:
        print(f"  Aviso: Nenhum manifesto JSON para copiar.")


# --- Função para gerar manifest.md (agora inclui o JSON copiado) ---
def generate_manifest(output_dir: Path, timestamp: str):
    print("[Final] Gerando arquivo de manifesto (manifest.md)...")
    manifest_file = output_dir / "manifest.md"
    try:
        with open(manifest_file, "w", encoding="utf-8") as f:
            f.write(
                f"# Manifesto de Contexto - Gerado por {Path(__file__).name} v1.7\n"
            )  # Versão Atualizada
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Diretório: ./{output_dir.relative_to(BASE_DIR)}\n\n")
            f.write("## Conteúdo Coletado:\n")
            # Lista todos os arquivos no diretório de saída agora
            files_in_dir = sorted(
                [
                    item.name
                    for item in output_dir.iterdir()
                    if item.is_file() and item.name != "manifest.md"
                ]
            )
            for filename in files_in_dir:
                f.write(f" - {filename}\n")
            f.write("\n## Notas:\n")
            f.write("- Revise os arquivos individuais para o contexto detalhado.\n")
            f.write(
                "- O arquivo `YYYYMMDD_HHMMSS_manifest.json` (se presente) contém o manifesto JSON detalhado gerado por `generate_manifest.py`.\n"
            )  # Nota Adicionada
            f.write(
                f"- '{PHPUNIT_OUTPUT_FILE_NAME}' contém a saída completa do comando 'php artisan test'.\n"
            )
            f.write(
                f"- '{DUSK_OUTPUT_FILE_NAME}' contém a saída da tentativa de execução de 'php artisan dusk'.\n"
            )
            f.write(
                f"- '{DUSK_INFO_FILE_NAME}' contém uma nota sobre a execução/pré-requisitos dos testes Dusk.\n"
            )
            f.write(
                "- O status dos itens no GitHub Project (se configurado e acessível) está em 'gh_project_items_*.json'.\n"
            )
            f.write(
                "- Alguns comandos podem ter falhado (verifique arquivos com mensagens de erro).\n"
            )
            f.write(
                "- A completude depende das ferramentas disponíveis (php, python, gh, jq, tree, cloc, composer, npm) e permissões.\n"
            )
        print(f"  Manifesto (manifest.md) gerado em: {manifest_file.name}")
    except Exception as e:
        print(f"  ERRO: Falha ao gerar o manifesto (manifest.md): {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)


# --- Função Principal Orchestrator (ATUALIZADA) ---
def run_all_collections(output_dir: Path, timestamp: str, args: argparse.Namespace):
    """Orchestrates all context collection steps, including manifest generation and copying."""
    step = 0
    # Etapas existentes (mantidas)
    step += 1
    collect_env_info(output_dir, step, TOTAL_STEPS)
    step += 1
    collect_python_env_info(output_dir, step, TOTAL_STEPS)
    step += 1
    collect_git_info(output_dir, args, step, TOTAL_STEPS)
    step += 1
    collect_gh_info(output_dir, args, step, TOTAL_STEPS)
    step += 1
    collect_gh_project_info(output_dir, args, step, TOTAL_STEPS)
    step += 1
    collect_artisan_info(output_dir, step, TOTAL_STEPS)
    step += 1
    collect_dependency_info(output_dir, step, TOTAL_STEPS)
    step += 1
    collect_structure_info(output_dir, args, step, TOTAL_STEPS)
    step += 1
    collect_github_issue_details(output_dir, args, step, TOTAL_STEPS)
    # Executa quality checks (phpstan, pint)
    step += 1
    run_quality_checks(
        output_dir, step, TOTAL_STEPS
    )  # Agora ocupa a etapa 11 e 12 internamente
    step += 1  # Ajusta o contador para a próxima etapa (13)
    step += 1
    run_tests(output_dir, step, TOTAL_STEPS)  # PHPUnit (Etapa 13)
    step += 1
    run_dusk_tests(output_dir, step, TOTAL_STEPS)  # Dusk (Etapa 14)
    step += 1
    create_dusk_note(output_dir, step, TOTAL_STEPS)  # Nota Dusk (Etapa 15)
    step += 1
    run_python_tests(output_dir, step, TOTAL_STEPS)  # pytest (Etapa 16)

    # --- AC22 #32: Invocar generate_manifest.py ---
    # Assume-se que esta etapa aconteça aqui, ANTES de tentar copiar o JSON.
    step += 1
    print(
        f"[{step}/{TOTAL_STEPS}] Invocando generate_manifest.py para criar/atualizar manifesto JSON..."
    )
    if MANIFEST_GENERATOR_SCRIPT.is_file() and os.access(
        MANIFEST_GENERATOR_SCRIPT, os.X_OK
    ):
        # Chama o script de manifesto sem argumentos extras por padrão.
        # Ele usará seu próprio timestamp e diretório de saída padrão (scripts/data/).
        cmd_manifest = [sys.executable, str(MANIFEST_GENERATOR_SCRIPT)]
        manifest_json_output_file = (
            output_dir / "generate_manifest_py_output.log"
        )  # Log da execução
        exit_code_manifest, _, stderr_manifest = run_command(
            cmd_manifest, manifest_json_output_file, check=False
        )
        if exit_code_manifest != 0:
            print(
                f"  AVISO: A execução de generate_manifest.py falhou (Código: {exit_code_manifest}). O manifesto JSON pode não ter sido gerado/atualizado.",
                file=sys.stderr,
            )
    else:
        print(
            f"  AVISO: Script generate_manifest.py não encontrado ou não executável em '{MANIFEST_GENERATOR_SCRIPT}'. Pulando geração do manifesto JSON.",
            file=sys.stderr,
        )

    # --- NOVA ETAPA: Copiar o manifesto JSON ---
    step += 1
    copy_latest_manifest_json(output_dir, step, TOTAL_STEPS)  # Etapa 18

    # --- ETAPA FINAL: Gerar manifest.md ---
    # Esta função agora é a última e irá incluir o JSON copiado na lista.
    generate_manifest(output_dir, timestamp)


# --- Função para configurar e retornar o parser de argumentos (sem alterações) ---
def setup_arg_parser() -> argparse.ArgumentParser:
    """Sets up and returns the argument parser."""
    parser = argparse.ArgumentParser(
        description="Collect project context for LLMs. Uses configuration from constants unless overridden by arguments.",
        epilog=f"""Examples:
  # Run with default settings
  python {Path(sys.argv[0]).name}

  # Specify a different output directory and higher tree depth
  python {Path(sys.argv[0]).name} --output-dir /tmp/my_context --tree-depth 4

  # Collect fewer GitHub items
  python {Path(sys.argv[0]).name} --issue-limit 100 --pr-limit 10

  # Collect info for a different GitHub Project
  python {Path(sys.argv[0]).name} --project-number 5 --project-owner "my-org" --project-status-field "Current Sprint"
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_BASE_DIR,  # Default from constant
        help=f"Base directory to save the context files (default: ./{DEFAULT_OUTPUT_BASE_DIR.relative_to(BASE_DIR)})",
    )
    parser.add_argument(
        "--tree-depth",
        type=int,
        default=DEFAULT_TREE_DEPTH,  # Default from constant
        help=f"Maximum depth for the 'tree' command (default: {DEFAULT_TREE_DEPTH})",
    )
    parser.add_argument(
        "--issue-limit",
        type=int,
        default=DEFAULT_GH_ISSUE_LIST_LIMIT,  # Default from constant
        help=f"Maximum number of GitHub issues to fetch details for (default: {DEFAULT_GH_ISSUE_LIST_LIMIT})",
    )
    parser.add_argument(
        "--tag-limit",
        type=int,
        default=DEFAULT_GIT_TAG_LIMIT,  # Default from constant
        help=f"Maximum number of recent Git tags to list (default: {DEFAULT_GIT_TAG_LIMIT})",
    )
    parser.add_argument(
        "--run-limit",
        type=int,
        default=DEFAULT_GH_RUN_LIST_LIMIT,  # Default from constant
        help=f"Maximum number of recent GitHub Actions runs to list (default: {DEFAULT_GH_RUN_LIST_LIMIT})",
    )
    parser.add_argument(
        "--pr-limit",
        type=int,
        default=DEFAULT_GH_PR_LIST_LIMIT,  # Default from constant
        help=f"Maximum number of recent GitHub Pull Requests to list (default: {DEFAULT_GH_PR_LIST_LIMIT})",
    )
    parser.add_argument(
        "--release-limit",
        type=int,
        default=DEFAULT_GH_RELEASE_LIST_LIMIT,  # Default from constant
        help=f"Maximum number of recent GitHub Releases to list (default: {DEFAULT_GH_RELEASE_LIST_LIMIT})",
    )
    parser.add_argument(
        "--project-number",
        dest="gh_project_number",
        default=DEFAULT_GH_PROJECT_NUMBER,  # Default from constant
        help=f"GitHub Project number to fetch items from (default: {DEFAULT_GH_PROJECT_NUMBER})",
    )
    parser.add_argument(
        "--project-owner",
        dest="gh_project_owner",
        default=DEFAULT_GH_PROJECT_OWNER,  # Default from constant
        help=f"Owner of the GitHub Project (@me, org_name, user_name) (default: {DEFAULT_GH_PROJECT_OWNER})",
    )
    parser.add_argument(
        "--project-status-field",
        dest="gh_project_status_field",
        default=DEFAULT_GH_PROJECT_STATUS_FIELD_NAME,  # Default from constant
        help=f"Name of the status field in the GitHub Project (default: '{DEFAULT_GH_PROJECT_STATUS_FIELD_NAME}')",
    )
    return parser


# --- Ponto de Entrada do Script (sem alterações) ---
if __name__ == "__main__":
    # Configura e processa argumentos primeiro
    arg_parser = setup_arg_parser()
    args = arg_parser.parse_args()

    print("Iniciando a coleta de contexto para o LLM...")
    print(
        f"Versão do Script: {Path(__file__).name} v1.7 (Copies Manifest JSON)"
    )  # Versão atualizada

    essential_cmds = ["git", "php"]
    missing_essential = [cmd for cmd in essential_cmds if not command_exists(cmd)]
    if missing_essential:
        print(
            f"ERRO FATAL: Comandos essenciais não encontrados: {', '.join(missing_essential)}. Instale-os.",
            file=sys.stderr,
        )
        sys.exit(1)

    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    # Usa o diretório base fornecido pelo argumento
    timestamp_dir_path = args.output_dir / timestamp_str
    try:
        timestamp_dir_path.mkdir(parents=True, exist_ok=True)
        print(f"Diretório de saída: {timestamp_dir_path.resolve()}")
    except OSError as e:
        print(
            f"ERRO FATAL: Não foi possível criar o diretório de saída '{timestamp_dir_path}'. Erro: {e}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Passa os argumentos parseados para a função principal
    run_all_collections(timestamp_dir_path, timestamp_str, args)

    print("\n" + "-" * 50)
    print("Coleta de contexto para LLM concluída!")
    print(f"Arquivos salvos em: {timestamp_dir_path.resolve()}")
    print(
        f"Consulte '{timestamp_dir_path.relative_to(BASE_DIR)}/manifest.md' para um resumo."
    )
    print("-" * 50)
    sys.exit(0)
