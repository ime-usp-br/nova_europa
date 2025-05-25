# -*- coding: utf-8 -*-
"""
Unit and Integration tests for the create_issue.py script.

Unit tests focus on parsing and templating (AC2).
Integration tests focus on interaction with the `gh` CLI (AC3+).
"""

import pytest
from pathlib import Path
import sys
import subprocess
from unittest import mock # Import mock
from typing import List, Dict, Any, Tuple, Optional
import json
import time

# Add script directory to sys.path to allow importing
# Assuming tests are run from the project root (e.g., using `python -m pytest`)
SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR.parent))

# Dynamically import the script to test
import importlib
create_issue_module = importlib.import_module("scripts.create_issue")

# Functions/Classes to test from the imported module
parse_plan_file = create_issue_module.parse_plan_file
prepare_issue_body = create_issue_module.prepare_issue_body
# Explicitamente importar/atribuir run_command para o escopo do módulo de teste
run_command = create_issue_module.run_command
find_existing_issue = create_issue_module.find_existing_issue
create_github_issue = create_issue_module.create_github_issue
edit_github_issue = create_issue_module.edit_github_issue
check_and_create_label = create_issue_module.check_and_create_label
check_and_create_milestone = create_issue_module.check_and_create_milestone
find_project_id = create_issue_module.find_project_id
main = create_issue_module.main
parse_arguments = create_issue_module.parse_arguments
# Mock the constants if necessary, e.g., BASE_DIR if not handled by fixtures
create_issue_module.BASE_DIR = SCRIPT_DIR.parent


# --- Helper Function ---
def _create_dummy_plan_file(path: Path, content: str):
    """Helper to create a plan file with given content."""
    path.write_text(content, encoding="utf-8")

# --- Fixtures ---

@pytest.fixture
def temp_plan_file(tmp_path: Path) -> Path:
    """Creates a temporary plan file path."""
    return tmp_path / "test_plan.txt"

@pytest.fixture
def temp_template_dir(tmp_path: Path) -> Path:
    """Creates a temporary directory for issue body templates."""
    template_dir = tmp_path / "templates" / "issue_bodies" # Match script structure
    template_dir.mkdir(parents=True)

    # Create default template for prepare_issue_body tests and generic fallback
    (template_dir / "default_body.md").write_text(
        "## Default Issue\n**Title:** __TITLE__\n**Info:** __INFO__",
        encoding="utf-8"
    )
    return template_dir

@pytest.fixture
def default_args(temp_plan_file: Path, temp_template_dir: Path):
    """Provides default parsed arguments for testing main logic."""
    # Use absolute path for input file in args
    input_file_abs = str(temp_plan_file.resolve())

    # Mock sys.argv for parse_arguments
    with mock.patch('sys.argv', ['scripts/create_issue.py', input_file_abs]):
        args = parse_arguments()
    # Add default values that might be loaded from config/env
    args.repo = None # Let repo_flags handle this
    args.project_owner = create_issue_module.PROJECT_PRIMARY_OWNER
    args.default_assignee = create_issue_module.DEFAULT_ASSIGNEE
    args.default_label = create_issue_module.DEFAULT_LABEL
    args.default_color = create_issue_module.DEFAULT_LABEL_COLOR
    args.dry_run = False # Default is not dry run
    args.milestone_title = None
    args.milestone_desc = None
    args.global_milestone_title_to_use = None # Initialize this
    # Set base_dir used by the script logic (needed for template path resolution)
    args.base_dir = SCRIPT_DIR.parent
    create_issue_module.BASE_DIR = SCRIPT_DIR.parent # Ensure module uses correct base

    # Reset global caches before each test using this fixture
    create_issue_module.checked_labels.clear()
    create_issue_module.checked_milestones.clear()
    create_issue_module.repo_owner = None # Reset repo owner determination

    return args

@pytest.fixture
def default_config():
    """Provides a default config dictionary (as loaded from load_env_vars)."""
    return {
        "repo_target": create_issue_module.REPO_TARGET, # Default empty
        "project_owner": create_issue_module.PROJECT_PRIMARY_OWNER,
        "default_assignee": create_issue_module.DEFAULT_ASSIGNEE,
        "default_label": create_issue_module.DEFAULT_LABEL,
        "default_label_color": create_issue_module.DEFAULT_LABEL_COLOR,
    }

