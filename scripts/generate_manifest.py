#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ==============================================================================
# generate_manifest.py (v1.11 - Implements AC8: File Type Categorization)
#
# Script para gerar um manifesto JSON estruturado do projeto, catalogando
# arquivos relevantes e extraindo metadados essenciais.
# Destinado a auxiliar ferramentas LLM e rastreamento de mudanças.
# AC3: Adiciona lógica para encontrar e carregar o manifesto anterior mais recente.
# AC4: Implementa a lógica de varredura de arquivos via git ls-files e scans adicionais.
# AC5: Implementa a filtragem de arquivos baseada em padrões padrão e argumentos --ignore.
# AC6: Adiciona detecção de arquivos binários (extensão + bytes) e planeja metadados nulos.
# AC7: Define a estrutura JSON final com chaves '_metadata' e 'files'.
# AC8: Implementa a função get_file_type para categorização granular.
#
# Uso:
#   python scripts/generate_manifest.py [-o output.json] [-i ignore_pattern] [-v]
#
# Argumentos:
#   -o, --output OUTPUT_PATH   Caminho para o arquivo JSON de saída.
#                              (Padrão: scripts/data/YYYYMMDD_HHMMSS_manifest.json)
#   -i, --ignore IGNORE_PATTERN Padrão (glob), diretório ou arquivo a ignorar. Use múltiplas vezes.
#   -v, --verbose              Habilita logging mais detalhado para depuração.
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
import time # Importado para run_command
import traceback # Importado para run_command e load_previous_manifest
import shlex # Importado para run_command
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set


# --- Constantes Globais ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent # Alterado para pegar a raiz do projeto
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "scripts" / "data"
TIMESTAMP_MANIFEST_REGEX = r'^\d{8}_\d{6}_manifest\.json$' # Regex para validar nome do arquivo
TIMESTAMP_DIR_REGEX = r'^\d{8}_\d{6}$' # Regex para validar nome de diretório timestamp
CONTEXT_CODE_DIR = PROJECT_ROOT / "context_llm" / "code"
CONTEXT_COMMON_DIR = PROJECT_ROOT / "context_llm" / "common"
VENDOR_USPDEV_DIRS = [
    PROJECT_ROOT / "vendor/uspdev/replicado/src/",
    PROJECT_ROOT / "vendor/uspdev/senhaunica-socialite/src/",
]

# AC5: Default ignore patterns set
DEFAULT_IGNORE_PATTERNS: Set[str] = {
    ".git/",                        # Git directory
    ".vscode/",                     # VSCode editor config
    ".idea/",                       # PHPStorm/IntelliJ editor config
    ".fleet/",                      # Fleet editor config
    "node_modules/",                # Node dependencies
    "storage/framework/cache/data/",# Laravel framework cache
    "storage/framework/sessions/",  # Laravel sessions
    "storage/framework/views/",     # Laravel compiled views
    "storage/logs/",                # Laravel logs
    "bootstrap/cache/",             # Laravel bootstrap cache
    "public/build/",                # Laravel compiled assets (Vite/Mix)
    "*.lock",                       # Dependency lock files (composer, npm, yarn)
    "*.sqlite",                     # SQLite databases
    "*.sqlite-journal",             # SQLite journals
    # ".env*",                        # Environment files (Removido dos defaults, cuidado ao commitar)
    "*.log",                        # Log files in general
    ".phpunit.cache/",              # PHPUnit cache
    "llm_outputs/",                 # LLM interaction script outputs
    "scripts/data/",                # Script data directory (incl. this manifest)
    "*.DS_Store",                   # macOS specific
    "Thumbs.db",                    # Windows specific
    "vendor/",                      # Default vendor dir (will be overridden by includes later)
    "context_llm/",                 # Default context dir (overridden by includes)
}

