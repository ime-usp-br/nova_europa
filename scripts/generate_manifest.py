#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ==============================================================================
# generate_manifest.py (v1.14 - Implements AC12: Add token_count structure)
#
# Script para gerar um manifesto JSON estruturado do projeto, catalogando
# arquivos relevantes e extraindo metadados essenciais.
# Destinado a auxiliar ferramentas LLM e rastreamento de mudanças.
# AC3: Adiciona lógica para encontrar e carregar o manifesto anterior mais recente.
# AC4: Implementa a lógica de varredura de arquivos via git ls-files e scans adicionais.
# AC5: Implementa a filtragem de arquivos baseada em padrões padrão e argumentos --ignore.
# AC6: Adiciona detecção de arquivos binários (extensão + bytes) e metadados nulos.
# AC7: Define a estrutura JSON final com chaves '_metadata' e 'files'.
# AC8: Implementa a função get_file_type para categorização granular.
# AC9: Implementa a lógica para determinar o status 'versioned' (rastreado pelo Git).
# AC10/AC11: Implementa o cálculo do hash SHA1 e exclusões.
# AC12: Adiciona a chave 'token_count' a todos os arquivos e estrutura básica para contagem.
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
import time
import traceback
import shlex
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from dotenv import load_dotenv
import google.generativeai as genai # AC12: Import genai
from google.genai import types # AC12: Import types if needed for future config
from google.api_core import exceptions as google_api_core_exceptions # AC12: Import exceptions for future handling

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

# AC5: Default ignore patterns set
DEFAULT_IGNORE_PATTERNS: Set[str] = {
    ".git/", ".vscode/", ".idea/", ".fleet/", "node_modules/",
    "storage/framework/cache/data/", "storage/framework/sessions/",
    "storage/framework/views/", "storage/logs/", "bootstrap/cache/",
    "public/build/", "*.lock", "*.sqlite", "*.sqlite-journal", "*.log",
    ".phpunit.cache/", "llm_outputs/", "scripts/data/", "*.DS_Store",
    "Thumbs.db", "vendor/", "context_llm/", # Ignore entire context_llm dir initially
}

# AC6: Constants for Binary File Detection
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

# AC12/AC13: Constants for Token Counting
GEMINI_MODEL_NAME = 'gemini-1.5-flash' # As specified in AC13

# --- Variáveis Globais (incluindo novas para AC12+) ---
repo_owner: Optional[str] = None
GEMINI_API_KEY: Optional[str] = None # AC12
genai_client: Optional[genai.Client] = None # AC12
genai_model: Optional[genai.GenerativeModel] = None # AC12
api_key_loaded: bool = False # AC12: Track if key loaded
gemini_initialized: bool = False # AC12: Track if client/model initialized

# --- Funções (run_command, parse_arguments, setup_logging, get_default_output_filepath, find_latest_context_code_dir, is_likely_binary - sem mudanças significativas) ---
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
    parser = argparse.ArgumentParser( description="Gera um manifesto JSON estruturado do projeto.", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=f"""Exemplos:\n  python {Path(__file__).name}\n  python {Path(__file__).name} -o build/manifest.json\n  python {Path(__file__).name} -i '*.tmp' -i 'docs/drafts/' -v""")
    parser.add_argument("-o", "--output", dest="output_path", type=str, default=None, help=f"Caminho para o arquivo JSON de saída. Padrão: {DEFAULT_OUTPUT_DIR.relative_to(PROJECT_ROOT)}/YYYYMMDD_HHMMSS_manifest.json")
    parser.add_argument("-i", "--ignore", dest="ignore_patterns", action="append", default=[], help="Padrão (glob), diretório ou arquivo a ignorar. Use múltiplas vezes.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Habilita logging mais detalhado.")
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
    if file_path.suffix.lower() in BINARY_EXTENSIONS: return True
    try:
        with open(file_path, 'rb') as f: chunk = f.read(512)
        if not chunk: return False
        if b'\0' in chunk: return True
        non_text_count = sum(1 for byte in chunk if bytes([byte]) not in TEXTCHARS)
        proportion = non_text_count / len(chunk) if len(chunk) > 0 else 0
        return proportion > 0.30
    except Exception as e: return False # Assume non-binary on error