# --- Mocks ---

@pytest.fixture
def mock_run_command():
    """ Mocks the run_command function in the create_issue module.

    Returns a mock object that can be configured to simulate different
    gh command outcomes. Use side_effect for dynamic responses.
    """
    with mock.patch('scripts.create_issue.run_command') as mock_run:
        # Default behavior: success (exit code 0), empty stdout/stderr
        mock_run.return_value = (0, "", "")
        yield mock_run


# ==============================================================
# == Unit Tests (AC2: Parsing and Templating - Already Done) ==
# ==============================================================
# These tests focus on parse_plan_file and prepare_issue_body logic.
# They were implemented in a previous step (commit d904b45).
# Keep them here for completeness and regression testing.

# --- Tests for parse_plan_file ---

def test_parse_single_block_simple(temp_plan_file: Path):
    """Test parsing a single block with basic KEY: VALUE pairs."""
    content = """
TITLE: Test Issue Title
TYPE: feature
ASSIGNEE: @me
LABELS: bug, ui
DESCRIPTION: This is a test description.
"""
    _create_dummy_plan_file(temp_plan_file, content)
    result = parse_plan_file(temp_plan_file)
    assert len(result) == 1
    assert result[0] == {
        "TITLE": "Test Issue Title",
        "TYPE": "feature",
        "ASSIGNEE": "@me",
        "LABELS": "bug, ui",
        "DESCRIPTION": "This is a test description.",
    }

def test_parse_multiple_blocks(temp_plan_file: Path):
    """Test parsing multiple blocks separated by ------."""
    content = """
TITLE: Issue 1
TYPE: bug
DESCRIPTION: First bug description.
------
TITLE: Issue 2
TYPE: feature
PROJECT: MyProject
DESCRIPTION: Second feature description.
"""
    _create_dummy_plan_file(temp_plan_file, content)
    result = parse_plan_file(temp_plan_file)
    assert len(result) == 2
    assert result[0]["TITLE"] == "Issue 1"
    assert result[0]["TYPE"] == "bug"
    assert result[1]["TITLE"] == "Issue 2"
    assert result[1]["PROJECT"] == "MyProject"

def test_parse_multiline_value_with_comment_stripping(temp_plan_file: Path):
    """Test parsing multiline values with comment removal."""
    content = """
TITLE: Multiline Test
DESCRIPTION: Line 1 of description.
  Line 2 indented. # This comment should be removed
# This whole line is a comment
Still part of description.
    Another indented line. # Another comment
"""
    _create_dummy_plan_file(temp_plan_file, content)
    result = parse_plan_file(temp_plan_file)
    assert len(result) == 1
    expected_description = (
        "Line 1 of description.\n"
        "  Line 2 indented.\n" # Comment " # ..." removed
        "Still part of description.\n" # Full comment line removed
        "    Another indented line." # Comment " # ..." removed
    )
    # Debugging output
    # print(f"Expected:\n'''{expected_description}'''")
    # print(f"Actual:\n'''{result[0]['DESCRIPTION']}'''")
    assert result[0]["DESCRIPTION"] == expected_description

def test_parse_multiline_title_keeps_comments(temp_plan_file: Path):
    """Test that TITLE and PARENT_ISSUE keep their content raw, including comments."""
    content = """
TITLE: This Title # Has a Comment
TYPE: chore
PARENT_ISSUE: #123 - Parent Issue Title # Another Comment
DESCRIPTION: Some description # This comment goes
    More description # This one too
"""
    _create_dummy_plan_file(temp_plan_file, content)
    result = parse_plan_file(temp_plan_file)
    assert len(result) == 1
    assert result[0]["TITLE"] == "This Title # Has a Comment" # Kept raw
    assert result[0]["PARENT_ISSUE"] == "#123 - Parent Issue Title # Another Comment" # Kept raw
    expected_description = "Some description\n    More description" # Comments " # ..." removed
    assert result[0]["DESCRIPTION"] == expected_description

