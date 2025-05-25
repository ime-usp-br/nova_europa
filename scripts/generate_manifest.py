#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ==============================================================================
# generate_manifest.py (v1.23.1 - Persist Context Summaries)
#
# Script para gerar um manifesto JSON estruturado do projeto, catalogando
# arquivos relevantes e extraindo metadados essenciais.
# Destinado a auxiliar ferramentas LLM e rastreamento de mudanças.
# Inclui contagem de tokens via API Gemini com fallback para estimativa.
# Adiciona cálculo de estimativa para arquivos .env* e context_llm/code/*.
# Adiciona fallback de estimativa para erros persistentes da API.
# PRESERVA o campo 'summary' do manifesto anterior se o hash do arquivo não mudou.
# NOVO: PERSISTE o summary para arquivos context_llm/code/* mesmo se o hash mudar.
#
# Uso:
#   python scripts/generate_manifest.py [-o output.json] [-i ignore_pattern] [-v] [--sleep SLEEP_SECONDS] [--timeout TIMEOUT_SECONDS]
#
# Argumentos:
#   -o, --output OUTPUT_PATH   Caminho para o arquivo JSON de saída.
#   -i, --ignore IGNORE_PATTERN Padrão (glob), diretório ou arquivo a ignorar.
#   -v, --verbose              Habilita logging mais detalhado.
#   --sleep SLEEP_SECONDS      Segundos de espera entre chamadas à API count_tokens (padrão: 0.5).
#   --timeout TIMEOUT_SECONDS  Timeout em segundos para a chamada API count_tokens (padrão: 6).
#   -h, --help                 Mostra esta mensagem de ajuda.
# ==============================================================================

import argparse
import concurrent.futures
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import traceback
import shlex
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from dotenv import load_dotenv

# Importa diretamente o google.genai
from google import genai
from google.genai import types
from google.genai import errors as google_genai_errors
from google.api_core import exceptions as google_api_core_exceptions
from tqdm import tqdm  # Adicionado para barra de progresso no sleep

# --- Constantes Globais ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "scripts" / "data"
TIMESTAMP_MANIFEST_REGEX = r"^\d{8}_\d{6}_manifest\.json$"
TIMESTAMP_DIR_REGEX = r"^\d{8}_\d{6}$"
CONTEXT_CODE_DIR = PROJECT_ROOT / "context_llm" / "code"
CONTEXT_COMMON_DIR = PROJECT_ROOT / "context_llm" / "common"
VENDOR_USPDEV_DIRS = [
    PROJECT_ROOT / "vendor/uspdev/replicado/src/",
    PROJECT_ROOT / "vendor/uspdev/senhaunica-socialite/src/",
]
DEFAULT_IGNORE_PATTERNS: Set[str] = {
    ".git/",
    ".vscode/",
    ".idea/",
    ".fleet/",
    "node_modules/",
    "storage/framework/cache/data/",
    "storage/framework/sessions/",
    "storage/framework/views/",
    "storage/logs/",
    "bootstrap/cache/",
    "public/build/",
    "*.lock",
    "*.sqlite",
    "*.sqlite-journal",
    "*.log",
    ".phpunit.cache/",
    "llm_outputs/",
    "scripts/data/",
    "*.DS_Store",
    "Thumbs.db",
    "vendor/",
    "context_llm/",  # context_llm/ base is ignored, specific subdirs are added later
}
BINARY_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".ico",
    ".tif",
    ".tiff",
    ".webp",
    ".mp3",
    ".wav",
    ".ogg",
    ".aac",
    ".flac",
    ".m4a",
    ".mp4",
    ".avi",
    ".mov",
    ".wmv",
    ".mkv",
    ".flv",
    ".zip",
    ".rar",
    ".7z",
    ".tar",
    ".gz",
    ".bz2",
    ".xz",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".odt",
    ".ods",
    ".odp",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".app",
    ".bin",
    ".o",
    ".a",
    ".sqlite",
    ".db",
    ".ttf",
    ".otf",
    ".woff",
    ".woff2",
    ".eot",
    ".pyc",
    ".phar",
    ".jar",
    ".class",
    ".swf",
    ".dat",
}
TEXTCHARS = bytes(range(32, 127)) + b"\n\r\t\f\b"
GEMINI_MODEL_NAME = "gemini-1.5-flash"  # Modelo para contagem de tokens
DEFAULT_INTER_CALL_SLEEP = 0.5
DEFAULT_RATE_LIMIT_SLEEP = 5.0
DEFAULT_API_TIMEOUT_SECONDS = 6

# --- Variáveis Globais ---
repo_owner: Optional[str] = None
GEMINI_API_KEYS_LIST: List[str] = []
current_api_key_index: int = 0
genai_client: Optional[genai.Client] = None
api_key_loaded: bool = False
gemini_initialized: bool = False
api_executor: Optional[concurrent.futures.ThreadPoolExecutor] = None


# --- Funções Auxiliares ---
# (Funções auxiliares como run_command, parse_arguments, setup_logging, get_default_output_filepath,
# find_latest_context_code_dir, is_likely_binary, load_api_keys, initialize_gemini,
# rotate_api_key_and_reinitialize, extract_php_dependencies, get_file_type,
# scan_project_files, filter_files, count_tokens_for_file, get_git_versioned_status
# permanecem essencialmente as mesmas da versão 1.23.0 - OMITIDAS PARA BREVIDADE,
# mas mantendo a lógica de tratamento de erros e logging)
def run_command(
    cmd_list: List[str],
    cwd: Path = PROJECT_ROOT,
    check: bool = True,
    capture: bool = True,
    input_data: Optional[str] = None,
    shell: bool = False,
    timeout: Optional[int] = 60,
) -> Tuple[int, str, str]:
    """Runs a subprocess command and returns exit code, stdout, stderr."""
    cmd_str = (
        shlex.join(cmd_list) if not shell else " ".join(map(shlex.quote, cmd_list))
    )
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
        return process.returncode, process.stdout or "", process.stderr or ""
    except FileNotFoundError:
        return 1, "", f"Command not found: {cmd_list[0]}"
    except subprocess.TimeoutExpired:
        return 1, "", f"Command timed out after {timeout}s: {cmd_str}"
    except subprocess.CalledProcessError as e:
        return e.returncode, e.stdout or "", e.stderr or ""
    except Exception as e:
        return 1, "", f"Unexpected error running command {cmd_str}: {e}"


