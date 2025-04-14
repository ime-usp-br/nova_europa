#!/bin/bash

# ==============================================================================
# gerar_contexto_llm.sh (v2.2)
#
# Coleta informações de contexto abrangentes de um projeto de desenvolvimento
# (com foco em Laravel/PHP) e seu ambiente para auxiliar LLMs.
#
# Inclui dados do Git, GitHub (repo, issues, actions, security), Laravel Artisan,
# PHPStan, ambiente do SO, dependências, estrutura do projeto e configuração ativa.
# Tenta detectar o gerenciador de pacotes para sugerir comandos de instalação
# caso ferramentas externas como 'tree' ou 'cloc' não sejam encontradas.
#
# Coloca TODOS os arquivos de saída, incluindo detalhes de issues, no diretório
# raiz do timestamp para facilitar o upload para LLMs.
#
# Dependências Base:
#   - Bash 4.3+ (para namerefs)
#   - Git
#   - PHP CLI
#   - sed, awk, tr, rev, grep, cut, date, head, find, wc
# Dependências Opcionais (script tentará executar se encontradas):
#   - gh (GitHub CLI): Para buscar detalhes do repo, issues, actions, security.
#   - jq: Para processar JSON do 'gh'.
#   - tree: Para visualizar estrutura de diretórios.
#   - cloc: Para contar linhas de código.
#   - composer: Para gerenciar dependências PHP.
#   - npm: Para gerenciar dependências Node.js.
#   - lsb_release: Para informações da distro Linux.
# ==============================================================================

# --- Configuração ---
OUTPUT_BASE_DIR="./code_context_llm"
EMPTY_TREE_COMMIT="4b825dc642cb6eb9a060e54bf8d69288fbee4904"
PHPSTAN_BIN="./vendor/bin/phpstan"
ARTISAN_CMD="php artisan"
GH_ISSUE_JSON_FIELDS="number,title,body,author,state,stateReason,assignees,labels,comments"
TREE_DEPTH=3
CLOC_EXCLUDE_REGEX='(vendor|node_modules|storage|public/build|\.git|\.idea|\.vscode|\.fleet|code_context_llm)'
TREE_IGNORE_PATTERN='vendor|node_modules|storage/framework|storage/logs|public/build|.git|.idea|.vscode|.fleet|code_context_llm'
GH_ISSUE_LIST_LIMIT=500
GIT_TAG_LIMIT=10
GH_RUN_LIST_LIMIT=10
GH_PR_LIST_LIMIT=20
GH_RELEASE_LIST_LIMIT=10

# Habilita saída em caso de erro e falha em pipelines
# set -e # Removido para permitir que comandos individuais falhem graciosamente
set -o pipefail

# --- Funções Auxiliares ---
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

suggest_install() {
    local cmd_name="$1"
    shift
    local pkg_name="$1"
    pkg_name="${pkg_name:-$cmd_name}"

    echo "  AVISO: Comando '$cmd_name' não encontrado."
    echo "  > Para coletar esta informação, tente instalar o pacote '$pkg_name'."
    if command_exists apt; then
        echo "  > Sugestão (Debian/Ubuntu): sudo apt update && sudo apt install $pkg_name"
    elif command_exists yum; then
        echo "  > Sugestão (CentOS/RHEL/Fedora antigo): sudo yum install $pkg_name"
    elif command_exists dnf; then
        echo "  > Sugestão (Fedora/RHEL recente): sudo dnf install $pkg_name"
    elif command_exists pacman; then
        echo "  > Sugestão (Arch): sudo pacman -S $pkg_name"
    elif command_exists brew; then
        echo "  > Sugestão (macOS): brew install $pkg_name"
    else
        echo "  > Verifique o gerenciador de pacotes do seu sistema para instalar '$pkg_name'."
    fi
}

# --- Início do Script ---
echo "Iniciando a coleta de contexto para o LLM..."
echo "Versão do Script: 2.2 (Data: $(date +'%Y-%m-%d'))"

