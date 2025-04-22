#!/bin/bash

# ==============================================================================
# run_tests.sh
#
# Script para executar as suítes de teste do projeto (PHPUnit e Laravel Dusk).
# Gerencia o início e parada dos serviços necessários para os testes Dusk.
#
# Uso:
#   ./scripts/run_tests.sh [--skip-phpunit] [--skip-dusk] [--stop-on-failure]
#
# Opções:
#   --skip-phpunit      Pula a execução dos testes PHPUnit.
#   --skip-dusk         Pula a execução dos testes Laravel Dusk.
#   --stop-on-failure   Para a execução imediatamente se uma suíte de teste falhar.
# ==============================================================================

# --- Configurações ---
PHP_ARTISAN="php artisan"
PHPUNIT_ENV="testing"
DUSK_ENV="dusk.local"
DUSK_APP_PORT="8000"       # Porta padrão para o servidor da aplicação durante testes Dusk
DUSK_CHROMEDRIVER_PORT="9515" # Porta padrão para o ChromeDriver
BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." >/dev/null 2>&1 && pwd )" # Raiz do projeto

# --- Variáveis de Estado ---
skip_phpunit=false
skip_dusk=false
stop_on_failure=false
overall_exit_code=0
app_server_pid=""
chromedriver_pid=""
dusk_setup_failed=false

# --- Funções Auxiliares ---

# Função para imprimir mensagens de log com timestamp
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Função para verificar se um comando existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Função para parar processos em background e limpar
cleanup() {
    log "Iniciando limpeza..."
    if [[ -n "$app_server_pid" ]]; then
        log "  Parando servidor da aplicação (PID: $app_server_pid)..."
        # Mata o processo e seus descendentes (grupo de processos)
        kill -TERM -$app_server_pid > /dev/null 2>&1 || kill -KILL -$app_server_pid > /dev/null 2>&1
        wait "$app_server_pid" 2>/dev/null
        app_server_pid=""
    fi
    if [[ -n "$chromedriver_pid" ]]; then
        log "  Parando ChromeDriver (PID: $chromedriver_pid)..."
        kill -TERM $chromedriver_pid > /dev/null 2>&1 || kill -KILL $chromedriver_pid > /dev/null 2>&1
        wait "$chromedriver_pid" 2>/dev/null
        chromedriver_pid=""
    fi
    log "Limpeza concluída."
}

# Registra a função cleanup para ser executada na saída do script (normal ou erro)
trap cleanup EXIT

# --- Processamento de Argumentos ---
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --skip-phpunit)
        skip_phpunit=true
        shift # past argument
        ;;
        --skip-dusk)
        skip_dusk=true
        shift # past argument
        ;;
        --stop-on-failure)
        stop_on_failure=true
        shift # past argument
        ;;
        *)    # argumento desconhecido
        log "Erro: Opção desconhecida $1"
        exit 1
        ;;
    esac
done

# --- Validação de Ambiente ---
log "Validando ambiente..."
if ! command_exists php; then
    log "Erro Fatal: Comando 'php' não encontrado. Instale o PHP CLI."
    exit 1
fi
if [ ! -f "$BASE_DIR/artisan" ]; then
    log "Erro Fatal: Arquivo 'artisan' não encontrado em $BASE_DIR. Execute este script da raiz do projeto."
    exit 1
fi
if [ ! -d "$BASE_DIR/vendor" ]; then
    log "Erro Fatal: Diretório 'vendor' não encontrado. Execute 'composer install'."
    exit 1
fi
log "Validação de ambiente básica OK."
echo # Linha em branco para separar

