#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ==============================================================================
# generate_manifest.py
#
# Script para gerar um manifesto JSON estruturado do projeto, catalogando
# arquivos relevantes e extraindo metadados essenciais.
# Destinado a auxiliar ferramentas LLM e rastreamento de mudanças.
#
# Uso:
#   python scripts/generate_manifest.py [-o output.json] [-i ignore_pattern] [-v]
#
# Argumentos:
#   -o, --output OUTPUT_PATH   Caminho para o arquivo JSON de saída.
#                              (Padrão: scripts/data/YYYYMMDD_HHMMSS_manifest.json)
#   -i, --ignore IGNORE_PATTERN Padrão (glob), diretório ou arquivo a ignorar. Pode ser usado várias vezes.
#   -v, --verbose              Habilita logging mais detalhado.
#   -h, --help                 Mostra esta mensagem de ajuda.
# ==============================================================================

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set

# --- Constantes Globais ---
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = BASE_DIR / "scripts" / "data"

# TODO: Refinar estas listas e lógicas de exclusão/inclusão nos próximos ACs
DEFAULT_IGNORE_PATTERNS: Set[str] = {
    ".git/",
    ".vscode/",
    ".idea/",
    "node_modules/",
    "vendor/", # Será refinado para incluir uspdev
    "storage/", # Será refinado
    "public/build/",
    "*.lock",
    "*.sqlite",
    "*.sqlite-journal",
    ".env*", # Ignorar arquivos .env por padrão
    "*.log",
    ".phpunit.cache/",
    "context_llm/", # Ignorar diretório de contexto gerado
    "llm_outputs/", # Ignorar saídas LLM
    "scripts/data/", # Ignorar diretório de dados de scripts (incluindo este manifesto)
    "*.DS_Store",
    "Thumbs.db"
}

# --- Funções ---

def parse_arguments() -> argparse.Namespace:
    """
    Configura e processa os argumentos da linha de comando.

    Returns:
        argparse.Namespace: Objeto contendo os argumentos processados.
    """
    parser = argparse.ArgumentParser(
        description="Gera um manifesto JSON estruturado do projeto para análise e contexto.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""Exemplos:
  # Gerar manifesto com configurações padrão
  python {Path(__file__).name}

  # Especificar arquivo de saída
  python {Path(__file__).name} -o build/manifest.json

  # Ignorar arquivos específicos e um diretório
  python {Path(__file__).name} -i '*.tmp' -i 'docs/drafts/'

  # Habilitar modo verbose
  python {Path(__file__).name} -v
"""
    )

    parser.add_argument(
        "-o", "--output",
        dest="output_path",
        type=str, # Processaremos como Path mais tarde
        default=None,
        help=f"Caminho para o arquivo JSON de saída. Padrão: {DEFAULT_OUTPUT_DIR.relative_to(BASE_DIR)}/YYYYMMDD_HHMMSS_manifest.json"
    )

    parser.add_argument(
        "-i", "--ignore",
        dest="ignore_patterns",
        action="append",
        default=[],
        help="Padrão (glob), diretório ou arquivo a ignorar (além dos padrões). Use múltiplas vezes."
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Habilita logging mais detalhado para depuração."
    )

    return parser.parse_args()

def setup_logging(verbose: bool):
    """Configura o nível de logging."""
    # TODO (AC Futuro): Implementar um sistema de logging mais robusto se necessário.
    # Por enquanto, o modo verbose pode controlar prints adicionais.
    if verbose:
        print("Modo verbose habilitado.")
    pass # Placeholder

def get_default_output_filepath() -> Path:
    """Gera o caminho padrão para o arquivo de saída com timestamp."""
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}_manifest.json"
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True) # Garante que o diretório exista
    return DEFAULT_OUTPUT_DIR / filename

# --- Bloco Principal ---
if __name__ == "__main__":
    args = parse_arguments()
    setup_logging(args.verbose)

    # Determina o caminho final do arquivo de saída
    if args.output_path:
        output_filepath = Path(args.output_path).resolve()
        # Garante que o diretório pai exista se um caminho completo for fornecido
        output_filepath.parent.mkdir(parents=True, exist_ok=True)
    else:
        output_filepath = get_default_output_filepath()

    print(f"--- Iniciando Geração do Manifesto ---")
    print(f"Arquivo de Saída: {output_filepath.relative_to(BASE_DIR)}")
    print(f"Padrões Ignorados Padrão: {len(DEFAULT_IGNORE_PATTERNS)}")
    if args.ignore_patterns:
        print(f"Padrões Ignorados Adicionais: {args.ignore_patterns}")
    if args.verbose:
        print(f"Argumentos recebidos: {args}")

    # Placeholder para a lógica principal que virá nos próximos ACs
    print("\n[!] Lógica principal de scan, hash, análise e escrita do JSON será implementada nos próximos ACs.")

    # Exemplo de como acessar os argumentos (será usado nos próximos ACs)
    ignore_list = list(DEFAULT_IGNORE_PATTERNS) + args.ignore_patterns
    if args.verbose:
        print(f"\nLista final de ignorados (combinada):")
        for item in sorted(ignore_list): print(f" - {item}")

    # TODO AC3: Ler manifesto anterior (se existir)
    # TODO AC4: Implementar scan de arquivos (git ls-files + rglob)
    # TODO AC5: Aplicar filtros de exclusão (ignore_list)
    # TODO AC6-11: Identificar tipos, calcular hash (se aplicável), gerar metadados
    # TODO AC12-13: Extrair dependências PHP
    # TODO AC14-17: Calcular `needs_ai_update`
    # TODO AC18: Comparar com manifesto anterior
    # TODO AC19: Implementar tratamento de erro
    # TODO AC20-21: Garantir qualidade
    # TODO AC22: Ser chamado pelo generate_context.py

    # Exemplo de criação de um JSON vazio (será substituído pela lógica real)
    manifest_data: Dict[str, Any] = {
        "_metadata": {
            "timestamp": datetime.datetime.now().isoformat(),
            "comment": "Manifesto inicial - Lógica de preenchimento pendente (ACs 3-19)",
            "output_file": str(output_filepath.relative_to(BASE_DIR)),
            "args": vars(args) # Inclui args para referência
        },
        "files": {} # O dicionário principal será preenchido aqui
    }

    # Salva o JSON (sobrescreve se já existir)
    try:
        with open(output_filepath, 'w', encoding='utf-8') as f:
            json.dump(manifest_data, f, indent=4, ensure_ascii=False)
        print(f"\nManifesto JSON (placeholder) salvo em: {output_filepath.relative_to(BASE_DIR)}")
    except IOError as e:
        print(f"\nErro ao salvar o arquivo de manifesto: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
         print(f"\nErro inesperado ao salvar o manifesto: {e}", file=sys.stderr)
         sys.exit(1)

    print("--- Geração do Manifesto Concluída (com lógica pendente) ---")
    sys.exit(0)