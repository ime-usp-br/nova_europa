#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ==============================================================================
# llm_interact.py (v2.3 - Implemented manifest-summary task logic)
#
# Interacts with Google Gemini API using project context and prompt templates.
# Offers two flows:
# 1. Direct Flow (Default): Uses the selected template directly as the final prompt (one API call).
# 2. Two-Stage Flow (--two-stage flag): Uses the template as a meta-prompt to generate
#    a final prompt (first API call), then uses that final prompt to get the
#    final response (second API call).
# Allows interactive task selection if task is not provided via argument.
# Allows excluding specific context files via --exclude-context.
# Allows viewing the final prompt without API call via --only-prompt.
# Allows viewing the meta-prompt without API call via --only-meta.
# Supports Gemini API key rotation for rate limiting.
# Supports creating GitHub PRs via 'create-pr' task.
# Supports creating test sub-issues via 'create-test-sub-issue'.
# Supports updating documentation via 'update-doc'.
# Supports generating file summaries and updating the manifest via 'manifest-summary'.
#
# Dependencies: google-generativeai, python-dotenv, tqdm, argparse, standard libs
# ==============================================================================

import argparse
import os
import sys
import subprocess
from pathlib import Path
import re
import google.genai as genai
from google.genai import types
from google.genai import errors
from google.api_core import exceptions as google_api_core_exceptions
from dotenv import load_dotenv
import traceback
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Union, Any, Callable, Set
import time
from tqdm import tqdm
import shutil
import shlex
import json # Added for manifest-summary logic
import concurrent.futures # Added for API timeout

# --- Configuration Constants (Globally Accessible) ---
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = BASE_DIR / "templates/prompts"
META_PROMPT_DIR = BASE_DIR / "templates/meta-prompts"
CONTEXT_DIR_BASE = BASE_DIR / "context_llm/code"
COMMON_CONTEXT_DIR = BASE_DIR / "context_llm/common"
OUTPUT_DIR_BASE = BASE_DIR / "llm_outputs"
CONTEXT_GENERATION_SCRIPT = BASE_DIR / "scripts/generate_context.py"
MANIFEST_DATA_DIR = BASE_DIR / "scripts" / "data" # For manifest-summary task
TIMESTAMP_DIR_REGEX = r'^\d{8}_\d{6}$'
TIMESTAMP_MANIFEST_REGEX = r'^\d{8}_\d{6}_manifest\.json$' # For manifest-summary task
GEMINI_MODEL_GENERAL_TASKS = 'gemini-2.5-flash-preview-04-17' # Upgraded default model
GEMINI_MODEL_RESOLVE = 'gemini-2.5-pro-exp-03-25' # Upgraded default model
# Model for manifest summary - Flash for potentially faster/cheaper summaries
GEMINI_MODEL_SUMMARY = 'gemini-2.5-flash-preview-04-17' # Updated to latest flash
WEB_SEARCH_ENCOURAGEMENT_PT = "\n\nPara garantir a melhor resposta possível, sinta-se à vontade para pesquisar na internet usando a ferramenta de busca disponível."
DEFAULT_BASE_BRANCH = 'main'
PR_CONTENT_DELIMITER_TITLE = "--- PR TITLE ---"
PR_CONTENT_DELIMITER_BODY = "--- PR BODY ---"
SUMMARY_CONTENT_DELIMITER_START = "--- START OF FILE "
SUMMARY_CONTENT_DELIMITER_END = "--- END OF FILE "
SUMMARY_TOKEN_LIMIT_PER_CALL = 200000
ESTIMATED_TOKENS_PER_SUMMARY = 200
MAX_OUTPUT_TOKENS_ESTIMATE = 50000 
SLEEP_DURATION_SECONDS = 70 # Default sleep duration for rate limiting
DEFAULT_API_TIMEOUT_SECONDS = 60 # Default timeout for Gemini API calls

# --- Global Variables ---
api_keys_list: List[str] = []
current_api_key_index: int = 0
genai_client: Optional[genai.Client] = None
# Global ThreadPoolExecutor for API call timeouts
api_executor: Optional[concurrent.futures.ThreadPoolExecutor] = None

# --- Helper Functions ---

def find_command(primary: str, fallback: str) -> Optional[str]:
    if shutil.which(primary): return primary
    if shutil.which(fallback): return fallback
    return None

PYTHON_CMD = find_command("python3", "python")
PIP_CMD = find_command("pip3", "pip")

def command_exists(cmd: str) -> bool: return shutil.which(cmd) is not None

def suggest_install(cmd_name: str, pkg_name: Optional[str] = None) -> str:
    """Generates installation suggestion message."""
    pkg = pkg_name or cmd_name
    suggestions = [f"AVISO: Comando '{cmd_name}' não encontrado."]
    suggestions.append(f" > Para usar esta funcionalidade, tente instalar o pacote '{pkg}'.")
    # (installation suggestions for different OS omitted for brevity)
    if command_exists('apt'): suggestions.append(f" > Sugestão (Debian/Ubuntu): sudo apt update && sudo apt install -y {pkg}")
    elif command_exists('dnf'): suggestions.append(f" > Sugestão (Fedora): sudo dnf install -y {pkg}")
    elif command_exists('yum'): suggestions.append(f" > Sugestão (RHEL/CentOS): sudo yum install -y {pkg}")
    elif command_exists('pacman'): suggestions.append(f" > Sugestão (Arch): sudo pacman -Syu --noconfirm {pkg}")
    elif command_exists('brew'): suggestions.append(f" > Sugestão (macOS): brew install {pkg}")
    elif command_exists('zypper'): suggestions.append(f" > Sugestão (openSUSE): sudo zypper install -y {pkg}")
    else: suggestions.append(f" > Verifique o gerenciador de pacotes do seu sistema para instalar '{pkg}'.")
    return "\n".join(suggestions) + "\n"

def write_warning_to_file(output_file: Path, warning_message: str):
    """Writes a warning message to the specified output file."""
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(warning_message, encoding='utf-8')
        # print(f"    {warning_message.splitlines()[0]}") # Less noisy
    except Exception as e:
        print(f"    ERRO CRÍTICO: Não foi possível escrever o aviso em {output_file}: {e}", file=sys.stderr)

def run_command(cmd_list: List[str], cwd: Path = BASE_DIR, check: bool = True, capture: bool = True, input_data: Optional[str] = None, shell: bool = False, timeout: Optional[int] = 300) -> Tuple[int, str, str]:
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