# --- Execução dos Testes PHPUnit ---
if [ "$skip_phpunit" = false ]; then
    log "[PHPUnit] Iniciando testes PHPUnit (Ambiente: $PHPUNIT_ENV)..."
    cd "$BASE_DIR" || exit 1 # Garante que estamos no diretório correto
    if [ ! -f ".env.$PHPUNIT_ENV" ] && [ "$PHPUNIT_ENV" == "testing" ]; then
         log "  Aviso: Arquivo '.env.$PHPUNIT_ENV' não encontrado. PHPUnit usará as configurações padrão ou do .env principal."
    fi
    $PHP_ARTISAN test --env=$PHPUNIT_ENV
    exit_code=$?
    if [ $exit_code -ne 0 ]; then
        log "Erro: Testes PHPUnit falharam (Código de Saída: $exit_code)."
        overall_exit_code=$exit_code
        if [ "$stop_on_failure" = true ]; then
            log "Parando execução devido à opção --stop-on-failure."
            exit $overall_exit_code
        fi
    else
        log "Sucesso: Testes PHPUnit concluídos."
    fi
    echo # Linha em branco para separar
else
    log "[PHPUnit] Testes PHPUnit pulados conforme solicitado (--skip-phpunit)."
    echo # Linha em branco para separar
fi

