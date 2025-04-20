#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ==============================================================================
# generate_context.py (v1.5 - Corrige NameError em argparse e melhora estrutura)
#
# Coleta informações de contexto abrangentes de um projeto de desenvolvimento
# (com foco em Laravel/PHP e Python) e seu ambiente para auxiliar LLMs.
#
# Permite configurar diretório de saída, limites de listagem e detalhes
# do projeto GitHub via argumentos de linha de comando.
# Inclui execução opcional de Dusk tests.
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
#   - lsb_release
# ==============================================================================

import argparse # Importado para argumentos CLI
import datetime
import json
import os
import platform
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
DEFAULT_OUTPUT_BASE_DIR = BASE_DIR / "context_llm/code" # Default output base
EMPTY_TREE_COMMIT = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
PHPSTAN_BIN = BASE_DIR / "vendor/bin/phpstan"
ARTISAN_CMD = ['php', str(BASE_DIR / 'artisan')]
PINT_BIN = BASE_DIR / "vendor/bin/pint"
GH_ISSUE_JSON_FIELDS = "number,title,body,author,state,stateReason,assignees,labels,comments"
DEFAULT_TREE_DEPTH = 3
CLOC_EXCLUDE_REGEX = r'(vendor|node_modules|storage|public/build|\.git|\.idea|\.vscode|\.fleet|context_llm)'
TREE_IGNORE_PATTERN = 'vendor|node_modules|storage/framework|storage/logs|public/build|.git|.idea|.vscode|.fleet|context_llm'
DEFAULT_GH_ISSUE_LIST_LIMIT = 500
DEFAULT_GIT_TAG_LIMIT = 10
DEFAULT_GH_RUN_LIST_LIMIT = 10
DEFAULT_GH_PR_LIST_LIMIT = 20
DEFAULT_GH_RELEASE_LIST_LIMIT = 10
DEFAULT_GH_PROJECT_NUMBER = os.getenv('GH_PROJECT_NUMBER', "1")
DEFAULT_GH_PROJECT_OWNER = os.getenv('GH_PROJECT_OWNER', "@me")
DEFAULT_GH_PROJECT_STATUS_FIELD_NAME = os.getenv('GH_PROJECT_STATUS_FIELD_NAME',"Status")

PHPUNIT_OUTPUT_FILE_NAME = "phpunit_test_results.txt"
DUSK_OUTPUT_FILE_NAME = "dusk_test_results.txt"
DUSK_INFO_FILE_NAME = "dusk_test_info.txt"

TOTAL_STEPS = 16

# --- Find Commands (Helper) ---
def find_command(primary: str, fallback: str) -> Optional[str]:
    if shutil.which(primary): return primary
    if shutil.which(fallback): return fallback
    return None

PYTHON_CMD = find_command("python3", "python")
PIP_CMD = find_command("pip3", "pip")

# --- Helper Functions (unchanged from v1.3) ---
def command_exists(cmd: str) -> bool: return shutil.which(cmd) is not None
def suggest_install(cmd_name: str, pkg_name: Optional[str] = None) -> None:
    pkg = pkg_name or cmd_name; print(f"  AVISO: Comando '{cmd_name}' não encontrado.", file=sys.stderr); print(f"  > Para coletar esta informação, tente instalar o pacote '{pkg}'.", file=sys.stderr)
    if command_exists('apt'): print(f"  > Sugestão (Debian/Ubuntu): sudo apt update && sudo apt install -y {pkg}", file=sys.stderr)
    elif command_exists('dnf'): print(f"  > Sugestão (Fedora): sudo dnf install -y {pkg}", file=sys.stderr)
    elif command_exists('yum'): print(f"  > Sugestão (RHEL/CentOS): sudo yum install -y {pkg}", file=sys.stderr)
    elif command_exists('pacman'): print(f"  > Sugestão (Arch): sudo pacman -Syu --noconfirm {pkg}", file=sys.stderr)
    elif command_exists('brew'): print(f"  > Sugestão (macOS): brew install {pkg}", file=sys.stderr)
    elif command_exists('zypper'): print(f"  > Sugestão (openSUSE): sudo zypper install -y {pkg}", file=sys.stderr)
    else: print(f"  > Verifique o gerenciador de pacotes do seu sistema para instalar '{pkg}'.", file=sys.stderr)

