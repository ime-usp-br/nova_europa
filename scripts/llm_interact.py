#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ==============================================================================
# llm_interact.py (v2.1 - Adds --only-prompt and --exclude-context flags)
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
from typing import List, Dict, Tuple, Optional, Union, Any, Callable
import time
from tqdm import tqdm
import shutil
import shlex # Import shlex for run_command

# --- Configuration ---
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = BASE_DIR / "templates/prompts" # Updated template directory
META_PROMPT_DIR = BASE_DIR / "templates/meta-prompts" # Keep for two-stage flow
CONTEXT_DIR_BASE = BASE_DIR / "context_llm/code"
COMMON_CONTEXT_DIR = BASE_DIR / "context_llm/common"
OUTPUT_DIR_BASE = BASE_DIR / "llm_outputs"
CONTEXT_GENERATION_SCRIPT = BASE_DIR / "scripts/generate_context.py" # Updated path
TIMESTAMP_DIR_REGEX = r'^\d{8}_\d{6}$'
GEMINI_MODEL_GENERAL_TASKS = 'gemini-2.5-pro-exp-03-25'
GEMINI_MODEL_RESOLVE = 'gemini-2.5-pro-exp-03-25'
WEB_SEARCH_ENCOURAGEMENT_PT = "\n\nPara garantir a melhor resposta possível, sinta-se à vontade para pesquisar na internet usando a ferramenta de busca disponível."
DEFAULT_BASE_BRANCH = 'main'
PR_CONTENT_DELIMITER_TITLE = "--- PR TITLE ---"
PR_CONTENT_DELIMITER_BODY = "--- PR BODY ---"
SLEEP_DURATION_SECONDS = 70 # Default sleep for rate limit retry

# --- Global Variables ---
api_keys_list: List[str] = []
current_api_key_index: int = 0
genai_client: Optional[genai.Client] = None

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
    if command_exists('apt'): suggestions.append(f" > Sugestão (Debian/Ubuntu): sudo apt update && sudo apt install -y {pkg}")
    elif command_exists('dnf'): suggestions.append(f" > Sugestão (Fedora): sudo dnf install -y {pkg}")
    elif command_exists('yum'): suggestions.append(f" > Sugestão (RHEL/CentOS): sudo yum install -y {pkg}")
    elif command_exists('pacman'): suggestions.append(f" > Sugestão (Arch): sudo pacman -Syu --noconfirm {pkg}")
    elif command_exists('brew'): suggestions.append(f" > Sugestão (macOS): brew install {pkg}")
    elif command_exists('zypper'): suggestions.append(f" > Sugestão (openSUSE): sudo zypper install -y {pkg}")
    else: suggestions.append(f" > Verifique o gerenciador de pacotes do seu sistema para instalar '{pkg}'.")
    return "\n".join(suggestions) + "\n"

def run_command(cmd_list: List[str], cwd: Path = BASE_DIR, check: bool = True, capture: bool = True, input_data: Optional[str] = None, shell: bool = False, timeout: Optional[int] = 300) -> Tuple[int, str, str]:
    """Runs a subprocess command and returns exit code, stdout, stderr."""
    cmd_str = shlex.join(cmd_list) if not shell else " ".join(map(shlex.quote, cmd_list))
    print(f"    Executing: {cmd_str}...")
    start_time = time.monotonic()
    try:
        process = subprocess.run(
            cmd_list if not shell else cmd_str,
            capture_output=capture, text=True, input=input_data,
            check=check, cwd=cwd, shell=shell, timeout=timeout
        )
        duration = time.monotonic() - start_time
        print(f"    Command finished in {duration:.2f}s with exit code {process.returncode}")
        return process.returncode, process.stdout or "", process.stderr or ""
    except FileNotFoundError:
        print(f"Error: Command '{cmd_list[0]}' not found.", file=sys.stderr)
        return 1, "", f"Command not found: {cmd_list[0]}"
    except subprocess.TimeoutExpired:
        duration = time.monotonic() - start_time
        error_msg = f"Comando excedeu o tempo limite de {timeout} segundos: {cmd_str} ({duration:.2f}s)"
        print(f"    ERRO: {error_msg}", file=sys.stderr)
        return 1, "", error_msg
    except subprocess.CalledProcessError as e:
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