def find_available_tasks(prompt_dir: Path) -> Dict[str, Path]:
    """Find available tasks (final prompts) in the specified directory."""
    tasks = {}
    if not prompt_dir.is_dir(): return tasks
    for filepath in prompt_dir.glob("prompt-*.txt"):
        if filepath.is_file():
            task_name = filepath.stem.replace("prompt-", "").replace("_", "-")
            if task_name: tasks[task_name] = filepath
    return tasks

def find_available_meta_tasks(prompt_dir: Path) -> Dict[str, Path]:
    """Find available meta tasks (meta-prompts) in the specified directory."""
    tasks = {}
    if not prompt_dir.is_dir(): return tasks
    for filepath in prompt_dir.glob("meta-prompt-*.txt"):
        if filepath.is_file():
            task_name = filepath.stem.replace("meta-prompt-", "").replace("_", "-")
            if task_name: tasks[task_name] = filepath
    return tasks

def find_latest_context_dir(context_base_dir: Path) -> Optional[Path]:
    """Find the most recent context directory within the base directory."""
    if not context_base_dir.is_dir():
        print(f"Error: Context base directory not found: {context_base_dir}", file=sys.stderr)
        return None
    valid_context_dirs = [d for d in context_base_dir.iterdir() if d.is_dir() and re.match(TIMESTAMP_DIR_REGEX, d.name)]
    if not valid_context_dirs:
        print(f"Error: No valid context directories found in {context_base_dir}", file=sys.stderr)
        return None
    return sorted(valid_context_dirs, reverse=True)[0]

def load_and_fill_template(template_path: Path, variables: Dict[str, str]) -> str:
    """Load a prompt/meta-prompt template and replace placeholders."""
    try:
        content = template_path.read_text(encoding='utf-8')
        def replace_match(match: re.Match[str]) -> str:
            var_name = match.group(1)
            return str(variables.get(var_name, ''))
        filled_content = re.sub(r'__([A-Z_]+)__', replace_match, content)
        return filled_content
    except FileNotFoundError: print(f"Error: Template file not found: {template_path}", file=sys.stderr); return ""
    except Exception as e: print(f"Error reading/processing template {template_path}: {e}", file=sys.stderr); return ""

def _load_files_from_dir(context_dir: Path, context_parts: List[types.Part], exclude_list: Optional[List[str]] = None) -> None:
    """Helper to load .txt, .json, .md files, excluding specified filenames."""
    file_patterns = ["*.txt", "*.json", "*.md"]
    loaded_count = 0
    excluded_count = 0
    exclude_set = set(exclude_list) if exclude_list else set()
    if not context_dir or not context_dir.is_dir(): return
    for pattern in file_patterns:
        for filepath in context_dir.glob(pattern):
            if filepath.is_file():
                if filepath.name in exclude_set: excluded_count += 1; continue
                try:
                    content = filepath.read_text(encoding='utf-8')
                    relative_path = filepath.relative_to(BASE_DIR)
                    context_parts.append(types.Part.from_text(text=f"--- START OF FILE {relative_path} ---\n{content}\n--- END OF FILE {relative_path} ---"))
                    loaded_count += 1
                except Exception as e: print(f"      - Warning: Could not read file {filepath.name}: {e}", file=sys.stderr)

def prepare_context_parts(primary_context_dir: Path, common_context_dir: Optional[Path] = None, exclude_list: Optional[List[str]] = None) -> List[types.Part]:
    """Prepare context files as types.Part, excluding specified filenames."""
    context_parts: List[types.Part] = []
    print("  Loading context files...")
    _load_files_from_dir(primary_context_dir, context_parts, exclude_list)
    if common_context_dir and common_context_dir.exists() and common_context_dir.is_dir():
        _load_files_from_dir(common_context_dir, context_parts, exclude_list)
    print(f"\n  Total context files loaded (after exclusions): {len(context_parts)}.")
    return context_parts

def save_llm_response(task_name: str, response_content: str) -> None:
    """Saves the LLM's final response."""
    try:
        task_output_dir = OUTPUT_DIR_BASE / task_name
        task_output_dir.mkdir(parents=True, exist_ok=True)
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{timestamp_str}.txt"
        output_filepath = task_output_dir / output_filename
        output_filepath.write_text(response_content, encoding='utf-8')
        print(f"  LLM Response saved to: {output_filepath.relative_to(BASE_DIR)}")
    except OSError as e: print(f"Error creating output directory {task_output_dir}: {e}", file=sys.stderr)
    except Exception as e: print(f"Error saving LLM response: {e}", file=sys.stderr); traceback.print_exc()

def parse_pr_content(llm_output: str) -> Tuple[Optional[str], Optional[str]]:
    """Parses the LLM output for create-pr task."""
    title_match = re.search(rf"^{re.escape(PR_CONTENT_DELIMITER_TITLE)}\s*(.*?)\s*{re.escape(PR_CONTENT_DELIMITER_BODY)}", llm_output, re.DOTALL | re.MULTILINE)
    body_match = re.search(rf"{re.escape(PR_CONTENT_DELIMITER_BODY)}\s*(.*)", llm_output, re.DOTALL | re.MULTILINE)
    if title_match and body_match:
        title = title_match.group(1).strip(); body = body_match.group(1).strip()
        if title and body is not None: return title, body
    print(f"Error: Could not parse LLM output for PR. Delimiters not found/formatted correctly.", file=sys.stderr)
    return None, None

def get_current_branch() -> Optional[str]:
    """Gets the current Git branch name."""
    exit_code, stdout, stderr = run_command(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], check=False)
    if exit_code == 0: return stdout.strip()
    print(f"Error getting current Git branch. Stderr: {stderr}", file=sys.stderr)
    return None

def check_new_commits(base_branch: str, head_branch: str) -> bool:
    """Checks for new commits on head branch vs base branch."""
    run_command(['git', 'fetch', 'origin', head_branch, base_branch], check=False)
    base_ref_to_compare = base_branch
    exit_code_remote, _, _ = run_command(['git', 'show-ref', '--verify', f'refs/remotes/origin/{base_branch}'], check=False)
    if exit_code_remote == 0: base_ref_to_compare = f'origin/{base_branch}'
    count_cmd = ['git', 'rev-list', '--count', f'{base_ref_to_compare}..{head_branch}']
    exit_code_count, stdout_count, stderr_count = run_command(count_cmd, check=False)
    if exit_code_count == 0:
        try: commit_count = int(stdout_count.strip()); print(f"  Found {commit_count} new commit(s) on '{head_branch}' compared to '{base_ref_to_compare}'."); return commit_count > 0
        except ValueError: print(f"Error parsing commit count: {stdout_count}", file=sys.stderr); return False
    else: print(f"Error checking commit count. Stderr: {stderr_count}", file=sys.stderr); return False

