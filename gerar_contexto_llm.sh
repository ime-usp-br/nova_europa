#!/bin/bash

# --- Configuração ---
# Diretório base para salvar os arquivos de contexto
OUTPUT_BASE_DIR="./code_context_llm"
# Hash do commit vazio do Git (usado para diff inicial)
EMPTY_TREE_COMMIT="4b825dc642cb6eb9a060e54bf8d69288fbee4904"
# Caminho para o executável do PHPStan (ajuste se necessário)
PHPSTAN_BIN="./vendor/bin/phpstan"
# Caminho para o executável do Artisan (ajuste se necessário)
ARTISAN_CMD="php artisan"
# Campos a serem extraídos de cada issue do GitHub via 'gh issue view'
GH_ISSUE_JSON_FIELDS="number,title,body,author,state,stateReason,assignees,labels,comments"

# Habilita saída em caso de erro e falha em pipelines
set -e
set -o pipefail

# --- Funções Auxiliares ---
# Função para verificar se um comando existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# --- Início do Script ---
echo "Iniciando a coleta de contexto para o LLM..."

# Cria diretório de saída baseado no timestamp (com segundos para maior unicidade)
TIMESTAMP=$(date +'%Y%m%d_%H%M%S')
TIMESTAMP_DIR="$OUTPUT_BASE_DIR/$TIMESTAMP"

echo "Criando diretório de saída: $TIMESTAMP_DIR"
mkdir -p "$TIMESTAMP_DIR"

# --- Coleta de Informações do Git ---
echo "Coletando informações do Git..."
# Adiciona todos os arquivos modificados e novos ao stage.
# ATENÇÃO: Isso modificará o estado do seu stage do Git.
git add .
# Gera logs e diffs
echo "  Gerando git log..."
git log > "$TIMESTAMP_DIR/git_log.txt"
echo "  Gerando git diff (Empty Tree -> HEAD)..."
git diff "$EMPTY_TREE_COMMIT" HEAD > "$TIMESTAMP_DIR/git_diff_empty_tree_to_head.txt"
echo "  Gerando git diff (--cached)..."
git diff --cached > "$TIMESTAMP_DIR/git_diff_cached.txt"

# --- Coleta de Informações do Laravel Artisan ---
echo "Coletando informações do Laravel Artisan..."
# (Comandos Artisan permanecem os mesmos da versão anterior)
echo "  Gerando artisan route:list..."
$ARTISAN_CMD route:list --json > "$TIMESTAMP_DIR/artisan_route_list.json" 2>/dev/null || $ARTISAN_CMD route:list > "$TIMESTAMP_DIR/artisan_route_list.txt"
echo "  Gerando artisan about..."
$ARTISAN_CMD about --json > "$TIMESTAMP_DIR/artisan_about.json" 2>/dev/null || $ARTISAN_CMD about > "$TIMESTAMP_DIR/artisan_about.txt"
echo "  Gerando artisan channel:list..."
if $ARTISAN_CMD list | grep -q channel:list; then
    $ARTISAN_CMD channel:list > "$TIMESTAMP_DIR/artisan_channel_list.txt"
else
    echo "  Comando 'channel:list' não encontrado. Pulando."
    touch "$TIMESTAMP_DIR/artisan_channel_list.txt"
fi
echo "  Gerando artisan db:show..."
$ARTISAN_CMD db:show --json > "$TIMESTAMP_DIR/artisan_db_show.json" 2>/dev/null || $ARTISAN_CMD db:show > "$TIMESTAMP_DIR/artisan_db_show.txt"
echo "  Gerando artisan event:list..."
$ARTISAN_CMD event:list > "$TIMESTAMP_DIR/artisan_event_list.txt"
echo "  Gerando artisan permission:show..."
if $ARTISAN_CMD list | grep -q permission:show; then
    $ARTISAN_CMD permission:show > "$TIMESTAMP_DIR/artisan_permission_show.txt"
else
     echo "  Comando 'permission:show' não encontrado (requer spatie/laravel-permission?). Pulando."
     touch "$TIMESTAMP_DIR/artisan_permission_show.txt"
