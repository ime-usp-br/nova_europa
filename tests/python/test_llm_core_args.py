# tests/python/test_llm_core_args.py
import pytest
import argparse
from scripts.llm_core import args as core_args_module

def test_get_common_arg_parser_creates_parser():
    """Testa se a função cria um objeto ArgumentParser."""
    parser = core_args_module.get_common_arg_parser("Test Description")
    assert isinstance(parser, argparse.ArgumentParser)
    assert parser.description == "Test Description"

def test_common_arg_parser_has_two_stage_flag():
    """Testa a presença e o padrão da flag --two-stage."""
    parser = core_args_module.get_common_arg_parser("Test")
    # Verifica se o argumento existe e qual seu valor padrão
    parsed_args_default = parser.parse_args([])
    assert hasattr(parsed_args_default, 'two_stage')
    assert parsed_args_default.two_stage is False

    # Verifica se a flag pode ser ativada
    parsed_args_true_long = parser.parse_args(['--two-stage'])
    assert parsed_args_true_long.two_stage is True
    parsed_args_true_short = parser.parse_args(['-ts'])
    assert parsed_args_true_short.two_stage is True

def test_common_arg_parser_has_observation_option():
    """Testa a presença e o padrão da opção --observation."""
    parser = core_args_module.get_common_arg_parser("Test")
    parsed_args_default = parser.parse_args([])
    assert hasattr(parsed_args_default, 'observation')
    assert parsed_args_default.observation == "" # Default é string vazia

    test_obs = "This is a test observation."
    parsed_args_with_value_long = parser.parse_args(['--observation', test_obs])
    assert parsed_args_with_value_long.observation == test_obs
    parsed_args_with_value_short = parser.parse_args(['-o', test_obs])
    assert parsed_args_with_value_short.observation == test_obs

def test_common_arg_parser_has_select_context_flag():
    """Testa a presença e o padrão da flag --select-context."""
    parser = core_args_module.get_common_arg_parser("Test")
    parsed_args_default = parser.parse_args([])
    assert hasattr(parsed_args_default, 'select_context')
    assert parsed_args_default.select_context is False
    parsed_args_true = parser.parse_args(['-sc'])
    assert parsed_args_true.select_context is True

def test_common_arg_parser_has_exclude_context_option():
    """Testa a presença e o padrão da opção --exclude-context (append)."""
    parser = core_args_module.get_common_arg_parser("Test")
    parsed_args_default = parser.parse_args([])
    assert hasattr(parsed_args_default, 'exclude_context')
    assert parsed_args_default.exclude_context == []

    parsed_args_single = parser.parse_args(['-ec', 'file.txt'])
    assert parsed_args_single.exclude_context == ['file.txt']

    parsed_args_multiple = parser.parse_args(['-ec', 'file1.txt', '--exclude-context', '*.log'])
    assert parsed_args_multiple.exclude_context == ['file1.txt', '*.log']

def test_common_arg_parser_has_verbose_flag():
    """Testa a presença e o padrão da flag --verbose."""
    parser = core_args_module.get_common_arg_parser("Test")
    parsed_args_default = parser.parse_args([])
    assert hasattr(parsed_args_default, 'verbose')
    assert parsed_args_default.verbose is False
    parsed_args_true = parser.parse_args(['-v'])
    assert parsed_args_true.verbose is True

# Adicionar mais testes para as outras flags comuns:
# -w/--web-search, -g/--generate-context, -y/--yes, -om/--only-meta, -op/--only-prompt, -ws/--with-sleep
