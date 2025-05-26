# -*- coding: utf-8 -*-
"""
Fixed version of the create_issue.py script.

The `parse_plan_file` function has been refactored to correctly handle:
- Leading whitespace before keys.
- Multiline values with indentation preservation.
- Accurate comment stripping for non-raw fields, respecting edge cases like `#digit` and `# at end.`.
- Raw value preservation (including comments and whitespace) for TITLE and PARENT_ISSUE fields.
"""

import argparse
import os
import sys
import subprocess
import re  # Importar re para regex
import json
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dotenv import load_dotenv
import traceback  # Adicionado para melhor depuração

# --- Constantes ---
# Assume BASE_DIR calculation might be different if run directly vs imported
try:
    BASE_DIR = Path(__file__).resolve().parent.parent
except NameError:
    # Fallback for interactive testing or different execution context
    BASE_DIR = Path(".").resolve()  # Adjust if needed

DEFAULT_INPUT_FILE = BASE_DIR / "planos/plano_dev.txt"
TEMPLATE_DIR = BASE_DIR / "templates/issue_bodies"
DEFAULT_TEMPLATE_NAME = "default_body.md"  # Fallback template filename
DEFAULT_LABEL = "todo"
DEFAULT_ASSIGNEE = "@me"
DEFAULT_LABEL_COLOR = "ededed"
PROJECT_PRIMARY_OWNER = "@me"  # First place to look for projects
REPO_TARGET = ""  # Default: use current repo. Can be set via --repo or env var
GH_ISSUE_LIST_LIMIT = 500  # How many recent open issues to check for duplicates

# --- Variáveis Globais ---
checked_labels: Dict[str, bool] = (
    {}
)  # Cache label existence check {label_name: exists_or_created}
checked_milestones: Dict[str, Optional[int]] = (
    {}
)  # Cache milestone check {title: number or None if not found}
repo_owner: Optional[str] = None  # Determined later


# --- Funções Auxiliares ---
def command_exists(cmd: str) -> bool:
    """Check if a command exists on the system."""
    # Use shutil.which for a more robust check
    import shutil

    return shutil.which(cmd) is not None


def suggest_install(cmd_name: str, pkg_name: Optional[str] = None) -> None:
    """Suggests installation commands based on common package managers."""
    pkg = pkg_name or cmd_name
    print(f"  AVISO: Comando '{cmd_name}' não encontrado.", file=sys.stderr)
    print(
        f"  > Para usar esta funcionalidade, tente instalar o pacote '{pkg}'.",
        file=sys.stderr,
    )
    if command_exists("apt"):
        print(
            f"  > Sugestão (Debian/Ubuntu): sudo apt update && sudo apt install {pkg}",
            file=sys.stderr,
        )
    elif command_exists("dnf") or command_exists("yum"):
        pm = "dnf" if command_exists("dnf") else "yum"
        print(f"  > Sugestão (Fedora/RHEL): sudo {pm} install {pkg}", file=sys.stderr)
    elif command_exists("brew"):
        print(f"  > Sugestão (macOS): brew install {pkg}", file=sys.stderr)
    else:
        print(
            f"  > Verifique o gerenciador de pacotes do seu sistema para instalar '{pkg}'.",
            file=sys.stderr,
        )


def run_command(
    cmd_list: List[str],
    check: bool = True,
    capture: bool = True,
    input_data: Optional[str] = None,
) -> Tuple[int, str, str]:
    """Runs a subprocess command and returns exit code, stdout, stderr."""
    try:
        process = subprocess.run(
            cmd_list,
            capture_output=capture,
            text=True,
            input=input_data,
            check=check,  # Raises CalledProcessError if check=True and return code is non-zero
            cwd=BASE_DIR,  # Run commands from project root
        )
        return process.returncode, process.stdout or "", process.stderr or ""
    except FileNotFoundError:
        print(
            f"Error: Command '{cmd_list[0]}' not found. Is it installed and in PATH?",
            file=sys.stderr,
        )
        return 1, "", f"Command not found: {cmd_list[0]}"
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {' '.join(cmd_list)}", file=sys.stderr)
        print(f"Exit Code: {e.returncode}", file=sys.stderr)
        print(f"Stderr: {e.stderr}", file=sys.stderr)
        print(f"Stdout: {e.stdout}", file=sys.stderr)
        return e.returncode, e.stdout or "", e.stderr or ""
    except Exception as e:
        print(
            f"Unexpected error running command {' '.join(cmd_list)}: {e}",
            file=sys.stderr,
        )
        traceback.print_exc()
        return 1, "", str(e)