def run_command(cmd_list: List[str], output_file: Path, cwd: Path = BASE_DIR, check: bool = False, shell: bool = False, timeout: Optional[int] = 300) -> Tuple[int, str, str]:
    cmd_str = shlex.join(cmd_list) if not shell else " ".join(cmd_list); print(f"    Executing: {cmd_str}...")
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True); process = subprocess.run(cmd_list if not shell else cmd_str, capture_output=True, text=True, check=check, cwd=cwd, shell=shell, timeout=timeout)
        stdout = process.stdout or ""; stderr = process.stderr or ""; exit_code = process.returncode; output_content = stdout
        if exit_code != 0 and not check: print(f"    AVISO: Comando finalizado com código {exit_code}. Stderr: {stderr.strip()}", file=sys.stderr); output_content += f"\n\n--- COMMAND FAILED (Exit Code: {exit_code}) ---\nStderr:\n{stderr}"
        if output_content and not output_content.endswith('\n'): output_content += '\n'
        output_file.write_text(output_content, encoding='utf-8')
        if exit_code == 0 or not check: print(f"    Output saved to: {output_file.name}")
        return exit_code, stdout.strip(), stderr.strip()
    except FileNotFoundError: error_msg = f"Comando não encontrado: {cmd_list[0]}"; print(f"    ERRO: {error_msg}", file=sys.stderr); output_file.write_text(f"ERRO: {error_msg}\n", encoding='utf-8'); return 1, "", error_msg
    except subprocess.TimeoutExpired: error_msg = f"Comando excedeu o tempo limite de {timeout} segundos: {cmd_str}"; print(f"    ERRO: {error_msg}", file=sys.stderr); output_file.write_text(f"ERRO: {error_msg}\n", encoding='utf-8'); return 1, "", error_msg
    except subprocess.CalledProcessError as e: error_msg = f"Comando falhou (Exit Code: {e.returncode})"; stderr_content = e.stderr or ""; stdout_content = e.stdout or ""; print(f"    ERRO: {error_msg}. Stderr: {stderr_content.strip()}", file=sys.stderr); output_file.write_text(f"ERRO: {error_msg}\nStderr:\n{stderr_content}\nStdout:\n{stdout_content}\n", encoding='utf-8'); return e.returncode, stdout_content.strip(), stderr_content.strip()
    except Exception as e: error_msg = f"Erro inesperado ao executar '{cmd_str}': {e}"; print(f"    ERRO: {error_msg}", file=sys.stderr); traceback.print_exc(file=sys.stderr); output_file.write_text(f"ERRO: {error_msg}\n{traceback.format_exc()}\n", encoding='utf-8'); return 1, "", str(e)

# --- Collection Functions (unchanged, but now receive args object) ---
def collect_env_info(output_dir: Path, step_num: int, total_steps: int):
    print(f"[{step_num}/{total_steps}] Coletando informações do Ambiente (SO, PHP, Node)...")
    run_command(['uname', '-a'], output_dir / "env_uname.txt")
    if command_exists('lsb_release'): run_command(['lsb_release', '-a'], output_dir / "env_distro_info.txt")
    elif (Path('/etc/os-release')).is_file():
        try: shutil.copy2('/etc/os-release', output_dir / "env_distro_info.txt"); print("    Distro info copied from /etc/os-release.")
        except Exception as e: print(f"    Erro ao copiar /etc/os-release: {e}", file=sys.stderr); (output_dir / "env_distro_info.txt").write_text(f"Erro ao copiar /etc/os-release: {e}\n")
    else: (output_dir / "env_distro_info.txt").write_text("Não foi possível determinar a distribuição Linux automaticamente.\n")
    if command_exists('php'): run_command(['php', '-v'], output_dir / "env_php_version.txt"); run_command(['php', '-m'], output_dir / "env_php_modules.txt")
    else: suggest_install("php", "php-cli"); (output_dir / "env_php_version.txt").write_text("Comando 'php' não encontrado.\n"); (output_dir / "env_php_modules.txt").write_text("Comando 'php' não encontrado.\n")
    if command_exists('node'): run_command(['node', '-v'], output_dir / "env_node_version.txt")
    else: suggest_install("node", "nodejs"); (output_dir / "env_node_version.txt").write_text("Node não encontrado.\n")
    if command_exists('npm'): run_command(['npm', '-v'], output_dir / "env_npm_version.txt")
    else: suggest_install("npm"); (output_dir / "env_npm_version.txt").write_text("NPM não encontrado.\n")

