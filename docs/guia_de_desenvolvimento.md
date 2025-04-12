# Guia de Estratégia de Desenvolvimento - Laravel 12 USP Starter Kit

**Versão:** 0.1.0<br>
**Data:** 2025-04-12

## 1. Introdução

### 1.1. Propósito deste Guia

Bem-vindo ao Guia de Estratégia de Desenvolvimento para o **Laravel 12 USP Starter Kit**. Este documento, assim como os demais arquivos de documentação `.md` neste repositório, segue um controle de versão próprio (detalhado na Seção 6.1) e serve como o manual operacional padrão para todos os desenvolvedores que utilizam ou contribuem para este Starter Kit dentro do ambiente da Universidade de São Paulo (USP).

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
    *   **Laravel Pint:** Ferramenta para formatação automática do estilo de código PHP (PSR-12). Execute `vendor/bin/pint` ou configure seu editor para usar o Pint.
    *   **Larastan:** Extensão do PHPStan para análise estática focada em Laravel. Ajuda a encontrar erros sem executar o código. Execute via `vendor/bin/phpstan analyse`.
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
    *   **Templates:** **SEMPRE** utilize os templates fornecidos (veja seção 5.3 para o local correto) ao criar novas Issues. Eles guiam o preenchimento das informações essenciais:
        *   `bug_body.md`: Para relatar bugs.
        *   `feature_body.md`: Para novas funcionalidades ou melhorias.
        *   `chore_body.md`: Para tarefas internas, refatorações, atualizações de dependências, etc.
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

Podemos usar um formato estruturado para nosso arquivo de plano (ex: `planos/plano_exemplo.txt`), onde cada bloco define uma issue e seus metadados usando pares `CHAVE: VALOR`. Veja o arquivo `planos/plano_exemplo.txt` e o script `criar_issues_script.sh` para detalhes do formato exato.

### 5.3. Templates de Corpo de Issue

Utilize os templates Markdown localizados em `project_templates/issue_bodies/`:

*   `bug_body.md`
*   `chore_body.md`
*   `feature_body.md`
*   `default_body.md` (Usado como fallback)

### 5.4. Script de Automação

O script `criar_issues_script.sh` incluído no repositório lê um arquivo de plano estruturado (como `planos/plano_exemplo.txt`) e cria ou **edita** Issues no GitHub.

*   **Funcionalidades do Script:**
    *   Lê blocos de definição de Issue de um arquivo texto.
    *   Usa templates Markdown do diretório `project_templates/issue_bodies/` com base no `TYPE` definido no bloco.
    *   Aplica labels, assignee e milestone (se fornecido via argumento de linha de comando).
    *   Associa a Issue a um GitHub Project (se especificado no bloco e o projeto existir).
    *   **Verifica se uma Issue aberta com o mesmo título já existe.** Se sim, edita a issue existente (atualizando corpo, assignee, milestone e adicionando labels). Se não, cria uma nova Issue.
    *   Verifica e cria labels e milestones que não existem (se possível).
*   **Como Usar:**
    1.  Certifique-se de ter `gh`, `jq` e outras ferramentas Unix padrão instaladas e o `gh` autenticado.
    2.  (Opcional) Crie ou modifique os templates em `project_templates/issue_bodies/`.
    3.  Crie seu arquivo de plano (ex: `planos/ciclo_atual.txt`) seguindo o formato do `planos/plano_exemplo.txt`.
    4.  Execute o script, passando o nome do arquivo de plano e, opcionalmente, um milestone:
        ```bash
        # Criar/Editar issues do plano, sem milestone específico
        ./criar_issues_script.sh planos/ciclo_atual.txt

        # Criar/Editar issues, associando-as ao milestone "Sprint 1" (cria se não existir)
        ./criar_issues_script.sh --milestone-title "Sprint 1" --milestone-desc "Objetivos da Sprint 1" planos/ciclo_atual.txt
        ```
    5.  Verifique as Issues criadas/editadas no seu repositório GitHub e no seu quadro Kanban (se configurado).

### 5.5. Fluxo de Trabalho com Automação

1.  **Planejamento:** Defina suas tarefas no arquivo de plano estruturado (ex: `planos/ciclo_atual.txt`).
2.  **Execução do Script:** Rode o script `criar_issues_script.sh seu_plano.txt [--milestone-title ...]`.
3.  **Gerenciamento:** Suas Issues aparecerão atualizadas ou criadas no GitHub e, se configurado, no Backlog do seu quadro Kanban.
4.  **Desenvolvimento:** Prossiga com o fluxo normal descrito na Fase 4 (puxar issue, criar branch, fazer commits atômicos referenciando a issue, PR, merge).

## 6. Documentação do Projeto