TIMESTAMP=$(date +'%Y%m%d_%H%M%S')
TIMESTAMP_DIR="$OUTPUT_BASE_DIR/$TIMESTAMP"

echo "Criando diretório de saída: $TIMESTAMP_DIR"
mkdir -p "$TIMESTAMP_DIR"

# --- Coleta de Informações do Ambiente ---
echo "[1/8] Coletando informações do Ambiente..."
echo "  Coletando informações do sistema (uname)..."
uname -a > "$TIMESTAMP_DIR/env_uname.txt" 2>/dev/null || echo "Falha ao executar uname" > "$TIMESTAMP_DIR/env_uname.txt"

echo "  Coletando informações da distribuição Linux..."
if command_exists lsb_release; then
    lsb_release -a > "$TIMESTAMP_DIR/env_distro_info.txt" 2>&1
elif [ -f /etc/os-release ]; then
    cat /etc/os-release > "$TIMESTAMP_DIR/env_distro_info.txt" 2>&1
elif [ -f /etc/debian_version ]; then
    echo "Debian $(cat /etc/debian_version)" > "$TIMESTAMP_DIR/env_distro_info.txt"
elif [ -f /etc/redhat-release ]; then
    cat /etc/redhat-release > "$TIMESTAMP_DIR/env_distro_info.txt"
else
    echo "Não foi possível determinar a distribuição Linux automaticamente." > "$TIMESTAMP_DIR/env_distro_info.txt"
fi

echo "  Coletando versão do PHP..."
if command_exists php; then
    php -v > "$TIMESTAMP_DIR/env_php_version.txt" 2>&1
else
    echo "Comando 'php' não encontrado." > "$TIMESTAMP_DIR/env_php_version.txt"
fi

echo "  Coletando módulos PHP carregados..."
if command_exists php; then
    php -m > "$TIMESTAMP_DIR/env_php_modules.txt" 2>&1
else
     echo "Comando 'php' não encontrado." > "$TIMESTAMP_DIR/env_php_modules.txt"
fi

echo "  Coletando versão do Composer..."
if command_exists composer; then
    composer --version > "$TIMESTAMP_DIR/env_composer_version.txt" 2>&1
else
     suggest_install "composer"
     echo "Composer não encontrado." > "$TIMESTAMP_DIR/env_composer_version.txt"
fi

echo "  Coletando versões Node/NPM..."
if command_exists node; then node -v > "$TIMESTAMP_DIR/env_node_version.txt" 2>&1; else suggest_install "node" "nodejs"; echo "Node não encontrado." > "$TIMESTAMP_DIR/env_node_version.txt"; fi
if command_exists npm; then npm -v > "$TIMESTAMP_DIR/env_npm_version.txt" 2>&1; else suggest_install "npm"; echo "NPM não encontrado." > "$TIMESTAMP_DIR/env_npm_version.txt"; fi

# --- Coleta de Informações do Git ---
echo "[2/8] Coletando informações do Git..."
if ! command_exists git; then
    suggest_install "git"
    echo "ERRO FATAL: Comando 'git' não encontrado. Abortando."
    exit 1
fi
# echo "  Adicionando arquivos modificados/novos ao stage (git add .)..." # Comentado por padrão
# git add .

