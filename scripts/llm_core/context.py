# -*- coding: utf-8 -*-
"""
LLM Core Context Management Module.
"""
import re
import sys
import json
import argparse # Adicionado para type hint
from pathlib import Path
from typing import List, Optional, Dict, Any, Set, Tuple # Adicionado Tuple

from google.genai import types  # Assuming types are from google.genai

from . import config as core_config


def find_latest_context_dir(context_base_dir: Path) -> Optional[Path]:
    """Find the most recent context directory within the base directory."""
    if not context_base_dir.is_dir():
        print(
            f"Erro: Diretório base de contexto não encontrado: {context_base_dir}",
            file=sys.stderr,
        )
        return None

    valid_context_dirs = [
        d
        for d in context_base_dir.iterdir()
        if d.is_dir() and re.match(core_config.TIMESTAMP_DIR_REGEX, d.name)
    ]

    if not valid_context_dirs:
        print(
            f"Erro: Nenhum diretório de contexto válido encontrado em {context_base_dir}",
            file=sys.stderr,
        )
        return None

    return sorted(valid_context_dirs, reverse=True)[0]


def _load_files_from_dir(
    context_dir: Path,
    context_parts: List[types.Part],
    exclude_list: Optional[List[str]] = None,
    manifest_data: Optional[Dict[str, Any]] = None,
) -> None:
    """Helper to load files from a specific directory (.txt, .json, .md)."""
    file_patterns = ["*.txt", "*.json", "*.md"]
    loaded_count = 0
    excluded_count = 0
    exclude_set = set(exclude_list) if exclude_list else set()

    if not context_dir or not context_dir.is_dir():
        return

    files_to_consider: Set[Path] = set()
    for pattern in file_patterns:
        files_to_consider.update(context_dir.glob(pattern))

    for filepath in files_to_consider:
        if not filepath.is_file():
            continue

        try:
            resolved_filepath = filepath.resolve(strict=True)
            relative_path_str = str(
                resolved_filepath.relative_to(core_config.PROJECT_ROOT).as_posix()
            )
        except (FileNotFoundError, ValueError) as e:
            print(
                f"      - Aviso: Pulando arquivo {filepath.name} devido a erro de caminho: {e}",
                file=sys.stderr,
            )
            continue

        if relative_path_str in exclude_set:
            excluded_count += 1
            continue

        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")
            summary = ""
            if (
                manifest_data
                and "files" in manifest_data
                and relative_path_str in manifest_data["files"]
            ):
                summary_data = manifest_data["files"][relative_path_str].get("summary")
                if summary_data:
                    summary = f"\n--- SUMMARY ---\n{summary_data}\n--- END SUMMARY ---"

            context_parts.append(
                types.Part.from_text(
                    text=f"--- START OF FILE {relative_path_str} ---{summary}\n{content}\n--- END OF FILE {relative_path_str} ---"
                )
            )
            loaded_count += 1
        except Exception as e:
            print(
                f"      - Aviso: Não foi possível ler o arquivo {relative_path_str}: {e}",
                file=sys.stderr,
            )

    print(
        f"      - Carregados {loaded_count} arquivo(s) de {context_dir.relative_to(core_config.PROJECT_ROOT)} (carregamento padrão)."
    )
    if exclude_list:
        print(
            f"      - Excluídos {excluded_count} arquivo(s) com base em --exclude-context (carregamento padrão)."
        )


