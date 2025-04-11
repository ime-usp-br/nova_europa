# Guia de Estratégia de Desenvolvimento - Laravel 12 USP Starter Kit

**Versão:** 0.1.0
**Data:** 11 de Abril de 2025

## 1. Introdução

### 1.1. Propósito deste Guia

Bem-vindo ao Guia de Estratégia de Desenvolvimento para o **Laravel 12 USP Starter Kit**. Este documento serve como o manual operacional padrão para todos os desenvolvedores que utilizam ou contribuem para este Starter Kit dentro do ambiente da Universidade de São Paulo (USP).

O objetivo principal é detalhar um processo de desenvolvimento organizado, consistente, eficiente e rastreável, cobrindo o ciclo de vida completo de uma tarefa, desde a concepção da ideia até a sua implementação e integração final no código-fonte.

### 1.2. Público-Alvo

Este guia destina-se a desenvolvedores da USP com níveis variados de experiência em desenvolvimento web e no framework Laravel, incluindo:

*   Desenvolvedores júnior e estagiários.
*   Desenvolvedores experientes que buscam padronização e agilidade.
*   Equipes responsáveis pelo desenvolvimento e manutenção de sistemas departamentais ou centrais da USP.

Assume-se um conhecimento básico de Git, linha de comando e dos fundamentos do Laravel.

### 1.3. Importância da Organização e do Processo

Mesmo para desenvolvedores trabalhando sozinhos ou em pequenas equipes, a adoção de um processo estruturado não é burocracia desnecessária, mas sim uma ferramenta essencial para:

*   **Manter a clareza e o foco:** Saber o que precisa ser feito e o que está em andamento.
*   **Garantir a qualidade:** Facilitar revisões, testes e a detecção precoce de problemas.
*   **Melhorar a manutenibilidade:** Criar um histórico de código compreensível e rastreável.
*   **Aumentar a produtividade:** Reduzir a sobrecarga cognitiva e otimizar o fluxo de trabalho.
*   **Facilitar a colaboração futura:** Estabelecer bases sólidas caso o projeto cresça ou novos membros se juntem.

### 1.4. Como Utilizar Este Guia

Este guia deve ser consultado como a **fonte principal de diretrizes** sobre como gerenciar tarefas, versionar código e colaborar (mesmo que a colaboração seja apenas consigo mesmo no futuro) dentro do contexto do Laravel 12 USP Starter Kit. Ele descreve a metodologia, as ferramentas e as práticas recomendadas que visam garantir um desenvolvimento de alta qualidade e consistente.

## 2. Visão Geral da Metodologia Adotada

Este Starter Kit adota uma metodologia de desenvolvimento inspirada nos princípios **Ágeis** e **Kanban**. Em vez de um plano de ação rígido, focamos em um sistema dinâmico e visual para gerenciar o fluxo de trabalho.

### 2.1. Princípios Ágeis/Kanban Aplicados

*   **Visualização do Fluxo:** Utilizamos o **GitHub Projects** como nosso quadro Kanban para tornar o trabalho visível.
*   **Gerenciamento Contínuo do Fluxo:** Monitoramos o progresso das tarefas através do quadro, identificando e resolvendo gargalos.
*   **Limitação do Trabalho em Progresso (WIP):** Mesmo para desenvolvedores solo, recomendamos limitar o número de tarefas "Em Progresso" (idealmente 1 ou 2) para manter o foco e acelerar a conclusão.
*   **Sistema Puxado:** O trabalho é "puxado" do backlog para as etapas seguintes conforme a capacidade permite, garantindo um fluxo mais suave.
*   **Melhoria Contínua:** O processo deve ser revisado e adaptado conforme necessário para otimizar a eficiência e a qualidade.

### 2.2. Filosofia Central: Issues Atômicas e Commits Atômicos

A base da nossa organização e rastreabilidade reside em duas práticas fundamentais:

*   **Issues Atômicas:** Cada unidade de trabalho (seja uma correção de bug, uma nova feature pequena, uma tarefa de refatoração ou documentação) **DEVE** ser representada por uma **Issue do GitHub**. A Issue deve ser focada, bem definida e ter critérios claros de aceitação (Definição de Pronto). Ela é a origem de todo trabalho rastreável.
*   **Commits Atômicos:** Cada `git commit` **DEVE** representar a **menor unidade lógica de ação concluída** que contribui para a resolução de uma Issue. Commits devem ser frequentes, focados em uma única coisa, e sempre vinculados à Issue correspondente.

