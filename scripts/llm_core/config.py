# -*- coding: utf-8 -*-
"""
LLM Core Configuration Module.

This module stores all global constants for the LLM interaction scripts.
"""
from pathlib import Path
import os

# Project Structure
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATE_DIR = PROJECT_ROOT / "templates/prompts"
META_PROMPT_DIR = PROJECT_ROOT / "templates/meta-prompts"
CONTEXT_SELECTORS_DIR = PROJECT_ROOT / "templates/context_selectors"
CONTEXT_DIR_BASE = PROJECT_ROOT / "context_llm/code"
COMMON_CONTEXT_DIR = PROJECT_ROOT / "context_llm/common"
OUTPUT_DIR_BASE = PROJECT_ROOT / "llm_outputs"
CONTEXT_GENERATION_SCRIPT = PROJECT_ROOT / "scripts/generate_context.py"
MANIFEST_DATA_DIR = PROJECT_ROOT / "scripts" / "data"

# Regex Patterns
TIMESTAMP_DIR_REGEX = r"^\d{8}_\d{6}$"
TIMESTAMP_MANIFEST_REGEX = r"^\d{8}_\d{6}_manifest\.json$"

# Gemini API Model Names
GEMINI_MODEL_GENERAL_TASKS = "gemini-2.5-flash-preview-05-20"
GEMINI_MODEL_RESOLVE = "gemini-2.5-flash-preview-05-20"
GEMINI_MODEL_SUMMARY = "gemini-2.5-flash-preview-05-20"
GEMINI_MODEL_FLASH = "gemini-2.5-flash-preview-05-20"

# Delimiters and Constants
WEB_SEARCH_ENCOURAGEMENT_PT = "\n\nPara garantir a melhor resposta possível, sinta-se à vontade para pesquisar na internet usando a ferramenta de busca disponível."
DEFAULT_BASE_BRANCH = "main"
PR_CONTENT_DELIMITER_TITLE = "--- PR TITLE ---"
PR_CONTENT_DELIMITER_BODY = "--- PR BODY ---"
SUMMARY_CONTENT_DELIMITER_START = "--- START OF FILE "
SUMMARY_CONTENT_DELIMITER_END = "--- END OF FILE "

# Numeric Constants
SUMMARY_TOKEN_LIMIT_PER_CALL = 200000
ESTIMATED_TOKENS_PER_SUMMARY = 200
# MAX_OUTPUT_TOKENS_ESTIMATE = 50000 # Consider if needed, or if model limits are sufficient
SLEEP_DURATION_SECONDS = 1  # Default sleep duration for rate limiting
DEFAULT_API_TIMEOUT_SECONDS = 300  # Default timeout for Gemini API calls
MANIFEST_MAX_TOKEN_FILTER = 200000
DEFAULT_MAX_FILES_PER_SUMMARY_CALL = 10

# Default values for arguments (can be overridden by .env or CLI)
DEFAULT_TARGET_BRANCH = "main"
DEFAULT_MAX_FILES_PER_CALL_SUMMARY = 10
DEFAULT_CONTEXT_GENERATION_TIMEOUT = 600  # 10 minutes for context generation
DEFAULT_GH_PROJECT_NUMBER = os.getenv("GH_PROJECT_NUMBER", "1")
DEFAULT_GH_PROJECT_OWNER = os.getenv("GH_PROJECT_OWNER", "@me")
DEFAULT_GH_PROJECT_STATUS_FIELD_NAME = os.getenv(
    "GH_PROJECT_STATUS_FIELD_NAME", "Status"
)
DEFAULT_RATE_LIMIT_SLEEP = 60
