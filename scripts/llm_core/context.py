# -*- coding: utf-8 -*-
"""
LLM Core Context Management Module.
"""
import re
import sys
import json
import argparse
import dataclasses # Adicionado para FileProcessUnit
from pathlib import Path
from typing import List, Optional, Dict, Any, Set, Tuple, Union # Adicionado Union

from google.genai import types

from . import config as core_config
from . import api_client 
from .exceptions import MissingEssentialFileAbort 
from . import io_utils 


@dataclasses.dataclass
class FileProcessUnit:
    """
    Dataclass para gerenciar o estado dos arquivos durante o processo de redução de contexto.
    """
    relative_path: str
    content: str
    token_count: int  # Token count of current content (integral, summary, or truncated)
    original_token_count: int  # Token count of the full original content
    original_content: str # Store original content for potential truncation later
    file_type: Optional[str] = None # Type of the file from manifest
    summary: Optional[str] = None
    summary_token_count: Optional[int] = None
    is_essential_from_map: bool = False
    is_reduced_to_summary: bool = False
    is_truncated: bool = False


def _truncate_content(content: str, target_token_count: int, verbose: bool = False) -> Tuple[str, int]:
    """
    Trunca o conteúdo para aproximadamente target_token_count, mantendo início e fim.
    Retorna o conteúdo truncado e sua nova contagem de tokens estimada.
    """
    chars_per_token_approx = 3.8
    target_char_count = int(target_token_count * chars_per_token_approx)
    
    separator = "\n\n... [CONTEÚDO TRUNCADO PARA CABER NO LIMITE DE TOKENS] ...\n\n"
    separator_len = len(separator)
    
    if not content: 
        return "", 0

    if len(content) <= target_char_count:
        return content, max(1, int(len(content) / chars_per_token_approx)) if content else 0

    if target_char_count <= separator_len:
        keep_start_chars = max(10, target_char_count - 10)
        truncated_content_str = content[:keep_start_chars] + "\n...[TRUNCADO]..."
        new_token_estimate = max(1, int(len(truncated_content_str) / chars_per_token_approx)) if truncated_content_str else 0
        if verbose:
            print(f"      Truncamento agressivo: mantendo {keep_start_chars} caracteres do início.")
        return truncated_content_str, new_token_estimate

    keep_each_side = (target_char_count - separator_len) // 2
    if keep_each_side < 50:
        keep_each_side = 50
        
        if target_char_count < (keep_each_side * 2 + separator_len):
             keep_start = max(10, target_char_count - len("\n...[TRUNCADO]..."))
             truncated_content_str = content[:keep_start] + "\n...[TRUNCADO]..."
             new_token_estimate = max(1, int(len(truncated_content_str) / chars_per_token_approx)) if truncated_content_str else 0
             if verbose:
                 print(f"      Truncamento priorizando início: {keep_start} caracteres.")
             return truncated_content_str, new_token_estimate

    start_chunk = content[:keep_each_side]
    end_chunk = content[-keep_each_side:]
    
    truncated_content_str = start_chunk + separator + end_chunk
    new_token_estimate = max(1, int(len(truncated_content_str) / chars_per_token_approx)) if truncated_content_str else 0

    if verbose:
        original_token_estimate = max(1, int(len(content) / chars_per_token_approx)) if content else 0
        print(f"      Conteúdo truncado: ~{new_token_estimate} tokens (original: ~{original_token_estimate} tokens).")
    
    return truncated_content_str, new_token_estimate


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
    processed_units: List[FileProcessUnit],
    exclude_set: Set[str],
    manifest_data: Optional[Dict[str, Any]],
    essential_map_paths_relative_str: Set[str],
    skip_if_already_loaded_relative_paths: Set[str],
    verbose: bool = False,
) -> None:
    """Helper to load files from a specific directory into FileProcessUnit list."""
    file_patterns = ["*.txt", "*.json", "*.md"] 
    loaded_count = 0
    excluded_by_arg_count = 0
    skipped_already_loaded_count = 0

    if not context_dir or not context_dir.is_dir():
        return

    files_to_consider: Set[Path] = set()
    for pattern in file_patterns:
        files_to_consider.update(context_dir.glob(pattern))

    for filepath_abs in files_to_consider:
        if not filepath_abs.is_file():
            continue

        try:
            relative_path_str = str(
                filepath_abs.relative_to(core_config.PROJECT_ROOT).as_posix()
            )
        except ValueError:
            if verbose:
                print(
                    f"      - Aviso: Pulando arquivo {filepath_abs.name} (fora da raiz do projeto).",
                    file=sys.stderr,
                )
            continue

        if relative_path_str in skip_if_already_loaded_relative_paths:
            skipped_already_loaded_count +=1
            if verbose:
                print(f"      - Pulando '{relative_path_str}' (já carregado como essencial).")
            continue

        if relative_path_str in exclude_set:
            excluded_by_arg_count += 1
            if verbose:
                print(f"      - Excluindo '{relative_path_str}' (de _load_files_from_dir) devido a --exclude-context.")
            continue

        try:
            content = filepath_abs.read_text(encoding="utf-8", errors="ignore")
            original_token_count = max(1, int(len(content) / 3.8)) if content else 0 
            
            summary_text: Optional[str] = None
            summary_tokens: Optional[int] = None
            file_type_from_manifest: Optional[str] = None

            if manifest_data and "files" in manifest_data and relative_path_str in manifest_data["files"]:
                metadata = manifest_data["files"][relative_path_str]
                if isinstance(metadata, dict): 
                    summary_text = metadata.get("summary")
                    stc_from_manifest = metadata.get("summary_token_count")
                    if isinstance(stc_from_manifest, int) and stc_from_manifest >= 0:
                        summary_tokens = stc_from_manifest
                    elif summary_text: 
                        summary_tokens = max(1, int(len(summary_text) / 3.8))
                    else:
                        summary_tokens = None
                    
                    file_type_from_manifest = metadata.get("type")
                    
                    manifest_token_count = metadata.get("token_count")
                    if isinstance(manifest_token_count, int) and manifest_token_count >= 0:
                        original_token_count = manifest_token_count


            is_essential = relative_path_str in essential_map_paths_relative_str

            processed_units.append(FileProcessUnit(
                relative_path=relative_path_str,
                content=content,
                original_content=content,
                token_count=original_token_count,
                original_token_count=original_token_count,
                file_type=file_type_from_manifest,
                summary=summary_text,
                summary_token_count=summary_tokens,
                is_essential_from_map=is_essential
            ))
            loaded_count += 1
        except Exception as e:
            if verbose:
                print(
                    f"      - Aviso: Não foi possível ler o arquivo {relative_path_str}: {e}",
                    file=sys.stderr,
                )
    if verbose:
        print(
            f"      - Carregados {loaded_count} arquivo(s) de {context_dir.relative_to(core_config.PROJECT_ROOT)} (padrão)."
        )
        if skip_if_already_loaded_relative_paths:
             print(
                f"      - Pulados {skipped_already_loaded_count} arquivo(s) por já terem sido carregados como essenciais."
            )
        if exclude_set:
            print(
                f"      - Excluídos {excluded_by_arg_count} arquivo(s) por --exclude-context (padrão)."
            )