def test_parse_block_missing_title(temp_plan_file: Path, capsys):
    """Test that blocks without a TITLE are skipped with a warning."""
    content = """
TYPE: bug
DESCRIPTION: This issue has no title.
------
TITLE: Valid Issue
DESCRIPTION: This one is fine.
"""
    _create_dummy_plan_file(temp_plan_file, content)
    result = parse_plan_file(temp_plan_file)
    assert len(result) == 1
    assert result[0]["TITLE"] == "Valid Issue"
    captured = capsys.readouterr()
    assert "Warning: Skipping block 1 - Missing or empty TITLE field." in captured.err

def test_parse_empty_file(temp_plan_file: Path):
    """Test parsing an empty file."""
    content = ""
    _create_dummy_plan_file(temp_plan_file, content)
    result = parse_plan_file(temp_plan_file)
    assert len(result) == 0

def test_parse_file_not_found(capsys):
    """Test parsing a non-existent file."""
    non_existent_path = Path("non_existent_plan.txt")
    result = parse_plan_file(non_existent_path)
    assert len(result) == 0
    captured = capsys.readouterr()
    assert f"Error: Input file '{non_existent_path}' not found." in captured.err

def test_parse_handles_extra_whitespace(temp_plan_file: Path):
    """Test parsing handles extra whitespace around keys, values, and separators."""
    content = """
TITLE  :  Spaced out title
  TYPE :   feature
DESCRIPTION:
    Line 1.

  Line 2.


------


  TITLE: Issue 2
DESCRIPTION: Desc 2.

"""
    _create_dummy_plan_file(temp_plan_file, content)
    result = parse_plan_file(temp_plan_file)
    assert len(result) == 2
    assert result[0]["TITLE"] == "Spaced out title"
    assert result[0]["TYPE"] == "feature"
    assert result[0]["DESCRIPTION"] == "Line 1.\n\n  Line 2."
    assert result[1]["TITLE"] == "Issue 2"


# --- Tests for prepare_issue_body ---

@pytest.fixture
def setup_templates(temp_template_dir: Path):
    """Creates dummy template files for prepare_issue_body tests."""
    (temp_template_dir / "feature_body.md").write_text(
        "## Feature Request\n**Goal:** __GOAL__\n**Details:** __DESCRIPTION__",
        encoding="utf-8"
    )
    (temp_template_dir / "bug_body.md").write_text(
        "## Bug Report\n**Problem:** __PROBLEM__\n**Steps:** __STEPS__\n**Parent:** __PARENT_ISSUE__",
        encoding="utf-8"
    )
    # Default already created by temp_template_dir fixture
    (temp_template_dir / "test_body.md").write_text(
        "## Test Task\n**Motivation:** __TEST_MOTIVATION__",
        encoding="utf-8"
    )
    (temp_template_dir / "chore_body.md").write_text(
        "## Chore Task\n**Task:** __TASK_DETAIL__",
        encoding="utf-8"
    )
    return temp_template_dir


def test_prepare_body_feature_template(setup_templates: Path):
    """Test preparing body using the feature template."""
    issue_data = {
        "TITLE": "New Feature",
        "TYPE": "feature",
        "GOAL": "Improve user experience",
        "DESCRIPTION": "Add a cool new button.",
    }
    body = prepare_issue_body(setup_templates, "feature", issue_data)
    assert "## Feature Request" in body
    assert "**Goal:** Improve user experience" in body
    assert "**Details:** Add a cool new button." in body

def test_prepare_body_bug_template(setup_templates: Path):
    """Test preparing body using the bug template."""
    issue_data = {
        "TITLE": "Button Error",
        "TYPE": "bug",
        "PROBLEM": "Button explodes on click.",
        "STEPS": "1. Click button\n2. See explosion",
        "PARENT_ISSUE": "#123",
    }
    body = prepare_issue_body(setup_templates, "bug", issue_data)
    assert "## Bug Report" in body
    assert "**Problem:** Button explodes on click." in body
    assert "**Steps:** 1. Click button\n2. See explosion" in body
    assert "**Parent:** #123" in body

def test_prepare_body_missing_placeholders(setup_templates: Path):
    """Test that missing placeholders are marked."""
    issue_data = {
        "TITLE": "Incomplete Feature",
        "TYPE": "feature",
        # GOAL is missing
        "DESCRIPTION": "Only description provided.",
    }
    body = prepare_issue_body(setup_templates, "feature", issue_data)
    assert "## Feature Request" in body
    assert "**Goal:** [Placeholder GOAL not provided]" in body
    assert "**Details:** Only description provided." in body