def prepare_context_parts(
    primary_context_dir: Optional[Path],
    common_context_dir: Optional[Path] = None,
    exclude_list: Optional[List[str]] = None,
    manifest_data: Optional[Dict[str, Any]] = None,
    include_list: Optional[List[str]] = None,
) -> List[types.Part]:
    """Prepara as partes do contexto como types.Part."""
    context_parts: List[types.Part] = []
    exclude_set = set(exclude_list) if exclude_list else set()
    loaded_count = 0
    excluded_by_arg_count = 0
    skipped_not_found = 0

    print("  Carregando arquivos de contexto...")

    if include_list is not None:
        print(
            f"    Carregando com base na lista de inclusão ({len(include_list)} arquivos)..."
        )
        include_set = set(include_list)

        for relative_path_str in include_set:
            if relative_path_str in exclude_set:
                excluded_by_arg_count += 1
                print(
                    f"      - Excluindo '{relative_path_str}' devido a --exclude-context."
                )
                continue

            filepath_absolute = (core_config.PROJECT_ROOT / relative_path_str).resolve(
                strict=False
            )

            if not filepath_absolute.is_file():
                print(
                    f"      - Aviso: Arquivo incluído não encontrado ou não é um arquivo: {relative_path_str}",
                    file=sys.stderr,
                )
                skipped_not_found += 1
                continue
            try:
                filepath_absolute.relative_to(core_config.PROJECT_ROOT)
            except ValueError:
                print(
                    f"      - Aviso: Pulando arquivo fora da raiz do projeto: {relative_path_str}",
                    file=sys.stderr,
                )
                skipped_not_found += 1
                continue
            try:
                content = filepath_absolute.read_text(encoding="utf-8", errors="ignore")
                summary = ""
                if (
                    manifest_data
                    and "files" in manifest_data
                    and relative_path_str in manifest_data["files"]
                ):
                    summary_data = manifest_data["files"][relative_path_str].get(
                        "summary"
                    )
                    if summary_data:
                        summary = (
                            f"\n--- SUMMARY ---\n{summary_data}\n--- END SUMMARY ---"
                        )
                context_parts.append(
                    types.Part.from_text(
                        text=f"--- START OF FILE {relative_path_str} ---{summary}\n{content}\n--- END OF FILE {relative_path_str} ---"
                    )
                )
                loaded_count += 1
            except Exception as e:
                print(
                    f"      - Aviso: Não foi possível ler o arquivo {relative_path_str}: {e}",
                    file=sys.stderr,
                )
                skipped_not_found += 1
        print(f"    Carregados {loaded_count} arquivos da lista de inclusão.")
        if exclude_list:
            print(
                f"    Excluídos {excluded_by_arg_count} arquivos com base em --exclude-context."
            )
        if skipped_not_found > 0:
            print(
                f"    Pulados {skipped_not_found} arquivos incluídos (não encontrados/legíveis/fora do projeto)."
            )
    else:  # Default loading
        print("    Carregando de diretórios padrão (contexto mais recente + comum)...")
        if primary_context_dir:
            _load_files_from_dir(
                primary_context_dir, context_parts, exclude_list, manifest_data
            )
        if (
            common_context_dir
            and common_context_dir.exists()
            and common_context_dir.is_dir()
        ):
            _load_files_from_dir(
                common_context_dir, context_parts, exclude_list, manifest_data
            )

    print(f"  Total de partes de contexto preparadas: {len(context_parts)}.")
    return context_parts


def find_latest_manifest_json(manifest_data_dir: Path) -> Optional[Path]:
    """Encontra o arquivo _manifest.json mais recente no diretório de dados."""
    if not manifest_data_dir.is_dir():
        return None
    manifest_files = [
        f
        for f in manifest_data_dir.glob("*_manifest.json")
        if f.is_file() and re.match(core_config.TIMESTAMP_MANIFEST_REGEX, f.name)
    ]
    if not manifest_files:
        return None
    return sorted(manifest_files, reverse=True)[0]


def load_manifest(manifest_path: Path) -> Optional[Dict[str, Any]]:
    """Carrega e parseia o arquivo de manifesto JSON."""
    if not manifest_path.is_file():
        print(
            f"Erro: Arquivo de manifesto não encontrado: {manifest_path}",
            file=sys.stderr,
        )
        return None
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if (
            not isinstance(data, dict)
            or "files" not in data
            or not isinstance(data["files"], dict)
        ):
            print(
                f"Erro: Formato inválido no manifesto {manifest_path.name}. Chave 'files' ausente/inválida.",
                file=sys.stderr,
            )
            return None
        return data
    except json.JSONDecodeError as e:
        print(f"Erro ao decodificar JSON de {manifest_path.name}: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(
            f"Erro ao ler arquivo de manifesto {manifest_path.name}: {e}",
            file=sys.stderr,
        )
        return None


