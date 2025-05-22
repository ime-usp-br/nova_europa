# tests/python/tasks/test_llm_task_manifest_summary.py
import pytest
import argparse
import json
from unittest.mock import patch, MagicMock, call

import sys
from pathlib import Path

_project_root_dir_for_task_test = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root_dir_for_task_test) not in sys.path:
    sys.path.insert(0, str(_project_root_dir_for_task_test))

from scripts.tasks import llm_task_manifest_summary
from scripts.llm_core import (
    config as task_core_config,
)  # Alias para o config usado no script da task
from scripts.llm_core import io_utils  # Para mockar parse_summaries_from_response


def test_add_task_specific_args():
    """Testa se os argumentos específicos da tarefa 'manifest-summary' são adicionados ao parser."""
    parser = argparse.ArgumentParser()
    llm_task_manifest_summary.add_task_specific_args(parser)

    action_dests = [action.dest for action in parser._actions]
    assert "manifest_path" in action_dests
    assert "force_summary" in action_dests
    assert "max_files_per_call" in action_dests

    args_default = parser.parse_args([])
    assert args_default.manifest_path is None
    assert args_default.force_summary == []
    assert (
        args_default.max_files_per_call
        == task_core_config.DEFAULT_MAX_FILES_PER_SUMMARY_CALL
    )

    args_custom = parser.parse_args(
        [
            "--manifest-path",
            "path/to/manifest.json",
            "--force-summary",
            "file1.md",
            "--force-summary",
            "app/file2.php",
            "--max-files-per-call",
            "5",
        ]
    )
    assert args_custom.manifest_path == "path/to/manifest.json"
    assert args_custom.force_summary == ["file1.md", "app/file2.php"]
    assert args_custom.max_files_per_call == 5


# Adicionar mais testes para:
# - Fluxo de duas etapas para manifest-summary
# - --force-summary
# - Cenários onde a API falha
# - Diferentes tamanhos de lote
# - Nenhum arquivo precisando de sumário