def collect_python_env_info(output_dir: Path, step_num: int, total_steps: int):
    print(f"[{step_num}/{total_steps}] Coletando informações do Ambiente Python...")
    if PYTHON_CMD: run_command([PYTHON_CMD, '--version'], output_dir / "env_python_version.txt"); run_command(['which', PYTHON_CMD], output_dir / "env_python_which.txt")
    else: suggest_install("python3 or python", "python3"); (output_dir / "env_python_version.txt").write_text("Python não encontrado.\n"); (output_dir / "env_python_which.txt").write_text("Python não encontrado.\n")
    if PIP_CMD: run_command([PIP_CMD, '--version'], output_dir / "env_pip_version.txt"); run_command([PIP_CMD, 'freeze'], output_dir / "env_pip_freeze.txt")
    else: suggest_install("pip3 or pip", "python3-pip"); (output_dir / "env_pip_version.txt").write_text("Pip não encontrado.\n"); (output_dir / "env_pip_freeze.txt").write_text("Pip não encontrado.\n")
    venv_status = "Ambiente virtual Python ATIVO: " + os.environ['VIRTUAL_ENV'] if 'VIRTUAL_ENV' in os.environ else "Nenhum ambiente virtual Python detectado (variável VIRTUAL_ENV não definida)."
    (output_dir / "env_python_venv_status.txt").write_text(venv_status + "\n")
    print("  Coletando arquivos de gerenciamento de pacotes Python (se existirem)...")
    for pkg_file in ["requirements.txt", "requirements-dev.txt", "Pipfile", "pyproject.toml"]:
        src_path = BASE_DIR / pkg_file
        if src_path.is_file():
            dest_path = output_dir / f"env_python_pkgfile_{pkg_file.replace('/', '_')}"
            try: shutil.copy2(src_path, dest_path); print(f"    Capturando {pkg_file}...")
            except Exception as e: print(f"    Erro ao copiar {pkg_file}: {e}", file=sys.stderr); dest_path.write_text(f"Erro ao ler {pkg_file}: {e}\n")
        else: print(f"    Arquivo {pkg_file} não encontrado.")

def collect_git_info(output_dir: Path, args: argparse.Namespace, step_num: int, total_steps: int):
    print(f"[{step_num}/{total_steps}] Coletando informações do Git...")
    if not command_exists('git'): print("   ERRO FATAL: Comando 'git' não encontrado. Saindo.", file=sys.stderr); sys.exit(1)
    git_log_format = "commit %H%nAuthor: %an <%ae>%nDate:   %ad%n%n%w(0,4)%s%n%n%w(0,4,4)%b%n"
    run_command(['git', 'log', f'--pretty=format:{git_log_format}'], output_dir / "git_log.txt")
    run_command(['git', 'diff', f'{EMPTY_TREE_COMMIT}..HEAD'], output_dir / "git_diff_empty_tree_to_head.txt")
    run_command(['git', 'diff', '--cached'], output_dir / "git_diff_cached.txt")
    run_command(['git', 'diff'], output_dir / "git_diff_unstaged.txt")
    run_command(['git', 'status'], output_dir / "git_status.txt")
    run_command(['git', 'ls-files'], output_dir / "git_ls_files.txt")
    exit_code, stdout, _ = run_command(['git', 'tag', '--sort=-creatordate'], output_dir / "git_recent_tags.txt")
    if exit_code == 0 and stdout:
        lines = stdout.strip().split('\n')
        (output_dir / "git_recent_tags.txt").write_text('\n'.join(lines[:args.tag_limit]) + '\n') # Use args.tag_limit
        print(f"    {min(len(lines), args.tag_limit)} tags recentes salvas.")
    elif exit_code == 0: (output_dir / "git_recent_tags.txt").write_text("Nenhuma tag encontrada.\n")

def collect_gh_info(output_dir: Path, args: argparse.Namespace, step_num: int, total_steps: int):
    print(f"[{step_num}/{total_steps}] Coletando contexto adicional do GitHub (Repo, Actions, Security)...")
    if not command_exists('gh'):
        suggest_install("gh"); print("  AVISO: Comando 'gh' não encontrado. Pulando esta seção.", file=sys.stderr)
        for fname in ["gh_run_list.txt", "gh_workflow_list.txt", "gh_pr_list.txt", "gh_release_list.txt", "gh_secret_list.txt", "gh_variable_list.txt", "gh_repo_view.txt", "gh_ruleset_list.txt"]: (output_dir / fname).write_text("gh não encontrado.\n")
        return
    # Use args for limits
    run_command(['gh', 'run', 'list', '--limit', str(args.run_limit)], output_dir / "gh_run_list.txt")
    run_command(['gh', 'workflow', 'list'], output_dir / "gh_workflow_list.txt")
    run_command(['gh', 'pr', 'list', '--state', 'all', '--limit', str(args.pr_limit)], output_dir / "gh_pr_list.txt")
    run_command(['gh', 'release', 'list', '--limit', str(args.release_limit)], output_dir / "gh_release_list.txt")
    run_command(['gh', 'secret', 'list'], output_dir / "gh_secret_list.txt")
    run_command(['gh', 'variable', 'list'], output_dir / "gh_variable_list.txt")
    run_command(['gh', 'repo', 'view'], output_dir / "gh_repo_view.txt")
    run_command(['gh', 'ruleset', 'list'], output_dir / "gh_ruleset_list.txt")

