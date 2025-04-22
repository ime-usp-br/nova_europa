#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ==============================================================================
# generate_manifest.py (v1.10 - Implements AC6: Binary File Detection)
#
# Script para gerar um manifesto JSON estruturado do projeto, catalogando
# arquivos relevantes e extraindo metadados essenciais.
# Destinado a auxiliar ferramentas LLM e rastreamento de mudanças.
# AC3: Adiciona lógica para encontrar e carregar o manifesto anterior mais recente.
# AC4: Implementa a lógica de varredura de arquivos via git ls-files e scans adicionais.
# AC5: Implementa a filtragem de arquivos baseada em padrões padrão e argumentos --ignore.
# AC6: Adiciona detecção de arquivos binários (extensão + bytes) e planeja metadados nulos.
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
    # ".env*",                        # Environment files (Removido dos defaults, mas cuidado ao commitar)
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
    """
    Configura e processa os argumentos da linha de comando.

    Returns:
        argparse.Namespace: Objeto contendo os argumentos processados.
    """
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

    parser.add_argument(
        "-o", "--output",
        dest="output_path",
        type=str, # Processaremos como Path mais tarde
        default=None,
        help=f"Caminho para o arquivo JSON de saída. Padrão: {DEFAULT_OUTPUT_DIR.relative_to(PROJECT_ROOT)}/YYYYMMDD_HHMMSS_manifest.json"
    )

    parser.add_argument(
        "-i", "--ignore",
        dest="ignore_patterns",
        action="append",
        default=[],
        help="Padrão (glob), diretório ou arquivo a ignorar (além dos padrões). Use múltiplas vezes."
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Habilita logging mais detalhado para depuração."
    )

    return parser.parse_args()

def setup_logging(verbose: bool):
    """Configura o nível de logging."""
    if verbose:
        print("Modo verbose habilitado.")
    # Placeholder for more complex logging if needed
    pass

def get_default_output_filepath() -> Path:
    """Gera o caminho padrão para o arquivo de saída com timestamp."""
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}_manifest.json"
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True) # Garante que o diretório exista
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
        # Retorna o dicionário 'files' se a estrutura for { "_metadata": {...}, "files": {...} }
        # Ou retorna o dict completo se a estrutura for { "path/file": {...} }
        if isinstance(data, dict) and "files" in data and isinstance(data["files"], dict):
             return data["files"]
        elif isinstance(data, dict) and "_metadata" not in data: # Assume it's the path -> metadata dict directly
            return data
        else: # Fallback ou estrutura inesperada
            print(f"  Warning: Estrutura inesperada no manifesto anterior '{latest_manifest_path.name}'. Ignorando.", file=sys.stderr)
            return {}
    except Exception as e:
        print(f"  Erro ao carregar ou processar manifesto anterior '{latest_manifest_path.name}': {e}", file=sys.stderr)
        if verbose: traceback.print_exc(file=sys.stderr)
        return {}

def find_latest_context_code_dir(context_base_dir: Path) -> Optional[Path]:
    """Find the most recent context directory within the base directory."""
    # Reutiliza a lógica de `llm_interact.py`/`generate_context.py`
    if not context_base_dir.is_dir():
        # print(f"Warning: Context base directory not found: {context_base_dir}", file=sys.stderr)
        return None
    # Ajuste para o regex correto do diretório
    valid_context_dirs = [d for d in context_base_dir.iterdir() if d.is_dir() and re.match(TIMESTAMP_DIR_REGEX, d.name)]
    if not valid_context_dirs:
        # print(f"Warning: No valid context directories found in {context_base_dir}", file=sys.stderr)
        return None
    return sorted(valid_context_dirs, reverse=True)[0]

