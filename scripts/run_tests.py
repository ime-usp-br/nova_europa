#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ==============================================================================
# run_tests.py (Python version of run_tests.sh - v1.1)
#
# Script para executar as suítes de teste do projeto (PHPUnit e Laravel Dusk).
# Gerencia o início e parada dos serviços necessários para os testes Dusk
# (ChromeDriver, Servidor Artisan, Servidor Vite Dev).
# Mantém as mesmas opções de linha de comando do script shell original.
# Segue o padrão PEP 8.
#
# Uso:
#   python scripts/run_tests.py [--skip-phpunit] [--skip-dusk] [--stop-on-failure]
#
# Opções:
#   --skip-phpunit      Pula a execução dos testes PHPUnit.
#   --skip-dusk         Pula a execução dos testes Laravel Dusk.
#   --stop-on-failure   Para a execução imediatamente se uma suíte de teste falhar.
# ==============================================================================

import argparse
import datetime
import os
import platform
import shlex
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple, Dict

# --- Configurações ---
BASE_DIR = Path(__file__).resolve().parent.parent  # Raiz do projeto
PHP_CMD = "php"
ARTISAN_FILE = BASE_DIR / "artisan"
VENDOR_DIR = BASE_DIR / "vendor"
PHPUNIT_ENV = "testing"
DUSK_ENV = "dusk.local"
DUSK_ENV_FILE = BASE_DIR / f".env.{DUSK_ENV}"
DUSK_APP_PORT = "8000"
DUSK_CHROMEDRIVER_PORT = "9515"
DUSK_TEST_DIR = BASE_DIR / "tests" / "Browser"
LOG_DIR = BASE_DIR / "storage" / "logs" # Diretório de logs
CHROMEDRIVER_LOG = LOG_DIR / "chromedriver.log"
DUSK_SERVE_LOG = LOG_DIR / "dusk_serve.log"
VITE_DEV_LOG = LOG_DIR / "vite_dev.log" # Log para o Vite

# --- Variáveis de Estado ---
overall_exit_code = 0
bg_processes: List[subprocess.Popen] = [] # Lista para armazenar Popen objects


# --- Funções Auxiliares ---

