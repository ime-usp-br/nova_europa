#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ==============================================================================
# generate_manifest.py (v1.19 - Added Rate Limit Handling & Key Rotation)
#
# Script para gerar um manifesto JSON estruturado do projeto, catalogando
# arquivos relevantes e extraindo metadados essenciais.
# Destinado a auxiliar ferramentas LLM e rastreamento de mudanças.
# Adiciona sleep entre chamadas de contagem de tokens e implementa rotação
# de API key (formato key1|key2|...) para lidar com erros de rate limit.
#
# Uso:
#   python scripts/generate_manifest.py [-o output.json] [-i ignore_pattern] [-v] [--sleep SLEEP_SECONDS]
#
# Argumentos:
#   -o, --output OUTPUT_PATH   Caminho para o arquivo JSON de saída.
#   -i, --ignore IGNORE_PATTERN Padrão (glob), diretório ou arquivo a ignorar.
#   -v, --verbose              Habilita logging mais detalhado.
#   --sleep SLEEP_SECONDS      Segundos de espera entre chamadas à API count_tokens (padrão: 1.0).
#   -h, --help                 Mostra esta mensagem de ajuda.
# ==============================================================================

import argparse
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
from google import genai
from google.genai import types
from google.genai import errors as google_genai_errors
from google.api_core import exceptions as google_api_core_exceptions

# --- Constantes Globais ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "scripts" / "data"
TIMESTAMP_MANIFEST_REGEX = r'^\d{8}_\d{6}_manifest\.json$'
TIMESTAMP_DIR_REGEX = r'^\d{8}_\d{6}$'
CONTEXT_CODE_DIR = PROJECT_ROOT / "context_llm" / "code"
CONTEXT_COMMON_DIR = PROJECT_ROOT / "context_llm" / "common"
VENDOR_USPDEV_DIRS = [
    PROJECT_ROOT / "vendor/uspdev/replicado/src/",
    PROJECT_ROOT / "vendor/uspdev/senhaunica-socialite/src/",
]
DEFAULT_IGNORE_PATTERNS: Set[str] = {
    ".git/", ".vscode/", ".idea/", ".fleet/", "node_modules/",
    "storage/framework/cache/data/", "storage/framework/sessions/",
    "storage/framework/views/", "storage/logs/", "bootstrap/cache/",
    "public/build/", "*.lock", "*.sqlite", "*.sqlite-journal", "*.log",
    ".phpunit.cache/", "llm_outputs/", "scripts/data/", "*.DS_Store",
    "Thumbs.db", "vendor/", "context_llm/",
}
BINARY_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.tif', '.tiff', '.webp',
    '.mp3', '.wav', '.ogg', '.aac', '.flac', '.m4a', '.mp4', '.avi', '.mov',
    '.wmv', '.mkv', '.flv', '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.odt', '.ods', '.odp',
    '.exe', '.dll', '.so', '.dylib', '.app', '.bin', '.o', '.a', '.sqlite', '.db',
    '.ttf', '.otf', '.woff', '.woff2', '.eot', '.pyc', '.phar', '.jar', '.class',
    '.swf', '.dat',
}
TEXTCHARS = bytes(range(32, 127)) + b'\n\r\t\f\b'
GEMINI_MODEL_NAME = 'gemini-1.5-flash'
DEFAULT_INTER_CALL_SLEEP = 1.0 # Default sleep between count_tokens calls
DEFAULT_RATE_LIMIT_SLEEP = 5.0 # Default sleep after hitting rate limit

# --- Variáveis Globais ---
repo_owner: Optional[str] = None
GEMINI_API_KEYS_LIST: List[str] = [] # Renamed for clarity
current_api_key_index: int = 0
genai_client: Optional[genai.Client] = None
api_key_loaded: bool = False
gemini_initialized: bool = False

# --- Funções ---
def run_command(cmd_list: List[str], cwd: Path = PROJECT_ROOT, check: bool = True, capture: bool = True, input_data: Optional[str] = None, shell: bool = False, timeout: Optional[int] = 60) -> Tuple[int, str, str]:
    """Runs a subprocess command and returns exit code, stdout, stderr."""
    cmd_str = shlex.join(cmd_list) if not shell else " ".join(map(shlex.quote, cmd_list))
    start_time = time.monotonic()
    try:
        process = subprocess.run(
            cmd_list if not shell else cmd_str,
            capture_output=capture, text=True, input=input_data,
            check=check, cwd=cwd, shell=shell, timeout=timeout,
            encoding='utf-8', errors='replace'
        )
        duration = time.monotonic() - start_time
        return process.returncode, process.stdout or "", process.stderr or ""
    except FileNotFoundError: return 1, "", f"Command not found: {cmd_list[0]}"
    except subprocess.TimeoutExpired: return 1, "", f"Command timed out after {timeout}s: {cmd_str}"
    except subprocess.CalledProcessError as e: return e.returncode, e.stdout or "", e.stderr or ""
    except Exception as e: return 1, "", f"Unexpected error running command {cmd_str}: {e}"