def prompt_user_on_empty_selection() -> bool:
    """Pergunta ao usuário se deve prosseguir com o contexto padrão ou abortar."""
    while True:
        choice = (
            input(
                "  A seleção preliminar de contexto retornou uma lista vazia.\n"
                "  Deseja prosseguir com o contexto padrão (todos os arquivos relevantes) ou abortar a tarefa? (P/a) [Abortar]: "
            )
            .strip()
            .lower()
        )
        if choice in ["a", "abortar", ""]:
            print("  Tarefa abortada pelo usuário devido à seleção de contexto vazia.")
            return False
        elif choice in ["p", "prosseguir"]:
            print("  Prosseguindo com o contexto padrão...")
            return True
        else:
            print(
                "  Entrada inválida. Por favor, digite 'p' para prosseguir ou 'a' para abortar."
            )


def confirm_and_modify_selection(
    suggested_files: List[str],
    manifest_data: Optional[Dict[str, Any]] = None,
    max_input_tokens: Optional[int] = None,
) -> Optional[List[str]]:
    """Exibe a lista sugerida, permite modificação ou confirmação (Y/n). Retorna lista final ou None."""
    current_files = list(suggested_files)
    files_metadata = manifest_data.get("files", {}) if manifest_data else {}

    def display_current_selection():
        print("\n--- Context Files for Current Task ---")
        if not current_files:
            print("  (List is currently empty)")
        else:
            total_tokens = 0
            for i, filepath_str in enumerate(current_files):
                metadata = files_metadata.get(filepath_str, {})
                token_count_str = str(metadata.get("token_count", "N/A"))
                print(f"  {i + 1}: {filepath_str} (Tokens: {token_count_str})")
                if isinstance(metadata.get("token_count"), int):
                    total_tokens += metadata.get("token_count", 0)
            print(f"  ----------------------------------")
            print(f"  Total Estimated Tokens for Selection: {total_tokens}")
            if max_input_tokens:
                print(
                    f"  Recommended Max Input Tokens for API call: {max_input_tokens}"
                )
                if total_tokens > max_input_tokens:
                    print(
                        f"  WARNING: Current selection ({total_tokens}) exceeds recommended max ({max_input_tokens})!"
                    )
        print("------------------------------------")

    while True:
        display_current_selection()
        print(
            "Commands: 'y' (yes/confirm), 'n' (no/use default context), 'a path/to/add' (add file), 'r index|path' (remove file), 'q' (quit task)"
        )
        choice = input(
            "Confirm selection, modify, or use default context? [Y]: "
        ).strip()

        if choice.lower() in ["y", "yes", ""]:
            print(
                f"  User confirmed using {len(current_files)} selected files for context."
            )
            return current_files
        elif choice.lower() in ["n", "no"]:
            print("  User chose to use the default context instead.")
            return None
        elif choice.lower() in ["q", "quit"]:
            print("  Task aborted by user during context selection.")
            sys.exit(0)
        elif choice.startswith("a "):
            path_to_add = choice[2:].strip()
            if not path_to_add:
                print("  Error: Please provide a path after 'a'.")
                continue
            abs_path_to_add = (core_config.PROJECT_ROOT / path_to_add).resolve(
                strict=False
            )
            if not abs_path_to_add.is_file():
                print(
                    f"  Error: File to add '{path_to_add}' does not exist or is not a file."
                )
                continue
            try:
                path_to_add_relative_str = str(
                    abs_path_to_add.relative_to(core_config.PROJECT_ROOT).as_posix()
                )
                if path_to_add_relative_str not in current_files:
                    current_files.append(path_to_add_relative_str)
                    print(f"  Added '{path_to_add_relative_str}'.")
                else:
                    print(f"  '{path_to_add_relative_str}' is already in the list.")
            except ValueError:
                print(
                    f"  Error: Path to add '{path_to_add}' seems to be outside the project root. Cannot add."
                )
        elif choice.startswith("r "):
            item_to_remove_str = choice[2:].strip()
            if not item_to_remove_str:
                print("  Error: Please provide an index or path after 'r'.")
                continue
            removed_successfully = False
            try:
                index_to_remove = int(item_to_remove_str) - 1
                if 0 <= index_to_remove < len(current_files):
                    removed_path = current_files.pop(index_to_remove)
                    print(f"  Removed '{removed_path}' (index {index_to_remove + 1}).")
                    removed_successfully = True
                else:
                    print(f"  Error: Index {index_to_remove + 1} is out of bounds.")
            except ValueError:
                path_to_remove_normalized = Path(item_to_remove_str).as_posix()
                if path_to_remove_normalized in current_files:
                    current_files.remove(path_to_remove_normalized)
                    print(f"  Removed '{path_to_remove_normalized}'.")
                    removed_successfully = True
                else:
                    found_partial_match = False
                    for i, p_str in reversed(list(enumerate(current_files))):
                        if p_str.endswith(path_to_remove_normalized):
                            removed_path = current_files.pop(i)
                            print(
                                f"  Removed '{removed_path}' (matched ending with '{path_to_remove_normalized}')."
                            )
                            removed_successfully = True
                            found_partial_match = True
                            break
                    if not found_partial_match:
                        print(
                            f"  Error: Path '{path_to_remove_normalized}' not found in the list for removal."
                        )
            if not removed_successfully and not item_to_remove_str.isdigit():
                print(
                    f"  Error: Could not remove '{item_to_remove_str}' (not a valid index or existing path/suffix)."
                )
        else:
            print("  Invalid command. Use 'y', 'n', 'a path', 'r index|path', or 'q'.")