def create_github_pr(title: str, body: str, head_branch: str, base_branch: str, is_draft: bool) -> bool:
    """Creates a GitHub Pull Request using the gh CLI."""
    cmd = ['gh', 'pr', 'create', '--title', title, '--body', body, '--head', head_branch, '--base', base_branch]
    if is_draft: cmd.append('--draft')
    print("\nAttempting to create Pull Request...")
    exit_code, stdout, stderr = run_command(cmd, check=False)
    if exit_code == 0: print("Pull Request created successfully!"); print(f"  URL: {stdout.strip()}"); return True
    else: print(f"Error creating Pull Request (Code: {exit_code}). Stderr: {stderr.strip()}", file=sys.stderr); return False

def confirm_step(prompt: str) -> Tuple[str, Optional[str]]:
    """Asks the user for confirmation (Y/n/q). Prompts for observation if 'n'."""
    while True:
        response = input(f"{prompt} (Y/n/q - Yes/No+Feedback/Quit) [Y]: ").lower().strip()
        if response in ['y', 'yes', '']: return 'y', None
        elif response in ['n', 'no']:
            observation = input("Please enter your observation/rule to improve the previous step: ").strip()
            if not observation: print("Observation cannot be empty if you want to redo. Please try again or choose 'y'/'q'."); continue
            return 'n', observation
        elif response in ['q', 'quit']: return 'q', None
        else: print("Invalid input. Please enter Y, n, or q.")

GenerateContentConfigType = Union[types.GenerationConfig, types.GenerateContentConfig, Dict[str, Any], None]

def initialize_genai_client() -> bool:
    """Initializes or reinitializes the global genai_client."""
    global genai_client, api_keys_list, current_api_key_index
    if not api_keys_list:
        api_key_string = os.getenv('GEMINI_API_KEY')
        if not api_key_string: print("Error: GEMINI_API_KEY environment variable not set.", file=sys.stderr); return False
        api_keys_list = [key.strip() for key in api_key_string.split('|') if key.strip()]
        if not api_keys_list: print("Error: GEMINI_API_KEY format is invalid or empty.", file=sys.stderr); return False
        current_api_key_index = 0
        print(f"Loaded {len(api_keys_list)} API keys.")
    if not (0 <= current_api_key_index < len(api_keys_list)): print(f"Error: Invalid API key index.", file=sys.stderr); return False
    active_key = api_keys_list[current_api_key_index]
    try: genai_client = genai.Client(api_key=active_key); print("Google GenAI Client initialized successfully."); return True
    except Exception as e: print(f"Error initializing Google GenAI Client: {e}", file=sys.stderr); return False

def rotate_api_key_and_reinitialize() -> bool:
    """Rotates to the next API key and reinitializes the client."""
    global current_api_key_index, api_keys_list
    if not api_keys_list or len(api_keys_list) <= 1: print("Error: Cannot rotate API key.", file=sys.stderr); return False
    start_index = current_api_key_index
    current_api_key_index = (current_api_key_index + 1) % len(api_keys_list)
    print(f"\n---> Rotated API Key to Index {current_api_key_index} <---\n")
    if current_api_key_index == start_index: print("Warning: Cycled through all API keys.", file=sys.stderr)
    if not initialize_genai_client(): print(f"Error: Failed to reinitialize client.", file=sys.stderr); return False
    return True

def execute_gemini_call(model: str, contents: List[types.Part], config: Optional[GenerateContentConfigType] = None, sleep_on_retry: int = SLEEP_DURATION_SECONDS) -> str:
    """Executes Gemini API call with rate limit handling, key rotation, and timeout."""
    global genai_client, api_executor
    if not genai_client: raise RuntimeError("GenAI client not initialized.")
    if not api_executor: raise RuntimeError("API Executor not initialized.")

    initial_key_index = current_api_key_index
    keys_tried_in_this_call = {initial_key_index}

    while True:
        try:
            if args.with_sleep:
                 print(f"  --with-sleep active: Waiting {sleep_on_retry} seconds...")
                 for _ in tqdm(range(sleep_on_retry), desc="Waiting before API call", unit="s", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}s [{elapsed}<{remaining}]"): time.sleep(1)

            if isinstance(config, dict):
                tools_list = [types.Tool(google_search_retrieval=types.GoogleSearchRetrieval())] if config.get('tools') and config['tools'][0].get('google_search_retrieval') else []
                gen_config = types.GenerateContentConfig(tools=tools_list)
            elif isinstance(config, types.GenerateContentConfig): gen_config = config
            else: gen_config = None

            def _api_call_task() -> types.GenerateContentResponse:
                """Task for thread pool to make API call."""
                if not genai_client: raise RuntimeError("Gemini client became uninitialized in task.")
                return genai_client.models.generate_content(model=model, contents=contents, config=gen_config)

            future = api_executor.submit(_api_call_task)
            response = future.result(timeout=DEFAULT_API_TIMEOUT_SECONDS) # Usar timeout global

            if response.prompt_feedback and response.prompt_feedback.block_reason:
                 print(f"  Warning: Prompt blocked due to {response.prompt_feedback.block_reason}.", file=sys.stderr)
            if response.candidates:
                 for candidate in response.candidates:
                     if hasattr(candidate, 'finish_reason') and candidate.finish_reason not in (types.FinishReason.STOP, types.FinishReason.FINISH_REASON_UNSPECIFIED):
                         print(f"  Warning: Candidate finished with reason: {candidate.finish_reason.name}", file=sys.stderr)
                         if hasattr(candidate, 'finish_message') and candidate.finish_message: print(f"  Finish message: {candidate.finish_message}", file=sys.stderr)
            try: return response.text
            except (ValueError, AttributeError): print("Warning: Could not extract text from response. Returning empty.", file=sys.stderr); print(f"Full Response: {response}", file=sys.stderr); return ""

        except concurrent.futures.TimeoutError:
             print(f"  API call timed out after {DEFAULT_API_TIMEOUT_SECONDS}s. Retrying if possible...", file=sys.stderr)
             raise TimeoutError # Re-raise TimeoutError for outer loop handling or fallback

        except (google_api_core_exceptions.ResourceExhausted, errors.ServerError) as e:
            print(f"  API Error ({type(e).__name__}) detected with Key Index {current_api_key_index}. Waiting and rotating API key...", file=sys.stderr)
            for i in tqdm(range(sleep_on_retry), desc="Waiting for quota/retry", unit="s", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}s [{elapsed}<{remaining}]"): time.sleep(1)
            if not rotate_api_key_and_reinitialize(): print("Error: Could not rotate API key. Raising original error.", file=sys.stderr); raise e
            if current_api_key_index in keys_tried_in_this_call: print("Error: Cycled through all API keys. Rate limits persistent.", file=sys.stderr); raise e
            keys_tried_in_this_call.add(current_api_key_index)
            print(f"  Retrying API call with Key Index {current_api_key_index}...")

        except errors.APIError as e:
             print(f"  Google API Error: {e}", file=sys.stderr)
             status_code = getattr(e, 'code', None) or getattr(e, 'status_code', None)
             if status_code == 429:
                 print(f"  API Error 429 detected with Key Index {current_api_key_index}. Waiting and rotating API key...", file=sys.stderr)
                 for i in tqdm(range(sleep_on_retry), desc="Waiting for quota/retry", unit="s", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}s [{elapsed}<{remaining}]"): time.sleep(1)
                 if not rotate_api_key_and_reinitialize(): print("Error: Could not rotate API key. Raising original error.", file=sys.stderr); raise e
                 if current_api_key_index in keys_tried_in_this_call: print("Error: Cycled through all API keys. Rate limits persistent.", file=sys.stderr); raise e
                 keys_tried_in_this_call.add(current_api_key_index)
                 print(f"  Retrying API call with Key Index {current_api_key_index}...")
             else: raise e

        except Exception as e: print(f"Unexpected Error during API call: {e}", file=sys.stderr); traceback.print_exc(); raise