def find_available_tasks(prompt_dir: Path) -> Dict[str, Path]:
    """Find available tasks (final prompts) in the specified directory."""
    tasks = {}
    if not prompt_dir.is_dir():
        print(f"Error: Prompt directory not found: {prompt_dir}", file=sys.stderr)
        return tasks
    # Expected pattern: prompt-task_name.txt
    for filepath in prompt_dir.glob("prompt-*.txt"):
        if filepath.is_file():
            task_name = filepath.stem.replace("prompt-", "").replace("_", "-")
            if task_name:
                tasks[task_name] = filepath
    return tasks

def find_available_meta_tasks(prompt_dir: Path) -> Dict[str, Path]:
    """Find available meta tasks (meta-prompts) in the specified directory."""
    tasks = {}
    if not prompt_dir.is_dir():
        print(f"Error: Meta-prompt directory not found: {prompt_dir}", file=sys.stderr)
        return tasks
    # Expected pattern: meta-prompt-task_name.txt
    for filepath in prompt_dir.glob("meta-prompt-*.txt"):
        if filepath.is_file():
            task_name = filepath.stem.replace("meta-prompt-", "").replace("_", "-")
            if task_name:
                tasks[task_name] = filepath
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
    except FileNotFoundError:
        print(f"Error: Template file not found: {template_path}", file=sys.stderr)
        return ""
    except Exception as e:
        print(f"Error reading/processing template {template_path}: {e}", file=sys.stderr)
        return ""

# --- Updated _load_files_from_dir to handle exclusions ---
def _load_files_from_dir(context_dir: Path, context_parts: List[types.Part], exclude_list: Optional[List[str]] = None) -> None:
    """Helper to load .txt, .json, .md files, excluding specified filenames."""
    file_patterns = ["*.txt", "*.json", "*.md"]
    loaded_count = 0
    excluded_count = 0
    exclude_set = set(exclude_list) if exclude_list else set()

    if not context_dir or not context_dir.is_dir(): return
    print(f"    Scanning directory: {context_dir.relative_to(BASE_DIR)}")
    for pattern in file_patterns:
        for filepath in context_dir.glob(pattern):
            if filepath.is_file():
                # --- Check exclusion ---
                if filepath.name in exclude_set:
                    print(f"      - Excluding file: {filepath.name}")
                    excluded_count += 1
                    continue
                # --- End exclusion check ---
                try:
                    content = filepath.read_text(encoding='utf-8')
                    relative_path = filepath.relative_to(BASE_DIR)
                    context_parts.append(types.Part.from_text(text=f"--- START OF FILE {relative_path} ---\n{content}\n--- END OF FILE {relative_path} ---"))
                    loaded_count += 1
                except Exception as e: print(f"      - Warning: Could not read file {filepath.name}: {e}", file=sys.stderr)
    if loaded_count == 0: print(f"      - No eligible context files found in this directory.")
    if excluded_count > 0: print(f"      - Excluded {excluded_count} file(s) based on --exclude-context.")

# --- Updated prepare_context_parts to accept and pass exclude_list ---
def prepare_context_parts(primary_context_dir: Path, common_context_dir: Optional[Path] = None, exclude_list: Optional[List[str]] = None) -> List[types.Part]:
    """Prepare context files as types.Part, excluding specified filenames."""
    context_parts: List[types.Part] = []
    print("  Loading context files...")
    _load_files_from_dir(primary_context_dir, context_parts, exclude_list) # Pass exclude_list
    if common_context_dir and common_context_dir.exists() and common_context_dir.is_dir():
        print("\n  Loading from common context directory...")
        _load_files_from_dir(common_context_dir, context_parts, exclude_list) # Pass exclude_list
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
        title = title_match.group(1).strip()
        body = body_match.group(1).strip()
        if title and body is not None: return title, body
    print(f"Error: Could not parse LLM output for PR. Delimiters '{PR_CONTENT_DELIMITER_TITLE}' or '{PR_CONTENT_DELIMITER_BODY}' not found/formatted incorrectly.", file=sys.stderr)
    return None, None