def get_essential_files_for_task(
    task_name: str,
    cli_args: argparse.Namespace,
    latest_dir_name: Optional[str],
    verbose: bool = False,
) -> List[Path]:
    """
    Identifica os caminhos absolutos dos arquivos potencialmente essenciais para uma dada tarefa e argumentos.
    Resolve placeholders nos padrões de ESSENTIAL_FILES_MAP.
    """
    essential_file_abs_paths: List[Path] = []
    task_map = core_config.ESSENTIAL_FILES_MAP.get(task_name, {})

    if verbose:
        print(f"  AC5.1a: Iniciando identificação de arquivos essenciais para tarefa '{task_name}'...")
        if "args" in task_map:
            for arg_name, file_pattern_template in task_map["args"].items():
                print(f"    - Padrão por argumento '{arg_name}': {file_pattern_template}")
        if "static" in task_map:
            for static_file_template in task_map["static"]:
                print(f"    - Padrão estático: {static_file_template}")

    if "args" in task_map:
        for arg_name, file_pattern_template in task_map["args"].items():
            if hasattr(cli_args, arg_name):
                arg_value = getattr(cli_args, arg_name)
                if arg_value:
                    formatted_file_pattern = str(file_pattern_template)
                    replacements: Dict[str, str] = {"latest_dir_name": latest_dir_name or ""}
                    for attr_name_in_args, val_cli_in_args in vars(cli_args).items():
                        if val_cli_in_args is not None:
                            replacements[attr_name_in_args] = str(val_cli_in_args)

                    if arg_name == "doc_file" and file_pattern_template == "{doc_file}":
                        path_to_check = Path(str(arg_value))
                        if not path_to_check.is_absolute():
                            path_to_check = (core_config.PROJECT_ROOT / path_to_check).resolve(strict=False)
                        essential_file_abs_paths.append(path_to_check)
                        if verbose:
                             print(f"    + Potencialmente essencial (de arg '{arg_name}'): {path_to_check.relative_to(core_config.PROJECT_ROOT) if path_to_check.is_absolute() and path_to_check.is_relative_to(core_config.PROJECT_ROOT) else path_to_check}")
                        continue

                    for key_placeholder, val_placeholder in replacements.items():
                        formatted_file_pattern = formatted_file_pattern.replace(f"{{{key_placeholder}}}", val_placeholder)

                    if "{" in formatted_file_pattern and "}" in formatted_file_pattern and verbose:
                        print(f"    - Aviso: Placeholder não resolvido em '{formatted_file_pattern}' para arg '{arg_name}'. Pulando.")
                        continue
                    
                    abs_path = (core_config.PROJECT_ROOT / formatted_file_pattern).resolve(strict=False)
                    essential_file_abs_paths.append(abs_path)
                    if verbose:
                         print(f"    + Potencialmente essencial (de arg '{arg_name}'): {abs_path.relative_to(core_config.PROJECT_ROOT) if abs_path.is_absolute() and abs_path.is_relative_to(core_config.PROJECT_ROOT) else abs_path}")

    if "static" in task_map:
        for static_file_template in task_map["static"]:
            formatted_static_file = str(static_file_template)
            replacements = {"latest_dir_name": latest_dir_name or ""}
            for attr_name_in_args, val_cli_in_args in vars(cli_args).items():
                 if val_cli_in_args is not None:
                    replacements[attr_name_in_args] = str(val_cli_in_args)

            for key_placeholder, val_placeholder in replacements.items():
                formatted_static_file = formatted_static_file.replace(f"{{{key_placeholder}}}", val_placeholder)
            
            if "{" in formatted_static_file and "}" in formatted_static_file and verbose:
                print(f"    - Aviso: Placeholder não resolvido em '{formatted_static_file}' para arquivo estático. Pulando.")
                continue

            abs_path = (core_config.PROJECT_ROOT / formatted_static_file).resolve(strict=False)
            essential_file_abs_paths.append(abs_path)
            if verbose:
                print(f"    + Potencialmente essencial (estático): {abs_path.relative_to(core_config.PROJECT_ROOT) if abs_path.is_absolute() and abs_path.is_relative_to(core_config.PROJECT_ROOT) else abs_path}")

    unique_paths = sorted(list(set(essential_file_abs_paths)))
    if verbose:
        print(f"  AC5.1a: Lista final de {len(unique_paths)} caminhos de arquivos potencialmente essenciais identificados para '{task_name}':")
        for p_idx, p in enumerate(unique_paths):
            try:
                print(f"    [{p_idx+1}] {p.relative_to(core_config.PROJECT_ROOT)}")
            except ValueError: 
                print(f"    [{p_idx+1}] {p} (fora da raiz do projeto)") 
    return unique_paths


