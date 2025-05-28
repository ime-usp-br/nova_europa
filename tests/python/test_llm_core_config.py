# tests/python/test_llm_core_config.py
import pytest
from pathlib import Path
from scripts.llm_core import config as core_config
import os # Para testar os valores de os.getenv


@pytest.fixture(autouse=True)
def mock_config_paths_in_tmp(tmp_path: Path, monkeypatch):
    """
    Mocks PROJECT_ROOT and all derived path constants in core_config to use tmp_path.
    Creates expected directory structures within tmp_path for these tests.
    This fixture is applied automatically to all tests in this file.
    """
    # 1. Mock PROJECT_ROOT
    monkeypatch.setattr(core_config, "PROJECT_ROOT", tmp_path)

    # 2. Re-calculate and mock all other path constants that depend on PROJECT_ROOT
    #    These new paths will be relative to tmp_path.
    mocked_template_dir = tmp_path / "templates" / "prompts"
    mocked_meta_prompt_dir = tmp_path / "templates" / "meta-prompts"
    mocked_context_selectors_dir = tmp_path / "templates" / "context_selectors"
    mocked_context_dir_base = tmp_path / "context_llm" / "code"
    mocked_common_context_dir = tmp_path / "context_llm" / "common"
    mocked_output_dir_base = tmp_path / "llm_outputs"
    mocked_context_generation_script = tmp_path / "scripts" / "generate_context.py"
    mocked_manifest_data_dir = tmp_path / "scripts" / "data"

    monkeypatch.setattr(core_config, "TEMPLATE_DIR", mocked_template_dir)
    monkeypatch.setattr(core_config, "META_PROMPT_DIR", mocked_meta_prompt_dir)
    monkeypatch.setattr(
        core_config, "CONTEXT_SELECTORS_DIR", mocked_context_selectors_dir
    )
    monkeypatch.setattr(core_config, "CONTEXT_DIR_BASE", mocked_context_dir_base)
    monkeypatch.setattr(core_config, "COMMON_CONTEXT_DIR", mocked_common_context_dir)
    monkeypatch.setattr(core_config, "OUTPUT_DIR_BASE", mocked_output_dir_base)
    monkeypatch.setattr(
        core_config, "CONTEXT_GENERATION_SCRIPT", mocked_context_generation_script
    )
    monkeypatch.setattr(core_config, "MANIFEST_DATA_DIR", mocked_manifest_data_dir)

    # 3. Create the directory structure that the config tests expect,
    #    relative to the mocked PROJECT_ROOT (which is tmp_path).
    mocked_template_dir.parent.mkdir(parents=True, exist_ok=True)  # templates/
    mocked_template_dir.mkdir(exist_ok=True)  # templates/prompts/
    mocked_meta_prompt_dir.mkdir(exist_ok=True)  # templates/meta-prompts/
    mocked_context_selectors_dir.mkdir(exist_ok=True)  # templates/context_selectors/

    mocked_context_dir_base.parent.mkdir(parents=True, exist_ok=True)  # context_llm/
    # CONTEXT_DIR_BASE (context_llm/code) é criado dinamicamente pelos scripts, não precisa existir para teste de config.
    mocked_common_context_dir.mkdir(parents=True, exist_ok=True)  # context_llm/common/

    mocked_output_dir_base.parent.mkdir(exist_ok=True)  # PROJECT_ROOT (tmp_path)
    # OUTPUT_DIR_BASE (llm_outputs) é criado dinamicamente, não precisa existir para teste de config.

    mocked_context_generation_script.parent.mkdir(
        parents=True, exist_ok=True
    )  # scripts/
    mocked_context_generation_script.touch()  # scripts/generate_context.py

    mocked_manifest_data_dir.mkdir(parents=True, exist_ok=True)  # scripts/data/

    return tmp_path


def test_project_root_is_correct(mock_config_paths_in_tmp: Path):
    """Verifica se PROJECT_ROOT (mockado) é o tmp_path."""
    assert isinstance(
        core_config.PROJECT_ROOT, Path
    ), "PROJECT_ROOT should be a Path object"
    assert (
        core_config.PROJECT_ROOT == mock_config_paths_in_tmp
    ), "PROJECT_ROOT was not correctly mocked to tmp_path"

    assert (
        core_config.PROJECT_ROOT / "scripts"
    ).is_dir(), "'scripts' directory not found in mocked PROJECT_ROOT"


def test_template_directories_exist(mock_config_paths_in_tmp: Path):
    """Verifica se os diretórios de template existem (agora dentro de tmp_path)."""
    assert (
        core_config.TEMPLATE_DIR.is_dir()
    ), f"TEMPLATE_DIR does not exist or is not a dir: {core_config.TEMPLATE_DIR}"
    assert (
        core_config.TEMPLATE_DIR == mock_config_paths_in_tmp / "templates" / "prompts"
    )
    assert (
        core_config.META_PROMPT_DIR.is_dir()
    ), f"META_PROMPT_DIR does not exist or is not a dir: {core_config.META_PROMPT_DIR}"
    assert (
        core_config.META_PROMPT_DIR
        == mock_config_paths_in_tmp / "templates" / "meta-prompts"
    )
    assert (
        core_config.CONTEXT_SELECTORS_DIR.is_dir()
    ), f"CONTEXT_SELECTORS_DIR does not exist or is not a dir: {core_config.CONTEXT_SELECTORS_DIR}"
    assert (
        core_config.CONTEXT_SELECTORS_DIR
        == mock_config_paths_in_tmp / "templates" / "context_selectors"
    )


