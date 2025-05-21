# tests/python/test_llm_core_prompts.py
import pytest
from pathlib import Path
from scripts.llm_core import prompts as core_prompts_module
from scripts.llm_core import config as core_config  # Importar para monkeypatch


# Testes para load_and_fill_template
def test_load_and_fill_template_basic_replacement(tmp_path: Path):
    template_content = "Hello __NAME__! Welcome to __PROJECT__."
    template_file = tmp_path / "test_template.txt"
    template_file.write_text(template_content)
    variables = {"NAME": "User", "PROJECT": "AwesomeApp"}
    expected_output = "Hello User! Welcome to AwesomeApp."
    assert (
        core_prompts_module.load_and_fill_template(template_file, variables)
        == expected_output
    )


def test_load_and_fill_template_missing_variable(tmp_path: Path):
    template_content = "Value: __VALUE__, Defaulting: __MISSING__."
    template_file = tmp_path / "test_template.txt"
    template_file.write_text(template_content)
    variables = {"VALUE": "123"}
    expected_output = "Value: 123, Defaulting: ."
    assert (
        core_prompts_module.load_and_fill_template(template_file, variables)
        == expected_output
    )


def test_load_and_fill_template_no_placeholders(tmp_path: Path):
    template_content = "This is a static template."
    template_file = tmp_path / "test_template.txt"
    template_file.write_text(template_content)
    variables = {"UNUSED": "data"}
    assert (
        core_prompts_module.load_and_fill_template(template_file, variables)
        == template_content
    )


def test_load_and_fill_template_file_not_found(tmp_path: Path):
    non_existent_file = tmp_path / "non_existent.txt"
    variables = {}
    result = core_prompts_module.load_and_fill_template(non_existent_file, variables)
    assert result == ""


# Testes para modify_prompt_with_observation
def test_modify_prompt_with_observation_adds_feedback():
    original_prompt = "Original prompt text."
    observation = "This is important feedback."
    expected_suffix = "\n\n--- USER FEEDBACK FOR RETRY ---\nThis is important feedback.\n--- END FEEDBACK ---"
    modified = core_prompts_module.modify_prompt_with_observation(
        original_prompt, observation
    )
    assert modified == original_prompt + expected_suffix


def test_modify_prompt_with_no_observation():
    original_prompt = "Original prompt text."
    modified = core_prompts_module.modify_prompt_with_observation(original_prompt, None)
    assert modified == original_prompt
    modified_empty = core_prompts_module.modify_prompt_with_observation(
        original_prompt, ""
    )
    assert modified_empty == original_prompt


# Testes para find_context_selector_prompt
@pytest.fixture
def setup_selector_prompts_env(tmp_path: Path, monkeypatch):
    """
    Cria arquivos de prompt seletores de contexto temporários e
    monkeypatches CONTEXT_SELECTORS_DIR e PROJECT_ROOT para os testes.
    """
    # Define o PROJECT_ROOT para o tmp_path para este conjunto de testes
    original_project_root = core_config.PROJECT_ROOT
    monkeypatch.setattr(core_config, "PROJECT_ROOT", tmp_path)

    # Cria os diretórios de template DENTRO de tmp_path
    # O caminho relativo para CONTEXT_SELECTORS_DIR será agora relativo a tmp_path
    selectors_dir_relative_to_mocked_root = Path("templates") / "context_selectors"
    selectors_dir_absolute_in_tmp = tmp_path / selectors_dir_relative_to_mocked_root
    selectors_dir_absolute_in_tmp.mkdir(parents=True, exist_ok=True)

    # Monkeypatch a constante CONTEXT_SELECTORS_DIR no módulo config
    # para apontar para o diretório de seletores de contexto de teste.
    original_context_selectors_dir = core_config.CONTEXT_SELECTORS_DIR
    monkeypatch.setattr(
        core_config, "CONTEXT_SELECTORS_DIR", selectors_dir_absolute_in_tmp
    )

    (
        selectors_dir_absolute_in_tmp / "select-context-for-resolve-ac-1stage.txt"
    ).write_text("1stage resolve content")
    (
        selectors_dir_absolute_in_tmp / "select-context-for-resolve-ac-2stages.txt"
    ).write_text("2stages resolve content")
    (selectors_dir_absolute_in_tmp / "select-context-for-commit-mesage.txt").write_text(
        "commit fallback content"
    )

    # Retorna o diretório base dos seletores de contexto mockado para verificações
    yield selectors_dir_absolute_in_tmp

    # Restaura as constantes originais após os testes
    monkeypatch.setattr(core_config, "PROJECT_ROOT", original_project_root)
    monkeypatch.setattr(
        core_config, "CONTEXT_SELECTORS_DIR", original_context_selectors_dir
    )


def test_find_context_selector_prompt_1stage(setup_selector_prompts_env):
    selectors_dir_mocked = setup_selector_prompts_env
    expected_path = selectors_dir_mocked / "select-context-for-resolve-ac-1stage.txt"
    found_path = core_prompts_module.find_context_selector_prompt("resolve-ac", False)
    assert found_path == expected_path


def test_find_context_selector_prompt_2stages(setup_selector_prompts_env):
    selectors_dir_mocked = setup_selector_prompts_env
    expected_path = selectors_dir_mocked / "select-context-for-resolve-ac-2stages.txt"
    found_path = core_prompts_module.find_context_selector_prompt("resolve-ac", True)
    assert found_path == expected_path


def test_find_context_selector_prompt_fallback(setup_selector_prompts_env):
    selectors_dir_mocked = setup_selector_prompts_env
    expected_path = selectors_dir_mocked / "select-context-for-commit-mesage.txt"
    # Teste com False
    found_path_false = core_prompts_module.find_context_selector_prompt(
        "commit-mesage", False
    )
    assert found_path_false == expected_path
    # Teste com True
    found_path_true = core_prompts_module.find_context_selector_prompt(
        "commit-mesage", True
    )
    assert found_path_true == expected_path


def test_find_context_selector_prompt_not_found(setup_selector_prompts_env):
    # setup_selector_prompts_env é necessário para mockar core_config.CONTEXT_SELECTORS_DIR
    # para um diretório vazio (ou um onde o arquivo não existe)
    assert (
        core_prompts_module.find_context_selector_prompt("non-existent-task", False)
        is None
    )
    assert (
        core_prompts_module.find_context_selector_prompt("non-existent-task", True)
        is None
    )