# --- Funções (load_previous_manifest, scan_project_files, filter_files, get_file_type - sem mudanças significativas) ---
def load_previous_manifest(data_dir: Path, verbose: bool) -> Dict[str, Any]:
    if not data_dir.is_dir(): return {}
    manifest_files = [f for f in data_dir.glob('*_manifest.json') if f.is_file() and re.match(TIMESTAMP_MANIFEST_REGEX, f.name)]
    if not manifest_files: return {}
    latest_manifest_path = sorted(manifest_files, reverse=True)[0]
    if verbose: print(f"  Encontrado manifesto anterior: '{latest_manifest_path.relative_to(PROJECT_ROOT)}'")
    try:
        with open(latest_manifest_path, 'r', encoding='utf-8') as f: data = json.load(f)
        if isinstance(data, dict) and "files" in data and isinstance(data["files"], dict): return data["files"]
        elif isinstance(data, dict) and "_metadata" not in data: return data # Assume old format
        else: return {}
    except Exception as e: return {}

def scan_project_files(verbose: bool) -> Tuple[Set[Path], Set[Path]]:
    all_files_set: Set[Path] = set()
    git_files_set: Set[Path] = set()
    exit_code_ls, stdout_ls, stderr_ls = run_command(['git', 'ls-files', '-z', '-c', '-o', '--exclude-standard'], check=False)
    if exit_code_ls == 0 and stdout_ls:
        tracked_paths = filter(None, stdout_ls.split('\0'))
        for path_str in tracked_paths:
            try:
                absolute_path = (PROJECT_ROOT / Path(path_str)).resolve(strict=True)
                if absolute_path.is_file():
                    relative_path = absolute_path.relative_to(PROJECT_ROOT)
                    all_files_set.add(relative_path)
                    git_files_set.add(relative_path)
            except (FileNotFoundError, ValueError, Exception): pass # Ignore files outside project or other errors
    additional_scan_dirs: List[Path] = [CONTEXT_COMMON_DIR]
    if latest_context_code_dir := find_latest_context_code_dir(CONTEXT_CODE_DIR): additional_scan_dirs.append(latest_context_code_dir)
    additional_scan_dirs.extend(VENDOR_USPDEV_DIRS)
    for scan_dir in additional_scan_dirs:
        abs_scan_dir = scan_dir.resolve(strict=False)
        if abs_scan_dir.is_dir():
            for item in abs_scan_dir.rglob('*'):
                try:
                    if item.is_file(): all_files_set.add(item.resolve(strict=True).relative_to(PROJECT_ROOT))
                except (FileNotFoundError, ValueError, Exception): pass
    return all_files_set, git_files_set

def filter_files(all_files: Set[Path], default_ignores: Set[str], custom_ignores: List[str], output_filepath: Path, verbose: bool) -> Set[Path]:
    filtered_files: Set[Path] = set()
    ignore_patterns = default_ignores.copy()
    ignore_patterns.update(custom_ignores)
    try: ignore_patterns.add(output_filepath.relative_to(PROJECT_ROOT).as_posix())
    except ValueError: pass
    for file_path in all_files:
        file_path_str = file_path.as_posix()
        is_ignored = False
        for pattern in ignore_patterns:
            is_dir_pattern = pattern.endswith('/')
            cleaned_pattern = pattern.rstrip('/')
            if file_path_str == cleaned_pattern or (is_dir_pattern and file_path_str.startswith(cleaned_pattern + '/')): is_ignored = True; break
            if pattern == "vendor/" and any(file_path_str.startswith(str(usp_dir.relative_to(PROJECT_ROOT)).replace('\\', '/')) for usp_dir in VENDOR_USPDEV_DIRS): continue
            if pattern == "context_llm/" and (file_path_str.startswith(str(CONTEXT_COMMON_DIR.relative_to(PROJECT_ROOT)).replace('\\', '/')) or ((latest_code_dir := find_latest_context_code_dir(CONTEXT_CODE_DIR)) and file_path_str.startswith(str(latest_code_dir.relative_to(PROJECT_ROOT)).replace('\\', '/')))): continue
            try:
                if file_path.match(pattern): is_ignored = True; break
            except Exception: pass
        if not is_ignored: filtered_files.add(file_path)
    return filtered_files