echo "  Gerando git log..."
git log > "$TIMESTAMP_DIR/git_log.txt" 2>/dev/null || echo "Falha ao gerar git log" > "$TIMESTAMP_DIR/git_log.txt"
echo "  Gerando git diff (Empty Tree -> HEAD)..."
git diff "$EMPTY_TREE_COMMIT" HEAD > "$TIMESTAMP_DIR/git_diff_empty_tree_to_head.txt" 2>/dev/null || echo "Falha ao gerar git diff (empty tree)" > "$TIMESTAMP_DIR/git_diff_empty_tree_to_head.txt"
echo "  Gerando git diff (--cached)..."
git diff --cached > "$TIMESTAMP_DIR/git_diff_cached.txt" 2>/dev/null || echo "Falha ao gerar git diff (--cached)" > "$TIMESTAMP_DIR/git_diff_cached.txt"
echo "  Gerando git diff (unstaged)..."
git diff > "$TIMESTAMP_DIR/git_diff_unstaged.txt" 2>/dev/null || echo "Falha ao gerar git diff (unstaged)" > "$TIMESTAMP_DIR/git_diff_unstaged.txt"
echo "  Gerando git status..."
git status > "$TIMESTAMP_DIR/git_status.txt" 2>/dev/null || echo "Falha ao gerar git status" > "$TIMESTAMP_DIR/git_status.txt"
echo "  Listando arquivos rastreados pelo Git..."
git ls-files > "$TIMESTAMP_DIR/git_ls_files.txt" 2>/dev/null || echo "Falha ao executar git ls-files" > "$TIMESTAMP_DIR/git_ls_files.txt"
echo "  Listando tags Git recentes..."
git tag --sort=-creatordate | head -n "$GIT_TAG_LIMIT" > "$TIMESTAMP_DIR/git_recent_tags.txt" 2>/dev/null || echo "Nenhuma tag encontrada ou falha ao listar tags." > "$TIMESTAMP_DIR/git_recent_tags.txt"

# --- Coleta de Informações Adicionais do GitHub (Repo, Workflow, Segurança) ---
echo "[3/8] Coletando contexto adicional do GitHub (Repo, Workflow, Segurança)..."
if ! command_exists gh; then
    suggest_install "gh" "gh"
    echo "  ERRO: Comando 'gh' (GitHub CLI) não encontrado. Pulando esta seção."
    # Cria arquivos vazios ou com erro para indicar a ausência
    touch "$TIMESTAMP_DIR/gh_run_list.txt" "$TIMESTAMP_DIR/gh_workflow_list.txt" "$TIMESTAMP_DIR/gh_pr_list.txt" \
          "$TIMESTAMP_DIR/gh_release_list.txt" "$TIMESTAMP_DIR/gh_secret_list.txt" "$TIMESTAMP_DIR/gh_variable_list.txt" \
          "$TIMESTAMP_DIR/gh_repo_view.txt" "$TIMESTAMP_DIR/gh_ruleset_list.txt" "$TIMESTAMP_DIR/gh_codescanning_alert_list.txt" \
          "$TIMESTAMP_DIR/gh_dependabot_alert_list.txt"
