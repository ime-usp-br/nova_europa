#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ==============================================================================
# generate_manifest.py (v1.8 - Implements AC4: File Scanning Logic)
#
# Script para gerar um manifesto JSON estruturado do projeto, catalogando
# arquivos relevantes e extraindo metadados essenciais.
# Destinado a auxiliar ferramentas LLM e rastreamento de mudanças.
# AC3: Adiciona lógica para encontrar e carregar o manifesto anterior mais recente.
# AC4: Implementa a lógica de varredura de arquivos via git ls-files e scans adicionais.
#
# Uso:
#   python scripts/generate_manifest.py [-o output.json] [-i ignore_pattern] [-v]
#
# Argumentos:
#   -o, --output OUTPUT_PATH   Caminho para o arquivo JSON de saída.
#                              (Padrão: scripts/data/YYYYMMDD_HHMMSS_manifest.json)
#   -i, --ignore IGNORE_PATTERN Padrão (glob), diretório ou arquivo a ignorar. Pode ser usado várias vezes.
#   -v, --verbose              Habilita logging mais detalhado.
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
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
import traceback
import shlex # Importado para run_command

# --- Constantes Globais ---
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = BASE_DIR / "scripts" / "data"
TIMESTAMP_MANIFEST_REGEX = r'^\d{8}_\d{6}_manifest\.json$' # Regex para validar nome do arquivo
CONTEXT_CODE_DIR = BASE_DIR / "context_llm" / "code"
CONTEXT_COMMON_DIR = BASE_DIR / "context_llm" / "common"
VENDOR_USPDEV_DIRS = [
    BASE_DIR / "vendor/uspdev/replicado/src/",
    BASE_DIR / "vendor/uspdev/senhaunica-socialite/src/",
]

