# -*- coding: utf-8 -*-
"""
LLM Core Configuration Module.

This module stores all global constants for the LLM interaction scripts.
"""
from pathlib import Path
import os
from typing import Dict, List, Optional, Any, Set, Tuple, Union  # Added Dict, Any

# Project Structure
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATE_DIR = PROJECT_ROOT / "templates" / "prompts"
META_PROMPT_DIR = PROJECT_ROOT / "templates" / "meta-prompts"
CONTEXT_SELECTORS_DIR = PROJECT_ROOT / "templates" / "context_selectors"
CONTEXT_DIR_BASE = PROJECT_ROOT / "context_llm" / "code"
COMMON_CONTEXT_DIR = PROJECT_ROOT / "context_llm" / "common"
OUTPUT_DIR_BASE = PROJECT_ROOT / "llm_outputs"
CONTEXT_GENERATION_SCRIPT = PROJECT_ROOT / "scripts" / "generate_context.py"
MANIFEST_DATA_DIR = PROJECT_ROOT / "scripts" / "data"

# Regex Patterns
TIMESTAMP_DIR_REGEX = r"^\d{8}_\d{6}$"
TIMESTAMP_MANIFEST_REGEX = r"^\d{8}_\d{6}_manifest\.json$"

# Gemini API Model Names & Limits
GEMINI_MODEL_GENERAL_TASKS = "gemini-2.5-flash-preview-05-20"
GEMINI_MODEL_RESOLVE = "gemini-2.5-flash-preview-05-20"
GEMINI_MODEL_SUMMARY = "gemini-2.5-flash-preview-05-20"
GEMINI_MODEL_FLASH = "gemini-2.5-flash-preview-05-20"

MODEL_INPUT_TOKEN_LIMITS: Dict[str, int] = {
    "gemini-2.5-flash-preview-05-20": 250000,
    "gemini-1.5-flash-preview-0514": 150000,  # Mantido para referência, se necessário
    "gemini-1.5-flash": 200000,  # Exemplo, verificar documentação oficial para limites corretos
    "gemini-1.5-pro": 200000,  # Exemplo, verificar documentação oficial para limites corretos
    # Default to a conservative value if model not listed
    "default": 200000,
}
DEFAULT_OUTPUT_TOKEN_ESTIMATE = 8192  # Default estimate for model output tokens
DEFAULT_TOKEN_SAFETY_BUFFER = 2048  # Buffer to avoid hitting hard limits

# Limites de RPM (Requisições Por Minuto) para modelos Gemini (Nível Gratuito como padrão)
MODEL_RPM_LIMITS: Dict[str, int] = {
    "gemini-2.5-flash-preview-05-20": 10,  # Baseado em "Pré-lançamento 04-17 do Gemini 2.5 Flash"
    "gemini-1.5-flash-preview-0514": 10,  # Mantendo consistência com o nome similar
    "gemini-1.5-flash": 15,
    "gemini-1.5-pro": 2,
    "gemini-2.0-flash": 15,
    "gemini-2.0-flash-lite": 30,
    "default": 5,  # RPM padrão conservador para modelos não listados ou não encontrados.
}


# Delimiters and Constants
WEB_SEARCH_ENCOURAGEMENT_PT = "\n\nPara garantir a melhor resposta possível, sinta-se à vontade para pesquisar na internet usando a ferramenta de busca disponível."
DEFAULT_BASE_BRANCH = "main"
PR_CONTENT_DELIMITER_TITLE = "--- PR TITLE ---"
PR_CONTENT_DELIMITER_BODY = "--- PR BODY ---"
SUMMARY_CONTENT_DELIMITER_START = "--- START OF FILE "  # Note o espaço
SUMMARY_CONTENT_DELIMITER_END = "--- END OF FILE "  # Note o espaço
ESSENTIAL_CONTENT_DELIMITER_START = "--- START OF ESSENTIAL FILE "
ESSENTIAL_CONTENT_DELIMITER_END = "--- END OF ESSENTIAL FILE "


# Numeric Constants
SUMMARY_TOKEN_LIMIT_PER_CALL = 200000  # Example limit for batching summaries
ESTIMATED_TOKENS_PER_SUMMARY = 200  # Rough estimate for a single summary
SLEEP_DURATION_SECONDS = 1  # Default sleep duration for rate limiting
DEFAULT_API_TIMEOUT_SECONDS = 300  # Default timeout for Gemini API calls
MANIFEST_MAX_TOKEN_FILTER = 200000
DEFAULT_MAX_FILES_PER_SUMMARY_CALL = 10
MAX_ESSENTIAL_TOKENS_FOR_SELECTOR_CALL = (
    120000  # Max tokens for pre-injected essential content
)
SELECTOR_LLM_MAX_INPUT_TOKENS = 200000  # Limite para a chamada da LLM seletora