else
    echo "  Listando execuções recentes do GitHub Actions (limite $GH_RUN_LIST_LIMIT)..."
    gh run list --limit "$GH_RUN_LIST_LIMIT" > "$TIMESTAMP_DIR/gh_run_list.txt" 2>&1 || echo "Falha ao listar runs do Actions (verifique permissões/habilitação)." > "$TIMESTAMP_DIR/gh_run_list.txt"

    echo "  Listando workflows do GitHub Actions..."
    gh workflow list > "$TIMESTAMP_DIR/gh_workflow_list.txt" 2>&1 || echo "Falha ao listar workflows." > "$TIMESTAMP_DIR/gh_workflow_list.txt"

    echo "  Listando Pull Requests recentes (limite $GH_PR_LIST_LIMIT)..."
    gh pr list --state all --limit "$GH_PR_LIST_LIMIT" > "$TIMESTAMP_DIR/gh_pr_list.txt" 2>&1 || echo "Falha ao listar Pull Requests." > "$TIMESTAMP_DIR/gh_pr_list.txt"

    echo "  Listando Releases recentes (limite $GH_RELEASE_LIST_LIMIT)..."
    gh release list --limit "$GH_RELEASE_LIST_LIMIT" > "$TIMESTAMP_DIR/gh_release_list.txt" 2>&1 || echo "Falha ao listar Releases (ou nenhuma encontrada)." > "$TIMESTAMP_DIR/gh_release_list.txt"

    echo "  Listando nomes de Secrets do GitHub (requer permissão)..."
    gh secret list > "$TIMESTAMP_DIR/gh_secret_list.txt" 2>&1 || echo "Falha ao listar Secrets (verifique permissões admin/owner)." > "$TIMESTAMP_DIR/gh_secret_list.txt"

    echo "  Listando nomes de Variables do GitHub (requer permissão)..."
    gh variable list > "$TIMESTAMP_DIR/gh_variable_list.txt" 2>&1 || echo "Falha ao listar Variables (verifique permissões)." > "$TIMESTAMP_DIR/gh_variable_list.txt"

    echo "  Coletando metadados do repositório GitHub..."
     gh repo view --json name,description,homepageUrl,topics,createdAt,updatedAt,pushedAt > "$TIMESTAMP_DIR/gh_repo_view.json" 2>&1 || \
     gh repo view > "$TIMESTAMP_DIR/gh_repo_view.txt" 2>&1 || \
     echo "Falha ao obter informações do repositório." > "$TIMESTAMP_DIR/gh_repo_view.txt"
     if [ -f "$TIMESTAMP_DIR/gh_repo_view.txt" ] && [ -f "$TIMESTAMP_DIR/gh_repo_view.json" ] && [ -s "$TIMESTAMP_DIR/gh_repo_view.txt" ]; then rm "$TIMESTAMP_DIR/gh_repo_view.json"; fi

    echo "  Listando Rulesets/Branch Protection Rules (requer permissão)..."
    if gh ruleset list --help > /dev/null 2>&1; then
         gh ruleset list > "$TIMESTAMP_DIR/gh_ruleset_list.txt" 2>&1 || echo "Falha ao listar Rulesets (verifique permissões)." > "$TIMESTAMP_DIR/gh_ruleset_list.txt"
    # elif gh rules list --help > /dev/null 2>&1; then # Exemplo para versões futuras/diferentes
    #      gh rules list > "$TIMESTAMP_DIR/gh_rules_list.txt" 2>&1 || echo "Falha ao listar Rules (verifique permissões)." > "$TIMESTAMP_DIR/gh_rules_list.txt"
    else
         echo "Comando 'gh ruleset list' (ou similar) não encontrado nesta versão do gh." > "$TIMESTAMP_DIR/gh_ruleset_list.txt"
    fi

    echo "  Listando alertas do Code Scanning (requer permissão/GHAS)..."
    if gh help code-scanning > /dev/null 2>&1 && gh code-scanning list --help > /dev/null 2>&1 ; then # Verifica se o subcommand existe
         gh code-scanning alert list > "$TIMESTAMP_DIR/gh_codescanning_alert_list.txt" 2>&1 || echo "Falha ao listar alertas Code Scanning (verifique permissões/GHAS)." > "$TIMESTAMP_DIR/gh_codescanning_alert_list.txt"
    else
         echo "Comando 'gh code-scanning alert list' não encontrado/disponível nesta versão do gh ou para este repo." > "$TIMESTAMP_DIR/gh_codescanning_alert_list.txt"
    fi

    echo "  Listando alertas do Dependabot (requer permissão/Dependabot)..."
     if gh help dependabot > /dev/null 2>&1 && gh dependabot alert list --help > /dev/null 2>&1 ; then # Verifica se o subcommand existe
         gh dependabot alert list > "$TIMESTAMP_DIR/gh_dependabot_alert_list.txt" 2>&1 || echo "Falha ao listar alertas Dependabot (verifique permissões/Dependabot)." > "$TIMESTAMP_DIR/gh_dependabot_alert_list.txt"
     else
         echo "Comando 'gh dependabot alert list' não encontrado/disponível nesta versão do gh ou para este repo." > "$TIMESTAMP_DIR/gh_dependabot_alert_list.txt"
     fi
fi

