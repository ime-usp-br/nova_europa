import argparse
import os
import sys
import subprocess # Added for AC14 and AC25/AC29
from pathlib import Path
import re
import google.genai as genai
from google.genai import types
# Import specific exceptions (AC32)
from google.genai import errors
from google.api_core import exceptions as google_api_core_exceptions
from dotenv import load_dotenv
import traceback # For debugging unexpected errors
from datetime import datetime # For timestamping output files (AC8)
from typing import List, Dict, Tuple, Optional, Union, Any, Callable # Added for type hinting
import time # Added for AC36
from tqdm import tqdm # Added for AC32 and AC36

# --- Configuration ---
# Assumes the script is in /scripts and templates in /project_templates/meta-prompts
BASE_DIR = Path(__file__).resolve().parent.parent
META_PROMPT_DIR = BASE_DIR / "templates/meta-prompts"
CONTEXT_DIR_BASE = BASE_DIR / "context_llm/code"
COMMON_CONTEXT_DIR = BASE_DIR / "context_llm/common" # Directory for common context files (AC7)
OUTPUT_DIR_BASE = BASE_DIR / "llm_outputs" # Directory for saving outputs, should be in .gitignore (AC8)
CONTEXT_GENERATION_SCRIPT = BASE_DIR / "gerar_contexto_llm.sh" # Path to context script (AC14)
TIMESTAMP_DIR_REGEX = r'^\d{8}_\d{6}$' # Regex to validate directory name format
# Gemini model to use (choose an appropriate model for tasks)
GEMINI_MODEL_GENERAL_TASKS = 'gemini-2.5-pro-exp-03-25' # Do not change. Do not insert in commit mesage.
GEMINI_MODEL_RESOLVE = 'gemini-2.5-pro-exp-03-25' # Do not change. Do not insert in commit mesage.
# Message to encourage web search (AC13 Observação Adicional)
WEB_SEARCH_ENCOURAGEMENT_PT = "\n\nPara garantir a melhor resposta possível, sinta-se à vontade para pesquisar na internet usando a ferramenta de busca disponível."
DEFAULT_BASE_BRANCH = 'main' # Default target branch for PRs (AC25)
PR_CONTENT_DELIMITER_TITLE = "--- PR TITLE ---" # AC25
PR_CONTENT_DELIMITER_BODY = "--- PR BODY ---" # AC25

# --- Global Variables for API Key Rotation (AC32) ---
api_keys_list: List[str] = []
current_api_key_index: int = 0
genai_client: Optional[genai.Client] = None


# --- Helper Functions ---

def find_available_tasks(prompt_dir: Path) -> Dict[str, Path]:
    """
    Find available tasks (meta-prompts) in the specified directory.

    Args:
        prompt_dir: The Path to the directory containing meta-prompt files.

    Returns:
        A dictionary mapping task names to the Paths of the files.
        Returns an empty dictionary if the directory doesn't exist or contains no prompts.
    """
    tasks = {}
    if not prompt_dir.is_dir():
        print(f"Error: Meta-prompt directory not found: {prompt_dir}", file=sys.stderr)
        return tasks
    # Expected pattern: meta-prompt-task_name.txt
    for filepath in prompt_dir.glob("meta-prompt-*.txt"):
        if filepath.is_file():
            # Allow underscores and hyphens in task names
            task_name = filepath.stem.replace("meta-prompt-", "").replace("_", "-")
            if task_name:
                tasks[task_name] = filepath
    return tasks

def find_latest_context_dir(context_base_dir: Path) -> Optional[Path]:
    """
    Find the most recent context directory within the base directory.

    Args:
        context_base_dir: The Path to the base directory where context
                          directories (timestamped) are located.

    Returns:
        A Path object for the latest directory found, or None if
        no valid directory is found or the base directory doesn't exist.
    """
    if not context_base_dir.is_dir():
        print(f"Error: Context base directory not found: {context_base_dir}", file=sys.stderr)
        return None

    valid_context_dirs = []
    for item in context_base_dir.iterdir():
        # Ensure it's a directory and matches the timestamp format, excluding the common dir
        if item.is_dir() and re.match(TIMESTAMP_DIR_REGEX, item.name):
            valid_context_dirs.append(item)

    if not valid_context_dirs:
        print(f"Error: No valid timestamped context directories (YYYYMMDD_HHMMSS format) found in {context_base_dir}", file=sys.stderr)
        return None

    # Sort directories by name (timestamp) in descending order
    latest_context_dir = sorted(valid_context_dirs, reverse=True)[0]
    return latest_context_dir

def load_and_fill_template(template_path: Path, variables: Dict[str, str]) -> str:
    """
    Load a meta-prompt template and replace placeholders with provided variables.

    Args:
        template_path: The Path to the template file.
        variables: A dictionary where keys are variable names (without __)
                   and values are the data for substitution.

    Returns:
        The template content with variables substituted.
        Returns an empty string if the template cannot be read or an error occurs.
    """
    try:
        content = template_path.read_text(encoding='utf-8')
        # Helper function to handle substitution
        def replace_match(match: re.Match[str]) -> str:
            var_name = match.group(1)
            # Returns the variable value from the dictionary or an empty string if not found
            # Ensures the value is a string for substitution
            return str(variables.get(var_name, ''))

        # Regex to find placeholders like __VARIABLE_EXAMPLE__
        filled_content = re.sub(r'__([A-Z_]+)__', replace_match, content)
        return filled_content
    except FileNotFoundError:
        print(f"Error: Template file not found: {template_path}", file=sys.stderr)
        return ""
    except Exception as e:
        print(f"Error reading or processing template {template_path}: {e}", file=sys.stderr)
        return ""


def _load_files_from_dir(context_dir: Path, context_parts: List[types.Part]) -> None:
    """Helper function to load .txt, .json and .md files from a directory into context_parts."""
    file_patterns = ["*.txt", "*.json", "*.md"]
    loaded_count = 0
    if not context_dir or not context_dir.is_dir():
        print(f"    - Directory not found or invalid: {context_dir}", file=sys.stderr)
        return

    print(f"    Scanning directory: {context_dir.relative_to(BASE_DIR)}")
    for pattern in file_patterns:
        for filepath in context_dir.glob(pattern):
            if filepath.is_file():
                try:
                    # print(f"      - Reading {filepath.name}") # Verbose logging removed
                    content = filepath.read_text(encoding='utf-8')
                    # Add file name at the beginning of content for LLM origin tracking
                    # Use keyword argument 'text='
                    relative_path = filepath.relative_to(BASE_DIR)
                    context_parts.append(types.Part.from_text(text=f"--- START OF FILE {relative_path} ---\n{content}\n--- END OF FILE {relative_path} ---"))
                    loaded_count += 1
                except Exception as e:
                    print(f"      - Warning: Could not read file {filepath.name}: {e}", file=sys.stderr)
    if loaded_count == 0:
        print(f"      - No context files (.txt, .json, .md) found in this directory.")

