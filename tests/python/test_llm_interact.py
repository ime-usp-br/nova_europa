# -*- coding: utf-8 -*-
"""
Unit tests for argument parsing and other functionalities in the llm_interact.py script.
"""

import pytest
import sys
from typing import List, Optional, Dict, Any  # Adicionado Dict e Any
from pathlib import Path
import re  # For load_and_fill_template tests
from scripts.llm_interact import (
    parse_arguments,
    DEFAULT_BASE_BRANCH,
    find_available_tasks,
    find_available_meta_tasks,
    prompt_user_to_select_task,  # Added for AC4 #47
    load_and_fill_template,  # Added for AC5 #47
)

# A fixed list of tasks for testing argument parsing in isolation.
# These would normally be discovered by scanning template directories.
MOCK_AVAILABLE_TASKS = [
    "resolve-ac",
    "commit-mesage",
    "manifest-summary",
    "update-doc",
    "create-pr",
    "analyze-ac",
    "create-test-sub-issue",
    "review-issue",
    "fix-phpstan",
    "fix-artisan-test",
    "fix-artisan-dusk",
]

# Mock tasks dictionary for testing prompt_user_to_select_task (AC4 #47)
MOCK_TASKS_DICT_FOR_PROMPT_TESTS: Dict[str, Path] = {
    "task-echo": Path("dummy/prompts/prompt-task-echo.txt"),
    "task-bravo": Path("dummy/prompts/prompt-task-bravo.txt"),
    "task-alpha": Path("dummy/prompts/prompt-task-alpha.txt"),  # Intentionally unsorted
}
# Expected sorted order for menu display and selection mapping
SORTED_MOCK_TASK_NAMES_FOR_PROMPT_TESTS = sorted(
    MOCK_TASKS_DICT_FOR_PROMPT_TESTS.keys()
)
# Expected: ["task-alpha", "task-bravo", "task-echo"]


def call_parse_arguments(cmd_list: Optional[List[str]] = None):
    """Helper para chamar parse_arguments, passando a lista de comandos explicitamente."""
    if cmd_list is None:
        cmd_list = []
    parser = parse_arguments(MOCK_AVAILABLE_TASKS)
    try:
        args = parser.parse_args(cmd_list)
        return args
    except SystemExit as e:
        print(
            f"\nArgparse exited with code {e.code} for command: {cmd_list}",
            file=sys.stderr,
        )
        raise


def test_parse_arguments_defaults():
    """Test parsing with no arguments, checking default values."""
    args = call_parse_arguments([])

    assert args.task is None
    assert args.two_stage is False
    assert args.issue is None
    assert args.ac is None
    assert args.observation == ""
    assert args.doc_file is None
    assert args.target_branch == DEFAULT_BASE_BRANCH
    assert args.draft is False
    assert args.web_search is False
    assert args.generate_context is False
    assert args.yes is False
    assert args.only_meta is False
    assert args.only_prompt is False
    assert args.with_sleep is False
    assert args.exclude_context == []
    assert args.manifest_path is None
    assert args.force_summary == []
    assert args.max_files_per_call == 10
    assert args.select_context is False


def test_parse_arguments_task_provided():
    """Test providing a task as a positional argument."""
    args = call_parse_arguments(["resolve-ac"])
    assert args.task == "resolve-ac"

    args = call_parse_arguments(["manifest-summary"])
    assert args.task == "manifest-summary"


def test_parse_arguments_invalid_task():
    """Test providing an invalid task."""
    with pytest.raises(SystemExit):
        call_parse_arguments(["this-task-is-not-valid"])