def test_context_directories_config(mock_config_paths_in_tmp: Path):
    """Verifica a configuração dos diretórios de contexto."""
    assert isinstance(core_config.CONTEXT_DIR_BASE, Path)
    # core_config.CONTEXT_DIR_BASE será agora tmp_path / "context_llm/code"
    # Seu pai é tmp_path / "context_llm", que foi criado pelo fixture.
    assert (
        core_config.CONTEXT_DIR_BASE.parent.is_dir()
    ), f"Parent of CONTEXT_DIR_BASE should exist: {core_config.CONTEXT_DIR_BASE.parent}"
    assert (
        core_config.CONTEXT_DIR_BASE
        == mock_config_paths_in_tmp / "context_llm" / "code"
    )

    assert isinstance(core_config.COMMON_CONTEXT_DIR, Path)
    assert (
        core_config.COMMON_CONTEXT_DIR.is_dir()
    ), f"COMMON_CONTEXT_DIR should exist: {core_config.COMMON_CONTEXT_DIR}"
    assert (
        core_config.COMMON_CONTEXT_DIR
        == mock_config_paths_in_tmp / "context_llm" / "common"
    )


def test_output_directory_config(mock_config_paths_in_tmp: Path):
    """Verifica a configuração do diretório de saída."""
    assert isinstance(core_config.OUTPUT_DIR_BASE, Path)
    # OUTPUT_DIR_BASE é mockado para tmp_path / "llm_outputs"
    # Seu pai é tmp_path (que é o PROJECT_ROOT mockado).
    assert (
        core_config.OUTPUT_DIR_BASE.parent == core_config.PROJECT_ROOT
    ), f"OUTPUT_DIR_BASE.parent ({core_config.OUTPUT_DIR_BASE.parent}) should be PROJECT_ROOT ({core_config.PROJECT_ROOT})"
    assert (
        core_config.OUTPUT_DIR_BASE.parent == mock_config_paths_in_tmp
    ), f"OUTPUT_DIR_BASE.parent ({core_config.OUTPUT_DIR_BASE.parent}) should be tmp_path ({mock_config_paths_in_tmp})"
    assert core_config.OUTPUT_DIR_BASE == mock_config_paths_in_tmp / "llm_outputs"


def test_script_paths_config(mock_config_paths_in_tmp: Path):
    """Verifica os caminhos para scripts externos."""
    assert (
        core_config.CONTEXT_GENERATION_SCRIPT.is_file()
    ), f"CONTEXT_GENERATION_SCRIPT not found or not a file: {core_config.CONTEXT_GENERATION_SCRIPT}"
    assert (
        core_config.CONTEXT_GENERATION_SCRIPT
        == mock_config_paths_in_tmp / "scripts" / "generate_context.py"
    )
    assert (
        core_config.MANIFEST_DATA_DIR.is_dir()
    ), f"MANIFEST_DATA_DIR does not exist or is not a dir: {core_config.MANIFEST_DATA_DIR}"
    assert (
        core_config.MANIFEST_DATA_DIR == mock_config_paths_in_tmp / "scripts" / "data"
    )


def test_regex_constants():
    """Verifica se as constantes regex são strings."""
    assert isinstance(core_config.TIMESTAMP_DIR_REGEX, str)
    assert isinstance(core_config.TIMESTAMP_MANIFEST_REGEX, str)


def test_gemini_model_names():
    """Verifica se os nomes dos modelos Gemini são strings não vazias."""
    assert (
        isinstance(core_config.GEMINI_MODEL_GENERAL_TASKS, str)
        and core_config.GEMINI_MODEL_GENERAL_TASKS
    )
    assert (
        isinstance(core_config.GEMINI_MODEL_RESOLVE, str)
        and core_config.GEMINI_MODEL_RESOLVE
    )
    assert (
        isinstance(core_config.GEMINI_MODEL_SUMMARY, str)
        and core_config.GEMINI_MODEL_SUMMARY
    )
    assert (
        isinstance(core_config.GEMINI_MODEL_FLASH, str)
        and core_config.GEMINI_MODEL_FLASH
    )