def parse_arguments() -> argparse.Namespace:
    """Configura e processa os argumentos da linha de comando."""
    parser = argparse.ArgumentParser(
        description="Gera um manifesto JSON estruturado do projeto.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""Exemplos:\n  python {Path(__file__).name}\n  python {Path(__file__).name} -o build/manifest.json\n  python {Path(__file__).name} -i '*.tmp' -i 'docs/drafts/' -v --sleep 0.5 --timeout 15""",
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="output_path",
        type=str,
        default=None,
        help=f"Caminho para o arquivo JSON de saída. Padrão: {DEFAULT_OUTPUT_DIR.relative_to(PROJECT_ROOT)}/YYYYMMDD_HHMMSS_manifest.json",
    )
    parser.add_argument(
        "-i",
        "--ignore",
        dest="ignore_patterns",
        action="append",
        default=[],
        help="Padrão (glob), diretório ou arquivo a ignorar. Use múltiplas vezes.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Habilita logging mais detalhado."
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=DEFAULT_INTER_CALL_SLEEP,
        help=f"Segundos de espera entre chamadas à API count_tokens (padrão: {DEFAULT_INTER_CALL_SLEEP}).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_API_TIMEOUT_SECONDS,
        help=f"Timeout em segundos para a chamada API count_tokens (padrão: {DEFAULT_API_TIMEOUT_SECONDS}).",
    )
    return parser.parse_args()


def setup_logging(verbose: bool):
    if verbose:
        print("Modo verbose habilitado.")