def get_file_type(relative_path: Path) -> str: # Simplified for brevity, assumed unchanged from AC8
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
            # Add more specific app types here...
            return 'code_php_app'
    if parts[0] == 'config' and suffix == '.php': return 'config_laravel'
    if parts[0] == 'database':
        if 'migrations' in parts and suffix == '.php': return 'migration_php'
        if 'factories' in parts and suffix == '.php': return 'code_php_factory'
        if 'seeders' in parts and suffix == '.php': return 'code_php_seeder'
    if parts[0] == 'resources' and 'views' in parts and suffix == '.blade.php': return 'view_blade'
    if parts[0] == 'routes' and suffix == '.php': return 'code_php_route'
    if parts[0] == 'tests':
        if suffix == '.php': return 'test_php'
    if parts[0] == 'scripts':
        if suffix == '.py': return 'code_python_script'
        if suffix == '.sh': return 'code_shell_script'
    if path_str.startswith('vendor/uspdev/') and suffix == '.php': return 'code_php_vendor_uspdev'
    if path_str.startswith('context_llm/common/'): return 'context_common'
    if path_str.startswith('context_llm/code/') and len(parts) > 2: return 'context_code' # Simplified
    if suffix == '.php': return 'code_php'
    if suffix in BINARY_EXTENSIONS: return f'binary_{suffix[1:]}'
    return 'unknown'

# --- AC12: Funções Novas para API Key e Gemini ---
def load_api_key(verbose: bool) -> bool:
    """Carrega a GEMINI_API_KEY do .env ou variáveis de ambiente."""
    global GEMINI_API_KEY, api_key_loaded
    if api_key_loaded: return True # Already loaded

    # Prioriza .env no diretório base do projeto
    dotenv_path = PROJECT_ROOT / '.env'
    if dotenv_path.is_file():
        if verbose: print(f"  Carregando variáveis de ambiente de: {dotenv_path.relative_to(PROJECT_ROOT)}")
        load_dotenv(dotenv_path=dotenv_path, verbose=verbose, override=True) # Override system vars if needed
    else:
        if verbose: print("  Arquivo .env não encontrado na raiz do projeto. Usando variáveis de ambiente do sistema (se existirem).")

    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    if not GEMINI_API_KEY:
        print("Erro: Variável de ambiente GEMINI_API_KEY não encontrada.", file=sys.stderr)
        print("  > Defina-a no seu arquivo .env ou nas variáveis de ambiente do sistema.", file=sys.stderr)
        api_key_loaded = False
        return False
    else:
        if verbose: print("  Chave de API GEMINI_API_KEY carregada com sucesso.")
        api_key_loaded = True
        return True

def initialize_gemini(verbose: bool) -> bool:
    """Inicializa o cliente e modelo Gemini se a chave foi carregada."""
    global genai_client, genai_model, gemini_initialized
    if gemini_initialized: return True # Already initialized
    if not api_key_loaded:
        if verbose: print("  Aviso: Chave de API não carregada. Impossível inicializar Gemini.")
        return False
    try:
        if verbose: print(f"  Inicializando Google GenAI Client e modelo '{GEMINI_MODEL_NAME}'...")
        genai.configure(api_key=GEMINI_API_KEY) # Configure directly
        genai_client = genai.Client() # Instantiate client (can be useful later)
        genai_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        print("  Cliente e modelo Gemini inicializados com sucesso.")
        gemini_initialized = True
        return True
    except Exception as e:
        print(f"Erro ao inicializar Google GenAI: {e}", file=sys.stderr)
        if verbose: traceback.print_exc(file=sys.stderr)
        gemini_initialized = False
        return False