# --- Execução dos Testes Dusk ---
if [ "$skip_dusk" = false ]; then
    log "[Dusk] Iniciando testes Laravel Dusk (Ambiente: $DUSK_ENV)..."
    cd "$BASE_DIR" || exit 1

    # 1. Verificar pré-requisitos do Dusk
    log "[Dusk] Verificando pré-requisitos..."
    if [ ! -f "$BASE_DIR/.env.$DUSK_ENV" ]; then
         log "  Aviso: Arquivo '.env.$DUSK_ENV' não encontrado. Dusk pode usar configuração incorreta."
    fi
    if [ ! -d "$BASE_DIR/tests/Browser" ]; then
        log "  Erro: Diretório 'tests/Browser' não encontrado. Execute 'php artisan dusk:install'?"
        dusk_setup_failed=true
    fi
    if [ ! -f "$BASE_DIR/vendor/laravel/dusk/bin/chromedriver-linux" ] && \
       [ ! -f "$BASE_DIR/vendor/laravel/dusk/bin/chromedriver-mac-x64" ] && \
       [ ! -f "$BASE_DIR/vendor/laravel/dusk/bin/chromedriver-mac-arm64" ] && \
       [ ! -f "$BASE_DIR/vendor/laravel/dusk/bin/chromedriver-win.exe" ]; then
        log "  Erro: ChromeDriver não encontrado em 'vendor/laravel/dusk/bin/'. Execute 'php artisan dusk:chrome-driver --detect'?"
        dusk_setup_failed=true
    fi

    if $dusk_setup_failed; then
        log "Erro: Falha na configuração do Dusk. Pulando testes Dusk."
        # Define um código de erro se a configuração falhar, mas não necessariamente para
        if [ $overall_exit_code -eq 0 ]; then overall_exit_code=1; fi
        if [ "$stop_on_failure" = true ]; then
            log "Parando execução devido à falha na configuração do Dusk e --stop-on-failure."
            exit $overall_exit_code
        fi
    else
        log "[Dusk] Pré-requisitos OK."

        # 2. Iniciar ChromeDriver em background
        log "[Dusk] Iniciando ChromeDriver na porta $DUSK_CHROMEDRIVER_PORT..."
        CHROMEDRIVER_PATH=""
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            CHROMEDRIVER_PATH="$BASE_DIR/vendor/laravel/dusk/bin/chromedriver-linux"
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            if [[ "$(uname -m)" == "arm64" ]]; then
                CHROMEDRIVER_PATH="$BASE_DIR/vendor/laravel/dusk/bin/chromedriver-mac-arm64"
            else
                CHROMEDRIVER_PATH="$BASE_DIR/vendor/laravel/dusk/bin/chromedriver-mac-x64"
            fi
        elif [[ "$OSTYPE" == "cygwin" || "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
             CHROMEDRIVER_PATH="$BASE_DIR/vendor/laravel/dusk/bin/chromedriver-win.exe"
        else
             log "  Erro: Sistema operacional não suportado para iniciar ChromeDriver automaticamente."
             # Não define overall_exit_code, pois o usuário pode iniciar manualmente
        fi

        if [[ -n "$CHROMEDRIVER_PATH" && -f "$CHROMEDRIVER_PATH" ]]; then
            "$CHROMEDRIVER_PATH" --port=$DUSK_CHROMEDRIVER_PORT > "$BASE_DIR/storage/logs/chromedriver.log" 2>&1 &
            chromedriver_pid=$!
            log "  ChromeDriver iniciado (PID: $chromedriver_pid). Aguardando inicialização..."
            sleep 5 # Espera o chromedriver iniciar
            # Verifica se ainda está rodando
            if ! ps -p $chromedriver_pid > /dev/null; then
                 log "  Erro: ChromeDriver falhou ao iniciar. Verifique $BASE_DIR/storage/logs/chromedriver.log"
                 chromedriver_pid="" # Limpa o PID se falhou
                 if [ $overall_exit_code -eq 0 ]; then overall_exit_code=1; fi
                 if [ "$stop_on_failure" = true ]; then exit $overall_exit_code; fi
                 dusk_setup_failed=true # Marca falha no setup para não rodar dusk:tests
            else
                 log "  ChromeDriver parece estar rodando."
            fi
        else
            log "  Aviso: ChromeDriver não encontrado ou OS não suportado para início automático. Certifique-se de que esteja rodando na porta $DUSK_CHROMEDRIVER_PORT."
            # Permite continuar, mas os testes podem falhar
        fi

        # 3. Iniciar Servidor da Aplicação em background (APENAS se chromedriver iniciou)
        if [ "$dusk_setup_failed" = false ]; then
            log "[Dusk] Iniciando servidor da aplicação na porta $DUSK_APP_PORT (Ambiente: $DUSK_ENV)..."
            # Usar setsid para criar um novo grupo de processos, permitindo matar o servidor e seus filhos
            setsid $PHP_ARTISAN serve --port=$DUSK_APP_PORT --env=$DUSK_ENV > "$BASE_DIR/storage/logs/dusk_serve.log" 2>&1 &
            app_server_pid=$!
            # Dorme um pouco para dar tempo ao servidor iniciar
            log "  Servidor iniciado (PID: $app_server_pid). Aguardando inicialização..."
            sleep 8
             # Verifica se ainda está rodando
            if ! ps -p $app_server_pid > /dev/null; then
                 log "  Erro: Servidor da aplicação falhou ao iniciar. Verifique $BASE_DIR/storage/logs/dusk_serve.log"
                 app_server_pid="" # Limpa o PID
                 if [ $overall_exit_code -eq 0 ]; then overall_exit_code=1; fi
                 if [ "$stop_on_failure" = true ]; then exit $overall_exit_code; fi
                 dusk_setup_failed=true # Marca falha no setup
            else
                 log "  Servidor da aplicação parece estar rodando."
            fi
        fi

        # 4. Executar Testes Dusk (APENAS se setup não falhou)
        if [ "$dusk_setup_failed" = false ]; then
            log "[Dusk] Executando testes Dusk..."
            $PHP_ARTISAN dusk --env=$DUSK_ENV
            exit_code=$?
            if [ $exit_code -ne 0 ]; then
                log "Erro: Testes Dusk falharam (Código de Saída: $exit_code). Verifique os logs e screenshots em tests/Browser/."
                overall_exit_code=$exit_code
                if [ "$stop_on_failure" = true ]; then
                    log "Parando execução devido à falha nos testes Dusk e --stop-on-failure."
                    # Cleanup será chamado pelo trap
                    exit $overall_exit_code
                fi
            else
                log "Sucesso: Testes Dusk concluídos."
            fi
        else
             log "[Dusk] Pulando execução dos testes devido a falha no setup anterior."
        fi
    fi # Fim do if $dusk_setup_failed
    echo # Linha em branco para separar
else
    log "[Dusk] Testes Dusk pulados conforme solicitado (--skip-dusk)."
    echo # Linha em branco para separar
fi

# --- Relatório Final ---
log "----------------------------------------"
if [ $overall_exit_code -eq 0 ]; then
    log "SUCESSO GERAL: Todas as suítes de teste executadas passaram."
else
    log "FALHA GERAL: Pelo menos uma suíte de teste falhou (Código de Saída Final: $overall_exit_code)."
fi
log "----------------------------------------"

# Cleanup será chamado automaticamente pelo trap na saída
exit $overall_exit_code