#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ==============================================================================
# generate_manifest.py (v1.9 - Implements AC5: File Filtering)
#
# Script para gerar um manifesto JSON estruturado do projeto, catalogando
# arquivos relevantes e extraindo metadados essenciais.
# Destinado a auxiliar ferramentas LLM e rastreamento de mudanças.
# AC3: Adiciona lógica para encontrar e carregar o manifesto anterior mais recente.
# AC4: Implementa a lógica de varredura de arquivos via git ls-files e scans adicionais.
# AC5: Implementa a filtragem de arquivos baseada em padrões padrão e argumentos --ignore.
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
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = BASE_DIR / "scripts" / "data"
TIMESTAMP_MANIFEST_REGEX = r'^\d{8}_\d{6}_manifest\.json$' # Regex para validar nome do arquivo
TIMESTAMP_DIR_REGEX = r'^\d{8}_\d{6}$' # Regex para validar nome de diretório timestamp
CONTEXT_CODE_DIR = BASE_DIR / "context_llm" / "code"
CONTEXT_COMMON_DIR = BASE_DIR / "context_llm" / "common"
VENDOR_USPDEV_DIRS = [
    BASE_DIR / "vendor/uspdev/replicado/src/",
    BASE_DIR / "vendor/uspdev/senhaunica-socialite/src/",
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
    ".env*",                        # Environment files (incl .env, .env.example etc) - Exclui por padrão
    "*.log",                        # Log files in general
    ".phpunit.cache/",              # PHPUnit cache
    "llm_outputs/",                 # LLM interaction script outputs
    "scripts/data/",                # Script data directory (incl. this manifest)
    "*.DS_Store",                   # macOS specific
    "Thumbs.db",                    # Windows specific
    "vendor/",                      # Default vendor dir (will be overridden by includes later)
    "context_llm/",                 # Default context dir (overridden by includes)
}

# --- Funções ---

def run_command(cmd_list: List[str], cwd: Path = BASE_DIR, check: bool = True, capture: bool = True, input_data: Optional[str] = None, shell: bool = False, timeout: Optional[int] = 60) -> Tuple[int, str, str]:
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
        help=f"Caminho para o arquivo JSON de saída. Padrão: {DEFAULT_OUTPUT_DIR.relative_to(BASE_DIR)}/YYYYMMDD_HHMMSS_manifest.json"
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
        if verbose: print(f"  Diretório de dados '{data_dir.relative_to(BASE_DIR)}' não encontrado. Nenhum manifesto anterior para carregar.")
        return {}
    manifest_files = [f for f in data_dir.glob('*_manifest.json') if f.is_file() and re.match(TIMESTAMP_MANIFEST_REGEX, f.name)]
    if not manifest_files:
        if verbose: print(f"  Nenhum arquivo de manifesto anterior encontrado em '{data_dir.relative_to(BASE_DIR)}'.")
        return {}
    latest_manifest_path = sorted(manifest_files, reverse=True)[0]
    if verbose: print(f"  Encontrado manifesto anterior mais recente: '{latest_manifest_path.relative_to(BASE_DIR)}'")
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
                    relative_path = absolute_path.relative_to(BASE_DIR)
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
            relative_scan_dir_str = str(scan_dir.relative_to(BASE_DIR)) if scan_dir.is_absolute() else str(scan_dir)
            if verbose: print(f"    Scanning recursively in '{relative_scan_dir_str}'...")
            count_a = 0
            for item in abs_scan_dir.rglob('*'):
                try:
                     if item.is_file(): # Check if it's a file
                         relative_path = item.resolve(strict=False).relative_to(BASE_DIR)
                         found_files.add(relative_path)
                         count_a += 1
                except ValueError:
                     if verbose: print(f"    Warning: Skipping file outside base dir? {item}")
                except Exception as e:
                    if verbose: print(f"    Warning: Error processing file during scan '{item}': {e}")

            if verbose: print(f"      Found {count_a} files in this directory scan.")
        elif verbose:
             try:
                 relative_scan_dir = scan_dir.relative_to(BASE_DIR)
                 if not str(relative_scan_dir).startswith("context_llm"):
                     print(f"    Warning: Additional scan directory not found: '{relative_scan_dir}'")
             except ValueError:
                  print(f"    Warning: Additional scan directory '{scan_dir}' is outside BASE_DIR.")


    if verbose: print(f"\n  Total unique files identified before filtering: {len(found_files)}")
    return found_files

# --- NOVA FUNÇÃO (AC5) ---
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
        ignore_patterns.add(output_filepath.relative_to(BASE_DIR).as_posix())
    except ValueError:
         print(f"Warning: Output path '{output_filepath}' seems outside BASE_DIR. Not adding to ignores.", file=sys.stderr)

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
# --- FIM DA NOVA FUNÇÃO ---


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
    print(f"Arquivo de Saída: {output_filepath.relative_to(BASE_DIR)}")

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

    # Placeholder para a lógica principal que virá nos próximos ACs
    print("\n[!] Lógica de geração de metadados (AC6+) será implementada nos próximos ACs.")

    # Exemplo de criação de um JSON (será substituído pela lógica real)
    # Formato final deve ser um dict: { "relative/path/file.php": { metadata... }, ... }
    current_manifest_files_data: Dict[str, Any] = {}
    # Iterar sobre filtered_file_paths agora
    for p in sorted(list(filtered_file_paths)):
         current_manifest_files_data[p.as_posix()] = { # Usar str(p.as_posix()) como chave
              "type": "pending_metadata...", # Placeholder
              "versioned": "pending...",
              "hash": None,
              "dependencies": None,
              "dependents": None,
              "summary": None,
              "needs_ai_update": "pending..."
         }
     # A lógica real iterará sobre os ARQUIVOS FILTRADOS e gerará metadados

    manifest_data_final: Dict[str, Any] = {
        "_metadata": {
            "timestamp": datetime.datetime.now().isoformat(),
            "comment": f"Manifesto gerado - AC5 Implementado. Arquivos filtrados: {len(filtered_file_paths)}.",
            "output_file": str(output_filepath.relative_to(BASE_DIR)),
            "args": vars(args),
            "previous_manifest_loaded": bool(previous_manifest_files_data),
            "files_found_before_filter": len(all_found_files_relative), # Add count before filtering
            "files_after_filter": len(filtered_file_paths) # Add count after filtering
        },
        "files": current_manifest_files_data # Adiciona os arquivos sob a chave "files"
    }


    try:
        with open(output_filepath, 'w', encoding='utf-8') as f:
            json.dump(manifest_data_final, f, indent=4, ensure_ascii=False)
        print(f"\nManifesto JSON (com arquivos filtrados) salvo em: {output_filepath.relative_to(BASE_DIR)}")
    except Exception as e:
         print(f"\nErro ao salvar o arquivo de manifesto: {e}", file=sys.stderr)
         traceback.print_exc(file=sys.stderr) # Adiciona traceback para depuração
         sys.exit(1)

    print("--- Geração do Manifesto Concluída (AC5 implementado) ---")
    sys.exit(0)