def get_current_branch() -> Optional[str]:
    """Gets the current Git branch name."""
    exit_code, stdout, stderr = run_command(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], check=False)
    if exit_code == 0: return stdout.strip()
    print(f"Error getting current Git branch. Stderr: {stderr}", file=sys.stderr)
    return None

def check_new_commits(base_branch: str, head_branch: str) -> bool:
    """Checks for new commits on head branch vs base branch."""
    print(f"  Fetching origin for branches '{head_branch}' and '{base_branch}'...")
    run_command(['git', 'fetch', 'origin', head_branch, base_branch], check=False) # Allow graceful fail
    base_ref_to_compare = base_branch
    exit_code_remote, _, _ = run_command(['git', 'show-ref', '--verify', f'refs/remotes/origin/{base_branch}'], check=False)
    if exit_code_remote == 0:
        base_ref_to_compare = f'origin/{base_branch}'
        print(f"  Comparing against remote base: {base_ref_to_compare}")
    else:
        print(f"  Warning: Remote base 'origin/{base_branch}' not found. Comparing against local '{base_branch}'.")

    count_cmd = ['git', 'rev-list', '--count', f'{base_ref_to_compare}..{head_branch}']
    exit_code_count, stdout_count, stderr_count = run_command(count_cmd, check=False)
    if exit_code_count == 0:
        try:
            commit_count = int(stdout_count.strip())
            print(f"  Found {commit_count} new commit(s) on '{head_branch}' compared to '{base_ref_to_compare}'.")
            return commit_count > 0
        except ValueError:
            print(f"Error parsing commit count: {stdout_count}", file=sys.stderr)
            return False
    else:
        print(f"Error checking commit count. Stderr: {stderr_count}", file=sys.stderr)
        return False # Assume no new commits if check fails

def create_github_pr(title: str, body: str, head_branch: str, base_branch: str, is_draft: bool) -> bool:
    """Creates a GitHub Pull Request using the gh CLI."""
    cmd = ['gh', 'pr', 'create', '--title', title, '--body', body, '--head', head_branch, '--base', base_branch]
    if is_draft: cmd.append('--draft')
    print("\nAttempting to create Pull Request...")
    # Confirmation is now handled by confirm_step before calling this function
    exit_code, stdout, stderr = run_command(cmd, check=False)
    if exit_code == 0:
        print("Pull Request created successfully!")
        print(f"  URL: {stdout.strip()}")
        return True
    else:
        print(f"Error creating Pull Request (Code: {exit_code}). Stderr: {stderr.strip()}", file=sys.stderr)
        return False

def confirm_step(prompt: str) -> Tuple[str, Optional[str]]:
    """Asks the user for confirmation (Y/n/q). Prompts for observation if 'n'."""
    while True:
        response = input(f"{prompt} (Y/n/q - Yes/No+Feedback/Quit) [Y]: ").lower().strip()
        if response in ['y', 'yes', '']: return 'y', None
        elif response in ['n', 'no']:
            observation = input("Please enter your observation/rule to improve the previous step: ").strip()
            if not observation:
                print("Observation cannot be empty if you want to redo. Please try again or choose 'y'/'q'.")
                continue
            return 'n', observation
        elif response in ['q', 'quit']: return 'q', None
        else: print("Invalid input. Please enter Y, n, or q.")

GenerateContentConfigType = Union[types.GenerationConfig, types.GenerateContentConfig, Dict[str, Any], None]