# --- Coleta de Informações do Laravel Artisan ---
echo "[4/8] Coletando informações do Laravel Artisan..."
if ! command_exists php; then
    echo "  Pulando comandos Artisan pois 'php' não foi encontrado."
else
    echo "  Gerando artisan route:list..."
    $ARTISAN_CMD route:list --json > "$TIMESTAMP_DIR/artisan_route_list.json" 2>/dev/null || $ARTISAN_CMD route:list > "$TIMESTAMP_DIR/artisan_route_list.txt" 2>/dev/null || echo "Falha ao gerar lista de rotas." > "$TIMESTAMP_DIR/artisan_route_list.txt"
    echo "  Gerando artisan about..."
    $ARTISAN_CMD about --json > "$TIMESTAMP_DIR/artisan_about.json" 2>/dev/null || $ARTISAN_CMD about > "$TIMESTAMP_DIR/artisan_about.txt" 2>/dev/null || echo "Falha ao gerar 'about'." > "$TIMESTAMP_DIR/artisan_about.txt"
    echo "  Gerando artisan channel:list..."
    if $ARTISAN_CMD list | grep -q channel:list; then
        $ARTISAN_CMD channel:list > "$TIMESTAMP_DIR/artisan_channel_list.txt" 2>&1 || echo "Falha ao executar channel:list" > "$TIMESTAMP_DIR/artisan_channel_list.txt"
    else
        echo "  Comando 'channel:list' não encontrado. Pulando." > "$TIMESTAMP_DIR/artisan_channel_list.txt"
    fi
    echo "  Gerando artisan db:show..."
    $ARTISAN_CMD db:show --json > "$TIMESTAMP_DIR/artisan_db_show.json" 2>/dev/null || $ARTISAN_CMD db:show > "$TIMESTAMP_DIR/artisan_db_show.txt" 2>/dev/null || echo "Falha ao executar db:show (verifique conexão com DB)." > "$TIMESTAMP_DIR/artisan_db_show.txt"
    echo "  Gerando artisan event:list..."
    $ARTISAN_CMD event:list > "$TIMESTAMP_DIR/artisan_event_list.txt" 2>&1 || echo "Falha ao executar event:list" > "$TIMESTAMP_DIR/artisan_event_list.txt"
    echo "  Gerando artisan permission:show..."
    if $ARTISAN_CMD list | grep -q permission:show; then
        $ARTISAN_CMD permission:show > "$TIMESTAMP_DIR/artisan_permission_show.txt" 2>&1 || echo "Falha ao executar permission:show" > "$TIMESTAMP_DIR/artisan_permission_show.txt"
    else
         echo "  Comando 'permission:show' não encontrado (requer spatie/laravel-permission?). Pulando." > "$TIMESTAMP_DIR/artisan_permission_show.txt"
    fi
    echo "  Gerando artisan queue:failed..."
    $ARTISAN_CMD queue:failed > "$TIMESTAMP_DIR/artisan_queue_failed.txt" 2>&1 || echo "Falha ao executar queue:failed" > "$TIMESTAMP_DIR/artisan_queue_failed.txt"
    echo "  Gerando artisan schedule:list..."
    $ARTISAN_CMD schedule:list > "$TIMESTAMP_DIR/artisan_schedule_list.txt" 2>&1 || echo "Falha ao executar schedule:list" > "$TIMESTAMP_DIR/artisan_schedule_list.txt"
    echo "  Verificando ambiente Laravel..."
    $ARTISAN_CMD env > "$TIMESTAMP_DIR/artisan_env.txt" 2>&1 || echo "Falha ao executar env" > "$TIMESTAMP_DIR/artisan_env.txt"
    echo "  Verificando status das migrations..."
    $ARTISAN_CMD migrate:status > "$TIMESTAMP_DIR/artisan_migrate_status.txt" 2>&1 || echo "Falha ao executar migrate:status (verifique conexão com DB)." > "$TIMESTAMP_DIR/artisan_migrate_status.txt"
    echo "  Mostrando configurações Laravel (app, database)..."
    if $ARTISAN_CMD list | grep -q config:show; then
        $ARTISAN_CMD config:show app > "$TIMESTAMP_DIR/artisan_config_show_app.txt" 2>&1 || echo "Falha ao executar config:show app" > "$TIMESTAMP_DIR/artisan_config_show_app.txt"
        $ARTISAN_CMD config:show database > "$TIMESTAMP_DIR/artisan_config_show_database.txt" 2>&1 || echo "Falha ao executar config:show database" > "$TIMESTAMP_DIR/artisan_config_show_database.txt"
    else
        echo "  Comando 'config:show' não disponível. Copiando arquivos de config/..." > "$TIMESTAMP_DIR/artisan_config_show_app.txt"
        echo "" > "$TIMESTAMP_DIR/artisan_config_show_database.txt"
        if [ -d config ]; then
             cp config/app.php "$TIMESTAMP_DIR/config_app.php.copy.txt" 2>/dev/null || true
             cp config/database.php "$TIMESTAMP_DIR/config_database.php.copy.txt" 2>/dev/null || true
        fi
    fi
