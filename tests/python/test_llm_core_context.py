# tests/python/test_llm_core_context.py
import pytest
import json
import re
import argparse # Adicionado para Namespace
from pathlib import Path
from unittest.mock import patch, mock_open, call, MagicMock
from google.genai import types as genai_types
from typing import List, Optional, Dict, Any, Set, Union  # Adicionado Union

# Adiciona o diretório raiz do projeto ao sys.path para importações corretas
import sys

_project_root_dir_for_test = Path(__file__).resolve().parent.parent.parent
if str(_project_root_dir_for_test) not in sys.path:
    sys.path.insert(0, str(_project_root_dir_for_test))

from scripts.llm_core import context as core_context
from scripts.llm_core import config as core_config


# --- Testes para find_latest_context_dir ---
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


# --- Testes para load_manifest ---
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


# --- Testes para prepare_context_parts ---
def _create_tmp_file_rel_to_project_root(
    project_root: Path, relative_path_str: str, content: str
) -> Path:
    """Helper to create a temp file using a path relative to the mocked project root."""
    full_path = project_root / relative_path_str
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    return full_path


def _check_loaded_parts(
    parts: List[genai_types.Part],
    expected_relative_paths_set: Set[str],  # Alterado para Set
    manifest_data: Optional[Dict[str, Any]],
    project_root_for_test: Path,
):
    """
    Checks if the loaded parts match the expected relative paths and content.
    Compares sets for paths to be order-agnostic.
    """
    assert len(parts) == len(
        expected_relative_paths_set
    ), f"Expected {len(expected_relative_paths_set)} parts, got {len(parts)}"

    actual_relative_paths_set = set()  # Alterado para Set
    for part in parts:
        assert hasattr(part, "text"), "Part is missing 'text' attribute"
        content_match = re.match(
            r"^--- START OF FILE (.*?) ---(?:\n--- SUMMARY ---\n(.*?)\n--- END SUMMARY ---)?\n(.*?)\n--- END OF FILE \1 ---$",
            part.text,
            re.DOTALL,
        )
        assert content_match, f"Part text format is incorrect: {part.text[:200]}..."

        relative_path_str = content_match.group(1).strip()
        actual_summary_in_part = (
            content_match.group(2).strip() if content_match.group(2) else None
        )
        actual_content_in_part = content_match.group(3)

        actual_relative_paths_set.add(relative_path_str)  # Adiciona ao Set

        expected_file_path_abs = project_root_for_test / relative_path_str
        assert (
            expected_file_path_abs.is_file()
        ), f"Source file for part {relative_path_str} not found at {expected_file_path_abs}"
        expected_content = expected_file_path_abs.read_text(
            encoding="utf-8", errors="ignore"
        )
        assert (
            actual_content_in_part == expected_content
        ), f"Content mismatch for {relative_path_str}"

        if manifest_data and "files" in manifest_data:
            expected_summary_from_manifest = (
                manifest_data["files"].get(relative_path_str, {}).get("summary")
            )
            if expected_summary_from_manifest:
                assert (
                    actual_summary_in_part == expected_summary_from_manifest
                ), f"Summary mismatch for {relative_path_str}"
            else:
                assert (
                    actual_summary_in_part is None
                ), f"Unexpected summary found for {relative_path_str} when none expected from manifest"
        elif actual_summary_in_part is not None:
            pytest.fail(
                f"Unexpected summary found for {relative_path_str} when no manifest data was provided"
            )

    assert (
        actual_relative_paths_set == expected_relative_paths_set
    ), "Mismatch in loaded file paths"