def prepare_context_parts(primary_context_dir: Path, common_context_dir: Optional[Path] = None) -> List[types.Part]:
    """
    List context files (.txt, .json, .md) from primary and optionally common directories,
    and prepare them as types.Part.

    Args:
        primary_context_dir: The Path to the primary (e.g., timestamped) context directory.
        common_context_dir: Optional Path to the common context directory.

    Returns:
        A list of types.Part objects representing the content of the files.
    """
    context_parts: List[types.Part] = []
    print("  Loading context files...")

    # Load from primary directory
    print("  Loading from primary context directory...")
    _load_files_from_dir(primary_context_dir, context_parts)

    # Load from common directory (AC7)
    if common_context_dir:
        print("\n  Loading from common context directory...")
        if common_context_dir.exists() and common_context_dir.is_dir():
             _load_files_from_dir(common_context_dir, context_parts)
        else:
             print(f"    - Common context directory not found or is not a directory: {common_context_dir}")

    print(f"\n  Total context files loaded: {len(context_parts)}.")
    return context_parts

def save_llm_response(task_name: str, response_content: str) -> None:
    """
    Saves the LLM's final response to a timestamped file within a task-specific directory.

    Args:
        task_name: The name of the task (e.g., 'resolve-ac', 'commit-mesage').
        response_content: The string content of the LLM's final response.
    """
    try:
        task_output_dir = OUTPUT_DIR_BASE / task_name
        task_output_dir.mkdir(parents=True, exist_ok=True) # Create dirs if they don't exist

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{timestamp_str}.txt" # Or use a more specific extension if needed, e.g., .diff, .md
        output_filepath = task_output_dir / output_filename

        output_filepath.write_text(response_content, encoding='utf-8')
        print(f"  LLM Response saved to: {output_filepath.relative_to(BASE_DIR)}")

    except OSError as e:
        print(f"Error creating output directory {task_output_dir}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"Error saving LLM response to file: {e}", file=sys.stderr)
        traceback.print_exc()

def parse_pr_content(llm_output: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parses the LLM output for the create-pr task to extract title and body.

    Args:
        llm_output: The raw string output from the LLM for the create-pr task.

    Returns:
        A tuple (title, body). Returns (None, None) if parsing fails.
    """
    # Match Title: Starts with delimiter, captures everything until the next delimiter, allowing newlines
    title_match = re.search(rf"^{re.escape(PR_CONTENT_DELIMITER_TITLE)}\s*(.*?)\s*{re.escape(PR_CONTENT_DELIMITER_BODY)}", llm_output, re.DOTALL | re.MULTILINE)
    # Match Body: Starts after delimiter, captures everything until the end of the string
    body_match = re.search(rf"{re.escape(PR_CONTENT_DELIMITER_BODY)}\s*(.*)", llm_output, re.DOTALL | re.MULTILINE)

    if title_match and body_match:
        title = title_match.group(1).strip()
        body = body_match.group(1).strip()
        # Ensure title is not empty, body can be empty if the LLM intended so
        if title and body is not None:
             return title, body
        else:
             print("Error: Parsed title is empty or body is unexpectedly None.", file=sys.stderr)
             return None, None
    else:
        print(f"Error: Could not parse LLM output. Delimiters '{PR_CONTENT_DELIMITER_TITLE}' or '{PR_CONTENT_DELIMITER_BODY}' not found or incorrect format.", file=sys.stderr)
        print(f"LLM Output received:\n---\n{llm_output}\n---", file=sys.stderr)
        return None, None

def get_current_branch() -> Optional[str]:
    """Gets the current Git branch name using subprocess."""
    try:
        # Execute 'git rev-parse --abbrev-ref HEAD' in the project's base directory
        result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True,  # Capture stdout and stderr
            text=True,            # Decode output as text
            check=True,           # Raise CalledProcessError on failure
            cwd=BASE_DIR          # Ensure command runs in the project root
        )
        # Return the cleaned branch name
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        # Handle errors during Git command execution
        print(f"Error getting current Git branch: {e}", file=sys.stderr)
        print(f"Command: {' '.join(e.cmd)}", file=sys.stderr)
        print(f"Return Code: {e.returncode}", file=sys.stderr)
        print(f"Stderr: {e.stderr}", file=sys.stderr)
        print(f"Stdout: {e.stdout}", file=sys.stderr)
        return None
    except FileNotFoundError:
        # Handle case where 'git' command is not found
        print("Error: 'git' command not found. Is Git installed and in PATH?", file=sys.stderr)
        return None
    except Exception as e:
        # Catch any other unexpected errors
        print(f"An unexpected error occurred while getting the Git branch: {e}", file=sys.stderr)
        traceback.print_exc()
        return None


def check_new_commits(base_branch: str, head_branch: str) -> bool:
    """Checks if there are new commits on the head branch compared to the base branch."""
    try:
        # Fetch latest changes from origin for both branches to ensure comparison is up-to-date
        print(f"  Fetching latest changes for branches '{head_branch}' and '{base_branch}' from origin...")
        subprocess.run(['git', 'fetch', 'origin', head_branch, base_branch], check=False, cwd=BASE_DIR, capture_output=True) # Allow fetch to fail gracefully if branch doesn't exist remotely yet

        # Use 'origin/base_branch' for comparison if it exists, otherwise use local base_branch
        base_ref_to_compare = base_branch
        check_remote_base = subprocess.run(['git', 'show-ref', '--verify', f'refs/remotes/origin/{base_branch}'], capture_output=True, text=True, check=False, cwd=BASE_DIR)
        if check_remote_base.returncode == 0:
             base_ref_to_compare = f'origin/{base_branch}'
             print(f"  Comparing against remote base branch: {base_ref_to_compare}")
        else:
            print(f"  Warning: Remote base branch 'origin/{base_branch}' not found. Comparing against local '{base_branch}'. Ensure it's up-to-date.")


        # Count commits on head_branch that are not on base_ref_to_compare
        count_cmd = ['git', 'rev-list', '--count', f'{base_ref_to_compare}..{head_branch}']
        print(f"  Executing: {' '.join(count_cmd)}")
        result = subprocess.run(count_cmd, capture_output=True, text=True, check=True, cwd=BASE_DIR)
        commit_count = int(result.stdout.strip())
        print(f"  Found {commit_count} new commit(s) on '{head_branch}' compared to '{base_ref_to_compare}'.")
        return commit_count > 0
    except subprocess.CalledProcessError as e:
        print(f"Error checking for new commits: {e}", file=sys.stderr)
        print(f"Command: {' '.join(e.cmd)}", file=sys.stderr)
        print(f"Stderr: {e.stderr}", file=sys.stderr)
        print(f"Stdout: {e.stdout}", file=sys.stderr)
        # Attempt comparison against local base branch as a fallback if origin fetch/compare failed
        try:
            print(f"  Retrying comparison against local base branch '{base_branch}'...")
            count_cmd = ['git', 'rev-list', '--count', f'{base_branch}..{head_branch}']
            result = subprocess.run(count_cmd, capture_output=True, text=True, check=True, cwd=BASE_DIR)
            commit_count = int(result.stdout.strip())
            print(f"  Found {commit_count} new commit(s) on '{head_branch}' compared to local '{base_branch}'.")
            return commit_count > 0
        except Exception as fallback_e:
             print(f"  Fallback check against local base branch also failed: {fallback_e}", file=sys.stderr)
             return False # Assume no new commits if checks fail
    except FileNotFoundError:
        print("Error: 'git' command not found. Is Git installed and in PATH?", file=sys.stderr)
        return False
    except ValueError:
        print("Error: Could not parse commit count.", file=sys.stderr)
        return False

def create_github_pr(title: str, body: str, head_branch: str, base_branch: str, is_draft: bool) -> bool:
    """Creates a GitHub Pull Request using the gh CLI."""
    try:
        cmd = [
            'gh', 'pr', 'create',
            '--title', title,
            '--body', body,
            '--head', head_branch,
            '--base', base_branch
        ]
        if is_draft:
            cmd.append('--draft')

        print("\nAttempting to create Pull Request...")
        print(f"  Command: {' '.join(cmd)}") # Echo the command

        # Ask for user confirmation before creating PR - THIS IS NOT SKIPPED by --yes (AC30)
        pr_confirm_choice, _ = confirm_step("Confirm creating PR with this Title/Body?")
        if pr_confirm_choice != 'y':
            print("Pull Request creation cancelled by user.")
            return False

        result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=BASE_DIR)
        print("Pull Request created successfully!")
        print(f"  URL: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating Pull Request: {e}", file=sys.stderr)
        print(f"Stderr: {e.stderr}", file=sys.stderr)
        print(f"Stdout: {e.stdout}", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("Error: 'gh' command not found. Is GitHub CLI installed and in PATH?", file=sys.stderr)
        return False

def parse_arguments(available_tasks: List[str]) -> argparse.Namespace:
    """
    Parse command-line arguments, including examples in the epilog.

    Args:
        available_tasks: A list of available task names.

    Returns:
        A Namespace object containing the parsed arguments.
    """
    script_name = Path(sys.argv[0]).name # Get script name for examples

    # --- Build epilog string with examples ---
    epilog_lines = ["\nExamples:"]
    sorted_tasks = sorted(available_tasks)

    for task_name in sorted_tasks:
        # --- ATUALIZAÇÃO: Adiciona exemplo para create-test-sub-issue ---
        if task_name == "create-test-sub-issue":
             example = f"  {script_name} {task_name} -i <parent_issue> [-a <parent_ac>] [-y] [-g] [-om] [-ws]"
             epilog_lines.append(example)
        # --- FIM DA ATUALIZAÇÃO ---
        elif task_name == "commit-mesage":
            example = f"  {script_name} {task_name} -i 28 [-y] [-g] [-om] [-ws]"
            epilog_lines.append(example)
        # (...) outros exemplos existentes...

    epilog_text = "\n".join(epilog_lines)

    # --- Create parser ---
    parser = argparse.ArgumentParser(
        description="Interact with Google Gemini using project context and meta-prompts.",
        epilog=epilog_text,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    task_choices_str = ", ".join(sorted_tasks)
    parser.add_argument(
        "task",
        choices=sorted_tasks,
        help=(f"The task to perform, based on available meta-prompts in "
              f"'{META_PROMPT_DIR.relative_to(BASE_DIR)}'.\nAvailable tasks: {task_choices_str}"),
        metavar="TASK"
    )

    # --- ATUALIZAÇÃO: Modifica help de --issue/-i ---
    parser.add_argument(
        "-i", "--issue",
        help="Issue number (e.g., 28). Fills __NUMERO_DA_ISSUE__ and __PARENT_ISSUE_NUMBER__. "
             "**Required for 'create-pr'**. For 'create-test-sub-issue', specifies the **parent issue** to be tested."
    )
    # --- FIM DA ATUALIZAÇÃO ---

    # --- ATUALIZAÇÃO: Modifica help de --ac/-a ---
    parser.add_argument(
        "-a", "--ac",
        help="Acceptance Criteria number (e.g., 5). Fills __NUMERO_DO_AC__ and __PARENT_AC_NUMBER__. "
             "For 'create-test-sub-issue', specifies the originating **parent AC** (optional)."
    )
    # --- FIM DA ATUALIZAÇÃO ---

    parser.add_argument("-o", "--observation", help="Additional observation/instruction for the task. Fills __OBSERVACAO_ADICIONAL__.", default="")
    parser.add_argument("-d", "--doc-file", help="Target documentation file path for 'update-doc' task. If omitted, you will be prompted to choose. Fills __ARQUIVO_DOC_ALVO__.")
    parser.add_argument("-b", "--target-branch", help=f"Target base branch for the Pull Request (default: {DEFAULT_BASE_BRANCH}). Used by 'create-pr'.", default=DEFAULT_BASE_BRANCH)
    parser.add_argument("--draft", action="store_true", help="Create the Pull Request as a draft. Used by 'create-pr'.")
    parser.add_argument("-w", "--web-search", action="store_true", help="Enable Google Search as a tool for the Gemini model (AC13).")
    parser.add_argument("-g", "--generate-context", action="store_true", help="Run the context generation script (gerar_contexto_llm.sh) before interacting with Gemini (AC14).")
    parser.add_argument("-y", "--yes", action="store_true", help="Automatically confirm Step 1 (prompt generation) and Step 2 (response generation), but still ask for final action confirmation.")
    parser.add_argument("-om", "--only-meta", action="store_true", help="Only generate and print the filled meta-prompt, then exit. Does not interact with the LLM.")
    parser.add_argument("-ws", "--with-sleep", action="store_true", help="Wait for 5 minutes before the first Gemini API call (AC36).")

    return parser.parse_args()

def find_documentation_files(base_dir: Path) -> List[Path]:
    """
    Find potential documentation files (.md) in the project.

    Args:
        base_dir: The root directory of the project.

    Returns:
        A sorted list of relative Path objects for documentation files.
    """
    print("  Scanning for documentation files...")
    found_paths: set[Path] = set() # Use a set to avoid duplicates

    # Check specific root files
    for filename in ["README.md", "CHANGELOG.md"]: # Add more root files if needed
        filepath = base_dir / filename
        if filepath.is_file():
            found_paths.add(filepath.relative_to(base_dir))

    # Check docs directory recursively
    docs_dir = base_dir / "docs"
    if docs_dir.is_dir():
        for filepath in docs_dir.rglob("*.md"):
            # Add more specific filtering here if needed (e.g., ignore subdirs)
            if filepath.is_file():
                 found_paths.add(filepath.relative_to(base_dir))

    print(f"  Found {len(found_paths)} unique documentation files.")
    # Return a sorted list of Path objects based on their string representation
    return sorted(list(found_paths), key=lambda p: str(p))


def prompt_user_to_select_doc(doc_files: List[Path]) -> Optional[Path]:
    """
    Displays a numbered list of doc files and prompts the user for selection.

    Args:
        doc_files: A list of relative Path objects for the documentation files.

    Returns:
        The selected relative Path object, or None if the user quits.
    """
    print("\nMultiple documentation files found. Please choose one to update:")
    for i, filepath in enumerate(doc_files):
        print(f"  {i + 1}: {filepath}")
    print("  q: Quit")

    while True:
        choice = input("Enter the number of the file to update (or 'q' to quit): ").strip().lower()
        if choice == 'q':
            return None
        try:
            index = int(choice) - 1
            if 0 <= index < len(doc_files):
                selected_path = doc_files[index]
                print(f"  You selected: {selected_path}")
                return selected_path # Return the relative path object
            else:
                print("  Invalid number. Please try again.")
        except ValueError:
            print("  Invalid input. Please enter a number or 'q'.")


def confirm_step(prompt: str) -> Tuple[str, Optional[str]]:
    """
    Asks the user for confirmation to proceed, redo, or quit.
    If redo ('n') is chosen, prompts for an observation.

    Args:
        prompt: The message to display to the user.

    Returns:
        A tuple: (user's choice ('y', 'n', 'q'), observation string or None).
        Converts choice to lowercase.
    """
    while True:
        response = input(f"{prompt} (Y/n/q - Yes/No+Feedback/Quit) [Y]: ").lower().strip()
        if response in ['y', 'yes', '']:
            return 'y', None
        elif response in ['n', 'no']:
            # AC10: Ask for observation when user wants to redo
            observation = input("Please enter your observation/rule to improve the previous step: ").strip()
            if not observation:
                print("Observation cannot be empty if you want to redo. Please try again or choose 'y'/'q'.")
                continue # Ask again
            return 'n', observation
        elif response in ['q', 'quit']:
            return 'q', None
        else:
            print("Invalid input. Please enter Y, n, or q.")

# Type alias for better readability
GenerateContentConfigType = Union[types.GenerationConfig, types.GenerateContentConfig, Dict[str, Any], None]

# --- AC32: Function to initialize/reinitialize the GenAI client ---
def initialize_genai_client() -> bool:
    """Initializes or reinitializes the global genai_client with the current API key."""
    global genai_client, api_keys_list, current_api_key_index
    if not api_keys_list:
        # Load and split keys only once if not already done
        api_key_string = os.environ.get('GEMINI_API_KEY')
        if not api_key_string:
             print("Error: GEMINI_API_KEY environment variable not set.", file=sys.stderr)
             return False # Indicate failure
        api_keys_list = api_key_string.split('|')
        if not api_keys_list or not all(api_keys_list): # Check if list is empty or contains empty strings
            print(f"Error: GEMINI_API_KEY format is invalid or contains empty keys ('{api_key_string}'). Should be key1|key2|...", file=sys.stderr)
            return False # Indicate failure
        current_api_key_index = 0 # Start with the first key
        print(f"Loaded {len(api_keys_list)} API keys.")

    if not (0 <= current_api_key_index < len(api_keys_list)):
        print(f"Error: Invalid current_api_key_index ({current_api_key_index}). Resetting to 0.", file=sys.stderr)
        current_api_key_index = 0

    # Use the key at the current index
    active_key = api_keys_list[current_api_key_index].strip() # Ensure no extra spaces
    if not active_key:
         print(f"Error: API key at index {current_api_key_index} is empty.", file=sys.stderr)
         return False

    print(f"Initializing Google GenAI Client with Key Index {current_api_key_index}...")
    try:
        # Re-instantiate the client to use the new key
        genai_client = genai.Client(api_key=active_key)
        print("Google GenAI Client initialized successfully.")
        return True # Indicate success
    except Exception as e:
        print(f"Error initializing Google GenAI Client with key index {current_api_key_index}: {e}", file=sys.stderr)
        return False # Indicate failure

# --- AC32: Function to rotate API key and reinitialize client ---
def rotate_api_key_and_reinitialize() -> bool:
    """Rotates to the next API key and reinitializes the client."""
    global current_api_key_index, api_keys_list
    if not api_keys_list or len(api_keys_list) <= 1: # Cannot rotate if only one key
        print("Error: API key list empty or only contains one key. Cannot rotate.", file=sys.stderr)
        return False # Indicate failure to rotate

    start_index = current_api_key_index
    current_api_key_index = (current_api_key_index + 1) % len(api_keys_list)
    print(f"\n---> Rotated API Key to Index {current_api_key_index} <---\n")

    if current_api_key_index == start_index:
         # We've looped through all keys without success on the *next* attempt
         print("Warning: Cycled through all API keys due to rate limits. Further attempts might fail.", file=sys.stderr)
         # Consider adding a delay or different logic if all keys are exhausted rapidly

    # Re-initialize the client with the new key
    if not initialize_genai_client():
        # If initialization fails with the new key, we might be in a bad state.
        # For now, report the error and signal failure.
        print(f"Error: Failed to initialize client with new key index {current_api_key_index}.", file=sys.stderr)
        return False

    return True # Indicate successful rotation and re-initialization

def execute_gemini_call(model: str, contents: List[types.Part], config: Optional[GenerateContentConfigType] = None) -> str:
    """
    Executes a call to the Gemini API, handles rate limit errors with key rotation, and returns the text response.
    """
    global genai_client # Need access to the global client instance

    if not genai_client:
         print("Error: GenAI client is not initialized.", file=sys.stderr)
         raise RuntimeError("GenAI client must be initialized before calling the API.")

    initial_key_index = current_api_key_index
    keys_tried_in_this_call = {initial_key_index} # Track keys tried in this specific call attempt

    while True: # Loop for retrying with rotated keys
        try:
            print(f"\n---> Attempting API call with Key Index {current_api_key_index} <---") # Refined log (Commit #28)
            # Optional sleep can be added here if needed before *every* call
            # time.sleep(1)

            response = genai_client.models.generate_content(
                model=model,
                contents=contents,
                config=config # Corrected based on SDK docs
            )
            # Handle potential API errors more gracefully if needed
            # Check response.prompt_feedback for safety issues, etc.
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                 print(f"  Warning: Prompt blocked due to {response.prompt_feedback.block_reason}.", file=sys.stderr)
                 # Depending on the reason, might want to raise an error or return specific message
            # Check candidates for finish_reason
            if response.candidates:
                 for candidate in response.candidates:
                     # Check if finish_reason exists and is not STOP or UNSPECIFIED
                     if hasattr(candidate, 'finish_reason') and candidate.finish_reason not in (types.FinishReason.STOP, types.FinishReason.FINISH_REASON_UNSPECIFIED):
                         print(f"  Warning: Candidate finished with reason: {candidate.finish_reason.name}", file=sys.stderr)
                         if hasattr(candidate, 'finish_message') and candidate.finish_message: # Check if finish_message exists
                             print(f"  Finish message: {candidate.finish_message}", file=sys.stderr)

            # Attempt to get text, handle potential AttributeError if parts are missing
            try:
                return response.text
            except ValueError:
                 print("  Warning: Could not extract text from response. Returning empty string.", file=sys.stderr)
                 print(f"  Full Response: {response}", file=sys.stderr)
                 return ""
            except AttributeError:
                 print("  Warning: Response object does not have 'text' attribute (likely due to blocking or error). Returning empty string.", file=sys.stderr)
                 print(f"  Full Response: {response}", file=sys.stderr)
                 return ""

        except google_api_core_exceptions.ResourceExhausted as e: # Specific exception for rate limits (AC32)
            print(f"\n---> Rate limit exceeded (ResourceExhausted) for Key Index {current_api_key_index}. Waiting and rotating API key... <---", file=sys.stderr) # Refined log
            for i in tqdm(range(300), desc="Waiting for quota", unit="s", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}s [{elapsed}<{remaining}]"): # Add progress bar
                time.sleep(1)
            if not rotate_api_key_and_reinitialize():
                print("  Error: Could not rotate API key. Raising original error.", file=sys.stderr)
                raise e # Re-raise original error if rotation failed
            # Check if we've tried all keys in this call attempt
            if current_api_key_index in keys_tried_in_this_call:
                 print("  Error: Cycled through all API keys for this request. Rate limits likely persistent across all keys.", file=sys.stderr)
                 raise e # Raise error after trying all keys
            keys_tried_in_this_call.add(current_api_key_index)
            print(f"  Retrying API call with Key Index {current_api_key_index}...")
            # Loop continues to retry with the new client

        except errors.APIError as e: # Catch other potential Google API errors
             print(f"  Google API Error: {e}", file=sys.stderr)
             # Check if it's a 429 error specifically if ResourceExhausted didn't catch it
             status_code = getattr(e, 'code', None) or getattr(e, 'status_code', None) # Try common attributes
             if status_code == 429:
                  print(f"\n---> API Error indicates rate limit (status 429) for Key Index {current_api_key_index}. Waiting and rotating API key... <---", file=sys.stderr) # Refined log
                  for i in tqdm(range(300), desc="Waiting for quota", unit="s", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}s [{elapsed}<{remaining}]"): # Add progress bar
                      time.sleep(1)
                  if not rotate_api_key_and_reinitialize():
                       print("  Error: Could not rotate API key. Raising original error.", file=sys.stderr)
                       raise e
                  # Check if we've tried all keys in this call attempt
                  if current_api_key_index in keys_tried_in_this_call:
                       print("  Error: Cycled through all API keys for this request. Rate limits likely persistent across all keys.", file=sys.stderr)
                       raise e # Raise error after trying all keys
                  keys_tried_in_this_call.add(current_api_key_index)
                  print(f"  Retrying API call with Key Index {current_api_key_index}...")
                  # Loop continues to retry with the new client
             else:
                  # Re-raise other Google API errors
                  raise e
        except Exception as e:
            print(f"  Unexpected Error during Gemini API call: {e}", file=sys.stderr)
            traceback.print_exc()
            raise # Re-raise other errors


def modify_prompt_with_observation(original_prompt: str, observation: str) -> str:
    """Appends the user observation to the original prompt for retrying."""
    modified_prompt = f"{original_prompt}\n\n--- USER FEEDBACK FOR RETRY ---\n{observation}\n--- END FEEDBACK ---"
    print("\n  >>> Prompt modified with observation for retry <<<")
    # print(modified_prompt) # Optionally print the modified prompt
    return modified_prompt

# --- Main Execution ---
if __name__ == "__main__":
    # --- Load .env variables ---
    dotenv_path = BASE_DIR / '.env'
    if dotenv_path.is_file():
        print(f"Loading environment variables from: {dotenv_path.relative_to(BASE_DIR)}")
        load_dotenv(dotenv_path=dotenv_path, verbose=True)
    else:
        print(f"Warning: .env file not found at {dotenv_path}. Relying on system environment variables.", file=sys.stderr)
    # --- End Load .env ---

    available_tasks_dict = find_available_tasks(META_PROMPT_DIR)
    available_task_names = list(available_tasks_dict.keys())

    if not available_task_names:
        print(f"Error: No meta-prompt files found in '{META_PROMPT_DIR}'. Exiting.", file=sys.stderr)
        sys.exit(1)

    try:
        args = parse_arguments(available_task_names)
        selected_task = args.task
        selected_meta_prompt_path = available_tasks_dict[selected_task]
        GEMINI_MODEL = GEMINI_MODEL_RESOLVE if selected_task == "resolve-ac" else GEMINI_MODEL_GENERAL_TASKS

        print(f"\nLLM Interaction Script")
        print(f"========================")
        print(f"Selected Task: {selected_task}")
        print(f"Using Meta-Prompt: {selected_meta_prompt_path.relative_to(BASE_DIR)}")
        print(f"Using Model: {GEMINI_MODEL}")
        print(f"Web Search Enabled: {args.web_search}") # Log the flag status (AC13)
        print(f"Generate Context Flag: {args.generate_context}") # Log the flag status (AC14)
        print(f"Auto-Confirm Steps 1&2: {args.yes}") # Log AC30 flag status
        print(f"Only Generate Meta-Prompt: {args.only_meta}") # AC35 Log flag status
        print(f"Wait Before API Call: {args.with_sleep}") # AC36 Log flag status
        if selected_task == 'create-pr': # AC25 Log relevant flags
            print(f"Target Branch: {args.target_branch}")
            print(f"Draft PR: {args.draft}")


        # --- AC25: Validate required --issue for create-pr ---
        if selected_task == 'create-pr' and not args.issue:
            print("Error: The 'create-pr' task requires the --issue (or -i) argument.", file=sys.stderr)
            sys.exit(1)
        # --- End AC25 ---


        # --- AC14: Run Context Generation Script ---
        if args.generate_context:
            print(f"\nRunning context generation script: {CONTEXT_GENERATION_SCRIPT.relative_to(BASE_DIR)}...")
            if not CONTEXT_GENERATION_SCRIPT.is_file():
                print(f"Error: Context generation script not found at {CONTEXT_GENERATION_SCRIPT}", file=sys.stderr)
                sys.exit(1)
            if not os.access(CONTEXT_GENERATION_SCRIPT, os.X_OK):
                 print(f"Error: Context generation script ({CONTEXT_GENERATION_SCRIPT}) is not executable. Please run 'chmod +x {CONTEXT_GENERATION_SCRIPT}'.", file=sys.stderr)
                 sys.exit(1)

            try:
                # Use subprocess.run for better control and error capturing
                result = subprocess.run([str(CONTEXT_GENERATION_SCRIPT)], capture_output=True, text=True, check=False, cwd=BASE_DIR)
                if result.returncode == 0:
                    print("Context generation script completed successfully.")
                    # print("Output:\n", result.stdout) # Optionally print stdout
                else:
                    print(f"Error: Context generation script failed with exit code {result.returncode}.", file=sys.stderr)
                    print(f"Stderr:\n{result.stderr}", file=sys.stderr)
                    print(f"Stdout:\n{result.stdout}", file=sys.stderr) # Show stdout even on failure
                    sys.exit(1) # Exit if context generation fails as requested by user
            except Exception as e:
                print(f"Error running context generation script: {e}", file=sys.stderr)
                traceback.print_exc()
                sys.exit(1)
        # --- End AC14 ---

        # --- Configure GenAI Client with API Key (AC32: Initial load) ---
        # Moved initialization to happen *after* context generation if flag is used,
        # but *before* finding context dir if not.
        # Initialize client early if not generating context, otherwise happens later
        if not args.generate_context and not args.only_meta: # Dont init if only meta is needed
             if not initialize_genai_client():
                 sys.exit(1)


        latest_context_dir = find_latest_context_dir(CONTEXT_DIR_BASE)
        if latest_context_dir is None:
            print("Fatal Error: Could not find a valid context directory. Exiting.", file=sys.stderr)
            sys.exit(1)
        print(f"Latest Context Directory: {latest_context_dir.relative_to(BASE_DIR)}")

        # --- Populate task_variables ---
        task_variables: Dict[str, str] = {
            "NUMERO_DA_ISSUE": args.issue if args.issue else "",
            "NUMERO_DO_AC": args.ac if args.ac else "",
            "OBSERVACAO_ADICIONAL": args.observation,
            "ARQUIVO_DOC_ALVO": "", # Default to empty
            "PARENT_ISSUE_NUMBER": args.issue if args.issue else "", # Map to --issue/-i
            "PARENT_AC_NUMBER": args.ac if args.ac else ""           # Map to --ac/-a
        }

        # --- AC22: Handle document file selection for update-doc task ---
        if selected_task == "update-doc":
            doc_file_path_str = args.doc_file
            if not doc_file_path_str:
                print("\n--doc-file not provided for 'update-doc' task.")
                found_docs = find_documentation_files(BASE_DIR)
                if not found_docs:
                    print("Error: No documentation files (.md in root or docs/) found to choose from.", file=sys.stderr)
                    sys.exit(1)
                selected_doc_path_relative = prompt_user_to_select_doc(found_docs)
                if not selected_doc_path_relative:
                    print("User chose to quit. Exiting.")
                    sys.exit(0)
                # Convert relative Path object back to string for the variable dictionary
                doc_file_path_str = str(selected_doc_path_relative)
            else:
                 # Validate if the provided relative path exists
                provided_path = BASE_DIR / args.doc_file
                if not provided_path.is_file():
                     print(f"Error: Provided document file '{args.doc_file}' not found relative to project root.", file=sys.stderr)
                     sys.exit(1)
                 # Use the provided relative path string
                doc_file_path_str = args.doc_file

            task_variables["ARQUIVO_DOC_ALVO"] = doc_file_path_str
            if not task_variables["ARQUIVO_DOC_ALVO"]: # Safety check
                 print("Error: Target document file could not be determined for update-doc task.", file=sys.stderr)
                 sys.exit(1)
            print(f"Target document file set to: {task_variables['ARQUIVO_DOC_ALVO']}")
        # --- End AC22 ---

        print(f"\nFinal Variables for template: {task_variables}")

        # Load initial meta-prompt
        meta_prompt_content_original = load_and_fill_template(selected_meta_prompt_path, task_variables)
        if not meta_prompt_content_original:
             print(f"Error loading or filling the meta-prompt. Exiting.", file=sys.stderr)
             sys.exit(1)
        meta_prompt_content_current = meta_prompt_content_original # Keep track of the current version

        # AC13 Observação Adicional: Append web search encouragement to meta-prompt
        if args.web_search:
            print("  Appending web search encouragement to meta-prompt...")
            meta_prompt_content_current += WEB_SEARCH_ENCOURAGEMENT_PT

        # --- AC35: Handle --only-meta flag ---
        if args.only_meta:
            print("\n--- Filled Meta-Prompt (as requested by --only-meta) ---")
            print(meta_prompt_content_current.strip())
            print("--- End of Meta-Prompt ---")
            print("\nExiting script as requested by --only-meta.")
            sys.exit(0)
        # --- End AC35 ---

        # --- Initialize GenAI Client if not done already (e.g., if -g was used) ---
        if genai_client is None:
             if not initialize_genai_client():
                 sys.exit(1)
        # --- End Client Initialization ---

        # Prepare context parts (reading .txt, .json, .md files)
        context_parts = prepare_context_parts(latest_context_dir, COMMON_CONTEXT_DIR)
        if not context_parts:
             print("Warning: No context files loaded. The AI might lack sufficient information.", file=sys.stderr)

        # --- Prepare Tools based on flags (AC13) ---
        tools_list = []
        if args.web_search:
            print("  Configuring Google Search Retrieval tool...")
            # Using default config for GoogleSearchRetrieval
            google_search_retrieval_tool = types.Tool(
                google_search_retrieval=types.GoogleSearchRetrieval()
            )
            tools_list.append(google_search_retrieval_tool)
            print("  Google Search Retrieval tool added.")
        # Add other tools here if needed based on future args

        # --- Create base GenerateContentConfig if tools are needed ---
        base_config = None
        if tools_list:
            # Assuming config should be of type types.GenerateContentConfig
            # Use **config_dict if base_config is a dict, or merge attributes if it's an object
            config_dict = {"tools": tools_list}
            # If other base configs are added later, merge them here
            # e.g., config_dict.update({"safety_settings": [...]})
            base_config = types.GenerateContentConfig(**config_dict) # Unpack dict to create the object
            print("  GenerateContentConfig created with tools.")
        # Add other base config options here if necessary (e.g., safety_settings)

        # --- AC36: Optional 5-minute sleep before first API call ---
        if args.with_sleep:
            sleep_duration_seconds = 300
            print(f"\n--with-sleep flag detected. Waiting for {sleep_duration_seconds // 60} minutes before proceeding...")
            for _ in tqdm(range(sleep_duration_seconds), desc="Waiting 5 minutes (--with-sleep)", unit="s", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}s [{elapsed}<{remaining}]"):
                time.sleep(1)
            print("Wait complete. Proceeding with API interaction.")
        # --- End AC36 ---

        print("\nStarting interaction with Gemini API...")

        # --- Step 1 Loop (Meta-Prompt + Context -> Final Prompt) ---
        prompt_final_content: Optional[str] = None
        while True:
            print(f"\nStep 1: Sending Meta-Prompt and Context (Model: {GEMINI_MODEL})...")
            # Pass prompt using keyword argument 'text='
            contents_etapa1 = [types.Part.from_text(text=meta_prompt_content_current)] + context_parts
            try:
                prompt_final_content = execute_gemini_call(GEMINI_MODEL, contents_etapa1, config=base_config)

                print("\n------------------------")
                print("  >>> Final Prompt Received (Step 1):")
                print("  ```")
                print(prompt_final_content.strip())
                print("  ```")
                print("------------------------")

                # AC30: Check --yes flag to skip confirmation
                if args.yes:
                    print("  Step 1 automatically confirmed (--yes flag).")
                    user_choice_step1 = 'y'
                    observation_step1 = None
                else:
                    user_choice_step1, observation_step1 = confirm_step("Use this generated prompt for Step 2?")

                if user_choice_step1 == 'y':
                    break # Exit Step 1 loop, proceed to Step 2
                elif user_choice_step1 == 'q':
                    print("Exiting after Step 1 as requested.")
                    sys.exit(0)
                elif user_choice_step1 == 'n':
                    # AC11: Incorporate observation into meta-prompt for retry
                    print(f"Received observation for Step 1 retry: '{observation_step1}'")
                    meta_prompt_content_current = modify_prompt_with_observation(meta_prompt_content_current, observation_step1)
                    # Continue loop to retry Step 1 with modified prompt
                else: # Should not happen due to confirm_step loop
                    print("Internal error in confirmation logic. Exiting.", file=sys.stderr)
                    sys.exit(1)

            except (errors.APIError, google_api_core_exceptions.ResourceExhausted) as e: # Catch specific API errors (AC32)
                print(f"  An API error occurred during Step 1: {e}", file=sys.stderr)
                # The execute_gemini_call function already tried rotating the key if it was a rate limit error.
                # Ask the user if they want to retry the call (potentially with the new key or the same key if rotation failed).
                retry_choice, _ = confirm_step("API call failed in Step 1. Retry?")
                if retry_choice == 'q' or retry_choice == 'n':
                    print("Exiting due to API error in Step 1.")
                    sys.exit(1)
                # If 'y', loop continues to retry Step 1
            except Exception as e: # Catches other errors
                print(f"  An unexpected error occurred during Step 1 execution: {e}", file=sys.stderr)
                traceback.print_exc()
                # Ask user if they want to retry in case of unexpected errors too
                retry_choice, _ = confirm_step("An unexpected error occurred in Step 1. Retry?")
                if retry_choice == 'q' or retry_choice == 'n':
                    print("Exiting due to unexpected error in Step 1.")
                    sys.exit(1)
                # If 'y', loop continues


        if not prompt_final_content: # Should ideally not happen if loop breaks on 'y'
            print("Error: Could not obtain final prompt from Step 1. Aborting.", file=sys.stderr)
            sys.exit(1)

        # --- Step 2 Loop (Final Prompt + Context -> Final Response) ---
        resposta_final_content: Optional[str] = None
        prompt_final_content_current = prompt_final_content # Keep track of current final prompt

        # AC13 Observação Adicional: Append web search encouragement to final prompt
        if args.web_search:
            print("  Appending web search encouragement to final prompt...")
            prompt_final_content_current += WEB_SEARCH_ENCOURAGEMENT_PT
        

        # --- AC36: Optional 5-minute sleep before second API call ---
        if args.with_sleep:
            sleep_duration_seconds = 300
            print(f"\n--with-sleep flag detected. Waiting for {sleep_duration_seconds // 60} minutes before proceeding...")
            for _ in tqdm(range(sleep_duration_seconds), desc="Waiting 5 minutes (--with-sleep)", unit="s", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}s [{elapsed}<{remaining}]"):
                time.sleep(1)
            print("Wait complete. Proceeding with API interaction.")
        # --- End AC36 ---

        while True:
            print(f"\nStep 2: Sending Final Prompt and Context (Model: {GEMINI_MODEL})...")
            # Pass final prompt using keyword argument 'text='
            contents_etapa2 = [types.Part.from_text(text=prompt_final_content_current)] + context_parts
            try:
                # AC27: This is the execution of the second step as required by AC27
                resposta_final_content = execute_gemini_call(GEMINI_MODEL, contents_etapa2, config=base_config)
                print("\n------------------------")
                print("  >>> Final Response Received (Step 2):")
                print("  ```")
                print(resposta_final_content.strip())
                print("  ```")
                print("------------------------")

                # AC30: Check --yes flag to skip confirmation for this step's output
                if args.yes:
                    print("  Step 2 automatically confirmed (--yes flag). Proceeding to final action confirmation.")
                    # Skip the intermediate confirmation but still need to check for final action below
                    break # Exit the Step 2 retry loop
                else:
                    user_choice_step2, observation_step2 = confirm_step("Use this generated response for the final action?")

                    if user_choice_step2 == 'y':
                        break # Exit Step 2 loop, proceed to final action confirmation
                    elif user_choice_step2 == 'q':
                        print("Exiting without proceeding to final action as requested.")
                        sys.exit(0)
                    elif user_choice_step2 == 'n':
                         # AC11: Incorporate observation into final prompt for retry
                        print(f"Received observation for Step 2 retry: '{observation_step2}'")
                        prompt_final_content_current = modify_prompt_with_observation(prompt_final_content_current, observation_step2)
                        # Continue loop to retry Step 2 with modified prompt
                    else: # Should not happen
                        print("Internal error in confirmation logic. Exiting.", file=sys.stderr)
                        sys.exit(1)

            except (errors.GoogleAPIError, google_api_core_exceptions.ResourceExhausted) as e: # Catch specific API errors (AC32)
                print(f"  An API error occurred during Step 2: {e}", file=sys.stderr)
                # The execute_gemini_call function already tried rotating the key if it was a rate limit error.
                retry_choice, _ = confirm_step("API call failed in Step 2. Retry?")
                if retry_choice == 'q' or retry_choice == 'n':
                    print("Exiting due to API error in Step 2.")
                    sys.exit(1)
                # If 'y', loop continues to retry Step 2
            except Exception as e: # Catches other errors
                print(f"  An unexpected error occurred during Step 2 execution: {e}", file=sys.stderr)
                traceback.print_exc()
                retry_choice, _ = confirm_step("An unexpected error occurred in Step 2. Retry?")
                if retry_choice == 'q' or retry_choice == 'n':
                    print("Exiting due to unexpected error in Step 2.")
                    sys.exit(1)
                # If 'y', loop continues


        # --- Final Action Confirmation & Execution (AC30 ensures this part is NOT skipped by --yes) ---
        if resposta_final_content is None: # Check if response was actually generated
            print("Error: No final response generated after Step 2. Aborting.", file=sys.stderr)
            sys.exit(1)

        if selected_task == 'create-pr':
            # --- Create PR Logic ---
            print("\nParsing PR content...")
            pr_title, pr_body = parse_pr_content(resposta_final_content)
            if pr_title and pr_body is not None:
                print("  Successfully parsed PR Title and Body.")
                # User confirmation happens inside create_github_pr now
                current_branch = get_current_branch() # AC29: Get current branch
                if not current_branch:
                    print("Error: Could not determine current Git branch. Cannot create PR.", file=sys.stderr)
                    sys.exit(1)
                print(f"  Current Branch (Head): {current_branch}") # Log head branch
                target_branch = args.target_branch
                print(f"  Target Branch (Base): {target_branch}") # Log base branch

                # Ensure "Closes #ISSUE" is in the body
                issue_ref_str = f"Closes #{args.issue}"
                if issue_ref_str not in pr_body:
                    print(f"  Warning: '{issue_ref_str}' not found in LLM body. Appending it.")
                    pr_body += f"\n\n{issue_ref_str}"

                # AC37: Check for new commits BEFORE creating the PR
                if not check_new_commits(target_branch, current_branch):
                    print(f"Error: No new commits found on branch '{current_branch}' compared to '{target_branch}'. PR creation aborted.", file=sys.stderr)
                    sys.exit(1) # Exit as there's nothing to PR

                # AC35 to AC41 will be implemented within this function call
                if create_github_pr(pr_title, pr_body, current_branch, target_branch, args.draft):
                    print("\nPull Request creation process finished.")
                    sys.exit(0) # Exit successfully after PR creation attempt
                else:
                    print("\nPull Request creation failed or was cancelled. Exiting.")
                    sys.exit(1) # Exit with error if PR creation failed
            else:
                # Parsing failed - ask user if they want to provide feedback to redo Step 2
                print("Error: Parsing PR Title/Body failed. Please provide feedback to retry Step 2 generation or quit.", file=sys.stderr)
                # This path should ideally trigger a retry of Step 2 in the main loop, but needs careful handling
                # For simplicity now, we exit. A more robust solution would integrate this back into the Step 2 loop.
                sys.exit(1)
            # ---- End Create PR Logic ----
        else:
            # --- Save File Logic for other tasks ---
            # AC30: This confirmation is NOT skipped by --yes
            user_choice_save, _ = confirm_step("Confirm saving this response?")
            if user_choice_save == 'y':
                 print("\nSaving Final Response...")
                 save_llm_response(selected_task, resposta_final_content.strip())
            elif user_choice_save == 'q':
                 print("Exiting without saving the response as requested.")
                 sys.exit(0)
            else: # 'n' was chosen - This path might be confusing after --yes was used for step 2.
                  # Consider clarifying or directly exiting if 'n' is chosen here after --yes was used before.
                 print("Operation cancelled by user. Not saving the response.")
                 sys.exit(0)
            # --- End Save File Logic ---


    except SystemExit as e:
        if e.code != 0:
             print(f"\nScript exited with code {e.code}.", file=sys.stderr)
        sys.exit(e.code)
    except Exception as e:
        print(f"\nUnexpected error during execution: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)