def test_parse_arguments_boolean_flags():
    """Test boolean flags (short and long versions where applicable)."""
    # Test --two-stage / -ts
    args_ts_long = call_parse_arguments(["--two-stage"])
    assert args_ts_long.two_stage is True
    args_ts_short = call_parse_arguments(["-ts"])
    assert args_ts_short.two_stage is True

    # Test --select-context / -sc
    args_sc_long = call_parse_arguments(["--select-context"])
    assert args_sc_long.select_context is True
    args_sc_short = call_parse_arguments(["-sc"])
    assert args_sc_short.select_context is True

    # Test --draft
    args_draft = call_parse_arguments(["--draft"])
    assert args_draft.draft is True

    # Test --web-search / -w
    args_w_long = call_parse_arguments(["--web-search"])
    assert args_w_long.web_search is True
    args_w_short = call_parse_arguments(["-w"])
    assert args_w_short.web_search is True

    # Test --generate-context / -g
    args_g_long = call_parse_arguments(["--generate-context"])
    assert args_g_long.generate_context is True
    args_g_short = call_parse_arguments(["-g"])
    assert args_g_short.generate_context is True

    # Test --yes / -y
    args_y_long = call_parse_arguments(["--yes"])
    assert args_y_long.yes is True
    args_y_short = call_parse_arguments(["-y"])
    assert args_y_short.yes is True

    # Test --only-meta / -om
    args_om_long = call_parse_arguments(["--only-meta"])
    assert args_om_long.only_meta is True
    args_om_short = call_parse_arguments(["-om"])
    assert args_om_short.only_meta is True

    # Test --only-prompt / -op
    args_op_long = call_parse_arguments(["--only-prompt"])
    assert args_op_long.only_prompt is True
    args_op_short = call_parse_arguments(["-op"])
    assert args_op_short.only_prompt is True

    # Test --with-sleep / -ws
    args_ws_long = call_parse_arguments(["--with-sleep"])
    assert args_ws_long.with_sleep is True
    args_ws_short = call_parse_arguments(["-ws"])
    assert args_ws_short.with_sleep is True


def test_parse_arguments_with_values():
    """Test arguments that take values (short and long versions)."""
    # Test --issue / -i
    args_i_long = call_parse_arguments(["--issue", "123"])
    assert args_i_long.issue == "123"
    args_i_short = call_parse_arguments(["-i", "456"])
    assert args_i_short.issue == "456"

    # Test --ac / -a
    args_a_long = call_parse_arguments(["--ac", "7"])
    assert args_a_long.ac == "7"
    args_a_short = call_parse_arguments(["-a", "8"])
    assert args_a_short.ac == "8"

    # Test --observation / -o
    obs_text = "This is an observation."
    args_o_long = call_parse_arguments(["--observation", obs_text])
    assert args_o_long.observation == obs_text
    args_o_short = call_parse_arguments(["-o", obs_text])
    assert args_o_short.observation == obs_text

    # Test --doc-file / -d
    doc_path = "docs/some_file.md"
    args_d_long = call_parse_arguments(["--doc-file", doc_path])
    assert args_d_long.doc_file == doc_path
    args_d_short = call_parse_arguments(["-d", doc_path])
    assert args_d_short.doc_file == doc_path

    # Test --target-branch / -b
    branch_name = "develop"
    args_b_long = call_parse_arguments(["--target-branch", branch_name])
    assert args_b_long.target_branch == branch_name
    args_b_short = call_parse_arguments(["-b", branch_name])
    assert args_b_short.target_branch == branch_name

    # Test --manifest-path
    manifest_file = "scripts/data/my_manifest.json"
    args_manifest = call_parse_arguments(["--manifest-path", manifest_file])
    assert args_manifest.manifest_path == manifest_file

    # Test --max-files-per-call
    max_files = "50"
    args_max_files = call_parse_arguments(["--max-files-per-call", max_files])
    assert args_max_files.max_files_per_call == int(max_files)


def test_parse_arguments_append_actions():
    """Test arguments with 'append' action."""
    # Test --exclude-context / -ec
    ec_files = ["file1.txt", "path/to/file2.py"]
    args_ec_long = call_parse_arguments(
        ["--exclude-context", ec_files[0], "--exclude-context", ec_files[1]]
    )
    assert args_ec_long.exclude_context == ec_files
    args_ec_short = call_parse_arguments(["-ec", ec_files[0], "-ec", ec_files[1]])
    assert args_ec_short.exclude_context == ec_files
    args_ec_mixed = call_parse_arguments(
        ["-ec", ec_files[0], "--exclude-context", ec_files[1]]
    )
    assert args_ec_mixed.exclude_context == ec_files

    # Test --force-summary
    fs_files = ["fileA.md", "module/fileB.php"]
    args_fs = call_parse_arguments(
        ["--force-summary", fs_files[0], "--force-summary", fs_files[1]]
    )
    assert args_fs.force_summary == fs_files


