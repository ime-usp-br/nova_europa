# tests/python/test_llm_core_config.py
import pytest
from pathlib import Path
from scripts.llm_core import config as core_config


def test_project_root_is_correct():
    """Verifica se PROJECT_ROOT aponta para o diretório pai de 'scripts/'."""
    # PROJECT_ROOT deve ser o diretório que contém 'scripts', 'app', 'tests', etc.
    # __file__ (este arquivo de teste) está em tests/python/
    # config.py está em scripts/llm_core/
    # PROJECT_ROOT em config.py é Path(__file__).resolve().parent.parent.parent
    # (llm_core -> scripts -> raiz_do_projeto)

    # Verifica se PROJECT_ROOT é um Path
    assert isinstance(
        core_config.PROJECT_ROOT, Path
    ), "PROJECT_ROOT should be a Path object"

    # Verifica se alguns diretórios/arquivos esperados existem relativos ao PROJECT_ROOT
    assert (
        core_config.PROJECT_ROOT / "scripts"
    ).is_dir(), "'scripts' directory not found in PROJECT_ROOT"
    assert (
        core_config.PROJECT_ROOT / "app"
    ).is_dir(), "'app' directory not found in PROJECT_ROOT"
    assert (
        core_config.PROJECT_ROOT / "tests"
    ).is_dir(), "'tests' directory not found in PROJECT_ROOT"
    assert (
        core_config.PROJECT_ROOT / "composer.json"
    ).is_file(), "'composer.json' not found in PROJECT_ROOT"


def test_template_directories_exist():
    """Verifica se os diretórios de template existem."""
    assert (
        core_config.TEMPLATE_DIR.is_dir()
    ), f"TEMPLATE_DIR does not exist: {core_config.TEMPLATE_DIR}"
    assert (
        core_config.META_PROMPT_DIR.is_dir()
    ), f"META_PROMPT_DIR does not exist: {core_config.META_PROMPT_DIR}"
    assert (
        core_config.CONTEXT_SELECTORS_DIR.is_dir()
    ), f"CONTEXT_SELECTORS_DIR does not exist: {core_config.CONTEXT_SELECTORS_DIR}"


def test_context_directories_config():
    """Verifica a configuração dos diretórios de contexto."""
    assert isinstance(core_config.CONTEXT_DIR_BASE, Path)
    # Não podemos verificar se CONTEXT_DIR_BASE existe, pois pode ser criado dinamicamente.
    # Apenas verificamos se o pai de CONTEXT_DIR_BASE/code existe.
    assert (core_config.CONTEXT_DIR_BASE.parent).is_dir()

    assert isinstance(core_config.COMMON_CONTEXT_DIR, Path)
    assert (
        core_config.COMMON_CONTEXT_DIR.is_dir()
    ), f"COMMON_CONTEXT_DIR does not exist or is not a dir: {core_config.COMMON_CONTEXT_DIR}"


def test_output_directory_config():
    """Verifica a configuração do diretório de saída."""
    assert isinstance(core_config.OUTPUT_DIR_BASE, Path)
    # O diretório base de saída pode não existir até a primeira execução, então apenas verificamos o pai.
    assert core_config.OUTPUT_DIR_BASE.parent == core_config.PROJECT_ROOT


def test_script_paths_config():
    """Verifica os caminhos para scripts externos."""
    assert (
        core_config.CONTEXT_GENERATION_SCRIPT.is_file()
    ), f"CONTEXT_GENERATION_SCRIPT not found: {core_config.CONTEXT_GENERATION_SCRIPT}"
    assert (
        core_config.MANIFEST_DATA_DIR.is_dir()
    ), f"MANIFEST_DATA_DIR does not exist or is not a dir: {core_config.MANIFEST_DATA_DIR}"


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
