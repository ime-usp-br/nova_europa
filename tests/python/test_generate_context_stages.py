# tests/python/test_generate_context_stages.py
import pytest
import argparse
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import sys
import shutil
import datetime  # Adicionado para current_run_timestamp

# Adiciona o diretório raiz do projeto (PROJECT_ROOT) ao sys.path para importações corretas
_project_root_dir_for_test = Path(__file__).resolve().parent.parent.parent
if str(_project_root_dir_for_test) not in sys.path:
    sys.path.insert(0, str(_project_root_dir_for_test))

from scripts import generate_context


@pytest.fixture
def mock_args(monkeypatch):
    def _mock_args(stages=None, **other_args):
        default_args = {
            "output_dir": Path("context_llm/code"),
            "tree_depth": generate_context.DEFAULT_TREE_DEPTH,
            "issue_limit": generate_context.DEFAULT_GH_ISSUE_LIST_LIMIT,
            "tag_limit": generate_context.DEFAULT_GIT_TAG_LIMIT,
            "run_limit": generate_context.DEFAULT_GH_RUN_LIST_LIMIT,
            "pr_limit": generate_context.DEFAULT_GH_PR_LIST_LIMIT,
            "release_limit": generate_context.DEFAULT_GH_RELEASE_LIST_LIMIT,
            "gh_project_number": generate_context.DEFAULT_GH_PROJECT_NUMBER,
            "gh_project_owner": generate_context.DEFAULT_GH_PROJECT_OWNER,
            "gh_project_status_field": generate_context.DEFAULT_GH_PROJECT_STATUS_FIELD_NAME,
            "stages": stages,
            "verbose": False,
        }
        default_args.update(other_args)
        return argparse.Namespace(**default_args)

    return _mock_args


@patch("scripts.generate_context.shutil.which", return_value=True)
@patch(
    "scripts.generate_context.subprocess.run"
)  # Este mock não será usado se run_command for mockado
def test_stages_argument_parsing(
    mock_subprocess_run, mock_shutil_which, tmp_path, mock_args, capsys
):
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(generate_context, "BASE_DIR", tmp_path)
    mock_default_output_base_dir = tmp_path / "context_llm_test" / "code"
    monkeypatch.setattr(
        generate_context, "DEFAULT_OUTPUT_BASE_DIR", mock_default_output_base_dir
    )

    parser = generate_context.setup_arg_parser()

    test_stages_single = ["git"]
    with patch.object(
        sys, "argv", ["generate_context.py", "--stages"] + test_stages_single
    ):
        args_single = parser.parse_args()
    assert args_single.stages == test_stages_single
    assert args_single.output_dir == mock_default_output_base_dir.resolve()

    test_stages_multiple = ["git", "artisan", "phpunit"]
    with patch.object(
        sys, "argv", ["generate_context.py", "--stages"] + test_stages_multiple
    ):
        args_multiple = parser.parse_args()
    assert args_multiple.stages == test_stages_multiple

    with patch.object(sys, "argv", ["generate_context.py", "-s", "env"]):
        args_alias = parser.parse_args()
    assert args_alias.stages == ["env"]

    with patch.object(sys, "argv", ["generate_context.py"]):
        args_no_stages = parser.parse_args()
    assert args_no_stages.stages is None

    with patch.object(
        sys, "argv", ["generate_context.py", "--stages", "invalid_stage_name"]
    ):
        with pytest.raises(SystemExit) as excinfo:
            parser.parse_args()
        assert excinfo.value.code == 2

    captured = capsys.readouterr()
    assert (
        "invalid choice: 'invalid_stage_name'" in captured.err.lower()
        or "invalid choice: 'invalid_stage_name'" in captured.out.lower()
    )

    all_defined_stages = list(generate_context.STAGES_CONFIG.keys())
    with patch.object(
        sys, "argv", ["generate_context.py", "--stages"] + all_defined_stages
    ):
        args_all_valid = parser.parse_args()
    assert args_all_valid.stages == all_defined_stages

    assert hasattr(generate_context, "STAGES_CONFIG")
    assert isinstance(generate_context.STAGES_CONFIG, dict)
    assert len(generate_context.STAGES_CONFIG.keys()) > 0
    for stage_name, config_val in generate_context.STAGES_CONFIG.items():
        assert "func" in config_val
        assert "description" in config_val
        assert callable(config_val["func"])
        assert isinstance(config_val["description"], str)
        assert "needs_cli_args" in config_val
        assert isinstance(config_val["needs_cli_args"], bool)
        assert "outputs" in config_val
        assert isinstance(config_val["outputs"], list)


