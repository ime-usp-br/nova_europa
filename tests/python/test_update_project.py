# -*- coding: utf-8 -*-

"""
Unit and integration tests for the update_project.py script.

Ensures the script correctly parses demarcated file blocks,
handles file paths securely, creates necessary directories,
and writes content to the target files within the project structure.
"""
import pytest
import sys
from pathlib import Path

# Import the function and potentially constants to be tested/mocked
from scripts.update_project import parse_source_content, update_files_from_source


# AC 1: Configure pytest (dependencies, basic fixtures)
# This file structure and the presence of pytest in requirements-dev.txt
# fulfills the initial setup requirement. The tmp_path fixture needed
# for subsequent ACs is provided by pytest automatically.

# Removed the placeholder test as actual tests are now present.

# --- AC 2: Unit Tests for Parsing Logic ---
# Existing unit tests for parse_source_content remain unchanged.


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
    matches = parse_source_content(test_content)
    assert len(matches) == 1
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
    assert matches[0][1] == ""  # Expecting empty string content


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
    assert matches[0][1] == "  \t\n  \n"


def test_parse_no_blocks_present():
    """Verify no matches are found when the delimiters are absent."""
    test_content = "Just some regular text without any file blocks."
    matches = parse_source_content(test_content)
    assert len(matches) == 0


def test_parse_malformed_start_delimiter():
    """Verify malformed start delimiter prevents matching."""
    test_content = """
--- STARTT OF FILE path/to/file.txt ---
Content here.
--- END OF FILE path/to/file.txt ---
"""
    matches = parse_source_content(test_content)
    assert len(matches) == 0


def test_parse_malformed_end_delimiter():
    """Verify malformed end delimiter prevents matching."""
    test_content = """
--- START OF FILE path/to/file.txt ---
Content here.
--- WRONG END OF FILE path/to/file.txt ---
"""
    matches = parse_source_content(test_content)
    assert len(matches) == 0


def test_parse_malformed_end_delimiter_mismatched_path():
    """Verify mismatched paths in start/end delimiters prevent matching."""
    test_content = """
--- START OF FILE path/correct.txt ---
Content here.
--- END OF FILE path/incorrect.txt ---
"""
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
    assert matches[0][0] == test_path
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
    assert matches[0][0] == ""
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
    matches = parse_source_content(test_content)
    assert len(matches) == 1
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
    assert matches[0][0] == "path/needs/trimming.txt"
    assert matches[0][1] == "Content."


# --- End of AC 2 Tests ---


# --- AC 3: Integration Tests for File Writing ---

SOURCE_FILE_NAME = "test_source_code.txt"


@pytest.fixture(autouse=True)
def change_project_root(monkeypatch, tmp_path):
    """
    Fixture to automatically redirect PROJECT_ROOT to tmp_path for all tests
    in this module that use tmp_path.
    """
    # Use the actual script's module path for setattr
    monkeypatch.setattr("scripts.update_project.PROJECT_ROOT", tmp_path)


def test_integration_single_file(tmp_path, capsys):
    """Verify writing a single file from a source block."""
    source_content = """
--- START OF FILE single.txt ---
This is the content.
--- END OF FILE single.txt ---
"""
    source_file = tmp_path / SOURCE_FILE_NAME
    source_file.write_text(source_content, encoding="utf-8")

    # Run the main function of the script
    update_files_from_source(source_file_name=SOURCE_FILE_NAME)

    # Assertions
    output_file = tmp_path / "single.txt"
    assert output_file.exists()
    assert output_file.read_text(encoding="utf-8") == "This is the content."

    captured = capsys.readouterr()
    assert "Successfully updated: 'single.txt'" in captured.out
    assert "Summary: 1 files updated, 0 errors." in captured.out


def test_integration_multiple_files(tmp_path, capsys):
    """Verify writing multiple files from source blocks."""
    source_content = """
--- START OF FILE file1.py ---
print("File 1")
--- END OF FILE file1.py ---

--- START OF FILE file2.log ---
Log entry.
--- END OF FILE file2.log ---
"""
    source_file = tmp_path / SOURCE_FILE_NAME
    source_file.write_text(source_content, encoding="utf-8")

    update_files_from_source(source_file_name=SOURCE_FILE_NAME)

    # Assertions
    file1 = tmp_path / "file1.py"
    file2 = tmp_path / "file2.log"
    assert file1.exists()
    assert file1.read_text(encoding="utf-8") == 'print("File 1")'
    assert file2.exists()
    assert file2.read_text(encoding="utf-8") == "Log entry."

    captured = capsys.readouterr()
    assert "Successfully updated: 'file1.py'" in captured.out
    assert "Successfully updated: 'file2.log'" in captured.out
    assert "Summary: 2 files updated, 0 errors." in captured.out