def test_prepare_body_unknown_type_uses_fallback(setup_templates: Path):
    """Test fallback order: unknown -> test -> chore -> default."""
    issue_data = {"TITLE": "Unknown Type", "TYPE": "unknown", "INFO": "Some info"}

    # 1. Should try unknown_body.md (doesn't exist) -> test_body.md
    body = prepare_issue_body(setup_templates, "unknown", issue_data)
    assert "## Test Task" in body # Falls back to test
    assert "**Motivation:** [Placeholder TEST_MOTIVATION not provided]" in body

    # Remove test_body.md, should now fall back to chore_body.md
    (setup_templates / "test_body.md").unlink()
    body = prepare_issue_body(setup_templates, "unknown", issue_data)
    assert "## Chore Task" in body # Falls back to chore
    assert "**Task:** [Placeholder TASK_DETAIL not provided]" in body

    # Remove chore_body.md, should now fall back to default_body.md
    (setup_templates / "chore_body.md").unlink()
    body = prepare_issue_body(setup_templates, "unknown", issue_data)
    assert "## Default Issue" in body # Falls back to default
    assert "**Title:** Unknown Type" in body
    assert "**Info:** Some info" in body

def test_prepare_body_no_templates_uses_generic(tmp_path: Path, capsys):
    """Test generic body generation when no templates exist."""
    empty_template_dir = tmp_path / "empty_templates" / "issue_bodies" # Match structure
    empty_template_dir.mkdir(parents=True)
    issue_data = {
        "TITLE": "Generic Issue",
        "TYPE": "feature",
        "DETAIL": "Some detail here",
        "EXTRA": "More data",
    }
    body = prepare_issue_body(empty_template_dir, "feature", issue_data)
    assert "Issue created from script for title: Generic Issue" in body
    assert "Details:" in body
    assert "- TYPE: feature" in body
    assert "- DETAIL: Some detail here" in body
    assert "- EXTRA: More data" in body
    assert "TITLE" not in body.split("Details:")[1]

    captured = capsys.readouterr()
    assert "Warning: No suitable template found" in captured.err

def test_prepare_body_handles_none_values(setup_templates: Path):
    """Test that None values in issue_data are handled gracefully."""
    issue_data = {
        "TITLE": "Feature with None Goal",
        "TYPE": "feature",
        "GOAL": None, # Explicit None
        "DESCRIPTION": "Description exists.",
    }
    body = prepare_issue_body(setup_templates, "feature", issue_data)
    assert "## Feature Request" in body
    assert "**Goal:** " in body # Placeholder replaced with empty string
    assert "**Details:** Description exists." in body

# =============================================
# == Integration Tests (AC3+) ==
# =============================================
# These tests mock or run gh CLI interactions.