def parse_arguments() -> argparse.Namespace:
    """Configura e processa os argumentos da linha de comando."""
    parser = argparse.ArgumentParser( description="Gera um manifesto JSON estruturado do projeto.", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=f"""Exemplos:\n  python {Path(__file__).name}\n  python {Path(__file__).name} -o build/manifest.json\n  python {Path(__file__).name} -i '*.tmp' -i 'docs/drafts/' -v --sleep 0.5""") # Added sleep example
    parser.add_argument("-o", "--output", dest="output_path", type=str, default=None, help=f"Caminho para o arquivo JSON de saída. Padrão: {DEFAULT_OUTPUT_DIR.relative_to(PROJECT_ROOT)}/YYYYMMDD_HHMMSS_manifest.json")
    parser.add_argument("-i", "--ignore", dest="ignore_patterns", action="append", default=[], help="Padrão (glob), diretório ou arquivo a ignorar. Use múltiplas vezes.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Habilita logging mais detalhado.")
    parser.add_argument("--sleep", type=float, default=DEFAULT_INTER_CALL_SLEEP, help=f"Segundos de espera entre chamadas à API count_tokens (padrão: {DEFAULT_INTER_CALL_SLEEP}).")
    return parser.parse_args()

def setup_logging(verbose: bool):
    if verbose: print("Modo verbose habilitado.")

def get_default_output_filepath() -> Path:
    """Gera o caminho padrão para o arquivo de saída com timestamp."""
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}_manifest.json"
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_OUTPUT_DIR / filename

def find_latest_context_code_dir(context_base_dir: Path) -> Optional[Path]:
    """Encontra o diretório de contexto mais recente dentro do diretório base."""
    if not context_base_dir.is_dir(): return None
    valid_context_dirs = [d for d in context_base_dir.iterdir() if d.is_dir() and re.match(TIMESTAMP_DIR_REGEX, d.name)]
    if not valid_context_dirs: return None
    return sorted(valid_context_dirs, reverse=True)[0]

def is_likely_binary(file_path: Path, verbose: bool) -> bool:
    """Verifica se um arquivo é provavelmente binário."""
    if file_path.suffix.lower() in BINARY_EXTENSIONS:
        if verbose: print(f"      -> Binary Check (AC6): Positive (extension '{file_path.suffix}')")
        return True
    try:
        with open(file_path, 'rb') as f: chunk = f.read(512)
        if not chunk: return False # Empty file is not binary
        if b'\0' in chunk:
             if verbose: print(f"      -> Binary Check (AC6): Positive (null byte found)")
             return True
        non_text_count = sum(1 for byte in chunk if bytes([byte]) not in TEXTCHARS)
        proportion = non_text_count / len(chunk) if len(chunk) > 0 else 0
        is_bin = proportion > 0.30 # Heuristic: >30% non-text bytes
        if is_bin and verbose: print(f"      -> Binary Check (AC6): Positive (high proportion of non-text bytes: {proportion:.1%})")
        return is_bin
    except Exception as e:
        if verbose: print(f"      -> Binary Check (AC6): Error reading file for binary check: {e}", file=sys.stderr)
        return False # Treat as non-binary if cannot read

def load_previous_manifest(data_dir: Path, verbose: bool) -> Dict[str, Any]:
    """Carrega o dicionário 'files' do manifesto anterior mais recente."""
    if not data_dir.is_dir():
        if verbose: print("  Aviso: Diretório de dados do manifesto não encontrado, não é possível carregar dados anteriores.")
        return {}
    manifest_files = [f for f in data_dir.glob('*_manifest.json') if f.is_file() and re.match(TIMESTAMP_MANIFEST_REGEX, f.name)]
    if not manifest_files:
        if verbose: print("  Aviso: Nenhum arquivo de manifesto anterior encontrado.")
        return {}
    latest_manifest_path = sorted(manifest_files, reverse=True)[0]
    if verbose: print(f"  Encontrado manifesto anterior: '{latest_manifest_path.relative_to(PROJECT_ROOT)}'")
    try:
        with open(latest_manifest_path, 'r', encoding='utf-8') as f: data = json.load(f)
        # Retorna o dicionário sob a chave 'files' se existir e for um dict, senão vazio
        if isinstance(data, dict) and "files" in data and isinstance(data["files"], dict):
            if verbose: print(f"  Manifesto anterior carregado com sucesso ({len(data['files'])} arquivos).")
            return data["files"]
        else:
             if verbose: print("  Aviso: Formato inesperado no manifesto anterior ou chave 'files' ausente/inválida.")
             return {}
    except Exception as e:
        if verbose: print(f"  Erro ao carregar ou parsear manifesto anterior '{latest_manifest_path.name}': {e}", file=sys.stderr)
        return {}