def load_essential_files_content(
    essential_file_paths_abs: List[Path],
    max_tokens_for_essentials_payload: int,
    verbose: bool = False
) -> Tuple[str, List[Path]]:
    """
    Carrega o conteúdo dos arquivos essenciais, aplicando truncamento se necessário.
    Retorna o conteúdo concatenado e os caminhos relativos dos arquivos carregados.
    """
    concatenated_content_parts: List[str] = []
    current_tokens_estimate = 0
    loaded_files_relative_paths: List[Path] = []

    if verbose and essential_file_paths_abs:
        print(f"  AC5.1b: Carregando conteúdo de {len(essential_file_paths_abs)} arquivo(s) essencial(is) (limite est. payload: {max_tokens_for_essentials_payload} tokens):")

    for file_path_abs in essential_file_paths_abs:
        if current_tokens_estimate >= max_tokens_for_essentials_payload:
            if verbose:
                print(f"    AC5.1b: Limite de tokens para payload essencial ({max_tokens_for_essentials_payload}) atingido. Pulando arquivos restantes.")
            break

        try:
            relative_path = file_path_abs.relative_to(core_config.PROJECT_ROOT)
            relative_path_str = relative_path.as_posix()
        except ValueError:
            if verbose:
                print(f"    Aviso (AC4.1): Arquivo essencial '{file_path_abs}' não parece estar dentro do PROJECT_ROOT. Pulando.", file=sys.stderr)
            continue

        if not file_path_abs.is_file():
            user_wants_to_continue = io_utils.prompt_user_for_missing_essential_file(relative_path_str)
            if not user_wants_to_continue:
                raise MissingEssentialFileAbort(
                    f"Tarefa abortada pelo usuário devido ao arquivo essencial ausente: {relative_path_str}"
                )
            else:
                if verbose:
                    print(f"    AC5.1b: Continuando sem o arquivo essencial ausente '{relative_path_str}'.")
                continue

        try:
            content = file_path_abs.read_text(encoding="utf-8", errors="ignore")
            estimated_tokens_current_file = max(1, int(len(content) / 3.8)) if content else 0
            
            content_to_add = content
            tokens_to_add = estimated_tokens_current_file
            was_truncated = False
            status_log_msg_part = "INTEGRALMENTE usado"

            if current_tokens_estimate + estimated_tokens_current_file > max_tokens_for_essentials_payload:
                remaining_token_budget = max_tokens_for_essentials_payload - current_tokens_estimate
                if remaining_token_budget < 50: 
                    if verbose:
                        print(f"    AVISO (AC3.4 / AC5.1b): Arquivo essencial '{relative_path_str}' ({estimated_tokens_current_file} tokens est.) pulado. Orçamento restante ({remaining_token_budget} tokens) muito pequeno para conteúdo útil.")
                    status_log_msg_part = "PULADO (orçamento insuficiente)"
                    content_to_add = "" # Não adiciona conteúdo
                    tokens_to_add = 0
                else:
                    if verbose:
                         print(f"    AVISO (AC3.4 / AC5.1b): Conteúdo do arquivo essencial '{relative_path_str}' ({estimated_tokens_current_file} tokens est.) será truncado para caber no orçamento de {remaining_token_budget} tokens.")
                    content_to_add, tokens_to_add = _truncate_content(content, remaining_token_budget, verbose)
                    was_truncated = True
                    status_log_msg_part = "TRUNCADO"
                    if tokens_to_add == 0 and content_to_add: 
                        tokens_to_add = 1
            
            if verbose: # AC5.1b Log
                print(f"    AC5.1b: Arquivo essencial '{relative_path_str}': Conteúdo {status_log_msg_part} (estimativa: {tokens_to_add} tokens).")


            if tokens_to_add > 0 or not content_to_add: 
                formatted_block = (
                    f"{core_config.ESSENTIAL_CONTENT_DELIMITER_START}{relative_path_str} ---\n"
                    f"{content_to_add}\n"
                    f"{core_config.ESSENTIAL_CONTENT_DELIMITER_END}{relative_path_str} ---\n\n"
                )
                concatenated_content_parts.append(formatted_block)
                current_tokens_estimate += tokens_to_add
                loaded_files_relative_paths.append(relative_path)
            elif verbose:
                 print(f"    AC5.1b: Arquivo essencial '{relative_path_str}' resultou em 0 tokens após tentativa de truncamento e não foi adicionado ao payload da LLM seletora.")

        except Exception as e:
            if verbose:
                print(f"  Aviso: Não foi possível ler ou processar o arquivo essencial '{file_path_abs.name}': {e}", file=sys.stderr)
    
    return "".join(concatenated_content_parts), loaded_files_relative_paths