def collect_gh_project_info(output_dir: Path, args: argparse.Namespace, step_num: int, total_steps: int):
    print(f"[{step_num}/{total_steps}] Coletando Status do GitHub Project...")
    status_file = output_dir / "gh_project_items_status.json"; summary_file = output_dir / "gh_project_items_summary.json"; error_log = output_dir / "gh_project_items_summary.error.log"
    project_num = args.gh_project_number; project_owner = args.gh_project_owner; status_field = args.gh_project_status_field
    if not command_exists('gh'): suggest_install("gh"); print("  AVISO: Comando 'gh' não encontrado. Pulando esta seção.", file=sys.stderr); status_file.write_text('{"error": "gh command not found"}\n'); summary_file.write_text('{"error": "gh command not found"}\n'); return
    if not project_num or not project_owner: msg = "Número ou proprietário do projeto GitHub não especificado via argumentos (--project-number, --project-owner)."; print(f"  AVISO: {msg} Pulando esta seção.", file=sys.stderr); status_file.write_text(json.dumps({"error": msg}) + "\n"); summary_file.write_text(json.dumps({"error": msg}) + "\n"); return
    print(f"  Coletando itens do Projeto #{project_num} (Owner: {project_owner})..."); cmd_list = ['gh', 'project', 'item-list', str(project_num), '--owner', project_owner, '--format', 'json']; exit_code, stdout_gh, stderr_gh = run_command(cmd_list, status_file, check=False)
    if exit_code != 0: print(f"  ERRO: Falha ao coletar itens do projeto (Código: {exit_code}). Erro salvo em {status_file.name}.", file=sys.stderr); summary_file.write_text(json.dumps({"error": f"Failed to list project items. Exit code: {exit_code}", "stderr": stderr_gh}) + "\n"); return
    if not command_exists('jq'): suggest_install("jq"); msg = "jq não encontrado para gerar resumo."; print(f"  AVISO: '{msg}'", file=sys.stderr); summary_file.write_text(json.dumps({"error": msg}) + "\n"); return
    if not stdout_gh or stdout_gh.strip() == "null" or stdout_gh.strip() == "": error_msg = "Comando gh project item-list retornou vazio ou nulo. Não é possível gerar resumo."; print(f"  AVISO: {error_msg}", file=sys.stderr); summary_file.write_text(json.dumps({"error": error_msg}) + "\n"); return

def collect_artisan_info(output_dir: Path, step_num: int, total_steps: int):
    print(f"[{step_num}/{total_steps}] Coletando informações do Laravel Artisan...")
    if not command_exists('php') or not (BASE_DIR / 'artisan').is_file(): print("  AVISO: Comando 'php' ou arquivo 'artisan' não encontrado. Pulando comandos Artisan.", file=sys.stderr); return
    code, _, _ = run_command(ARTISAN_CMD + ['route:list', '--json'], output_dir / "artisan_route_list.json");
    if code != 0: run_command(ARTISAN_CMD + ['route:list'], output_dir / "artisan_route_list.txt")
    code, _, _ = run_command(ARTISAN_CMD + ['about', '--json'], output_dir / "artisan_about.json");
    if code != 0: run_command(ARTISAN_CMD + ['about'], output_dir / "artisan_about.txt")
    code, _, _ = run_command(ARTISAN_CMD + ['db:show', '--json'], output_dir / "artisan_db_show.json");
    if code != 0: run_command(ARTISAN_CMD + ['db:show'], output_dir / "artisan_db_show.txt")
    run_command(ARTISAN_CMD + ['channel:list'], output_dir / "artisan_channel_list.txt")
    run_command(ARTISAN_CMD + ['event:list'], output_dir / "artisan_event_list.txt")
    run_command(ARTISAN_CMD + ['permission:show'], output_dir / "artisan_permission_show.txt")
    run_command(ARTISAN_CMD + ['queue:failed'], output_dir / "artisan_queue_failed.txt")
    run_command(ARTISAN_CMD + ['schedule:list'], output_dir / "artisan_schedule_list.txt")
    run_command(ARTISAN_CMD + ['env'], output_dir / "artisan_env.txt")
    run_command(ARTISAN_CMD + ['migrate:status'], output_dir / "artisan_migrate_status.txt")
    run_command(ARTISAN_CMD + ['config:show', 'app'], output_dir / "artisan_config_show_app.txt")
    run_command(ARTISAN_CMD + ['config:show', 'database'], output_dir / "artisan_config_show_database.txt")

def collect_dependency_info(output_dir: Path, step_num: int, total_steps: int):
    print(f"[{step_num}/{total_steps}] Coletando informações de Dependências (Composer, NPM)...")
    if command_exists('composer'): run_command(['composer', 'show'], output_dir / "composer_show.txt")
    else: suggest_install("composer"); (output_dir / "composer_show.txt").write_text("Composer não encontrado.\n")
    if command_exists('npm'): run_command(['npm', 'list', '--depth=0'], output_dir / "npm_list_depth0.txt")
    else: suggest_install("npm"); (output_dir / "npm_list_depth0.txt").write_text("NPM não encontrado.\n")

