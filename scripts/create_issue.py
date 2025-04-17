import argparse
import os
import sys
import subprocess
import re # Importar re para regex
import json
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dotenv import load_dotenv
import traceback # Adicionado para melhor depuração

# --- Constantes (mantidas como antes) ---
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INPUT_FILE = BASE_DIR / "planos/plano_dev.txt"
TEMPLATE_DIR = BASE_DIR / "project_templates/issue_bodies"
DEFAULT_TEMPLATE_NAME = "default_body.md" # Fallback template filename
DEFAULT_LABEL = "todo"
DEFAULT_ASSIGNEE = "@me"
DEFAULT_LABEL_COLOR = "ededed"
PROJECT_PRIMARY_OWNER = "@me" # First place to look for projects
REPO_TARGET = "" # Default: use current repo. Can be set via --repo or env var
GH_ISSUE_LIST_LIMIT = 500 # How many recent open issues to check for duplicates

# --- Variáveis Globais (mantidas como antes) ---
checked_labels: Dict[str, bool] = {} # Cache label existence check {label_name: exists_or_created}
checked_milestones: Dict[str, Optional[int]] = {} # Cache milestone check {title: number or None if not found}
repo_owner: Optional[str] = None # Determined later


# --- Funções Auxiliares (mantidas como antes) ---
def command_exists(cmd: str) -> bool:
    """Check if a command exists on the system."""
    # (Código da função mantido)
    return subprocess.run(['which', cmd], capture_output=True, text=True).returncode == 0

def suggest_install(cmd_name: str, pkg_name: Optional[str] = None) -> None:
    """Suggests installation commands based on common package managers."""
    # (Código da função mantido)
    pkg = pkg_name or cmd_name
    print(f"  AVISO: Comando '{cmd_name}' não encontrado.", file=sys.stderr)
    print(f"  > Para usar esta funcionalidade, tente instalar o pacote '{pkg}'.", file=sys.stderr)
    if command_exists('apt'):
        print(f"  > Sugestão (Debian/Ubuntu): sudo apt update && sudo apt install {pkg}", file=sys.stderr)
    elif command_exists('dnf') or command_exists('yum'):
        pm = 'dnf' if command_exists('dnf') else 'yum'
        print(f"  > Sugestão (Fedora/RHEL): sudo {pm} install {pkg}", file=sys.stderr)
    elif command_exists('brew'):
        print(f"  > Sugestão (macOS): brew install {pkg}", file=sys.stderr)
    else:
        print(f"  > Verifique o gerenciador de pacotes do seu sistema para instalar '{pkg}'.", file=sys.stderr)