@pytest.mark.parametrize(
    "scenario_name, primary_files_to_create, common_files_to_create, exclude_list, expected_loaded_paths_set, manifest_data, primary_context_dir_exists, common_context_dir_exists",
    [
        (
            "load_latest_only",
            {"latest_file1.txt": "latest1 content"},
            {},
            [],
            {"context_llm/code/{latest_dir_name}/latest_file1.txt"},
            None,
            True,
            False,
        ),
        (
            "load_common_only",
            {},
            {"common_fileA.txt": "commonA content"},
            [],
            {"context_llm/common/common_fileA.txt"},
            None,
            False,
            True,
        ),
        (
            "load_both_no_overlap",
            {"latest_file1.txt": "latest1 content"},
            {"common_fileA.txt": "commonA content"},
            [],
            {
                "context_llm/code/{latest_dir_name}/latest_file1.txt",
                "context_llm/common/common_fileA.txt",
            },
            None,
            True,
            True,
        ),
        (
            "load_with_primary_exclusions",
            {"latest_file1.txt": "latest1", "latest_file2.txt": "latest2_excl_content"},
            {"common_file1.txt": "common1"},
            ["context_llm/code/{latest_dir_name}/latest_file2.txt"],
            {
                "context_llm/common/common_file1.txt",
                "context_llm/code/{latest_dir_name}/latest_file1.txt",
            },
            None,
            True,
            True,
        ),
        (
            "load_with_common_exclusions",
            {"latest_file1.txt": "latest1"},
            {"common_file1.txt": "common1_excl_content", "common_file2.txt": "common2"},
            ["context_llm/common/common_file1.txt"],
            {
                "context_llm/common/common_file2.txt",
                "context_llm/code/{latest_dir_name}/latest_file1.txt",
            },
            None,
            True,
            True,
        ),
        (
            "load_with_mixed_exclusions",
            {"latest_file1.txt": "latest1_excl_content", "latest_file2.txt": "latest2"},
            {"common_file1.txt": "common1_excl_content", "common_file2.txt": "common2"},
            [
                "context_llm/code/{latest_dir_name}/latest_file1.txt",
                "context_llm/common/common_file1.txt",
            ],
            {
                "context_llm/common/common_file2.txt",
                "context_llm/code/{latest_dir_name}/latest_file2.txt",
            },
            None,
            True,
            True,
        ),
        (
            "load_with_exclusions_and_manifest",
            {
                "latest_main.txt": "latest main",
                "latest_excl.txt": "latest excl content",
            },
            {
                "common_main.txt": "common main",
                "common_excl.txt": "common excl content",
            },
            [
                "context_llm/common/common_excl.txt",
                "context_llm/code/{latest_dir_name}/latest_excl.txt",
            ],
            {
                "context_llm/code/{latest_dir_name}/latest_main.txt",
                "context_llm/common/common_main.txt",
            },
            {
                "files": {
                    "context_llm/code/{latest_dir_name}/latest_main.txt": {
                        "summary": "Summary for latest main"
                    },
                    "context_llm/common/common_main.txt": {
                        "summary": "Summary for common main"
                    },
                    "context_llm/code/{latest_dir_name}/latest_excl.txt": {
                        "summary": "Summary for excluded latest"
                    },
                }
            },
            True,
            True,
        ),
    ],
)
def test_prepare_context_parts_default_loading(
    tmp_path: Path,
    monkeypatch,
    scenario_name: str,
    primary_files_to_create: Dict[str, str],
    common_files_to_create: Dict[str, str],
    exclude_list: List[str],
    expected_loaded_paths_set: Set[str],
    manifest_data: Optional[Dict[str, Any]],
    primary_context_dir_exists: bool,
    common_context_dir_exists: bool,
):
    monkeypatch.setattr(core_config, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        core_config, "COMMON_CONTEXT_DIR", tmp_path / "context_llm" / "common"
    )

    latest_dir_name = "20230101_120000"
    primary_dir = tmp_path / "context_llm" / "code" / latest_dir_name
    common_dir = tmp_path / "context_llm" / "common"

    if primary_context_dir_exists:
        primary_dir.mkdir(parents=True, exist_ok=True)
        for fname, content in primary_files_to_create.items():
            _create_tmp_file_rel_to_project_root(
                tmp_path, f"context_llm/code/{latest_dir_name}/{fname}", content
            )

    if common_context_dir_exists:
        common_dir.mkdir(parents=True, exist_ok=True)
        for fname, content in common_files_to_create.items():
            _create_tmp_file_rel_to_project_root(
                tmp_path, f"context_llm/common/{fname}", content
            )

    formatted_exclude_list = [
        item.format(latest_dir_name=latest_dir_name) for item in exclude_list
    ]

    formatted_manifest_data = None
    if manifest_data and "files" in manifest_data:
        formatted_manifest_data = {"files": {}}
        for k, v in manifest_data["files"].items():
            formatted_k = k.format(latest_dir_name=latest_dir_name)
            formatted_manifest_data["files"][formatted_k] = v

    formatted_expected_paths_set = {
        s.format(latest_dir_name=latest_dir_name) for s in expected_loaded_paths_set
    }

    actual_loaded_parts = core_context.prepare_context_parts(
        primary_dir if primary_context_dir_exists else None,
        common_dir if common_context_dir_exists else None,
        exclude_list=formatted_exclude_list,
        manifest_data=formatted_manifest_data,
        include_list=None,
    )

    _check_loaded_parts(
        actual_loaded_parts,
        formatted_expected_paths_set,
        formatted_manifest_data,
        tmp_path,
    )