def collect_structure_info(output_dir: Path, args: argparse.Namespace, step_num: int, total_steps: int):
    print(f"[{step_num}/{total_steps}] Coletando informações da Estrutura do Projeto...")
    tree_file = output_dir / f"project_tree_L{args.tree_depth}.txt" # Use args
    if command_exists('tree'): run_command(['tree', '-L', str(args.tree_depth), '-a', '-I', TREE_IGNORE_PATTERN], tree_file)
    else: suggest_install("tree"); tree_file.write_text("Comando 'tree' não encontrado.\n")
    cloc_file = output_dir / "project_cloc.txt"
    if command_exists('cloc'): run_command(['cloc', '.', '--fullpath', f'--not-match-d={CLOC_EXCLUDE_REGEX}'], cloc_file)
    else: suggest_install("cloc"); cloc_file.write_text("Comando 'cloc' não encontrado.\n")

def copy_project_files(output_dir: Path, step_num: int, total_steps: int):
    print(f"[{step_num}/{total_steps}] Copiando Planos e Meta-Prompts...") # Combined step number
    dirs_to_copy = { "planos": BASE_DIR / "planos", "meta-prompts": BASE_DIR / "templates" / "meta-prompts" }
    for name, src_dir in dirs_to_copy.items():
        if src_dir.is_dir():
            print(f"  Copiando arquivos de '{src_dir.relative_to(BASE_DIR)}'...")
            copied_count = 0
            for src_file in src_dir.glob('*.txt'):
                if src_file.is_file():
                    try: shutil.copy2(src_file, output_dir / src_file.name); copied_count += 1
                    except Exception as e: print(f"    Erro ao copiar {src_file.name}: {e}", file=sys.stderr)
            if copied_count == 0: print(f"    Nenhum arquivo .txt encontrado em {name}/")
        else: print(f"  Diretório '{src_dir.relative_to(BASE_DIR)}' não encontrado.")

def collect_github_issue_details(output_dir: Path, args: argparse.Namespace, step_num: int, total_steps: int):
     print(f"[{step_num}/{total_steps}] Coletando detalhes das Issues do GitHub (gh)...")
     issues_dir = output_dir
     if not command_exists('gh') or not command_exists('jq'): print("  AVISO: 'gh' ou 'jq' não encontrado. Pulando coleta de issues.", file=sys.stderr); (issues_dir / "github_issues_skipped.log").write_text("gh ou jq não encontrado.\n"); return
     print(f"  Issues serão salvas em: {issues_dir.relative_to(BASE_DIR)}")
     print(f"  Listando e filtrando issues (limite: {args.issue_limit}, excluindo 'Closed as not planned')...") # Use args
     list_cmd = ['gh', 'issue', 'list', '--state', 'all', '--limit', str(args.issue_limit), '--json', 'number,stateReason']
     try:
         list_process = subprocess.run(list_cmd, capture_output=True, text=True, check=True, cwd=BASE_DIR)
         jq_filter = '[.[] | select(.stateReason != "NOT_PLANNED") | .number]'
         jq_process = subprocess.run(['jq', '-c', jq_filter], input=list_process.stdout, text=True, check=True, capture_output=True)
         issue_numbers = json.loads(jq_process.stdout)
     except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as e: print(f"  AVISO: Falha ao listar/filtrar issues: {e}", file=sys.stderr); (issues_dir / "github_issues_error.log").write_text(f"Falha ao listar/filtrar issues: {e}\n"); return
     if not issue_numbers: print("  Nenhuma issue encontrada (após filtrar)."); (issues_dir / "no_issues_found.json").write_text('{ "message": "Nenhuma issue encontrada (após filtrar)." }\n'); return
     print(f"  Encontradas {len(issue_numbers)} issues para baixar detalhes...")
     downloaded_count = 0
     for issue_number in issue_numbers:
         print(f"    Coletando detalhes da Issue #{issue_number}...")
         issue_output_file = issues_dir / f"github_issue_{issue_number}_details.json"
         view_cmd = ['gh', 'issue', 'view', str(issue_number), '--json', GH_ISSUE_JSON_FIELDS]
         exit_code, _, stderr_view = run_command(view_cmd, issue_output_file, check=False)
         if exit_code == 0: downloaded_count += 1
         else: print(f"    AVISO: Falha ao coletar detalhes da Issue #{issue_number} (Código: {exit_code}).", file=sys.stderr)
         time.sleep(0.2)
     print(f"  Coleta de {downloaded_count}/{len(issue_numbers)} issues concluída.")