def prepare_payload_for_selector_llm(
    task_name: str,
    cli_args: argparse.Namespace,
    latest_dir_name: Optional[str],
    full_manifest_data: Dict[str, Any],
    selector_prompt_template_content: str,
    max_tokens_for_essentials_payload: int,
    verbose: bool = False
) -> str:
    """
    Prepara o payload completo para a LLM seletora.
    """
    essential_file_abs_paths = get_essential_files_for_task(task_name, cli_args, latest_dir_name, verbose)
    
    essential_content_str, loaded_essential_relative_paths = load_essential_files_content(
        essential_file_abs_paths,
        max_tokens_for_essentials_payload,
        verbose
    )

    remaining_manifest_files_for_selector: Dict[str, Any] = {}
    files_metadata_from_manifest = full_manifest_data.get("files", {})
    
    loaded_essential_relative_paths_str_set = {p.as_posix() for p in loaded_essential_relative_paths}
    
    if verbose:
        print("  Filtrando manifesto restante para LLM seletora:")

    for path_str, metadata in files_metadata_from_manifest.items():
        if path_str not in loaded_essential_relative_paths_str_set:
            if not isinstance(metadata, dict): continue
            token_c = metadata.get("token_count")
            token_c_val = float('inf')
            if token_c is None: pass
            elif not isinstance(token_c, int):
                if verbose: print(f"    - Aviso: token_count para '{path_str}' não é um inteiro ({token_c}), tratando como muito grande.")
                pass
            else: token_c_val = token_c

            if token_c_val <= core_config.MANIFEST_MAX_TOKEN_FILTER:
                remaining_manifest_files_for_selector[path_str] = {
                    "type": metadata.get("type"),
                    "summary": metadata.get("summary"),
                    "token_count": token_c
                }
            elif verbose:
                 print(f"    - Arquivo '{path_str}' (tokens: {token_c_val}) filtrado do manifesto para LLM seletora (limite: {core_config.MANIFEST_MAX_TOKEN_FILTER}).")

    remaining_manifest_json_str = json.dumps({"files": remaining_manifest_files_for_selector}, indent=2, ensure_ascii=False)
    
    final_selector_prompt = selector_prompt_template_content.replace(
        "{{REMAINING_MANIFEST_JSON}}", remaining_manifest_json_str
    )
    final_selector_prompt = final_selector_prompt.replace(
        "{{ESSENTIAL_FILES_CONTENT}}", essential_content_str
    )

    if verbose:
        essential_tokens_est = max(1, int(len(essential_content_str) / 3.8)) if essential_content_str else 0
        remaining_manifest_tokens_est = max(1, int(len(remaining_manifest_json_str) / 3.8)) if remaining_manifest_json_str else 0
        # Estima tokens do template
        prompt_template_tokens_est = max(1, int(len(re.sub(r"{{.*?}}", "", selector_prompt_template_content)) / 3.8))
        
        total_payload_tokens_est = essential_tokens_est + remaining_manifest_tokens_est + prompt_template_tokens_est
        print(f"    Conteúdo essencial injetado no prompt seletor (~{essential_tokens_est} tokens).")
        print(f"    JSON do manifesto dos demais arquivos (~{remaining_manifest_tokens_est} tokens, {len(remaining_manifest_files_for_selector)} arquivos).")
        print(f"    Tamanho do prompt seletor template (sem placeholders) (~{prompt_template_tokens_est} tokens).")
        print(f"    AC5.1c: Tamanho total estimado do payload para LLM seletora: ~{total_payload_tokens_est} tokens.")
        
    return final_selector_prompt