# AC6: Constants for Binary File Detection
BINARY_EXTENSIONS = {
    # Images
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.tif', '.tiff', '.webp',
    # Audio
    '.mp3', '.wav', '.ogg', '.aac', '.flac', '.m4a',
    # Video
    '.mp4', '.avi', '.mov', '.wmv', '.mkv', '.flv',
    # Compressed
    '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz',
    # Documents
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.odt', '.ods', '.odp',
    # Executables & Libraries
    '.exe', '.dll', '.so', '.dylib', '.app', '.bin', '.o', '.a',
    # Databases
    '.sqlite', '.db', # Note: .sqlite already ignored by default pattern
    # Fonts
    '.ttf', '.otf', '.woff', '.woff2', '.eot',
    # Other
    '.pyc', '.phar', '.jar', '.class', '.swf', '.dat',
}
TEXTCHARS = bytes(range(32, 127)) + b'\n\r\t\f\b' # Common printable ASCII + whitespace

# --- Funções ---

def run_command(cmd_list: List[str], cwd: Path = PROJECT_ROOT, check: bool = True, capture: bool = True, input_data: Optional[str] = None, shell: bool = False, timeout: Optional[int] = 60) -> Tuple[int, str, str]:
    """Runs a subprocess command and returns exit code, stdout, stderr."""
    cmd_str = shlex.join(cmd_list) if not shell else " ".join(map(shlex.quote, cmd_list)) # Safer joining for display
    # print(f"    Executing: {cmd_str}...") # Moved verbose logging inside main logic
    start_time = time.monotonic()
    try:
        process = subprocess.run(
            cmd_list if not shell else cmd_str, # Pass list unless shell=True
            capture_output=capture,
            text=True,
            input=input_data,
            check=check, # Raises CalledProcessError if check=True and return code is non-zero
            cwd=cwd,
            shell=shell,
            timeout=timeout,
            encoding='utf-8', errors='replace' # Add encoding/error handling
        )
        end_time = time.monotonic()
        duration = end_time - start_time
        # print(f"    Command finished in {duration:.2f}s with exit code {process.returncode}") # Moved verbose logging inside main logic
        return process.returncode, process.stdout or "", process.stderr or ""
    except FileNotFoundError:
        print(f"Error: Command '{cmd_list[0]}' not found. Is it installed and in PATH?", file=sys.stderr)
        return 1, "", f"Command not found: {cmd_list[0]}"
    except subprocess.TimeoutExpired:
        duration = time.monotonic() - start_time
        error_msg = f"Comando excedeu o tempo limite de {timeout} segundos: {cmd_str} ({duration:.2f}s)"
        print(f"    ERRO: {error_msg}", file=sys.stderr)
        return 1, "", error_msg
    except subprocess.CalledProcessError as e: # Only happens if check=True
        duration = time.monotonic() - start_time
        print(f"Error running command: {cmd_str} ({duration:.2f}s)", file=sys.stderr)
        print(f"Exit Code: {e.returncode}", file=sys.stderr)
        print(f"Stderr: {e.stderr or ''}", file=sys.stderr)
        print(f"Stdout: {e.stdout or ''}", file=sys.stderr)
        return e.returncode, e.stdout or "", e.stderr or ""
    except Exception as e:
        duration = time.monotonic() - start_time
        print(f"Unexpected error running command {cmd_str} ({duration:.2f}s): {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1, "", str(e)

def parse_arguments() -> argparse.Namespace:
    """Configura e processa os argumentos da linha de comando."""
    parser = argparse.ArgumentParser(
        description="Gera um manifesto JSON estruturado do projeto para análise e contexto.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""Exemplos:
  # Gerar manifesto com configurações padrão
  python {Path(__file__).name}

  # Especificar arquivo de saída
  python {Path(__file__).name} -o build/manifest.json

  # Ignorar arquivos específicos e um diretório
  python {Path(__file__).name} -i '*.tmp' -i 'docs/drafts/'

  # Habilitar modo verbose
  python {Path(__file__).name} -v
"""
    )
    parser.add_argument("-o", "--output", dest="output_path", type=str, default=None, help=f"Caminho para o arquivo JSON de saída. Padrão: {DEFAULT_OUTPUT_DIR.relative_to(PROJECT_ROOT)}/YYYYMMDD_HHMMSS_manifest.json")
    parser.add_argument("-i", "--ignore", dest="ignore_patterns", action="append", default=[], help="Padrão (glob), diretório ou arquivo a ignorar (além dos padrões). Use múltiplas vezes.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Habilita logging mais detalhado para depuração.")
    return parser.parse_args()

def setup_logging(verbose: bool):
    """Configura o nível de logging."""
    if verbose: print("Modo verbose habilitado.")
    pass

def get_default_output_filepath() -> Path:
    """Gera o caminho padrão para o arquivo de saída com timestamp."""
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}_manifest.json"
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_OUTPUT_DIR / filename

def load_previous_manifest(data_dir: Path, verbose: bool) -> Dict[str, Any]:
    """Encontra e carrega o manifesto anterior mais recente do diretório de dados."""
    if not data_dir.is_dir():
        if verbose: print(f"  Diretório de dados '{data_dir.relative_to(PROJECT_ROOT)}' não encontrado. Nenhum manifesto anterior para carregar.")
        return {}
    manifest_files = [f for f in data_dir.glob('*_manifest.json') if f.is_file() and re.match(TIMESTAMP_MANIFEST_REGEX, f.name)]
    if not manifest_files:
        if verbose: print(f"  Nenhum arquivo de manifesto anterior encontrado em '{data_dir.relative_to(PROJECT_ROOT)}'.")
        return {}
    latest_manifest_path = sorted(manifest_files, reverse=True)[0]
    if verbose: print(f"  Encontrado manifesto anterior mais recente: '{latest_manifest_path.relative_to(PROJECT_ROOT)}'")
    try:
        with open(latest_manifest_path, 'r', encoding='utf-8') as f: data = json.load(f)
        if verbose: print(f"  Manifesto anterior carregado com sucesso.")
        if isinstance(data, dict) and "files" in data and isinstance(data["files"], dict): return data["files"]
        elif isinstance(data, dict) and "_metadata" not in data: return data
        else: print(f"  Warning: Estrutura inesperada no manifesto anterior '{latest_manifest_path.name}'. Ignorando.", file=sys.stderr); return {}
    except Exception as e:
        print(f"  Erro ao carregar ou processar manifesto anterior '{latest_manifest_path.name}': {e}", file=sys.stderr)
        if verbose: traceback.print_exc(file=sys.stderr)
        return {}

def find_latest_context_code_dir(context_base_dir: Path) -> Optional[Path]:
    """Encontra o diretório de contexto mais recente dentro do diretório base."""
    if not context_base_dir.is_dir(): return None
    valid_context_dirs = [d for d in context_base_dir.iterdir() if d.is_dir() and re.match(TIMESTAMP_DIR_REGEX, d.name)]
    if not valid_context_dirs: return None
    return sorted(valid_context_dirs, reverse=True)[0]

def scan_project_files(verbose: bool) -> Set[Path]:
    """Escaneia o projeto para encontrar arquivos relevantes."""
    found_files: Set[Path] = set()
    if verbose: print("  Scanning versioned/tracked files using 'git ls-files'...")
    exit_code_ls, stdout_ls, stderr_ls = run_command(['git', 'ls-files', '-z', '-c', '-o', '--exclude-standard'], check=False)
    if exit_code_ls == 0 and stdout_ls:
        tracked_paths = filter(None, stdout_ls.split('\0'))
        count_v = 0
        for path_str in tracked_paths:
            try:
                absolute_path = PROJECT_ROOT / Path(path_str) # Assume relative to root
                if absolute_path.is_file():
                    relative_path = absolute_path.relative_to(PROJECT_ROOT)
                    found_files.add(relative_path)
                    count_v += 1
            except ValueError:
                 if verbose: print(f"    Warning: Skipping git ls-files entry outside base dir? {path_str}")
            except Exception as e:
                 if verbose: print(f"    Warning: Error processing git ls-files entry '{path_str}': {e}")
        if verbose: print(f"    Found {count_v} potentially versioned/tracked files via git ls-files.")
    else:
        print("  Warning: 'git ls-files' failed or returned no files. Proceeding with manual scans only.", file=sys.stderr)
        if stderr_ls and verbose: print(f"    Git stderr: {stderr_ls.strip()}", file=sys.stderr)

    additional_scan_dirs: List[Path] = [CONTEXT_COMMON_DIR]
    if latest_context_code_dir := find_latest_context_code_dir(CONTEXT_CODE_DIR): additional_scan_dirs.append(latest_context_code_dir)
    additional_scan_dirs.extend(VENDOR_USPDEV_DIRS)

    if verbose: print("\n  Performing additional scans for specific directories...")
    for scan_dir in additional_scan_dirs:
        abs_scan_dir = scan_dir.resolve(strict=False)
        if abs_scan_dir.is_dir():
            relative_scan_dir_str = str(scan_dir.relative_to(PROJECT_ROOT)) if scan_dir.is_absolute() else str(scan_dir)
            if verbose: print(f"    Scanning recursively in '{relative_scan_dir_str}'...")
            count_a = 0
            for item in abs_scan_dir.rglob('*'):
                try:
                    if item.is_file():
                        relative_path = item.resolve(strict=False).relative_to(PROJECT_ROOT)
                        found_files.add(relative_path)
                        count_a += 1
                except ValueError:
                     if verbose: print(f"    Warning: Skipping additional scan file outside base dir? {item}")
                except Exception as e:
                    if verbose: print(f"    Warning: Error processing file during additional scan '{item}': {e}")
            if verbose: print(f"      Found {count_a} files in this directory scan.")
        elif verbose:
             relative_scan_dir_str = str(scan_dir.relative_to(PROJECT_ROOT)) if scan_dir.is_absolute() else str(scan_dir)
             if not relative_scan_dir_str.startswith("context_llm/common"):
                 print(f"    Warning: Additional scan directory not found: '{relative_scan_dir_str}'")
    if verbose: print(f"\n  Total unique files identified before filtering: {len(found_files)}")
    return found_files

def filter_files(all_files: Set[Path], default_ignores: Set[str], custom_ignores: List[str], output_filepath: Path, verbose: bool) -> Set[Path]:
    """Filtra um conjunto de arquivos baseado em padrões de exclusão."""
    filtered_files: Set[Path] = set()
    ignored_count = 0
    ignore_patterns = default_ignores.copy()
    ignore_patterns.update(custom_ignores)
    try: ignore_patterns.add(output_filepath.relative_to(PROJECT_ROOT).as_posix())
    except ValueError:
         if verbose: print(f"  Warning: Output path '{output_filepath}' seems outside PROJECT_ROOT. Not adding to ignores.", file=sys.stderr)

    if verbose: print(f"  Applying {len(ignore_patterns)} unique ignore patterns...")
    for file_path in all_files:
        file_path_str = file_path.as_posix()
        is_ignored = False
        matched_pattern = None
        for pattern in ignore_patterns:
            is_dir_pattern = pattern.endswith('/')
            cleaned_pattern = pattern.rstrip('/')

            # 1. Direct match or directory prefix match
            if file_path_str == cleaned_pattern or (is_dir_pattern and file_path_str.startswith(cleaned_pattern + '/')):
                is_ignored = True
                matched_pattern = pattern
                break

            # 2. Glob pattern match using pathlib.match (relative path)
            try:
                if file_path.match(pattern):
                    is_ignored = True
                    matched_pattern = pattern
                    break
            except Exception as e:
                 if verbose: print(f"    Warning: Error matching pattern '{pattern}' against '{file_path_str}': {e}", file=sys.stderr)

        if not is_ignored:
            filtered_files.add(file_path)
        elif verbose:
            print(f"    Ignoring file due to pattern '{matched_pattern}': {file_path_str}")
            ignored_count += 1
    if verbose: print(f"  Ignored {ignored_count} files based on patterns.")
    print(f"  Total files after filtering: {len(filtered_files)}")
    return filtered_files

def is_likely_binary(file_path: Path, verbose: bool) -> bool:
    """Verifica se um arquivo é provavelmente binário."""
    if file_path.suffix.lower() in BINARY_EXTENSIONS:
        if verbose: print(f"      -> Detected as binary by extension ({file_path.suffix})")
        return True
    try:
        with open(file_path, 'rb') as f: chunk = f.read(512)
        if not chunk: return False
        if b'\0' in chunk:
            if verbose: print(f"      -> Detected as binary (contains null byte)")
            return True
        non_text_count = sum(1 for byte in chunk if bytes([byte]) not in TEXTCHARS)
        proportion = non_text_count / len(chunk)
        if proportion > 0.30:
            if verbose: print(f"      -> Detected as likely binary ({proportion:.1%} non-text bytes in first chunk)")
            return True
        else:
             if verbose: print(f"      -> Considered text ({proportion:.1%} non-text bytes)")
             return False
    except Exception as e:
        if verbose: print(f"      -> Could not perform content sniffing due to error: {e}. Assuming text for now.", file=sys.stderr)
        return False

# --- FUNÇÃO AC8 ---
def get_file_type(relative_path: Path) -> str:
    """
    Determina um tipo granular para o arquivo baseado em seu caminho e nome.

    Args:
        relative_path: Path objeto relativo à raiz do projeto.

    Returns:
        Uma string descritiva do tipo de arquivo.
    """
    path_str = relative_path.as_posix() # Usar posix para consistência
    parts = relative_path.parts
    name = relative_path.name
    suffix = relative_path.suffix.lower()

    # 1. Check by specific filenames (highest priority)
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

    # 2. Check by specific directories
    if parts[0] == 'app':
        if suffix == '.php':
            if 'Http/Controllers' in path_str: return 'code_php_controller'
            if 'Http/Middleware' in path_str: return 'code_php_middleware'
            if 'Http/Requests' in path_str: return 'code_php_request'
            if 'Models' in path_str: return 'code_php_model'
            if 'Providers' in path_str: return 'code_php_provider'
            if 'Console/Commands' in path_str: return 'code_php_command'
            if 'Services' in path_str: return 'code_php_service'
            if 'Actions' in path_str: return 'code_php_action'
            if 'Events' in path_str: return 'code_php_event'
            if 'Listeners' in path_str: return 'code_php_listener'
            if 'Jobs' in path_str: return 'code_php_job'
            if 'Mail' in path_str: return 'code_php_mailable'
            if 'Notifications' in path_str: return 'code_php_notification'
            if 'Policies' in path_str: return 'code_php_policy'
            if 'Rules' in path_str: return 'code_php_rule'
            if 'View/Components' in path_str: return 'code_php_view_component'
            if 'Livewire/Forms' in path_str: return 'code_php_livewire_form'
            if 'Livewire/Actions' in path_str: return 'code_php_livewire_action'
            if 'Livewire' in path_str: return 'code_php_livewire' # Generic Livewire PHP
            return 'code_php_app' # Default for app/
        elif suffix == '.blade.php' and 'Livewire' in path_str: return 'view_livewire_blade' # Livewire Blade

    if parts[0] == 'config' and suffix == '.php': return 'config_laravel'
    if parts[0] == 'database':
        if 'migrations' in parts and suffix == '.php': return 'migration_php'
        if 'factories' in parts and suffix == '.php': return 'code_php_factory'
        if 'seeders' in parts and suffix == '.php': return 'code_php_seeder'
    if parts[0] == 'lang':
        if suffix == '.php': return 'localization_php'
        if suffix == '.json': return 'localization_json'
    if parts[0] == 'public':
        if suffix == '.php': return 'code_php_public'
        if suffix == '.js': return 'asset_js'
        if suffix == '.css': return 'asset_css'
        if suffix in BINARY_EXTENSIONS: return f'asset_binary_{suffix[1:]}'
        if name == '.htaccess': return 'config_apache'
        return 'asset_public'
    if parts[0] == 'resources':
        if 'views' in parts and suffix == '.blade.php':
             if 'components' in parts: return 'view_blade_component'
             return 'view_blade'
        if 'css' in parts and suffix == '.css': return 'asset_source_css'
        if 'js' in parts and suffix == '.js': return 'asset_source_js'
        if 'images' in parts and suffix in BINARY_EXTENSIONS: return f'asset_source_image_{suffix[1:]}'
    if parts[0] == 'routes' and suffix == '.php': return 'code_php_route'
    if parts[0] == 'tests':
        if suffix == '.php':
            if 'Feature' in parts: return 'test_php_feature'
            if 'Unit' in parts: return 'test_php_unit'
            if 'Browser' in parts: return 'test_php_dusk'
            if 'Fakes' in parts: return 'test_php_fake'
            return 'test_php' # Generic test
    if parts[0] == 'docs':
        if suffix == '.md':
            if 'adr' in parts: return 'docs_adr_md'
            return 'docs_md'
    if parts[0] == 'scripts':
        if suffix == '.py': return 'code_python_script'
        if suffix == '.sh': return 'code_shell_script'
    if parts[0] == 'templates':
        if 'issue_bodies' in parts and suffix == '.md': return 'template_issue_body'
        if 'meta-prompts' in parts and suffix == '.txt': return 'template_meta_prompt'
        if 'prompts' in parts and suffix == '.txt': return 'template_prompt'

    # Check for USPDev Vendor dirs
    if 'vendor/uspdev/replicado/src' in path_str and suffix == '.php': return 'code_php_vendor_uspdev_replicado'
    if 'vendor/uspdev/senhaunica-socialite/src' in path_str and suffix == '.php': return 'code_php_vendor_uspdev_senhaunica'

    # Check for context files
    if parts[0] == 'context_llm':
        if parts[1] == 'common':
            if suffix == '.md' or suffix == '.txt': return 'context_common_doc'
            if suffix == '.json' or suffix == '.yaml' or suffix == '.yml': return 'context_common_config'
            return 'context_common_other'
        if parts[1] == 'code' and len(parts) > 2 and re.match(TIMESTAMP_DIR_REGEX, parts[2]): # Inside latest code dir
            if name.startswith('git_log'): return 'context_code_git_log'
            if name.startswith('git_diff'): return 'context_code_git_diff'
            if name.startswith('github_issue_'): return 'context_code_issue_details'
            if name.startswith('artisan_'): return 'context_code_artisan_output'
            if name.startswith('env_'): return 'context_code_env_info'
            if name.startswith('phpstan_'): return 'context_code_phpstan'
            if name.startswith('phpunit_'): return 'context_code_phpunit'
            if name.startswith('dusk_'): return 'context_code_dusk'
            if name.startswith('pint_'): return 'context_code_pint'
            if name == 'manifest.md': return 'context_code_manifest_summary'
            if name.endswith('_manifest.json'): return 'context_code_manifest_json' # Catch the copied JSON manifest
            # Add more specific context types here if needed
            return 'context_code_other' # Generic context file

    # 3. Check by general extension (lower priority)
    if suffix == '.php': return 'code_php'
    if suffix == '.js': return 'code_js'
    if suffix == '.py': return 'code_python'
    if suffix == '.sh': return 'code_shell'
    if suffix == '.json': return 'config_json'
    if suffix == '.yaml' or suffix == '.yml': return 'config_yaml'
    if suffix == '.md': return 'docs_md'
    if suffix == '.txt': return 'text_plain'
    if suffix == '.css': return 'style_css'
    if suffix in BINARY_EXTENSIONS: return f'binary_{suffix[1:]}' # Generic binary

    # Default fallback
    return 'unknown'
# --- FIM FUNÇÃO AC8 ---


# --- Bloco Principal ---
if __name__ == "__main__":
    args = parse_arguments()
    setup_logging(args.verbose)

    if args.output_path:
        output_filepath = Path(args.output_path).resolve()
        try: output_filepath.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e: print(f"Erro fatal: Não foi possível criar o diretório pai para o arquivo de saída '{output_filepath}': {e}", file=sys.stderr); sys.exit(1)
    else:
        output_filepath = get_default_output_filepath()

    print(f"--- Iniciando Geração do Manifesto ---")
    print(f"Arquivo de Saída: {output_filepath.relative_to(PROJECT_ROOT)}")

    # --- AC3: Carrega o manifesto anterior ---
    if args.verbose: print("\n[AC3] Carregando manifesto anterior (se existir)...")
    previous_manifest_files_data = load_previous_manifest(DEFAULT_OUTPUT_DIR, args.verbose)
    if previous_manifest_files_data: print(f"  Manifesto anterior carregado com dados para {len(previous_manifest_files_data)} arquivo(s).")
    else: print("  Nenhum manifesto anterior válido carregado. Será gerado um manifesto completo.")

    # --- AC4: Escaneia os arquivos do projeto ---
    print("\n[AC4] Escaneando arquivos do projeto...")
    all_found_files_relative: Set[Path] = scan_project_files(args.verbose)
    print(f"  Escaneamento concluído. Total de arquivos únicos identificados: {len(all_found_files_relative)}")

    # --- AC5: Aplica filtros de exclusão ---
    print("\n[AC5] Filtrando arquivos baseados nas regras de exclusão...")
    filtered_file_paths = filter_files(
        all_found_files_relative,
        DEFAULT_IGNORE_PATTERNS,
        args.ignore_patterns,
        output_filepath,
        args.verbose
    )

    # --- AC6+ Processing Loop (AC8 Integration) ---
    print("\n[AC6-AC8+] Processando arquivos filtrados e gerando metadados...")
    current_manifest_files_data: Dict[str, Any] = {}
    binary_file_count = 0
    processed_file_count = 0

    for file_path_relative in sorted(list(filtered_file_paths)):
        processed_file_count +=1
        file_path_absolute = PROJECT_ROOT / file_path_relative
        relative_path_str = file_path_relative.as_posix()
        if args.verbose: print(f"\n  Processing ({processed_file_count}/{len(filtered_file_paths)}): {relative_path_str}")

        is_binary = is_likely_binary(file_path_absolute, args.verbose)
        if is_binary: binary_file_count += 1

        # --- AC8: Get File Type ---
        file_type = get_file_type(file_path_relative)
        if args.verbose: print(f"      -> Type (AC8): {file_type}")
        # --- End AC8 ---

        # --- Placeholder for Future Metadata Generation (AC7+) ---
        metadata: Dict[str, Any] = {
            "type": file_type, # Use the determined type
            "versioned": "pending_AC9",
            "hash": None,
            "dependencies": None,
            "dependents": None, # AC14
            "summary": None, # AC15/AC16
            "needs_ai_update": "pending_AC17",
        }

        if is_binary:
            metadata['hash'] = None
            metadata['summary'] = None
            if args.verbose: print(f"      -> Binary: Setting hash and summary to null.")

        # Placeholder for other ACs...

        current_manifest_files_data[relative_path_str] = metadata


    print(f"\n  Processamento concluído para {len(filtered_file_paths)} arquivos.")
    print(f"  Detecção AC6: {binary_file_count} arquivos identificados como binários.")

    # --- Final Manifest Structure (AC7) ---
    manifest_data_final: Dict[str, Any] = {
        "_metadata": {
            "timestamp": datetime.datetime.now().isoformat(),
            "comment": f"Manifesto gerado - AC8 (File Type) Implementado. Metadados adicionais pendentes. Arquivos processados: {len(filtered_file_paths)}.", # Updated comment
            "output_file": str(output_filepath.relative_to(PROJECT_ROOT)),
            "args": vars(args),
            "previous_manifest_loaded": bool(previous_manifest_files_data),
            "files_found_before_filter": len(all_found_files_relative),
            "files_after_filter": len(filtered_file_paths),
            "binary_files_detected": binary_file_count
        },
        "files": current_manifest_files_data
    }

    try:
        with open(output_filepath, 'w', encoding='utf-8') as f:
            json.dump(manifest_data_final, f, indent=4, ensure_ascii=False)
        print(f"\nManifesto JSON (com arquivos filtrados) salvo em: {output_filepath.relative_to(PROJECT_ROOT)}")
    except Exception as e:
         print(f"\nErro ao salvar o arquivo de manifesto: {e}", file=sys.stderr)
         traceback.print_exc(file=sys.stderr)
         sys.exit(1)

    print(f"--- Geração do Manifesto Concluída (AC8 Implementado) ---")
    sys.exit(0)