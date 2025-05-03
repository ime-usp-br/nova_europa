#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
from pathlib import Path  # Usar pathlib para manipulação de caminhos mais robusta
import traceback
from typing import List, Tuple

# --- Constante Chave ---
# Calcula o diretório raiz do projeto (assumindo que este script está em /scripts)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Regex compiled once for efficiency
# Using MULTILINE to match ^ at the beginning of lines,
# and DOTALL so that . matches newlines in the file content.
# Group 1: File path (non-greedy)
# Group 2: File content
PARSE_PATTERN = re.compile(
    r"^--- START OF FILE ?(.*?) *---\n(.*?)\n^--- END OF FILE ?\1 *---",
    re.MULTILINE | re.DOTALL,
)


def parse_source_content(content: str) -> List[Tuple[str, str]]:
    """
    Parses the input string to find file blocks demarcated by
    '--- START OF FILE path ---' and '--- END OF FILE path ---'.

    Args:
        content: The string content to parse.

    Returns:
        A list of tuples, where each tuple contains:
        (relative_filepath_str, file_content)
    """
    matches = PARSE_PATTERN.findall(content)
    # Clean whitespace from captured path and return
    # Content is kept as is (including leading/trailing whitespace within the block)
    return [(path.strip(), file_content) for path, file_content in matches]


def update_files_from_source(source_file_name="source_code_string.txt"):
    """
    Reads a source file (expected in project root) containing multiple file
    contents demarcated by specific markers, extracts each file's path and content,
    and writes/overwrites the files relative to the project root.

    Args:
        source_file_name (str): The name of the input text file, expected
                                to be in the project root directory.
    """
    # Constrói o caminho completo para o arquivo fonte usando PROJECT_ROOT
    source_file_path = PROJECT_ROOT / source_file_name

    print(f"--- Starting file update process ---")
    print(f"Project Root: '{PROJECT_ROOT}'")
    print(f"Reading source file: '{source_file_path}'")

    try:
        # Usa o caminho completo para ler o arquivo fonte
        with open(source_file_path, "r", encoding="utf-8") as f:
            source_text = f.read()
        print(
            f"Successfully read source file: '{source_file_path.relative_to(PROJECT_ROOT)}'"
        )
    except FileNotFoundError:
        print(f"Error: Source file not found at '{source_file_path}'")
        print(
            f"Ensure the file '{source_file_name}' exists in the project root directory ('{PROJECT_ROOT}')."
        )
        sys.exit(1)
    except IOError as e:
        print(f"Error reading source file '{source_file_path}': {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred while reading '{source_file_path}': {e}")
        traceback.print_exc()
        sys.exit(1)

    # Parse the content using the dedicated function
    parsed_blocks = parse_source_content(source_text)

    if not parsed_blocks:
        print(
            "Warning: No file blocks found in the source file matching the expected format."
        )
        print("Format: --- START OF FILE path/file ---")
        print("        <content>")
        print("        --- END OF FILE path/file ---")
        return

    print(f"Found {len(parsed_blocks)} file blocks to process.")
    files_updated = 0
    errors_occurred = 0

    # Process parsed blocks instead of raw matches
    for relative_filepath_str, file_content in parsed_blocks:
        # Path should already be stripped by parse_source_content, but check for empty
        if not relative_filepath_str:
            print("  Warning: Found a block with an empty file path. Skipping.")
            errors_occurred += 1
            continue

        # Constrói o caminho completo de SAÍDA usando PROJECT_ROOT
        output_path = PROJECT_ROOT / relative_filepath_str
        # Normaliza o caminho (remove './', lida com .. se houver, ajusta barras)
        # Use try-except block for resolve() in case of invalid paths on specific OS
        try:
            output_path = output_path.resolve()
        except Exception as e:
            print(f"  Error resolving path '{relative_filepath_str}': {e}. Skipping.")
            errors_occurred += 1
            continue


        # Verificação de segurança básica: impedir escrita fora do diretório do projeto
        try:
            # Garante que o caminho resolvido ainda está dentro do diretório raiz do projeto
            output_path.relative_to(PROJECT_ROOT)
        except ValueError:
            print(
                f"  Error: Attempted to write outside the project directory: '{output_path}'. Skipping."
            )
            errors_occurred += 1
            continue

        print(f"\nProcessing file: '{output_path.relative_to(PROJECT_ROOT)}'...")

        try:
            # Obter o diretório pai usando pathlib
            directory = output_path.parent

            # Cria o diretório pai se ele não existir
            if directory:
                print(
                    f"  Ensuring directory exists: '{directory.relative_to(PROJECT_ROOT)}'"
                )
                # Usa pathlib para criar diretórios
                directory.mkdir(parents=True, exist_ok=True)

            # Escreve o arquivo (sobrescreve se existir) usando o caminho completo
            print(f"  Writing content to '{output_path.relative_to(PROJECT_ROOT)}'...")
            with open(output_path, "w", encoding="utf-8") as outfile:
                outfile.write(file_content)

            print(f"  Successfully updated: '{output_path.relative_to(PROJECT_ROOT)}'")
            files_updated += 1

        except OSError as e:
            print(
                f"  Error creating directory or writing file '{output_path.relative_to(PROJECT_ROOT)}': {e}"
            )
            errors_occurred += 1
        except Exception as e:
            print(
                f"  An unexpected error occurred while processing '{output_path.relative_to(PROJECT_ROOT)}': {e}"
            )
            traceback.print_exc() # Print traceback for unexpected errors
            errors_occurred += 1

    print("\n--- File update process finished ---")
    print(f"Summary: {files_updated} files updated, {errors_occurred} errors.")


if __name__ == "__main__":
    # Permite passar um nome de arquivo fonte diferente como argumento
    # Se nenhum argumento for passado, usa o default "source_code_string.txt"
    source_arg = sys.argv[1] if len(sys.argv) > 1 else "source_code_string.txt"
    update_files_from_source(source_arg)