def modify_prompt_with_observation(original_prompt: str, observation: str) -> str:
    """Appends user observation to the prompt for retrying."""
    modified_prompt = f"{original_prompt}\n\n--- USER FEEDBACK FOR RETRY ---\n{observation}\n--- END FEEDBACK ---"
    print("\n  >>> Prompt modified with observation for retry <<<")
    return modified_prompt

def prompt_user_to_select_task(tasks: Dict[str, Path]) -> Optional[str]:
    """Displays available tasks and prompts user for selection."""
    print("\nPlease choose a task to perform:")
    sorted_tasks = sorted(tasks.keys())
    for i, task_name in enumerate(sorted_tasks): print(f"  {i + 1}: {task_name}")
    print("  q: Quit")
    while True:
        choice = input("Enter the number of the task (or 'q' to quit): ").strip().lower()
        if choice == 'q': return None
        try:
            index = int(choice) - 1
            if 0 <= index < len(sorted_tasks): selected_task = sorted_tasks[index]; print(f"  You selected task: {selected_task}"); return selected_task
            else: print("  Invalid number. Please try again.")
        except ValueError: print("  Invalid input. Please enter a number or 'q'.")

def find_documentation_files(base_dir: Path) -> List[Path]:
    """Find potential documentation files (.md) in the project."""
    print("  Scanning for documentation files...")
    found_paths: Set[Path] = set()
    for filename in ["README.md", "CHANGELOG.md"]:
        filepath = base_dir / filename
        if filepath.is_file(): found_paths.add(filepath.relative_to(base_dir))
    docs_dir = base_dir / "docs"
    if docs_dir.is_dir():
        for filepath in docs_dir.rglob("*.md"):
            if filepath.is_file(): found_paths.add(filepath.relative_to(base_dir))
    print(f"  Found {len(found_paths)} unique documentation files.")
    return sorted(list(found_paths), key=lambda p: str(p))

def prompt_user_to_select_doc(doc_files: List[Path]) -> Optional[Path]:
    """Displays a numbered list of doc files and prompts the user for selection."""
    print("\nMultiple documentation files found. Please choose one to update:")
    for i, filepath in enumerate(doc_files): print(f"  {i + 1}: {filepath}")
    print("  q: Quit")
    while True:
        choice = input("Enter the number of the file to update (or 'q' to quit): ").strip().lower()
        if choice == 'q': return None
        try:
            index = int(choice) - 1
            if 0 <= index < len(doc_files): selected_path = doc_files[index]; print(f"  You selected: {selected_path}"); return selected_path
            else: print("  Invalid number. Please try again.")
        except ValueError: print("  Invalid input. Please enter a number or 'q'.")

# --- Funções específicas para a task manifest-summary (AC7, AC8, AC9) ---

def find_latest_manifest_json(manifest_data_dir: Path) -> Optional[Path]:
    """Encontra o arquivo _manifest.json mais recente no diretório de dados."""
    if not manifest_data_dir.is_dir(): return None
    manifest_files = [f for f in manifest_data_dir.glob('*_manifest.json') if f.is_file() and re.match(TIMESTAMP_MANIFEST_REGEX, f.name)]
    if not manifest_files: return None
    return sorted(manifest_files, reverse=True)[0]

def load_manifest(manifest_path: Path) -> Optional[Dict[str, Any]]:
    """Carrega e parseia o arquivo de manifesto JSON."""
    if not manifest_path.is_file(): print(f"Error: Manifest file not found: {manifest_path}", file=sys.stderr); return None
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f: data = json.load(f)
        if not isinstance(data, dict) or "files" not in data or not isinstance(data["files"], dict):
            print(f"Error: Invalid manifest format in {manifest_path.name}. Missing 'files' dictionary.", file=sys.stderr)
            return None
        return data
    except json.JSONDecodeError as e: print(f"Error decoding JSON from {manifest_path.name}: {e}", file=sys.stderr); return None
    except Exception as e: print(f"Error reading manifest file {manifest_path.name}: {e}", file=sys.stderr); return None