def scan_project_files(verbose: bool) -> Tuple[Set[Path], Set[Path]]:
    """Escaneia o projeto por arquivos, priorizando git e incluindo dirs específicos."""
    all_files_set: Set[Path] = set()
    git_files_set: Set[Path] = set()
    if verbose: print("  Executando 'git ls-files' para encontrar arquivos versionados/rastreados...")
    # -c: cached, -o: others, -z: null terminated, --exclude-standard: use .gitignore
    exit_code_ls, stdout_ls, stderr_ls = run_command(['git', 'ls-files', '-z', '-c', '-o', '--exclude-standard'], check=False)
    if exit_code_ls == 0 and stdout_ls:
        tracked_paths = filter(None, stdout_ls.split('\0'))
        for path_str in tracked_paths:
            try:
                absolute_path = (PROJECT_ROOT / Path(path_str)).resolve(strict=True) # Resolve symlinks, check existence
                if absolute_path.is_file():
                    relative_path = absolute_path.relative_to(PROJECT_ROOT)
                    all_files_set.add(relative_path)
                    git_files_set.add(relative_path) # Mark as versioned/tracked by git
            except (FileNotFoundError, ValueError, Exception) as e:
                 if verbose: print(f"    Aviso: Ignorando path de 'git ls-files' devido a erro: {path_str} ({e})", file=sys.stderr)
    else:
         print(f"  Aviso: 'git ls-files' falhou (Code: {exit_code_ls}). A varredura pode estar incompleta. Stderr: {stderr_ls.strip()}", file=sys.stderr)
    if verbose: print(f"  Arquivos iniciais encontrados via Git: {len(all_files_set)}")

    # Scans adicionais (contexto comum, último código, vendor uspdev)
    additional_scan_dirs: List[Path] = [CONTEXT_COMMON_DIR]
    latest_context_code_dir = find_latest_context_code_dir(CONTEXT_CODE_DIR)
    if latest_context_code_dir: additional_scan_dirs.append(latest_context_code_dir)
    additional_scan_dirs.extend(VENDOR_USPDEV_DIRS)
    if verbose: print("  Realizando scans adicionais em diretórios específicos...")
    for scan_dir in additional_scan_dirs:
        abs_scan_dir = scan_dir.resolve(strict=False)
        if verbose: print(f"    Escaneando: {abs_scan_dir.relative_to(PROJECT_ROOT)}")
        if abs_scan_dir.is_dir():
            for item in abs_scan_dir.rglob('*'):
                try:
                    if item.is_file():
                        relative_path = item.resolve(strict=True).relative_to(PROJECT_ROOT)
                        all_files_set.add(relative_path)
                except (FileNotFoundError, ValueError, Exception) as e:
                     if verbose: print(f"      Aviso: Ignorando item durante scan adicional: {item} ({e})", file=sys.stderr)
        elif verbose: print(f"      Aviso: Diretório de scan adicional não existe: {abs_scan_dir}")

    if verbose: print(f"  Total de arquivos únicos encontrados após scans: {len(all_files_set)}")
    return all_files_set, git_files_set