def scan_project_files(verbose: bool) -> Set[Path]:
    """
    Scans the project directory to find relevant files using git ls-files
    and additional scans for specific directories.

    Args:
        verbose: Flag to enable detailed logging.

    Returns:
        A set of unique Path objects relative to the project root.
    """
    found_files: Set[Path] = set()

    # 1. Prioritize git ls-files for versioned files
    if verbose: print("  Scanning versioned files using 'git ls-files'...")
    # -z para null termination, -c para cached (stage), -o para others (untracked mas não ignorados)
    exit_code_ls, stdout_ls, stderr_ls = run_command(['git', 'ls-files', '-z', '-c', '-o', '--exclude-standard'], check=False)
    if exit_code_ls == 0 and stdout_ls:
        # Split by null character and filter empty strings
        tracked_paths = filter(None, stdout_ls.split('\0'))
        count_v = 0
        for path_str in tracked_paths:
            # Resolve to handle potential weirdness, then make relative
            try:
                absolute_path = Path(path_str).resolve(strict=False) # Don't fail on symlinks etc.
                if absolute_path.is_file(): # Check if it's a file *after* resolving
                    relative_path = absolute_path.relative_to(PROJECT_ROOT)
                    found_files.add(relative_path)
                    count_v += 1
            except ValueError:
                 if verbose: print(f"    Warning: Skipping file outside base dir? {path_str}")
            except Exception as e:
                 if verbose: print(f"    Warning: Error processing git ls-files entry '{path_str}': {e}")
        if verbose: print(f"    Found {count_v} potentially versioned/tracked files via git ls-files.")
    else:
        print("  Warning: 'git ls-files' failed or returned no files. Proceeding with manual scans only.", file=sys.stderr)
        if stderr_ls and verbose: print(f"    Git stderr: {stderr_ls.strip()}", file=sys.stderr)

    # 2. Additional scans for specific unversioned/vendor directories
    additional_scan_dirs: List[Path] = []
    additional_scan_dirs.append(CONTEXT_COMMON_DIR)
    if latest_context_code_dir := find_latest_context_code_dir(CONTEXT_CODE_DIR):
        additional_scan_dirs.append(latest_context_code_dir)
    else:
         if verbose: print(f"  Skipping scan: Latest context code directory not found in '{CONTEXT_CODE_DIR}'.")
    additional_scan_dirs.extend(VENDOR_USPDEV_DIRS)

    if verbose: print("\n  Performing additional scans for specific directories...")
    for scan_dir in additional_scan_dirs:
        abs_scan_dir = scan_dir.resolve(strict=False) # Resolve antes de verificar is_dir
        if abs_scan_dir.is_dir():
            relative_scan_dir_str = str(scan_dir.relative_to(PROJECT_ROOT)) if scan_dir.is_absolute() else str(scan_dir)
            if verbose: print(f"    Scanning recursively in '{relative_scan_dir_str}'...")
            count_a = 0
            for item in abs_scan_dir.rglob('*'):
                try:
                     if item.is_file(): # Check if it's a file
                         relative_path = item.resolve(strict=False).relative_to(PROJECT_ROOT)
                         found_files.add(relative_path)
                         count_a += 1
                except ValueError:
                     if verbose: print(f"    Warning: Skipping file outside base dir? {item}")
                except Exception as e:
                    if verbose: print(f"    Warning: Error processing file during scan '{item}': {e}")

            if verbose: print(f"      Found {count_a} files in this directory scan.")
        elif verbose:
             try:
                 relative_scan_dir = scan_dir.relative_to(PROJECT_ROOT)
                 # Avoid warning if common context dir doesn't exist yet
                 if not str(relative_scan_dir).startswith("context_llm/common"):
                     print(f"    Warning: Additional scan directory not found: '{relative_scan_dir}'")
             except ValueError:
                  print(f"    Warning: Additional scan directory '{scan_dir}' is outside PROJECT_ROOT.")


    if verbose: print(f"\n  Total unique files identified before filtering: {len(found_files)}")
    return found_files