fi

# --- Coleta de Informações de Dependências ---
echo "[5/8] Coletando informações de Dependências..."
echo "  Listando pacotes Composer instalados..."
if command_exists composer; then
    composer show > "$TIMESTAMP_DIR/composer_show.txt" 2>&1 || echo "Falha ao executar composer show" > "$TIMESTAMP_DIR/composer_show.txt"
else
     echo "Composer não encontrado." > "$TIMESTAMP_DIR/composer_show.txt"
fi
echo "  Listando pacotes NPM de nível superior..."
if command_exists npm; then
    npm list --depth=0 > "$TIMESTAMP_DIR/npm_list_depth0.txt" 2>&1 || echo "Falha ao executar npm list (está em um projeto node?)." > "$TIMESTAMP_DIR/npm_list_depth0.txt"
else
    echo "NPM não encontrado." > "$TIMESTAMP_DIR/npm_list_depth0.txt"
fi

# --- Coleta de Estrutura do Projeto ---
echo "[6/8] Coletando informações da Estrutura do Projeto..."
echo "  Gerando árvore de diretórios (nível $TREE_DEPTH)..."
if command_exists tree; then
    tree -L "$TREE_DEPTH" -a -I "$TREE_IGNORE_PATTERN" > "$TIMESTAMP_DIR/project_tree_L${TREE_DEPTH}.txt" || echo "Erro ao gerar tree (verifique permissões ou profundidade)." > "$TIMESTAMP_DIR/project_tree_L${TREE_DEPTH}.txt"
else
    suggest_install "tree"
    echo "Comando 'tree' não encontrado. Listando diretórios de nível 1..." > "$TIMESTAMP_DIR/project_tree_L${TREE_DEPTH}.txt"
    ls -Ap1 > "$TIMESTAMP_DIR/project_toplevel_dirs.txt" 2>/dev/null || echo "Falha ao executar ls." >> "$TIMESTAMP_DIR/project_tree_L${TREE_DEPTH}.txt"
fi
echo "  Contando linhas de código (cloc)..."
if command_exists cloc; then
    cloc . --fullpath --not-match-d="${CLOC_EXCLUDE_REGEX}" > "$TIMESTAMP_DIR/project_cloc.txt" 2>&1 || echo "Falha ao executar cloc." > "$TIMESTAMP_DIR/project_cloc.txt"
else
    suggest_install "cloc" "cloc"
    echo "Comando 'cloc' não encontrado. Pulando contagem de linhas." > "$TIMESTAMP_DIR/project_cloc.txt"
fi