*   **README.md:** Deve conter a visão geral do Starter Kit, instruções de instalação rápida, propósito e um link para a Wiki. **DEVE** incluir a linha `**Versão:** X.Y.Z` e `**Data:** YYYY-MM-DD` (ver Seção 6.1). Pode incluir uma *explicação* da estrutura do quadro Kanban.
*   **Wiki do GitHub:** É o local ideal para a documentação mais detalhada e que pode ter um ciclo de atualização diferente (histórico próprio da Wiki). Conteúdo ideal para a Wiki:
    *   Guias de configuração avançada.
    *   Tutoriais sobre como estender o Starter Kit.
    *   Explicação da arquitetura de código e dos serviços incluídos (ReplicadoService, etc.).
    *   Detalhes sobre o sistema de permissões.
    *   Como executar e interpretar os testes.
    *   Estratégias de deploy recomendadas (se houver).
    *   Convenções de código (reforçando Pint/Larastan).
*   **Documentos `.md` no Repositório:** Arquivos como este guia (`docs/guia_de_desenvolvimento.md`), ADRs (`docs/adr/`), o Termo de Abertura (`docs/termo_abertura_projeto.md`), e outros documentos `.md` mantidos junto ao código **DEVEM** seguir o sistema de versionamento descrito na Seção 6.1.
*   **Documentação no Código:** Comentários claros no código, especialmente em partes mais complexas ou específicas da USP.
*   **Manutenção da Documentação Versionada:** A documentação versionada (`.md` no repo) deve ser tratada como código. Crie Issues (tipo `docs`) para rastrear necessidades de atualização ou criação e siga o mesmo fluxo de desenvolvimento (commit, PR). As atualizações da versão no cabeçalho ocorrem conforme descrito na Seção 6.1.

### 6.1. Versionamento da Documentação no Repositório

Para garantir clareza sobre qual versão do Starter Kit um documento `.md` descreve, adotamos a seguinte estratégia:

*   **Alinhamento com o Código:** A versão da documentação `.md` no repositório **DEVE** espelhar a versão [SemVer](https://semver.org/lang/pt-BR/) do release do Starter Kit (tag Git).
*   **Identificação:** Todo arquivo `.md` versionado (exceto `LICENSE`) **DEVE** iniciar com:
    ```markdown
    **Versão:** X.Y.Z
    **Data:** YYYY-MM-DD
    ```
    (Onde X.Y.Z é a tag do release e YYYY-MM-DD a data de criação da tag).
*   **Atualização:** A `Versão` e `Data` no cabeçalho dos documentos **DEVEM** ser atualizadas no commit que prepara a criação de uma nova tag de release (ex: `v0.1.0`, `v0.2.0`).
*   **Versão Inicial:** A versão inicial de toda a documentação `.md` neste repositório é `0.1.0`, datada de `2025-04-12`.
*   **Escopo:** Aplica-se a: `README.md`, `docs/guia_de_desenvolvimento.md`, `docs/termo_abertura_projeto.md`, `docs/adr/*.md`,  `padroes_codigo_boas_praticas.md`.
*   **Changelog:** É **RECOMENDÁVEL** usar `CHANGELOG.md` ou GitHub Releases para detalhar mudanças entre versões, incluindo as da documentação.

*Para detalhes completos da estratégia, consulte o arquivo `docs/versionamento_documentacao.md`.*

## 7. Manutenção e Evolução Contínua

O processo descrito aplica-se não apenas ao desenvolvimento inicial, mas também à manutenção e evolução contínua do projeto:

*   **Bugs:** Bugs encontrados em produção ou desenvolvimento devem ser registrados como Issues usando o template apropriado (`bug_body.md`) e seguir o fluxo normal (A Fazer -> Em Progresso -> Revisão -> Concluído). Use a label `bug`.
*   **Refatorações e Dívida Técnica:** Tarefas de melhoria de código, atualização de dependências, ou pagamento de dívida técnica devem ser criadas como Issues (template `chore_body.md`), priorizadas no backlog e trabalhadas como qualquer outra tarefa. Use labels `refactor` ou `tech-debt`.
*   **Novas Funcionalidades:** Ideias para novas funcionalidades entram no Backlog (como Draft ou Issue `feature`) e seguem o ciclo completo de detalhamento, priorização e implementação.
*   **Atualizações de Documentação:** Mudanças necessárias na documentação versionada (`.md` no repo) **DEVEM** ser tratadas via Issues (tipo `docs`) e Pull Requests, seguindo o fluxo padrão. A atualização da versão no cabeçalho ocorre conforme a Seção 6.1.

A chave é tratar *todo* o trabalho rastreável através de Issues, mantendo o quadro Kanban atualizado e seguindo a disciplina dos commits atômicos vinculados. Isso garante que o projeto permaneça organizado e manutenível ao longo do tempo.