def prepare_context_parts(
    primary_context_dir: Optional[Path],
    common_context_dir: Optional[Path] = None,
    exclude_list: Optional[List[str]] = None,
    manifest_data: Optional[Dict[str, Any]] = None,
    include_list: Optional[List[str]] = None,
    max_input_tokens_for_call: Optional[int] = None,
    is_for_selector_llm: bool = False, 
    task_name_for_essentials: Optional[str] = None,
    cli_args_for_essentials: Optional[argparse.Namespace] = None,
    latest_dir_name_for_essentials: Optional[str] = None,
    verbose: bool = False,
) -> List[types.Part]:
    """
    Prepara as partes do contexto como types.Part, aplicando estratégias de redução se necessário.
    Levanta MissingEssentialFileAbort se um arquivo essencial não for encontrado e o usuário abortar.
    """
    context_parts_final: List[types.Part] = []
    processed_units: List[FileProcessUnit] = []
    exclude_set = set(exclude_list) if exclude_list else set()
    loaded_as_essential_paths_str: Set[str] = set() 
    essential_map_paths_relative_str: Set[str] = set() 

    if verbose: print("  Carregando e processando arquivos de contexto...")

    if task_name_for_essentials and cli_args_for_essentials:
        essential_file_abs_paths = get_essential_files_for_task(
            task_name_for_essentials,
            cli_args_for_essentials,
            latest_dir_name_for_essentials,
            verbose
        )
        for p in essential_file_abs_paths:
            try:
                essential_map_paths_relative_str.add(p.relative_to(core_config.PROJECT_ROOT).as_posix())
            except ValueError: 
                 if verbose: print(f"      - Aviso (Map Essencial): Arquivo '{p}' fora da raiz. Não será marcado como essencial pelo mapa.")

        for essential_abs_path in essential_file_abs_paths:
            try:
                rel_path_str = essential_abs_path.relative_to(core_config.PROJECT_ROOT).as_posix()
            except ValueError:
                if verbose: print(f"      - Aviso (Essencial): Arquivo '{essential_abs_path}' fora da raiz. Pulando.")
                continue

            if not essential_abs_path.is_file():
                if not io_utils.prompt_user_for_missing_essential_file(rel_path_str): 
                    raise MissingEssentialFileAbort(f"Tarefa abortada pelo usuário: arquivo essencial '{rel_path_str}' ausente.")
                if verbose: print(f"      - Aviso (Essencial): '{rel_path_str}' não encontrado, continuando sem ele por escolha do usuário.")
                continue 

            try:
                content = essential_abs_path.read_text(encoding="utf-8", errors="ignore")
                token_count_val = max(1, int(len(content) / 3.8)) if content else 0 
                summary_val, summary_token_val, type_val = None, None, None
                if manifest_data and "files" in manifest_data and rel_path_str in manifest_data["files"]:
                    meta = manifest_data["files"][rel_path_str]
                    if isinstance(meta,dict):
                        summary_val = meta.get("summary")
                        stc_from_manifest = meta.get("summary_token_count")
                        if isinstance(stc_from_manifest, int) and stc_from_manifest >= 0:
                            summary_token_val = stc_from_manifest
                        elif summary_val: 
                            summary_token_val = max(1, int(len(summary_val)/3.8))
                        else:
                            summary_token_val = None
                        type_val = meta.get("type")
                        manifest_token_count_val = meta.get("token_count")
                        if isinstance(manifest_token_count_val, int): token_count_val = manifest_token_count_val


                processed_units.append(FileProcessUnit(
                    relative_path=rel_path_str, content=content, original_content=content,
                    token_count=token_count_val, original_token_count=token_count_val,
                    file_type=type_val, summary=summary_val, summary_token_count=summary_token_val,
                    is_essential_from_map=True
                ))
                loaded_as_essential_paths_str.add(rel_path_str)
                if verbose: print(f"    + Carregado como essencial: '{rel_path_str}' ({token_count_val} tokens).")
            except Exception as e:
                if verbose: print(f"      - Aviso (Essencial): Não foi possível ler '{rel_path_str}': {e}", file=sys.stderr)

    if include_list is not None:
        if verbose: print(f"    Carregando com base na lista de inclusão ({len(include_list)} arquivos)...")
        loaded_count_incl = 0
        excluded_by_arg_count_incl = 0
        skipped_not_found_incl = 0
        skipped_already_loaded_incl = 0

        for rel_path_str_incl in include_list:
            if rel_path_str_incl in loaded_as_essential_paths_str:
                skipped_already_loaded_incl +=1
                if verbose: print(f"      - Pulando '{rel_path_str_incl}' (já carregado como essencial).")
                continue
            if rel_path_str_incl in exclude_set:
                excluded_by_arg_count_incl +=1
                if verbose: print(f"      - Excluindo '{rel_path_str_incl}' (de include_list) por --exclude-context.")
                continue
            
            filepath_abs_incl = (core_config.PROJECT_ROOT / rel_path_str_incl).resolve(strict=False)
            if not filepath_abs_incl.is_file():
                if verbose: print(f"      - Aviso: Arquivo incluído '{rel_path_str_incl}' não encontrado. Pulando.")
                skipped_not_found_incl +=1
                continue
            
            try:
                filepath_abs_incl.relative_to(core_config.PROJECT_ROOT)
            except ValueError:
                if verbose: print(f"      - Aviso: Pulando arquivo fora da raiz: {rel_path_str_incl}",file=sys.stderr)
                skipped_not_found_incl += 1
                continue

            try:
                content = filepath_abs_incl.read_text(encoding="utf-8", errors="ignore")
                original_token_count = max(1, int(len(content) / 3.8)) if content else 0 
                summary_text_incl, summary_tokens_val_incl, file_type_val_incl = None, None, None

                if manifest_data and "files" in manifest_data and rel_path_str_incl in manifest_data["files"]:
                    metadata = manifest_data["files"][rel_path_str_incl]
                    if isinstance(metadata, dict):
                        summary_text_incl = metadata.get("summary")
                        stc_from_manifest_incl = metadata.get("summary_token_count")
                        if isinstance(stc_from_manifest_incl, int) and stc_from_manifest_incl >= 0:
                            summary_tokens_val_incl = stc_from_manifest_incl
                        elif summary_text_incl: 
                            summary_tokens_val_incl = max(1, int(len(summary_text_incl) / 3.8))
                        else:
                            summary_tokens_val_incl = None
                        file_type_val_incl = metadata.get("type")
                        manifest_token_count_val_incl = metadata.get("token_count")
                        if isinstance(manifest_token_count_val_incl,int): original_token_count = manifest_token_count_val_incl

                processed_units.append(FileProcessUnit(
                    relative_path=rel_path_str_incl, content=content, original_content=content,
                    token_count=original_token_count, original_token_count=original_token_count,
                    file_type=file_type_val_incl, summary=summary_text_incl,
                    summary_token_count=summary_tokens_val_incl,
                    is_essential_from_map=False
                ))
                loaded_count_incl += 1
            except Exception as e:
                if verbose: print(f"      - Aviso: Não foi possível ler '{rel_path_str_incl}': {e}", file=sys.stderr)
                skipped_not_found_incl +=1
        if verbose:
            print(f"    Carregados {loaded_count_incl} arquivos da lista de inclusão.")
            if skipped_already_loaded_incl >0: print(f"    Pulados {skipped_already_loaded_incl} da include_list (já carregados como essenciais).")
            if exclude_set: print(f"    Excluídos {excluded_by_arg_count_incl} da include_list por --exclude-context.")
            if skipped_not_found_incl > 0: print(f"    Pulados {skipped_not_found_incl} da include_list (não encontrados/legíveis).")
    else:
        if verbose: print("    Carregando de diretórios padrão (contexto mais recente + comum)...")
        if primary_context_dir:
            _load_files_from_dir(primary_context_dir, processed_units, exclude_set, manifest_data, essential_map_paths_relative_str, loaded_as_essential_paths_str, verbose)
        if common_context_dir and common_context_dir.exists() and common_context_dir.is_dir():
            _load_files_from_dir(common_context_dir, processed_units, exclude_set, manifest_data, essential_map_paths_relative_str, loaded_as_essential_paths_str, verbose)

    current_total_tokens = sum(unit.token_count for unit in processed_units)

    if max_input_tokens_for_call is not None and current_total_tokens > max_input_tokens_for_call:
        if verbose:
            print(f"  AVISO (AC2.2): Contexto inicial ({current_total_tokens} tokens) excede o limite ({max_input_tokens_for_call} tokens). Aplicando reduções...")

        units_for_summary_reduction = sorted(
            [unit for unit in processed_units if not unit.is_essential_from_map and unit.summary and unit.summary_token_count is not None and unit.summary_token_count < unit.original_token_count],
            key=lambda u: (u.original_token_count - (u.summary_token_count or u.original_token_count)),
            reverse=True
        )
        for unit in units_for_summary_reduction:
            if current_total_tokens <= max_input_tokens_for_call: break
            if unit.summary and unit.summary_token_count is not None:
                token_reduction = unit.token_count - unit.summary_token_count
                if token_reduction > 0:
                    if verbose: print(f"    AC2.2.1: Substituindo '{unit.relative_path}' ({unit.original_token_count} tokens originais) por sumário ({unit.summary_token_count} tokens). Economia: {token_reduction}")
                    unit.content = unit.summary
                    unit.token_count = unit.summary_token_count
                    current_total_tokens -= token_reduction
                    unit.is_reduced_to_summary = True
        
        if current_total_tokens > max_input_tokens_for_call:
            units_to_truncate_non_essential = sorted(
                [unit for unit in processed_units if not unit.is_essential_from_map and not unit.is_reduced_to_summary],
                key=lambda u: u.token_count, reverse=True
            )
            for unit in units_to_truncate_non_essential:
                if current_total_tokens <= max_input_tokens_for_call: break
                needed_reduction_overall = current_total_tokens - max_input_tokens_for_call
                max_reduction_for_this_file = max(0, unit.token_count - 50) 
                reduction_to_apply = min(needed_reduction_overall, max_reduction_for_this_file)
                if reduction_to_apply > 0:
                    target_token_for_this_file = unit.token_count - reduction_to_apply
                    original_tokens_before_trunc = unit.token_count
                    unit.content, unit.token_count = _truncate_content(unit.original_content, target_token_for_this_file, verbose)
                    current_total_tokens -= (original_tokens_before_trunc - unit.token_count)
                    unit.is_truncated = True
                    if verbose: print(f"    AC2.2.2 (Não Essencial): Truncando '{unit.relative_path}' de {original_tokens_before_trunc} para {unit.token_count} tokens.")
        
        if current_total_tokens > max_input_tokens_for_call:
            units_to_truncate_essential = sorted(
                [unit for unit in processed_units if unit.is_essential_from_map and not unit.is_reduced_to_summary],
                key=lambda u: u.token_count, reverse=True
            )
            for unit in units_to_truncate_essential:
                if current_total_tokens <= max_input_tokens_for_call: break
                needed_reduction_overall = current_total_tokens - max_input_tokens_for_call
                max_reduction_for_this_file = max(0, unit.token_count - 100) 
                reduction_to_apply = min(needed_reduction_overall, max_reduction_for_this_file)
                if reduction_to_apply > 0:
                    target_token_for_this_file = unit.token_count - reduction_to_apply
                    original_tokens_before_trunc = unit.token_count
                    unit.content, unit.token_count = _truncate_content(unit.original_content, target_token_for_this_file, verbose)
                    current_total_tokens -= (original_tokens_before_trunc - unit.token_count)
                    unit.is_truncated = True
                    if verbose: print(f"    AVISO (AC3.4): Conteúdo do arquivo essencial '{unit.relative_path}' ({original_tokens_before_trunc} tokens est.) foi truncado para {unit.token_count} tokens para caber no limite da chamada principal.")

    for unit in processed_units:
        content_type_log = "integral"
        if unit.is_reduced_to_summary: content_type_log = "sumário"
        elif unit.is_truncated: content_type_log = "truncado"
        
        if verbose:
             print(f"    -> Incluindo '{unit.relative_path}' ({unit.token_count} tokens) como conteúdo {content_type_log}.")

        summary_block_for_part_text = ""
        if unit.summary and not unit.is_reduced_to_summary and not is_for_selector_llm: # is_for_selector_llm condition is not relevant here
            summary_block_for_part_text = f"--- SUMMARY ---\n{unit.summary}\n--- END SUMMARY ---"
        
        delimiter_start = core_config.ESSENTIAL_CONTENT_DELIMITER_START if unit.is_essential_from_map else core_config.SUMMARY_CONTENT_DELIMITER_START
        delimiter_end = core_config.ESSENTIAL_CONTENT_DELIMITER_END if unit.is_essential_from_map else core_config.SUMMARY_CONTENT_DELIMITER_END
        
        final_text_parts = [f"{delimiter_start}{unit.relative_path} ---"]
        if summary_block_for_part_text:
            final_text_parts.append(summary_block_for_part_text)
        final_text_parts.append(unit.content)
        final_text_parts.append(f"{delimiter_end}{unit.relative_path} ---")
        
        final_text = "\n".join(final_text_parts)
        context_parts_final.append(types.Part.from_text(text=final_text))

    final_total_tokens = sum(unit.token_count for unit in processed_units)
    if verbose and max_input_tokens_for_call and final_total_tokens > max_input_tokens_for_call :
        print(f"  AVISO FINAL (AC2.2): Contexto final ({final_total_tokens} tokens) ainda excede o limite ({max_input_tokens_for_call} tokens) após reduções.")

    print(f"  Total de partes de contexto preparadas: {len(context_parts_final)} (~{final_total_tokens} tokens).")
    return context_parts_final


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
    verbose: bool = False, 
) -> Optional[List[str]]:
    """Exibe a lista sugerida, permite modificação ou confirmação (Y/n). Retorna lista final ou None."""
    current_files = list(suggested_files)
    files_metadata = manifest_data.get("files", {}) if manifest_data else {}

    if verbose: 
        print(f"  AC5.1d: Lista de arquivos retornada pela LLM seletora ({len(current_files)} arquivos):")
        for f_idx, f_path in enumerate(current_files):
            print(f"    [{f_idx+1}] {f_path}")

    def display_current_selection():
        print("\n--- Context Files for Current Task ---")
        if not current_files:
            print("  (List is currently empty)")
        else:
            total_tokens = 0
            for i, filepath_str in enumerate(current_files):
                metadata = files_metadata.get(filepath_str, {})
                token_count_val = metadata.get("token_count")
                token_count_str = str(token_count_val) if token_count_val is not None else "N/A"
                
                print(f"  {i + 1}: {filepath_str} (Tokens: {token_count_str})") 
                if isinstance(token_count_val, int):
                    total_tokens += token_count_val
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
            if verbose: print(f"  Usuário confirmou o uso de {len(current_files)} arquivos selecionados para o contexto.")
            return current_files
        elif choice.lower() in ["n", "no"]:
            if verbose: print("  Usuário optou por usar o contexto padrão em vez da seleção.")
            return None
        elif choice.lower() in ["q", "quit"]:
            if verbose: print("  Tarefa abortada pelo usuário durante a seleção de contexto.")
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
                    if verbose: print(f"    AC5.1e: Usuário adicionou '{path_to_add_relative_str}' à seleção.") 
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
            original_path_removed_for_log: Optional[str] = None
            try:
                index_to_remove = int(item_to_remove_str) - 1
                if 0 <= index_to_remove < len(current_files):
                    original_path_removed_for_log = current_files.pop(index_to_remove)
                    print(f"  Removed '{original_path_removed_for_log}' (index {index_to_remove + 1}).")
                    removed_successfully = True
                else:
                    print(f"  Error: Index {index_to_remove + 1} is out of bounds.")
            except ValueError:
                path_to_remove_normalized = Path(item_to_remove_str).as_posix()
                if path_to_remove_normalized in current_files:
                    current_files.remove(path_to_remove_normalized)
                    original_path_removed_for_log = path_to_remove_normalized
                    print(f"  Removed '{path_to_remove_normalized}'.")
                    removed_successfully = True
                else:
                    found_partial_match = False
                    for i, p_str in reversed(list(enumerate(current_files))):
                        if p_str.endswith(path_to_remove_normalized):
                            original_path_removed_for_log = current_files.pop(i)
                            print(
                                f"  Removed '{original_path_removed_for_log}' (matched ending with '{path_to_remove_normalized}')."
                            )
                            removed_successfully = True
                            found_partial_match = True
                            break
                    if not found_partial_match:
                        print(
                            f"  Error: Path '{path_to_remove_normalized}' not found in the list for removal."
                        )
            if removed_successfully and verbose and original_path_removed_for_log: 
                print(f"    AC5.1e: Usuário removeu '{original_path_removed_for_log}' da seleção.")
            elif not removed_successfully and not item_to_remove_str.isdigit():
                print(
                    f"  Error: Could not remove '{item_to_remove_str}' (not a valid index or existing path/suffix)."
                )
        else:
            print("  Invalid command. Use 'y', 'n', 'a path', 'r index|path', or 'q'.")