def test_delimiter_constants():
    """Verifica se as constantes de delimitador são strings."""
    assert isinstance(core_config.WEB_SEARCH_ENCOURAGEMENT_PT, str)
    assert isinstance(core_config.DEFAULT_BASE_BRANCH, str)
    assert isinstance(core_config.PR_CONTENT_DELIMITER_TITLE, str)
    assert isinstance(core_config.PR_CONTENT_DELIMITER_BODY, str)
    assert isinstance(core_config.SUMMARY_CONTENT_DELIMITER_START, str)
    assert isinstance(core_config.SUMMARY_CONTENT_DELIMITER_END, str)
    assert isinstance(core_config.ESSENTIAL_CONTENT_DELIMITER_START, str)
    assert isinstance(core_config.ESSENTIAL_CONTENT_DELIMITER_END, str)


def test_numeric_constants():
    """Verifica tipos e valores de constantes numéricas."""
    assert (
        isinstance(core_config.SUMMARY_TOKEN_LIMIT_PER_CALL, int)
        and core_config.SUMMARY_TOKEN_LIMIT_PER_CALL > 0
    )
    assert (
        isinstance(core_config.ESTIMATED_TOKENS_PER_SUMMARY, int)
        and core_config.ESTIMATED_TOKENS_PER_SUMMARY > 0
    )
    assert (
        isinstance(core_config.SLEEP_DURATION_SECONDS, (int, float))
        and core_config.SLEEP_DURATION_SECONDS >= 0
    )
    assert (
        isinstance(core_config.DEFAULT_API_TIMEOUT_SECONDS, int)
        and core_config.DEFAULT_API_TIMEOUT_SECONDS > 0
    )
    assert (
        isinstance(core_config.MANIFEST_MAX_TOKEN_FILTER, int)
        and core_config.MANIFEST_MAX_TOKEN_FILTER > 0
    )
    assert (
        isinstance(core_config.DEFAULT_MAX_FILES_PER_SUMMARY_CALL, int)
        and core_config.DEFAULT_MAX_FILES_PER_SUMMARY_CALL > 0
    )
    assert (
        isinstance(core_config.MAX_ESSENTIAL_TOKENS_FOR_SELECTOR_CALL, int)
        and core_config.MAX_ESSENTIAL_TOKENS_FOR_SELECTOR_CALL > 0
    )
    assert (
        isinstance(core_config.SELECTOR_LLM_MAX_INPUT_TOKENS, int)
        and core_config.SELECTOR_LLM_MAX_INPUT_TOKENS > 0
    )

def test_essential_files_map_structure_and_resolve_ac_config():
    """Verifica a estrutura geral de ESSENTIAL_FILES_MAP e a configuração para resolve-ac."""
    assert isinstance(core_config.ESSENTIAL_FILES_MAP, dict), "ESSENTIAL_FILES_MAP should be a dictionary."

    # Verifica AC 1.1 - Configuração para resolve-ac
    assert "resolve-ac" in core_config.ESSENTIAL_FILES_MAP, "Task 'resolve-ac' missing in ESSENTIAL_FILES_MAP."
    resolve_ac_config = core_config.ESSENTIAL_FILES_MAP["resolve-ac"]
    assert isinstance(resolve_ac_config, dict), "'resolve-ac' entry should be a dictionary."

    assert "args" in resolve_ac_config, "'args' key missing for 'resolve-ac'."
    assert isinstance(resolve_ac_config["args"], dict), "'args' for 'resolve-ac' should be a dictionary."
    assert "issue" in resolve_ac_config["args"], "'issue' argument missing in 'resolve-ac' args."
    # AC1.1: O padrão DEVE especificar que `github_issue_<X>_details.json` é essencial.
    # O path no MAP é relativo ao PROJECT_ROOT, e o arquivo está em context_llm/code/{latest_dir_name}/
    assert resolve_ac_config["args"]["issue"] == "context_llm/code/{latest_dir_name}/github_issue_{issue}_details.json", \
        "Incorrect file pattern for 'resolve-ac' and argument 'issue'."

    assert "static" in resolve_ac_config, "'static' key missing for 'resolve-ac'."
    assert isinstance(resolve_ac_config["static"], list), "'static' for 'resolve-ac' should be a list."
    # Verifica alguns arquivos estáticos esperados para resolve-ac
    assert "docs/guia_de_desenvolvimento.md" in resolve_ac_config["static"]
    assert "context_llm/code/{latest_dir_name}/phpunit_test_results.txt" in resolve_ac_config["static"]


    # Verifica outras tarefas para garantir que a estrutura é seguida (preparação para outros ACs)
    for task_name, task_config in core_config.ESSENTIAL_FILES_MAP.items():
        assert isinstance(task_config, dict), f"Config for task '{task_name}' should be a dict."
        if "args" in task_config:
            assert isinstance(task_config["args"], dict), f"'args' for task '{task_name}' should be a dict."
            for arg_name, file_pattern in task_config["args"].items():
                assert isinstance(arg_name, str), f"Argument name for '{task_name}' should be a string."
                assert isinstance(file_pattern, str), f"File pattern for arg '{arg_name}' in '{task_name}' should be a string."
        if "static" in task_config:
            assert isinstance(task_config["static"], list), f"'static' for task '{task_name}' should be a list."
            for static_file in task_config["static"]:
                assert isinstance(static_file, str), f"Static file entry for '{task_name}' should be a string."