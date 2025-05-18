# -*- coding: utf-8 -*-
"""
LLM Core Arguments Module.
"""
import argparse
from pathlib import Path
import sys
from . import config as core_config # Import the core config

def get_common_arg_parser(description: str) -> argparse.ArgumentParser:
    """
    Creates and returns a base argparse.ArgumentParser with common arguments
    for LLM interaction scripts.
    """
    script_name = Path(sys.argv[0]).name if sys.argv else "llm_task_script.py"
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Common flags already present in llm_interact_copy.py's parser
    parser.add_argument(
        "--two-stage",
        "-ts",
        action="store_true",
        help="Use two-stage meta-prompt flow (meta-prompt -> final prompt -> response). Default is direct flow.",
    )
    parser.add_argument(
        "-o",
        "--observation",
        help=f"Additional observation/instruction. Fills {core_config.WEB_SEARCH_ENCOURAGEMENT_PT.splitlines()[0]} in prompts. E.g., 'Focus on PSR-12 compliance.'",
        default="",
    )
    parser.add_argument(
        "-sc",
        "--select-context",
        action="store_true",
        help="Enable preliminary context selection by LLM from the manifest.",
    )
    parser.add_argument(
        "-ec",
        "--exclude-context",
        action="append",
        help="Filename(s) or glob pattern(s) to exclude from context (e.g., -ec file1.txt -ec '*.log'). Can be used multiple times. Applied AFTER LLM selection if -sc is used.",
        default=[],
    )
    parser.add_argument(
        "-w",
        "--web-search",
        action="store_true",
        help="Enable Google Search tool for Gemini (if model supports it).",
    )
    parser.add_argument(
        "-g",
        "--generate-context",
        action="store_true",
        help=f"Run context generation script ('{core_config.CONTEXT_GENERATION_SCRIPT.name}') before interaction.",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Auto-confirm intermediate LLM steps. Final action (e.g., save file, create PR) still requires confirmation.",
    )
    parser.add_argument(
        "-om",
        "--only-meta",
        action="store_true",
        help="Only print the filled meta-prompt (if --two-stage is active) and exit. Does not call API.",
    )
    parser.add_argument(
        "-op",
        "--only-prompt",
        action="store_true",
        help="Only print the final prompt (direct or generated from meta-prompt) and exit. Does not call API for final response.",
    )
    parser.add_argument(
        "-ws",
        "--with-sleep",
        action="store_true",
        help=f"Wait {core_config.SLEEP_DURATION_SECONDS}s before each API attempt (for rate limiting).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output for debugging."
    )

    # Consider adding --api-key, --timeout, --model overrides if needed frequently across tasks
    # For now, these might be better handled via .env or global config if not task-specific.

    return parser