def run_command(cmd_list: List[str], check: bool = True, capture: bool = True, input_data: Optional[str] = None) -> Tuple[int, str, str]:
    """Runs a subprocess command and returns exit code, stdout, stderr."""
    # (Código da função mantido)
    try:
        process = subprocess.run(
            cmd_list,
            capture_output=capture,
            text=True,
            input=input_data,
            check=check, # Raises CalledProcessError if check=True and return code is non-zero
            cwd=BASE_DIR # Run commands from project root
        )
        return process.returncode, process.stdout or "", process.stderr or ""
    except FileNotFoundError:
        print(f"Error: Command '{cmd_list[0]}' not found. Is it installed and in PATH?", file=sys.stderr)
        return 1, "", f"Command not found: {cmd_list[0]}"
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {' '.join(cmd_list)}", file=sys.stderr)
        print(f"Exit Code: {e.returncode}", file=sys.stderr)
        print(f"Stderr: {e.stderr}", file=sys.stderr)
        print(f"Stdout: {e.stdout}", file=sys.stderr)
        return e.returncode, e.stdout or "", e.stderr or ""
    except Exception as e:
        print(f"Unexpected error running command {' '.join(cmd_list)}: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1, "", str(e)


def escape_for_jq_string(value: str) -> str:
    """Escapes a string for safe embedding within a jq filter string."""
    # (Código da função mantido)
    return value.replace('\\', '\\\\').replace('"', '\\"')

def load_env_vars(args: argparse.Namespace) -> Dict[str, Any]:
    """Loads config from .env, returning a dict of relevant settings."""
    # (Código da função mantido)
    config = {}
    dotenv_path = BASE_DIR / '.env'
    if dotenv_path.is_file():
        print(f"Loading environment variables from: {dotenv_path.relative_to(BASE_DIR)}")
        load_dotenv(dotenv_path=dotenv_path, verbose=True)
    else:
        print("No .env file found, using script defaults and CLI args.", file=sys.stderr)
    config['repo_target'] = args.repo or os.getenv('GH_REPO_TARGET', REPO_TARGET)
    config['project_owner'] = args.project_owner or os.getenv('GH_PROJECT_OWNER', PROJECT_PRIMARY_OWNER)
    config['default_assignee'] = args.default_assignee or os.getenv('DEFAULT_ASSIGNEE', DEFAULT_ASSIGNEE)
    config['default_label'] = args.default_label or os.getenv('DEFAULT_LABEL', DEFAULT_LABEL)
    config['default_label_color'] = args.default_color or os.getenv('DEFAULT_LABEL_COLOR', DEFAULT_LABEL_COLOR)
    return config

def find_project_id(project_name_or_num: str, owner: str, repo_flags: List[str]) -> Optional[str]:
    """Finds a GitHub project ID by its title or number for a specific owner."""
    # (Código da função mantido)
    print(f"  Searching for project '{project_name_or_num}' under owner '{owner}'...")
    escaped_proj = escape_for_jq_string(project_name_or_num)
    jq_filter = f'.projects[] | select(.title == "{escaped_proj}" or (.number | tostring) == "{escaped_proj}") | .id'
    cmd = ['gh', 'project', 'list', '--owner', owner, '--format', 'json', '--jq', jq_filter]
    exit_code, stdout, stderr = run_command(cmd, check=False, capture=True)
    if exit_code != 0:
        print(f"  Warning: Failed to list projects for owner '{owner}'. Stderr: {stderr.strip()}", file=sys.stderr)
        return None
    project_id = stdout.strip().split('\n')[0] # Get the first matching ID
    if project_id:
        print(f"    Found project ID: {project_id}")
        return project_id
    else:
        print(f"    Project '{project_name_or_num}' not found under owner '{owner}'.")
        return None


def check_and_create_label(label_name: str, repo_flags: List[str], color: str) -> bool:
    """Checks if a label exists, creates it if not. Returns True if available/created."""
    # (Código da função mantido)
    global checked_labels
    if label_name in checked_labels:
        return checked_labels[label_name]
    print(f"    Checking label: '{label_name}'...")
    escaped_label = escape_for_jq_string(label_name)
    jq_filter = f'.[] | select(.name == "{escaped_label}")'
    cmd_list = ['gh', 'label', 'list'] + repo_flags + ['--search', label_name, '--json', 'name', '--jq', jq_filter]
    exit_code, stdout, _ = run_command(cmd_list, check=False, capture=True)
    if exit_code == 0 and stdout.strip():
        print(f"      Label '{label_name}' exists.")
        checked_labels[label_name] = True
        return True
    elif exit_code != 0:
         print(f"      Warning: Failed to check label '{label_name}'. Assuming it doesn't exist.", file=sys.stderr)
    print(f"      Label '{label_name}' not found or check failed. Creating...")
    cmd_create = ['gh', 'label', 'create', label_name] + repo_flags + ['--color', color, '--description', 'Created by script']
    exit_code_create, stdout_create, stderr_create = run_command(cmd_create, check=False, capture=True)
    if exit_code_create == 0:
        print(f"      Label '{label_name}' created.")
        checked_labels[label_name] = True
        return True
    else:
        if "already exists" in stderr_create.lower():
            print(f"      Label '{label_name}' likely already exists (creation failed with 'already exists').")
            checked_labels[label_name] = True
            return True
        else:
            print(f"      Error: Failed to create label '{label_name}'. Stderr: {stderr_create.strip()}", file=sys.stderr)
            checked_labels[label_name] = False
            return False

def check_and_create_milestone(title: str, description: Optional[str], repo_flags: List[str]) -> Optional[str]:
    """Checks if a milestone exists by title, creates if not (if desc provided). Returns title if available/created."""
    # (Código da função mantido)
    global checked_milestones
    if title in checked_milestones:
        return title if checked_milestones[title] is not None else None # Return title if exists
    print(f"  Checking milestone: '{title}'...")
    escaped_title = escape_for_jq_string(title)
    jq_filter = f'.[] | select(.title == "{escaped_title}") | .number' # Check by title
    cmd_list = ['gh', 'milestone', 'list'] + repo_flags + ['--json', 'title,number', '--jq', jq_filter]
    exit_code, stdout, stderr = run_command(cmd_list, check=False, capture=True)
    if exit_code != 0:
        print(f"    Warning: Failed to list milestones. Stderr: {stderr.strip()}", file=sys.stderr)
        checked_milestones[title] = None
        return None
    milestone_num = stdout.strip().split('\n')[0]
    if milestone_num:
        print(f"    Milestone '{title}' found (Number: {milestone_num}).")
        checked_milestones[title] = int(milestone_num)
        return title # Return the title for association
    print(f"    Milestone '{title}' not found.")
    if description:
        print(f"    Attempting to create milestone '{title}'...")
        cmd_create = ['gh', 'milestone', 'create', '--title', title, '--description', description] + repo_flags
        exit_code_create, stdout_create, stderr_create = run_command(cmd_create, check=False, capture=True)
        if exit_code_create == 0:
            print(f"    Milestone '{title}' created.")
            checked_milestones[title] = -1 # Mark as created
            return title
        else:
            if "already exists" in stderr_create.lower():
                 print(f"    Milestone '{title}' likely already exists (creation failed). Using title.")
                 checked_milestones[title] = -1 # Mark as likely existing
                 return title
            else:
                print(f"    Error: Failed to create milestone '{title}'. Stderr: {stderr_create.strip()}", file=sys.stderr)
                checked_milestones[title] = None
                return None
    else:
        print(f"    Description not provided for milestone '{title}'. Cannot create.")
        checked_milestones[title] = None
        return None

def find_existing_issue(title: str, repo_flags: List[str]) -> Optional[int]:
    """Finds the most recent OPEN issue with the exact title."""
    # (Código da função mantido)
    print(f"  Checking for existing open issue with title '{title}'...")
    escaped_title_jq = escape_for_jq_string(title)
    jq_filter = f'map(select(.title == "{escaped_title_jq}" and .state == "OPEN")) | sort_by(.updatedAt) | reverse | .[0].number // empty'
    cmd_list = ['gh', 'issue', 'list'] + repo_flags + ['--state', 'open', '--limit', str(GH_ISSUE_LIST_LIMIT), '--json', 'number,title,state,updatedAt']
    exit_code, stdout, stderr = run_command(cmd_list, check=False, capture=True)
    if exit_code != 0:
        print(f"    Warning: Failed to list issues (Code: {exit_code}). Stderr: {stderr.strip()}", file=sys.stderr)
        return None
    try:
        issue_number_str = subprocess.run(['jq', '-r', jq_filter], input=stdout, text=True, check=True, capture_output=True).stdout.strip()
        if issue_number_str:
            print(f"    Found existing open issue: #{issue_number_str}")
            return int(issue_number_str)
        else:
            print("    No existing open issue found with that exact title.")
            return None
    except subprocess.CalledProcessError as e:
        print(f"    Warning: jq processing failed (Code: {e.returncode}). Stderr: {e.stderr}", file=sys.stderr)
        return None
    except ValueError:
        print(f"    Warning: Could not parse issue number from jq output: '{issue_number_str}'.", file=sys.stderr)
        return None

def prepare_issue_body(template_dir: Path, issue_type: str, issue_data: Dict[str, str]) -> str:
    """Loads the appropriate template and fills placeholders."""
    # (Código da função mantido)
    template_file = template_dir / f"{issue_type.lower()}_body.md"
    if not template_file.is_file():
        print(f"    Warning: Template '{template_file.name}' not found. Trying 'test' template...", file=sys.stderr)
        template_file = template_dir / "test_body.md" # Fallback to test for test type
        if not template_file.is_file():
            print(f"    Warning: Test template not found. Trying chore template...", file=sys.stderr)
            template_file = template_dir / "chore_body.md" # Fallback to chore for chore/refactor
            if not template_file.is_file():
                 print(f"    Warning: Chore template not found. Trying default...", file=sys.stderr)
                 template_file = template_dir / DEFAULT_TEMPLATE_NAME
                 if not template_file.is_file():
                      print(f"    Warning: Default template '{DEFAULT_TEMPLATE_NAME}' not found. Using generic body.", file=sys.stderr)
                      return f"Issue created from script for title: {issue_data.get('TITLE', '[No Title]')}\n\nDetails:\n" + "\n".join(f"- {k}: {v}" for k, v in issue_data.items() if k != 'TITLE')

    print(f"    Using template: {template_file.relative_to(BASE_DIR)}")
    try:
        body = template_file.read_text(encoding='utf-8')
        for key, value in issue_data.items():
            placeholder = f"__{key}__"
            # Usa uma função lambda para garantir que o valor seja string antes de substituir
            body = re.sub(re.escape(placeholder), lambda m: str(value) if value is not None else '', body)

        body = re.sub(r'__([A-Z_]+)__', r'[Placeholder \1 not provided]', body)
        return body
    except Exception as e:
        print(f"    Error reading or processing template {template_file}: {e}", file=sys.stderr)
        return f"Error processing template. Raw data: {issue_data}"

# --- NOVA FUNÇÃO parse_plan_file ---
def parse_plan_file(filepath: Path) -> List[Dict[str, str]]:
    """Parses the structured plan file into a list of issue data dictionaries."""
    issues = []
    if not filepath.is_file():
        print(f"Error: Input file '{filepath}' not found.", file=sys.stderr)
        return issues

    try:
        content = filepath.read_text(encoding='utf-8')
        # Split into blocks using ------ as delimiter, handle potential extra newlines
        blocks = re.split(r'\n------\s*\n', content.strip())

        for i, block in enumerate(blocks):
            if not block.strip():
                continue

            print(f"\n--- Processing Block {i+1} ---")
            issue_data: Dict[str, str] = {}
            current_key: Optional[str] = None
            current_value_lines: List[str] = []

            def save_previous_value():
                """Helper to save the accumulated value for the previous key."""
                nonlocal current_key, current_value_lines, issue_data
                if current_key and current_value_lines:
                    full_value = "\n".join(current_value_lines).strip()
                    # LÓGICA MODIFICADA: Remove comments only for non-TITLE/non-PARENT_ISSUE multi-lines
                    if current_key not in ["TITLE", "PARENT_ISSUE"]:
                        # Remove comments starting a line or preceded by space,
                        # but keep # followed by digits
                        # (?m) for multiline, ^\s*#.* matches comment lines
                        # \s+#(?! \d) matches space+hash not followed by space+digit
                        # This is a heuristic, might need refinement
                        cleaned_value = re.sub(r'(?m)(^\s*#.*|\s+#(?! ?\d).*)', '', full_value)
                        issue_data[current_key] = issue_data[current_key] + "\n" + cleaned_value.strip()
                    else:
                        # Keep value as is for TITLE/PARENT_ISSUE (though they shouldn't be multi-line usually)
                        issue_data[current_key] = issue_data[current_key] + "\n" + full_value
                    current_value_lines = []


            for line in block.strip().split('\n'):
                line_strip = line.strip()
                # Check for KEY: VALUE pattern
                match = re.match(r'^([A-Z_]+):\s*(.*)', line) # Key must be uppercase/underscore
                if match:
                    save_previous_value() # Save the value of the *previous* key

                    current_key = match.group(1).strip()
                    raw_value_part = match.group(2).strip()

                    # NOVA LÓGICA: Handle TITLE and PARENT_ISSUE specifically
                    if current_key in ["TITLE", "PARENT_ISSUE"]:
                        issue_data[current_key] = raw_value_part # Store raw value, no comment stripping
                    else:
                        # Original logic for other keys: strip comment after first #
                        issue_data[current_key] = raw_value_part.split('#', 1)[0].rstrip()

                    current_value_lines = [] # Reset for potential multi-line
                    print(f"  Parsed Key: {current_key}, Initial Value: '{issue_data[current_key]}'")

                elif current_key:
                    # LÓGICA MODIFICADA: Append to multi-line only if NOT TITLE or PARENT_ISSUE
                    if current_key not in ["TITLE", "PARENT_ISSUE"]:
                         current_value_lines.append(line) # Keep original indentation/comments for now
                    # else: Ignore continuation lines for TITLE/PARENT_ISSUE

            save_previous_value() # Save the last key's value

            if 'TITLE' in issue_data:
                issues.append(issue_data)
            else:
                print("  Warning: Skipping block - Missing TITLE field.", file=sys.stderr)

    except Exception as e:
        print(f"Error parsing plan file {filepath}: {e}", file=sys.stderr)
        traceback.print_exc()

    return issues
# --- FIM DA NOVA FUNÇÃO ---


def create_github_issue(issue_data: Dict[str, str], issue_body: str, cli_args: argparse.Namespace, config: Dict[str, Any], repo_flags: List[str]) -> bool:
    """Creates a new GitHub issue using gh CLI."""
    # (Código da função mantido)
    global repo_owner
    print("  Attempting to create new issue...")
    cmd_create = ['gh', 'issue', 'create']
    cmd_create.extend(['-t', issue_data['TITLE']])
    cmd_create.extend(['-F', '-'])
    assignee = issue_data.get('ASSIGNEE', config['default_assignee'])
    if assignee:
        cmd_create.extend(['-a', assignee])
    labels_str = issue_data.get('LABELS', '')
    issue_type = issue_data.get('TYPE', 'default').lower()
    labels_to_add = set(filter(None, [label.strip() for label in labels_str.split(',')]))
    if issue_type != 'default':
        labels_to_add.add(issue_type)
    if not labels_to_add and config['default_label']:
         labels_to_add.add(config['default_label'])
    final_labels = []
    for label in labels_to_add:
        if check_and_create_label(label, repo_flags, config['default_label_color']):
             final_labels.append(label)
        else:
            print(f"    Warning: Skipping label '{label}' due to creation/check failure.", file=sys.stderr)
    if final_labels:
        # Combine labels into a single -l argument for create
        cmd_create.extend(['-l', ','.join(final_labels)])
    milestone_title = cli_args.milestone_title
    if milestone_title:
        cmd_create.extend(['-m', milestone_title])
    elif cli_args.milestone_title is not None:
         print(f"    Error: Cannot assign mandatory milestone '{cli_args.milestone_title}' during creation.", file=sys.stderr)
         return False
    project_name_or_num = issue_data.get('PROJECT')
    if project_name_or_num:
        project_id = find_project_id(project_name_or_num, config['project_owner'], repo_flags)
        if not project_id and config['project_owner'] != repo_owner:
             project_id = find_project_id(project_name_or_num, repo_owner, repo_flags)
        if project_id:
            print(f"    Associating with project '{project_name_or_num}'.")
            cmd_create.extend(['-p', project_name_or_num])
        else:
             print(f"    Error: Project '{project_name_or_num}' not found under '{config['project_owner']}' or '{repo_owner}'. Cannot create issue.", file=sys.stderr)
             return False
    cmd_create.extend(repo_flags)
    if cli_args.dry_run:
        print("  [DRY RUN] Would execute:")
        print(f"    echo '<issue_body>' | {' '.join(cmd_create)}")
        return True
    print(f"  Executing: echo '<issue_body>' | {' '.join(cmd_create)}")
    exit_code, stdout, stderr = run_command(cmd_create, check=False, capture=True, input_data=issue_body)
    if exit_code == 0:
        print(f"  Issue created successfully: {stdout.strip()}")
        return True
    else:
        print(f"  Error creating issue (Code: {exit_code}). Stderr: {stderr.strip()}", file=sys.stderr)
        return False


def edit_github_issue(issue_number: int, issue_data: Dict[str, str], issue_body: str, cli_args: argparse.Namespace, config: Dict[str, Any], repo_flags: List[str]) -> bool:
    """Edits an existing GitHub issue using gh CLI."""
    # (Código da função mantido)
    print(f"  Attempting to edit existing issue #{issue_number}...")
    cmd_edit = ['gh', 'issue', 'edit', str(issue_number)]
    cmd_edit.extend(['--body-file', '-'])
    assignee = issue_data.get('ASSIGNEE', config['default_assignee'])
    if assignee:
        cmd_edit.extend(['--add-assignee', assignee])
    labels_str = issue_data.get('LABELS', '')
    issue_type = issue_data.get('TYPE', 'default').lower()
    labels_to_add = set(filter(None, [label.strip() for label in labels_str.split(',')]))
    if issue_type != 'default':
        labels_to_add.add(issue_type)
    added_labels_count = 0
    for label in labels_to_add:
        if check_and_create_label(label, repo_flags, config['default_label_color']):
             cmd_edit.extend(['--add-label', label])
             added_labels_count += 1
        else:
            print(f"    Warning: Skipping adding label '{label}' during edit due to creation/check failure.", file=sys.stderr)
    if added_labels_count > 0:
         print(f"    Will attempt to add {added_labels_count} label(s).")
    milestone_title = cli_args.milestone_title
    if milestone_title:
        cmd_edit.extend(['-m', milestone_title])
    elif cli_args.milestone_title is not None:
         print(f"    Error: Cannot assign mandatory milestone '{cli_args.milestone_title}' during edit.", file=sys.stderr)
         return False
    if issue_data.get('PROJECT'):
        print(f"    Info: Project association ('{issue_data['PROJECT']}') is ignored during edit. Please verify/add manually if needed.")
    cmd_edit.extend(repo_flags)
    if cli_args.dry_run:
        print("  [DRY RUN] Would execute:")
        print(f"    echo '<issue_body>' | {' '.join(cmd_edit)}")
        return True
    print(f"  Executing: echo '<issue_body>' | {' '.join(cmd_edit)}")
    exit_code, stdout, stderr = run_command(cmd_edit, check=False, capture=True, input_data=issue_body)
    if exit_code == 0:
        print(f"  Issue #{issue_number} edited successfully.")
        return True
    else:
        print(f"  Error editing issue #{issue_number} (Code: {exit_code}). Stderr: {stderr.strip()}", file=sys.stderr)
        return False

# --- Função main (sem modificações significativas na lógica principal de loop) ---
def main(args: argparse.Namespace, config: Dict[str, Any]) -> int:
    """Main logic of the script."""
    global repo_owner
    input_file_path = Path(args.input_file)
    template_dir_path = TEMPLATE_DIR
    if not input_file_path.is_file():
        print(f"Error: Input file '{input_file_path}' not found.", file=sys.stderr)
        return 1
    if not template_dir_path.is_dir():
        print(f"Error: Template directory '{template_dir_path}' not found.", file=sys.stderr)
        return 1
    repo_flags = []
    if config['repo_target']:
        repo_flags.extend(['-R', config['repo_target']])
        print(f"Targeting repository: {config['repo_target']}")
        try:
            repo_owner = config['repo_target'].split('/')[0]
            if not repo_owner or '/' not in config['repo_target']: raise ValueError("Invalid format")
        except Exception:
            print(f"Error: Could not determine owner from repo target '{config['repo_target']}'. Expected format 'owner/repo'.", file=sys.stderr)
            return 1
    else:
        print("Using current repository.")
        exit_code, stdout, stderr = run_command(['gh', 'repo', 'view', '--json', 'owner', '--jq', '.owner.login'], check=False)
        if exit_code != 0 or not stdout.strip():
            print(f"Error: Failed to determine owner of current repository. Stderr: {stderr.strip()}", file=sys.stderr)
            return 1
        repo_owner = stdout.strip()
    print(f"Determined repository owner: {repo_owner}")
    global_milestone_title_to_use: Optional[str] = None
    if args.milestone_title:
        milestone_title = check_and_create_milestone(args.milestone_title, args.milestone_desc, repo_flags)
        if milestone_title:
            global_milestone_title_to_use = milestone_title
            print(f"Using milestone: '{global_milestone_title_to_use}'")
        else:
            print(f"Error: Failed to find or create the specified milestone '{args.milestone_title}'. Aborting.", file=sys.stderr)
            return 1
    parsed_issues = parse_plan_file(input_file_path) # Chama a função modificada
    if not parsed_issues:
        print("No issues found or parsed from the plan file.")
        return 0
    total_issues = len(parsed_issues)
    processed_count = 0
    error_count = 0
    print(f"\nStarting GitHub Issue processing for {total_issues} blocks...")
    for issue_data in parsed_issues:
        print("-" * 40)
        title = issue_data.get("TITLE")
        if not title:
            print("Skipping block: TITLE is missing.", file=sys.stderr)
            error_count += 1
            continue
        print(f"Processing Issue: '{title}'")
        issue_type = issue_data.get('TYPE', 'default')
        # Passa args.milestone_title para prepare_issue_body se for necessário no template
        issue_data['APPLIED_MILESTONE'] = global_milestone_title_to_use or ""
        issue_body = prepare_issue_body(template_dir_path, issue_type, issue_data)
        existing_issue_num = find_existing_issue(title, repo_flags)
        success = False
        if existing_issue_num:
            # Passa args (que contém o milestone verificado/criado) para a função de edição
            success = edit_github_issue(existing_issue_num, issue_data, issue_body, args, config, repo_flags)
        else:
            # Passa args (que contém o milestone verificado/criado) para a função de criação
            success = create_github_issue(issue_data, issue_body, args, config, repo_flags)
        if success:
            processed_count += 1
        else:
            error_count += 1
        if not args.dry_run:
            time.sleep(1)
    print("-" * 40)
    print("GitHub Issue processing finished.")
    print(f"Summary: {processed_count} issues processed successfully, {error_count} errors encountered.")
    return 0 if error_count == 0 else 1

# --- Função parse_arguments (sem alterações necessárias aqui) ---
def parse_arguments() -> argparse.Namespace:
    """Parses command-line arguments."""
    # (Código da função mantido)
    parser = argparse.ArgumentParser(
        description="Create or edit GitHub Issues from a structured plan file.",
        epilog=f"""Examples:
  # Process default file ({DEFAULT_INPUT_FILE.name})
  python {Path(sys.argv[0]).name}

  # Process a specific plan file
  python {Path(sys.argv[0]).name} planos/meu_plano.txt

  # Process default file and assign to a milestone (creates if needed with desc)
  python {Path(sys.argv[0]).name} --milestone-title "Sprint 5" --milestone-desc "Tasks for Sprint 5"

  # Process specific file for a different repo
  python {Path(sys.argv[0]).name} --repo another-owner/another-repo planos/outro_plano.txt

  # Dry run: Show what would happen without making changes
  python {Path(sys.argv[0]).name} --dry-run planos/meu_plano.txt
""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        'input_file',
        nargs='?',
        default=str(DEFAULT_INPUT_FILE),
        help=f"Path to the structured plan file (default: {DEFAULT_INPUT_FILE.relative_to(BASE_DIR)})"
    )
    parser.add_argument('--milestone-title', help="Title of the milestone to assign issues to. If it doesn't exist, it will be created if --milestone-desc is also provided.")
    parser.add_argument('--milestone-desc', help="Description for the milestone if it needs to be created.")
    parser.add_argument('-R', '--repo', metavar='OWNER/REPO', help=f"Target repository (default: current directory's repo, can be set via GH_REPO_TARGET env var). Overrides GH_REPO_TARGET if set.")
    parser.add_argument('--default-assignee', help=f"Default assignee if not specified in the plan file (default: {DEFAULT_ASSIGNEE}, can be set via DEFAULT_ASSIGNEE env var).")
    parser.add_argument('--default-label', help=f"Default label if no labels are specified (default: {DEFAULT_LABEL}, can be set via DEFAULT_LABEL env var).")
    parser.add_argument('--default-color', help=f"Default color for newly created labels (default: {DEFAULT_LABEL_COLOR}, can be set via DEFAULT_LABEL_COLOR env var).")
    parser.add_argument('--project-owner', help=f"Owner (@me or org/user) to search for projects first (default: {PROJECT_PRIMARY_OWNER}, can be set via GH_PROJECT_OWNER env var).")
    parser.add_argument('--dry-run', action='store_true', help="Simulate the process without actually creating or editing issues on GitHub.")
    return parser.parse_args()


# --- Ponto de Entrada (sem alterações) ---
if __name__ == "__main__":
    if not command_exists('gh'):
        suggest_install('gh')
        sys.exit(1)
    if not command_exists('jq'):
        suggest_install('jq')
        print("Warning: 'jq' not found. Issue duplicate checking and project finding might fail.", file=sys.stderr)

    parsed_args = parse_arguments()
    loaded_config = load_env_vars(parsed_args) # Load .env and merge with defaults/args

    exit_code = main(parsed_args, loaded_config)
    sys.exit(exit_code)