def filter_files(all_files: Set[Path], default_ignores: Set[str], custom_ignores: List[str], output_filepath: Path, verbose: bool) -> Set[Path]:
    """Filtra a lista de arquivos com base nos padrões de ignore."""
    filtered_files: Set[Path] = set()
    ignore_patterns = default_ignores.copy()
    ignore_patterns.update(custom_ignores)
    try: ignore_patterns.add(output_filepath.relative_to(PROJECT_ROOT).as_posix())
    except ValueError: pass
    if verbose: print(f"  Aplicando {len(ignore_patterns)} padrões de exclusão...")
    skipped_count = 0
    for file_path in all_files:
        file_path_str = file_path.as_posix()
        is_ignored = False
        for pattern in ignore_patterns:
            # Check for vendor/uspdev/* explicitly to avoid excluding them due to vendor/ pattern
            if pattern == "vendor/" and any(file_path_str.startswith(str(usp_dir.relative_to(PROJECT_ROOT).as_posix()) + '/') for usp_dir in VENDOR_USPDEV_DIRS):
                continue # Don't ignore USPDev paths due to the general vendor/ rule
            # Check for context_llm common/latest explicitly
            if pattern == "context_llm/":
                is_common = file_path_str.startswith(str(CONTEXT_COMMON_DIR.relative_to(PROJECT_ROOT).as_posix()) + '/')
                latest_code_dir = find_latest_context_code_dir(CONTEXT_CODE_DIR)
                is_latest_code = latest_code_dir and file_path_str.startswith(str(latest_code_dir.relative_to(PROJECT_ROOT).as_posix()) + '/')
                if is_common or is_latest_code:
                    continue # Don't ignore common or latest code dir due to general context_llm/ rule

            is_dir_pattern = pattern.endswith('/')
            cleaned_pattern = pattern.rstrip('/')
            # Check for exact match or directory prefix match
            if file_path_str == cleaned_pattern or (is_dir_pattern and file_path_str.startswith(cleaned_pattern + '/')):
                is_ignored = True; break
            # Check for glob match
            try:
                if file_path.match(pattern): is_ignored = True; break
            except Exception as e: # Catch potential issues with Path.match
                 if verbose: print(f"    Warning: Error matching pattern '{pattern}' for file '{file_path_str}': {e}", file=sys.stderr)
        if not is_ignored: filtered_files.add(file_path)
        elif verbose: skipped_count += 1
    if verbose: print(f"  Filtro concluído. {len(filtered_files)} arquivos retidos, {skipped_count} ignorados.")
    return filtered_files