def test_integration_subdirectory_creation(tmp_path, capsys):
    """Verify creation of necessary subdirectories."""
    source_content = """
--- START OF FILE nested/path/to/deep_file.js ---
console.log('Deep');
--- END OF FILE nested/path/to/deep_file.js ---
"""
    source_file = tmp_path / SOURCE_FILE_NAME
    source_file.write_text(source_content, encoding="utf-8")

    update_files_from_source(source_file_name=SOURCE_FILE_NAME)

    # Assertions
    output_file = tmp_path / "nested/path/to/deep_file.js"
    output_dir = tmp_path / "nested/path/to"
    assert output_dir.exists()
    assert output_dir.is_dir()
    assert output_file.exists()
    assert output_file.read_text(encoding="utf-8") == "console.log('Deep');"

    captured = capsys.readouterr()
    assert "Ensuring directory exists: 'nested/path/to'" in captured.out
    assert "Successfully updated: 'nested/path/to/deep_file.js'" in captured.out
    assert "Summary: 1 files updated, 0 errors." in captured.out


def test_integration_overwrite_existing_file(tmp_path, capsys):
    """Verify that existing files are overwritten."""
    target_file = tmp_path / "existing.txt"
    target_file.write_text("Old content", encoding="utf-8")

    source_content = """
--- START OF FILE existing.txt ---
New content.
--- END OF FILE existing.txt ---
"""
    source_file = tmp_path / SOURCE_FILE_NAME
    source_file.write_text(source_content, encoding="utf-8")

    update_files_from_source(source_file_name=SOURCE_FILE_NAME)

    # Assertions
    assert target_file.exists()
    assert target_file.read_text(encoding="utf-8") == "New content."

    captured = capsys.readouterr()
    assert "Successfully updated: 'existing.txt'" in captured.out
    assert "Summary: 1 files updated, 0 errors." in captured.out


def test_integration_relative_paths_handled(tmp_path, capsys):
    """Verify that relative paths like '..' are resolved correctly within root."""
    source_content = """
--- START OF FILE dir1/../dir2/final.txt ---
Relative path test.
--- END OF FILE dir1/../dir2/final.txt ---
"""
    source_file = tmp_path / SOURCE_FILE_NAME
    source_file.write_text(source_content, encoding="utf-8")

    update_files_from_source(source_file_name=SOURCE_FILE_NAME)

    # Assertions
    output_file = tmp_path / "dir2/final.txt"  # dir1/../dir2 becomes dir2
    output_dir = tmp_path / "dir2"
    assert output_dir.exists() and output_dir.is_dir()
    assert output_file.exists()
    assert output_file.read_text(encoding="utf-8") == "Relative path test."

    captured = capsys.readouterr()
    assert (
        "Successfully updated: 'dir2/final.txt'" in captured.out
    )  # Script logs the normalized relative path
    assert "Summary: 1 files updated, 0 errors." in captured.out


def test_integration_source_file_not_found(tmp_path, capsys):
    """Verify graceful exit if the source file does not exist."""
    non_existent_source = "this_file_does_not_exist.txt"

    # Expect SystemExit with code 1
    with pytest.raises(SystemExit) as excinfo:
        update_files_from_source(source_file_name=non_existent_source)

    assert excinfo.value.code == 1

    # Check stderr/stdout for the error message
    captured = capsys.readouterr()
    # The script prints to stdout in this case
    expected_path = tmp_path / non_existent_source
    assert f"Error: Source file not found at '{expected_path}'" in captured.out


def test_integration_path_traversal_attempt(tmp_path, capsys):
    """Verify prevention of writing outside the project root."""
    # Create a directory outside the mocked project root (tmp_path)
    # This shouldn't happen in real usage but simulates the check
    outside_dir = tmp_path.parent / "outside_test_dir"
    outside_dir.mkdir(exist_ok=True)  # Ensure it exists for cleanup
    outside_file_target = outside_dir / "malicious.txt"

    source_content = f"""
--- START OF FILE ../{outside_dir.name}/malicious.txt ---
Attempting path traversal.
--- END OF FILE ../{outside_dir.name}/malicious.txt ---

--- START OF FILE safe_insider.txt ---
This should be written.
--- END OF FILE safe_insider.txt ---
"""
    source_file = tmp_path / SOURCE_FILE_NAME
    source_file.write_text(source_content, encoding="utf-8")

    try:
        update_files_from_source(source_file_name=SOURCE_FILE_NAME)

        # Assertions
        assert (
            not outside_file_target.exists()
        )  # Critical: File outside root MUST NOT be created
        safe_file = tmp_path / "safe_insider.txt"
        assert safe_file.exists()  # Safe file should be created
        assert safe_file.read_text(encoding="utf-8") == "This should be written."

        captured = capsys.readouterr()
        assert (
            "Error: Attempted to write outside the project directory:" in captured.out
        )
        # Check relative path shown in error message - .resolve() makes it absolute
        # Check if the absolute path of the *intended* illegal write is mentioned
        assert str(outside_file_target.resolve()) in captured.out
        assert "Skipping." in captured.out
        assert (
            "Successfully updated: 'safe_insider.txt'" in captured.out
        )  # Safe file success message
        assert (
            "Summary: 1 files updated, 1 errors." in captured.out
        )  # Ensure error was counted

    finally:
        # Clean up the directory created outside tmp_path
        if outside_file_target.exists():
            outside_file_target.unlink()  # Should not exist, but clean up if it does
        if outside_dir.exists():
            outside_dir.rmdir()