fi
echo "  Gerando artisan queue:failed..."
$ARTISAN_CMD queue:failed > "$TIMESTAMP_DIR/artisan_queue_failed.txt"
echo "  Gerando artisan schedule:list..."
$ARTISAN_CMD schedule:list > "$TIMESTAMP_DIR/artisan_schedule_list.txt"


# --- Coleta de Informações do GitHub ---
echo "Coletando informações das Issues do GitHub (exceto 'Closed as not planned')..."

# Verifica se os comandos 'gh' e 'jq' estão disponíveis
if ! command_exists gh; then
    echo "  ERRO: Comando 'gh' (GitHub CLI) não encontrado. Pulando a coleta de dados das issues."
    echo '{ "error": "Comando gh não encontrado" }' > "$TIMESTAMP_DIR/github_issues_error.json"
elif ! command_exists jq; then
    echo "  ERRO: Comando 'jq' não encontrado. É necessário para processar a lista de issues. Pulando a coleta."
    echo '{ "error": "Comando jq não encontrado" }' > "$TIMESTAMP_DIR/github_issues_error.json"
else
    # Cria um subdiretório para as issues
    GITHUB_ISSUES_DIR="$TIMESTAMP_DIR/github_issues"
    mkdir -p "$GITHUB_ISSUES_DIR"
    echo "  Issues serão salvas em: $GITHUB_ISSUES_DIR"

    # Lista os números de TODAS as issues (abertas e fechadas) e filtra usando jq
    # para excluir aquelas onde stateReason é "NOT_PLANNED".
    # Em seguida, extrai apenas os números das issues restantes.
    echo "  Listando e filtrando issues..."
    gh issue list --state all --limit 500 --json number,stateReason -q 'map(select(.stateReason != "NOT_PLANNED")) | .[].number' | while read -r issue_number; do
    # Adicionado --limit 500 como exemplo, ajuste se tiver muitas issues.
        if [[ -n "$issue_number" ]]; then
            echo "  Coletando detalhes da Issue #$issue_number..."
            # Tenta buscar os detalhes da issue. Adicionamos stateReason aos campos.
            gh issue view "$issue_number" --json "$GH_ISSUE_JSON_FIELDS" > "$GITHUB_ISSUES_DIR/github_issue_${issue_number}_details.json" || \
                echo "  AVISO: Falha ao coletar detalhes da Issue #$issue_number. Verifique permissões ou se a issue existe."
        fi
    done

    # Verifica se algum arquivo foi criado no diretório de issues
    if [ -z "$(ls -A $GITHUB_ISSUES_DIR 2>/dev/null)" ]; then # Adicionado 2>/dev/null para o caso do diretório não ser criado
        echo "  Nenhuma issue encontrada (após filtrar 'Closed as not planned') ou nenhuma pôde ser baixada."
        # Opcional: remover o diretório vazio
        # rmdir "$GITHUB_ISSUES_DIR"
        # Ou criar um arquivo indicando que não há issues
        if [ -d "$GITHUB_ISSUES_DIR" ]; then # Só cria o arquivo se o diretório existir
           echo '{ "message": "Nenhuma issue encontrada (após filtrar) ou baixada." }' > "$GITHUB_ISSUES_DIR/no_issues_found.json"
        fi
    else
       echo "  Coleta de issues filtradas concluída."
    fi
fi

# --- Execução do PHPStan ---
echo "Executando análise estática com PHPStan..."
# Verifica se o binário do PHPStan existe
if [ -f "$PHPSTAN_BIN" ]; then
    $PHPSTAN_BIN analyse > "$TIMESTAMP_DIR/phpstan_analysis.txt" 2>&1 || true
else
    echo "  Binário do PHPStan não encontrado em '$PHPSTAN_BIN'. Pulando análise."
    echo "PHPStan não executado: Binário não encontrado em $PHPSTAN_BIN" > "$TIMESTAMP_DIR/phpstan_analysis.txt"
fi

# --- Finalização ---
echo ""
echo "-----------------------------------------------------"
echo "Coleta de contexto para LLM concluída!"
echo "Arquivos salvos em: $TIMESTAMP_DIR"
echo "-----------------------------------------------------"

exit 0