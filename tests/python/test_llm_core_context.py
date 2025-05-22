# tests/python/test_llm_core_context.py
import pytest
import json
from pathlib import Path
from unittest.mock import patch, mock_open, call
from scripts.llm_core import context as core_context
from scripts.llm_core import config as core_config

# ... (testes anteriores de find_latest_context_dir e load_manifest - sem alterações) ...


# Testes para find_latest_context_dir (sem alterações)
def test_find_latest_context_dir_no_dir(tmp_path: Path):
    assert core_context.find_latest_context_dir(tmp_path / "non_existent") is None


def test_find_latest_context_dir_empty_dir(tmp_path: Path):
    context_base = tmp_path / "context_base"
    context_base.mkdir()
    assert core_context.find_latest_context_dir(context_base) is None


def test_find_latest_context_dir_one_valid(tmp_path: Path):
    context_base = tmp_path / "context_base"
    context_base.mkdir()
    dir1 = context_base / "20230101_120000"
    dir1.mkdir()
    assert core_context.find_latest_context_dir(context_base) == dir1


def test_find_latest_context_dir_multiple_valid(tmp_path: Path):
    context_base = tmp_path / "context_base"
    context_base.mkdir()
    dir1 = context_base / "20230101_100000"
    dir1.mkdir()
    dir2_latest = context_base / "20230102_120000"
    dir2_latest.mkdir()
    dir3 = context_base / "20221231_235959"
    dir3.mkdir()
    assert core_context.find_latest_context_dir(context_base) == dir2_latest


def test_find_latest_context_dir_with_invalid_names(tmp_path: Path):
    context_base = tmp_path / "context_base"
    context_base.mkdir()
    dir_valid = context_base / "20230101_110000"
    dir_valid.mkdir()
    (context_base / "invalid_name").mkdir()
    (context_base / "20230101_1000").write_text("file, not dir")
    assert core_context.find_latest_context_dir(context_base) == dir_valid


# Testes para load_manifest (sem alterações)
@patch("pathlib.Path.is_file")
@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data='{"files": {"path/to/file.py": {"type": "code_python"}}}',
)
def test_load_manifest_success(mock_file_open, mock_path_is_file, tmp_path: Path):
    mock_path_is_file.return_value = True
    manifest_file = tmp_path / "data" / "20230101_120000_manifest.json"

    result = core_context.load_manifest(manifest_file)
    mock_path_is_file.assert_called_once_with()
    mock_file_open.assert_called_once_with(manifest_file, "r", encoding="utf-8")
    assert result is not None
    assert "files" in result
    assert "path/to/file.py" in result["files"]


@patch("pathlib.Path.is_file", return_value=False)
def test_load_manifest_file_not_found(mock_path_is_file, tmp_path: Path):
    non_existent_manifest = tmp_path / "ghost_manifest.json"
    result = core_context.load_manifest(non_existent_manifest)
    assert result is None
    mock_path_is_file.assert_called_once_with()


@patch("pathlib.Path.is_file", return_value=True)
@patch("builtins.open", new_callable=mock_open, read_data="invalid json")
def test_load_manifest_invalid_json(
    mock_file_invalid_json, mock_path_is_file, tmp_path: Path
):
    manifest_file = tmp_path / "invalid_format.json"
    result = core_context.load_manifest(manifest_file)
    assert result is None


@patch("pathlib.Path.is_file", return_value=True)
@patch("builtins.open", new_callable=mock_open, read_data='{"not_files_key": {}}')
def test_load_manifest_missing_files_key(
    mock_file_missing_key, mock_path_is_file, tmp_path: Path
):
    manifest_file = tmp_path / "missing_key.json"
    result = core_context.load_manifest(manifest_file)
    assert result is None


# Testes para prepare_context_parts
@patch("scripts.llm_core.context._load_files_from_dir")
def test_prepare_context_parts_default_loading(
    mock_load_from_dir, tmp_path: Path, monkeypatch
):
    monkeypatch.setattr(core_config, "PROJECT_ROOT", tmp_path)

    primary_dir = tmp_path / "context" / "code" / "20230101_120000"
    common_dir = tmp_path / "context" / "common"
    primary_dir.mkdir(parents=True, exist_ok=True)
    common_dir.mkdir(parents=True, exist_ok=True)

    core_context.prepare_context_parts(
        primary_dir,
        common_dir,
        exclude_list=None,
        manifest_data=None,
        include_list=None,
    )

    assert mock_load_from_dir.call_count == 2
    mock_load_from_dir.assert_any_call(primary_dir, [], None, None)
    mock_load_from_dir.assert_any_call(common_dir, [], None, None)