@pytest.mark.integration # Mark as integration tests
class TestGitHubInteraction:

    # --- AC3: Basic Interaction Coverage (Finding, Creating, Editing) ---

    # tests/python/test_create_issue.py -> test_ac3_find_existing_issue_mocked_found

    @mock.patch('scripts.create_issue.run_command')
    def test_ac3_find_existing_issue_mocked_found(self, mock_run_cmd):
        """AC3: Test finding an existing issue (mocked - found)."""
        test_title = "Existing Test Issue"
        mock_repo_flags = ["-R", "mock/repo"]
        issue_number = 123

        # Mock gh search issues response (finding the issue)
        # search_output = json.dumps([{"number": issue_number, "title": test_title, "state": "OPEN", "updatedAt": "..."}]) # We don't need the full json anymore for the search mock
        # Mock gh issue view response (confirming the title)
        view_output = json.dumps({"title": test_title})

        # Configure side_effect based on command args
        def side_effect(*args, **kwargs):
            cmd_list = args[0]
            # Check more specifically for the search command with the jq filter
            if "search" in cmd_list and "issues" in cmd_list and "--jq" in cmd_list and ".[0].number // empty" in cmd_list:
                # CORRECT: Return *only* the issue number as a string, simulating the jq filter
                return (0, str(issue_number), "")
            elif "issue" in cmd_list and "view" in cmd_list and str(issue_number) in cmd_list:
                 # Ensure the view command mock is also specific enough if needed
                return (0, view_output, "") # Success for view
            # Add a print for unexpected calls to aid debugging
            print(f"Warning: Unexpected command mocked in test_ac3_find_existing_issue_mocked_found: {' '.join(cmd_list)}", file=sys.stderr)
            return (1, "", f"Unexpected command in mock: {' '.join(cmd_list)}") # Default failure

        mock_run_cmd.side_effect = side_effect

        found_num = find_existing_issue(test_title, mock_repo_flags)

        assert found_num == issue_number # Should now pass
        # Verify search command was called (checking the specific call args is good practice)
        # Note: the mock.call object might be complex due to the list structure.
        # We already verified the side_effect logic handles the expected command.

        # Verify view command was called (assert_has_calls is robust)
        view_call = mock.call(
             ['gh', 'issue', 'view', str(issue_number), '-R', 'mock/repo', '--json', 'title'],
             check=False, capture=True
        )
        # Combine the expected calls if needed
        # search_call = mock.call(...) # Construct the expected search call if you want to assert it too
        # mock_run_cmd.assert_has_calls([search_call, view_call], any_order=False)

        # Check that the view command was actually called
        assert any(
            "view" in call.args[0] and str(issue_number) in call.args[0]
            for call in mock_run_cmd.call_args_list
        ), f"Expected 'gh issue view {issue_number}' to be called"

    @mock.patch('scripts.create_issue.check_and_create_label', return_value=True) # Assume label check/create succeeds
    @mock.patch('scripts.create_issue.run_command')
    def test_ac3_edit_issue_mocked(self, mock_run_cmd, mock_label_check, default_args, default_config):
        """AC3: Test editing an existing issue (mocked)."""
        issue_number = 123
        issue_data = {"TITLE": "Existing Issue to Edit", "TYPE": "feature", "LABELS": "ui", "ASSIGNEE": "dev1"}
        issue_body = "Updated Body"
        mock_repo_flags = ["-R", "mock/repo"] # Assume repo flags determined

        # Mock the 'gh issue edit' call to succeed
        mock_run_cmd.return_value = (0, "", "") # Success for edit command

        success = edit_github_issue(issue_number, issue_data, issue_body, default_args, default_config, mock_repo_flags)

        assert success is True
        mock_run_cmd.assert_called_once()
        args, kwargs = mock_run_cmd.call_args
        assert args[0][0:3] == ['gh', 'issue', 'edit']
        assert str(issue_number) in args[0]
        assert "--body-file" in args[0]
        assert "-" in args[0] # Body from stdin
        assert "--add-label" in args[0]
        assert "feature" in args[0] # TYPE becomes a label
        assert "ui" in args[0]      # Specific label
        assert "--add-assignee" in args[0]
        assert issue_data["ASSIGNEE"] in args[0]
        assert kwargs.get('input_data') == issue_body

    # --- AC3 + AC4: Live Interaction Tests ---
    # These tests require the --live flag and GH_TEST_REPO env var

    @pytest.mark.live # Mark as live test
    def test_ac3_ac4_live_create_find_edit(self, live_run, test_repo, repo_flags, default_args, default_config, temp_plan_file, temp_template_dir):
        """AC3+AC4: Live test: Create, find, then edit an issue."""
        if not live_run: pytest.skip("Requires --live flag")

        issue_title = f"Live Test Issue - {int(time.time())}" # Unique title
        issue_type_create = "bug"
        labels_create = "live-test,initial"
        desc_create = "Initial description for live test."
        issue_data_create = {
            "TITLE": issue_title,
            "TYPE": issue_type_create,
            "LABELS": labels_create,
            "DESCRIPTION": desc_create,
            "ASSIGNEE": default_config["default_assignee"], # Use default assignee
        }
        # Create a simple plan file for create
        plan_content_create = f"TITLE: {issue_title}\nTYPE: {issue_type_create}\nLABELS: {labels_create}\nDESCRIPTION: {desc_create}\nASSIGNEE: {default_config['default_assignee']}"
        _create_dummy_plan_file(temp_plan_file, plan_content_create)

        # Prepare body (using default template)
        issue_body_create = prepare_issue_body(temp_template_dir, issue_type_create, issue_data_create)

        # 1. Create the issue (live)
        print(f"\n[Live Test] Creating issue '{issue_title}' in {test_repo}...")
        create_success = create_github_issue(issue_data_create, issue_body_create, default_args, default_config, repo_flags)
        assert create_success is True, "Live creation failed"

        # Give GitHub API a moment
        time.sleep(3)

        # 2. Find the issue (live)
        print(f"[Live Test] Finding issue '{issue_title}'...")
        found_issue_num = find_existing_issue(issue_title, repo_flags)
        assert found_issue_num is not None, f"Could not find live created issue '{issue_title}'"

        # 3. Edit the issue (live)
        print(f"[Live Test] Editing issue #{found_issue_num}...")
        issue_type_edit = "feature" # Change type
        labels_edit = "updated,live-test" # Change labels (keep live-test)
        desc_edit = "Updated description."
        assignee_edit = "ayrtonnotrya" # Change assignee (replace with a valid user if needed)
        issue_data_edit = {
            "TITLE": issue_title, # Keep same title
            "TYPE": issue_type_edit,
            "LABELS": labels_edit,
            "DESCRIPTION": desc_edit,
            "ASSIGNEE": assignee_edit,
        }
        # Create plan for edit
        plan_content_edit = f"TITLE: {issue_title}\nTYPE: {issue_type_edit}\nLABELS: {labels_edit}\nDESCRIPTION: {desc_edit}\nASSIGNEE: {assignee_edit}"
        # NOTE: Technically we don't need the plan file for the edit function call,
        # but prepare_issue_body needs the data.
        issue_body_edit = prepare_issue_body(temp_template_dir, issue_type_edit, issue_data_edit)

        edit_success = edit_github_issue(found_issue_num, issue_data_edit, issue_body_edit, default_args, default_config, repo_flags)
        assert edit_success is True, f"Live editing of issue #{found_issue_num} failed"

        # 4. (Optional) Verify changes via gh issue view (outside script's scope, but good for manual check)
        print(f"[Live Test] Issue created/found/edited: #{found_issue_num}. Verify manually if needed.")
        # Example manual check: gh issue view <number> -R <test_repo> --json title,body,labels,assignees


    @pytest.mark.live # Mark as live test
    def test_ac3_ac4_live_check_create_label(self, live_run, test_repo, repo_flags, default_config):
        """AC3+AC4: Live test: Check and create a label."""
        if not live_run: pytest.skip("Requires --live flag")

        label_name = f"live-label-{int(time.time())}"
        label_color = "f0f0f0"

        # Reset cache for this test
        create_issue_module.checked_labels.clear()

        # 1. Check/Create label (should create)
        print(f"\n[Live Test] Checking/Creating label '{label_name}' in {test_repo}...")
        created = check_and_create_label(label_name, repo_flags, label_color)
        assert created is True, f"Failed to create label '{label_name}'"

        # 2. Check again (should find)
        print(f"[Live Test] Checking label '{label_name}' again...")
        # Clear cache to force re-check
        create_issue_module.checked_labels.pop(label_name, None)
        found = check_and_create_label(label_name, repo_flags, label_color)
        assert found is True, f"Failed to find existing label '{label_name}' on second check"

        # 3. Clean up (optional but good practice)
        print(f"[Live Test] Deleting label '{label_name}'...")
        exit_code, _, stderr = create_issue_module.run_command(["gh", "label", "delete", label_name] + repo_flags + ["--yes"], check=False)
        if exit_code != 0:
            print(f"  Warning: Failed to delete test label '{label_name}'. Stderr: {stderr.strip()}", file=sys.stderr)

    @pytest.mark.live # Mark as live test
    def test_ac3_ac4_live_check_create_milestone(self, live_run, test_repo, repo_flags):
        """AC3+AC4: Live test: Check and create a milestone."""
        if not live_run: pytest.skip("Requires --live flag")

        milestone_title = f"Live Milestone {int(time.time())}"
        milestone_desc = "Description for live test milestone."

        # Reset cache for this test
        create_issue_module.checked_milestones.clear()

        # 1. Check/Create milestone (should create)
        print(f"\n[Live Test] Checking/Creating milestone '{milestone_title}' in {test_repo}...")
        created_title = check_and_create_milestone(milestone_title, milestone_desc, repo_flags)
        assert created_title == milestone_title, f"Failed to create milestone '{milestone_title}'"

        # 2. Check again (should find)
        print(f"[Live Test] Checking milestone '{milestone_title}' again...")
        # Clear cache to force re-check
        create_issue_module.checked_milestones.pop(milestone_title, None)
        found_title = check_and_create_milestone(milestone_title, None, repo_flags) # Don't provide desc for find
        assert found_title == milestone_title, f"Failed to find existing milestone '{milestone_title}' on second check"

        # 3. Clean up (optional but good practice) - Find the number first
        print(f"[Live Test] Deleting milestone '{milestone_title}'...")
        jq_filter = f'.[] | select(.title == "{create_issue_module.escape_for_jq_string(milestone_title)}") | .number'
        cmd_list_num = ["gh", "milestone", "list"] + repo_flags + ["--json", "title,number", "--jq", jq_filter]
        exit_code_num, stdout_num, _ = create_issue_module.run_command(cmd_list_num, check=False)
        milestone_num_str = stdout_num.strip()

        if exit_code_num == 0 and milestone_num_str:
            try:
                 milestone_num = int(milestone_num_str)
                 # Use create_issue_module.run_command
                 exit_code_del, _, stderr_del = create_issue_module.run_command(["gh", "milestone", "delete", str(milestone_num)] + repo_flags, check=False)
                 if exit_code_del != 0:
                      print(f"  Warning: Failed to delete test milestone '{milestone_title}' (Number: {milestone_num}). Stderr: {stderr_del.strip()}", file=sys.stderr)
            except ValueError:
                 print(f"  Warning: Could not parse milestone number '{milestone_num_str}' for deletion.", file=sys.stderr)
        else:
            print(f"  Warning: Could not find milestone number to delete milestone '{milestone_title}'.", file=sys.stderr)

    @pytest.mark.live # Mark as live test
    def test_ac3_ac4_live_find_project(self, live_run, test_repo, repo_flags, default_config):
        """AC3+AC4: Live test: Find a project (assumes a project exists)."""
        if not live_run: pytest.skip("Requires --live flag")

        # IMPORTANT: This test assumes a project named 'Test Project Board'
        # exists under the configured GH_TEST_REPO owner OR under @me.
        # Adjust the project name if necessary.
        project_to_find = "Laravel 12 Starter Kit" # Use the actual project name from context
        owner_to_check = default_config["project_owner"] # Usually @me

        print(f"\n[Live Test] Finding project '{project_to_find}' under '{owner_to_check}'...")
        project_id = find_project_id(project_to_find, owner_to_check, repo_flags)

        # If not found under primary owner, try repo owner (if different)
        if not project_id:
             repo_owner_actual = test_repo.split('/')[0]
             if owner_to_check != repo_owner_actual:
                  print(f"[Live Test] Project not found under '{owner_to_check}', trying repo owner '{repo_owner_actual}'...")
                  project_id = find_project_id(project_to_find, repo_owner_actual, repo_flags)

        assert project_id is not None, f"Failed to find project '{project_to_find}' under '{owner_to_check}' or repo owner. Ensure project exists."
        print(f"[Live Test] Found project ID: {project_id}")


# --- Placeholder for Future Tests ---
# Add tests for AC5, AC6, AC7, AC8, AC9, AC10, AC11, AC12 as development progresses.
# Example structure:
#
# @mock.patch('scripts.create_issue.run_command')
# def test_ac6_create_issue_flags(self, mock_run_cmd, ...):
#     """AC6: Test specific flags used in 'gh issue create'."""
#     # Setup issue_data with specific fields (assignee, milestone, project)
#     # Call create_github_issue
#     # Assert mock_run_cmd was called with the exact expected flags (-a, -m, -p, -l)
#     pass
#
# @mock.patch('scripts.create_issue.run_command')
# def test_ac11_error_handling_gh_fail(self, mock_run_cmd, ...):
#      """AC11: Test error handling when gh command fails."""
#      # Configure mock_run_cmd to return non-zero exit code
#      # Call create_github_issue or edit_github_issue
#      # Assert the function returns False and logs an error
#      pass