def get_file_type(relative_path: Path) -> str:
    """Determina um tipo granular para o arquivo baseado no caminho e extensão."""
    path_str = relative_path.as_posix(); parts = relative_path.parts; name = relative_path.name; suffix = relative_path.suffix.lower()
    if name == 'composer.json': return 'dependency_composer'
    if name == 'package.json': return 'dependency_npm'
    if name == 'artisan': return 'code_php_artisan'
    if name == 'README.md': return 'docs_readme'
    if name == 'CHANGELOG.md': return 'docs_changelog'
    if name == 'LICENSE': return 'docs_license'
    if name.startswith('.env'): return 'environment_env'
    if name == '.gitignore': return 'config_git_ignore'
    if name == '.gitattributes': return 'config_git_attributes'
    if name == '.editorconfig': return 'config_editor'
    if name == 'phpunit.xml': return 'config_phpunit'
    if name == 'phpstan.neon': return 'config_phpstan'
    if name == 'pint.json': return 'config_pint'
    if name == 'vite.config.js': return 'config_vite'
    if name == 'tailwind.config.js': return 'config_tailwind'
    if name == 'postcss.config.js': return 'config_postcss'
    if parts[0] == 'app':
        if suffix == '.php':
            if 'Http/Controllers' in path_str: return 'code_php_controller'
            if 'Models' in path_str: return 'code_php_model'
            if 'Providers' in path_str: return 'code_php_provider'
            if 'Livewire/Forms' in path_str: return 'code_php_livewire_form'
            if 'Livewire/Actions' in path_str: return 'code_php_action'
            if 'Livewire' in path_str: return 'code_php_livewire'
            if 'View/Components' in path_str: return 'code_php_view_component'
            if 'Services' in path_str: return 'code_php_service'
            if 'Http/Middleware' in path_str: return 'code_php_middleware'
            if 'Http/Requests' in path_str: return 'code_php_request'
            if 'Console/Commands' in path_str: return 'code_php_command'
            return 'code_php_app'
    if parts[0] == 'config' and suffix == '.php': return 'config_laravel'
    if parts[0] == 'database':
        if 'migrations' in parts and suffix == '.php': return 'migration_php'
        if 'factories' in parts and suffix == '.php': return 'code_php_factory'
        if 'seeders' in parts and suffix == '.php': return 'code_php_seeder'
    if parts[0] == 'resources' and 'views' in parts and suffix == '.blade.php':
         if 'components' in parts: return 'view_blade_component'
         return 'view_blade'
    if parts[0] == 'resources' and 'css' in parts: return 'asset_source_css'
    if parts[0] == 'resources' and 'js' in parts: return 'asset_source_js'
    if parts[0] == 'resources' and 'images' in parts: return f'asset_source_image_{suffix[1:]}' if suffix else 'asset_source_image'
    if parts[0] == 'public' and suffix == '.php': return 'code_php_public'
    if parts[0] == 'public' and suffix in ['.ico', '.png', '.jpg', '.jpeg', '.gif']: return f'asset_binary_{suffix[1:]}'
    if parts[0] == 'public' and suffix == '.txt': return 'asset_public'
    if parts[0] == 'public' and suffix == '.htaccess': return 'config_apache'
    if parts[0] == 'routes' and suffix == '.php': return 'code_php_route'
    if parts[0] == 'tests':
        if 'Feature' in parts and suffix == '.php': return 'test_php_feature'
        if 'Unit' in parts and suffix == '.php': return 'test_php_unit'
        if 'Browser' in parts and suffix == '.php': return 'test_php_dusk'
        if 'Fakes' in parts and suffix == '.php': return 'test_php_fake'
        if suffix == '.php': return 'test_php'
    if parts[0] == 'scripts':
        if suffix == '.py': return 'code_python_script'
        if suffix == '.sh': return 'code_shell_script'
    if parts[0] == 'docs':
        if 'adr' in parts and suffix == '.md': return 'docs_adr_md'
        if suffix == '.md': return 'docs_md'
    if parts[0] == 'planos' and suffix == '.txt': return 'plan_text'
    if parts[0] == 'templates':
        if 'meta-prompts' in parts and suffix == '.txt': return 'template_meta_prompt'
        if 'prompts' in parts and suffix == '.txt': return 'template_prompt'
        if 'issue_bodies' in parts and suffix == '.md': return 'template_issue_body'
    if path_str.startswith('vendor/uspdev/replicado/src/') and suffix == '.php': return 'code_php_vendor_uspdev_replicado'
    if path_str.startswith('vendor/uspdev/senhaunica-socialite/src/') and suffix == '.php': return 'code_php_vendor_uspdev_senhaunica'
    if path_str.startswith('context_llm/common/'): return 'context_common'
    if path_str.startswith('context_llm/code/') and len(parts) > 2:
        file_part = name.lower()
        # More specific context file types
        if file_part == 'git_log.txt': return 'context_code_git_log'
        if file_part == 'git_diff_cached.txt': return 'context_code_git_diff_cached'
        if file_part == 'git_diff_unstaged.txt': return 'context_code_git_diff_unstaged'
        if file_part == 'git_status.txt': return 'context_code_git_status'
        if file_part == 'git_ls_files.txt': return 'context_code_git_lsfiles'
        if file_part.startswith('github_issue_'): return 'context_code_issue_details'
        if file_part.startswith('artisan_'): return 'context_code_artisan_output'
        if file_part.startswith('env_'): return 'context_code_env_info'
        if file_part == 'composer_show.txt': return 'context_code_deps_composer'
        if file_part == 'npm_list_depth0.txt': return 'context_code_deps_npm'
        if file_part == 'env_pip_freeze.txt': return 'context_code_deps_pip'
        if file_part == 'project_tree_l3.txt': return 'context_code_project_tree'
        if file_part == 'project_cloc.txt': return 'context_code_cloc'
        if file_part == 'phpstan_analysis.txt': return 'context_code_phpstan'
        if file_part == 'pint_test_results.txt': return 'context_code_pint'
        if file_part == 'phpunit_test_results.txt': return 'context_code_phpunit'
        if file_part == 'dusk_test_results.txt': return 'context_code_dusk_results'
        if file_part == 'dusk_test_info.txt': return 'context_code_dusk_info'
        if file_part == 'manifest.md': return 'context_code_manifest_md'
        # Fallback for other context files
        return 'context_code'
    if suffix == '.php': return 'code_php'
    if suffix == '.js': return 'code_js'
    if suffix == '.py': return 'code_python'
    if suffix == '.sh': return 'code_shell'
    if suffix == '.json': return 'config_json'
    if suffix in ['.yaml', '.yml']: return 'config_yaml'
    if suffix == '.md': return 'docs_md'
    if suffix == '.txt': return 'text_plain'
    if suffix in BINARY_EXTENSIONS: return f'binary_{suffix[1:]}'
    return 'unknown'