def test_parse_arguments_combined():
    """Test a combination of various arguments."""
    cmd_list = [
        "commit-mesage",
        "-i",
        "99",
        "--ac",
        "1",
        "-ts",
        "--observation",
        "A complex observation.",
        "-ec",
        "exclude/this.txt",
        "--exclude-context",
        "another/one.json",
        "--draft",
        "-g",
        "-sc",
        "--max-files-per-call",
        "5",
    ]
    args = call_parse_arguments(cmd_list)

    assert args.task == "commit-mesage"
    assert args.issue == "99"
    assert args.ac == "1"
    assert args.two_stage is True
    assert args.observation == "A complex observation."
    assert args.exclude_context == ["exclude/this.txt", "another/one.json"]
    assert args.draft is True
    assert args.generate_context is True
    assert args.select_context is True
    assert args.max_files_per_call == 5

    # Check defaults for unspecified args
    assert args.doc_file is None
    assert args.target_branch == DEFAULT_BASE_BRANCH
    assert args.web_search is False
    assert args.yes is False
    assert args.only_meta is False
    assert args.only_prompt is False
    assert args.with_sleep is False
    assert args.manifest_path is None
    assert args.force_summary == []


def test_parse_arguments_missing_value_for_option():
    """Test that argparse exits if an option requiring a value is missing it."""
    # Example: -i needs a value
    with pytest.raises(SystemExit):
        call_parse_arguments(["-i"])

    with pytest.raises(SystemExit):
        call_parse_arguments(["resolve-ac", "--ac"])  # --ac also needs a value

    with pytest.raises(SystemExit):
        call_parse_arguments(["--max-files-per-call"])


def test_parse_arguments_task_help():
    """Test the help message for task choices."""
    parser = parse_arguments(MOCK_AVAILABLE_TASKS)
    # This is a bit of an indirect test, checking if the help string for 'task'
    # contains the mock tasks. Argparse formats this help string.
    task_help_string = ""
    for action in parser._actions:
        if action.dest == "task":
            task_help_string = action.help
            break
    assert "resolve-ac" in task_help_string
    assert "commit-mesage" in task_help_string
    assert "manifest-summary" in task_help_string
    assert (
        "Available: resolve-ac, commit-mesage, manifest-summary, update-doc, create-pr, analyze-ac, create-test-sub-issue"
        in task_help_string
    )


def test_parse_arguments_empty_tasks_list():
    """Test that parser can be created with an empty list of tasks."""
    parser = parse_arguments([])

    args_options = parser.parse_args(["--two-stage"])
    assert args_options.two_stage is True
    assert args_options.task is None

    # If choices is empty, argparse still parses the positional argument,
    # but it won't validate against the (non-existent) choices.
    # This behavior is fine, as the main script would exit if all_task_names is empty
    # before getting to a point where an invalid task choice would matter.
    args_task = parser.parse_args(["some-nonexistent-task"])
    assert args_task.task == "some-nonexistent-task"


# --- Task Discovery Tests (AC3 #47) ---


def test_find_available_tasks_empty_dir(tmp_path: Path):
    """Test find_available_tasks with an empty directory."""
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()
    assert find_available_tasks(prompt_dir) == {}


def test_find_available_tasks_dir_not_exists(tmp_path: Path):
    """Test find_available_tasks with a non-existent directory."""
    prompt_dir = tmp_path / "non_existent_prompts"
    assert find_available_tasks(prompt_dir) == {}


def test_find_available_tasks_single_valid_task(tmp_path: Path):
    """Test find_available_tasks with one valid task file."""
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()
    task_file = prompt_dir / "prompt-my-task.txt"
    task_file.write_text("content")
    expected = {"my-task": task_file.resolve()}
    assert find_available_tasks(prompt_dir) == expected


def test_find_available_tasks_multiple_valid_tasks(tmp_path: Path):
    """Test find_available_tasks with multiple valid task files, including underscores in names."""
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()
    task_file1 = prompt_dir / "prompt-task-one.txt"
    task_file1.write_text("content1")
    task_file2 = prompt_dir / "prompt-task_two_is_long.txt"  # with underscore
    task_file2.write_text("content2")
    task_file3 = prompt_dir / "prompt-another-task.txt"
    task_file3.write_text("content3")

    expected = {
        "task-one": task_file1.resolve(),
        "task-two-is-long": task_file2.resolve(),
        "another-task": task_file3.resolve(),
    }
    result = find_available_tasks(prompt_dir)
    assert result == expected