def run_quality_checks(output_dir: Path, step_num: int, total_steps: int):
    print(f"[{step_num}/{total_steps}] Executando análise estática com PHPStan...")
    if PHPSTAN_BIN.is_file() and os.access(PHPSTAN_BIN, os.X_OK): run_command([str(PHPSTAN_BIN), 'analyse', '--no-progress'], output_dir / "phpstan_analysis.txt")
    else: suggest_install("PHPStan/Larastan", "larastan/larastan --dev"); (output_dir / "phpstan_analysis.txt").write_text(f"PHPStan não executado: Binário não encontrado ou não executável em {PHPSTAN_BIN}\n")
    print(f"[{step_num+1}/{total_steps}] Verificando estilo de código com Pint...")
    pint_file = output_dir / "pint_test_results.txt"
    if PINT_BIN.is_file() and os.access(PINT_BIN, os.X_OK):
        exit_code, _, _ = run_command([str(PINT_BIN), '--test'], pint_file)
        if exit_code != 0:
             with open(pint_file, "a", encoding="utf-8") as f: f.write(f"\n\n--- Pint Exit Code: {exit_code} ---\n")
             print(f"  AVISO: Verificação Pint falhou/encontrou problemas (Código: {exit_code}).", file=sys.stderr)
    else: suggest_install("Laravel Pint", "laravel/pint --dev"); pint_file.write_text(f"Pint não executado: Binário não encontrado ou não executável em {PINT_BIN}\n")

def run_tests(output_dir: Path, step_num: int, total_steps: int):
    print(f"[{step_num}/{total_steps}] Executando testes PHPUnit (php artisan test)...")
    phpunit_output_file = output_dir / PHPUNIT_OUTPUT_FILE_NAME
    if (BASE_DIR / 'artisan').is_file() and command_exists('php'):
        exit_code, _, _ = run_command(ARTISAN_CMD + ['test', '--env=testing'], phpunit_output_file)
        with open(phpunit_output_file, "a", encoding="utf-8") as f:
             f.write(f"\n\n--- PHPUnit Exit Code: {exit_code} ---")
             if exit_code != 0: f.write(f"\n  -> Revise o arquivo '{PHPUNIT_OUTPUT_FILE_NAME}' para detalhes da falha.")
        if exit_code != 0: print(f"  AVISO: Testes PHPUnit falharam (Código: {exit_code}). Veja {phpunit_output_file.name}.", file=sys.stderr)
    else: print("  AVISO: Arquivo 'artisan' ou comando 'php' não encontrado. Pulando testes PHPUnit.", file=sys.stderr); phpunit_output_file.write_text("Comando 'php artisan test' não executado: PHP ou artisan não encontrado.\n")

def run_dusk_tests(output_dir: Path, step_num: int, total_steps: int):
    print(f"[{step_num}/{total_steps}] Executando testes Dusk (php artisan dusk)...")
    dusk_output_file = output_dir / DUSK_OUTPUT_FILE_NAME
    dusk_env_file = BASE_DIR / ".env.dusk.local"
    if not (BASE_DIR / 'artisan').is_file() or not command_exists('php'): print("  AVISO: Arquivo 'artisan' ou comando 'php' não encontrado. Pulando testes Dusk.", file=sys.stderr); dusk_output_file.write_text("Comando 'php artisan dusk' não executado: PHP ou artisan não encontrado.\n"); return
    if not dusk_env_file.is_file(): print(f"  AVISO: Arquivo de ambiente Dusk '{dusk_env_file.name}' não encontrado. Os testes Dusk podem falhar ou usar configuração incorreta.", file=sys.stderr)
    print("  ASSUMINDO que o ChromeDriver está rodando manualmente na porta 9515 (ou configurada em DUSK_DRIVER_URL no .env.dusk.local).")
    print("  ASSUMINDO que o servidor da aplicação (ex: php artisan serve) está rodando na URL correta (ex: http://127.0.0.1:8000).")
    exit_code, _, stderr = run_command(ARTISAN_CMD + ['dusk'], dusk_output_file, check=False, timeout=600)
    try:
        with open(dusk_output_file, "a", encoding="utf-8") as f:
             f.write(f"\n\n--- Dusk Exit Code: {exit_code} ---")
             if exit_code != 0: f.write(f"\n  -> Revise o arquivo '{DUSK_OUTPUT_FILE_NAME}' e os diretórios tests/Browser/screenshots/ e tests/Browser/console/ para detalhes da falha.")
    except Exception as e: print(f"  ERRO: Não foi possível anexar o código de saída ao arquivo {dusk_output_file.name}: {e}", file=sys.stderr)
    if exit_code == 0: print(f"  Testes Dusk executados com sucesso (Código: 0). Veja {DUSK_OUTPUT_FILE_NAME}.")
    else: print(f"  AVISO: Testes Dusk falharam ou retornaram avisos (Código: {exit_code}). Veja {DUSK_OUTPUT_FILE_NAME}.", file=sys.stderr)

