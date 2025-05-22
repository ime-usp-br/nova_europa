import json
import os
import shutil
from pathlib import Path

# Nome do arquivo de entrada e diretório de saída
INPUT_FILE_NAME = "context_selected.txt"
OUTPUT_BASE_DIR_NAME = "context_llm/temp"

# Caminho para a raiz do projeto (assumindo que o script está na raiz)
PROJECT_ROOT = Path(__file__).resolve().parent


def copy_selected_files():
    """
    Lê um arquivo JSON com uma lista de arquivos relevantes e os copia
    para um diretório temporário, mantendo a estrutura de pastas.
    """
    input_file_path = PROJECT_ROOT / INPUT_FILE_NAME
    output_base_path = PROJECT_ROOT / OUTPUT_BASE_DIR_NAME

    print(f"Lendo arquivo de seleção: {input_file_path}")

    if not input_file_path.is_file():
        print(f"Erro: Arquivo de seleção '{input_file_path}' não encontrado.")
        return

    try:
        with open(input_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print(
            f"Erro: Falha ao decodificar JSON do arquivo '{input_file_path}'. Verifique o formato."
        )
        return
    except Exception as e:
        print(f"Erro ao ler o arquivo '{input_file_path}': {e}")
        return

    relevant_files = data.get("relevant_files")

    if not isinstance(relevant_files, list):
        print(
            "Erro: A chave 'relevant_files' não foi encontrada ou não é uma lista no JSON."
        )
        return

    if not relevant_files:
        print("Nenhum arquivo selecionado para cópia.")
        return

    print(f"Criando/Verificando diretório de saída: {output_base_path}")
    output_base_path.mkdir(parents=True, exist_ok=True)

    copied_count = 0
    skipped_count = 0
    error_count = 0

    print(f"\nIniciando cópia de {len(relevant_files)} arquivos selecionados...")

    for relative_path_str in relevant_files:
        # Normaliza o caminho para o sistema operacional atual
        # e remove qualquer barra inicial que possa causar problemas com Path.joinpath
        normalized_relative_path = Path(
            os.path.normpath(relative_path_str.lstrip("/\\"))
        )

        source_file_path = PROJECT_ROOT / normalized_relative_path
        destination_file_path = output_base_path / normalized_relative_path

        if not source_file_path.is_file():
            print(
                f"  [AVISO] Arquivo fonte não encontrado ou não é um arquivo: '{source_file_path}'. Pulando."
            )
            skipped_count += 1
            continue

        try:
            # Cria o diretório de destino se não existir
            destination_file_path.parent.mkdir(parents=True, exist_ok=True)

            shutil.copy2(source_file_path, destination_file_path)
            print(f"  [OK] Copiado: '{source_file_path}' -> '{destination_file_path}'")
            copied_count += 1
        except Exception as e:
            print(
                f"  [ERRO] Falha ao copiar '{source_file_path}' para '{destination_file_path}': {e}"
            )
            error_count += 1

    print("\n--- Resumo da Cópia ---")
    print(f"Arquivos copiados com sucesso: {copied_count}")
    print(f"Arquivos pulados (não encontrados): {skipped_count}")
    print(f"Erros durante a cópia: {error_count}")
    print(f"Destino: {output_base_path.resolve()}")


if __name__ == "__main__":
    copy_selected_files()