def test_find_available_tasks_with_invalid_and_valid_files(tmp_path: Path):
    """Test find_available_tasks with a mix of valid, invalid, and non-file entries."""
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()

    valid_file = prompt_dir / "prompt-real-deal.txt"
    valid_file.write_text("valid content")

    # Invalid names or extensions
    (prompt_dir / "notprompt-task.txt").write_text("invalid prefix")
    (prompt_dir / "prompt-invalid.md").write_text("invalid extension")
    (prompt_dir / "prompt-.txt").write_text("stem 'prompt-' results in empty task name")
    (prompt_dir / "another.txt").write_text("not matching pattern")

    # A directory that matches the pattern (should be ignored by is_file)
    (prompt_dir / "prompt-a-directory.txt").mkdir()

    expected = {"real-deal": valid_file.resolve()}
    assert find_available_tasks(prompt_dir) == expected


def test_find_available_meta_tasks_empty_dir(tmp_path: Path):
    """Test find_available_meta_tasks with an empty directory."""
    meta_prompt_dir = tmp_path / "meta_prompts"
    meta_prompt_dir.mkdir()
    assert find_available_meta_tasks(meta_prompt_dir) == {}


def test_find_available_meta_tasks_dir_not_exists(tmp_path: Path):
    """Test find_available_meta_tasks with a non-existent directory."""
    meta_prompt_dir = tmp_path / "non_existent_meta_prompts"
    assert find_available_meta_tasks(meta_prompt_dir) == {}


def test_find_available_meta_tasks_single_valid_task(tmp_path: Path):
    """Test find_available_meta_tasks with one valid meta task file."""
    meta_prompt_dir = tmp_path / "meta_prompts"
    meta_prompt_dir.mkdir()
    task_file = meta_prompt_dir / "meta-prompt-my-meta-task.txt"
    task_file.write_text("content")
    expected = {"my-meta-task": task_file.resolve()}
    assert find_available_meta_tasks(meta_prompt_dir) == expected


def test_find_available_meta_tasks_multiple_valid_tasks(tmp_path: Path):
    """Test find_available_meta_tasks with multiple valid meta task files."""
    meta_prompt_dir = tmp_path / "meta_prompts"
    meta_prompt_dir.mkdir()
    task_file1 = meta_prompt_dir / "meta-prompt-meta-one.txt"
    task_file1.write_text("content1")
    task_file2 = meta_prompt_dir / "meta-prompt-meta_two_is_also_long.txt"
    task_file2.write_text("content2")
    task_file3 = meta_prompt_dir / "meta-prompt-another-meta.txt"
    task_file3.write_text("content3")

    expected = {
        "meta-one": task_file1.resolve(),
        "meta-two-is-also-long": task_file2.resolve(),
        "another-meta": task_file3.resolve(),
    }
    result = find_available_meta_tasks(meta_prompt_dir)
    assert result == expected


def test_find_available_meta_tasks_with_invalid_and_valid_files(tmp_path: Path):
    """Test find_available_meta_tasks with a mix of valid, invalid, and non-file entries."""
    meta_prompt_dir = tmp_path / "meta_prompts"
    meta_prompt_dir.mkdir()

    valid_file = meta_prompt_dir / "meta-prompt-real-meta.txt"
    valid_file.write_text("valid content")

    # Invalid names or extensions
    (meta_prompt_dir / "notmetaprompt-task.txt").write_text("invalid prefix")
    (meta_prompt_dir / "meta-prompt-invalid.md").write_text("invalid extension")
    (meta_prompt_dir / "meta-prompt-.txt").write_text(
        "stem 'meta-prompt-' results in empty task name"
    )
    (meta_prompt_dir / "another.txt").write_text("not matching pattern")

    # A directory that matches the pattern (should be ignored by is_file)
    (meta_prompt_dir / "meta-prompt-a-directory.txt").mkdir()

    expected = {"real-meta": valid_file.resolve()}
    assert find_available_meta_tasks(meta_prompt_dir) == expected


# --- Interactive Task Selection Tests (AC4 #47) ---