def select_files_for_summary_batch(
    manifest_data: Dict[str, Any],
    all_candidates: List[str],
    processed_files: Set[str], # Set of filepaths already processed in previous batches
    max_files_per_call: int,
    max_input_tokens: int,
    max_output_tokens: int,
    est_tokens_per_summary: int
) -> Tuple[List[str], int, int]:
    """Seleciona um lote de arquivos para sumarização, respeitando os limites de token.
       Ignora arquivos individuais que excedam o limite de input e continua a busca.
    """
    batch_files = []
    current_input_tokens = 0
    current_estimated_output = 0
    files_dict = manifest_data.get("files", {})

    for filepath in all_candidates:
        if filepath in processed_files:
            # print(f"    Skipping '{filepath}': Already processed in a previous batch of this run.") # Debug
            continue # Skip already processed files

        if len(batch_files) >= max_files_per_call:
            # print(f"    Batch limit reached ({max_files_per_call} files). Stopping batch formation.") # Debug
            break # Limit number of files per batch

        metadata = files_dict.get(filepath)
        if not isinstance(metadata, dict):
            # print(f"    Skipping '{filepath}': Invalid metadata in manifest.") # Debug
            continue # Skip invalid entries

        file_token_count = metadata.get("token_count")
        if file_token_count is None or not isinstance(file_token_count, int) or file_token_count <= 0:
            # print(f"    Skipping '{filepath}' for batch: Invalid or missing token_count ({file_token_count}).") # Debug
            continue

        # --- ALTERAÇÃO INÍCIO ---
        # 1. Verificar se o arquivo *sozinho* já excede o limite de ENTRADA
        if file_token_count > max_input_tokens:
            print(f"    Skipping '{filepath}' for batch: Individual file token count ({file_token_count}) exceeds max input limit ({max_input_tokens}).")
            processed_files.add(filepath) # Marca como processado para não tentar de novo nesta execução
            continue # Pula para o PRÓXIMO ARQUIVO candidato

        # 2. Calcular totais potenciais se este arquivo for adicionado
        potential_input_tokens = current_input_tokens + file_token_count
        potential_output_tokens = current_estimated_output + est_tokens_per_summary

        # 3. Verificar se adicionar este arquivo excede os limites TOTAIS do lote
        if potential_input_tokens <= max_input_tokens and potential_output_tokens <= max_output_tokens:
            # Arquivo cabe no lote atual
            batch_files.append(filepath)
            current_input_tokens = potential_input_tokens
            current_estimated_output = potential_output_tokens
            # print(f"    Added '{filepath}' to batch. Current Input: {current_input_tokens}, Est. Output: {current_estimated_output}") # Debug
        else:
            # Arquivo não cabe no lote atual. Pular este arquivo e TENTAR O PRÓXIMO candidato.
            # print(f"    Cannot add '{filepath}' to current batch: Would exceed limits (Input: {potential_input_tokens}/{max_input_tokens} or Est. Output: {potential_output_tokens}/{max_output_tokens}). Trying next candidate.") # Debug
            continue # Tenta o próximo arquivo da lista `all_candidates` para ESTE MESMO lote.
        # --- ALTERAÇÃO FIM ---

    # Retorna o lote formado
    # print(f"  Batch formed with {len(batch_files)} files. Total Input: {current_input_tokens}, Total Est. Output: {current_estimated_output}") # Debug
    return batch_files, current_input_tokens, current_estimated_output

def prepare_api_content_for_summary(batch_files: List[str], base_summary_prompt: str) -> Tuple[List[types.Part], List[str]]:
    """Prepara a lista de conteúdos para a chamada API de sumarização."""
    contents_for_api: List[types.Part] = [types.Part.from_text(text=base_summary_prompt)]
    processed_paths = []
    for filepath_str in batch_files:
        filepath = BASE_DIR / filepath_str
        try:
            content = filepath.read_text(encoding='utf-8', errors='ignore')
            # Include path and metadata in the input part for context
            # The prompt needs to instruct the LLM to use this info
            part_text = f"{SUMMARY_CONTENT_DELIMITER_START}{filepath_str} ---\n{content}\n{SUMMARY_CONTENT_DELIMITER_END}{filepath_str} ---"
            contents_for_api.append(types.Part.from_text(text=part_text))
            processed_paths.append(filepath_str)
        except Exception as e:
            print(f"    Warning: Could not read file '{filepath_str}' for summary API call: {e}", file=sys.stderr)
    return contents_for_api, processed_paths

def parse_summaries_from_response(llm_response: str) -> Dict[str, str]:
    """Parseia a resposta da LLM para extrair sumários individuais."""
    summaries: Dict[str, str] = {}
    # Regex para encontrar os blocos delimitados
    pattern = re.compile(
        rf"^{re.escape(SUMMARY_CONTENT_DELIMITER_START)}(.*?){re.escape(' ---')}\n(.*?)\n^{re.escape(SUMMARY_CONTENT_DELIMITER_END)}\1{re.escape(' ---')}",
        re.MULTILINE | re.DOTALL
    )
    matches = pattern.findall(llm_response)
    for filepath, summary in matches:
        summaries[filepath.strip()] = summary.strip()
    return summaries