# --- Funções para Rate Limit e Rotação de Chave (Adaptado de llm_interact.py) ---
def load_api_keys(verbose: bool) -> bool:
    """Loads GEMINI_API_KEYS from .env or environment variables."""
    global GEMINI_API_KEYS_LIST, api_key_loaded, current_api_key_index
    if api_key_loaded: return True

    dotenv_path = PROJECT_ROOT / '.env'
    if dotenv_path.is_file():
        if verbose: print(f"  Carregando variáveis de ambiente de: {dotenv_path.relative_to(PROJECT_ROOT)}")
        load_dotenv(dotenv_path=dotenv_path, verbose=verbose, override=True)

    api_key_string = os.getenv('GEMINI_API_KEY') # Assume a mesma variável usada em llm_interact
    if not api_key_string:
        print("Erro: Variável de ambiente GEMINI_API_KEY não encontrada.", file=sys.stderr)
        api_key_loaded = False
        return False

    GEMINI_API_KEYS_LIST = [key.strip() for key in api_key_string.split('|') if key.strip()]
    if not GEMINI_API_KEYS_LIST:
        print("Erro: Formato da GEMINI_API_KEY inválido ou vazio. Use '|' para separar múltiplas chaves.", file=sys.stderr)
        api_key_loaded = False
        return False

    current_api_key_index = 0 # Start with the first key
    api_key_loaded = True
    if verbose: print(f"  {len(GEMINI_API_KEYS_LIST)} Chave(s) de API GEMINI carregadas.")
    return True

def initialize_gemini(verbose: bool) -> bool:
    """Initializes the Gemini client using the current API key."""
    global genai_client, gemini_initialized, GEMINI_API_KEYS_LIST, current_api_key_index
    if gemini_initialized: return True
    if not api_key_loaded or not GEMINI_API_KEYS_LIST or not (0 <= current_api_key_index < len(GEMINI_API_KEYS_LIST)):
        if verbose: print("  Aviso: Chaves de API não carregadas ou índice inválido. Impossível inicializar Gemini.")
        return False

    active_key = GEMINI_API_KEYS_LIST[current_api_key_index]
    try:
        if verbose: print(f"  Inicializando Google GenAI Client com Key Index {current_api_key_index}...")
        genai_client = genai.Client(api_key=active_key)
        print("  Cliente Gemini inicializado com sucesso.")
        gemini_initialized = True
        return True
    except Exception as e:
        print(f"Erro ao inicializar Google GenAI Client com Key Index {current_api_key_index}: {e}", file=sys.stderr)
        if verbose: traceback.print_exc(file=sys.stderr)
        gemini_initialized = False
        return False

def rotate_api_key_and_reinitialize(verbose: bool) -> bool:
    """Rotates to the next API key and reinitializes the client."""
    global current_api_key_index, GEMINI_API_KEYS_LIST
    if not GEMINI_API_KEYS_LIST or len(GEMINI_API_KEYS_LIST) <= 1:
        if verbose: print("  Aviso: Não é possível rotacionar (apenas uma ou nenhuma chave disponível).", file=sys.stderr)
        return False # Cannot rotate if only one key

    start_index = current_api_key_index
    current_api_key_index = (current_api_key_index + 1) % len(GEMINI_API_KEYS_LIST)
    print(f"\n---> Rotacionando Chave de API para Índice {current_api_key_index} <---\n")
    if current_api_key_index == start_index:
        print("Aviso: Ciclo completo por todas as chaves de API. Limites de taxa podem persistir.", file=sys.stderr)

    return initialize_gemini(verbose) # Re-initialize with the new key