def test_prompt_user_to_select_task_valid_choice_first(mocker: Any, capsys: Any):
    """Test selecting the first task with valid numeric input."""
    mock_input = mocker.patch("builtins.input")
    mock_input.return_value = (
        "1"  # Corresponds to SORTED_MOCK_TASK_NAMES_FOR_PROMPT_TESTS[0]
    )

    selected_task = prompt_user_to_select_task(MOCK_TASKS_DICT_FOR_PROMPT_TESTS)

    assert selected_task == SORTED_MOCK_TASK_NAMES_FOR_PROMPT_TESTS[0]

    captured = capsys.readouterr()
    expected_menu = "\nPlease choose a task to perform:\n"
    for i, task_name in enumerate(SORTED_MOCK_TASK_NAMES_FOR_PROMPT_TESTS):
        expected_menu += f"  {i + 1}: {task_name}\n"
    expected_menu += "  q: Quit\n"

    assert expected_menu in captured.out
    assert (
        f"  You selected task: {SORTED_MOCK_TASK_NAMES_FOR_PROMPT_TESTS[0]}\n"
        in captured.out
    )
    mock_input.assert_called_once_with(
        "Enter the number of the task (or 'q' to quit): "
    )


def test_prompt_user_to_select_task_valid_choice_last(mocker: Any, capsys: Any):
    """Test selecting the last task with valid numeric input."""
    mock_input = mocker.patch("builtins.input")
    last_task_index_str = str(len(SORTED_MOCK_TASK_NAMES_FOR_PROMPT_TESTS))
    mock_input.return_value = last_task_index_str

    selected_task = prompt_user_to_select_task(MOCK_TASKS_DICT_FOR_PROMPT_TESTS)

    expected_task_name = SORTED_MOCK_TASK_NAMES_FOR_PROMPT_TESTS[-1]
    assert selected_task == expected_task_name

    captured = capsys.readouterr()
    assert f"  You selected task: {expected_task_name}\n" in captured.out
    mock_input.assert_called_once_with(
        "Enter the number of the task (or 'q' to quit): "
    )


def test_prompt_user_to_select_task_quit_lower(mocker: Any, capsys: Any):
    """Test quitting the selection with 'q'."""
    mock_input = mocker.patch("builtins.input")
    mock_input.return_value = "q"

    selected_task = prompt_user_to_select_task(MOCK_TASKS_DICT_FOR_PROMPT_TESTS)

    assert selected_task is None

    captured = capsys.readouterr()
    assert "You selected task:" not in captured.out  # No selection confirmation
    mock_input.assert_called_once_with(
        "Enter the number of the task (or 'q' to quit): "
    )


def test_prompt_user_to_select_task_quit_upper(mocker: Any, capsys: Any):
    """Test quitting the selection with 'Q' (case-insensitivity)."""
    mock_input = mocker.patch("builtins.input")
    mock_input.return_value = "Q"

    selected_task = prompt_user_to_select_task(MOCK_TASKS_DICT_FOR_PROMPT_TESTS)
    assert selected_task is None
    mock_input.assert_called_once_with(
        "Enter the number of the task (or 'q' to quit): "
    )


def test_prompt_user_to_select_task_invalid_text_then_valid(mocker: Any, capsys: Any):
    """Test providing invalid text input, then a valid numeric input."""
    mock_input = mocker.patch("builtins.input")
    mock_input.side_effect = ["sometext", "2"]  # Invalid, then 2nd task

    valid_selection_index = 1  # 0-indexed for "2"
    expected_task_name = SORTED_MOCK_TASK_NAMES_FOR_PROMPT_TESTS[valid_selection_index]

    selected_task = prompt_user_to_select_task(MOCK_TASKS_DICT_FOR_PROMPT_TESTS)

    assert selected_task == expected_task_name

    captured = capsys.readouterr()
    assert "  Invalid input. Please enter a number or 'q'.\n" in captured.out
    assert f"  You selected task: {expected_task_name}\n" in captured.out
    assert mock_input.call_count == 2


