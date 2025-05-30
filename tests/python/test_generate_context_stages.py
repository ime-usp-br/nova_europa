# tests/python/test_generate_context_stages.py
import pytest
import argparse
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import sys

# Adiciona o diretório raiz do projeto (PROJECT_ROOT) ao sys.path para importações corretas
_project_root_dir_for_test = Path(__file__).resolve().parent.parent.parent
if str(_project_root_dir_for_test) not in sys.path:
    sys.path.insert(0, str(_project_root_dir_for_test))

from scripts import generate_context # Importa o módulo diretamente

# Fixture para mockar os argumentos da linha de comando
@pytest.fixture
def mock_args(monkeypatch):
    def _mock_args(stages=None, **other_args):
        default_args = {
            "output_dir": Path("context_llm/code"), # Será mockado para tmp_path
            "tree_depth": generate_context.DEFAULT_TREE_DEPTH,
            "issue_limit": generate_context.DEFAULT_GH_ISSUE_LIST_LIMIT,
            "tag_limit": generate_context.DEFAULT_GIT_TAG_LIMIT,
            "run_limit": generate_context.DEFAULT_GH_RUN_LIST_LIMIT,
            "pr_limit": generate_context.DEFAULT_GH_PR_LIST_LIMIT,
            "release_limit": generate_context.DEFAULT_GH_RELEASE_LIST_LIMIT,
            "gh_project_number": generate_context.DEFAULT_GH_PROJECT_NUMBER,
            "gh_project_owner": generate_context.DEFAULT_GH_PROJECT_OWNER,
            "gh_project_status_field": generate_context.DEFAULT_GH_PROJECT_STATUS_FIELD_NAME,
            "stages": stages
        }
        default_args.update(other_args)
        return argparse.Namespace(**default_args)
    return _mock_args


@patch("scripts.generate_context.shutil.which", return_value=True) # Assume todos os comandos existem
@patch("scripts.generate_context.subprocess.run")
def test_stages_argument_parsing(mock_subprocess_run, mock_shutil_which, tmp_path, mock_args, capsys):
    """
    Testa AC1: --stages argument e sua capacidade de aceitar uma lista.
    Verifica também se o `setup_arg_parser` e o `STAGES_CONFIG` estão corretos.
    """
    # Mockear BASE_DIR para tmp_path para isolar o teste
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(generate_context, "BASE_DIR", tmp_path)
    monkeypatch.setattr(generate_context, "DEFAULT_OUTPUT_BASE_DIR", tmp_path / "context_llm_test" / "code")
    
    # Setup
    parser = generate_context.setup_arg_parser()
    
    # 1. Teste: --stages com um estágio válido
    test_stages_single = ["git"]
    with patch.object(sys, 'argv', ['generate_context.py', '--stages'] + test_stages_single):
        args_single = parser.parse_args()
    assert args_single.stages == test_stages_single

    # 2. Teste: --stages com múltiplos estágios válidos
    test_stages_multiple = ["git", "artisan", "phpunit"]
    with patch.object(sys, 'argv', ['generate_context.py', '--stages'] + test_stages_multiple):
        args_multiple = parser.parse_args()
    assert args_multiple.stages == test_stages_multiple

    # 3. Teste: -s (alias) com um estágio
    with patch.object(sys, 'argv', ['generate_context.py', '-s', 'env']):
        args_alias = parser.parse_args()
    assert args_alias.stages == ["env"]

    # 4. Teste: --stages sem valor (deve usar default=None, que significa todos)
    with patch.object(sys, 'argv', ['generate_context.py']): # Sem --stages
        args_no_stages = parser.parse_args()
    assert args_no_stages.stages is None 

    # 5. Teste: Estágio inválido (argparse com 'choices' deve tratar isso)
    with patch.object(sys, 'argv', ['generate_context.py', '--stages', 'invalid_stage_name']):
        with pytest.raises(SystemExit) as excinfo:
            parser.parse_args()
        assert excinfo.value.code == 2 # argparse sai com 2 em erro de argumento
    
    captured = capsys.readouterr() # Para verificar a mensagem de erro do argparse
    assert "invalid choice: 'invalid_stage_name'" in captured.err.lower() or "invalid choice: 'invalid_stage_name'" in captured.out.lower()

    # 6. Verificar se todos os nomes em STAGES_CONFIG são válidos (para a opção choices)
    all_defined_stages = list(generate_context.STAGES_CONFIG.keys())
    with patch.object(sys, 'argv', ['generate_context.py', '--stages'] + all_defined_stages):
        args_all_valid = parser.parse_args()
    assert args_all_valid.stages == all_defined_stages

    # Garantir que o STAGES_CONFIG foi definido e tem chaves
    assert hasattr(generate_context, 'STAGES_CONFIG')
    assert isinstance(generate_context.STAGES_CONFIG, dict)
    assert len(generate_context.STAGES_CONFIG.keys()) > 0
    for stage_name, config in generate_context.STAGES_CONFIG.items():
        assert 'func' in config
        assert 'description' in config
        assert callable(config['func'])
        assert isinstance(config['description'], str)
        assert 'needs_cli_args' in config
        assert isinstance(config['needs_cli_args'], bool)