# --- Coleta de Informações do GitHub Issues ---
# *** MODIFICADO: Não usa mais subdiretório ***
echo "[7/8] Coletando informações das Issues do GitHub (exceto 'Closed as not planned')..."
if ! command_exists gh; then
    # Já sugerido antes
    echo "  ERRO: Comando 'gh' (GitHub CLI) não encontrado. Pulando a coleta de dados das issues." > "$TIMESTAMP_DIR/github_issues_error.log"
elif ! command_exists jq; then
    suggest_install "jq"
    echo "  ERRO: Comando 'jq' não encontrado. É necessário para processar a lista de issues. Pulando a coleta." > "$TIMESTAMP_DIR/github_issues_error.log"
else
    echo "  Issues serão salvas em: $TIMESTAMP_DIR"
    echo "  Listando e filtrando issues (limite: $GH_ISSUE_LIST_LIMIT)..."
    gh issue list --state all --limit "$GH_ISSUE_LIST_LIMIT" --json number,stateReason -q 'map(select(.stateReason != "NOT_PLANNED")) | .[].number' | while read -r issue_number; do
        if [[ -n "$issue_number" ]]; then
            echo "    Coletando detalhes da Issue #$issue_number..."
            # *** MODIFICADO: Salva direto no TIMESTAMP_DIR ***
            issue_output_file="$TIMESTAMP_DIR/github_issue_${issue_number}_details.json"
            issue_error_file="$TIMESTAMP_DIR/github_issue_${issue_number}_error.log"

            gh issue view "$issue_number" --json "$GH_ISSUE_JSON_FIELDS" > "$issue_output_file" 2>"$issue_error_file" || \
                echo "    AVISO: Falha ao coletar detalhes da Issue #$issue_number. Verifique $issue_error_file."

            if [ -f "$issue_error_file" ] && [ ! -s "$issue_error_file" ]; then
                rm "$issue_error_file"
            fi
        fi
    done

    # *** MODIFICADO: Verifica arquivos diretamente no TIMESTAMP_DIR ***
    if [ "$(find "$TIMESTAMP_DIR" -maxdepth 1 -name 'github_issue_*_details.json' -print -quit 2>/dev/null)" = "" ]; then
        echo "  Nenhuma issue encontrada (após filtrar 'Closed as not planned') ou nenhuma pôde ser baixada."
        echo '{ "message": "Nenhuma issue encontrada (após filtrar) ou baixada." }' > "$TIMESTAMP_DIR/no_issues_found.json"
    else
       echo "  Coleta de issues filtradas concluída."
    fi
fi

# --- Execução do PHPStan ---
echo "[8/8] Executando análise estática com PHPStan..."
if [ -f "$PHPSTAN_BIN" ]; then
    $PHPSTAN_BIN analyse --no-progress > "$TIMESTAMP_DIR/phpstan_analysis.txt" 2>&1
    PHPSTAN_EXIT_CODE=$?
    if [ $PHPSTAN_EXIT_CODE -ne 0 ]; then
        echo "  AVISO: PHPStan finalizado com código de saída $PHPSTAN_EXIT_CODE (erros encontrados ou falha). Veja $TIMESTAMP_DIR/phpstan_analysis.txt."
    else
        echo "  Análise PHPStan concluída sem erros reportados (código de saída 0)."
    fi
else
    echo "  Binário do PHPStan não encontrado em '$PHPSTAN_BIN'. Pulando análise."
    echo "PHPStan não executado: Binário não encontrado em $PHPSTAN_BIN" > "$TIMESTAMP_DIR/phpstan_analysis.txt"
fi

# --- Finalização ---
echo ""
echo "-----------------------------------------------------"
echo "Coleta de contexto para LLM concluída!"
echo "Arquivos salvos em: $TIMESTAMP_DIR"
echo "Use os arquivos neste diretório como contexto."
echo "-----------------------------------------------------"

# Limpa o stage do Git se o adicionamos no início (descomente a linha 'git add .' também)
# echo "Limpando o stage do Git (git reset)..."
# git reset > /dev/null 2>&1

exit 0