# --- End of AC 3 Tests ---


# --- AC 4: Edge Case Tests ---


def test_integration_empty_source_file(tmp_path, capsys):
    """Verify behavior when the source input file is completely empty."""
    source_file = tmp_path / SOURCE_FILE_NAME
    source_file.write_text("", encoding="utf-8")  # Create empty file

    update_files_from_source(source_file_name=SOURCE_FILE_NAME)

    # Assertions
    # No files should be created
    found_files = list(tmp_path.glob("*"))
    # Only the empty source file itself should exist
    assert len(found_files) == 1
    assert found_files[0].name == SOURCE_FILE_NAME

    captured = capsys.readouterr()
    # Expect a warning about no blocks found
    assert "Warning: No file blocks found in the source file" in captured.out
    assert "Summary: 0 files updated, 0 errors." in captured.out


def test_integration_empty_content_block_writes_empty_file(tmp_path, capsys):
    """Verify that a block with empty content creates an empty file."""
    source_content = """
Some text before.
--- START OF FILE completely_empty.txt ---
--- END OF FILE completely_empty.txt ---
Some text after.
"""
    source_file = tmp_path / SOURCE_FILE_NAME
    source_file.write_text(source_content, encoding="utf-8")

    update_files_from_source(source_file_name=SOURCE_FILE_NAME)

    # Assertions
    output_file = tmp_path / "completely_empty.txt"
    assert output_file.exists()
    # Ensure the file is actually empty
    assert output_file.read_text(encoding="utf-8") == ""

    captured = capsys.readouterr()
    assert "Successfully updated: 'completely_empty.txt'" in captured.out
    assert "Summary: 1 files updated, 0 errors." in captured.out


def test_integration_malformed_delimiters_in_file(tmp_path, capsys):
    """Verify malformed delimiters in the source file are skipped."""
    source_content = """
Valid block before:
--- START OF FILE valid_before.txt ---
Content 1
--- END OF FILE valid_before.txt ---

Malformed start:
--- STARTT OF FILE invalid_start.txt ---
Content X
--- END OF FILE invalid_start.txt ---

Malformed end:
--- START OF FILE invalid_end.txt ---
Content Y
--- ENDD OF FILE invalid_end.txt ---

Mismatched path:
--- START OF FILE mismatch1.txt ---
Content Z
--- END OF FILE mismatch2.txt ---

Missing end:
--- START OF FILE missing_end.txt ---
Content W

Valid block after:
--- START OF FILE valid_after.txt ---
Content 2
--- END OF FILE valid_after.txt ---
"""
    source_file = tmp_path / SOURCE_FILE_NAME
    source_file.write_text(source_content, encoding="utf-8")

    update_files_from_source(source_file_name=SOURCE_FILE_NAME)

    # Assertions
    assert (tmp_path / "valid_before.txt").exists()
    assert (tmp_path / "valid_before.txt").read_text() == "Content 1"
    assert (tmp_path / "valid_after.txt").exists()
    assert (tmp_path / "valid_after.txt").read_text() == "Content 2"

    assert not (tmp_path / "invalid_start.txt").exists()
    assert not (tmp_path / "invalid_end.txt").exists()
    assert not (tmp_path / "mismatch1.txt").exists()
    assert not (tmp_path / "mismatch2.txt").exists()
    assert not (tmp_path / "missing_end.txt").exists()

    captured = capsys.readouterr()
    # Check the summary: only the 2 valid files should be processed.
    assert "Summary: 2 files updated, 0 errors." in captured.out
    # Script doesn't necessarily warn about malformed blocks found during parsing,
    # it just doesn't match them. The warning only appears if *no* blocks match.


def test_integration_empty_path_in_block(tmp_path, capsys):
    """Verify handling of a block with an empty file path."""
    source_content = """
--- START OF FILE ---
Content for empty path.
--- END OF FILE ---

--- START OF FILE valid.txt ---
Valid content.
--- END OF FILE valid.txt ---
"""
    source_file = tmp_path / SOURCE_FILE_NAME
    source_file.write_text(source_content, encoding="utf-8")

    update_files_from_source(source_file_name=SOURCE_FILE_NAME)

    # Assertions
    # File with empty path should not be created
    # Check if any file *without* an extension exists (could be the empty path one)
    found_no_ext = [p for p in tmp_path.iterdir() if p.is_file() and not p.suffix]
    assert (
        not found_no_ext
    )  # Or specifically check for a file named "" which is unlikely

    # Valid file should be created
    valid_file = tmp_path / "valid.txt"
    assert valid_file.exists()
    assert valid_file.read_text() == "Valid content."

    captured = capsys.readouterr()
    # Expect a warning about the empty path block and an error count of 1
    assert "Warning: Found a block with an empty file path. Skipping." in captured.out
    assert "Successfully updated: 'valid.txt'" in captured.out
    assert "Summary: 1 files updated, 1 errors." in captured.out


# --- End of AC 4 Tests ---
