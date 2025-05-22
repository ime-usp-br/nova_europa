# tests/python/test_llm_core_io_utils.py
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import datetime
from scripts.llm_core import io_utils
from scripts.llm_core import (
    config as actual_core_config_module,
)  # Importando o módulo real


# Mock para core_config.PROJECT_ROOT usado nos testes
# Usamos tmp_path que é fornecido pelo pytest como a raiz do projeto mockada
@pytest.fixture
def mock_project_root(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(actual_core_config_module, "PROJECT_ROOT", tmp_path)
    return tmp_path


@patch("pathlib.Path.write_text", autospec=True)
@patch("pathlib.Path.mkdir", autospec=True)
def test_save_llm_response(
    mock_mkdir_method, mock_write_text_method, tmp_path: Path, monkeypatch
):
    # Monkeypatch a constante OUTPUT_DIR_BASE no módulo config que io_utils usa
    test_llm_outputs_dir_for_this_test = tmp_path / "llm_outputs_test_save"
    # Não precisamos criar, a função deve criar se necessário
    # monkeypatch.setattr(actual_core_config_module, 'OUTPUT_DIR_BASE', test_llm_outputs_dir_for_this_test)
    # monkeypatch.setattr(actual_core_config_module, 'PROJECT_ROOT', tmp_path) # Já feito pelo fixture

    task_name = "test_task_save"
    response_content = "This is a test response for saving."

    fixed_timestamp = "20250520_180000"
    mock_datetime_module = MagicMock()
    mock_datetime_instance = MagicMock()
    mock_datetime_instance.strftime.return_value = fixed_timestamp
    mock_datetime_module.datetime.now.return_value = mock_datetime_instance

    # Patch onde 'datetime.datetime' é usado em 'io_utils'
    with patch("scripts.llm_core.io_utils.datetime", mock_datetime_module):
        # Passa o diretório de saída mockado como argumento
        io_utils.save_llm_response(
            task_name,
            response_content,
            output_dir_base_override=test_llm_outputs_dir_for_this_test,
        )

    mock_mkdir_method.assert_called_once()
    # O primeiro argumento posicional de mkdir é o objeto Path em si.
    mkdir_instance_path = mock_mkdir_method.call_args.args[0]

    # Diretório esperado para criação
    expected_dir_to_create = test_llm_outputs_dir_for_this_test / task_name
    assert mkdir_instance_path == expected_dir_to_create
    # Verifica os argumentos nomeados de mkdir
    assert mock_mkdir_method.call_args.kwargs == {"parents": True, "exist_ok": True}

    mock_write_text_method.assert_called_once()
    # O primeiro argumento posicional de write_text é o objeto Path em si.
    path_obj_written_to = mock_write_text_method.call_args.args[0]
    # O segundo argumento posicional é o conteúdo.
    saved_content = mock_write_text_method.call_args.args[1]
    # O argumento nomeado 'encoding'.
    saved_encoding = mock_write_text_method.call_args.kwargs.get("encoding")

    assert saved_content == response_content
    assert saved_encoding == "utf-8"

    # Verifica o caminho completo do arquivo
    expected_file_path = expected_dir_to_create / f"{fixed_timestamp}.txt"
    assert path_obj_written_to == expected_file_path
    assert path_obj_written_to.parent == expected_dir_to_create


@patch("builtins.input")
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

    mock_input.return_value = ""  # Default to yes
    choice, obs = io_utils.confirm_step("Proceed?")
    assert choice == "y"
    assert obs is None

    mock_input.return_value = "s"  # Portuguese "Sim"
    choice, obs = io_utils.confirm_step("Proceed?")
    assert choice == "y"
    assert obs is None

    # Test "no" with observation
    # Precisamos resetar o side_effect se quisermos mudar o comportamento entre chamadas no mesmo teste
    mock_input.side_effect = None  # Reset side_effect
    mock_input.side_effect = ["n", "Needs more details."]
    choice, obs = io_utils.confirm_step("Proceed?")
    assert choice == "n"
    assert obs == "Needs more details."

    mock_input.side_effect = None
    mock_input.side_effect = ["nao", "Needs more details."]
    choice, obs = io_utils.confirm_step("Proceed?")
    assert choice == "n"
    assert obs == "Needs more details."

    # Test "quit"
    mock_input.side_effect = None
    mock_input.return_value = "q"
    choice, obs = io_utils.confirm_step("Proceed?")
    assert choice == "q"
    assert obs is None

    mock_input.return_value = "sair"  # Portuguese "Sair"
    choice, obs = io_utils.confirm_step("Proceed?")
    assert choice == "q"
    assert obs is None

    # Test invalid input then valid
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
    llm_output = (
        f"PR Title\n{actual_core_config_module.PR_CONTENT_DELIMITER_BODY}\nPR Body"
    )
    title, body = io_utils.parse_pr_content(llm_output)
    assert title is None
    assert body is None


def test_parse_pr_content_missing_body_delimiter():
    llm_output = (
        f"{actual_core_config_module.PR_CONTENT_DELIMITER_TITLE}\nPR Title\nPR Body"
    )
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


# Testes para find_documentation_files
def test_find_documentation_files_basic(mock_project_root: Path):
    readme_file = mock_project_root / "README.md"
    readme_file.write_text("# Main Readme")
    changelog_file = mock_project_root / "CHANGELOG.md"
    changelog_file.write_text("# Changelog")
    docs_dir = mock_project_root / "docs"
    docs_dir.mkdir()
    doc1_file = docs_dir / "guide1.md"
    doc1_file.write_text("Guide 1")
    sub_docs_dir = docs_dir / "subsection"
    sub_docs_dir.mkdir()
    doc2_file = sub_docs_dir / "guide2.md"
    doc2_file.write_text("Guide 2")
    (docs_dir / "not_doc.txt").write_text("some text")  # Should be ignored

    found_files = io_utils.find_documentation_files(mock_project_root)

    # Os caminhos retornados devem ser relativos a mock_project_root
    expected_relative_paths = sorted(
        [
            Path("README.md"),
            Path("CHANGELOG.md"),
            Path("docs/guide1.md"),
            Path("docs/subsection/guide2.md"),
        ],
        key=lambda p: str(p),
    )

    assert found_files == expected_relative_paths


def test_find_documentation_files_no_docs_dir(mock_project_root: Path):
    readme_file = mock_project_root / "README.md"
    readme_file.write_text("# Main Readme")

    found_files = io_utils.find_documentation_files(mock_project_root)
    assert found_files == [Path("README.md")]


def test_find_documentation_files_empty_project(mock_project_root: Path):
    found_files = io_utils.find_documentation_files(mock_project_root)
    assert found_files == []


# Testes para prompt_user_to_select_doc
@patch("builtins.input")
def test_prompt_user_to_select_doc_valid_choice(mock_input: MagicMock, capsys):
    doc_files = [Path("README.md"), Path("docs/guide.md")]
    mock_input.return_value = "2"  # Selects docs/guide.md

    selected = io_utils.prompt_user_to_select_doc(doc_files)
    assert selected == Path("docs/guide.md")

    captured = capsys.readouterr()
    assert "1: README.md" in captured.out
    assert "2: docs/guide.md" in captured.out
    assert "Você selecionou: docs/guide.md" in captured.out


@patch("builtins.input")
def test_prompt_user_to_select_doc_quit(mock_input: MagicMock):
    doc_files = [Path("README.md")]
    mock_input.return_value = "q"

    selected = io_utils.prompt_user_to_select_doc(doc_files)
    assert selected is None


@patch("builtins.input")
def test_prompt_user_to_select_doc_invalid_then_valid(mock_input: MagicMock, capsys):
    doc_files = [Path("README.md"), Path("docs/other.md")]
    mock_input.side_effect = [
        "invalid",
        "0",
        "3",
        "1",
    ]  # Invalid, too low, too high, then valid

    selected = io_utils.prompt_user_to_select_doc(doc_files)
    assert selected == Path("README.md")

    captured = capsys.readouterr()
    assert "Entrada inválida. Por favor, digite um número ou 'q'." in captured.out
    assert "Número inválido. Por favor, tente novamente." in captured.out  # For 0 and 3
    assert mock_input.call_count == 4


def test_prompt_user_to_select_doc_empty_list():
    selected = io_utils.prompt_user_to_select_doc([])
    assert selected is None