def log(message: str):
    """Imprime mensagens de log com timestamp."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def command_exists(cmd: str) -> bool:
    """Verifica se um comando existe no PATH."""
    return shutil.which(cmd) is not None

def run_command(
    cmd_list: List[str],
    env: Optional[Dict[str, str]] = None,
    cwd: Path = BASE_DIR,
    check: bool = True,
    capture: bool = True,
    print_output: bool = False,
    timeout: Optional[int] = None, # Adiciona timeout opcional
) -> Tuple[int, str, str]:
    """Executa um comando e retorna (exit_code, stdout, stderr)."""
    cmd_str = shlex.join(cmd_list)
    log(f"  Executando: {cmd_str} (em {cwd})")
    start_time = time.monotonic()
    try:
        process_env = os.environ.copy()
        if env:
            process_env.update(env)

        process = subprocess.run(
            cmd_list,
            capture_output=capture,
            text=True,
            cwd=cwd,
            env=process_env,
            check=check, # Levanta exceção se check=True e falhar
            encoding="utf-8",
            errors="replace",
            timeout=timeout # Passa o timeout
        )
        duration = time.monotonic() - start_time
        stdout = process.stdout or ""
        stderr = process.stderr or ""

        if print_output and capture:
             if stdout:
                 print(f"    Stdout:\n{stdout.strip()}")
             if stderr:
                 print(f"    Stderr:\n{stderr.strip()}", file=sys.stderr)
        log(f"    Comando concluído em {duration:.2f}s com código {process.returncode}")
        return process.returncode, stdout, stderr

    except FileNotFoundError:
        log(f"Erro: Comando '{cmd_list[0]}' não encontrado.")
        return 1, "", f"Comando não encontrado: {cmd_list[0]}"
    except subprocess.CalledProcessError as e:
        log(f"Erro: Comando falhou com código {e.returncode}.")
        duration = time.monotonic() - start_time
        log(f"    Comando falhou após {duration:.2f}s")
        if capture:
            print(f"    Stderr:\n{e.stderr.strip()}", file=sys.stderr)
            print(f"    Stdout:\n{e.stdout.strip()}", file=sys.stderr)
            return e.returncode, e.stdout or "", e.stderr or ""
        return e.returncode, "", ""
    except subprocess.TimeoutExpired as e:
        log(f"Erro: Comando excedeu o tempo limite de {timeout}s.")
        duration = time.monotonic() - start_time
        log(f"    Comando excedeu timeout após {duration:.2f}s")
        return 1, e.stdout or "", e.stderr or f"TimeoutExpired: Command '{cmd_str}' timed out after {timeout} seconds"
    except Exception as e:
        log(f"Erro inesperado ao executar comando: {e}")
        traceback.print_exc()
        return 1, "", str(e)

def start_background_process(cmd_list: List[str], log_file: Path, env: Optional[Dict[str, str]] = None) -> Optional[subprocess.Popen]:
    """Inicia um processo em background, redireciona saída e retorna o objeto Popen."""
    cmd_str = shlex.join(cmd_list)
    log(f"  Iniciando em background: {cmd_str} > {log_file.relative_to(BASE_DIR)}")
    log_handle = None # Inicializa para o finally
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        process_env = os.environ.copy()
        if env:
            process_env.update(env)

        log_handle = open(log_file, 'w', encoding='utf-8')

        kwargs = {}
        # Para Unix-like, start_new_session cria um novo grupo de processos
        if platform.system() != "Windows":
            kwargs['start_new_session'] = True
        # Para Windows, pode-se usar flags como DETACHED_PROCESS ou CREATE_NEW_PROCESS_GROUP
        # Mas Popen.terminate() / Popen.kill() geralmente funcionam bem no Windows.

        p = subprocess.Popen(
            cmd_list,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            cwd=BASE_DIR,
            env=process_env,
            **kwargs
        )
        bg_processes.append(p) # Adiciona à lista global para cleanup
        # NÃO feche o log_handle aqui, o processo Popen precisa dele aberto.
        # O handle será fechado implicitamente quando o processo Popen for encerrado.
        return p
    except FileNotFoundError:
        log(f"Erro: Comando '{cmd_list[0]}' não encontrado ao tentar iniciar em background.")
        if log_handle and not log_handle.closed: log_handle.close() # Fecha se ocorreu erro
        return None
    except Exception as e:
        log(f"Erro inesperado ao iniciar processo em background '{cmd_str}': {e}")
        traceback.print_exc()
        if log_handle and not log_handle.closed: log_handle.close() # Fecha se ocorreu erro
        return None

def check_process_running(p: Optional[subprocess.Popen], name: str) -> bool:
    """Verifica se um processo Popen ainda está rodando."""
    if p is None:
        log(f"  Erro: Objeto de processo para '{name}' é None.")
        return False
    # poll() retorna None se o processo ainda está rodando
    if p.poll() is None:
        log(f"  {name} (PID: {p.pid}) parece estar rodando.")
        return True
    else:
        log(f"  Erro: {name} (PID: {p.pid}) terminou inesperadamente com código {p.returncode}. Verifique '{name}.log'.")
        # Remove o processo da lista se ele já terminou
        if p in bg_processes:
            bg_processes.remove(p)
        return False

def get_chromedriver_path() -> Optional[Path]:
    """Determina o caminho do executável ChromeDriver apropriado."""
    base_path = VENDOR_DIR / "laravel" / "dusk" / "bin"
    system = platform.system()
    machine = platform.machine().lower() # Normaliza a arquitetura

    if system == "Linux":
        # Adicionar mais arquiteturas Linux se necessário (arm, etc.)
        return base_path / "chromedriver-linux"
    elif system == "Darwin": # macOS
        if "arm64" in machine or "aarch64" in machine :
            return base_path / "chromedriver-mac-arm64"
        else: # Assume x86_64
            return base_path / "chromedriver-mac-x64"
    elif system == "Windows":
         # Adicionar lógica para arm64 no Windows se necessário
         return base_path / "chromedriver-win.exe"
    else:
        log(f"  Aviso: Sistema operacional '{system}' não suportado para detecção automática do ChromeDriver.")
        return None

def cleanup():
    """Para todos os processos em background iniciados."""
    if not bg_processes:
        # Evita log desnecessário se nenhum processo foi iniciado (ex: ao usar --help)
        return

    log("Iniciando limpeza de processos em background...")
    # Itera sobre uma cópia da lista para poder remover itens da original
    processes_to_stop = list(bg_processes)
    bg_processes.clear() # Limpa a lista global

    for p in processes_to_stop:
        if p.poll() is None: # Só tenta parar se ainda estiver rodando
            pid_info = f"(PID: {p.pid})" if hasattr(p, 'pid') else "(PID desconhecido)"
            log(f"  Parando processo {pid_info}...")
            try:
                # Tenta terminar graciosamente primeiro
                if platform.system() != "Windows":
                    # Em Unix, tenta enviar SIGTERM para o grupo de processos
                    # Isso tem mais chance de parar processos filhos (como o servidor PHP real)
                    os.killpg(os.getpgid(p.pid), signal.SIGTERM)
                else:
                    # No Windows, Popen.terminate() é geralmente a melhor opção
                    p.terminate()

                # Espera um pouco pelo encerramento gracioso
                p.wait(timeout=5)
                log(f"    Processo {pid_info} terminado com código {p.returncode}.")
            except ProcessLookupError:
                 log(f"    Processo {pid_info} já não existia.")
            except subprocess.TimeoutExpired:
                log(f"    Processo {pid_info} não encerrou com terminate/SIGTERM. Forçando kill...")
                try:
                    # Se não funcionou, força o encerramento
                    if platform.system() != "Windows":
                        os.killpg(os.getpgid(p.pid), signal.SIGKILL)
                    else:
                        p.kill()
                    p.wait(timeout=2) # Espera curta após SIGKILL
                    log(f"      Processo {pid_info} forçado a encerrar.")
                except Exception as kill_e:
                    log(f"      Erro ao forçar encerramento do processo {pid_info}: {kill_e}")
            except Exception as e:
                 log(f"    Erro ao tentar parar processo {pid_info}: {e}")
        # else: # Opcional: Log se o processo já tinha terminado antes do cleanup
        #     log(f"  Processo (PID: {p.pid}) já havia terminado.")

    log("Limpeza concluída.")

# --- Função Principal ---
def main():
    global overall_exit_code

    parser = argparse.ArgumentParser(
        description="Executa as suítes de teste PHPUnit e Laravel Dusk.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""Exemplos:
  python scripts/run_tests.py
  python scripts/run_tests.py --skip-dusk
  python scripts/run_tests.py --stop-on-failure
"""
    )
    parser.add_argument(
        "--skip-phpunit",
        action="store_true",
        help="Pula a execução dos testes PHPUnit.",
    )
    parser.add_argument(
        "--skip-dusk",
        action="store_true",
        help="Pula a execução dos testes Laravel Dusk.",
    )
    parser.add_argument(
        "--stop-on-failure",
        action="store_true",
        help="Para a execução imediatamente se uma suíte de teste falhar.",
    )
    args = parser.parse_args()

    log("Iniciando execução dos testes...")
    log(f"Diretório Base: {BASE_DIR}")

    # --- Validação de Ambiente ---
    log("Validando ambiente...")
    essential_cmds = [PHP_CMD]
    if not args.skip_dusk:
        essential_cmds.append("npm") # Adiciona npm como essencial se Dusk não for pulado

    missing_essential = [cmd for cmd in essential_cmds if not command_exists(cmd)]
    if missing_essential:
         log(f"Erro Fatal: Comandos essenciais não encontrados: {', '.join(missing_essential)}. Instale-os.")
         return 1

    if not ARTISAN_FILE.is_file():
        log(f"Erro Fatal: Arquivo 'artisan' não encontrado em {BASE_DIR}. Execute da raiz do projeto.")
        return 1
    if not VENDOR_DIR.is_dir():
        log("Erro Fatal: Diretório 'vendor' não encontrado. Execute 'composer install'.")
        return 1

    log("Validação de ambiente OK.")
    print("-" * 40)

    # --- Execução dos Testes PHPUnit ---
    if not args.skip_phpunit:
        log(f"[PHPUnit] Iniciando testes PHPUnit (Ambiente: {PHPUNIT_ENV})...")
        phpunit_env_file = BASE_DIR / f".env.{PHPUNIT_ENV}"
        if not phpunit_env_file.is_file() and PHPUNIT_ENV == "testing":
             log(f"  Aviso: Arquivo '{phpunit_env_file.name}' não encontrado. Usando config padrão/.env.")

        phpunit_cmd = [PHP_CMD, str(ARTISAN_FILE), "test", f"--env={PHPUNIT_ENV}"]
        exit_code, _, _ = run_command(phpunit_cmd, check=False, print_output=True)

        if exit_code != 0:
            log(f"Erro: Testes PHPUnit falharam (Código de Saída: {exit_code}).")
            overall_exit_code = exit_code
            if args.stop_on_failure:
                log("Parando execução devido à opção --stop-on-failure.")
                return overall_exit_code
        else:
            log("Sucesso: Testes PHPUnit concluídos.")
        print("-" * 40)
    else:
        log("[PHPUnit] Testes PHPUnit pulados conforme solicitado (--skip-phpunit).")
        print("-" * 40)

    # --- Execução dos Testes Dusk ---
    if not args.skip_dusk:
        log(f"[Dusk] Iniciando testes Laravel Dusk (Ambiente: {DUSK_ENV})...")
        dusk_setup_failed = False

        # 1. Verificar pré-requisitos do Dusk
        log("[Dusk] Verificando pré-requisitos...")
        if not DUSK_ENV_FILE.is_file():
             log(f"  Aviso: Arquivo '{DUSK_ENV_FILE.name}' não encontrado. Usando config padrão.")
        if not DUSK_TEST_DIR.is_dir():
            log(f"  Erro: Diretório '{DUSK_TEST_DIR.relative_to(BASE_DIR)}' não encontrado. Execute 'php artisan dusk:install'?")
            dusk_setup_failed = True

        chromedriver_path = get_chromedriver_path()
        if not chromedriver_path or not chromedriver_path.is_file():
            log(f"  Erro: ChromeDriver não encontrado em '{VENDOR_DIR / 'laravel' / 'dusk' / 'bin'}'. Execute 'php artisan dusk:chrome-driver --detect'?")
            dusk_setup_failed = True

        # 1.b Verificar se node_modules existe (necessário para npm run dev)
        if not (BASE_DIR / "node_modules").is_dir():
            log("  Erro: Diretório 'node_modules' não encontrado. Execute 'npm install'.")
            dusk_setup_failed = True

        if dusk_setup_failed:
            log("Erro: Falha na configuração/pré-requisitos do Dusk. Pulando testes Dusk.")
            if overall_exit_code == 0: overall_exit_code = 1 # Marca como erro
            if args.stop_on_failure:
                log("Parando execução devido à falha na configuração do Dusk e --stop-on-failure.")
                return overall_exit_code
        else:
            log("[Dusk] Pré-requisitos OK.")
            chromedriver_proc = None
            app_server_proc = None
            vite_proc = None # Variável para o processo Vite

            try: # Envolve o setup e execução do Dusk em try para garantir cleanup
                # 2. Iniciar ChromeDriver
                log(f"[Dusk] Iniciando ChromeDriver ({chromedriver_path.name}) na porta {DUSK_CHROMEDRIVER_PORT}...")
                chromedriver_proc = start_background_process(
                    [str(chromedriver_path), f"--port={DUSK_CHROMEDRIVER_PORT}"],
                    CHROMEDRIVER_LOG
                )
                log("  Aguardando inicialização do ChromeDriver (5s)...")
                time.sleep(5)
                if not check_process_running(chromedriver_proc, "ChromeDriver"):
                    dusk_setup_failed = True
                    if overall_exit_code == 0: overall_exit_code = 1
                    if args.stop_on_failure: return overall_exit_code # Sai dentro do try

                # 3. Iniciar Servidor da Aplicação
                if not dusk_setup_failed:
                    log(f"[Dusk] Iniciando servidor da aplicação na porta {DUSK_APP_PORT} (Ambiente: {DUSK_ENV})...")
                    serve_cmd = [PHP_CMD, str(ARTISAN_FILE), "serve", f"--port={DUSK_APP_PORT}", f"--env={DUSK_ENV}"]
                    app_server_proc = start_background_process(serve_cmd, DUSK_SERVE_LOG)
                    log("  Aguardando inicialização do servidor da aplicação (8s)...")
                    time.sleep(8)
                    if not check_process_running(app_server_proc, "Servidor App"):
                        dusk_setup_failed = True
                        if overall_exit_code == 0: overall_exit_code = 1
                        if args.stop_on_failure: return overall_exit_code # Sai dentro do try

                # 4. Iniciar Servidor Vite Dev
                if not dusk_setup_failed:
                    log("[Dusk] Iniciando servidor Vite Dev ('npm run dev')...")
                    vite_cmd = ["npm", "run", "dev"]
                    vite_proc = start_background_process(vite_cmd, VITE_DEV_LOG)
                    log("  Aguardando inicialização do Vite (10s)...") # Aumentado para 10s
                    time.sleep(10)
                    if not check_process_running(vite_proc, "Vite Dev Server"):
                        dusk_setup_failed = True
                        if overall_exit_code == 0: overall_exit_code = 1
                        if args.stop_on_failure: return overall_exit_code # Sai dentro do try

                # 5. Executar Testes Dusk
                if not dusk_setup_failed:
                    log("[Dusk] Executando testes Dusk...")
                    dusk_env_vars = os.environ.copy()
                    dusk_env_vars['APP_ENV'] = DUSK_ENV # Garante que o Artisan use o env correto
                    # Passa o .env específico para o comando dusk se necessário
                    # A run_command já passa o env correto para o subprocesso
                    dusk_cmd = [PHP_CMD, str(ARTISAN_FILE), "dusk", f"--env={DUSK_ENV}"]
                    exit_code_dusk, _, _ = run_command(
                        dusk_cmd,
                        check=False,
                        print_output=True,
                        env=dusk_env_vars # Passa o env explicitamente
                    )
                    if exit_code_dusk != 0:
                        log(f"Erro: Testes Dusk falharam (Código de Saída: {exit_code_dusk}). Verifique logs/screenshots.")
                        overall_exit_code = exit_code_dusk
                        if args.stop_on_failure:
                            log("Parando execução devido à falha nos testes Dusk e --stop-on-failure.")
                            return overall_exit_code # Sai dentro do try
                    else:
                        log("Sucesso: Testes Dusk concluídos.")
                else:
                     log("[Dusk] Pulando execução dos testes devido a falha no setup anterior.")

            finally:
                # O cleanup será chamado no finally do ponto de entrada principal
                # Não é necessário chamar aqui, para evitar chamadas duplas
                pass

        print("-" * 40)
    else:
        log("[Dusk] Testes Dusk pulados conforme solicitado (--skip-dusk).")
        print("-" * 40)

    return overall_exit_code

# --- Ponto de Entrada ---
if __name__ == "__main__":
    final_exit_code = 0
    try:
        # Cria o diretório de logs se não existir
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        final_exit_code = main()
    except Exception as e:
        log(f"Erro inesperado no script: {e}")
        traceback.print_exc()
        final_exit_code = 1 # Marca como erro geral
    finally:
        cleanup() # Garante que a limpeza ocorra
        log(f"Execução do script finalizada com código de saída: {final_exit_code}")
        sys.exit(final_exit_code)