def get_essential_files_for_task(
    task_name: str,
    cli_args: argparse.Namespace,
    latest_dir_name: Optional[str],
    verbose: bool = False,
) -> List[Path]:
    """
    Identifica os caminhos absolutos dos arquivos essenciais para uma dada tarefa e argumentos.
    Resolve placeholders nos padrões de ESSENTIAL_FILES_MAP.
    """
    essential_file_paths: List[Path] = []
    task_map = core_config.ESSENTIAL_FILES_MAP.get(task_name, {})

    # Processar arquivos baseados em argumentos
    if "args" in task_map:
        for arg_name, file_pattern_template in task_map["args"].items():
            if hasattr(cli_args, arg_name):
                arg_value = getattr(cli_args, arg_name)
                if arg_value:
                    formatted_file_pattern = file_pattern_template
                    replacements = {"latest_dir_name": latest_dir_name or ""}
                    for attr, val_cli in vars(cli_args).items():
                        if val_cli is not None:
                            replacements[attr] = str(val_cli)
                    
                    if arg_name == "doc_file" and file_pattern_template == "{doc_file}":
                        formatted_file_pattern = str(arg_value) # O valor já é o path
                    else:
                        for key_placeholder, val_placeholder in replacements.items():
                            formatted_file_pattern = formatted_file_pattern.replace(f"{{{key_placeholder}}}", val_placeholder)

                    if "{" in formatted_file_pattern and "}" in formatted_file_pattern and verbose:
                        print(f"  Aviso: Placeholder não resolvido em '{formatted_file_pattern}' para arg '{arg_name}'. Pulando.")
                        continue
                    
                    abs_path = (core_config.PROJECT_ROOT / formatted_file_pattern).resolve(strict=False)
                    if abs_path.is_file():
                        essential_file_paths.append(abs_path)
                    elif verbose:
                        print(f"  Aviso: Arquivo essencial de arg '{formatted_file_pattern}' não encontrado em {abs_path}.")

    # Processar arquivos estáticos
    if "static" in task_map:
        for static_file_template in task_map["static"]:
            formatted_static_file = static_file_template
            replacements = {"latest_dir_name": latest_dir_name or ""}
            for attr, val_cli in vars(cli_args).items():
                 if val_cli is not None:
                    replacements[attr] = str(val_cli)

            for key_placeholder, val_placeholder in replacements.items():
                formatted_static_file = formatted_static_file.replace(f"{{{key_placeholder}}}", val_placeholder)

            if "{" in formatted_static_file and "}" in formatted_static_file and verbose:
                print(f"  Aviso: Placeholder não resolvido em '{formatted_static_file}' para arquivo estático. Pulando.")
                continue

            abs_path = (core_config.PROJECT_ROOT / formatted_static_file).resolve(strict=False)
            if abs_path.is_file():
                essential_file_paths.append(abs_path)
            elif verbose:
                print(f"  Aviso: Arquivo essencial estático '{formatted_static_file}' não encontrado em {abs_path}.")
    
    unique_paths = list(set(essential_file_paths))
    if verbose:
        print(f"  Identificados {len(unique_paths)} caminhos de arquivos essenciais únicos para '{task_name}'.")
    return unique_paths


