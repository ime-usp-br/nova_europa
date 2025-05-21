# tests/python/test_llm_core_io_utils.py
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import datetime 
from scripts.llm_core import io_utils 
from scripts.llm_core import config as actual_core_config_module 

@patch('pathlib.Path.write_text', autospec=True) 
@patch('pathlib.Path.mkdir', autospec=True) 
def test_save_llm_response(mock_mkdir_method, mock_write_text_method, tmp_path: Path, monkeypatch):
    # Não precisamos mais de monkeypatch para OUTPUT_DIR_BASE aqui,
    # pois vamos passar o diretório diretamente para a função.
    
    test_llm_outputs_dir_for_this_test = tmp_path / "llm_outputs_test_save"
    # Não é necessário criar test_llm_outputs_dir_for_this_test aqui, 
    # a função save_llm_response (via mkdir) deve criá-lo.
    
    task_name = "test_task_save"
    response_content = "This is a test response for saving."
    
    fixed_timestamp = "20250520_180000"
    mock_datetime_module = MagicMock() 
    mock_datetime_instance = MagicMock() 
    mock_datetime_instance.strftime.return_value = fixed_timestamp
    mock_datetime_module.datetime.now.return_value = mock_datetime_instance
    
    # Patch onde 'datetime.datetime' é usado em 'io_utils'
    with patch('scripts.llm_core.io_utils.datetime', mock_datetime_module):
        # Passa o diretório de saída mockado como argumento
        io_utils.save_llm_response(task_name, response_content, output_dir_base_override=test_llm_outputs_dir_for_this_test)

    mock_mkdir_method.assert_called_once()
    mkdir_instance_path = mock_mkdir_method.call_args.args[0]
    
    expected_dir_to_create = test_llm_outputs_dir_for_this_test / task_name
    assert mkdir_instance_path == expected_dir_to_create
    assert mock_mkdir_method.call_args.kwargs == {'parents': True, 'exist_ok': True}

    mock_write_text_method.assert_called_once()
    path_obj_written_to = mock_write_text_method.call_args.args[0]
    saved_content = mock_write_text_method.call_args.args[1]
    saved_encoding = mock_write_text_method.call_args.kwargs.get('encoding')

    assert saved_content == response_content
    assert saved_encoding == 'utf-8'
    
    expected_file_path = expected_dir_to_create / f"{fixed_timestamp}.txt"
    assert path_obj_written_to == expected_file_path
    assert path_obj_written_to.parent == expected_dir_to_create


@patch('builtins.input')
def test_confirm_step(mock_input):
    # Test "yes"
    mock_input.return_value = "y"
    choice, obs = io_utils.confirm_step("Proceed?")
    assert choice == "y"
    assert obs is None

    mock_input.return_value = "Y"
    choice, obs = io_utils.confirm_step("Proceed?")
    assert choice == "y"
    assert obs is None

    mock_input.return_value = "" 
    choice, obs = io_utils.confirm_step("Proceed?")
    assert choice == "y"
    assert obs is None
    
    mock_input.return_value = "s" 
    choice, obs = io_utils.confirm_step("Proceed?")
    assert choice == "y"
    assert obs is None

    mock_input.side_effect = None 
    mock_input.side_effect = ["n", "Needs more details."]
    choice, obs = io_utils.confirm_step("Proceed?")
    assert choice == "n"
    assert obs == "Needs more details."
    
    mock_input.side_effect = None
    mock_input.side_effect = ["nao", "Needs more details."] 
    choice, obs = io_utils.confirm_step("Proceed?")
    assert choice == "n"
    assert obs == "Needs more details."

    mock_input.side_effect = None 
    mock_input.return_value = "q"
    choice, obs = io_utils.confirm_step("Proceed?")
    assert choice == "q"
    assert obs is None
    
    mock_input.return_value = "sair" 
    choice, obs = io_utils.confirm_step("Proceed?")
    assert choice == "q"
    assert obs is None

    mock_input.side_effect = None
    mock_input.side_effect = ["invalid", "y"]
    choice, obs = io_utils.confirm_step("Proceed?")
    assert choice == "y"
    assert obs is None

def test_parse_pr_content_valid():
    llm_output = f"{actual_core_config_module.PR_CONTENT_DELIMITER_TITLE}\nPR Title\n{actual_core_config_module.PR_CONTENT_DELIMITER_BODY}\nPR Body line 1.\nLine 2."
    title, body = io_utils.parse_pr_content(llm_output)
    assert title == "PR Title"
    assert body == "PR Body line 1.\nLine 2."

def test_parse_pr_content_missing_title_delimiter():
    llm_output = f"PR Title\n{actual_core_config_module.PR_CONTENT_DELIMITER_BODY}\nPR Body"
    title, body = io_utils.parse_pr_content(llm_output)
    assert title is None
    assert body is None 

def test_parse_pr_content_missing_body_delimiter():
    llm_output = f"{actual_core_config_module.PR_CONTENT_DELIMITER_TITLE}\nPR Title\nPR Body"
    title, body = io_utils.parse_pr_content(llm_output)
    assert title is None 
    assert body is None       

def test_parse_summaries_from_response_valid():
    llm_response = f"""
{actual_core_config_module.SUMMARY_CONTENT_DELIMITER_START}path/to/file1.md ---
Summary for file1.
This is its summary.
{actual_core_config_module.SUMMARY_CONTENT_DELIMITER_END}path/to/file1.md ---

Some other text.

{actual_core_config_module.SUMMARY_CONTENT_DELIMITER_START}app/code.php ---
Summary for code.
Multiple lines.
{actual_core_config_module.SUMMARY_CONTENT_DELIMITER_END}app/code.php ---
"""
    summaries = io_utils.parse_summaries_from_response(llm_response)
    assert len(summaries) == 2
    assert summaries["path/to/file1.md"] == "Summary for file1.\nThis is its summary."
    assert summaries["app/code.php"] == "Summary for code.\nMultiple lines."

def test_parse_summaries_from_response_no_matches():
    llm_response = "No summaries here."
    summaries = io_utils.parse_summaries_from_response(llm_response)
    assert len(summaries) == 0

def test_parse_summaries_from_response_empty_response():
    llm_response = ""
    summaries = io_utils.parse_summaries_from_response(llm_response)
    assert len(summaries) == 0