def test_prompt_user_to_select_task_number_too_low_then_valid(mocker: Any, capsys: Any):
    """Test providing an out-of-bounds (too low) number, then a valid one."""
    mock_input = mocker.patch("builtins.input")
    mock_input.side_effect = ["0", "3"]  # Invalid (0), then 3rd task

    valid_selection_index = 2  # 0-indexed for "3"
    expected_task_name = SORTED_MOCK_TASK_NAMES_FOR_PROMPT_TESTS[valid_selection_index]

    selected_task = prompt_user_to_select_task(MOCK_TASKS_DICT_FOR_PROMPT_TESTS)

    assert selected_task == expected_task_name

    captured = capsys.readouterr()
    assert "  Invalid number. Please try again.\n" in captured.out
    assert f"  You selected task: {expected_task_name}\n" in captured.out
    assert mock_input.call_count == 2


def test_prompt_user_to_select_task_number_too_high_then_valid(
    mocker: Any, capsys: Any
):
    """Test providing an out-of-bounds (too high) number, then a valid one."""
    mock_input = mocker.patch("builtins.input")
    num_tasks = len(SORTED_MOCK_TASK_NAMES_FOR_PROMPT_TESTS)
    invalid_high_number = str(num_tasks + 1)  # e.g., "4" if 3 tasks
    mock_input.side_effect = [invalid_high_number, "1"]  # Invalid, then 1st task

    valid_selection_index = 0  # 0-indexed for "1"
    expected_task_name = SORTED_MOCK_TASK_NAMES_FOR_PROMPT_TESTS[valid_selection_index]

    selected_task = prompt_user_to_select_task(MOCK_TASKS_DICT_FOR_PROMPT_TESTS)

    assert selected_task == expected_task_name

    captured = capsys.readouterr()
    assert "  Invalid number. Please try again.\n" in captured.out
    assert f"  You selected task: {expected_task_name}\n" in captured.out
    assert mock_input.call_count == 2


def test_prompt_user_to_select_task_empty_input_then_valid(mocker: Any, capsys: Any):
    """Test providing empty input (Enter key), then a valid one."""
    mock_input = mocker.patch("builtins.input")
    mock_input.side_effect = ["", "2"]  # Empty string, then 2nd task

    valid_selection_index = 1  # 0-indexed for "2"
    expected_task_name = SORTED_MOCK_TASK_NAMES_FOR_PROMPT_TESTS[valid_selection_index]

    selected_task = prompt_user_to_select_task(MOCK_TASKS_DICT_FOR_PROMPT_TESTS)

    assert selected_task == expected_task_name

    captured = capsys.readouterr()
    # Empty input is treated as invalid text
    assert "  Invalid input. Please enter a number or 'q'.\n" in captured.out
    assert f"  You selected task: {expected_task_name}\n" in captured.out
    assert mock_input.call_count == 2


# --- Template Loading and Filling Tests (AC5 #47) ---


def test_load_and_fill_template_basic_replacement(tmp_path: Path):
    """Test basic placeholder replacement."""
    template_content = "Hello __NAME__! Version __VERSION__."
    template_file = tmp_path / "template1.txt"
    template_file.write_text(template_content)
    variables = {"NAME": "User", "VERSION": "1.0"}

    result = load_and_fill_template(template_file, variables)
    assert result == "Hello User! Version 1.0."


def test_load_and_fill_template_variable_missing(tmp_path: Path):
    """Test when a variable in the template is not in the variables dictionary."""
    template_content = "Data: __REQUIRED_DATA__, Optional: __OPTIONAL_DATA__."
    template_file = tmp_path / "template2.txt"
    template_file.write_text(template_content)
    variables = {"REQUIRED_DATA": "Important"}


def load_and_fill_template(template_path: Path, variables: Dict[str, str]) -> str:
    """Load a prompt/meta-prompt template and replace placeholders."""
    try:
        content = template_path.read_text(encoding="utf-8")

        def replace_match(match: re.Match[str]) -> str:
            var_name = match.group(1)
            return str(variables.get(var_name, ""))

        filled_content = re.sub(r"__([A-Z0-9_]+)__", replace_match, content)
        return filled_content
    except FileNotFoundError:
        print(f"Error: Template file not found: {template_path}", file=sys.stderr)
        return ""
    except Exception as e:
        print(
            f"Error reading/processing template {template_path}: {e}", file=sys.stderr
        )
        return ""


def test_load_and_fill_template_no_variables_in_template(tmp_path: Path):
    """Test a template with no placeholders."""
    template_content = "This is static text."
    template_file = tmp_path / "template3.txt"
    template_file.write_text(template_content)
    variables = {"UNUSED_VAR": "Value"}

    result = load_and_fill_template(template_file, variables)
    assert result == "This is static text."


