# -*- coding: utf-8 -*-
"""
LLM Core Configuration Module.

This module stores all global constants for the LLM interaction scripts.
"""
from pathlib import Path
import os
from typing import Dict, List, Optional, Any, Set, Tuple, Union # Added Dict, Any

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
    "gemini-2.5-pro-preview-05-06": 250000,
    "gemini-2.0-flash": 250000,
    "gemini-2.0-flash-lite": 250000,
    "gemini-1.5-flash": 250000,
    "gemini-1.5-pro": 250000,
    # Default to a conservative value if model not listed
    "default": 250000
}
DEFAULT_OUTPUT_TOKEN_ESTIMATE = 8192 # Default estimate for model output tokens
DEFAULT_TOKEN_SAFETY_BUFFER = 2048   # Buffer to avoid hitting hard limits


# Delimiters and Constants
WEB_SEARCH_ENCOURAGEMENT_PT = "\n\nPara garantir a melhor resposta possível, sinta-se à vontade para pesquisar na internet usando a ferramenta de busca disponível."
DEFAULT_BASE_BRANCH = "main"
PR_CONTENT_DELIMITER_TITLE = "--- PR TITLE ---"
PR_CONTENT_DELIMITER_BODY = "--- PR BODY ---"
SUMMARY_CONTENT_DELIMITER_START = "--- START OF FILE " # Note o espaço
SUMMARY_CONTENT_DELIMITER_END = "--- END OF FILE "   # Note o espaço
ESSENTIAL_CONTENT_DELIMITER_START = "--- START OF ESSENTIAL FILE "
ESSENTIAL_CONTENT_DELIMITER_END = "--- END OF ESSENTIAL FILE "


# Numeric Constants
SUMMARY_TOKEN_LIMIT_PER_CALL = 200000  # Example limit for batching summaries
ESTIMATED_TOKENS_PER_SUMMARY = 200  # Rough estimate for a single summary
SLEEP_DURATION_SECONDS = 1  # Default sleep duration for rate limiting
DEFAULT_API_TIMEOUT_SECONDS = 300 # Default timeout for Gemini API calls
MANIFEST_MAX_TOKEN_FILTER = 200000
DEFAULT_MAX_FILES_PER_SUMMARY_CALL = 10
MAX_ESSENTIAL_TOKENS_FOR_SELECTOR_CALL = 75000 # Max tokens for pre-injected essential content
# Limite de tokens para a chamada da LLM seletora (modelo flash).
# Deve ser menor que o limite do modelo flash (ex: 1M para gemini-1.5-flash)
# para acomodar o prompt seletor e o JSON dos sumários.
SELECTOR_LLM_MAX_INPUT_TOKENS = 200000 # Exemplo, ajuste conforme necessário

# Default values for arguments
DEFAULT_TARGET_BRANCH = "main"
DEFAULT_MAX_FILES_PER_CALL_SUMMARY = 10
DEFAULT_CONTEXT_GENERATION_TIMEOUT = 600 # 10 minutes
DEFAULT_GH_PROJECT_NUMBER = os.getenv("GH_PROJECT_NUMBER", "1")
DEFAULT_GH_PROJECT_OWNER = os.getenv("GH_PROJECT_OWNER", "@me")
DEFAULT_GH_PROJECT_STATUS_FIELD_NAME = os.getenv("GH_PROJECT_STATUS_FIELD_NAME", "Status")
DEFAULT_RATE_LIMIT_SLEEP = 60