# --- Testes para _load_files_from_dir (que é chamado por prepare_context_parts) ---
def test_load_files_from_dir_basic_loading_and_exclusion(
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.setattr(core_config, "PROJECT_ROOT", tmp_path)
    test_dir = tmp_path / "test_context_dir"
    test_dir.mkdir()

    file1_content = "Content of file1"
    file2_content = "Content of file2 to be excluded"
    file3_content = "Content of file3.md"

    file1_rel_path = "test_context_dir/file1.txt"
    file2_rel_path = "test_context_dir/file2_excluded.txt"
    file3_rel_path = "test_context_dir/file3.md"
    file_ignored_ext_rel_path = "test_context_dir/file4.log"

    (test_dir / "file1.txt").write_text(file1_content)
    (test_dir / "file2_excluded.txt").write_text(file2_content)
    (test_dir / "file3.md").write_text(file3_content)
    (test_dir / "file4.log").write_text("log content")

    loaded_parts: List[genai_types.Part] = []
    exclude_list = [file2_rel_path]

    core_context._load_files_from_dir(
        test_dir, loaded_parts, exclude_list=exclude_list, manifest_data=None
    )

    assert len(loaded_parts) == 2

    loaded_paths = set()
    for part in loaded_parts:
        match = re.search(r"--- START OF FILE (.*?) ---", part.text)
        assert match
        loaded_paths.add(match.group(1).strip())

    assert file1_rel_path in loaded_paths
    assert file3_rel_path in loaded_paths
    assert file2_rel_path not in loaded_paths
    assert file_ignored_ext_rel_path not in loaded_paths


@patch("scripts.llm_core.context._load_files_from_dir")
def test_prepare_context_parts_with_include_list(
    mock_load_from_dir, tmp_path: Path, monkeypatch
):
    monkeypatch.setattr(core_config, "PROJECT_ROOT", tmp_path)

    include_list = ["path/to/include1.txt", "path/to/include2.json"]
    for rel_path_str in include_list:
        _create_tmp_file_rel_to_project_root(
            tmp_path, rel_path_str, f"Content of {rel_path_str}"
        )

    actual_loaded_parts = core_context.prepare_context_parts(
        primary_context_dir=None,
        common_context_dir=None,
        exclude_list=None,
        manifest_data=None,
        include_list=include_list,
    )

    mock_load_from_dir.assert_not_called()
    assert len(actual_loaded_parts) == len(include_list)

    loaded_paths_from_parts = set()
    for part in actual_loaded_parts:
        match = re.search(r"--- START OF FILE (.*?) ---", part.text)
        assert match
        loaded_paths_from_parts.add(match.group(1).strip())

    assert loaded_paths_from_parts == set(include_list)


@pytest.mark.parametrize(
    "scenario_name, files_to_create, include_list, exclude_list, expected_loaded_paths_set, manifest_data",
    [
        (
            "include_basic",
            {"inc_file1.txt": "incl1", "other.txt": "other"},
            ["inc_file1.txt"],
            [],
            {"inc_file1.txt"},
            None,
        ),
        (
            "include_with_exclusion",
            {"inc_file1.txt": "incl1", "inc_file2.txt": "incl2_excl"},
            ["inc_file1.txt", "inc_file2.txt"],
            ["inc_file2.txt"],
            {"inc_file1.txt"},
            None,
        ),
        (
            "include_non_existent",
            {"inc_file1.txt": "incl1"},
            ["inc_file1.txt", "non_existent.txt"],
            [],
            {"inc_file1.txt"},
            None,
        ),
        (
            "include_with_manifest_summaries",
            {"inc_file1.txt": "incl1", "inc_file2.txt": "incl2"},
            ["inc_file1.txt", "inc_file2.txt"],
            [],
            {"inc_file1.txt", "inc_file2.txt"},
            {
                "files": {
                    "inc_file1.txt": {"summary": "Summary for include 1"},
                    "inc_file2.txt": {"summary": "Summary for include 2"},
                }
            },
        ),
        (
            "include_and_exclude_with_manifest",
            {
                "inc_file1.txt": "incl1",
                "inc_file2_excl.txt": "incl2_excl",
                "inc_file3.txt": "incl3_content",
            },
            ["inc_file1.txt", "inc_file2_excl.txt", "inc_file3.txt"],
            ["inc_file2_excl.txt"],
            {"inc_file1.txt", "inc_file3.txt"},
            {
                "files": {
                    "inc_file1.txt": {"summary": "Summary for include 1"},
                    "inc_file2_excl.txt": {"summary": "Summary for excluded include 2"},
                    "inc_file3.txt": {"summary": "Summary for include 3"},
                }
            },
        ),
    ],
)
def test_prepare_context_parts_with_include_list_parametrized( # Renomeado para evitar conflito
    tmp_path: Path,
    monkeypatch,
    scenario_name: str,
    files_to_create: Dict[str, str],
    include_list: List[str],
    exclude_list: List[str],
    expected_loaded_paths_set: Set[str],
    manifest_data: Optional[Dict[str, Any]],
):
    monkeypatch.setattr(core_config, "PROJECT_ROOT", tmp_path)

    for rel_path_str, content in files_to_create.items():
        _create_tmp_file_rel_to_project_root(tmp_path, rel_path_str, content)

    actual_loaded_parts = core_context.prepare_context_parts(
        primary_context_dir=None,
        common_context_dir=None,
        exclude_list=exclude_list,
        manifest_data=manifest_data,
        include_list=include_list,
    )

    _check_loaded_parts(
        actual_loaded_parts,
        expected_loaded_paths_set,
        manifest_data,
        tmp_path,
    )

# --- Testes para get_essential_files_for_task (AC1.2a) ---
def test_get_essential_files_for_task_resolve_ac(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(core_config, "PROJECT_ROOT", tmp_path)
    latest_dir = "20230101_000000"
    (tmp_path / "context_llm" / "code" / latest_dir).mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs").mkdir(exist_ok=True)

    # Criar arquivos essenciais mockados
    issue_file_rel = f"context_llm/code/{latest_dir}/github_issue_123_details.json"
    _create_tmp_file_rel_to_project_root(tmp_path, issue_file_rel, '{"title": "Issue 123"}')
    _create_tmp_file_rel_to_project_root(tmp_path, "docs/guia_de_desenvolvimento.md", "Guia dev")
    
    args = argparse.Namespace(issue="123", ac="1") # Simula argumentos da CLI

    essential_paths = core_context.get_essential_files_for_task("resolve-ac", args, latest_dir, verbose=True)
    
    essential_paths_relative_str = {p.relative_to(tmp_path).as_posix() for p in essential_paths}
    
    expected_paths_str = {
        issue_file_rel,
        "docs/guia_de_desenvolvimento.md",
        # phpunit_test_results.txt e phpstan_analysis.txt não foram criados, então não devem estar na lista
    }
    assert essential_paths_relative_str == expected_paths_str

# --- Testes para load_essential_files_content (AC1.2b) ---
def test_load_essential_files_content_basic(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(core_config, "PROJECT_ROOT", tmp_path)
    file1_rel = "essentials/file1.txt"
    file2_rel = "essentials/file2.md"
    _create_tmp_file_rel_to_project_root(tmp_path, file1_rel, "Content file 1")
    _create_tmp_file_rel_to_project_root(tmp_path, file2_rel, "## Content file 2")
    
    abs_paths = [tmp_path / file1_rel, tmp_path / file2_rel]
    
    content_str, loaded_paths = core_context.load_essential_files_content(abs_paths, 10000, verbose=True)
    
    assert len(loaded_paths) == 2
    assert Path(file1_rel) in loaded_paths
    assert Path(file2_rel) in loaded_paths
    
    assert f"{core_config.ESSENTIAL_CONTENT_DELIMITER_START}{file1_rel} ---" in content_str
    assert "Content file 1" in content_str
    assert f"{core_config.ESSENTIAL_CONTENT_DELIMITER_END}{file1_rel} ---" in content_str
    assert f"{core_config.ESSENTIAL_CONTENT_DELIMITER_START}{file2_rel} ---" in content_str
    assert "## Content file 2" in content_str
    assert f"{core_config.ESSENTIAL_CONTENT_DELIMITER_END}{file2_rel} ---" in content_str

# --- Testes para prepare_payload_for_selector_llm (AC1.2d) ---
def test_prepare_payload_for_selector_llm_commit_mesage(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(core_config, "PROJECT_ROOT", tmp_path)
    latest_dir = "20230101_000000"
    context_code_dir = tmp_path / "context_llm" / "code" / latest_dir
    context_code_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs").mkdir(exist_ok=True)

    # Arquivos essenciais para commit-mesage
    diff_file_rel = f"context_llm/code/{latest_dir}/git_diff_cached.txt"
    log_file_rel = f"context_llm/code/{latest_dir}/git_log.txt"
    guia_file_rel = "docs/guia_de_desenvolvimento.md"
    
    _create_tmp_file_rel_to_project_root(tmp_path, diff_file_rel, "diff content")
    _create_tmp_file_rel_to_project_root(tmp_path, log_file_rel, "log content")
    _create_tmp_file_rel_to_project_root(tmp_path, guia_file_rel, "guia content")

    # Outro arquivo no manifesto (não essencial)
    other_file_rel = "app/MyClass.php"
    _create_tmp_file_rel_to_project_root(tmp_path, other_file_rel, "class MyClass {}")

    full_manifest_data = {
        "files": {
            diff_file_rel: {"type": "context_code_git_diff_cached", "summary": "Diff summary", "token_count": 10},
            log_file_rel: {"type": "context_code_git_log", "summary": "Log summary", "token_count": 15},
            guia_file_rel: {"type": "docs_md", "summary": "Guia summary", "token_count": 20},
            other_file_rel: {"type": "code_php", "summary": "MyClass summary", "token_count": 5}
        }
    }
    
    selector_prompt_template = "Prompt: {{ESSENTIAL_FILES_CONTENT}} \nManifesto: {{REMAINING_MANIFEST_JSON}}"
    
    args = argparse.Namespace(issue=None) # commit-mesage pode não ter issue

    payload = core_context.prepare_payload_for_selector_llm(
        "commit-mesage", args, latest_dir, full_manifest_data, selector_prompt_template, verbose=True
    )

    # Verificar se o conteúdo essencial está no payload
    assert "diff content" in payload
    assert "log content" in payload
    assert "guia content" in payload
    assert f"{core_config.ESSENTIAL_CONTENT_DELIMITER_START}{diff_file_rel} ---" in payload
    
    # Verificar se o manifesto restante está no payload e NÃO contém os essenciais
    assert "MyClass summary" in payload # Do sumário do manifesto restante
    assert diff_file_rel not in payload[payload.find("{{REMAINING_MANIFEST_JSON}}"):] # Checa se não está no JSON
    
    # Verificar se o placeholder do prompt foi substituído
    assert "Prompt: " in payload
    assert "Manifesto: " in payload
    assert "{{ESSENTIAL_FILES_CONTENT}}" not in payload
    assert "{{REMAINING_MANIFEST_JSON}}" not in payload

    # Verificar se o JSON do manifesto restante está correto
    try:
        # Extrair a parte do JSON do payload
        json_part_match = re.search(r'Manifesto: ({.*?})$', payload, re.DOTALL)
        assert json_part_match, "JSON part not found in payload"
        remaining_manifest_parsed = json.loads(json_part_match.group(1))
        assert "files" in remaining_manifest_parsed
        assert other_file_rel in remaining_manifest_parsed["files"]
        assert diff_file_rel not in remaining_manifest_parsed["files"]
        assert log_file_rel not in remaining_manifest_parsed["files"]
        assert guia_file_rel not in remaining_manifest_parsed["files"]
        assert remaining_manifest_parsed["files"][other_file_rel]["summary"] == "MyClass summary"
    except json.JSONDecodeError as e:
        pytest.fail(f"Failed to parse JSON from payload: {e}\nPayload part: {json_part_match.group(1) if json_part_match else 'Not Found'}")