def update_manifest_file(manifest_path: Path, manifest_data: Dict[str, Any]) -> bool:
    """Escreve os dados atualizados de volta no arquivo de manifesto JSON."""
    try:
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving updated manifest file '{manifest_path.name}': {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return False

# --- Argument Parser Setup ---
def parse_arguments(all_available_tasks: List[str]) -> argparse.Namespace:
    """Sets up and parses command-line arguments."""
    script_name = Path(sys.argv[0]).name
    epilog_lines = ["\nExamples:"]
    epilog_lines.append("\n  # Direct Flow (Default):")
    epilog_lines.append(f"    python {script_name} commit-mesage -i 35")
    epilog_lines.append(f"    python {script_name} resolve-ac -i 35 -a 9 -o 'Use Service Pattern'")
    epilog_lines.append(f"    python {script_name} update-doc -i 35 -d README.md")
    epilog_lines.append(f"    python {script_name} manifest-summary --max-files-per-call 5 # Run summary task in smaller batches")
    epilog_lines.append("\n  # Two-Stage Flow (Meta-Prompt):")
    epilog_lines.append(f"    python {script_name} commit-mesage -i 35 --two-stage")
    epilog_lines.append(f"    python {script_name} resolve-ac -i 35 -a 9 --two-stage -om # Show meta-prompt only")
    epilog_text = "\n".join(epilog_lines)

    parser = argparse.ArgumentParser(
        description="Interact with Google Gemini using project context and prompt templates.",
        epilog=epilog_text,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    task_choices_str = ", ".join(all_available_tasks) if all_available_tasks else "None found"
    parser.add_argument("task", nargs='?', choices=all_available_tasks if all_available_tasks else None, help=f"Task to perform. If omitted, you'll be prompted. Available: {task_choices_str}", metavar="TASK")
    parser.add_argument("--two-stage", "-ts", action="store_true", help="Use two-stage meta-prompt flow.")
    parser.add_argument("-i", "--issue", help="Issue number. Fills placeholders. Required for 'create-pr'.")
    parser.add_argument("-a", "--ac", help="Acceptance Criteria number. Fills placeholders.")
    parser.add_argument("-o", "--observation", help="Additional observation/instruction. Fills __OBSERVACAO_ADICIONAL__.", default="")
    parser.add_argument("-d", "--doc-file", help="Target documentation file path for 'update-doc'. Relative to project root.")
    parser.add_argument("-b", "--target-branch", help=f"Target base branch for 'create-pr' (default: {DEFAULT_BASE_BRANCH}).", default=DEFAULT_BASE_BRANCH)
    parser.add_argument("--draft", action="store_true", help="Create PR as draft ('create-pr' task).")
    parser.add_argument("-w", "--web-search", action="store_true", help="Enable Google Search tool for Gemini.")
    parser.add_argument("-g", "--generate-context", action="store_true", help=f"Run '{CONTEXT_GENERATION_SCRIPT.name}' before interaction.")
    parser.add_argument("-y", "--yes", action="store_true", help="Auto-confirm intermediate LLM steps. Final action still requires confirmation.")
    parser.add_argument("-om", "--only-meta", action="store_true", help="Only print the filled meta-prompt (if --two-stage) and exit.")
    parser.add_argument("-op", "--only-prompt", action="store_true", help="Only print the final prompt (direct or generated in Step 1) and exit.")
    parser.add_argument("-ws", "--with-sleep", action="store_true", help=f"Wait {SLEEP_DURATION_SECONDS}s before each API attempt.")
    parser.add_argument("-ec", "--exclude-context", action='append', help="Filename(s) to exclude from context (e.g., -ec file1.txt). Can be used multiple times.", default=[])
    # Arguments for manifest-summary task (AC6 #38)
    parser.add_argument("--manifest-path", type=str, help="[manifest-summary] Specify the path to the manifest file to process (optional, defaults to latest).")
    parser.add_argument("--force-summary", action='append', help="[manifest-summary] Force summary generation for specific files (relative path), even if summary exists. Can be used multiple times.", default=[])
    parser.add_argument("--max-files-per-call", type=int, default=10, help=f"[manifest-summary] Max files per API call (default: 10). Affects token usage.")

    return parser.parse_args()


# --- Ponto de Entrada Principal ---
if __name__ == "__main__":
    dotenv_path = BASE_DIR / '.env'
    if dotenv_path.is_file(): load_dotenv(dotenv_path=dotenv_path, verbose=False)

    direct_tasks_dict = find_available_tasks(TEMPLATE_DIR)
    meta_tasks_dict = find_available_meta_tasks(META_PROMPT_DIR)
    all_tasks_dict = {**direct_tasks_dict, **meta_tasks_dict}
    all_task_names = list(all_tasks_dict.keys())

    try: args = parse_arguments(all_task_names)
    except SystemExit as e: sys.exit(e.code)

    selected_task = args.task
    if not selected_task:
        if not all_task_names: print("Error: No tasks found. Exiting.", file=sys.stderr); sys.exit(1)
        selected_task = prompt_user_to_select_task(all_tasks_dict)
        if not selected_task: print("No task selected. Exiting."); sys.exit(0)

    is_two_stage = args.two_stage
    prompt_path: Optional[Path] = None
    template_base_dir: Path

    if is_two_stage:
        prompt_path = meta_tasks_dict.get(selected_task)
        template_base_dir = META_PROMPT_DIR
        if not prompt_path: print(f"Error: Meta-prompt for '{selected_task}' not found in {template_base_dir.relative_to(BASE_DIR)}.", file=sys.stderr); sys.exit(1)
        print(f"\nSelected Flow: Two-Stage"); print(f"Using Meta-Prompt: {prompt_path.relative_to(BASE_DIR)}")
    else:
        prompt_path = direct_tasks_dict.get(selected_task)
        template_base_dir = TEMPLATE_DIR
        if not prompt_path: print(f"Error: Prompt for task '{selected_task}' not found in {template_base_dir.relative_to(BASE_DIR)}.", file=sys.stderr); sys.exit(1)
        print(f"\nSelected Flow: Direct"); print(f"Using Prompt: {prompt_path.relative_to(BASE_DIR)}")

    GEMINI_MODEL = GEMINI_MODEL_RESOLVE if selected_task == "resolve-ac" else GEMINI_MODEL_SUMMARY if selected_task == "manifest-summary" else GEMINI_MODEL_GENERAL_TASKS
    print(f"Using Gemini Model: {GEMINI_MODEL}")

    # --- Validations ---
    if selected_task == 'create-pr' and not args.issue: print("Error: 'create-pr' task requires --issue.", file=sys.stderr); sys.exit(1)
    if selected_task == 'create-test-sub-issue' and not args.issue: print("Error: 'create-test-sub-issue' task requires --issue.", file=sys.stderr); sys.exit(1)
    if selected_task == 'update-doc':
        if args.doc_file and not (BASE_DIR / args.doc_file).is_file():
             print(f"Error: Specified --doc-file '{args.doc_file}' not found relative to project root.", file=sys.stderr); sys.exit(1)
        elif not args.doc_file: print("Info: --doc-file not specified for update-doc. Will prompt for selection.")
    if selected_task == 'analyze-ac' and (not args.issue or not args.ac): print("Error: 'analyze-ac' task requires --issue and --ac.", file=sys.stderr); sys.exit(1)
    if selected_task == 'resolve-ac' and (not args.issue or not args.ac): print("Error: 'resolve-ac' task requires --issue and --ac.", file=sys.stderr); sys.exit(1)

    # --- Context Generation ---
    if args.generate_context:
        print(f"\nRunning context generation script: {CONTEXT_GENERATION_SCRIPT.relative_to(BASE_DIR)}...")
        if not CONTEXT_GENERATION_SCRIPT.is_file() or not os.access(CONTEXT_GENERATION_SCRIPT, os.X_OK):
             print(f"Error: Context script not found or not executable.", file=sys.stderr); sys.exit(1)
        exit_code_ctx, _, stderr_ctx = run_command([sys.executable, str(CONTEXT_GENERATION_SCRIPT)], check=False)
        if exit_code_ctx != 0: print(f"Error: Context generation failed. Stderr:\n{stderr_ctx}", file=sys.stderr); sys.exit(1)
        print("Context generation script completed.")

    # --- Load Context (Only if not manifest-summary) ---
    latest_context_dir: Optional[Path] = None
    context_parts: List[types.Part] = []
    if selected_task != "manifest-summary":
        latest_context_dir = find_latest_context_dir(CONTEXT_DIR_BASE)
        if latest_context_dir is None: print("Fatal Error: Could not find context directory.", file=sys.stderr); sys.exit(1)
        print(f"Latest Context Directory: {latest_context_dir.relative_to(BASE_DIR)}")
        context_parts = prepare_context_parts(latest_context_dir, COMMON_CONTEXT_DIR, args.exclude_context)
        if not context_parts: print("Warning: No context files loaded (or all were excluded). Proceeding without file context.", file=sys.stderr)

    # --- Prepare Variables ---
    task_variables: Dict[str, str] = {
        "NUMERO_DA_ISSUE": args.issue if args.issue else "",
        "NUMERO_DO_AC": args.ac if args.ac else "",
        "OBSERVACAO_ADICIONAL": args.observation,
        "ARQUIVO_DOC_ALVO": "",
        "PARENT_ISSUE_NUMBER": args.issue if args.issue else "",
        "PARENT_AC_NUMBER": args.ac if args.ac else ""
    }
    if selected_task == "update-doc":
        doc_file_path_str = args.doc_file
        if not doc_file_path_str:
             found_docs = find_documentation_files(BASE_DIR)
             if not found_docs: print("Error: No doc files found.", file=sys.stderr); sys.exit(1)
             selected_doc_path_relative = prompt_user_to_select_doc(found_docs)
             if not selected_doc_path_relative: print("User quit."); sys.exit(0)
             doc_file_path_str = str(selected_doc_path_relative)
        task_variables["ARQUIVO_DOC_ALVO"] = doc_file_path_str
        if not task_variables["ARQUIVO_DOC_ALVO"]: print("Error: Target doc file missing.", file=sys.stderr); sys.exit(1)
        print(f"Target document file set to: {task_variables['ARQUIVO_DOC_ALVO']}")

    # --- Load and Fill Initial Prompt ---
    initial_prompt_content_original = load_and_fill_template(prompt_path, task_variables)
    if not initial_prompt_content_original: print(f"Error loading initial prompt. Exiting.", file=sys.stderr); sys.exit(1)
    initial_prompt_content_current = initial_prompt_content_original
    if args.web_search: initial_prompt_content_current += WEB_SEARCH_ENCOURAGEMENT_PT

    # --- Handle --only-meta / --only-prompt ---
    if args.only_meta and is_two_stage: print("\n--- Filled Meta-Prompt (--only-meta) ---"); print(initial_prompt_content_current.strip()); print("--- End ---"); sys.exit(0)
    elif args.only_meta: print("Warning: --only-meta is only applicable with --two-stage flow.", file=sys.stderr)
    if args.only_prompt and not is_two_stage: print(f"\n--- Final Prompt (--only-prompt) ---"); print(initial_prompt_content_current.strip()); print("--- End ---"); sys.exit(0)

    # --- Initialize Client (if needed for API calls) ---
    if not args.only_prompt and not args.only_meta:
        if genai_client is None:
            if not initialize_genai_client(): sys.exit(1)
        # Initialize API executor only if client is ready and we might make API calls
        if genai_client: api_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    # --- Prepare Tools/Config ---
    tools_list = [types.Tool(google_search_retrieval=types.GoogleSearchRetrieval())] if args.web_search else []
    base_config = types.GenerateContentConfig(tools=tools_list) if tools_list else None

    # --- Task Specific Logic ---
    if selected_task == "manifest-summary":
        print("\n[TASK: manifest-summary]")
        manifest_to_process_path = None
        if args.manifest_path:
            manifest_to_process_path = Path(args.manifest_path).resolve()
            if not manifest_to_process_path.is_file(): print(f"Error: Specified manifest file not found: {args.manifest_path}", file=sys.stderr); sys.exit(1)
        else:
            manifest_to_process_path = find_latest_manifest_json(MANIFEST_DATA_DIR)
            if not manifest_to_process_path: print(f"Error: Could not find the latest manifest file in {MANIFEST_DATA_DIR}.", file=sys.stderr); sys.exit(1)

        print(f"  Processing manifest: {manifest_to_process_path.relative_to(BASE_DIR)}")
        manifest_data = load_manifest(manifest_to_process_path)
        if not manifest_data or "files" not in manifest_data: print(f"Error: Invalid or empty manifest file: {manifest_to_process_path.name}", file=sys.stderr); sys.exit(1)

        files_dict = manifest_data.get("files", {})
        candidates_for_summary = []
        print("  Identifying files needing summary...")
        for filepath, metadata in files_dict.items():
            if not isinstance(metadata, dict): continue
            if metadata.get("summary") is None and not metadata.get("type", "").startswith("binary_"):
                 if metadata.get("token_count") is not None: candidates_for_summary.append(filepath)
                 else: print(f"    Skipping '{filepath}' for summary: Missing token_count.", file=sys.stderr)

        if not candidates_for_summary: print("  No files found needing summaries in the manifest."); sys.exit(0)
        print(f"  Found {len(candidates_for_summary)} files potentially needing summaries.")

        if not genai_client or not api_executor: print("Error: Gemini client or API executor not initialized. Cannot proceed.", file=sys.stderr); sys.exit(1)

        summary_prompt_path = TEMPLATE_DIR / "prompt-manifest-summary.txt"
        if not summary_prompt_path.is_file(): print(f"Error: Summary prompt template not found at {summary_prompt_path}", file=sys.stderr); sys.exit(1)
        base_summary_prompt = summary_prompt_path.read_text(encoding='utf-8')

        processed_files_in_run: Set[str] = set()
        manifest_was_modified = False

        while True:
            batch_files, batch_input_tokens, batch_output_estimate = select_files_for_summary_batch(
                manifest_data, candidates_for_summary, processed_files_in_run,
                args.max_files_per_call, SUMMARY_TOKEN_LIMIT_PER_CALL,
                MAX_OUTPUT_TOKENS_ESTIMATE, ESTIMATED_TOKENS_PER_SUMMARY
            )

            if not batch_files: break # No more files to process

            print(f"\n  Processing batch of {len(batch_files)} files (Input Tokens: ~{batch_input_tokens}, Est. Output Tokens: ~{batch_output_estimate})...")

            contents_for_api, processed_paths_in_batch = prepare_api_content_for_summary(batch_files, base_summary_prompt)

            if not processed_paths_in_batch: print("    Batch empty after attempting to read files. Skipping batch."); continue

            print(f"    Sending {len(processed_paths_in_batch)} files to API for summarization...")
            try:
                 # Note: manifest-summary uses the direct flow, no meta-prompt step needed here.
                 llm_response = execute_gemini_call(GEMINI_MODEL_SUMMARY, contents_for_api, config=base_config, sleep_on_retry=SLEEP_DURATION_SECONDS)
                 print("    API call successful.")
                 parsed_summaries = parse_summaries_from_response(llm_response)
                 print(f"    Parsed {len(parsed_summaries)} summaries from response.")

                 updated_count_in_batch = 0
                 for filepath, summary in parsed_summaries.items():
                     if filepath in manifest_data["files"] and manifest_data["files"][filepath].get("summary") is None:
                         manifest_data["files"][filepath]["summary"] = summary
                         processed_files_in_run.add(filepath)
                         manifest_was_modified = True
                         updated_count_in_batch+=1
                     # else: print(f"    Warning: Parsed summary for '{filepath}' but no matching entry found or summary already exists.", file=sys.stderr)
                 print(f"    Applied {updated_count_in_batch} new summaries to manifest data for this batch.")

            except TimeoutError:
                print(f"  ERROR: API call timed out for batch. Skipping this batch.", file=sys.stderr)
            except Exception as e:
                print(f"  ERROR: Failed to process batch: {e}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                print("  Skipping this batch due to error.")

            # Add all attempted files in the batch to processed to avoid retrying them in this run
            processed_files_in_run.update(batch_files)


        if manifest_was_modified:
             if update_manifest_file(manifest_to_process_path, manifest_data): print(f"\nManifest file '{manifest_to_process_path.name}' updated successfully.")
             else: print(f"\nError: Failed to update manifest file '{manifest_to_process_path.name}'.", file=sys.stderr); sys.exit(1)
        else: print("\nNo summaries were generated or updated in the manifest.")

    else: # Other tasks (Existing logic)
        # --- Determine/Generate Final Prompt ---
        final_prompt_to_send: Optional[str] = None
        if is_two_stage:
            print("\nExecuting Two-Stage Flow (Step 1: Meta -> Final Prompt)...")
            prompt_final_content: Optional[str] = None
            meta_prompt_current = initial_prompt_content_current
            while True:
                print(f"\nStep 1: Sending Meta-Prompt + Context...")
                contents_step1 = [types.Part.from_text(text=meta_prompt_current)] + context_parts
                try:
                    prompt_final_content = execute_gemini_call(GEMINI_MODEL, contents_step1, config=base_config, sleep_on_retry=SLEEP_DURATION_SECONDS)
                    print("\n--- Generated Final Prompt (Step 1) ---"); print(prompt_final_content.strip()); print("---")
                    if args.yes: print("  Step 1 auto-confirmed (--yes)."); user_choice, observation = 'y', None
                    else: user_choice, observation = confirm_step("Use this generated prompt for Step 2?")
                    if user_choice == 'y': final_prompt_to_send = prompt_final_content; break
                    elif user_choice == 'q': print("Exiting after Step 1."); sys.exit(0)
                    elif user_choice == 'n': meta_prompt_current = modify_prompt_with_observation(meta_prompt_current, observation)
                    else: print("Internal error. Exiting.", file=sys.stderr); sys.exit(1)
                except Exception as e:
                     print(f"  Error during Step 1 API call: {e}", file=sys.stderr)
                     retry_choice, _ = confirm_step("API call failed in Step 1. Retry?")
                     if retry_choice != 'y': print("Exiting due to API error in Step 1."); sys.exit(1)
            if not final_prompt_to_send: print("Error: Could not obtain final prompt. Aborting.", file=sys.stderr); sys.exit(1)
            if args.web_search: final_prompt_to_send += WEB_SEARCH_ENCOURAGEMENT_PT
        else: final_prompt_to_send = initial_prompt_content_current

        if args.only_prompt: print(f"\n--- Final Prompt (--only-prompt) ---"); print(final_prompt_to_send.strip()); print("--- End ---"); sys.exit(0)

        # --- Execute Final API Call ---
        final_response_content: Optional[str] = None
        final_prompt_current = final_prompt_to_send
        while True:
            print(f"\n{'Step 2: Sending' if is_two_stage else 'Sending'} Final Prompt + Context...")
            contents_final = [types.Part.from_text(text=final_prompt_current)] + context_parts
            try:
                final_response_content = execute_gemini_call(GEMINI_MODEL, contents_final, config=base_config, sleep_on_retry=SLEEP_DURATION_SECONDS)
                print("\n--- Final Response ---"); print(final_response_content.strip()); print("---")
                if args.yes: print("  Response auto-confirmed (--yes)."); user_choice, observation = 'y', None
                else: user_choice, observation = confirm_step("Proceed with this final response?")
                if user_choice == 'y': break
                elif user_choice == 'q': print("Exiting."); sys.exit(0)
                elif user_choice == 'n': final_prompt_current = modify_prompt_with_observation(final_prompt_current, observation)
                else: print("Internal error. Exiting.", file=sys.stderr); sys.exit(1)
            except Exception as e:
                 print(f"  Error during final API call: {e}", file=sys.stderr)
                 retry_choice, _ = confirm_step("Final API call failed. Retry?")
                 if retry_choice != 'y': print("Exiting due to API error in final step."); sys.exit(1)

        # --- Final Action ---
        if final_response_content is None: print("Error: No final response obtained.", file=sys.stderr); sys.exit(1)

        if selected_task == 'create-pr':
            print("\nParsing PR content...")
            pr_title, pr_body = parse_pr_content(final_response_content)
            if pr_title and pr_body is not None:
                current_branch = get_current_branch()
                if not current_branch: print("Error: Cannot get current branch.", file=sys.stderr); sys.exit(1)
                target_branch = args.target_branch
                issue_ref_str = f"Closes #{args.issue}"
                if issue_ref_str not in pr_body: print(f"Appending '{issue_ref_str}'."); pr_body += f"\n\n{issue_ref_str}"
                if not check_new_commits(target_branch, current_branch): print(f"Error: No new commits on '{current_branch}' vs '{target_branch}'. Aborting PR.", file=sys.stderr); sys.exit(1)
                pr_confirm_choice, _ = confirm_step(f"Confirm creating {'DRAFT ' if args.draft else ''}PR: '{pr_title}'?")
                if pr_confirm_choice == 'y':
                    if create_github_pr(pr_title, pr_body, current_branch, target_branch, args.draft): print("\nPR creation process finished.")
                    else: print("\nPR creation failed.", file=sys.stderr); sys.exit(1)
                else: print("PR creation cancelled."); sys.exit(0)
            else: print("Error: Parsing PR content failed.", file=sys.stderr); sys.exit(1)
        else: # Default action: Save to file
            save_confirm_choice, _ = confirm_step("Confirm saving this response?")
            if save_confirm_choice == 'y':
                 print("\nSaving Final Response...")
                 save_llm_response(selected_task, final_response_content.strip())
            else: print("Save cancelled."); sys.exit(0)

    # Shutdown executor if it was initialized
    if api_executor:
        print("Shutting down API executor...")
        api_executor.shutdown(wait=False) # Don't wait indefinitely

    sys.exit(0)