# --- AC12: Placeholder para a função de contagem (será implementada nos ACs 13-18) ---
def count_tokens_for_file(
    filepath_absolute: Path,
    model: Optional[genai.GenerativeModel],
    previous_token_count: Optional[int],
    current_hash: Optional[str],
    previous_hash: Optional[str],
    verbose: bool
) -> Optional[int]:
    """
    (PLACEHOLDER AC12-18) Conta tokens de um arquivo usando a API Gemini,
    com lógica incremental e tratamento de erro.

    Retorna Optional[int] para representar a contagem ou falha/skip.
    """
    if not gemini_initialized or not model:
        if verbose: print(f"      -> Token Count (AC12+): Skipping (Gemini not initialized)")
        return None

    # Lógica Incremental (AC16 - será implementada aqui)
    if current_hash and previous_hash and current_hash == previous_hash and previous_token_count is not None:
         if verbose: print(f"      -> Token Count (AC16): Reusing previous count ({previous_token_count}) as hash matches.")
         return previous_token_count

    if verbose: print(f"      -> Token Count (AC12+): HASH different or no previous data. Counting needed (but placeholder for now).")

    # Lógica de Leitura e Chamada API (AC13, AC15, AC17, AC18 - será implementada aqui)
    # try:
    #     content = filepath_absolute.read_text(encoding='utf-8', errors='ignore')
    #     response = model.count_tokens(content) # Placeholder call
    #     token_count = response.total_tokens
    #     if verbose: print(f"      -> Token Count (AC13): Successfully counted: {token_count}")
    #     return token_count
    # except Exception as e:
    #     if verbose: print(f"      -> Token Count (AC14/18): Error counting tokens: {e}", file=sys.stderr)
    #     return None

    # Por enquanto, para AC12, só retornamos None para indicar que a estrutura existe
    return None


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

    # AC12: Carregar chave de API e inicializar Gemini
    if load_api_key(args.verbose):
        initialize_gemini(args.verbose)
    else:
        print("  Aviso: Incapaz de carregar a chave de API. A contagem de tokens será pulada.")

    if args.verbose: print("\n[AC3] Carregando manifesto anterior (se existir)...")
    previous_manifest_files_data = load_previous_manifest(DEFAULT_OUTPUT_DIR, args.verbose)

    print("\n[AC4 & AC9] Escaneando arquivos do projeto e identificando versionados...")
    all_found_files_relative, versioned_files_set = scan_project_files(args.verbose)

    print("\n[AC5] Filtrando arquivos baseados nas regras de exclusão...")
    filtered_file_paths = filter_files( all_found_files_relative, DEFAULT_IGNORE_PATTERNS, args.ignore_patterns, output_filepath, args.verbose)

    print("\n[AC6-AC12] Processando arquivos, gerando metadados (hash, tipo, token_count)...")
    current_manifest_files_data: Dict[str, Any] = {}
    binary_file_count = 0
    processed_file_count = 0

    for file_path_relative in sorted(list(filtered_file_paths)):
        processed_file_count += 1
        file_path_absolute = PROJECT_ROOT / file_path_relative
        relative_path_str = file_path_relative.as_posix()
        if args.verbose: print(f"\n  Processing ({processed_file_count}/{len(filtered_file_paths)}): {relative_path_str}")

        is_binary = is_likely_binary(file_path_absolute, args.verbose)
        if is_binary: binary_file_count += 1

        file_type = get_file_type(file_path_relative)
        if args.verbose: print(f"      -> Type (AC8): {file_type}")

        is_versioned = file_path_relative in versioned_files_set
        if relative_path_str.startswith(('vendor/uspdev/', 'context_llm/')): is_versioned = False
        if args.verbose: print(f"      -> Versioned (AC9): {is_versioned}")

        calculated_hash: Optional[str] = None
        is_env_file = file_type == 'environment_env'
        is_context_code = relative_path_str.startswith('context_llm/code/')
        should_calculate_hash = not is_binary and not is_env_file and not is_context_code

        if should_calculate_hash:
            try: calculated_hash = hashlib.sha1(file_path_absolute.read_bytes()).hexdigest()
            except Exception: pass # Handle read errors gracefully
        if args.verbose: print(f"      -> Hash (AC10/11): {calculated_hash or 'null (excluded/error)'}")

        # AC12: Initialize token_count to None
        token_count: Optional[int] = None

        # --- Placeholder for AC13-18 Logic ---
        should_count_tokens = gemini_initialized and not is_binary and not is_env_file and not is_context_code
        if should_count_tokens:
            previous_file_data = previous_manifest_files_data.get(relative_path_str, {})
            previous_hash = previous_file_data.get("hash")
            previous_count = previous_file_data.get("token_count")

            # Placeholder call - will be implemented later
            token_count = count_tokens_for_file(
                file_path_absolute,
                genai_model,
                previous_count,
                calculated_hash,
                previous_hash,
                args.verbose
            )
        elif args.verbose:
             reason = "binary" if is_binary else "env file" if is_env_file else "context_code file" if is_context_code else "Gemini not initialized"
             print(f"      -> Token Count (AC14): Skipping count ({reason}).")
        # --- End Placeholder ---

        metadata: Dict[str, Any] = {
            "type": file_type,
            "versioned": is_versioned,
            "hash": calculated_hash,
            "token_count": token_count, # AC12: Key is present, value is None for now
            "dependencies": [], # Placeholder
            "dependents": [], # Placeholder
            "summary": None, # Placeholder
        }
        if is_binary: metadata['summary'] = None # Ensure summary is null for binary

        current_manifest_files_data[relative_path_str] = metadata

    print(f"\n  Processamento concluído para {len(filtered_file_paths)} arquivos.")
    print(f"  Detecção AC6: {binary_file_count} arquivos binários.")
    print(f"  Cálculo AC10/11: Hashes SHA1 calculados ou nulos.")
    print(f"  Estrutura AC12: Chave 'token_count' adicionada (valor placeholder 'null').")

    manifest_data_final: Dict[str, Any] = {
        "_metadata": {
            "timestamp": datetime.datetime.now().isoformat(),
            "comment": f"Manifesto gerado - AC12 (token_count structure) Implementado. Contagem real pendente. Arquivos processados: {len(filtered_file_paths)}.",
            "output_file": str(output_filepath.relative_to(PROJECT_ROOT)),
            "args": vars(args),
            "previous_manifest_loaded": bool(previous_manifest_files_data),
            "files_found_before_filter": len(all_found_files_relative),
            "files_after_filter": len(filtered_file_paths),
            "binary_files_detected": binary_file_count,
            "gemini_initialized": gemini_initialized, # AC12: Indicate if token counting might be possible later
        },
        "files": current_manifest_files_data
    }

    try:
        with open(output_filepath, 'w', encoding='utf-8') as f:
            json.dump(manifest_data_final, f, indent=4, ensure_ascii=False)
        print(f"\nManifesto JSON (com estrutura token_count) salvo em: {output_filepath.relative_to(PROJECT_ROOT)}")
    except Exception as e:
         print(f"\nErro ao salvar o arquivo de manifesto: {e}", file=sys.stderr)
         traceback.print_exc(file=sys.stderr)
         sys.exit(1)

    print(f"--- Geração do Manifesto Concluída (AC12 Implementado) ---")
    sys.exit(0)