def count_tokens_for_file(
    filepath_absolute: Path,
    client: Optional[genai.Client],
    previous_token_count: Optional[int],
    current_hash: Optional[str],
    previous_hash: Optional[str],
    verbose: bool,
    sleep_seconds: float # Add sleep parameter
) -> Optional[int]:
    """Counts tokens with rate limit handling and key rotation."""
    if not gemini_initialized or not client:
        if verbose: print(f"      -> Token Count: Skipping (Gemini client not initialized)")
        return None

    # AC16: Incremental Logic
    if current_hash and previous_hash and current_hash == previous_hash and previous_token_count is not None:
        if verbose: print(f"      -> Token Count (AC16): Reusing previous count ({previous_token_count}) as hash matches.")
        return previous_token_count

    if verbose: print(f"      -> Token Count (AC13/16): Counting needed for {filepath_absolute.name}")

    # Apply sleep before making a potential API call
    if sleep_seconds > 0:
        if verbose: print(f"      -> Sleeping for {sleep_seconds:.2f}s before API call...")
        time.sleep(sleep_seconds)

    initial_key_index = current_api_key_index
    keys_tried_in_this_call = {initial_key_index}

    while True: # Loop for retries with key rotation
        try:
            if verbose: print(f"        -> Attempting count_tokens with Key Index {current_api_key_index}")
            content = filepath_absolute.read_text(encoding='utf-8', errors='ignore')
            response = client.models.count_tokens(model=GEMINI_MODEL_NAME, contents=content)
            token_count = response.total_tokens
            if verbose: print(f"      -> Token Count (AC13): Successfully counted: {token_count}")
            return token_count # Success!

        except (IOError, OSError) as e:
            if verbose: print(f"      -> Token Count (AC14): Error reading file '{filepath_absolute.name}': {e}", file=sys.stderr)
            return None # Read error, no retry

        # --- Rate Limit / API Error Handling ---
        except (google_api_core_exceptions.ResourceExhausted, google_genai_errors.APIError) as e:
            status_code = -1
            is_rate_limit = isinstance(e, google_api_core_exceptions.ResourceExhausted)
            if isinstance(e, google_genai_errors.APIError):
                status_code = getattr(e, 'code', -1)
                # Treat 429 specifically as rate limit
                if status_code == 429:
                    is_rate_limit = True

            if is_rate_limit:
                print(f"      -> Rate Limit Error ({type(e).__name__}{f', code={status_code}' if status_code != -1 else ''}) with Key Index {current_api_key_index}. Waiting {DEFAULT_RATE_LIMIT_SLEEP}s and rotating key...", file=sys.stderr)
                time.sleep(DEFAULT_RATE_LIMIT_SLEEP)

                if not rotate_api_key_and_reinitialize(verbose):
                    print(f"      Error: Falha ao rotacionar chave de API após rate limit. Retornando None.", file=sys.stderr)
                    return None

                if current_api_key_index in keys_tried_in_this_call:
                    print(f"      Error: Ciclo completo de chaves de API. Limite de taxa provavelmente persistente para '{filepath_absolute.name}'. Retornando None.", file=sys.stderr)
                    return None

                keys_tried_in_this_call.add(current_api_key_index)
                if verbose: print(f"        -> Retrying count_tokens with new Key Index {current_api_key_index}")
                continue # Continue the while loop to retry with the new key

            else: # Handle other API errors without retry
                if verbose: print(f"      -> Token Count (AC18): API Error for '{filepath_absolute.name}': {type(e).__name__} - {e}", file=sys.stderr)
                return None
        except Exception as e: # Catch other unexpected errors
            if verbose: print(f"      -> Token Count: Unexpected Error for '{filepath_absolute.name}': {e}", file=sys.stderr)
            # traceback.print_exc(file=sys.stderr) # Uncomment for full trace if needed
            return None
        # --- End Error Handling ---