def initialize_genai_client() -> bool:
    """Initializes or reinitializes the global genai_client."""
    global genai_client, api_keys_list, current_api_key_index
    if not api_keys_list:
        api_key_string = os.environ.get('GEMINI_API_KEY')
        if not api_key_string: print("Error: GEMINI_API_KEY environment variable not set.", file=sys.stderr); return False
        api_keys_list = [key.strip() for key in api_key_string.split('|') if key.strip()]
        if not api_keys_list: print("Error: GEMINI_API_KEY format is invalid or contains empty keys.", file=sys.stderr); return False
        current_api_key_index = 0
        print(f"Loaded {len(api_keys_list)} API keys.")
    if not (0 <= current_api_key_index < len(api_keys_list)): print(f"Error: Invalid API key index ({current_api_key_index}).", file=sys.stderr); return False
    active_key = api_keys_list[current_api_key_index]
    print(f"Initializing Google GenAI Client with Key Index {current_api_key_index}...")
    try: genai_client = genai.Client(api_key=active_key); print("Google GenAI Client initialized successfully."); return True
    except Exception as e: print(f"Error initializing Google GenAI Client: {e}", file=sys.stderr); return False

def rotate_api_key_and_reinitialize() -> bool:
    """Rotates to the next API key and reinitializes the client."""
    global current_api_key_index, api_keys_list
    if not api_keys_list or len(api_keys_list) <= 1: print("Error: Cannot rotate API key (list empty or single key).", file=sys.stderr); return False
    start_index = current_api_key_index
    current_api_key_index = (current_api_key_index + 1) % len(api_keys_list)
    print(f"\n---> Rotated API Key to Index {current_api_key_index} <---\n")
    if current_api_key_index == start_index: print("Warning: Cycled through all API keys. Rate limits may persist.", file=sys.stderr)
    if not initialize_genai_client(): print(f"Error: Failed to initialize client with new key index {current_api_key_index}.", file=sys.stderr); return False
    return True

def execute_gemini_call(model: str, contents: List[types.Part], config: Optional[GenerateContentConfigType] = None, sleep_on_retry: int = SLEEP_DURATION_SECONDS) -> str:
    """Executes Gemini API call with rate limit handling and key rotation."""
    global genai_client
    if not genai_client: raise RuntimeError("GenAI client not initialized.")
    initial_key_index = current_api_key_index
    keys_tried_in_this_call = {initial_key_index}

    while True:
        try:
            print(f"\n---> Attempting API call with Key Index {current_api_key_index} <---")
            # Sleep if --with-sleep is active before making the call
            if args.with_sleep:
                 print(f"  --with-sleep active: Waiting {SLEEP_DURATION_SECONDS} seconds...")
                 for _ in tqdm(range(sleep_on_retry), desc="Waiting before API call", unit="s", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}s [{elapsed}<{remaining}]"):
                     time.sleep(1)

            # Ensure config is passed correctly
            gen_config_arg = config if isinstance(config, types.GenerateContentConfig) else None
            safety_settings_arg = config.get("safety_settings") if isinstance(config, dict) else None
            tools_arg = config.get("tools") if isinstance(config, dict) else (config.tools if hasattr(config, 'tools') else None)


            response = genai_client.models.generate_content(
                model=model,
                contents=contents,
            )

            # Process response (same as before)
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                 print(f"  Warning: Prompt blocked due to {response.prompt_feedback.block_reason}.", file=sys.stderr)
            if response.candidates:
                 for candidate in response.candidates:
                     if hasattr(candidate, 'finish_reason') and candidate.finish_reason not in (types.FinishReason.STOP, types.FinishReason.FINISH_REASON_UNSPECIFIED):
                         print(f"  Warning: Candidate finished with reason: {candidate.finish_reason.name}", file=sys.stderr)
                         if hasattr(candidate, 'finish_message') and candidate.finish_message: print(f"  Finish message: {candidate.finish_message}", file=sys.stderr)
            try: return response.text
            except (ValueError, AttributeError): print("Warning: Could not extract text from response. Returning empty.", file=sys.stderr); print(f"Full Response: {response}", file=sys.stderr); return ""

        except (google_api_core_exceptions.ResourceExhausted, errors.ServerError) as e: # Include ServerError for retry
            print(f"  API Error ({type(e).__name__}) detected with Key Index {current_api_key_index}. Waiting and rotating API key...", file=sys.stderr) # Refined log
            for i in tqdm(range(sleep_on_retry), desc="Waiting for quota/retry", unit="s", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}s [{elapsed}<{remaining}]"): time.sleep(1)

            if not rotate_api_key_and_reinitialize(): print("Error: Could not rotate API key. Raising original error.", file=sys.stderr); raise e
            if current_api_key_index in keys_tried_in_this_call: print("Error: Cycled through all API keys. Rate limits likely persistent.", file=sys.stderr); raise e
            keys_tried_in_this_call.add(current_api_key_index)
            print(f"  Retrying API call with Key Index {current_api_key_index}...")
            # Loop continues

        except errors.APIError as e:
            print(f"  Google API Error: {e}", file=sys.stderr)
            status_code = getattr(e, 'code', None) or getattr(e, 'status_code', None)
            if status_code == 429: # Explicitly handle 429 if not caught by ResourceExhausted
                 print(f"  API Error 429 detected with Key Index {current_api_key_index}. Waiting and rotating API key...", file=sys.stderr)
                 for i in tqdm(range(sleep_on_retry), desc="Waiting for quota/retry", unit="s", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}s [{elapsed}<{remaining}]"): time.sleep(1)

                 if not rotate_api_key_and_reinitialize(): print("Error: Could not rotate API key. Raising original error.", file=sys.stderr); raise e
                 if current_api_key_index in keys_tried_in_this_call: print("Error: Cycled through all API keys. Rate limits likely persistent.", file=sys.stderr); raise e
                 keys_tried_in_this_call.add(current_api_key_index)
                 print(f"  Retrying API call with Key Index {current_api_key_index}...")
                 # Loop continues
            else: raise e # Re-raise other Google API errors

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
    for i, task_name in enumerate(sorted_tasks):
        print(f"  {i + 1}: {task_name}")
    print("  q: Quit")

    while True:
        choice = input("Enter the number of the task (or 'q' to quit): ").strip().lower()
        if choice == 'q': return None
        try:
            index = int(choice) - 1
            if 0 <= index < len(sorted_tasks):
                selected_task = sorted_tasks[index]
                print(f"  You selected task: {selected_task}")
                return selected_task
            else: print("  Invalid number. Please try again.")
        except ValueError: print("  Invalid input. Please enter a number or 'q'.")