def create_dusk_note(output_dir: Path, step_num: int, total_steps: int):
    print(f"[{step_num}/{total_steps}] Criando arquivo de informação sobre testes Dusk...")
    dusk_info_file = output_dir / DUSK_INFO_FILE_NAME
    content = f"""
######################################################################
# NOTA IMPORTANTE SOBRE TESTES DUSK                                #
######################################################################

Este script ('generate_context.py') TENTA EXECUTAR os testes Laravel Dusk ('php artisan dusk') assumindo que o ChromeDriver e o servidor da aplicação estão rodando manualmente.

A saída desta tentativa de execução foi salva em '{DUSK_OUTPUT_FILE_NAME}'.

**Lembretes para execução manual (se necessário):**
1. Garanta que o servidor Laravel esteja rodando (ex: 'php artisan serve --port=8000').
2. Garanta que o ChromeDriver esteja rodando (ex: './vendor/laravel/dusk/bin/chromedriver-linux --port=9515').
3. Execute 'php artisan dusk' manualmente no terminal.
4. Execute 'generate_context.py' DEPOIS, se precisar capturar o estado *após* essa execução manual.

Os artefatos de falha (screenshots, console logs) ainda estarão nos diretórios padrão do Dusk ('tests/Browser/screenshots', 'tests/Browser/console').

######################################################################
"""
    try: dusk_info_file.write_text(content.strip() + "\n", encoding='utf-8'); print(f"  Arquivo '{DUSK_INFO_FILE_NAME}' criado com sucesso.")
    except Exception as e: print(f"  ERRO: Falha ao criar '{DUSK_INFO_FILE_NAME}': {e}", file=sys.stderr)

def generate_manifest(output_dir: Path, timestamp: str):
    print("[Final] Gerando arquivo de manifesto...")
    manifest_file = output_dir / "manifest.md"
    try:
        with open(manifest_file, 'w', encoding='utf-8') as f:
            f.write(f"# Manifesto de Contexto - Gerado por {Path(__file__).name} v1.4\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Diretório: ./{output_dir.relative_to(BASE_DIR)}\n\n")
            f.write("## Conteúdo Coletado:\n")
            files_in_dir = sorted([item.name for item in output_dir.iterdir() if item.is_file() and item.name != "manifest.md"])
            for filename in files_in_dir: f.write(f" - {filename}\n")
            f.write("\n## Notas:\n")
            f.write("- Revise os arquivos individuais para o contexto detalhado.\n")
            f.write(f"- '{PHPUNIT_OUTPUT_FILE_NAME}' contém a saída completa do comando 'php artisan test'.\n")
            f.write(f"- '{DUSK_OUTPUT_FILE_NAME}' contém a saída da tentativa de execução de 'php artisan dusk'.\n")
            f.write(f"- '{DUSK_INFO_FILE_NAME}' contém uma nota sobre a execução/pré-requisitos dos testes Dusk.\n")
            f.write("- O status dos itens no GitHub Project (se configurado e acessível) está em 'gh_project_items_*.json'.\n")
            f.write("- Alguns comandos podem ter falhado (verifique arquivos com mensagens de erro).\n")
            f.write("- A completude depende das ferramentas disponíveis (php, python, gh, jq, tree, cloc, composer, npm) e permissões.\n")
        print(f"  Manifesto gerado em: {manifest_file.name}")
    except Exception as e: print(f"  ERRO: Falha ao gerar o manifesto: {e}", file=sys.stderr); traceback.print_exc(file=sys.stderr)

# --- Função Principal Orchestrator (Adaptada para chamar as funções Python) ---
def run_all_collections(output_dir: Path, timestamp: str, args: argparse.Namespace):
    """Orchestrates all context collection steps, using args."""
    collect_env_info(output_dir, 1, TOTAL_STEPS)
    collect_python_env_info(output_dir, 2, TOTAL_STEPS)
    collect_git_info(output_dir, args, 3, TOTAL_STEPS)
    collect_gh_info(output_dir, args, 4, TOTAL_STEPS)
    collect_gh_project_info(output_dir, args, 5, TOTAL_STEPS)
    collect_artisan_info(output_dir, 6, TOTAL_STEPS)
    collect_dependency_info(output_dir, 7, TOTAL_STEPS)
    collect_structure_info(output_dir, args, 8, TOTAL_STEPS)
    copy_project_files(output_dir, 9, TOTAL_STEPS) # Step 9 & 10 combined
    collect_github_issue_details(output_dir, args, 11, TOTAL_STEPS)
    run_quality_checks(output_dir, 12, TOTAL_STEPS) # Step 12 & 13 combined
    run_tests(output_dir, 14, TOTAL_STEPS) # PHPUnit
    run_dusk_tests(output_dir, 15, TOTAL_STEPS) # Dusk
    create_dusk_note(output_dir, 16, TOTAL_STEPS)
    generate_manifest(output_dir, timestamp)