# --- Bloco Principal ---
if __name__ == "__main__":
    args = parse_arguments()
    setup_logging(args.verbose)

    if args.output_path:
        output_filepath = Path(args.output_path).resolve()
        try: output_filepath.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e: print(f"Erro fatal: Não foi possível criar diretório para '{output_filepath}': {e}", file=sys.stderr); sys.exit(1)
    else:
        output_filepath = get_default_output_filepath()

    print(f"--- Iniciando Geração do Manifesto ---")
    print(f"Arquivo de Saída: {output_filepath.relative_to(PROJECT_ROOT)}")
    print(f"Intervalo entre chamadas API count_tokens: {args.sleep}s")

    # Load API keys from the start
    if not load_api_keys(args.verbose):
        print("Aviso: Incapaz de carregar chave(s) de API. A contagem de tokens será pulada.")
    else:
        # Initialize Gemini client with the first key
        initialize_gemini(args.verbose)

    if args.verbose: print("\n[AC3] Carregando manifesto anterior (se existir)...")
    previous_manifest_files_data = load_previous_manifest(DEFAULT_OUTPUT_DIR, args.verbose)

    print("\n[AC4 & AC9] Escaneando arquivos do projeto e identificando versionados...")
    all_found_files_relative, versioned_files_set = scan_project_files(args.verbose)

    print("\n[AC5] Filtrando arquivos baseados nas regras de exclusão...")
    filtered_file_paths = filter_files( all_found_files_relative, DEFAULT_IGNORE_PATTERNS, args.ignore_patterns, output_filepath, args.verbose)

    print("\n[AC6-AC18] Processando arquivos, gerando metadados (hash, tipo, versioned, token_count)...")
    current_manifest_files_data: Dict[str, Any] = {}
    binary_file_count = 0
    processed_file_count = 0
    token_api_calls_made = 0

    for file_path_relative in sorted(list(filtered_file_paths)):
        processed_file_count += 1
        file_path_absolute = PROJECT_ROOT / file_path_relative
        relative_path_str = file_path_relative.as_posix()
        if args.verbose: print(f"\n  Processing ({processed_file_count}/{len(filtered_file_paths)}): {relative_path_str}")

        is_binary = is_likely_binary(file_path_absolute, args.verbose) # AC6
        if is_binary: binary_file_count += 1

        file_type = get_file_type(file_path_relative) # AC8
        if args.verbose: print(f"      -> Type (AC8): {file_type}")

        is_versioned = file_path_relative in versioned_files_set # AC9 check 1
        if relative_path_str.startswith(('vendor/uspdev/', 'context_llm/')): is_versioned = False # AC9 check 2
        if args.verbose: print(f"      -> Versioned (AC9): {is_versioned}")

        calculated_hash: Optional[str] = None
        is_env_file = file_type == 'environment_env'
        is_context_code = relative_path_str.startswith('context_llm/code/')
        should_calculate_hash = not is_binary and not is_env_file # AC11: Exclude binary and env

        if should_calculate_hash:
            try: calculated_hash = hashlib.sha1(file_path_absolute.read_bytes()).hexdigest() # AC10
            except Exception as e:
                 if args.verbose: print(f"      -> Hash (AC11): Error calculating hash: {e}", file=sys.stderr) # AC11 error case
        if is_context_code: calculated_hash = None # AC11: Also null for context code
        if args.verbose: print(f"      -> Hash (AC10/11): {calculated_hash or 'null (excluded/error)'}")

        token_count: Optional[int] = None
        should_count_tokens = gemini_initialized and not is_binary and not is_env_file and not is_context_code
        if should_count_tokens:
            previous_file_data = previous_manifest_files_data.get(relative_path_str, {})
            previous_hash = previous_file_data.get("hash")
            previous_count = previous_file_data.get("token_count")

            token_count_result = count_tokens_for_file(
                file_path_absolute,
                genai_client, # Pass the global client
                previous_count,
                calculated_hash,
                previous_hash,
                args.verbose,
                args.sleep # Pass the sleep duration
            )

            if token_count_result is not None and (previous_count is None or calculated_hash != previous_hash):
                 token_api_calls_made +=1

            token_count = token_count_result

        elif args.verbose:
             reason = "binary" if is_binary else "env file" if is_env_file else "context_code file" if is_context_code else "Gemini not initialized"
             print(f"      -> Token Count (AC14): Skipping count ({reason}). Setting to null.")

        metadata: Dict[str, Any] = {
            "type": file_type,
            "versioned": is_versioned,
            "hash": calculated_hash,
            "token_count": token_count,
            "dependencies": [],
            "dependents": [],
            "summary": None,
        }
        if is_binary: metadata['summary'] = None

        current_manifest_files_data[relative_path_str] = metadata

    print(f"\n  Processamento concluído para {len(filtered_file_paths)} arquivos.")
    print(f"  Detecção AC6: {binary_file_count} arquivos binários.")
    print(f"  Cálculo AC10/11: Hashes SHA1 calculados ou nulos.")
    print(f"  Contagem Tokens (AC12-18): {token_api_calls_made} chamadas reais à API Gemini realizadas (após reuso de cache e retentativas).")

    manifest_data_final: Dict[str, Any] = {
        "_metadata": {
            "timestamp": datetime.datetime.now().isoformat(),
            "comment": f"Manifesto gerado - v1.19 (Rate Limit Handling/Key Rotation). Arquivos processados: {len(filtered_file_paths)}.", # Updated comment
            "output_file": str(output_filepath.relative_to(PROJECT_ROOT)),
            "args": vars(args),
            "previous_manifest_loaded": bool(previous_manifest_files_data),
            "files_found_before_filter": len(all_found_files_relative),
            "files_after_filter": len(filtered_file_paths),
            "binary_files_detected": binary_file_count,
            "gemini_initialized": gemini_initialized,
            "token_api_calls_made": token_api_calls_made,
        },
        "files": current_manifest_files_data # AC7
    }

    try:
        with open(output_filepath, 'w', encoding='utf-8') as f:
            json.dump(manifest_data_final, f, indent=4, ensure_ascii=False)
        print(f"\nManifesto JSON salvo em: {output_filepath.relative_to(PROJECT_ROOT)}")
    except Exception as e:
         print(f"\nErro ao salvar o arquivo de manifesto: {e}", file=sys.stderr)
         traceback.print_exc(file=sys.stderr)
         sys.exit(1)

    print(f"--- Geração do Manifesto Concluída (v1.19) ---")
    sys.exit(0)