def get_default_output_filepath() -> Path:
    """Gera o caminho padrão para o arquivo de saída com timestamp."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_manifest.json"
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_OUTPUT_DIR / filename


def find_latest_context_code_dir(context_base_dir: Path) -> Optional[Path]:
    """Encontra o diretório de contexto mais recente dentro do diretório base."""
    if not context_base_dir.is_dir():
        return None
    valid_context_dirs = [
        d
        for d in context_base_dir.iterdir()
        if d.is_dir() and re.match(TIMESTAMP_DIR_REGEX, d.name)
    ]
    if not valid_context_dirs:
        return None
    return sorted(valid_context_dirs, reverse=True)[0]


def is_likely_binary(file_path: Path, verbose: bool) -> bool:
    """Verifica se um arquivo é provavelmente binário."""
    if file_path.suffix.lower() in BINARY_EXTENSIONS:
        if verbose:
            print(
                f"      -> Binary Check (AC6): Positive (extension '{file_path.suffix}')"
            )
        return True
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(512)
        if not chunk:
            return False
        if b"\0" in chunk:
            if verbose:
                print(f"      -> Binary Check (AC6): Positive (null byte found)")
            return True
        non_text_count = sum(1 for byte in chunk if bytes([byte]) not in TEXTCHARS)
        proportion = non_text_count / len(chunk) if len(chunk) > 0 else 0
        is_bin = proportion > 0.30
        if is_bin and verbose:
            print(
                f"      -> Binary Check (AC6): Positive (high proportion of non-text bytes: {proportion:.1%})"
            )
        return is_bin
    except Exception as e:
        if verbose:
            print(
                f"      -> Binary Check (AC6): Error reading file for binary check: {e}",
                file=sys.stderr,
            )
        return False


def load_previous_manifest(data_dir: Path, verbose: bool) -> Dict[str, Any]:
    """Carrega o dicionário 'files' do manifesto anterior mais recente."""
    if not data_dir.is_dir():
        if verbose:
            print(
                "  Aviso: Diretório de dados do manifesto não encontrado, não é possível carregar dados anteriores."
            )
        return {}
    manifest_files = [
        f
        for f in data_dir.glob("*_manifest.json")
        if f.is_file() and re.match(TIMESTAMP_MANIFEST_REGEX, f.name)
    ]
    if not manifest_files:
        if verbose:
            print("  Aviso: Nenhum arquivo de manifesto anterior encontrado.")
        return {}
    latest_manifest_path = sorted(manifest_files, reverse=True)[0]
    if verbose:
        print(
            f"  Encontrado manifesto anterior: '{latest_manifest_path.relative_to(PROJECT_ROOT)}'"
        )
    try:
        with open(latest_manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if (
            isinstance(data, dict)
            and "files" in data
            and isinstance(data["files"], dict)
        ):
            if verbose:
                print(
                    f"  Manifesto anterior carregado com sucesso ({len(data['files'])} arquivos)."
                )
            return data["files"]
        else:
            if verbose:
                print(
                    "  Aviso: Formato inesperado no manifesto anterior ou chave 'files' ausente/inválida."
                )
            return {}
    except Exception as e:
        if verbose:
            print(
                f"  Erro ao carregar ou parsear manifesto anterior '{latest_manifest_path.name}': {e}",
                file=sys.stderr,
            )
        return {}


def get_git_versioned_status(filepath_relative: Path, verbose: bool) -> bool:
    """Checks if a specific file is tracked by Git using ls-files."""
    try:
        exit_code, _, stderr = run_command(
            ["git", "ls-files", "--error-unmatch", filepath_relative.as_posix()],
            check=False,
            capture=True,
        )
        return exit_code == 0
    except Exception as e:
        if verbose:
            print(
                f"      Warning: Error checking git status for {filepath_relative}: {e}",
                file=sys.stderr,
            )
        return False  # Assume not versioned on error


def scan_project_files(verbose: bool) -> Tuple[Set[Path], Set[Path]]:
    """Escaneia o projeto por arquivos, priorizando git e incluindo dirs específicos."""
    all_files_set: Set[Path] = set()
    if verbose:
        print("  Executando 'git ls-files -z -c -o --exclude-standard'...")
    exit_code_ls, stdout_ls, stderr_ls = run_command(
        ["git", "ls-files", "-z", "-c", "-o", "--exclude-standard"], check=False
    )
    if exit_code_ls == 0 and stdout_ls:
        tracked_paths = filter(None, stdout_ls.split("\0"))
        for path_str in tracked_paths:
            try:
                absolute_path = (PROJECT_ROOT / Path(path_str)).resolve(strict=True)
                if absolute_path.is_file() and absolute_path.is_relative_to(
                    PROJECT_ROOT
                ):
                    all_files_set.add(absolute_path.relative_to(PROJECT_ROOT))
            except Exception as e:
                if verbose:
                    print(
                        f"    Aviso: Ignorando path de 'git ls-files': {path_str} ({e})",
                        file=sys.stderr,
                    )
    else:
        print(
            f"  Aviso: 'git ls-files' falhou (Code: {exit_code_ls}). Stderr: {stderr_ls.strip()}",
            file=sys.stderr,
        )
    if verbose:
        print(f"  Arquivos iniciais via Git: {len(all_files_set)}")

    additional_scan_dirs: List[Path] = [CONTEXT_COMMON_DIR]
    latest_context_code_dir = find_latest_context_code_dir(CONTEXT_CODE_DIR)
    if latest_context_code_dir:
        additional_scan_dirs.append(latest_context_code_dir)
    additional_scan_dirs.extend(VENDOR_USPDEV_DIRS)
    additional_scan_dirs.append(PROJECT_ROOT / "docs" / "laravel_12")

    if verbose:
        print("  Realizando scans adicionais em diretórios específicos...")
    for scan_dir in additional_scan_dirs:
        abs_scan_dir = scan_dir.resolve(strict=False)
        if verbose:
            print(f"    Escaneando: {abs_scan_dir.relative_to(PROJECT_ROOT)}")
        if abs_scan_dir.is_dir():
            for item in abs_scan_dir.rglob("*"):
                try:
                    if item.is_file() and item.resolve(strict=True).is_relative_to(
                        PROJECT_ROOT
                    ):
                        relative_path = item.resolve(strict=True).relative_to(
                            PROJECT_ROOT
                        )
                        all_files_set.add(relative_path)
                except Exception as e:
                    if verbose:
                        print(
                            f"      Aviso: Ignorando item durante scan adicional: {item} ({e})",
                            file=sys.stderr,
                        )
        elif verbose:
            print(
                f"      Aviso: Diretório de scan adicional não existe: {abs_scan_dir}"
            )
    if verbose:
        print(
            f"  Total de arquivos únicos encontrados após scans: {len(all_files_set)}"
        )
    return all_files_set, set()  # versioned_files_set is now determined later


def filter_files(
    all_files: Set[Path],
    default_ignores: Set[str],
    custom_ignores: List[str],
    output_filepath: Path,
    verbose: bool,
) -> Set[Path]:
    """Filtra a lista de arquivos com base nos padrões de ignore."""
    filtered_files: Set[Path] = set()
    ignore_patterns = default_ignores.copy()
    ignore_patterns.update(custom_ignores)
    try:
        ignore_patterns.add(output_filepath.relative_to(PROJECT_ROOT).as_posix())
    except ValueError:
        pass  # output_filepath might be outside root

    if verbose:
        print(f"  Aplicando {len(ignore_patterns)} padrões de exclusão...")
    skipped_count = 0
    for file_path in all_files:
        file_path_str = file_path.as_posix()
        is_ignored = False
        for pattern in ignore_patterns:
            # --- START Special Handling Logic ---
            # Allow vendor/uspdev/*
            if pattern == "vendor/" and any(
                file_path_str.startswith(
                    str(usp_dir.relative_to(PROJECT_ROOT).as_posix())
                )
                for usp_dir in VENDOR_USPDEV_DIRS
            ):
                continue
            # Allow context_llm/common/* and context_llm/code/<latest>/*
            if pattern == "context_llm/":
                is_common = file_path_str.startswith(
                    str(CONTEXT_COMMON_DIR.relative_to(PROJECT_ROOT).as_posix())
                )
                latest_code_dir = find_latest_context_code_dir(CONTEXT_CODE_DIR)
                is_latest_code = latest_code_dir and file_path_str.startswith(
                    str(latest_code_dir.relative_to(PROJECT_ROOT).as_posix())
                )
                if is_common or is_latest_code:
                    continue
            # --- END Special Handling Logic ---

            # General Ignore Logic
            is_dir_pattern = pattern.endswith("/")
            cleaned_pattern = pattern.rstrip("/")
            if file_path_str == cleaned_pattern or (
                is_dir_pattern and file_path_str.startswith(cleaned_pattern + "/")
            ):
                is_ignored = True
                break
            try:
                if file_path.match(pattern):
                    is_ignored = True
                    break
            except Exception as e:
                if verbose:
                    print(
                        f"    Warning: Error matching pattern '{pattern}' for file '{file_path_str}': {e}",
                        file=sys.stderr,
                    )

        if not is_ignored:
            filtered_files.add(file_path)
        elif verbose:
            skipped_count += 1
    if verbose:
        print(
            f"  Filtro concluído. {len(filtered_files)} arquivos retidos, {skipped_count} ignorados."
        )
    return filtered_files


def get_file_type(relative_path: Path) -> str:
    """Determina um tipo granular para o arquivo baseado no caminho e extensão."""
    # (Código da função mantido como na sua implementação anterior, v1.22.0)
    path_str = relative_path.as_posix()
    parts = relative_path.parts
    name = relative_path.name
    suffix = relative_path.suffix.lower()
    if name == "composer.json":
        return "dependency_composer"
    if name == "package.json":
        return "dependency_npm"
    if name == "artisan":
        return "code_php_artisan"
    if name == "README.md":
        return "docs_readme"
    if name == "CHANGELOG.md":
        return "docs_changelog"
    if name == "LICENSE":
        return "docs_license"
    if name.startswith(".env"):
        return "environment_env"  # Alterado para detectar qualquer .env*
    if name == ".gitignore":
        return "config_git_ignore"
    if name == ".gitattributes":
        return "config_git_attributes"
    if name == ".editorconfig":
        return "config_editor"
    if name == "phpunit.xml":
        return "config_phpunit"
    if name == "phpstan.neon":
        return "config_phpstan"
    if name == "pint.json":
        return "config_pint"
    if name == "vite.config.js":
        return "config_vite"
    if name == "tailwind.config.js":
        return "config_tailwind"
    if name == "postcss.config.js":
        return "config_postcss"
    if parts[0] == "app":
        if suffix == ".php":
            if "Http/Controllers" in path_str:
                return "code_php_controller"
            if "Models" in path_str:
                return "code_php_model"
            if "Providers" in path_str:
                return "code_php_provider"
            if "Livewire/Forms" in path_str:
                return "code_php_livewire_form"
            if "Livewire/Actions" in path_str:
                return "code_php_action"
            if "Livewire" in path_str:
                return "code_php_livewire"
            if "View/Components" in path_str:
                return "code_php_view_component"
            if "Services" in path_str:
                return "code_php_service"
            if "Http/Middleware" in path_str:
                return "code_php_middleware"
            if "Http/Requests" in path_str:
                return "code_php_request"
            if "Console/Commands" in path_str:
                return "code_php_command"
            return "code_php_app"
    if parts[0] == "config" and suffix == ".php":
        return "config_laravel"
    if parts[0] == "database":
        if "migrations" in parts and suffix == ".php":
            return "migration_php"
        if "factories" in parts and suffix == ".php":
            return "code_php_factory"
        if "seeders" in parts and suffix == ".php":
            return "code_php_seeder"
    if parts[0] == "resources" and "views" in parts and suffix == ".blade.php":
        if "components" in parts:
            return "view_blade_component"
        return "view_blade"
    if parts[0] == "resources" and "css" in parts:
        return "asset_source_css"
    if parts[0] == "resources" and "js" in parts:
        return "asset_source_js"
    if parts[0] == "resources" and "images" in parts:
        return f"asset_source_image_{suffix[1:]}" if suffix else "asset_source_image"
    if parts[0] == "public" and suffix == ".php":
        return "code_php_public"
    if parts[0] == "public" and suffix in BINARY_EXTENSIONS:
        return f"asset_binary_{suffix[1:]}"
    if parts[0] == "public" and suffix == ".txt":
        return "asset_public"
    if parts[0] == "public" and name == ".htaccess":
        return "config_apache"  # Especificado o nome exato
    if parts[0] == "routes" and suffix == ".php":
        return "code_php_route"
    if parts[0] == "tests":
        if "Feature" in parts and suffix == ".php":
            return "test_php_feature"
        if "Unit" in parts and suffix == ".php":
            return "test_php_unit"
        if "Browser" in parts and suffix == ".php":
            return "test_php_dusk"
        if "Fakes" in parts and suffix == ".php":
            return "test_php_fake"
        if suffix == ".php":
            return "test_php"
    if parts[0] == "scripts":
        if suffix == ".py":
            return "code_python_script"
        if suffix == ".sh":
            return "code_shell_script"
    if (
        parts[0] == "docs"
        and len(parts) > 1
        and parts[1] == "laravel_12"
        and suffix == ".md"
    ):
        return "docs_laravel_api"
    if parts[0] == "docs":
        if "adr" in parts and suffix == ".md":
            return "docs_adr_md"
        if suffix == ".md":
            return "docs_md"
    if parts[0] == "planos" and suffix == ".txt":
        return "plan_text"
    if parts[0] == "templates":
        if "meta-prompts" in parts and suffix == ".txt":
            return "template_meta_prompt"
        if "prompts" in parts and suffix == ".txt":
            return "template_prompt"
        if "issue_bodies" in parts and suffix == ".md":
            return "template_issue_body"
    if path_str.startswith("vendor/uspdev/replicado/src/") and suffix == ".php":
        return "code_php_vendor_uspdev_replicado"
    if (
        path_str.startswith("vendor/uspdev/senhaunica-socialite/src/")
        and suffix == ".php"
    ):
        return "code_php_vendor_uspdev_senhaunica"
    if path_str.startswith("context_llm/common/"):
        return "context_common"
    if path_str.startswith("context_llm/code/") and len(parts) > 2:
        file_part = name.lower()
        if file_part == "git_log.txt":
            return "context_code_git_log"
        if file_part == "git_diff_cached.txt":
            return "context_code_git_diff_cached"
        if file_part == "git_diff_unstaged.txt":
            return "context_code_git_diff_unstaged"
        if file_part == "git_diff_empty_tree_to_head.txt":
            return "context_code_git_diff_tree"
        if file_part == "git_status.txt":
            return "context_code_git_status"
        if file_part == "git_ls_files.txt":
            return "context_code_git_lsfiles"
        if file_part == "git_recent_tags.txt":
            return "context_code_git_tags"
        if file_part.startswith("github_issue_") and file_part.endswith(
            "_details.json"
        ):
            return "context_code_issue_details"
        if file_part.startswith("artisan_"):
            return "context_code_artisan_output"
        if file_part.startswith("env_"):
            return "context_code_env_info"
        if file_part == "composer_show.txt":
            return "context_code_deps_composer"
        if file_part == "npm_list_depth0.txt":
            return "context_code_deps_npm"
        if file_part == "env_pip_freeze.txt":
            return "context_code_deps_pip"
        if file_part.startswith("project_tree_"):
            return "context_code_project_tree"
        if file_part == "project_cloc.txt":
            return "context_code_cloc"
        if file_part == "phpstan_analysis.txt":
            return "context_code_phpstan"
        if file_part == "pint_test_results.txt":
            return "context_code_pint"
        if file_part == "phpunit_test_results.txt":
            return "context_code_phpunit"
        if file_part == "dusk_test_results.txt":
            return "context_code_dusk_results"
        if file_part == "dusk_test_info.txt":
            return "context_code_dusk_info"
        if file_part == "manifest.md":
            return "context_code_manifest_md"
        if file_part.endswith("_manifest.json"):
            return "context_code_manifest_json"
        if file_part.startswith("gh_"):
            return "context_code_github_cli"
        # Catch-all for other copied files from planos/templates
        if any(p in path_str for p in ["/planos/", "/meta-prompts/", "/prompts/"]):
            return "context_code"
        return "context_code"  # Genérico para outros arquivos em context_llm/code/
    if suffix == ".php":
        return "code_php"
    if suffix == ".js":
        return "code_js"
    if suffix == ".py":
        return "code_python"
    if suffix == ".sh":
        return "code_shell"
    if suffix == ".json":
        return "config_json"
    if suffix in [".yaml", ".yml"]:
        return "config_yaml"
    if suffix == ".md":
        return "docs_md"
    if suffix == ".txt":
        return "text_plain"
    if suffix in BINARY_EXTENSIONS:
        return f"binary_{suffix[1:]}"
    return "unknown"


def load_api_keys(verbose: bool) -> bool:
    """Loads API keys from .env file."""
    global GEMINI_API_KEYS_LIST, api_key_loaded, current_api_key_index
    if api_key_loaded:
        return True
    dotenv_path = PROJECT_ROOT / ".env"
    if dotenv_path.is_file():
        if verbose:
            print(
                f"  Carregando variáveis de ambiente de: {dotenv_path.relative_to(PROJECT_ROOT)}"
            )
        load_dotenv(dotenv_path=dotenv_path, verbose=verbose, override=True)
    api_key_string = os.getenv("GEMINI_API_KEY")
    if not api_key_string:
        print(
            "Erro: Variável de ambiente GEMINI_API_KEY não encontrada.", file=sys.stderr
        )
        api_key_loaded = False
        return False
    GEMINI_API_KEYS_LIST = [
        key.strip() for key in api_key_string.split("|") if key.strip()
    ]
    if not GEMINI_API_KEYS_LIST:
        print(
            "Erro: Formato da GEMINI_API_KEY inválido ou vazio. Use '|' para separar múltiplas chaves.",
            file=sys.stderr,
        )
        api_key_loaded = False
        return False
    current_api_key_index = 0
    api_key_loaded = True
    if verbose:
        print(f"  {len(GEMINI_API_KEYS_LIST)} Chave(s) de API GEMINI carregadas.")
    return True


def initialize_gemini(verbose: bool) -> bool:
    """Initializes the Gemini client using the current API key."""
    global genai_client, gemini_initialized, GEMINI_API_KEYS_LIST, current_api_key_index
    if gemini_initialized:
        return True
    if (
        not api_key_loaded
        or not GEMINI_API_KEYS_LIST
        or not (0 <= current_api_key_index < len(GEMINI_API_KEYS_LIST))
    ):
        if verbose:
            print(
                "  Aviso: Chaves de API não carregadas ou índice inválido. Impossível inicializar Gemini."
            )
        return False
    active_key = GEMINI_API_KEYS_LIST[current_api_key_index]
    try:
        if verbose:
            print(
                f"  Inicializando Google GenAI Client com Key Index {current_api_key_index}..."
            )
        genai_client = genai.Client(api_key=active_key)
        print("  Google GenAI Client inicializado com sucesso.")
        gemini_initialized = True
        return True
    except Exception as e:
        print(
            f"Erro ao inicializar Google GenAI Client com Key Index {current_api_key_index}: {e}",
            file=sys.stderr,
        )
        if verbose:
            traceback.print_exc(file=sys.stderr)
        gemini_initialized = False
        return False


def rotate_api_key_and_reinitialize(verbose: bool) -> bool:
    """Rotates to the next API key and reinitializes the client."""
    global current_api_key_index, GEMINI_API_KEYS_LIST, gemini_initialized
    if not GEMINI_API_KEYS_LIST or len(GEMINI_API_KEYS_LIST) <= 1:
        if verbose:
            print(
                "  Aviso: Não é possível rotacionar (apenas uma ou nenhuma chave disponível).",
                file=sys.stderr,
            )
        return False
    start_index = current_api_key_index
    current_api_key_index = (current_api_key_index + 1) % len(GEMINI_API_KEYS_LIST)
    print(
        f"\n---> Rotacionando Chave de API para Índice {current_api_key_index} <---\n"
    )
    gemini_initialized = False  # Mark as uninitialized before trying the new key
    if current_api_key_index == start_index:
        print(
            "Aviso: Ciclo completo por todas as chaves de API. Limites de taxa podem persistir.",
            file=sys.stderr,
        )
    return initialize_gemini(verbose)


def extract_php_dependencies(file_content: str) -> List[str]:
    """Extracts FQCNs from use statements in PHP code, excluding function/const."""
    dependencies = set()
    simple_use_pattern = r"^\s*use\s+(?!function|const)([\w\\]+)(?:\s+as\s+\w+)?\s*;"
    matches_simple = re.findall(simple_use_pattern, file_content, re.MULTILINE)
    dependencies.update(matches_simple)
    group_use_pattern = r"^\s*use\s+([\w\\]+)\s*\{([^}]+)\}\s*;"
    matches_group = re.findall(group_use_pattern, file_content, re.MULTILINE)
    for base_namespace, group_content in matches_group:
        items = [item.strip() for item in group_content.split(",") if item.strip()]
        for item in items:
            if item.lower().startswith(("function ", "const ")):
                continue
            parts = item.split(" as ")
            class_or_subnamespace = parts[0].strip()
            full_path = (
                base_namespace.rstrip("\\") + "\\" + class_or_subnamespace.lstrip("\\")
            )
            dependencies.add(full_path)
    return sorted(list(dependencies))


def count_tokens_for_file(
    executor: Optional[concurrent.futures.ThreadPoolExecutor],  # Made Optional
    filepath_absolute: Path,
    file_type: str,
    previous_token_count: Optional[int],
    current_hash: Optional[str],
    previous_hash: Optional[str],
    verbose: bool,
    sleep_seconds: float,
    timeout_seconds: int,
) -> Optional[int]:
    """Counts tokens with rate limit handling, key rotation, timeout, and specific type estimates."""
    global genai_client

    # --- AC1 #38 & AC2 #38: Estimate for .env* and context_code_* files ---
    if file_type == "environment_env" or file_type.startswith("context_code_"):
        try:
            content = filepath_absolute.read_text(encoding="utf-8", errors="ignore")
            token_count = max(1, int(len(content) / 4)) if content else 0
            if verbose:
                print(
                    f"      -> Token Count (Estimate AC1/2): {token_count} (for {file_type})"
                )
            return token_count
        except Exception as e:
            if verbose:
                print(
                    f"      -> Token Count (Estimate AC1/2): Error reading '{filepath_absolute.name}' for estimation: {e}",
                    file=sys.stderr,
                )
            return None

    # Reuse previous count if hash matches (AC16)
    if (
        current_hash
        and previous_hash
        and current_hash == previous_hash
        and previous_token_count is not None
    ):
        if verbose:
            print(
                f"      -> Token Count (AC16): Reusing previous count ({previous_token_count}) as hash matches."
            )
        return previous_token_count

    # Check if Gemini client and executor are ready for API calls
    if not gemini_initialized or not genai_client or not executor:
        if verbose:
            print(
                f"      -> Token Count: Skipping API call (Gemini client/executor not ready). Estimating as fallback."
            )
        try:
            content = filepath_absolute.read_text(encoding="utf-8", errors="ignore")
            token_count = max(1, int(len(content) / 4)) if content else 0
            if verbose:
                print(
                    f"      -> Token Count (Fallback Estimate due to no client/executor): Estimated tokens: {token_count}"
                )
            return token_count
        except Exception as e:
            if verbose:
                print(
                    f"      -> Token Count: Error reading file '{filepath_absolute.name}' for fallback estimation: {e}",
                    file=sys.stderr,
                )
            return None

    if verbose:
        print(
            f"      -> Token Count (AC13/16): API/Fallback counting needed for {filepath_absolute.name}"
        )

    content_for_api: Optional[str] = None
    try:
        content_for_api = filepath_absolute.read_text(encoding="utf-8", errors="ignore")
    except (IOError, OSError) as e:
        if verbose:
            print(
                f"      -> Token Count (AC14): Error reading file '{filepath_absolute.name}' for API call: {e}",
                file=sys.stderr,
            )
        return None
    except MemoryError:
        if verbose:
            print(
                f"      -> Token Count (AC14): MemoryError reading large file '{filepath_absolute.name}' for API. Estimating.",
                file=sys.stderr,
            )
        try:
            token_count = max(1, int(os.path.getsize(filepath_absolute) / 4))
            if verbose:
                print(
                    f"      -> Token Count (AC20 Fallback for MemoryError): Estimated tokens: {token_count}"
                )
            return token_count
        except Exception as estimate_e:
            if verbose:
                print(
                    f"      -> Token Count: Error estimating size for MemoryError file: {estimate_e}",
                    file=sys.stderr,
                )
            return None

    if sleep_seconds > 0:
        if verbose:
            print(f"      -> Sleeping for {sleep_seconds:.2f}s before API call...")
        for _ in tqdm(
            range(int(sleep_seconds * 10)),
            desc="Waiting before API call",
            unit="ds",
            leave=False,
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}",
        ):
            time.sleep(0.1)

    initial_key_index = current_api_key_index
    keys_tried_in_this_call = {initial_key_index}
    token_count = None

    while True:

        def _api_call_task(content_str: str) -> int:
            """Makes the actual API call to count tokens via client."""
            if not genai_client:
                raise RuntimeError("Gemini client became uninitialized.")
            try:
                response = genai_client.models.count_tokens(
                    model=GEMINI_MODEL_NAME, contents=content_str
                )
                return response.total_tokens
            except Exception as inner_e:
                print(
                    f"      -> Erro interno na task API ({type(inner_e).__name__}): {inner_e}",
                    file=sys.stderr,
                )
                raise inner_e

        future = None
        try:
            if verbose:
                print(
                    f"        -> Attempting count_tokens with Key Index {current_api_key_index}, Timeout {timeout_seconds}s"
                )
            future = executor.submit(_api_call_task, content_for_api)
            token_count = future.result(timeout=timeout_seconds)
            if verbose:
                print(
                    f"      -> Token Count (AC13): Successfully counted via API: {token_count}"
                )
            return token_count

        except concurrent.futures.TimeoutError:
            print(
                f"      -> Token Count (AC19): API call timed out after {timeout_seconds}s for '{filepath_absolute.name}'. Estimating.",
                file=sys.stderr,
            )
            token_count = (
                max(1, int(len(content_for_api) / 4)) if content_for_api else 0
            )
            if verbose:
                print(
                    f"      -> Token Count (AC20 Fallback for Timeout): Estimated tokens: {token_count}"
                )
            return token_count

        except (
            google_api_core_exceptions.ResourceExhausted,
            errors.ServerError,
            google_api_core_exceptions.DeadlineExceeded,
        ) as e:
            print(
                f"      -> Rate Limit/Server Error/Deadline ({type(e).__name__}) with Key Index {current_api_key_index}. Waiting {DEFAULT_RATE_LIMIT_SLEEP}s and rotating key...",
                file=sys.stderr,
            )
            time.sleep(DEFAULT_RATE_LIMIT_SLEEP)
            if not rotate_api_key_and_reinitialize(verbose):
                print(
                    f"      Error: Falha ao rotacionar chave de API. Estimating as fallback.",
                    file=sys.stderr,
                )
                token_count = (
                    max(1, int(len(content_for_api) / 4)) if content_for_api else 0
                )
                if verbose:
                    print(
                        f"      -> Token Count (AC3 Fallback - Rotation Failed): Estimated tokens: {token_count}"
                    )
                return token_count
            if current_api_key_index in keys_tried_in_this_call:
                print(
                    f"      Error: Ciclo completo de chaves API. Limite/Erro persistente para '{filepath_absolute.name}'. Estimating.",
                    file=sys.stderr,
                )
                token_count = (
                    max(1, int(len(content_for_api) / 4)) if content_for_api else 0
                )
                if verbose:
                    print(
                        f"      -> Token Count (AC3 Fallback - Full Cycle): Estimated tokens: {token_count}"
                    )
                return token_count
            keys_tried_in_this_call.add(current_api_key_index)
            if verbose:
                print(
                    f"        -> Retrying count_tokens with new Key Index {current_api_key_index}"
                )
            continue

        except (errors.APIError, google_api_core_exceptions.GoogleAPICallError) as e:
            print(
                f"      -> Token Count (AC18): API Call Error for '{filepath_absolute.name}': {type(e).__name__} - {e}. Estimating.",
                file=sys.stderr,
            )
            token_count = (
                max(1, int(len(content_for_api) / 4)) if content_for_api else 0
            )
            if verbose:
                print(
                    f"      -> Token Count (AC3 Fallback - API Error): Estimated tokens: {token_count}"
                )
            return token_count
        except Exception as e:
            if verbose:
                print(
                    f"      -> Token Count: Unexpected Error during API call/result for '{filepath_absolute.name}': {e}",
                    file=sys.stderr,
                )
            traceback.print_exc(file=sys.stderr)
            return None


# --- Bloco Principal ---
if __name__ == "__main__":
    args = parse_arguments()
    setup_logging(args.verbose)

    output_filepath = (
        Path(args.output_path).resolve()
        if args.output_path
        else get_default_output_filepath()
    )
    try:
        output_filepath.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(
            f"Erro fatal: Não foi possível criar diretório para '{output_filepath}': {e}",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"--- Iniciando Geração do Manifesto (v1.23.1) ---")  # Versão Atualizada
    print(f"Arquivo de Saída: {output_filepath.relative_to(PROJECT_ROOT)}")
    print(f"Intervalo entre chamadas API count_tokens: {args.sleep}s")
    print(f"Timeout para chamadas API count_tokens: {args.timeout}s")

    if not load_api_keys(args.verbose):
        print(
            "Aviso: Incapaz de carregar chave(s) de API. A contagem de tokens via API será pulada (usará estimativas)."
        )
    else:
        initialize_gemini(args.verbose)

    if args.verbose:
        print("\n[AC3] Carregando manifesto anterior (se existir)...")
    previous_manifest_files_data = load_previous_manifest(
        DEFAULT_OUTPUT_DIR, args.verbose
    )

    print("\n[AC4 & AC9] Escaneando arquivos do projeto...")
    all_found_files_relative, _ = scan_project_files(args.verbose)

    print("\n[AC5] Filtrando arquivos baseados nas regras de exclusão...")
    filtered_file_paths = filter_files(
        all_found_files_relative,
        DEFAULT_IGNORE_PATTERNS,
        args.ignore_patterns,
        output_filepath,
        args.verbose,
    )

    print(
        f"\n[AC6-AC25] Processando {len(filtered_file_paths)} arquivos, gerando metadados..."
    )
    current_manifest_files_data: Dict[str, Any] = {}
    binary_file_count = 0
    processed_file_count = 0
    token_api_calls_or_fallbacks = 0

    # Initialize global executor only if Gemini client is ready
    api_executor = (
        concurrent.futures.ThreadPoolExecutor(max_workers=1)
        if gemini_initialized
        else None
    )

    try:
        for file_path_relative in sorted(list(filtered_file_paths)):
            processed_file_count += 1
            file_path_absolute = PROJECT_ROOT / file_path_relative
            relative_path_str = file_path_relative.as_posix()
            if args.verbose:
                print(
                    f"\n  Processing ({processed_file_count}/{len(filtered_file_paths)}): {relative_path_str}"
                )

            is_binary = is_likely_binary(file_path_absolute, args.verbose)
            if is_binary:
                binary_file_count += 1

            file_type = get_file_type(file_path_relative)
            if args.verbose:
                print(f"      -> Type (AC8): {file_type}")

            is_versioned = get_git_versioned_status(file_path_relative, args.verbose)
            if relative_path_str.startswith(("vendor/uspdev/", "context_llm/")):
                is_versioned = False
            if args.verbose:
                print(f"      -> Versioned (AC9): {is_versioned}")

            calculated_hash: Optional[str] = None
            is_env_file = file_type == "environment_env"
            is_context_code = file_type.startswith("context_code_")
            should_calculate_hash = (
                not is_binary and not is_env_file and not is_context_code
            )

            if should_calculate_hash:
                try:
                    file_content_bytes = file_path_absolute.read_bytes()
                    calculated_hash = hashlib.sha1(file_content_bytes).hexdigest()
                except Exception as e:
                    if args.verbose:
                        print(
                            f"      -> Hash (AC10/11): Error reading file content bytes: {e}",
                            file=sys.stderr,
                        )
            elif args.verbose:
                reason_hash = (
                    "binary (AC6)"
                    if is_binary
                    else (
                        "env file (AC11)"
                        if is_env_file
                        else (
                            "context code (AC11)"
                            if is_context_code
                            else "unknown exclusion"
                        )
                    )
                )
                print(f"      -> Hash (AC11): Setting to null ({reason_hash})")

            if args.verbose:
                print(f"      -> Hash (AC10/11): {calculated_hash or 'null'}")

            dependencies: List[str] = []
            if file_type.startswith(("code_php_", "migration_php", "test_php_")):
                try:
                    file_content_str = file_path_absolute.read_text(
                        encoding="utf-8", errors="ignore"
                    )
                    dependencies = extract_php_dependencies(file_content_str)
                    if args.verbose:
                        print(
                            f"      -> Dependencies (AC22): Extracted {len(dependencies)} use statements."
                        )
                except Exception as e:
                    if args.verbose:
                        print(
                            f"      -> Dependencies (AC22): Error extracting: {e}",
                            file=sys.stderr,
                        )
                    dependencies = []
            elif args.verbose:
                print(f"      -> Dependencies (AC23): Skipping (not a PHP file).")

            dependents: List[str] = []

            token_count: Optional[int] = None
            should_count_tokens_or_estimate = not is_binary

            previous_file_data = {}  # Começa vazio
            relative_path_str = file_path_relative.as_posix()  # Caminho relativo atual

            if file_type.startswith("context_code_"):
                # Busca especial para arquivos de contexto: ignora o timestamp no path
                current_filename = file_path_relative.name
                found_previous_path_str = None
                # Itera pelas chaves do manifesto anterior
                for prev_path_str in previous_manifest_files_data.keys():
                    # Verifica se é um arquivo de contexto com o mesmo nome de arquivo
                    if prev_path_str.startswith(
                        "context_llm/code/"
                    ) and prev_path_str.endswith(f"/{current_filename}"):
                        # Garante que não estamos pegando o mesmo timestamp (caso de rerodagem sem novo contexto)
                        if (
                            Path(prev_path_str).parent.name
                            != file_path_relative.parent.name
                        ):
                            found_previous_path_str = prev_path_str
                            break  # Pega o primeiro encontrado (provavelmente o mais recente anterior)

                if found_previous_path_str:
                    previous_file_data = previous_manifest_files_data.get(
                        found_previous_path_str, {}
                    )
                    if args.verbose and previous_file_data:
                        print(
                            f"      -> Found previous manifest data for '{current_filename}' using path '{found_previous_path_str}'"
                        )
                elif args.verbose:
                    print(
                        f"      -> No corresponding previous manifest data found for context file '{current_filename}'."
                    )

            else:
                # Lógica original para arquivos não-contexto: busca pelo path exato
                previous_file_data = previous_manifest_files_data.get(
                    relative_path_str, {}
                )
            # --- Fim da Lógica MODIFICADA ---

            # Agora recupera os dados do dicionário `previous_file_data` (que pode ou não ter sido encontrado)
            previous_hash = previous_file_data.get("hash")
            previous_count = previous_file_data.get("token_count")
            previous_summary = previous_file_data.get("summary")

            if should_count_tokens_or_estimate:
                token_count_result = count_tokens_for_file(
                    api_executor,
                    file_path_absolute,
                    file_type,
                    previous_count,
                    calculated_hash,
                    previous_hash,
                    args.verbose,
                    args.sleep,
                    args.timeout,
                )
                if token_count_result is not None and (
                    not previous_hash
                    or calculated_hash != previous_hash
                    or previous_count is None
                ):
                    token_api_calls_or_fallbacks += 1
                token_count = token_count_result
            elif args.verbose:
                reason = "binary"
                print(
                    f"      -> Token Count: Skipping count ({reason}). Setting to null."
                )

            # --- Lógica REVISADA para Preservação do Sumário (v1.23.1) ---
            # Esta lógica agora funcionará corretamente porque previous_summary será
            # populado corretamente para context_code* devido à busca acima.
            preserved_summary: Optional[str] = None

            if file_type.startswith("context_code"):
                if previous_summary is not None:
                    preserved_summary = previous_summary
                    if args.verbose:
                        print(
                            f"      -> Summary: Preserving previous summary for context file (regardless of hash)."
                        )
                elif args.verbose:
                    print(
                        f"      -> Summary: Setting to null (new context file or no previous summary)."
                    )

            elif calculated_hash and previous_hash and calculated_hash == previous_hash:
                # Para TODOS OS OUTROS arquivos, preserva o sumário APENAS se o hash não mudou.
                if previous_summary is not None:
                    preserved_summary = previous_summary
                    if args.verbose:
                        print(
                            f"      -> Summary: Reusing previous summary (hash unchanged)."
                        )
                elif args.verbose:
                    print(
                        f"      -> Summary: Setting to null (hash matches, but no previous summary found)."
                    )

            elif (
                args.verbose
            ):  # Hash mudou (e não é context_code) ou arquivo novo/binário/env
                print(
                    f"      -> Summary: Setting to null (hash changed or file is new/binary/env/context-without-prev-summary)."
                )
            # --- Fim da Lógica REVISADA ---

            # ... (cálculo de token_count) ...

            metadata: Dict[str, Any] = {
                "type": file_type,
                "versioned": is_versioned,
                "hash": calculated_hash,
                "token_count": token_count,  # Valor calculado/reusado
                "dependencies": dependencies,
                "dependents": dependents,
                "summary": preserved_summary,  # Usa o valor determinado pela NOVA lógica
            }

            # Garante que binários SEMPRE tenham summary null (AC6), mesmo se a lógica acima
            # acidentalmente preservar algo (improvável, mas seguro).
            if is_binary:
                metadata["summary"] = None
                if (
                    args.verbose
                    and preserved_summary is not None
                    and not file_type.startswith("context_code_")
                ):
                    print(
                        f"      -> Summary: Overriding previous summary with null because file is binary."
                    )

            current_manifest_files_data[relative_path_str] = metadata

    finally:
        if api_executor:
            print("\nShutting down API executor...")
            api_executor.shutdown(
                wait=True
            )  # Espera as tarefas pendentes antes de sair
            print("Executor shut down.")

    print(f"\n  Processamento concluído para {len(filtered_file_paths)} arquivos.")
    print(f"  Detecção AC6: {binary_file_count} arquivos binários.")
    print(f"  Cálculo AC10/11: Hashes SHA1 calculados ou nulos.")
    print(
        f"  Contagem Tokens (AC1, AC2, AC3, AC12-20): {token_api_calls_or_fallbacks} chamadas API Gemini ou fallbacks de estimativa realizados."
    )
    print(f"  Extração Dependências (AC22/23): Processado para arquivos PHP.")

    manifest_data_final: Dict[str, Any] = {
        "_metadata": {
            "timestamp": datetime.datetime.now().isoformat(),
            "comment": f"Manifesto gerado - v1.23.1 (Persist Context Summaries). Arquivos processados: {len(filtered_file_paths)}.",  # Versão Atualizada
            "output_file": str(output_filepath.relative_to(PROJECT_ROOT)),
            "args": vars(args),
            "previous_manifest_loaded": bool(previous_manifest_files_data),
            "files_found_before_filter": len(all_found_files_relative),
            "files_after_filter": len(filtered_file_paths),
            "binary_files_detected": binary_file_count,
            "gemini_initialized": gemini_initialized,
            "token_api_calls_or_fallbacks": token_api_calls_or_fallbacks,
        },
        "files": current_manifest_files_data,
    }

    try:
        with open(output_filepath, "w", encoding="utf-8") as f:
            json.dump(manifest_data_final, f, indent=4, ensure_ascii=False)
        print(f"\nManifesto JSON salvo em: {output_filepath.relative_to(PROJECT_ROOT)}")
    except Exception as e:
        print(f"\nErro ao salvar o arquivo de manifesto: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

    print(f"--- Geração do Manifesto Concluída (v1.23.1) ---")  # Atualizado
    sys.exit(0)