# --- FUNÇÃO AC5 ---
def filter_files(
    all_files: Set[Path],
    default_ignores: Set[str],
    custom_ignores: List[str],
    output_filepath: Path,
    verbose: bool
) -> Set[Path]:
    """
    Filters a set of file paths based on ignore patterns.

    Args:
        all_files: Set of Path objects relative to the project root.
        default_ignores: Set of default ignore patterns (strings).
        custom_ignores: List of custom ignore patterns from CLI (strings).
        output_filepath: Path object of the manifest file itself (to ignore).
        verbose: Flag to enable detailed logging.

    Returns:
        A new set of Path objects containing only the files that were NOT ignored.
    """
    filtered_files: Set[Path] = set()
    ignored_count = 0

    # Combine ignore patterns and add the output file itself
    ignore_patterns = default_ignores.copy()
    ignore_patterns.update(custom_ignores)
    try:
        ignore_patterns.add(output_filepath.relative_to(PROJECT_ROOT).as_posix())
    except ValueError:
         if verbose: print(f"  Warning: Output path '{output_filepath}' seems outside PROJECT_ROOT. Not adding to ignores.", file=sys.stderr)

    if verbose: print(f"  Applying {len(ignore_patterns)} unique ignore patterns...")

    for file_path in all_files:
        file_path_str = file_path.as_posix() # Use POSIX paths for consistent matching
        is_ignored = False
        matched_pattern = None

        for pattern in ignore_patterns:
            # 1. Direct match or directory prefix match
            #    Ensure pattern ends with / for directory match if not already
            dir_pattern = pattern.rstrip('/') + '/'
            if file_path_str == pattern or file_path_str.startswith(dir_pattern):
                is_ignored = True
                matched_pattern = pattern
                break

            # 2. Glob pattern match using pathlib.match
            #    Handles patterns like *.log, src/**/*.php, etc.
            try:
                if file_path.match(pattern):
                    is_ignored = True
                    matched_pattern = pattern
                    break
            except Exception as e: # Path.match can fail on complex/invalid patterns
                 if verbose: print(f"    Warning: Error matching pattern '{pattern}' against '{file_path_str}': {e}", file=sys.stderr)


        if not is_ignored:
            filtered_files.add(file_path)
        elif verbose:
            print(f"    Ignoring file due to pattern '{matched_pattern}': {file_path_str}")
            ignored_count += 1

    if verbose: print(f"  Ignored {ignored_count} files based on patterns.")
    print(f"  Total files after filtering: {len(filtered_files)}")
    return filtered_files
# --- FIM FUNÇÃO AC5 ---

# --- FUNÇÃO AC6 ---
def is_likely_binary(file_path: Path, verbose: bool) -> bool:
    """
    Checks if a file is likely binary based on its extension and content sniffing.

    Args:
        file_path: Absolute Path object to the file.
        verbose: Flag to enable detailed logging.

    Returns:
        True if the file is likely binary, False otherwise.
    """
    # 1. Check by extension first (faster)
    if file_path.suffix.lower() in BINARY_EXTENSIONS:
        if verbose: print(f"      -> Detected as binary by extension ({file_path.suffix})")
        return True

    # 2. Content sniffing (only if extension doesn't match common binary ones)
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(512)  # Read the first 512 bytes
        if not chunk:
            if verbose: print(f"      -> Considered text (empty file)")
            return False  # Empty file is considered text

        # Check for null byte
        if b'\0' in chunk:
            if verbose: print(f"      -> Detected as binary (contains null byte)")
            return True

        # Heuristic: Check proportion of non-text characters
        non_text_count = sum(1 for byte in chunk if bytes([byte]) not in TEXTCHARS)
        proportion = non_text_count / len(chunk)
        if proportion > 0.30:  # Arbitrary threshold (adjust if needed)
            if verbose: print(f"      -> Detected as likely binary ({proportion:.1%} non-text bytes in first chunk)")
            return True
        else:
             if verbose: print(f"      -> Considered text ({proportion:.1%} non-text bytes)")
             return False

    except Exception as e:
        # If we can't read the file, we can't determine for sure.
        # Let's NOT classify it as binary, but the error should be logged elsewhere.
        if verbose: print(f"      -> Could not perform content sniffing due to error: {e}. Assuming text for now.", file=sys.stderr)
        return False
