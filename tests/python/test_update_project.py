# -*- coding: utf-8 -*-

"""
Unit and integration tests for the update_project.py script.

Ensures the script correctly parses demarcated file blocks,
handles file paths securely, creates necessary directories,
and writes content to the target files within the project structure.
"""

import pytest  # noqa: F401 - pytest is the test runner
# Import the function to be tested directly from the script
from scripts.update_project import parse_source_content


# AC 1: Configure pytest (dependencies, basic fixtures)
# This file structure and the presence of pytest in requirements-dev.txt
# fulfills the initial setup requirement. The tmp_path fixture needed
# for subsequent ACs is provided by pytest automatically.

def test_placeholder_for_setup():
    """
    Placeholder test to confirm pytest setup is working.
    This test will be replaced by actual tests for AC 3 and onwards.
    """
    assert True

# --- AC 2: Unit Tests for Parsing Logic ---
# Tests now use the imported `parse_source_content` function

def test_parse_single_valid_block():
    """Verify parsing of a single, standard file block."""
    test_content = """
Some text before the block.

--- START OF FILE path/to/file.txt ---
File content line 1.
Line 2.
--- END OF FILE path/to/file.txt ---

Some text after the block.
"""
    # Call the actual parsing function from the script
    matches = parse_source_content(test_content)
    assert len(matches) == 1
    # The function returns a list of (path, content) tuples
    assert matches[0][0] == "path/to/file.txt"
    assert matches[0][1] == "File content line 1.\nLine 2."

def test_parse_multiple_valid_blocks():
    """Verify parsing of multiple file blocks within the same string."""
    test_content = """
--- START OF FILE file1.py ---
print("hello")
--- END OF FILE file1.py ---
Some separator text.
--- START OF FILE path/to/another.css ---
.class { color: red; }
--- END OF FILE path/to/another.css ---
"""
    matches = parse_source_content(test_content)
    assert len(matches) == 2
    assert matches[0][0] == "file1.py"
    assert matches[0][1] == 'print("hello")'
    assert matches[1][0] == "path/to/another.css"
    assert matches[1][1] == ".class { color: red; }"

def test_parse_block_with_empty_content():
    """Verify parsing works correctly when the content is empty."""
    test_content = """
--- START OF FILE empty.txt ---

--- END OF FILE empty.txt ---
"""
    matches = parse_source_content(test_content)
    assert len(matches) == 1
    assert matches[0][0] == "empty.txt"
    assert matches[0][1] == "" # Expecting empty string content

def test_parse_block_with_only_whitespace_content():
    """Verify parsing works correctly when content is only whitespace/newlines."""
    test_content = """
--- START OF FILE whitespace.log ---
  \t
  \n
--- END OF FILE whitespace.log ---
"""
    matches = parse_source_content(test_content)
    assert len(matches) == 1
    assert matches[0][0] == "whitespace.log"
    # The parser captures exactly what's between delimiters
    assert matches[0][1] == "  \t\n  \n"

def test_parse_no_blocks_present():
    """Verify no matches are found when the delimiters are absent."""
    test_content = "Just some regular text without any file blocks."
    matches = parse_source_content(test_content)
    assert len(matches) == 0

def test_parse_malformed_start_delimiter():
    """Verify malformed start delimiter prevents matching."""
    test_content = """
--- START OF FILE path/to/file.txt ---
Content here.
--- WRONG END OF FILE path/to/file.txt ---
"""
    # The regex requires exact "END OF FILE" structure with the correct path
    matches = parse_source_content(test_content)
    assert len(matches) == 0

def test_parse_malformed_end_delimiter_mismatched_path():
    """Verify mismatched paths in start/end delimiters prevent matching."""
    test_content = """
--- START OF FILE path/correct.txt ---
Content here.
--- END OF FILE path/incorrect.txt ---
"""
    # The \1 backreference in the regex enforces matching paths
    matches = parse_source_content(test_content)
    assert len(matches) == 0

def test_parse_missing_end_delimiter():
    """Verify block is not matched if end delimiter is missing."""
    test_content = """
--- START OF FILE path/incomplete.txt ---
Content here.
"""
    matches = parse_source_content(test_content)
    assert len(matches) == 0

def test_parse_block_with_special_regex_chars_in_path():
    """Verify paths containing characters special to regex are handled."""
    test_path = "path/with[special].chars"
    test_content = f"""
--- START OF FILE {test_path} ---
Content.
--- END OF FILE {test_path} ---
"""
    matches = parse_source_content(test_content)
    assert len(matches) == 1
    assert matches[0][0] == test_path # Path captured correctly
    assert matches[0][1] == "Content."

def test_parse_block_with_empty_path():
    """Verify parsing captures an empty path (script might warn later)."""
    test_content = """
--- START OF FILE ---
Content for empty path.
--- END OF FILE ---
"""
    matches = parse_source_content(test_content)
    assert len(matches) == 1
    assert matches[0][0] == "" # Path is captured as empty string
    assert matches[0][1] == "Content for empty path."

def test_parse_delimiters_must_be_at_line_start():
    """Verify that delimiters not at the start of a line are not matched."""
    test_content = """
  --- START OF FILE indented.txt ---
Content
--- END OF FILE indented.txt ---

--- START OF FILE correct.txt ---
More Content
--- END OF FILE correct.txt ---
"""
    # The ^ anchor in the regex requires delimiters to be at the absolute start of a line.
    matches = parse_source_content(test_content)
    assert len(matches) == 1 # Only the 'correct.txt' block should match
    assert matches[0][0] == "correct.txt"
    assert matches[0][1] == "More Content"

def test_parse_path_with_leading_trailing_spaces_in_delimiter():
    """Verify leading/trailing spaces around path in delimiter are stripped."""
    test_content = """
--- START OF FILE   path/needs/trimming.txt   ---
Content.
--- END OF FILE   path/needs/trimming.txt   ---
"""
    matches = parse_source_content(test_content)
    assert len(matches) == 1
    # parse_source_content is responsible for stripping the path
    assert matches[0][0] == "path/needs/trimming.txt"
    assert matches[0][1] == "Content."

# --- End of AC 2 Tests ---


# Future tests for AC 3 (File Writing & Integration with tmp_path) will go here.
# Example:
# def test_write_single_file(tmp_path):
#     # Setup source file in tmp_path
#     # Run update_project.py (perhaps via subprocess or by importing/calling main)
#     # Assert file exists in tmp_path with correct content
#     ...

# Future tests for AC 4 (Edge Cases) will go here.
# Example:
# def test_invalid_path_outside_root(tmp_path, capsys): # Example for AC3/4
#     # Setup source file with path like ../../outside.txt
#     # Run update_project.py
#     # Assert file was NOT created outside tmp_path
#     # Assert warning/error message was printed (using capsys fixture)
#     ...