# --- Argument Parser Setup ---
def parse_arguments(available_tasks: List[str]) -> argparse.Namespace:
    """Sets up and parses command-line arguments."""
    script_name = Path(sys.argv[0]).name
    epilog_lines = ["\nExamples:"]
    sorted_tasks_list = sorted(available_tasks)

    epilog_lines.append("\n  # Direct Flow (Default - Single API call):")
    epilog_lines.append(f"    python {script_name} commit-mesage -i 35")
    epilog_lines.append(f"    python {script_name} resolve-ac -i 35 -a 9 -o 'Use Service Pattern'")
    epilog_lines.append(f"    python {script_name} update-doc -i 35 -d README.md")
    epilog_lines.append(f"    python {script_name} analyze-ac -i 35 -a 9")
    epilog_lines.append(f"    python {script_name} create-pr -i 35 -b main")
    epilog_lines.append(f"    python {script_name} create-test-sub-issue -i 20")
    epilog_lines.append(f"    python {script_name} commit-mesage -i 35 -g -y")
    epilog_lines.append(f"    python {script_name} resolve-ac -i 35 -a 9 -op  # Show final prompt only")
    epilog_lines.append(f"    python {script_name} resolve-ac -i 35 -a 9 -ws  # Wait before API call")
    epilog_lines.append(f"    python {script_name} commit-mesage -i 35 -ec git_log.txt -ec phpstan_analysis.txt # Exclude context files")


    epilog_lines.append("\n  # Two-Stage Flow (Using Meta-Prompts - Requires --two-stage):")
    epilog_lines.append(f"    python {script_name} commit-mesage -i 35 --two-stage")
    epilog_lines.append(f"    python {script_name} resolve-ac -i 35 -a 9 --two-stage -om # Show meta-prompt only")

    epilog_text = "\n".join(epilog_lines)

    parser = argparse.ArgumentParser(
        description="Interact with Google Gemini using project context and prompt templates. Default is Direct Flow (one API call). Use --two-stage for Meta-Prompt flow.",
        epilog=epilog_text,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    all_available_tasks = sorted(list(set(find_available_tasks(TEMPLATE_DIR).keys()) | set(find_available_meta_tasks(META_PROMPT_DIR).keys())))
    task_choices_str = ", ".join(all_available_tasks) if all_available_tasks else "None found"

    parser.add_argument(
        "task", nargs='?', choices=all_available_tasks if all_available_tasks else None,
        help=f"Task to perform. If omitted, you'll be prompted. Available: {task_choices_str}",
        metavar="TASK"
    )
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
    parser.add_argument("-ec", "--exclude-context", action='append', help="Filename(s) to exclude from context (e.g., -ec file1.txt -ec file2.json). Can be used multiple times.", default=[])


    return parser.parse_args()


# --- Main Execution ---
if __name__ == "__main__":
    # --- Load .env variables ---
    dotenv_path = BASE_DIR / '.env'
    if dotenv_path.is_file(): print(f"Loading env vars from: {dotenv_path.relative_to(BASE_DIR)}") ; load_dotenv(dotenv_path=dotenv_path, verbose=True)
    else: print(f"Warning: .env file not found at {dotenv_path}.", file=sys.stderr)

    # --- Find Tasks (Both types) ---
    direct_tasks_dict = find_available_tasks(TEMPLATE_DIR)
    meta_tasks_dict = find_available_meta_tasks(META_PROMPT_DIR)
    all_tasks_dict = {**direct_tasks_dict, **meta_tasks_dict}
    all_task_names = list(all_tasks_dict.keys())

    # --- Parse Arguments ---
    try: args = parse_arguments(all_task_names)
    except SystemExit as e: sys.exit(e.code)

    # --- Select Task Interactively if needed ---
    selected_task = args.task
    if not selected_task:
        if not all_task_names: print("Error: No tasks found. Exiting.", file=sys.stderr); sys.exit(1)
        selected_task = prompt_user_to_select_task(all_tasks_dict)
        if not selected_task: print("No task selected. Exiting."); sys.exit(0)

    # --- Determine Flow and Prompt Path ---
    is_two_stage = args.two_stage
    prompt_path: Optional[Path] = None

    if is_two_stage:
        prompt_path = meta_tasks_dict.get(selected_task)
        if not prompt_path: print(f"Error: Meta-prompt for '{selected_task}' not found in {META_PROMPT_DIR.relative_to(BASE_DIR)}.", file=sys.stderr); sys.exit(1)
        print(f"\nSelected Flow: Two-Stage"); print(f"Using Meta-Prompt: {prompt_path.relative_to(BASE_DIR)}")
    else:
        prompt_path = direct_tasks_dict.get(selected_task)
        if not prompt_path: print(f"Error: Prompt for task '{selected_task}' not found in {TEMPLATE_DIR.relative_to(BASE_DIR)}.", file=sys.stderr); sys.exit(1)
        print(f"\nSelected Flow: Direct"); print(f"Using Prompt: {prompt_path.relative_to(BASE_DIR)}")

    GEMINI_MODEL = GEMINI_MODEL_RESOLVE if selected_task == "resolve-ac" else GEMINI_MODEL_GENERAL_TASKS
    # Print other args... (omitted for brevity, same as before)

    # --- Validate Required Args ---
    if selected_task == 'create-pr' and not args.issue: print("Error: 'create-pr' requires --issue.", file=sys.stderr); sys.exit(1)
    # ... other validations ...

    # --- Run Context Generation ---
    if args.generate_context:
        print(f"\nRunning context generation script: {CONTEXT_GENERATION_SCRIPT.relative_to(BASE_DIR)}...")
        if not CONTEXT_GENERATION_SCRIPT.is_file() or not os.access(CONTEXT_GENERATION_SCRIPT, os.X_OK):
             print(f"Error: Context script not found or not executable.", file=sys.stderr); sys.exit(1)
        exit_code_ctx, _, stderr_ctx = run_command([sys.executable, str(CONTEXT_GENERATION_SCRIPT)], check=False) # Use sys.executable
        if exit_code_ctx != 0: print(f"Error: Context generation failed. Stderr:\n{stderr_ctx}", file=sys.stderr); sys.exit(1)
        print("Context generation script completed.")

    # --- Load Context ---
    latest_context_dir = find_latest_context_dir(CONTEXT_DIR_BASE)
    if latest_context_dir is None: print("Fatal Error: Could not find context directory.", file=sys.stderr); sys.exit(1)
    print(f"Latest Context Directory: {latest_context_dir.relative_to(BASE_DIR)}")
    # Pass the exclude list from args
    context_parts = prepare_context_parts(latest_context_dir, COMMON_CONTEXT_DIR, args.exclude_context)
    if not context_parts: print("Warning: No context files loaded (or all were excluded).", file=sys.stderr)

    # --- Prepare Variables ---
    task_variables: Dict[str, str] = { # Same logic as before...
        "NUMERO_DA_ISSUE": args.issue if args.issue else "",
        "NUMERO_DO_AC": args.ac if args.ac else "",
        "OBSERVACAO_ADICIONAL": args.observation,
        "ARQUIVO_DOC_ALVO": "",
        "PARENT_ISSUE_NUMBER": args.issue if args.issue else "",
        "PARENT_AC_NUMBER": args.ac if args.ac else ""
    }
    # Handle doc file for update-doc (same logic as before)
    if selected_task == "update-doc":
        doc_file_path_str = args.doc_file
        if not doc_file_path_str:
             found_docs = find_documentation_files(BASE_DIR)
             if not found_docs: print("Error: No doc files found.", file=sys.stderr); sys.exit(1)
             selected_doc_path_relative = prompt_user_to_select_doc(found_docs)
             if not selected_doc_path_relative: print("User quit."); sys.exit(0)
             doc_file_path_str = str(selected_doc_path_relative)
        else:
             if not (BASE_DIR / args.doc_file).is_file(): print(f"Error: Provided doc file '{args.doc_file}' not found.", file=sys.stderr); sys.exit(1)
             doc_file_path_str = args.doc_file
        task_variables["ARQUIVO_DOC_ALVO"] = doc_file_path_str
        if not task_variables["ARQUIVO_DOC_ALVO"]: print("Error: Target doc file missing.", file=sys.stderr); sys.exit(1)
        print(f"Target document file set to: {task_variables['ARQUIVO_DOC_ALVO']}")

    print(f"\nFinal Variables for template: {task_variables}")

    # --- Load and Fill Initial Prompt ---
    initial_prompt_content_original = load_and_fill_template(prompt_path, task_variables)
    if not initial_prompt_content_original: print(f"Error loading initial prompt. Exiting.", file=sys.stderr); sys.exit(1)
    initial_prompt_content_current = initial_prompt_content_original
    if args.web_search: initial_prompt_content_current += WEB_SEARCH_ENCOURAGEMENT_PT

    # --- Handle --only-meta ---
    if args.only_meta and is_two_stage:
        print("\n--- Filled Meta-Prompt (--only-meta) ---")
        print(initial_prompt_content_current.strip())
        print("--- End of Meta-Prompt ---")
        print("\nExiting script as requested by --only-meta.")
        sys.exit(0)
    elif args.only_meta:
         print("Warning: --only-meta is only applicable with --two-stage flow.", file=sys.stderr)
         # Continue to --only-prompt check or execution

    # --- Initialize Client (if not already) ---
    if genai_client is None and not args.only_prompt: # Dont init if only prompt is needed
        if not initialize_genai_client(): sys.exit(1)

    # --- Prepare Tools/Config ---
    tools_list = [types.Tool(google_search_retrieval=types.GoogleSearchRetrieval())] if args.web_search else []
    base_config = types.GenerateContentConfig(tools=tools_list) if tools_list else None
    if base_config: print("  GenerateContentConfig created with tools.")

    print("\nStarting interaction with Gemini API...")

    # --- Determine the Final Prompt to be Sent ---
    final_prompt_to_send: Optional[str] = None
    if is_two_stage:
        print("\nExecuting Two-Stage Flow (Step 1: Meta -> Final Prompt)...")
        prompt_final_content: Optional[str] = None
        meta_prompt_current = initial_prompt_content_current
        while True:
            print(f"\nStep 1: Sending Meta-Prompt + Context...")
            contents_step1 = [types.Part.from_text(text=meta_prompt_current)] + context_parts
            try:
                prompt_final_content = execute_gemini_call(GEMINI_MODEL, contents_step1, config=base_config, sleep_on_retry=args.with_sleep)
                print("\n--- Generated Final Prompt (Step 1) ---"); print(prompt_final_content.strip()); print("---")
                if args.yes: print("  Step 1 auto-confirmed (--yes)."); user_choice, observation = 'y', None
                else: user_choice, observation = confirm_step("Use this generated prompt for Step 2?")
                if user_choice == 'y': final_prompt_to_send = prompt_final_content; break
                elif user_choice == 'q': print("Exiting after Step 1."); sys.exit(0)
                elif user_choice == 'n': meta_prompt_current = modify_prompt_with_observation(meta_prompt_current, observation)
                else: print("Internal error. Exiting.", file=sys.stderr); sys.exit(1)
            except Exception as e: # Catch errors during execute_gemini_call
                 print(f"  Error during Step 1 API call: {e}", file=sys.stderr)
                 retry_choice, _ = confirm_step("API call failed in Step 1. Retry?")
                 if retry_choice != 'y': print("Exiting due to API error in Step 1."); sys.exit(1)
                 # Loop continues to retry
        if not final_prompt_to_send: print("Error: Could not obtain final prompt. Aborting.", file=sys.stderr); sys.exit(1)
        if args.web_search: final_prompt_to_send += WEB_SEARCH_ENCOURAGEMENT_PT # Append encouragement
    else:
        # Direct Flow: The initial prompt is the final prompt
        final_prompt_to_send = initial_prompt_content_current

    # --- Handle --only-prompt ---
    if args.only_prompt:
        print(f"\n--- Final Prompt to be Sent (--only-prompt) ---")
        print(final_prompt_to_send.strip())
        print("--- End of Final Prompt ---")
        print("\nExiting script as requested by --only-prompt.")
        sys.exit(0)

    # --- Execute Final API Call (Step 2 or Direct Flow) ---
    final_response_content: Optional[str] = None
    final_prompt_current = final_prompt_to_send # Start with the determined final prompt

    while True:
        print(f"\n{'Step 2: Sending' if is_two_stage else 'Sending'} Final Prompt + Context...")
        contents_final = [types.Part.from_text(text=final_prompt_current)] + context_parts
        try:
            final_response_content = execute_gemini_call(GEMINI_MODEL, contents_final, config=base_config, sleep_on_retry=args.with_sleep)
            print("\n--- Final Response ---"); print(final_response_content.strip()); print("---")
            if args.yes: print("  Response auto-confirmed (--yes)."); user_choice, observation = 'y', None
            else: user_choice, observation = confirm_step("Proceed with this final response?")

            if user_choice == 'y': break
            elif user_choice == 'q': print("Exiting."); sys.exit(0)
            elif user_choice == 'n': final_prompt_current = modify_prompt_with_observation(final_prompt_current, observation)
            else: print("Internal error. Exiting.", file=sys.stderr); sys.exit(1)
        except Exception as e: # Catch errors during execute_gemini_call
             print(f"  Error during final API call: {e}", file=sys.stderr)
             retry_choice, _ = confirm_step("Final API call failed. Retry?")
             if retry_choice != 'y': print("Exiting due to API error in final step."); sys.exit(1)
             # Loop continues to retry

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
    else:
        save_confirm_choice, _ = confirm_step("Confirm saving this response?")
        if save_confirm_choice == 'y':
             print("\nSaving Final Response...")
             save_llm_response(selected_task, final_response_content.strip())
        else: print("Save cancelled."); sys.exit(0)

    sys.exit(0) # Ensure explicit exit success