def test_load_and_fill_template_empty_variables_dictionary(tmp_path: Path):
    """Test when the variables dictionary is empty but the template has placeholders."""
    template_content = "Value: __TOKEN1__, Another: __TOKEN2__."
    template_file = tmp_path / "template4.txt"
    template_file.write_text(template_content)
    variables: Dict[str, str] = {}  # Explicitly typed empty dict

    result = load_and_fill_template(template_file, variables)
    assert result == "Value: , Another: ."


def test_load_and_fill_template_variable_types(tmp_path: Path):
    """Test if non-string variables are converted to string during replacement."""
    template_content = "Count: __COUNT__, Flag: __IS_READY__."
    template_file = tmp_path / "template5.txt"
    template_file.write_text(template_content)
    # Type of variables in load_and_fill_template is Dict[str, str],
    # but the function uses str(variables.get(...)), so we test with non-str values.
    variables_mixed_types: Dict[str, Any] = {"COUNT": 123, "IS_READY": True}

    # Cast to Dict[str, str] for the function call, simulating how it might be used
    # if variables were constructed from various sources. The internal str() handles it.
    result = load_and_fill_template(
        template_file, {k: str(v) for k, v in variables_mixed_types.items()}
    )
    assert result == "Count: 123, Flag: True."


def test_load_and_fill_template_placeholder_format_and_case(tmp_path: Path):
    """Test that only __UPPER_CASE_SNAKE__ placeholders are replaced."""
    template_content = (
        "Valid: __VALID_VAR__, Invalid1: __invalid_var__, "
        "Invalid2: __MixedCase__, Invalid3: _SINGLE_UNDERSCORES_, "
        "Valid2: __ANOTHER_VALID__."
    )
    template_file = tmp_path / "template6.txt"
    template_file.write_text(template_content)
    variables = {
        "VALID_VAR": "Replaced1",
        "invalid_var": "NotThis1",
        "MixedCase": "NotThis2",
        "SINGLE_UNDERSCORES": "NotThis3",
        "ANOTHER_VALID": "Replaced2",
    }

    result = load_and_fill_template(template_file, variables)
    expected = (
        "Valid: Replaced1, Invalid1: __invalid_var__, "
        "Invalid2: __MixedCase__, Invalid3: _SINGLE_UNDERSCORES_, "
        "Valid2: Replaced2."
    )
    assert result == expected


def test_load_and_fill_template_file_not_found(tmp_path: Path, capsys: Any):
    """Test behavior when the template file does not exist."""
    non_existent_file = tmp_path / "non_existent_template.txt"
    variables: Dict[str, str] = {}

    result = load_and_fill_template(non_existent_file, variables)
    assert result == ""  # Expect empty string on error

    captured = capsys.readouterr()
    assert f"Error: Template file not found: {non_existent_file}" in captured.err
    # Further check for the specific "Error reading/processing template" might be too brittle
    # if the error message format changes slightly. The main point is it handles it.


def test_load_and_fill_template_special_regex_chars_in_content(tmp_path: Path):
    """Test that special regex characters in template content are preserved."""
    template_content = "Text with (parentheses) and [brackets]. Value: __VALUE__."
    template_file = tmp_path / "template7.txt"
    template_file.write_text(template_content)
    variables = {"VALUE": "Test"}

    result = load_and_fill_template(template_file, variables)
    assert result == "Text with (parentheses) and [brackets]. Value: Test."


def test_load_and_fill_template_placeholder_at_start_and_end(tmp_path: Path):
    """Test placeholders at the very start and end of the template string."""
    template_content = "__START__ text __END__"
    template_file = tmp_path / "template8.txt"
    template_file.write_text(template_content)
    variables = {"START": "Begin", "END": "Finish"}

    result = load_and_fill_template(template_file, variables)
    assert result == "Begin text Finish"


def test_load_and_fill_template_empty_template_file(tmp_path: Path):
    """Test with an empty template file."""
    template_file = tmp_path / "empty_template.txt"
    template_file.write_text("")
    variables = {"VAR": "some_value"}

    result = load_and_fill_template(template_file, variables)
    assert result == ""