@patch("scripts.generate_context.shutil.which", return_value=True)
@patch("scripts.generate_context.run_command")
@patch("scripts.generate_context.find_second_latest_context_dir")
@patch("scripts.generate_context.shutil.copy2")
@patch(
    "scripts.generate_context.invoke_manifest_generator"
)  # Mock para não executar o script real
@patch("scripts.generate_context.copy_latest_manifest_json")  # Mock
@patch("scripts.generate_context.generate_manifest_md")  # Mock
def test_fallback_logic_for_skipped_stages(
    mock_generate_manifest_md: MagicMock,
    mock_copy_latest_manifest: MagicMock,
    mock_invoke_manifest_gen: MagicMock,
    mock_shutil_copy2: MagicMock,
    mock_find_second_latest: MagicMock,
    mock_run_command_func: MagicMock,  # Renomeado para ser o mock da função run_command
    mock_shutil_which_func: MagicMock,
    tmp_path: Path,
    mock_args,
    capsys,
    monkeypatch,
):
    monkeypatch.setattr(generate_context, "BASE_DIR", tmp_path)
    output_base_for_script = tmp_path / "context_output_base"
    output_base_for_script.mkdir(parents=True, exist_ok=True)

    current_run_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    current_run_dir = output_base_for_script / current_run_timestamp
    # O script principal cria este diretório, então não precisamos criar aqui no teste
    # current_run_dir.mkdir(parents=True, exist_ok=True) # Removido

    previous_run_timestamp = "20230101_000000"
    previous_context_dir_mock = output_base_for_script / previous_run_timestamp
    previous_context_dir_mock.mkdir(exist_ok=True)

    (previous_context_dir_mock / "git_log.txt").write_text("old git log")
    (previous_context_dir_mock / "git_status.txt").write_text("old git status")
    # git_diff_cached.txt não existe no anterior para testar AC5.3

    mock_find_second_latest.return_value = previous_context_dir_mock

    # Configurar o mock de run_command para a chamada de generate_manifest.py
    mock_run_command_func.return_value = (
        0,
        "Mocked manifest gen stdout",
        "Mocked manifest gen stderr",
    )

    args_instance = mock_args(
        stages=["env"], output_dir=output_base_for_script, verbose=True
    )

    # Mockar as funções dos estágios para que não executem suas lógicas reais
    # e para que não chamem run_command (que já está mockado globalmente)
    original_stages_config = generate_context.STAGES_CONFIG.copy()  # Salva original

    mocked_stages_config_for_test = {}
    for stage_name, config_details in original_stages_config.items():
        new_config_details = config_details.copy()
        new_config_details["func"] = MagicMock(name=f"mock_func_{stage_name}")
        mocked_stages_config_for_test[stage_name] = new_config_details

    with patch.dict(generate_context.STAGES_CONFIG, mocked_stages_config_for_test):
        generate_context.run_all_collections(
            current_run_dir, current_run_timestamp, args_instance
        )

    mock_shutil_copy2.assert_any_call(
        previous_context_dir_mock / "git_log.txt", current_run_dir / "git_log.txt"
    )
    mock_shutil_copy2.assert_any_call(
        previous_context_dir_mock / "git_status.txt", current_run_dir / "git_status.txt"
    )

    captured = capsys.readouterr()
    assert (
        f"AVISO (AC5.3): Arquivo esperado 'git_diff_cached.txt' do estágio 'git' não encontrado em '{previous_run_timestamp}'. Não copiado."
        in captured.out
    )
    assert not (current_run_dir / "git_diff_cached.txt").exists()

    mock_find_second_latest.return_value = None
    if (current_run_dir / "git_log.txt").exists():
        (current_run_dir / "git_log.txt").unlink(missing_ok=True)  # Python 3.8+
    if (current_run_dir / "git_status.txt").exists():
        (current_run_dir / "git_status.txt").unlink(missing_ok=True)

    # Limpar mocks de chamada entre execuções de run_all_collections se necessário.
    # No entanto, para este teste, o importante é o valor de retorno de find_second_latest
    mock_shutil_copy2.reset_mock()  # Reseta contagem de chamadas para a próxima verificação

    with patch.dict(generate_context.STAGES_CONFIG, mocked_stages_config_for_test):
        generate_context.run_all_collections(
            current_run_dir, current_run_timestamp, args_instance
        )

    captured_ac6 = capsys.readouterr()
    assert (
        f"AVISO (AC6): Nenhum diretório de contexto anterior encontrado para fallback dos estágios pulados:"
        in captured_ac6.out
    )
    mock_shutil_copy2.assert_not_called()  # Não deve ter copiado nada pois não achou dir anterior

    shutil.rmtree(output_base_for_script, ignore_errors=True)

    # Restaurar STAGES_CONFIG original para não afetar outros testes
    generate_context.STAGES_CONFIG = original_stages_config
