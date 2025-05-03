# -*- coding: utf-8 -*-
"""
Unit tests for the create_issue.py script, focusing on parsing and templating.

Ensures the script correctly parses structured plan files (`KEY: VALUE` blocks)
and prepares issue bodies using templates according to AC 2 of Issue #46.
"""

import pytest
from pathlib import Path
import sys
from typing import List, Dict, Any

import importlib
import scripts.create_issue

# Add script directory to sys.path to allow importing
# Assuming tests are run from the project root (e.g., using `python -m pytest`)
SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR.parent))

# Functions to test
from scripts.create_issue import parse_plan_file, prepare_issue_body

# --- Fixtures ---

@pytest.fixture
def temp_plan_file(tmp_path: Path) -> Path:
    """Creates a temporary plan file path."""
    return tmp_path / "test_plan.txt"

@pytest.fixture
def temp_template_dir(tmp_path: Path) -> Path:
    """Creates a temporary directory for issue body templates."""
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    return template_dir

# --- Tests for parse_plan_file (AC 2 Part 1) ---

def test_parse_single_block_simple(temp_plan_file: Path):
    """Test parsing a single block with basic KEY: VALUE pairs."""
    content = """
TITLE: Test Issue Title
TYPE: feature
ASSIGNEE: @me
LABELS: bug, ui
DESCRIPTION: This is a test description.
"""
    temp_plan_file.write_text(content, encoding="utf-8")
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
    temp_plan_file.write_text(content, encoding="utf-8")
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
    temp_plan_file.write_text(content, encoding="utf-8")
    result = parse_plan_file(temp_plan_file)
    assert len(result) == 1
    expected_description = (
        "Line 1 of description.\n"
        "  Line 2 indented.\n" # Comment " # ..." removed
        "Still part of description.\n" # Full comment line removed
        "    Another indented line." # Comment " # ..." removed
    )
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
    temp_plan_file.write_text(content, encoding="utf-8")
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
    temp_plan_file.write_text(content, encoding="utf-8")
    result = parse_plan_file(temp_plan_file)
    assert len(result) == 1
    assert result[0]["TITLE"] == "Valid Issue"
    captured = capsys.readouterr()
    assert "Warning: Skipping block 1 - Missing or empty TITLE field." in captured.err # Matches script output

def test_parse_empty_file(temp_plan_file: Path):
    """Test parsing an empty file."""
    content = ""
    temp_plan_file.write_text(content, encoding="utf-8")
    result = parse_plan_file(temp_plan_file)
    assert len(result) == 0

def test_parse_file_not_found(capsys):
    """Test parsing a non-existent file."""
    non_existent_path = Path("non_existent_plan.txt")
    result = parse_plan_file(non_existent_path)
    assert len(result) == 0
    captured = capsys.readouterr()
    # Assuming parse_arguments resolves path now, error might differ slightly or not happen here
    # Let's assert based on the function's own error message
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
    temp_plan_file.write_text(content, encoding="utf-8")
    result = parse_plan_file(temp_plan_file)
    assert len(result) == 2
    assert result[0]["TITLE"] == "Spaced out title"
    assert result[0]["TYPE"] == "feature"
    assert result[0]["DESCRIPTION"] == "Line 1.\n\n  Line 2." # Preserves internal newlines and indentation
    assert result[1]["TITLE"] == "Issue 2"


# --- Tests for prepare_issue_body (AC 2 Part 2) ---

@pytest.fixture
def setup_templates(temp_template_dir: Path):
    """Creates dummy template files."""
    (temp_template_dir / "feature_body.md").write_text(
        "## Feature Request\n**Goal:** __GOAL__\n**Details:** __DESCRIPTION__",
        encoding="utf-8"
    )
    (temp_template_dir / "bug_body.md").write_text(
        "## Bug Report\n**Problem:** __PROBLEM__\n**Steps:** __STEPS__\n**Parent:** __PARENT_ISSUE__",
        encoding="utf-8"
    )
    (temp_template_dir / "default_body.md").write_text(
        "## Default Issue\n**Title:** __TITLE__\n**Info:** __INFO__",
        encoding="utf-8"
    )
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
    empty_template_dir = tmp_path / "empty_templates"
    empty_template_dir.mkdir()
    issue_data = {
        "TITLE": "Generic Issue",
        "TYPE": "feature",
        "DETAIL": "Some detail here",
        "EXTRA": "More data",
    }
    body = prepare_issue_body(empty_template_dir, "feature", issue_data)
    assert "Issue created from script for title: Generic Issue" in body
    assert "Details:" in body
    assert "- TYPE: feature" in body # TYPE is included as it's in issue_data
    assert "- DETAIL: Some detail here" in body
    assert "- EXTRA: More data" in body
    assert "TITLE" not in body.split("Details:")[1] # Title shouldn't be repeated in details

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

# --- End of AC 2 Tests ---