# Mapeamento de tarefas e seus argumentos para arquivos essenciais
# Chave: nome da tarefa (como usado no dispatcher llm_interact.py)
# Valor: dicionário com chaves "args" e/ou "static"
#   "args": mapeia o nome do argumento (dest do argparse) para um padrão de nome de arquivo.
#           Placeholders como {arg_value} ou {nome_do_arg} devem ser usados,
#           correspondendo ao 'dest' do argumento no argparse.
#           A lógica de substituição e busca no diretório de contexto será feita pela função que usa este mapa.
#   "static": uma lista de caminhos de arquivo (relativos à raiz do projeto ou a um dir de contexto)
#             que são sempre essenciais para a tarefa. Placeholders como {latest_dir_name}
#             podem ser usados aqui também e serão resolvidos pela lógica de carregamento.
ESSENTIAL_FILES_MAP: Dict[str, Dict[str, Any]] = {
    "resolve-ac": {
        "args": {
            "issue": "context_llm/code/{latest_dir_name}/github_issue_{issue}_details.json",
            # "ac" não mapeia para um arquivo, mas é usado no prompt.
        },
        "static": [
            "docs/guia_de_desenvolvimento.md",
            "docs/padroes_codigo_boas_praticas.md",
            "context_llm/code/{latest_dir_name}/phpunit_test_results.txt",
            "context_llm/code/{latest_dir_name}/phpstan_analysis.txt",
        ],
    },
    "commit-mesage": {
        "args": {
            "issue": "context_llm/code/{latest_dir_name}/github_issue_{issue}_details.json",
        },
        "static": [
            "context_llm/code/{latest_dir_name}/git_diff_cached.txt",
            "context_llm/code/{latest_dir_name}/git_log.txt",
            "docs/guia_de_desenvolvimento.md",
        ],
    },
    "analyze-ac": {
        "args": {
            "issue": "context_llm/code/{latest_dir_name}/github_issue_{issue}_details.json",
        },
        "static": [
            "docs/guia_de_desenvolvimento.md",
            "docs/padroes_codigo_boas_praticas.md",
            "context_llm/code/{latest_dir_name}/gh_project_items_status.json",
        ],
    },
    "create-pr": {
        "args": {
            "issue": "context_llm/code/{latest_dir_name}/github_issue_{issue}_details.json",
        },
        "static": [
            "context_llm/code/{latest_dir_name}/git_diff_cached.txt", # ou o diff relevante
            "context_llm/code/{latest_dir_name}/git_log.txt", # commits do branch
            "docs/guia_de_desenvolvimento.md", # Para padrões de PR
        ],
    },
    "update-doc": {
         "args": {
            "issue": "context_llm/code/{latest_dir_name}/github_issue_{issue}_details.json",
            # doc_file é um caso especial, pois o próprio valor do argumento é o path
            # a lógica de carregamento precisará de um tratamento especial para ele.
            # Aqui, podemos apenas indicar que o argumento 'doc_file' é relevante.
            "doc_file": "{doc_file}", # O valor de args.doc_file será o próprio caminho
        },
        "static": [
            "docs/versionamento_documentacao.md",
            "CHANGELOG.md", # Para ser atualizado
            # diffs da issue
            "context_llm/code/{latest_dir_name}/git_diff_cached.txt",
        ]
    },
    # Tarefas de correção podem precisar de seus respectivos arquivos de resultado de análise
    "fix-artisan-test": {
        "static": ["context_llm/code/{latest_dir_name}/phpunit_test_results.txt"]
    },
    "fix-artisan-dusk": {
        "static": ["context_llm/code/{latest_dir_name}/dusk_test_results.txt"]
    },
    "fix-phpstan": {
        "static": ["context_llm/code/{latest_dir_name}/phpstan_analysis.txt"]
    },
    # Outras tarefas podem não ter arquivos essenciais baseados em args ou estáticos fixos,
    # dependendo primariamente do manifest.json para seleção via --select-context.
    "manifest-summary": { # Esta tarefa não usa pré-injeção, opera sobre o manifest.json que é carregado separadamente
        "static": []
    },
    "create-test-sub-issue": {
        "args": {
            "issue": "context_llm/code/{latest_dir_name}/github_issue_{issue}_details.json", # Issue pai
        },
        "static": [
            "docs/guia_de_desenvolvimento.md", # Para padrões de teste
            ".github/workflows/laravel.yml" # Para contexto de CI
        ]
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
            # O manifesto JSON mais recente é carregado pelo fluxo de --select-context
            # Se não usar --select-context, a task precisaria carregar explicitamente um manifest.json
        ]
    }
}