# --- FIM FUNÇÃO AC6 ---


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
    # -------------------------------------------

    # --- AC6+ Placeholder Loop & Binary Check ---
    print("\n[AC6+] Processando arquivos filtrados e gerando metadados (Placeholder - AC6 Focus)...")
    current_manifest_files_data: Dict[str, Any] = {}
    binary_file_count = 0

    # Iterar sobre os arquivos FILTRADOS
    for file_path_relative in sorted(list(filtered_file_paths)):
        file_path_absolute = PROJECT_ROOT / file_path_relative
        relative_path_str = file_path_relative.as_posix()
        if args.verbose: print(f"\n  Processing: {relative_path_str}")

        # --- AC6: Binary File Detection ---
        is_binary = is_likely_binary(file_path_absolute, args.verbose)
        if is_binary:
            binary_file_count += 1
        # --- Fim AC6 ---

        # --- Placeholder for Future Metadata Generation (AC7+) ---
        metadata: Dict[str, Any] = {
            "type": "pending_AC8",
            "versioned": "pending_AC9",
            "hash": None, # AC10/AC11/AC6
            "dependencies": None, # AC12/AC13 (default None for now)
            "dependents": None, # AC14 (Always None initially)
            "summary": None, # AC15/AC16 (Default None unless error or binary)
            "needs_ai_update": "pending_AC17",
        }

        # --- Lógica AC6 (Aplicada ao Placeholder) ---
        if is_binary:
            metadata['hash'] = None  # AC6 requirement
            metadata['summary'] = None # AC6 requirement
            if args.verbose: print(f"      -> Setting hash and summary to null for binary file.")
        # --- Fim Lógica AC6 ---

        # Placeholder for other ACs:
        # metadata['type'] = get_file_type(file_path_relative) # AC8
        # metadata['versioned'] = is_versioned(file_path_relative, versioned_files_set) # AC9
        # if not is_binary and not is_env_file(file_path_relative): # AC10/AC11
        #     try:
        #         metadata['hash'] = calculate_sha256(file_path_absolute)
        #     except Exception as e:
        #         metadata['summary'] = f"<<ERROR_READING_FILE: {e}>>" # AC16
        #         metadata['hash'] = None
        # metadata['dependencies'] = extract_php_dependencies(file_path_absolute) if is_php(file_path_relative) else [] # AC12/AC13 (simplified)
        # metadata['needs_ai_update'] = check_ai_update_needed(metadata, previous_manifest_files_data.get(relative_path_str)) # AC17

        current_manifest_files_data[relative_path_str] = metadata
    # --- Fim do Placeholder Loop ---

    print(f"\n  Detecção AC6: {binary_file_count} arquivos identificados como binários.")

    # --- Handling Removed Files (AC18 Placeholder) ---
    # files_in_previous = set(previous_manifest_files_data.keys())
    # files_in_current = set(current_manifest_files_data.keys())
    # removed_files = files_in_previous - files_in_current
    # if removed_files and args.verbose:
    #    print(f"\n[AC18] {len(removed_files)} files were present in the previous manifest but not found now (removed):")
    #    for removed in sorted(list(removed_files)): print(f"  - {removed}")
    # A lógica atual já não inclui arquivos removidos no 'current_manifest_files_data'

    # --- Final Manifest Structure ---
    manifest_data_final: Dict[str, Any] = {
        "_metadata": {
            "timestamp": datetime.datetime.now().isoformat(),
            "comment": f"Manifesto gerado - AC6 (Detecção Binária) Implementado. Lógica de metadados pendente. Arquivos processados: {len(filtered_file_paths)}.",
            "output_file": str(output_filepath.relative_to(PROJECT_ROOT)),
            "args": vars(args),
            "previous_manifest_loaded": bool(previous_manifest_files_data),
            "files_found_before_filter": len(all_found_files_relative),
            "files_after_filter": len(filtered_file_paths),
            "binary_files_detected": binary_file_count # Adiciona contagem AC6
        },
        "files": current_manifest_files_data # Adiciona os arquivos sob a chave "files"
    }

    try:
        with open(output_filepath, 'w', encoding='utf-8') as f:
            json.dump(manifest_data_final, f, indent=4, ensure_ascii=False)
        print(f"\nManifesto JSON (com arquivos filtrados) salvo em: {output_filepath.relative_to(PROJECT_ROOT)}")
    except Exception as e:
         print(f"\nErro ao salvar o arquivo de manifesto: {e}", file=sys.stderr)
         traceback.print_exc(file=sys.stderr) # Adiciona traceback para depuração
         sys.exit(1)

    print(f"--- Geração do Manifesto Concluída (AC6 Implementado) ---")
    sys.exit(0)