# --- Função para configurar e retornar o parser de argumentos ---
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
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '-o', '--output-dir', type=Path,
        # Correção: Usar a constante global DEFAULT aqui
        default=DEFAULT_OUTPUT_BASE_DIR,
        help=f"Base directory to save the context files (default: ./{DEFAULT_OUTPUT_BASE_DIR.relative_to(BASE_DIR)})"
    )
    parser.add_argument(
        '--tree-depth', type=int,
        default=DEFAULT_TREE_DEPTH, # Correção: Usar a constante global DEFAULT aqui
        help=f"Maximum depth for the 'tree' command (default: {DEFAULT_TREE_DEPTH})"
    )
    parser.add_argument(
        '--issue-limit', type=int,
        default=DEFAULT_GH_ISSUE_LIST_LIMIT, # Correção
        help=f"Maximum number of GitHub issues to fetch details for (default: {DEFAULT_GH_ISSUE_LIST_LIMIT})"
    )
    parser.add_argument(
        '--tag-limit', type=int,
        default=DEFAULT_GIT_TAG_LIMIT, # Correção
        help=f"Maximum number of recent Git tags to list (default: {DEFAULT_GIT_TAG_LIMIT})"
    )
    parser.add_argument(
        '--run-limit', type=int,
        default=DEFAULT_GH_RUN_LIST_LIMIT, # Correção
        help=f"Maximum number of recent GitHub Actions runs to list (default: {DEFAULT_GH_RUN_LIST_LIMIT})"
    )
    parser.add_argument(
        '--pr-limit', type=int,
        default=DEFAULT_GH_PR_LIST_LIMIT, # Correção
        help=f"Maximum number of recent GitHub Pull Requests to list (default: {DEFAULT_GH_PR_LIST_LIMIT})"
    )
    parser.add_argument(
        '--release-limit', type=int,
        default=DEFAULT_GH_RELEASE_LIST_LIMIT, # Correção
        help=f"Maximum number of recent GitHub Releases to list (default: {DEFAULT_GH_RELEASE_LIST_LIMIT})"
    )
    parser.add_argument(
        '--project-number', dest='gh_project_number',
        default=DEFAULT_GH_PROJECT_NUMBER, # Correção
        help=f"GitHub Project number to fetch items from (default: {DEFAULT_GH_PROJECT_NUMBER})"
    )
    parser.add_argument(
        '--project-owner', dest='gh_project_owner',
        default=DEFAULT_GH_PROJECT_OWNER, # Correção
        help=f"Owner of the GitHub Project (@me, org_name, user_name) (default: {DEFAULT_GH_PROJECT_OWNER})"
    )
    parser.add_argument(
        '--project-status-field', dest='gh_project_status_field',
        default=DEFAULT_GH_PROJECT_STATUS_FIELD_NAME, # Correção
        help=f"Name of the status field in the GitHub Project (default: '{DEFAULT_GH_PROJECT_STATUS_FIELD_NAME}')"
    )
    return parser

# --- Ponto de Entrada do Script ---
if __name__ == "__main__":
    # Configura e processa argumentos primeiro
    arg_parser = setup_arg_parser()
    args = arg_parser.parse_args()

    print("Iniciando a coleta de contexto para o LLM...")
    print(f"Versão do Script: {Path(__file__).name} v1.5 (Python Migration + Args Fix)") # Versão atualizada

    essential_cmds = ['git', 'php']
    missing_essential = [cmd for cmd in essential_cmds if not command_exists(cmd)]
    if missing_essential: print(f"ERRO FATAL: Comandos essenciais não encontrados: {', '.join(missing_essential)}. Instale-os.", file=sys.stderr); sys.exit(1)

    timestamp_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    # Usa o diretório base fornecido pelo argumento
    timestamp_dir_path = args.output_dir / timestamp_str
    try:
        timestamp_dir_path.mkdir(parents=True, exist_ok=True)
        print(f"Diretório de saída: {timestamp_dir_path.resolve()}")
    except OSError as e: print(f"ERRO FATAL: Não foi possível criar o diretório de saída '{timestamp_dir_path}'. Erro: {e}", file=sys.stderr); sys.exit(1)

    # Passa os argumentos parseados para a função principal
    run_all_collections(timestamp_dir_path, timestamp_str, args)

    print("\n" + "-"*50); print("Coleta de contexto para LLM concluída!"); print(f"Arquivos salvos em: {timestamp_dir_path.resolve()}"); print(f"Consulte '{timestamp_dir_path.relative_to(BASE_DIR)}/manifest.md' para um resumo."); print("-" * 50)
    sys.exit(0)