def load_essential_files_content(
    essential_file_paths: List[Path],
    max_tokens: int,
    verbose: bool = False
) -> Tuple[str, List[Path]]:
    """
    Carrega o conteúdo integral dos arquivos essenciais, respeitando um limite de tokens.
    Retorna o conteúdo concatenado e formatado, e a lista de caminhos relativos dos arquivos carregados.
    """
    concatenated_content_parts: List[str] = []
    current_tokens_estimate = 0
    loaded_files_relative_paths: List[Path] = []

    for file_path_abs in essential_file_paths:
        try:
            content = file_path_abs.read_text(encoding="utf-8", errors="ignore")
            estimated_tokens = len(content) // 4  # Estimativa simples

            if current_tokens_estimate + estimated_tokens > max_tokens and concatenated_content_parts:
                if verbose:
                    print(f"  Aviso: Limite de tokens para conteúdo essencial ({max_tokens}) atingido. '{file_path_abs.name}' não será totalmente incluído.")
                break 

            relative_path = file_path_abs.relative_to(core_config.PROJECT_ROOT)
            relative_path_str = relative_path.as_posix()
            
            formatted_block = (
                f"{core_config.ESSENTIAL_CONTENT_DELIMITER_START}{relative_path_str} ---\n"
                f"{content}\n"
                f"{core_config.ESSENTIAL_CONTENT_DELIMITER_END}{relative_path_str} ---\n\n"
            )
            concatenated_content_parts.append(formatted_block)
            current_tokens_estimate += estimated_tokens
            loaded_files_relative_paths.append(relative_path)
            if verbose:
                print(f"    Conteúdo essencial de '{relative_path_str}' pré-injetado ({estimated_tokens} tokens est.).")

        except Exception as e:
            if verbose:
                print(f"  Aviso: Não foi possível ler o arquivo essencial '{file_path_abs.name}': {e}", file=sys.stderr)
    
    return "".join(concatenated_content_parts), loaded_files_relative_paths


def prepare_payload_for_selector_llm(
    task_name: str,
    cli_args: argparse.Namespace,
    latest_dir_name: Optional[str],
    full_manifest_data: Dict[str, Any],
    selector_prompt_template_content: str,
    verbose: bool = False
) -> str:
    """
    Prepara o payload completo para a LLM seletora, incluindo conteúdo essencial pré-injetado
    e o JSON do manifesto dos demais arquivos.
    """
    essential_file_abs_paths = get_essential_files_for_task(task_name, cli_args, latest_dir_name, verbose)
    
    essential_content_str, loaded_essential_relative_paths = load_essential_files_content(
        essential_file_abs_paths,
        core_config.MAX_ESSENTIAL_TOKENS_FOR_SELECTOR_CALL,
        verbose
    )

    remaining_manifest_files: Dict[str, Any] = {}
    if "files" in full_manifest_data:
        loaded_essential_relative_paths_str_set = {p.as_posix() for p in loaded_essential_relative_paths}
        for path_str, metadata in full_manifest_data["files"].items():
            if path_str not in loaded_essential_relative_paths_str_set:
                token_c = metadata.get("token_count")
                if (token_c is None or 
                    (isinstance(token_c, int) and token_c <= core_config.MANIFEST_MAX_TOKEN_FILTER)):
                    remaining_manifest_files[path_str] = {
                        "type": metadata.get("type"),
                        "summary": metadata.get("summary"),
                        "token_count": metadata.get("token_count")
                    }
                elif verbose:
                     print(f"    Arquivo '{path_str}' (tokens: {token_c}) filtrado do manifesto para LLM seletora devido ao MANIFEST_MAX_TOKEN_FILTER.")

    remaining_manifest_json_str = json.dumps({"files": remaining_manifest_files}, indent=2, ensure_ascii=False)
    
    final_selector_prompt = selector_prompt_template_content.replace(
        "{{ESSENTIAL_FILES_CONTENT}}", essential_content_str
    )
    final_selector_prompt = final_selector_prompt.replace(
        "{{REMAINING_MANIFEST_JSON}}", remaining_manifest_json_str
    )

    if verbose:
        print(f"    Conteúdo essencial injetado no prompt seletor (Total tokens est. essenciais: {len(essential_content_str)//4}).")
        print(f"    JSON do manifesto dos demais arquivos (Total itens: {len(remaining_manifest_files)}).")

    return final_selector_prompt