def escape_for_jq_string(value: str) -> str:
    """Escapes a string for safe embedding within a jq filter string."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def load_env_vars(args: argparse.Namespace) -> Dict[str, Any]:
    """Loads config from .env, returning a dict of relevant settings."""
    config = {}
    # Use args.base_dir if available, otherwise use script's BASE_DIR
    base_dir_to_use = getattr(args, "base_dir", BASE_DIR)
    dotenv_path = base_dir_to_use / ".env"
    if dotenv_path.is_file():
        print(
            f"Loading environment variables from: {dotenv_path.relative_to(base_dir_to_use)}"
        )
        load_dotenv(dotenv_path=dotenv_path, verbose=True)
    else:
        print(
            f"No .env file found at {dotenv_path}, using script defaults and CLI args.",
            file=sys.stderr,
        )
    config["repo_target"] = args.repo or os.getenv("GH_REPO_TARGET", REPO_TARGET)
    config["project_owner"] = args.project_owner or os.getenv(
        "GH_PROJECT_OWNER", PROJECT_PRIMARY_OWNER
    )
    config["default_assignee"] = args.default_assignee or os.getenv(
        "DEFAULT_ASSIGNEE", DEFAULT_ASSIGNEE
    )
    config["default_label"] = args.default_label or os.getenv(
        "DEFAULT_LABEL", DEFAULT_LABEL
    )
    config["default_label_color"] = args.default_color or os.getenv(
        "DEFAULT_LABEL_COLOR", DEFAULT_LABEL_COLOR
    )
    return config


def find_project_id(
    project_name_or_num: str, owner: str, repo_flags: List[str]
) -> Optional[str]:
    """Finds a GitHub project ID by its title or number for a specific owner."""
    print(f"  Searching for project '{project_name_or_num}' under owner '{owner}'...")
    escaped_proj = escape_for_jq_string(project_name_or_num)
    jq_filter = f'.projects[] | select(.title == "{escaped_proj}" or (.number | tostring) == "{escaped_proj}") | .id'
    cmd = [
        "gh",
        "project",
        "list",
        "--owner",
        owner,
        "--format",
        "json",
        "--jq",
        jq_filter,
    ]
    exit_code, stdout, stderr = run_command(cmd, check=False, capture=True)
    if exit_code != 0:
        print(
            f"  Warning: Failed to list projects for owner '{owner}'. Stderr: {stderr.strip()}",
            file=sys.stderr,
        )
        return None
    project_id = stdout.strip().split("\n")[0]  # Get the first matching ID
    if project_id:
        print(f"    Found project ID: {project_id}")
        return project_id
    else:
        print(f"    Project '{project_name_or_num}' not found under owner '{owner}'.")
        return None


def check_and_create_label(label_name: str, repo_flags: List[str], color: str) -> bool:
    """Checks if a label exists, creates it if not. Returns True if available/created."""
    global checked_labels
    if label_name in checked_labels:
        return checked_labels[label_name]
    print(f"    Checking label: '{label_name}'...")
    escaped_label = escape_for_jq_string(label_name)
    jq_filter = f'.[] | select(.name == "{escaped_label}")'
    cmd_list = (
        ["gh", "label", "list"]
        + repo_flags
        + ["--search", label_name, "--json", "name", "--jq", jq_filter]
    )
    exit_code, stdout, _ = run_command(cmd_list, check=False, capture=True)
    if exit_code == 0 and stdout.strip():
        print(f"      Label '{label_name}' exists.")
        checked_labels[label_name] = True
        return True
    elif exit_code != 0:
        print(
            f"      Warning: Failed to check label '{label_name}'. Assuming it doesn't exist.",
            file=sys.stderr,
        )
    print(f"      Label '{label_name}' not found or check failed. Creating...")
    cmd_create = (
        ["gh", "label", "create", label_name]
        + repo_flags
        + ["--color", color, "--description", "Created by script"]
    )
    exit_code_create, stdout_create, stderr_create = run_command(
        cmd_create, check=False, capture=True
    )
    if exit_code_create == 0:
        print(f"      Label '{label_name}' created.")
        checked_labels[label_name] = True
        return True
    else:
        # Check stderr case-insensitively for "already exists" or similar GH CLI output
        stderr_lower = stderr_create.lower()
        if (
            "already exists" in stderr_lower
            or "name has already been taken" in stderr_lower
        ):
            print(
                f"      Label '{label_name}' likely already exists (creation failed, but error indicates existence)."
            )
            checked_labels[label_name] = True
            return True
        else:
            print(
                f"      Error: Failed to create label '{label_name}'. Stderr: {stderr_create.strip()}",
                file=sys.stderr,
            )
            checked_labels[label_name] = False
            return False


def check_and_create_milestone(
    title: str, description: Optional[str], repo_flags: List[str]
) -> Optional[str]:
    """Checks if a milestone exists by title, creates if not (if desc provided). Returns title if available/created."""
    global checked_milestones
    if title in checked_milestones:
        return (
            title if checked_milestones[title] is not None else None
        )  # Return title if exists
    print(f"  Checking milestone: '{title}'...")
    escaped_title = escape_for_jq_string(title)
    jq_filter = f'.[] | select(.title == "{escaped_title}") | .number'  # Check by title
    cmd_list = (
        ["gh", "milestone", "list"]
        + repo_flags
        + ["--json", "title,number", "--jq", jq_filter]
    )
    exit_code, stdout, stderr = run_command(cmd_list, check=False, capture=True)
    if exit_code != 0:
        print(
            f"    Warning: Failed to list milestones. Stderr: {stderr.strip()}",
            file=sys.stderr,
        )
        checked_milestones[title] = None
        return None
    milestone_num = stdout.strip().split("\n")[0]
    if milestone_num:
        try:
            num = int(milestone_num)
            print(f"    Milestone '{title}' found (Number: {num}).")
            checked_milestones[title] = num
            return title  # Return the title for association
        except ValueError:
            print(
                f"    Warning: Found milestone '{title}' but failed to parse number '{milestone_num}'. Assuming found.",
                file=sys.stderr,
            )
            checked_milestones[title] = -1  # Mark as found, number unknown
            return title

    print(f"    Milestone '{title}' not found.")
    if description is not None:  # Allow empty description for creation
        print(f"    Attempting to create milestone '{title}'...")
        cmd_create = [
            "gh",
            "milestone",
            "create",
            "--title",
            title,
            "--description",
            description,  # Pass description even if empty
        ] + repo_flags
        exit_code_create, stdout_create, stderr_create = run_command(
            cmd_create, check=False, capture=True
        )
        if exit_code_create == 0:
            print(f"    Milestone '{title}' created.")
            checked_milestones[title] = (
                -1
            )  # Mark as created (number not immediately needed)
            return title
        else:
            # Check stderr case-insensitively
            stderr_lower = stderr_create.lower()
            if (
                "already exists" in stderr_lower
                or "title has already been taken" in stderr_lower
            ):
                print(
                    f"    Milestone '{title}' likely already exists (creation failed, but error indicates existence). Using title."
                )
                checked_milestones[title] = -1  # Mark as likely existing
                return title
            else:
                print(
                    f"    Error: Failed to create milestone '{title}'. Stderr: {stderr_create.strip()}",
                    file=sys.stderr,
                )
                checked_milestones[title] = None
                return None
    else:
        print(f"    Description not provided for milestone '{title}'. Cannot create.")
        checked_milestones[title] = None
        return None


def find_existing_issue(title: str, repo_flags: List[str]) -> Optional[int]:
    """Finds the most recent OPEN issue with the exact title."""
    print(f"  Checking for existing open issue with title '{title}'...")
    # Using gh search issues is more reliable than listing and filtering large numbers
    # Note: Search has eventual consistency, might have slight delay.
    # `gh search issues` requires quoting the query string properly
    search_query = f'"{title}" in:title is:open is:issue'
    cmd_list = (
        ["gh", "search", "issues", search_query]
        + repo_flags
        + [
            "--json",
            "number,title,state,updatedAt",
            # Sort by updated date descending directly in the search
            "--order",
            "desc",
            "--sort",
            "updated",
            # Limit results early
            "--limit",
            "1",
            # Extract just the number if found
            "--jq",
            ".[0].number // empty",
        ]
    )
    exit_code, stdout, stderr = run_command(cmd_list, check=False, capture=True)

    if exit_code != 0:
        # Handle common search error: Needs login/scopes
        if "authentication required" in stderr.lower():
            print(
                f"    Error: Failed to search issues. Authentication required. Please run `gh auth login` or check token scopes. Stderr: {stderr.strip()}",
                file=sys.stderr,
            )
        else:
            print(
                f"    Warning: Failed to search issues (Code: {exit_code}). Stderr: {stderr.strip()}",
                file=sys.stderr,
            )
        return None

    issue_number_str = stdout.strip()
    if issue_number_str:
        try:
            issue_number = int(issue_number_str)
            # Double check title match because search can be fuzzy
            # We only need to check this specific issue now
            cmd_check = (
                ["gh", "issue", "view", str(issue_number)]
                + repo_flags
                + ["--json", "title"]
            )
            code_check, out_check, err_check = run_command(
                cmd_check, check=False, capture=True
            )
            if code_check == 0:
                try:
                    actual_title = json.loads(out_check).get("title")
                    if actual_title == title:
                        print(
                            f"    Found existing open issue with exact title match: #{issue_number}"
                        )
                        return issue_number
                    else:
                        print(
                            f"    Found issue #{issue_number} via search, but title ('{actual_title}') doesn't match '{title}' exactly. Treating as not found."
                        )
                        return None
                except json.JSONDecodeError:
                    print(
                        f"    Warning: Could not parse JSON checking title for issue #{issue_number}. Assuming mismatch.",
                        file=sys.stderr,
                    )
                    return None
            else:
                print(
                    f"    Warning: Found issue #{issue_number} via search, but failed to verify title. Stderr: {err_check.strip()}",
                    file=sys.stderr,
                )
                return None  # Treat as not found if verification fails

        except ValueError:
            print(
                f"    Warning: Could not parse issue number from search output: '{issue_number_str}'.",
                file=sys.stderr,
            )
            return None
    else:
        print("    No existing open issue found with that exact title.")
        return None


# --- FIXED parse_plan_file function ---
def parse_plan_file(filepath: Path) -> List[Dict[str, Any]]:
    """Parses the structured plan file into a list of issue data dictionaries."""
    issues = []
    if not filepath.is_file():
        print(f"Error: Input file '{filepath}' not found.", file=sys.stderr)
        return issues

    try:
        content = filepath.read_text(encoding="utf-8")
        # Split into blocks using ------ as delimiter, handle potential extra newlines
        blocks = re.split(r"\n------\s*\n", content.strip())

        # Compile regex for efficiency
        key_regex = re.compile(r"^\s*([A-Z_]+)\s*:\s*(.*)")  # Allow space before colon

        for i, block in enumerate(blocks):
            block_content = block.strip()
            if not block_content:
                continue

            issue_data: Dict[str, Any] = {}
            current_key: Optional[str] = None
            first_line_value: Optional[str] = None
            continuation_lines: List[str] = []
            processed_content_before_first_key = (
                False  # Flag to warn only once per block
            )

            def save_previous_value():
                """Helper to save the accumulated value for the previous key."""
                nonlocal current_key, first_line_value, continuation_lines, issue_data
                if current_key is None:
                    return

                all_lines = []
                if first_line_value is not None:
                    all_lines.append(first_line_value)
                all_lines.extend(continuation_lines)

                if not all_lines:
                    issue_data[current_key] = ""
                    return

                final_value = ""
                if current_key in ["TITLE", "PARENT_ISSUE"]:
                    final_value = "\n".join(all_lines)
                else:
                    processed_lines = []
                    # Regex to find trailing comments starting with " # "
                    # It captures the content before the comment marker in group 1.
                    comment_regex = re.compile(
                        r"^(.*?)(\s#\s+.*)$"
                    )  # Non-greedy match before " # "

                    for line in all_lines:
                        if re.match(r"^\s*#", line):
                            continue  # Skip full comment lines

                        match = comment_regex.match(line)
                        if match:
                            # Found comment marker, keep group 1 and strip trailing space
                            processed_line = match.group(1).rstrip()
                        else:
                            # No comment marker found, just rstrip the line
                            processed_line = line.rstrip()
                        processed_lines.append(processed_line)

                    final_value = "\n".join(processed_lines).strip()  # Strip block ends

                issue_data[current_key] = final_value

            # --- Start processing lines in block ---
            lines_in_block = block_content.split("\n")
            current_key = None  # Reset state for new block
            first_line_value = None
            continuation_lines = []
            processed_content_before_first_key = False

            for line_num, line in enumerate(lines_in_block):
                match = key_regex.match(line)  # Use compiled regex

                if match:  # Found a new KEY:
                    if current_key is not None:  # Save previous key's data first
                        save_previous_value()
                    # Set state for the newly found key
                    current_key = match.group(1)
                    raw_value = match.group(2)
                    if current_key in ["TITLE", "PARENT_ISSUE"]:
                        first_line_value = raw_value  # Keep raw first line
                    else:
                        first_line_value = (
                            raw_value.rstrip()
                        )  # Strip trailing space for non-raw
                    continuation_lines = []  # Reset continuation lines
                    processed_content_before_first_key = False  # Reset warning flag
                elif (
                    current_key is not None
                ):  # It's a continuation line for the active key
                    continuation_lines.append(line)
                elif (
                    line.strip()
                ):  # Line has content, but no key active and doesn't start a key
                    if not processed_content_before_first_key:
                        print(
                            f"  Warning: Ignoring content before the first KEY: in block {i+1}.",
                            file=sys.stderr,
                        )
                        processed_content_before_first_key = True
            # --- End processing lines in block ---

            # Save the last key's data after the loop finishes
            if current_key is not None:
                save_previous_value()

            # Validate and add the issue if TITLE is present and non-empty
            title = issue_data.get("TITLE")
            if title:
                issues.append(issue_data)
            elif issue_data:  # Only warn if block had *some* data but no title
                print(
                    f"  Warning: Skipping block {i+1} - Missing or empty TITLE field.",
                    file=sys.stderr,
                )

    except Exception as e:
        print(f"Error parsing plan file {filepath}: {e}", file=sys.stderr)
        traceback.print_exc()

    return issues


# --- End of FIXED parse_plan_file function ---


def prepare_issue_body(
    template_dir: Path, issue_type: str, issue_data: Dict[str, str]
) -> str:
    """Loads the appropriate template and fills placeholders."""
    template_file = template_dir / f"{issue_type.lower()}_body.md"
    search_order = [
        template_file,
        template_dir / "test_body.md",
        template_dir / "chore_body.md",
        template_dir / DEFAULT_TEMPLATE_NAME,
    ]
    found_template = None
    for tf in search_order:
        if tf.is_file():
            found_template = tf
            # print(f"    Using template: {found_template.relative_to(BASE_DIR)}") # Keep commented for tests
            break
    if not found_template:
        print(
            f"    Warning: No suitable template found (tried {', '.join(f.name for f in search_order)}). Using generic body.",
            file=sys.stderr,
        )
        generic_body = f"Issue created from script for title: {issue_data.get('TITLE', '[No Title]')}\n\nDetails:\n"
        generic_body += "\n".join(
            f"- {k}: {v}"
            for k, v in issue_data.items()
            if k != "TITLE" and v  # Only include keys with non-empty values
        )
        return generic_body

    try:
        body = found_template.read_text(encoding="utf-8")
        # Substitute provided keys
        for key, value in issue_data.items():
            placeholder = f"__{key}__"
            # Ensure value is a string before substitution
            str_value = str(value) if value is not None else ""
            body = body.replace(placeholder, str_value)

        # Replace any remaining placeholders with a notice
        body = re.sub(r"__([A-Z_]+)__", r"[Placeholder \1 not provided]", body)
        return body
    except Exception as e:
        print(
            f"    Error reading or processing template {found_template}: {e}",
            file=sys.stderr,
        )
        return f"Error processing template. Raw data: {issue_data}"


def create_github_issue(
    issue_data: Dict[str, str],
    issue_body: str,
    cli_args: argparse.Namespace,
    config: Dict[str, Any],
    repo_flags: List[str],
) -> bool:
    """Creates a new GitHub issue using gh CLI."""
    global repo_owner  # Used for project search fallback
    print("  Attempting to create new issue...")
    cmd_create = ["gh", "issue", "create"]
    cmd_create.extend(["-t", issue_data["TITLE"]])
    cmd_create.extend(["-F", "-"])  # Pass body via stdin

    # Assignee
    assignee = issue_data.get("ASSIGNEE", config["default_assignee"])
    if assignee:
        cmd_create.extend(["-a", assignee])

    # Labels
    labels_str = issue_data.get("LABELS", "")
    issue_type = issue_data.get("TYPE", "default").lower()
    labels_to_add = set(
        filter(None, [label.strip() for label in labels_str.split(",")])
    )
    if issue_type != "default":
        labels_to_add.add(issue_type)
    if not labels_to_add and config["default_label"]:
        labels_to_add.add(config["default_label"])

    final_labels = []
    if labels_to_add:
        print("    Checking/creating labels...")
        for label in sorted(list(labels_to_add)):  # Process consistently
            if check_and_create_label(label, repo_flags, config["default_label_color"]):
                final_labels.append(label)
            else:
                print(
                    f"    Warning: Skipping label '{label}' due to creation/check failure.",
                    file=sys.stderr,
                )
    if final_labels:
        # Combine labels into a single -l argument for create
        cmd_create.extend(["-l", ",".join(final_labels)])
        print(f"    Applying labels: {', '.join(final_labels)}")

    # Milestone (use pre-checked/created title from args)
    milestone_title = getattr(cli_args, "global_milestone_title_to_use", None)
    if milestone_title:
        print(f"    Applying milestone: '{milestone_title}'")
        cmd_create.extend(["-m", milestone_title])
    elif (
        cli_args.milestone_title is not None
    ):  # Check if a milestone was mandated but failed pre-check
        print(
            f"    Error: Cannot assign mandatory milestone '{cli_args.milestone_title}' during creation (pre-check failed).",
            file=sys.stderr,
        )
        return False

    # Project
    project_name_or_num = issue_data.get("PROJECT")
    project_id_found = None  # Store ID if found for logging
    if project_name_or_num:
        # Try primary owner first
        project_id_found = find_project_id(
            project_name_or_num, config["project_owner"], repo_flags
        )
        # If not found and primary owner is different from repo owner, try repo owner
        if (
            not project_id_found
            and repo_owner
            and config["project_owner"] != repo_owner
        ):
            print(
                f"    Project not found under '{config['project_owner']}', trying repo owner '{repo_owner}'..."
            )
            project_id_found = find_project_id(
                project_name_or_num, repo_owner, repo_flags
            )

        if project_id_found:
            print(
                f"    Associating with project '{project_name_or_num}' (ID: {project_id_found})."
            )
            # Use project name/number for gh cli, it handles the lookup
            cmd_create.extend(["-p", project_name_or_num])
        else:
            # Construct appropriate error message
            owners_searched = [config["project_owner"]]
            if repo_owner and config["project_owner"] != repo_owner:
                owners_searched.append(repo_owner)
            owner_str = "' or '".join(owners_searched)
            print(
                f"    Error: Project '{project_name_or_num}' not found under owner(s) '{owner_str}'. Cannot create issue.",
                file=sys.stderr,
            )
            return False

    # Repository flags
    cmd_create.extend(repo_flags)

    # Execution or Dry Run
    if cli_args.dry_run:
        print("  [DRY RUN] Would execute:")
        print(f"    echo '<issue_body>' | {' '.join(cmd_create)}")
        return True

    print(f"  Executing: echo '<issue_body>' | {' '.join(cmd_create)}")
    exit_code, stdout, stderr = run_command(
        cmd_create, check=False, capture=True, input_data=issue_body
    )

    if exit_code == 0:
        # stdout usually contains the URL of the created issue
        print(f"  Issue created successfully: {stdout.strip()}")
        return True
    else:
        print(
            f"  Error creating issue (Code: {exit_code}). Stderr: {stderr.strip()}",
            file=sys.stderr,
        )
        # Provide specific feedback if possible
        if "Could not resolve to a ProjectV2" in stderr:
            print(
                "  Hint: Check if the project name/number is correct and accessible.",
                file=sys.stderr,
            )
        elif "Could not resolve to a Milestone" in stderr:
            print("  Hint: Check if the milestone title is correct.", file=sys.stderr)
        elif "Invalid input" in stderr:
            print(
                "  Hint: Check assignee format (@username) or label characters.",
                file=sys.stderr,
            )
        return False


def edit_github_issue(
    issue_number: int,
    issue_data: Dict[str, str],
    issue_body: str,
    cli_args: argparse.Namespace,
    config: Dict[str, Any],
    repo_flags: List[str],
) -> bool:
    """Edits an existing GitHub issue using gh CLI."""
    print(f"  Attempting to edit existing issue #{issue_number}...")
    cmd_edit = ["gh", "issue", "edit", str(issue_number)]

    # Body update always happens via stdin
    cmd_edit.extend(["--body-file", "-"])

    # Assignee: Use --add-assignee to avoid removing existing ones unintentionally
    assignee = issue_data.get("ASSIGNEE", config["default_assignee"])
    if assignee:
        cmd_edit.extend(["--add-assignee", assignee])  # Adds if not already assigned

    # Labels: Use --add-label for specified labels
    labels_str = issue_data.get("LABELS", "")
    issue_type = issue_data.get("TYPE", "default").lower()
    labels_to_add = set(
        filter(None, [label.strip() for label in labels_str.split(",")])
    )
    if issue_type != "default":
        labels_to_add.add(issue_type)

    added_labels_count = 0
    if labels_to_add:
        print("    Checking/creating labels for edit...")
        for label in sorted(list(labels_to_add)):
            if check_and_create_label(label, repo_flags, config["default_label_color"]):
                cmd_edit.extend(["--add-label", label])  # Adds if not already present
                added_labels_count += 1
            else:
                print(
                    f"    Warning: Skipping adding label '{label}' during edit due to creation/check failure.",
                    file=sys.stderr,
                )
    if added_labels_count > 0:
        print(f"    Will attempt to add {added_labels_count} label(s).")

    # Milestone (use pre-checked/created title from args)
    milestone_title = getattr(cli_args, "global_milestone_title_to_use", None)
    if milestone_title:
        print(f"    Applying milestone: '{milestone_title}'")
        cmd_edit.extend(["-m", milestone_title])  # Sets the milestone
    elif (
        cli_args.milestone_title is not None
    ):  # Check if a milestone was mandated but failed pre-check
        print(
            f"    Error: Cannot assign mandatory milestone '{cli_args.milestone_title}' during edit (pre-check failed).",
            file=sys.stderr,
        )
        return False

    # Project association is NOT handled by `gh issue edit`.
    # Requires `gh project item-add` which needs the project ID and issue ID (not number).
    # This is complex; inform the user instead.
    if issue_data.get("PROJECT"):
        print(
            f"    Info: Project association ('{issue_data['PROJECT']}') is ignored during edit. Use `gh project item-add` manually if needed."
        )

    # Repository flags
    cmd_edit.extend(repo_flags)

    # Execution or Dry Run
    if cli_args.dry_run:
        print("  [DRY RUN] Would execute:")
        print(f"    echo '<issue_body>' | {' '.join(cmd_edit)}")
        return True

    print(f"  Executing: echo '<issue_body>' | {' '.join(cmd_edit)}")
    exit_code, stdout, stderr = run_command(
        cmd_edit, check=False, capture=True, input_data=issue_body
    )

    if exit_code == 0:
        # Edit command usually doesn't output much on success
        print(f"  Issue #{issue_number} edited successfully.")
        return True
    else:
        print(
            f"  Error editing issue #{issue_number} (Code: {exit_code}). Stderr: {stderr.strip()}",
            file=sys.stderr,
        )
        # Provide hints if possible
        if "Could not resolve to a Milestone" in stderr:
            print(
                "  Hint: Check if the milestone title exists in the repository.",
                file=sys.stderr,
            )
        elif "Could not resolve label" in stderr:
            print(
                "  Hint: Label check/creation might have failed silently before edit attempt.",
                file=sys.stderr,
            )
        elif "Could not resolve user" in stderr:
            print(
                "  Hint: Check assignee username format (@username).", file=sys.stderr
            )
        return False


# --- Função main ---
def main(args: argparse.Namespace, config: Dict[str, Any]) -> int:
    """Main logic of the script."""
    global repo_owner
    # Ensure BASE_DIR is set correctly based on args if provided (e.g. from tests)
    global BASE_DIR
    if hasattr(args, "base_dir"):
        BASE_DIR = args.base_dir
        print(f"Using Base Directory: {BASE_DIR}")

    input_file_path = Path(args.input_file)
    # Resolve template dir relative to potentially overridden BASE_DIR
    template_dir_path = BASE_DIR / "templates/issue_bodies"

    if not input_file_path.is_file():
        # Try resolving relative to BASE_DIR if it's not absolute
        if not input_file_path.is_absolute():
            input_file_path = BASE_DIR / args.input_file  # Use original arg if relative
        if not input_file_path.is_file():
            # Use the string representation that was resolved/passed in args for error
            print(
                f"Error: Input file '{args.input_file}' not found (checked absolute and relative to {BASE_DIR}).",
                file=sys.stderr,
            )
            return 1

    if not template_dir_path.is_dir():
        print(
            f"Error: Template directory '{template_dir_path}' not found.",
            file=sys.stderr,
        )
        return 1

    # Determine Repository and Owner
    repo_flags = []
    if config["repo_target"]:
        repo_flags.extend(["-R", config["repo_target"]])
        print(f"Targeting repository: {config['repo_target']}")
        try:
            if "/" not in config["repo_target"]:
                raise ValueError("Invalid format")
            repo_owner = config["repo_target"].split("/")[0]
        except Exception:
            print(
                f"Error: Could not determine owner from repo target '{config['repo_target']}'. Expected format 'owner/repo'.",
                file=sys.stderr,
            )
            return 1
    else:
        print("Using current repository (determining owner...).")
        # Use --jq with error handling
        exit_code, stdout, stderr = run_command(
            ["gh", "repo", "view", "--json", "owner", "--jq", ".owner.login"],
            check=False,
            capture=True,  # Capture stderr
        )
        if exit_code != 0 or not stdout.strip():
            print(
                f"Error: Failed to determine owner of current repository. Is this a valid git repo with a GitHub remote? Stderr: {stderr.strip()}",
                file=sys.stderr,
            )
            return 1
        repo_owner = stdout.strip()
    print(f"Determined repository owner: {repo_owner}")

    # --- Pre-check/Create Milestone specified via CLI ---
    args.global_milestone_title_to_use = None
    if args.milestone_title:
        # Pass description only if provided, otherwise pass None
        milestone_desc = (
            args.milestone_desc if args.milestone_desc is not None else None
        )
        verified_milestone_title = check_and_create_milestone(
            args.milestone_title, milestone_desc, repo_flags
        )
        if verified_milestone_title:
            args.global_milestone_title_to_use = verified_milestone_title
            print(
                f"Successfully verified/created milestone: '{args.global_milestone_title_to_use}'"
            )
        else:
            # If milestone was required but failed, abort early.
            print(
                f"Error: Failed to find or create the mandatory milestone '{args.milestone_title}'. Aborting.",
                file=sys.stderr,
            )
            return 1
    # --- End Milestone Pre-check ---

    # --- Parse Plan File ---
    parsed_issues = parse_plan_file(input_file_path)  # Chama a função corrigida
    if not parsed_issues:
        print("No issues found or parsed from the plan file.")
        return 0  # Not an error if the file was empty or only contained invalid blocks
    # --- End Parse Plan File ---

    total_issues = len(parsed_issues)
    processed_count = 0
    created_count = 0
    edited_count = 0
    error_count = 0
    skipped_count = 0  # For issues skipped due to missing title etc. before API calls

    print(
        f"\nStarting GitHub Issue processing for {total_issues} valid blocks found..."
    )
    for i, issue_data in enumerate(parsed_issues):
        print("-" * 40)
        title = issue_data.get("TITLE")
        if not title:  # Should have been caught by parser, but double-check
            print(f"Skipping block {i+1}: TITLE is missing or empty.", file=sys.stderr)
            skipped_count += 1
            continue

        print(f"Processing Issue {i+1}/{total_issues}: '{title}'")

        # Prepare Body
        issue_type = issue_data.get("TYPE", "default")
        # Add checked milestone to data for potential use in templates
        issue_data["APPLIED_MILESTONE"] = args.global_milestone_title_to_use or ""
        issue_body = prepare_issue_body(template_dir_path, issue_type, issue_data)

        # Check for Existing Issue
        existing_issue_num = find_existing_issue(title, repo_flags)

        # Create or Edit
        success = False
        action_taken = "None"
        if existing_issue_num:
            action_taken = "Edit"
            success = edit_github_issue(
                existing_issue_num, issue_data, issue_body, args, config, repo_flags
            )
            if success and not args.dry_run:
                edited_count += 1
        else:
            action_taken = "Create"
            success = create_github_issue(
                issue_data, issue_body, args, config, repo_flags
            )
            if success and not args.dry_run:
                created_count += 1

        # Update Counts
        if success:
            processed_count += 1
            print(f"Action '{action_taken}' succeeded for '{title}'.")
        else:
            error_count += 1
            print(f"Action '{action_taken}' failed for '{title}'.", file=sys.stderr)

        # Optional delay between API calls
        if not args.dry_run and total_issues > 1 and i < total_issues - 1:
            time.sleep(1)  # 1 second delay

    # --- Summary ---
    print("-" * 40)
    print("GitHub Issue processing finished.")
    summary_parts = [f"Total blocks found: {total_issues}"]
    if skipped_count > 0:
        summary_parts.append(f"Skipped (no title): {skipped_count}")
    summary_parts.append(f"Processed: {processed_count}")
    if not args.dry_run:
        summary_parts.append(f"Created: {created_count}")
        summary_parts.append(f"Edited: {edited_count}")
    summary_parts.append(f"Errors: {error_count}")
    if args.dry_run:
        summary_parts.append("(Dry Run Mode)")

    print(f"Summary: {', '.join(summary_parts)}.")
    # Return error code if any errors occurred during processing
    return 0 if error_count == 0 else 1


# --- End main ---


# --- Função parse_arguments ---
def parse_arguments() -> argparse.Namespace:
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Create or edit GitHub Issues from a structured plan file.",
        epilog=f"""Examples:
  # Process default file ({DEFAULT_INPUT_FILE.name}) in current repo
  python scripts/create_issue.py

  # Process a specific plan file
  python scripts/create_issue.py planos/meu_plano.txt

  # Process default file and assign to a milestone (creates if needed with desc)
  python scripts/create_issue.py --milestone-title "Sprint 5" --milestone-desc "Tasks for Sprint 5"

  # Process specific file for a different repo
  python scripts/create_issue.py --repo another-owner/another-repo planos/outro_plano.txt

  # Dry run: Show what would happen without making changes
  python scripts/create_issue.py --dry-run planos/meu_plano.txt
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "input_file",
        nargs="?",
        default=str(
            DEFAULT_INPUT_FILE.relative_to(BASE_DIR)
        ),  # Show relative path in help
        help=f"Path to the structured plan file (default: relative path '{DEFAULT_INPUT_FILE.relative_to(BASE_DIR)}'). Can be absolute.",
    )
    parser.add_argument(
        "--milestone-title",
        help="Title of the milestone to assign issues to. If it doesn't exist, it will be created if --milestone-desc is also provided (use empty string for no description: --milestone-desc '').",
    )
    parser.add_argument(
        "--milestone-desc",
        help="Description for the milestone if it needs to be created. Required for creation unless milestone already exists.",
    )
    parser.add_argument(
        "-R",
        "--repo",
        metavar="OWNER/REPO",
        help=f"Target repository (e.g., 'myorg/myproject'). Overrides GH_REPO_TARGET env var. If omitted, uses the repository in the current directory.",
    )
    parser.add_argument(
        "--default-assignee",
        help=f"Default assignee if not specified in the plan file (default: {DEFAULT_ASSIGNEE}, can be set via DEFAULT_ASSIGNEE env var). Use '@me' for yourself.",
    )
    parser.add_argument(
        "--default-label",
        help=f"Default label if no labels are specified in the plan file or by TYPE (default: {DEFAULT_LABEL}, can be set via DEFAULT_LABEL env var).",
    )
    parser.add_argument(
        "--default-color",
        help=f"Default color (hex, no #) for newly created labels (default: {DEFAULT_LABEL_COLOR}, can be set via DEFAULT_LABEL_COLOR env var).",
    )
    parser.add_argument(
        "--project-owner",
        help=f"Owner (@me or org/user name) to search for projects first (default: {PROJECT_PRIMARY_OWNER}, can be set via GH_PROJECT_OWNER env var). Will also search under repo owner if different.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the process: parse file, check existence, show commands, but do not create/edit issues on GitHub.",
    )
    # Add hidden args for testing if needed, e.g., base_dir
    parser.add_argument(
        "--base-dir",
        help=argparse.SUPPRESS,  # Hidden arg for tests to override BASE_DIR
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help=argparse.SUPPRESS,  # Keep hidden live flag if used by tests
    )

    # Perform initial parsing
    args = parser.parse_args()

    # Post-process args: Resolve input_file path based on BASE_DIR
    # This makes `main` always receive a potentially resolved Path object
    input_path = Path(args.input_file)
    # If base_dir is explicitly passed (tests), use it, otherwise use script's BASE_DIR
    base_dir_context = Path(args.base_dir) if args.base_dir else BASE_DIR
    # Resolve the input path relative to the context BASE_DIR if it's not absolute
    if not input_path.is_absolute():
        resolved_path = (base_dir_context / input_path).resolve()
    else:
        resolved_path = input_path  # Already absolute

    args.input_file = str(resolved_path)  # Store resolved path as string
    print(f"Using resolved input file path: {args.input_file}")

    # Set base_dir on args namespace if it wasn't explicitly passed, useful for load_env_vars
    if not args.base_dir:
        args.base_dir = base_dir_context  # Use the same context dir

    return args


# --- Ponto de Entrada ---
if __name__ == "__main__":
    if not command_exists("gh"):
        suggest_install("gh", "gh")  # Suggest package name 'gh' explicitly
        sys.exit(1)
    if not command_exists("jq"):
        # jq is now optional, only used fallback project search and label check
        suggest_install("jq", "jq")
        print(
            "Warning: 'jq' command not found. Some operations like project finding might rely on 'gh' built-in JSON/jq capabilities.",
            file=sys.stderr,
        )  # Less critical now

    parsed_args = parse_arguments()
    loaded_config = load_env_vars(parsed_args)  # Load .env and merge with defaults/args

    # Add the config dictionary to args namespace for easier access in functions
    for key, value in loaded_config.items():
        # Only set if not already set by a direct CLI argument
        if getattr(parsed_args, key, None) is None:
            setattr(parsed_args, key, value)

    exit_code = main(parsed_args, loaded_config)
    sys.exit(exit_code)