### 2.3. A Importância da Rastreabilidade (Commit <> Issue <> PR)

Manter um vínculo claro entre o código escrito (Commits), a tarefa que ele resolve (Issue) e o processo de revisão/integração (Pull Request) é crucial. Isso cria um histórico completo e auditável, permitindo entender *por que* uma mudança foi feita, *qual* problema ela resolveu e *como* ela foi integrada. Esta rastreabilidade é essencial para manutenção, debugging e colaboração futura.

## 3. Ferramentas Essenciais e Configuração Inicial

Para seguir esta estratégia de desenvolvimento, as seguintes ferramentas são essenciais e devem ser configuradas corretamente:

*   **Git e GitHub:** O sistema de controle de versão distribuído e a plataforma de hospedagem central. Certifique-se de ter o Git instalado e uma conta no GitHub. O código do Starter Kit estará em um repositório GitHub.
*   **GitHub CLI (`gh`):** A ferramenta de linha de comando oficial do GitHub. Permite interagir com Issues, PRs, Repositórios e mais, diretamente do terminal. É fundamental para a automação da criação de Issues.
    *   **Instalação e Autenticação:** Siga as [instruções oficiais](https://cli.github.com/manual/installation) para instalar o `gh` no seu sistema. Após a instalação, autentique-se executando `gh auth login` e seguindo as instruções.
*   **GitHub Projects (v2):** A ferramenta integrada ao GitHub para gerenciamento visual de projetos (quadro Kanban). Será usada para visualizar e gerenciar o fluxo de Issues. (Ver Seção 4.3 para configuração).
*   **Ferramentas de Qualidade (Pré-configuradas no Starter Kit):**
    *   **Laravel Pint:** Ferramenta para formatação automática do estilo de código PHP (PSR-12). Execute `composer lint` ou configure seu editor para usar o Pint.
    *   **Larastan:** Extensão do PHPStan para análise estática focada em Laravel. Ajuda a encontrar erros sem executar o código. Execute via `composer analyse`.
*   **EditorConfig:** O arquivo `.editorconfig` incluído no Starter Kit ajuda a manter estilos de codificação consistentes (espaçamento, fim de linha) entre diferentes editores e IDEs. Garanta que seu editor tenha um plugin EditorConfig instalado e ativado.

## 4. Ciclo de Vida Detalhado do Desenvolvimento

Este ciclo descreve o fluxo recomendado para transformar uma ideia ou necessidade em código integrado ao projeto.

### 4.1. Fase 1: Planejamento e Captura de Demandas

*   **Backlog Centralizado:** Todas as ideias, novas funcionalidades, bugs relatados, tarefas técnicas e melhorias devem ser capturadas como itens no **Backlog** do quadro **GitHub Projects** associado ao repositório.
*   **Tipos de Itens:**
    *   **Draft Issues (Rascunhos):** Use para capturar ideias rapidamente diretamente no quadro Kanban, sem poluir a lista de Issues do repositório. Detalhe-as mais tarde.
    *   **Issues Reais (Repositório):** Quando uma tarefa está mais definida ou pronta para ser considerada para trabalho, converta o rascunho ou crie uma Issue diretamente no repositório GitHub.
*   **Decomposição:** Funcionalidades maiores (Épicos) devem ser quebradas em Issues menores e mais gerenciáveis (atômicas) antes de serem movidas para o fluxo de trabalho ativo. Uma Issue deve, idealmente, representar um trabalho que pode ser concluído em horas ou, no máximo, poucos dias.

### 4.2. Fase 2: Criação e Detalhamento de Issues Atômicas

**Toda unidade de trabalho rastreável DEVE começar como uma Issue no GitHub.** A qualidade da Issue é fundamental para a clareza e eficiência do desenvolvimento.

*   **Como Criar Issues Eficazes:**
    *   **Título:** Claro, conciso e acionável. Deve resumir o problema ou a tarefa. (Ex: "[BUG] Botão de login não funciona no Firefox", "[FEAT] Implementar exportação de usuários para CSV").
    *   **Descrição:** Detalhada e contextualizada. Explique o *quê* e o *porquê*. Para bugs, inclua passos para reproduzir, comportamento esperado vs. atual, ambiente. Para features, descreva o objetivo, a motivação e a solução proposta.
    *   **Templates:** **SEMPRE** utilize os templates fornecidos (`.github/ISSUE_TEMPLATE/`) ao criar novas Issues. Eles guiam o preenchimento das informações essenciais:
        *   `bug_report.md`: Para relatar bugs.
        *   `feature_request.md`: Para novas funcionalidades ou melhorias.
        *   `chore_refactor.md`: Para tarefas internas, refatorações, atualizações de dependências, etc.
    *   **Critérios de Aceite:** **OBRIGATÓRIO.** Defina claramente como você saberá que a Issue está "Pronta" (Done). Use checklists Markdown (`- [ ] Critério 1`). Uma Issue só pode ser considerada concluída quando todos os seus critérios de aceite forem atendidos. Isto deve ser *verificável* (princípio IEEE 830).
*   **Organização da Issue:**
    *   **Labels:** Use labels consistentemente para categorizar (ex: `bug`, `feature`, `chore`), priorizar (`priority:high`, `priority:medium`), indicar status (`status:blocked`) ou módulo (`module:auth`).
    *   **Assignees:** Atribua a Issue a si mesmo (`@me`) quando começar a trabalhar nela.
    *   **Milestones (Opcional):** Agrupe Issues relacionadas a uma entrega ou objetivo maior.

### 4.3. Fase 3: Gerenciamento do Fluxo com o Quadro Kanban (GitHub Projects)

O quadro Kanban no GitHub Projects é a ferramenta central para visualizar e gerenciar o fluxo de trabalho.

*   **Configuração Sugerida (Solo/Pequeno Time):**
    *   **Colunas (Controladas pelo Campo "Status"):**
        1.  `Backlog`: Todas as Issues/Rascunhos recém-criados ou a serem priorizados.
        2.  `A Fazer (To Do)`: Issues priorizadas, detalhadas e prontas para iniciar o desenvolvimento.
        3.  `Em Progresso (In Progress)`: A(s) Issue(s) que está(ão) sendo trabalhada(s) ativamente.
        4.  `Concluído (Done)`: Issues cujo trabalho foi concluído, testado e integrado (PR mergeado).
    *   **Limites de WIP:** Defina um limite baixo para a coluna "Em Progresso" (ex: `WIP: 1` ou `WIP: 2`). Isso força o foco em *terminar* tarefas antes de *começar* novas.
*   **Sistema Puxado:**
    *   Não comece a trabalhar em uma nova Issue apenas porque terminou a anterior.
    *   Verifique se a coluna "Em Progresso" está *abaixo* do limite de WIP.
    *   Se sim, **puxe** a Issue de maior prioridade (geralmente a do topo) da coluna "A Fazer" para "Em Progresso".
    *   Atualize o "Status" da Issue no GitHub Projects e atribua-a a si mesmo.
*   **Priorização Visual:** Mantenha as Issues dentro da coluna "A Fazer" ordenadas verticalmente por prioridade (mais importante no topo).
*   **Automações (Workflows):** Configure os workflows básicos no GitHub Projects para reduzir trabalho manual:
    *   `Item added to project` -> Mover para `Backlog` (Set Status: Backlog).
    *   `Issue closed` / `Pull request merged` -> Mover para `Concluído` (Set Status: Done).
    *   *(Opcional)* `Pull request opened` -> Mover Issue vinculada para `Em Progresso` (ou `Revisão`).

### 4.4. Fase 4: Desenvolvimento Orientado por Issues

O desenvolvimento de código deve ser sempre guiado por uma Issue específica.

*   **Branching Strategy:** Antes de começar a codificar, crie um branch Git específico para a Issue a partir do branch principal (ex: `main` ou `develop`). Use uma convenção de nomenclatura clara:
    *   `feature/<ID>-descricao-curta` (ex: `feature/45-autenticacao-google`)
    *   `fix/<ID>-descricao-curta` (ex: `fix/124-botao-logout-firefox`)
    *   `chore/<ID>-descricao-curta` (ex: `chore/55-atualizar-composer-deps`)
    *   `refactor/<ID>-descricao-curta` (ex: `refactor/60-simplificar-userservice`)
*   **Implementação Focada:** Trabalhe *exclusivamente* no código necessário para satisfazer os Critérios de Aceite da Issue atual. Evite introduzir mudanças não relacionadas (scope creep) neste branch. Se descobrir algo novo, crie outra Issue no Backlog.
*   **Commits Atômicos e Frequentes:** Faça commits pequenos, lógicos e que representem um passo concluído. Não cometa código quebrado ou incompleto (`git stash` é seu amigo).
*   **Mensagens de Commit (Obrigatório):** Siga um padrão consistente (como Conventional Commits) e **SEMPRE referencie a Issue ID** na mensagem.
    *   **Formato:** `<tipo>(<escopo_opcional>): <descrição imperativa concisa> (#<ID_da_Issue>)`
    *   **Tipos Comuns:** `feat:` (nova feature), `fix:` (correção de bug), `refactor:` (mudança que não altera comportamento externo), `chore:` (manutenção, build), `test:` (adição/ajuste de testes), `docs:` (mudanças na documentação).
    *   **Exemplo:** `feat: Adiciona rota e controller para logout (#124)`

### 4.5. Fase 5: Integração e Revisão (Pull Requests)

Mesmo trabalhando sozinho, usar Pull Requests (PRs) é uma excelente prática.

*   **Criação do PR:** Quando o desenvolvimento no branch da Issue estiver completo e todos os critérios de aceite atendidos:
    *   Faça push do branch para o GitHub: `git push origin feature/124-botao-logout`.
    *   Abra um Pull Request no GitHub, comparando seu branch (`feature/124-botao-logout`) com o branch principal (`main` ou `develop`).
*   **Estrutura do PR:**
    *   **Título:** Claro e relacionado à Issue (GitHub pode sugerir baseado no branch/commits).
    *   **Descrição:** Resuma as mudanças. **OBRIGATÓRIO** usar `Closes #<ID>` ou `Fixes #<ID>` para vincular o PR à Issue e garantir seu fechamento automático no merge.
    *   **Revisão:** Revise seu próprio código no PR. Isso ajuda a pegar erros antes do merge.
*   **Integração Contínua (CI):** A abertura/atualização do PR deve disparar automaticamente os workflows do GitHub Actions configurados no Starter Kit (testes, Pint, Larastan). O PR só deve ser mergeado se a CI passar.

### 4.6. Fase 6: Merge e Conclusão

*   **Merge:** Após a auto-revisão e a passagem da CI, faça o merge do PR no branch principal. Use preferencialmente a opção "Squash and merge" ou "Rebase and merge" para manter um histórico do branch principal mais limpo, se apropriado para o seu fluxo. Garanta que a mensagem do commit de merge também referencie a Issue.
*   **Verificação:** Confirme que a Issue foi automaticamente fechada no GitHub e que a automação do GitHub Projects moveu o cartão para a coluna "Concluído".
*   **Limpeza:** Exclua o branch da feature (`git branch -d feature/124-botao-logout`, `git push origin --delete feature/124-botao-logout`).

### 4.7. Fase 7: Deploy (Opcional)

O merge no branch principal pode ser o gatilho para um processo de deploy (manual ou automatizado via GitHub Actions) para um ambiente de testes ou produção. Isso está fora do escopo estrito deste guia, mas é o próximo passo natural.

## 5. Automatizando a Criação de Issues com `gh` CLI

Para acelerar a criação de Issues a partir de um plano de ação ou lista de tarefas, especialmente após uma sessão de planejamento, podemos usar a `gh` CLI e scripts Bash.

### 5.1. Propósito da Automação

*   **Velocidade:** Criar múltiplas Issues rapidamente.
*   **Consistência:** Usar templates e aplicar labels/assignees padrão.
*   **Integração:** Gerar Issues diretamente do terminal.

### 5.2. Formatos de Arquivo de Input (`plano_*.txt`)

Podemos usar dois formatos para nosso arquivo de plano:

*   **`plano_simples.txt`:** Cada linha contém apenas o título da Issue.
    ```
    Corrigir bug de login na API
    Implementar paginação na lista de usuários
    ```
*   **`plano_estruturado.txt`:** Usa `|` para separar Título, tipo (para template/label) e labels adicionais (separadas por vírgula).
    ```
    Corrigir bug de login na API|bug|prioridade:alta
    Implementar paginação na lista de usuários|feature
    Refatorar módulo de autenticação|refactor|tech-debt
    Configurar CI/CD|chore|ci-cd
    ```

### 5.3. Templates de Corpo de Issue

Utilize os templates Markdown localizados em `.github/ISSUE_TEMPLATES/script_templates/`:

*   `bug_template.md`
*   `feature_template.md`
*   `chore_refactor_template.md`
*   `default_template.md`

### 5.4. Scripts de Automação

Os scripts a seguir leem os arquivos de plano e criam as Issues no GitHub.

**Script Básico (`criar_issues_simples.sh`):**

```bash
#!/bin/bash

# Uso: ./criar_issues_simples.sh <arquivo_de_plano.txt>

PLAN_FILE="${1:-plano_simples.txt}" # Usa argumento ou padrão
DEFAULT_LABELS=("todo" "backlog")
ASSIGNEE="@me"
PROJECT_NAME="" # Preencha se usar GitHub Project
# REPO_TARGET="seu-usuario/seu-repo" # Descomente e ajuste se não estiver no diretório

# ... (restante do script 'Exemplo 1' de github_cli_referencia.md) ...
# (Adapte a leitura do arquivo para usar $PLAN_FILE)
# ... (loop while lendo $PLAN_FILE) ...
# ... (comando gh issue create usando -t "$issue_title" e -b "Tarefa...") ...

# ---- Conteúdo completo do script básico ----
# Arquivo contendo os títulos das issues, um por linha
PLAN_FILE="${1:-plano_simples.txt}"
# Labels padrão a serem adicionadas a todas as issues
DEFAULT_LABELS=("todo" "backlog")
# Atribuir a si mesmo? ("@me" ou deixe vazio "")
ASSIGNEE="@me"
# Adicionar a um projeto? (Nome ou número do projeto, ex: "Meu Kanban Pessoal")
# Encontre via `gh project list` ou na URL do projeto. Deixe vazio "" se não usar.
PROJECT_NAME=""
# Repositório (se necessário, senão usa o atual) ex: "meu-usuario/meu-repo"
# REPO_TARGET="meu-usuario/meu-repo"

# Verifica se o arquivo de plano existe
if [ ! -f "$PLAN_FILE" ]; then
  echo "Erro: Arquivo de plano '$PLAN_FILE' não encontrado."
  echo "Uso: $0 [<arquivo_de_plano.txt>]"
  exit 1
fi

echo "Iniciando criação de Issues a partir de '$PLAN_FILE'..."

# Constrói os flags de label
label_flags=""
for label in "${DEFAULT_LABELS[@]}"; do
  label_flags+=" -l \"$label\""
done

# Constrói o flag de assignee
assignee_flag=""
if [ -n "$ASSIGNEE" ]; then
  assignee_flag=" -a \"$ASSIGNEE\""
fi

# Constrói o flag de projeto
project_flag=""
if [ -n "$PROJECT_NAME" ]; then
  # Tentativa de encontrar o ID do projeto pelo nome (requer gh >= 2.5.0 para --format json)
  PROJECT_ID=$(gh project list --owner '@me' --format json --jq '.projects[] | select(.title == "'"$PROJECT_NAME"'") | .id' 2>/dev/null)
  if [ -z "$PROJECT_ID" ]; then
      # Se falhar ou não for JSON, tenta usar o nome diretamente (pode funcionar em versões futuras ou se for número)
      echo "Aviso: Não foi possível encontrar o ID do projeto '$PROJECT_NAME'. Tentando usar o nome/número diretamente."
      PROJECT_ID="$PROJECT_NAME"
  fi
    project_flag=" -p \"$PROJECT_ID\"" # Usa o ID encontrado ou o nome/número original
fi

# Constrói o flag de repositório
repo_flag=""
if [ -n "$REPO_TARGET" ]; then
  repo_flag=" -R \"$REPO_TARGET\""
fi

# Lê o arquivo linha por linha
while IFS= read -r issue_title || [[ -n "$issue_title" ]]; do
  # Ignora linhas vazias ou comentadas com #
  if [[ -z "$issue_title" || "$issue_title" =~ ^# ]]; then
    continue
  fi

  echo "Criando Issue: '$issue_title'"

  # Monta e executa o comando gh
  # shellcheck disable=SC2086 # Expansão intencional dos flags
  gh issue create -t "$issue_title" \
                  -b "Tarefa definida no plano de ação." \
                  $label_flags \
                  $assignee_flag \
                  $project_flag \
                  $repo_flag

  # Verifica se o comando foi bem sucedido
  if [ $? -ne 0 ]; then
    echo "Erro ao criar Issue: '$issue_title'"
    # Decide se quer parar ou continuar
    # exit 1 # Para em caso de erro
    echo "Continuando com a próxima..."
  else
    echo "Issue '$issue_title' criada com sucesso."
  fi

  # Pequena pausa para não sobrecarregar a API (opcional)
  sleep 1

done < "$PLAN_FILE"

echo "Criação de Issues concluída."
# ---- Fim do conteúdo completo ----
```

**Script Avançado (`criar_issues_estruturadas.sh`):**

```bash
#!/bin/bash

# Uso: ./criar_issues_estruturadas.sh <arquivo_de_plano_estruturado.txt>

PLAN_FILE="${1:-plano_estruturado.txt}" # Usa argumento ou padrão
TEMPLATE_DIR=".github/ISSUE_TEMPLATES/script_templates"
DEFAULT_TEMPLATE="default_template.md"
DEFAULT_LABEL_IF_EMPTY="todo"
ASSIGNEE="@me"
PROJECT_NAME="" # Preencha se usar GitHub Project
# REPO_TARGET="seu-usuario/seu-repo" # Descomente e ajuste se não estiver no diretório

# ... (restante do script 'Exemplo 2' de github_cli_referencia.md) ...
# (Adapte a leitura do arquivo para usar $PLAN_FILE)
# ... (loop while lendo $PLAN_FILE) ...
# ... (lógica para extrair título, tipo, labels) ...
# ... (lógica para escolher template_file) ...
# ... (construção de label_flags) ...
# ... (comando gh issue create usando -F "$template_file" e flags) ...

# ---- Conteúdo completo do script avançado ----
# Arquivo contendo as issues estruturadas: Título|tipo|label1,label2,...
PLAN_FILE="${1:-plano_estruturado.txt}"
# Diretório contendo os templates .md para o corpo das issues
TEMPLATE_DIR=".github/ISSUE_TEMPLATES/script_templates"
# Template padrão a ser usado se um específico não for encontrado
DEFAULT_TEMPLATE="default_template.md"
# Label padrão a ser adicionada se nenhuma específica for fornecida
DEFAULT_LABEL_IF_EMPTY="todo"
# Atribuir a si mesmo?
ASSIGNEE="@me"
# Adicionar a um projeto?
PROJECT_NAME=""
# Repositório alvo?
# REPO_TARGET="meu-usuario/meu-repo"

# Verifica se o arquivo de plano existe
if [ ! -f "$PLAN_FILE" ]; then
  echo "Erro: Arquivo de plano '$PLAN_FILE' não encontrado."
  echo "Uso: $0 [<arquivo_de_plano_estruturado.txt>]"
  exit 1
fi

# Verifica se o diretório de templates existe
if [ ! -d "$TEMPLATE_DIR" ]; then
  echo "Erro: Diretório de templates '$TEMPLATE_DIR' não encontrado."
  exit 1
fi

echo "Iniciando criação de Issues estruturadas a partir de '$PLAN_FILE'..."

# Constrói o flag de assignee
assignee_flag=""
if [ -n "$ASSIGNEE" ]; then
  assignee_flag=" -a \"$ASSIGNEE\""
fi

# Constrói o flag de projeto
project_flag=""
if [ -n "$PROJECT_NAME" ]; then
  # Tentativa de encontrar o ID do projeto pelo nome (requer gh >= 2.5.0 para --format json)
  PROJECT_ID=$(gh project list --owner '@me' --format json --jq '.projects[] | select(.title == "'"$PROJECT_NAME"'") | .id' 2>/dev/null)
  if [ -z "$PROJECT_ID" ]; then
      # Se falhar ou não for JSON, tenta usar o nome diretamente (pode funcionar em versões futuras ou se for número)
      echo "Aviso: Não foi possível encontrar o ID do projeto '$PROJECT_NAME'. Tentando usar o nome/número diretamente."
      PROJECT_ID="$PROJECT_NAME"
  fi
    project_flag=" -p \"$PROJECT_ID\"" # Usa o ID encontrado ou o nome/número original
fi

# Constrói o flag de repositório
repo_flag=""
if [ -n "$REPO_TARGET" ]; then
  repo_flag=" -R \"$REPO_TARGET\""
fi

# Lê o arquivo linha por linha, usando '|' como delimitador
while IFS='|' read -r issue_title issue_type_labels extra || [[ -n "$issue_title" ]]; do
  # Ignora linhas vazias ou comentadas com #
  if [[ -z "$issue_title" || "$issue_title" =~ ^# ]]; then
    continue
  fi

  # Limpa espaços extras (se houver)
  issue_title=$(echo "$issue_title" | sed 's/^[ \t]*//;s/[ \t]*$//')
  issue_type_labels=$(echo "$issue_type_labels" | sed 's/^[ \t]*//;s/[ \t]*$//')

  # Separa o tipo (primeira parte antes da vírgula) das labels específicas
  issue_type="${issue_type_labels%%,*}" # Pega a parte antes da primeira vírgula
  specific_labels_str="${issue_type_labels#*,}" # Pega a parte depois da primeira vírgula

  # Se não houver vírgula, o tipo é toda a string e não há labels específicas
  if [[ "$issue_type" == "$specific_labels_str" ]]; then
      specific_labels_str=""
  fi

  # Se o tipo estiver vazio, use 'default'
  if [ -z "$issue_type" ]; then
    issue_type="default"
  fi

  # Padroniza tipo para minúsculo para nome do arquivo
  issue_type_lower=$(echo "$issue_type" | tr '[:upper:]' '[:lower:]')

  echo "Processando: Título='$issue_title', Tipo='$issue_type', Labels='$specific_labels_str'"

  # Determina o arquivo de template a ser usado
  template_file="$TEMPLATE_DIR/${issue_type_lower}_template.md"
  if [ ! -f "$template_file" ]; then
    # Tenta também com 'chore_refactor' se for 'chore' ou 'refactor'
    if [[ "$issue_type_lower" == "chore" || "$issue_type_lower" == "refactor" ]]; then
      template_file="$TEMPLATE_DIR/chore_refactor_template.md"
    fi
  fi
  if [ ! -f "$template_file" ]; then
     echo "Aviso: Template para tipo '$issue_type_lower' ou 'chore_refactor' não encontrado. Usando default."
     template_file="$TEMPLATE_DIR/$DEFAULT_TEMPLATE"
     if [ ! -f "$template_file" ]; then
         echo "Erro: Template default '$DEFAULT_TEMPLATE' não encontrado em '$TEMPLATE_DIR'. Pulando issue."
         continue
     fi
  fi

  # Constrói os flags de label
  label_flags=""
  # Adiciona o tipo como label (se não for 'default')
  if [[ "$issue_type" != "default" ]]; then
    label_flags+=" -l \"$issue_type\""
  fi

  # Adiciona as labels específicas da linha
  if [ -n "$specific_labels_str" ]; then
    IFS=',' read -ra specific_labels <<< "$specific_labels_str"
    for label in "${specific_labels[@]}"; do
      clean_label=$(echo "$label" | sed 's/^[ \t]*//;s/[ \t]*$//') # Limpa espaços
      if [ -n "$clean_label" ]; then
        label_flags+=" -l \"$clean_label\""
      fi
    done
  elif [ -n "$DEFAULT_LABEL_IF_EMPTY" ]; then
     # Adiciona label padrão se nenhuma específica foi dada
        label_flags+=" -l \"$DEFAULT_LABEL_IF_EMPTY\""
  fi


  echo "  Usando template: $template_file"
  echo "  Labels a adicionar: $(echo $label_flags | sed 's/-l //g')" # Mostra as labels

  # Monta e executa o comando gh
  # shellcheck disable=SC2086 # Expansão intencional dos flags
  gh issue create -t "$issue_title" \
                  -F "$template_file" \
                  $label_flags \
                  $assignee_flag \
                  $project_flag \
                  $repo_flag

  if [ $? -ne 0 ]; then
    echo "Erro ao criar Issue: '$issue_title'"
    # exit 1
    echo "Continuando com a próxima..."
  else
    echo "Issue '$issue_title' criada com sucesso."
  fi

  sleep 1 # Pausa

done < "$PLAN_FILE"

echo "Criação de Issues estruturadas concluída."
# ---- Fim do conteúdo completo ----
```

**Como Usar:**

1.  Salve os scripts (`criar_issues_simples.sh`, `criar_issues_estruturadas.sh`).
2.  Torne-os executáveis (`chmod +x *.sh`).
3.  Crie a estrutura de pastas `.github/ISSUE_TEMPLATES/script_templates/` e coloque os arquivos de template (`bug_template.md`, etc.) dentro dela.
4.  Crie seu arquivo de plano (ex: `ciclo_atual.txt`) no formato desejado.
5.  (Opcional) Edite as variáveis no topo dos scripts (DEFAULT_LABELS, PROJECT_NAME, etc.) conforme sua necessidade.
6.  Execute o script apropriado, passando o nome do arquivo de plano como argumento:
    ```bash
    ./criar_issues_estruturadas.sh ciclo_atual.txt
    ```
7.  Verifique as Issues criadas no seu repositório GitHub e no seu quadro Kanban (se configurado).

### 5.5. Fluxo de Trabalho com Automação

1.  **Planejamento:** Defina suas tarefas no arquivo `plano_*.txt`.
2.  **Execução do Script:** Rode o script `criar_issues_estruturadas.sh seu_plano.txt`.
3.  **Gerenciamento:** Suas Issues aparecerão no GitHub e, se configurado, no Backlog do seu quadro Kanban.
4.  **Desenvolvimento:** Prossiga com o fluxo normal descrito na Fase 4 (puxar issue, criar branch, fazer commits atômicos referenciando a issue, PR, merge).

## 6. Documentação do Projeto

*   **README.md:** Deve conter a visão geral do Starter Kit, instruções de instalação rápida, propósito e um link para a Wiki. Pode incluir uma *explicação* da estrutura do quadro Kanban.
*   **Wiki do GitHub:** É o local ideal para a documentação mais detalhada:
    *   Este **Guia de Estratégia de Desenvolvimento**.
    *   Guias de configuração avançada.
    *   Tutoriais sobre como estender o Starter Kit.
    *   Explicação da arquitetura de código e dos serviços incluídos (ReplicadoService, etc.).
    *   Detalhes sobre o sistema de permissões.
    *   Como executar e interpretar os testes.
    *   Estratégias de deploy recomendadas (se houver).
    *   Convenções de código (reforçando Pint/Larastan).
*   **Documentação no Código:** Comentários claros no código, especialmente em partes mais complexas ou específicas da USP.
*   **Manutenção:** A documentação deve ser tratada como código. Crie Issues (tipo `docs`) para rastrear necessidades de atualização ou criação de documentação e siga o mesmo fluxo de desenvolvimento para elas.

## 7. Manutenção e Evolução Contínua

O processo descrito aplica-se não apenas ao desenvolvimento inicial, mas também à manutenção e evolução contínua do projeto:

*   **Bugs:** Bugs encontrados em produção ou desenvolvimento devem ser registrados como Issues usando o template `bug_report.md` e seguir o fluxo normal (A Fazer -> Em Progresso -> Revisão -> Concluído). Use a label `bug`.
*   **Refatorações e Dívida Técnica:** Tarefas de melhoria de código, atualização de dependências, ou pagamento de dívida técnica devem ser criadas como Issues (template `chore_refactor.md`), priorizadas no backlog e trabalhadas como qualquer outra tarefa. Use labels `refactor` ou `tech-debt`.
*   **Novas Funcionalidades:** Ideias para novas funcionalidades entram no Backlog (como Draft ou Issue `feature`) e seguem o ciclo completo de detalhamento, priorização e implementação.

A chave é tratar *todo* o trabalho rastreável através de Issues, mantendo o quadro Kanban atualizado e seguindo a disciplina dos commits atômicos vinculados. Isso garante que o projeto permaneça organizado e manutenível ao longo do tempo.