# TODO (AC5): Refinar estas listas e lógicas de exclusão/inclusão
DEFAULT_IGNORE_PATTERNS: Set[str] = {
    ".git/",
    ".vscode/",
    ".idea/",
    ".fleet/",
    "node_modules/",
    # "vendor/", # Removido temporariamente - refinar no AC5
    "storage/framework/", # Ignorar cache, views, sessions
    "storage/logs/",      # Ignorar logs
    "bootstrap/cache/",   # Ignorar cache de bootstrap
    "public/build/",      # Ignorar assets compilados
    "*.lock",
    "*.sqlite",
    "*.sqlite-journal",
    ".env*", # Ignorar arquivos .env por padrão
    "*.log",
    ".phpunit.cache/",
    # "context_llm/", # Removido temporariamente - refinar no AC5
    "llm_outputs/", # Ignorar saídas LLM
    "scripts/data/", # Ignorar diretório de dados de scripts (incluindo este manifesto)
    "*.DS_Store",
    "Thumbs.db"
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
            timeout=timeout
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
    valid_context_dirs = [d for d in context_base_dir.iterdir() if d.is_dir() and re.match(TIMESTAMP_DIR_REGEX.replace("_manifest.json", ""), d.name)] # Adjusted Regex
    if not valid_context_dirs:
        # print(f"Warning: No valid context directories found in {context_base_dir}", file=sys.stderr)
        return None
    return sorted(valid_context_dirs, reverse=True)[0]

# --- NOVA FUNÇÃO (AC4) ---
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
    exit_code, stdout, stderr = run_command(['git', 'ls-files', '-z'], check=False) # -z for null termination
    if exit_code == 0 and stdout:
        # Split by null character and filter empty strings
        versioned_paths = filter(None, stdout.split('\0'))
        count = 0
        for path_str in versioned_paths:
            path_obj = Path(path_str).resolve() # Resolve to absolute first
            if path_obj.is_file(): # Ensure it's actually a file
                try:
                    found_files.add(path_obj.relative_to(BASE_DIR))
                    count += 1
                except ValueError:
                     if verbose: print(f"    Warning: Skipping file outside base dir? {path_obj}")
        if verbose: print(f"    Found {count} versioned files via git.")
    else:
        print("  Warning: 'git ls-files' failed or returned no files. Proceeding with manual scans only.", file=sys.stderr)
        if stderr and verbose: print(f"    Git stderr: {stderr.strip()}", file=sys.stderr)

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
        if scan_dir.is_dir():
            if verbose: print(f"    Scanning recursively in '{scan_dir.relative_to(BASE_DIR)}'...")
            count = 0
            for item in scan_dir.rglob('*'):
                if item.is_file():
                     try:
                         found_files.add(item.resolve().relative_to(BASE_DIR))
                         count += 1
                     except ValueError:
                         if verbose: print(f"    Warning: Skipping file outside base dir? {item}")
            if verbose: print(f"      Found {count} files in this directory.")
        elif verbose:
            # Only warn if it's not the context dir (which might not exist initially)
             if not str(scan_dir).startswith(str(CONTEXT_CODE_DIR)):
                  print(f"    Warning: Additional scan directory not found: '{scan_dir.relative_to(BASE_DIR)}'")


    if verbose: print(f"\n  Total unique files identified before filtering: {len(found_files)}")
    return found_files

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
    all_found_files = scan_project_files(args.verbose)
    print(f"  Escaneamento concluído. Total de arquivos únicos identificados: {len(all_found_files)}")
    # -------------------------------------------

    # Placeholder para a lógica principal que virá nos próximos ACs
    print("\n[!] Lógica de filtragem (AC5) e geração de metadados (AC6+) será implementada nos próximos ACs.")

    ignore_list = list(DEFAULT_IGNORE_PATTERNS) + args.ignore_patterns
    if args.verbose:
        print(f"\nLista final de ignorados (a ser aplicada no AC5):")
        for item in sorted(ignore_list): print(f" - {item}")

    # TODO AC5: Aplicar filtros de exclusão (ignore_list, e filtro para o próprio output_filepath) em `all_found_files`
    # TODO AC6-11: Identificar tipos, calcular hash (se aplicável), gerar metadados para cada ARQUIVO FILTRADO
    # TODO AC12-13: Extrair dependências PHP (Usará 'previous_manifest_files_data')
    # TODO AC14-17: Calcular `needs_ai_update` (Usará 'previous_manifest_files_data')
    # TODO AC18: Comparar com manifesto anterior ('previous_manifest_files_data')
    # TODO AC19: Implementar tratamento de erro
    # TODO AC20-21: Garantir qualidade
    # TODO AC22: Ser chamado pelo generate_context.py

    # Exemplo de criação de um JSON (será substituído pela lógica real)
    # Formato final deve ser um dict: { "relative/path/file.php": { metadata... }, ... }
    manifest_data: Dict[str, Any] = {
        "_metadata": {
            "timestamp": datetime.datetime.now().isoformat(),
            "comment": "Manifesto inicial - Lógica de preenchimento pendente (ACs 5+)",
            "output_file": str(output_filepath.relative_to(BASE_DIR)),
            "args": vars(args),
            "previous_manifest_loaded": bool(previous_manifest_files_data),
            "files_found_before_filter": len(all_found_files) # Add count before filtering
        },
        "files": {
            # Exemplo:
             str(p.as_posix()): { # Usar str(p.as_posix()) como chave
                  "type": "pending...",
                  "versioned": "pending...",
                  "hash": None,
                  "dependencies": None,
                  "dependents": None,
                  "summary": None,
                  "needs_ai_update": "pending..."
            } for p in sorted(list(all_found_files))[:5] # Mostra só 5 como exemplo
            # A lógica real iterará sobre os ARQUIVOS FILTRADOS
        }
    }

    try:
        with open(output_filepath, 'w', encoding='utf-8') as f:
            json.dump(manifest_data, f, indent=4, ensure_ascii=False)
        print(f"\nManifesto JSON (placeholder) salvo em: {output_filepath.relative_to(BASE_DIR)}")
    except Exception as e:
         print(f"\nErro ao salvar o arquivo de manifesto: {e}", file=sys.stderr)
         sys.exit(1)

    print("--- Geração do Manifesto Concluída (com lógica pendente) ---")
    sys.exit(0)