# Default values for arguments
DEFAULT_TARGET_BRANCH = "main"
DEFAULT_MAX_FILES_PER_CALL_SUMMARY = 10
DEFAULT_CONTEXT_GENERATION_TIMEOUT = 600  # 10 minutes
DEFAULT_GH_PROJECT_NUMBER = os.getenv("GH_PROJECT_NUMBER", "1")
DEFAULT_GH_PROJECT_OWNER = os.getenv("GH_PROJECT_OWNER", "@me")
DEFAULT_GH_PROJECT_STATUS_FIELD_NAME = os.getenv(
    "GH_PROJECT_STATUS_FIELD_NAME", "Status"
)
DEFAULT_RATE_LIMIT_SLEEP = 60  # Sleep for errors like 429, ResourceExhausted (reactive)

ESSENTIAL_FILES_MAP: Dict[str, Dict[str, Any]] = {
    "resolve-ac": {
        "args": {
            "issue": "context_llm/code/{latest_dir_name}/github_issue_{issue}_details.json",
        },
        "static": [
            "docs/guia_de_desenvolvimento.md",
            "docs/padroes_codigo_boas_praticas.md",
            "context_llm/code/{latest_dir_name}/phpunit_test_results.txt",  # Opcional, pode não existir
            "context_llm/code/{latest_dir_name}/phpstan_analysis.txt",  # Opcional
            "context_llm/code/{latest_dir_name}/dusk_test_results.txt",  # Opcional
        ],
    },
    "commit-mesage": {
        "args": {
            "issue": "context_llm/code/{latest_dir_name}/github_issue_{issue}_details.json",  # Opcional, pode não existir
        },
        "static": [
            "context_llm/code/{latest_dir_name}/git_diff_cached.txt",
            "context_llm/code/{latest_dir_name}/git_log.txt",
            "docs/guia_de_desenvolvimento.md",
            "docs/padroes_codigo_boas_praticas.md",
        ],
    },
    "analyze-ac": {
        "args": {
            "issue": "context_llm/code/{latest_dir_name}/github_issue_{issue}_details.json",
        },
        "static": [
            "docs/guia_de_desenvolvimento.md",
            "docs/padroes_codigo_boas_praticas.md",
        ],
    },
    "create-pr": {
        "args": {
            "issue": "context_llm/code/{latest_dir_name}/github_issue_{issue}_details.json",
        },
        "static": [
            "context_llm/code/{latest_dir_name}/git_diff_cached.txt",
            "context_llm/code/{latest_dir_name}/git_log.txt",
            "docs/guia_de_desenvolvimento.md",
            "docs/padroes_codigo_boas_praticas.md",
        ],
    },
    "update-doc": {
        "args": {
            "issue": "context_llm/code/{latest_dir_name}/github_issue_{issue}_details.json",
            "doc_file": "{doc_file}",
        },
        "static": [
            "docs/versionamento_documentacao.md",
            "docs/padroes_codigo_boas_praticas.md",
            "CHANGELOG.md",
            "context_llm/code/{latest_dir_name}/git_diff_cached.txt",  # Diff da issue
        ],
    },
    "fix-artisan-test": {
        "static": [
            "context_llm/code/{latest_dir_name}/phpunit_test_results.txt",
            "docs/padroes_codigo_boas_praticas.md",
        ]
    },
    "fix-artisan-dusk": {
        "static": [
            "context_llm/code/{latest_dir_name}/dusk_test_results.txt",
            "docs/padroes_codigo_boas_praticas.md",
        ]
    },
    "fix-phpstan": {
        "static": [
            "context_llm/code/{latest_dir_name}/phpstan_analysis.txt",
            "docs/padroes_codigo_boas_praticas.md",
        ]
    },
    "manifest-summary": {"static": []},
    "create-test-sub-issue": {
        "args": {
            "issue": "context_llm/code/{latest_dir_name}/github_issue_{issue}_details.json",
        },
        "static": [
            "docs/guia_de_desenvolvimento.md",
            "docs/padroes_codigo_boas_praticas.md",
            ".github/workflows/laravel.yml",  # Opcional
        ],
    },
    "review-issue": {
        "args": {
            "issue": "context_llm/code/{latest_dir_name}/github_issue_{issue}_details.json",
        },
        "static": [
            "README.md",
            "docs/guia_de_desenvolvimento.md",
            "docs/padroes_codigo_boas_praticas.md",
            "context_llm/code/{latest_dir_name}/git_log.txt",
            "context_llm/code/{latest_dir_name}/gh_pr_list.txt",
            "context_llm/code/{latest_dir_name}/20250529_085817_manifest.json",  # Exemplo, precisa ser dinâmico se for usado assim
        ],
    },
}
