# Guia de Estratégia de Desenvolvimento - Laravel 12 USP Starter Kit

**Versão:** 0.1.0<br>
**Data:** 2025-04-17

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
*   **GitHub CLI (`gh`):** A ferramenta de linha de comando oficial do GitHub. Permite interagir com Issues, PRs, Repositórios e mais, diretamente do terminal. É fundamental para a automação da criação de Issues e Pull Requests.
    *   **Instalação e Autenticação:** Siga as [instruções oficiais](https://cli.github.com/manual/installation) para instalar o `gh` no seu sistema. Após a instalação, autentique-se executando `gh auth login` e seguindo as instruções. **Recomendado:** Use um token PAT com os scopes necessários (`repo`, `project`, `workflow`).
*   **GitHub Projects (v2):** A ferramenta integrada ao GitHub para gerenciamento visual de projetos (quadro Kanban). Será usada para visualizar e gerenciar o fluxo de Issues. (Ver Seção 4.3 para configuração).
*   **Ferramentas de Qualidade (Pré-configuradas no Starter Kit):**
    *   **Laravel Pint:** Ferramenta para formatação automática do estilo de código PHP (PSR-12). Execute `vendor/bin/pint` ou configure seu editor para usar o Pint.
    *   **Larastan:** Extensão do PHPStan para análise estática focada em Laravel. Ajuda a encontrar erros sem executar o código. Execute via `vendor/bin/phpstan analyse`.
*   **Ferramentas de Teste (Pré-configuradas no Starter Kit):**
    *   **PHPUnit:** Framework padrão para testes unitários e de feature. Executado via `php artisan test`.
    *   **Laravel Dusk:** Ferramenta para testes de browser End-to-End. Executado via `php artisan dusk`.
    *   **Google Chrome ou Chromium:** Necessário para a execução dos testes Dusk.
*   **EditorConfig:** O arquivo `.editorconfig` incluído no Starter Kit ajuda a manter estilos de codificação consistentes (espaçamento, fim de linha) entre diferentes editores e IDEs. Garanta que seu editor tenha um plugin EditorConfig instalado e ativado.
*   **(Opcional) Ferramentas de Desenvolvimento Adicionais:**
    *   **Script de Geração de Contexto LLM (`scripts/generate_context.py`):** Ferramenta Python para coletar informações abrangentes do projeto e ambiente. **DEVE** ser usada para gerar o contexto necessário para a ferramenta de interação com LLM. Requer `jq`. Opcionalmente usa `tree`, `cloc`, `composer`, `npm`.
    *   **Scripts de Interação com LLM (`scripts/llm_interact.py` e `scripts/tasks/llm_task_*.py`):** Ferramentas Python para automatizar interações com a API do Google Gemini. `llm_interact.py` atua como dispatcher para os scripts de tarefa em `scripts/tasks/`. **PODEM** ser usadas para auxiliar em tarefas de desenvolvimento. Requerem `python3 >= 3.10`, Pip, e a instalação de `google-genai`, `python-dotenv`, `tqdm`. Requer `GEMINI_API_KEY` no `.env`.
    *   **Script de Criação de Issues (`scripts/create_issue.py`):** Ferramenta Python para automação de criação/edição de Issues no GitHub a partir de arquivos de plano. Requer `python3 >= 3.8`, `gh` CLI, `jq`.

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
    *   **Templates:** **SEMPRE** utilize os templates fornecidos (localizados em `templates/issue_bodies/`) ao criar novas Issues. Eles guiam o preenchimento das informações essenciais:
        *   `bug_body.md`: Para relatar bugs.
        *   `feature_body.md`: Para novas funcionalidades ou melhorias.
        *   `chore_body.md`: Para tarefas internas, refatorações, atualizações de dependências, etc.
        *   `test_body.md`: Para definir sub-tarefas de teste para uma issue pai.
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
    *   `test/<ID>-descricao-curta` (ex: `test/31-test-login-ui`)
*   **Implementação Focada:** Trabalhe *exclusivamente* no código necessário para satisfazer os Critérios de Aceite da Issue atual. Evite introduzir mudanças não relacionadas (scope creep) neste branch. Se descobrir algo novo, crie outra Issue no Backlog.
*   **Commits Atômicos e Frequentes:** Faça commits pequenos, lógicos e que representem um passo concluído. Não cometa código quebrado ou incompleto (`git stash` é seu amigo).
*   **Mensagens de Commit (Obrigatório):** Siga um padrão consistente (como Conventional Commits) e **SEMPRE referencie a Issue ID** na mensagem.
    *   **Formato:** `<tipo>(<escopo_opcional>): <descrição imperativa concisa> (#<ID_da_Issue>)`
    *   **Tipos Comuns:** `feat:` (nova feature), `fix:` (correção de bug), `refactor:` (mudança que não altera comportamento externo), `chore:` (manutenção, build), `test:` (adição/ajuste de testes), `docs:` (mudanças na documentação).
    *   **Exemplo:** `feat: Adiciona rota e controller para logout (#124)`
    *   **Opcional:** Utilize o script `scripts/llm_interact.py` com a tarefa `commit-mesage` (ex: `python scripts/llm_interact.py commit-mesage -i 124 -g`) ou o script de tarefa direto (`python scripts/tasks/llm_task_commit_mesage.py -i 124 -g`) para gerar uma mensagem de commit sugerida, baseada nas alterações em stage e no histórico do projeto. **REVISE** a mensagem gerada antes de usar.

### 4.5. Fase 5: Integração e Revisão (Pull Requests)

Mesmo trabalhando sozinho, usar Pull Requests (PRs) é uma excelente prática.

*   **Criação do PR:** Quando o desenvolvimento no branch da Issue estiver completo e todos os critérios de aceite atendidos:
    *   Faça push do branch para o GitHub: `git push origin feature/124-botao-logout`.
    *   Abra um Pull Request no GitHub, comparando seu branch (`feature/124-botao-logout`) com o branch principal (`main` ou `develop`).
*   **Estrutura do PR:**
    *   **Título:** Claro e relacionado à Issue (GitHub pode sugerir baseado no branch/commits).
    *   **Descrição:** Resuma as mudanças. **OBRIGATÓRIO** usar `Closes #<ID>` ou `Fixes #<ID>` para vincular o PR à Issue e garantir seu fechamento automático no merge.
    *   **Revisão:** Revise seu próprio código no PR. Isso ajuda a pegar erros antes do merge.
    *   **Opcional:** Utilize o script `scripts/llm_interact.py` com a tarefa `create-pr` (ex: `python scripts/llm_interact.py create-pr -i 124 -g`) ou o script de tarefa direto (`python scripts/tasks/llm_task_create_pr.py -i 124 -g`) para gerar automaticamente o título e corpo do PR, e opcionalmente criá-lo no GitHub. **REVISE** o conteúdo gerado.
*   **Integração Contínua (CI):** A abertura/atualização do PR deve disparar automaticamente os workflows do GitHub Actions configurados no Starter Kit (testes, Pint, Larastan). O PR só deve ser mergeado se a CI passar.

### 4.6. Fase 6: Merge e Conclusão

*   **Merge:** Após a auto-revisão e a passagem da CI, faça o merge do PR no branch principal. Use preferencialmente a opção "Squash and merge" ou "Rebase and merge" para manter um histórico do branch principal mais limpo, se apropriado para o seu fluxo. Garanta que a mensagem do commit de merge também referencie a Issue.
*   **Verificação:** Confirme que a Issue foi automaticamente fechada no GitHub e que a automação do GitHub Projects moveu o cartão para a coluna "Concluído".
*   **Limpeza:** Exclua o branch da feature (`git branch -d feature/124-botao-logout`, `git push origin --delete feature/124-botao-logout`).

### 4.7. Fase 7: Deploy (Opcional)

O merge no branch principal pode ser o gatilho para um processo de deploy (manual ou automatizado via GitHub Actions) para um ambiente de testes ou produção. Isso está fora do escopo estrito deste guia, mas é o próximo passo natural.

## 5. Automatizando a Criação de Issues com `gh` CLI e Python

Para acelerar a criação de Issues a partir de um plano de ação ou lista de tarefas, especialmente após uma sessão de planejamento, podemos usar a `gh` CLI e o script Python fornecido.

### 5.1. Propósito da Automação

*   **Velocidade:** Criar múltiplas Issues rapidamente.
*   **Consistência:** Usar templates e aplicar labels/assignees padrão.
*   **Integração:** Gerar Issues diretamente do terminal.

### 5.2. Formatos de Arquivo de Input (`planos/*.txt`)

Utilize um formato estruturado para o arquivo de plano (ex: `planos/plano_exemplo.txt`), onde cada bloco define uma issue e seus metadados usando pares `KEY: VALUE`. Consulte o arquivo de exemplo para detalhes do formato.

### 5.3. Templates de Corpo de Issue

Utilize os templates Markdown localizados em `templates/issue_bodies/`:

*   `bug_body.md`
*   `chore_body.md`
*   `feature_body.md`
*   `test_body.md`
*   `default_body.md` (Usado como fallback)

### 5.4. Script de Automação Python (`scripts/create_issue.py`)

O script `scripts/create_issue.py` incluído no repositório lê um arquivo de plano estruturado e cria ou **edita** Issues no GitHub.

*   **Funcionalidades Principais:** Consulte a docstring do script para detalhes completos sobre parsing, uso de templates, verificação de duplicatas, manipulação de labels/milestones/projetos.
*   **Como Usar:**
    1.  Certifique-se de ter `python3 >= 3.8`, `gh` CLI e `jq` instalados e o `gh` autenticado.
    2.  (Opcional) Crie/modifique os templates em `templates/issue_bodies/`.
    3.  Crie seu arquivo de plano (ex: `planos/ciclo_atual.txt`).
    4.  Execute o script, passando o nome do arquivo de plano e, opcionalmente, um milestone:
        ```bash
        # Criar/Editar issues do plano, sem milestone específico
        python scripts/create_issue.py planos/ciclo_atual.txt

        # Criar/Editar issues, associando-as ao milestone "Sprint 1" (cria se não existir com desc)
        python scripts/create_issue.py --milestone-title "Sprint 1" --milestone-desc "Objetivos da Sprint 1" planos/ciclo_atual.txt
        ```
    5.  Verifique as Issues criadas/editadas no GitHub e no seu quadro Kanban.

### 5.5. Fluxo de Trabalho com Automação

1.  **Planejamento:** Defina suas tarefas no arquivo de plano estruturado.
2.  **Execução do Script:** Rode `python scripts/create_issue.py seu_plano.txt [--milestone-title ...]`.
3.  **Gerenciamento:** Suas Issues aparecerão no GitHub e no quadro Kanban.
4.  **Desenvolvimento:** Prossiga com o fluxo normal (Fase 4).

## 6. Documentação do Projeto

*   **README.md:** Deve conter a visão geral, instalação rápida, propósito e link para a Wiki. **DEVE** incluir cabeçalho de versão/data.
*   **Wiki do GitHub:** Local para documentação detalhada (configuração avançada, tutoriais, arquitetura, testes, deploy).
*   **Documentos `.md` no Repositório:** Arquivos (`docs/`, ADRs) mantidos junto ao código **DEVEM** seguir o sistema de versionamento (Seção 6.1).
*   **Documentação no Código:** DocBlocks claros e comentários explicativos.
*   **Manutenção da Documentação Versionada:** Trate como código (Issues `docs`, PRs).

### 6.1. Versionamento da Documentação no Repositório

*   **Alinhamento com o Código:** Versão do `.md` reflete a tag SemVer do release do código.
*   **Identificação:** Todo arquivo `.md` versionado (exceto `LICENSE` e `CHANGELOG.md`) **DEVE** iniciar com:
    ```markdown
    **Versão:** X.Y.Z
    **Data:** YYYY-MM-DD
    ```
*   **Atualização:** A `Versão` e `Data` nos cabeçalhos dos documentos **DEVEM** ser atualizadas no commit que prepara a tag de release.
*   **Escopo:** Aplica-se a: `README.md`, `docs/*.md` (exceto `CHANGELOG.md`), `docs/adr/*.md`.

*Para detalhes completos, consulte `docs/versionamento_documentacao.md`.*

## 7. Manutenção e Evolução Contínua

O processo (Issues -> Branch -> Commits -> PR -> Merge) aplica-se a todo trabalho:

*   **Bugs:** Issue `bug`, template `bug_body.md`.
*   **Refatorações/Dívida Técnica:** Issue `chore`/`refactor`, template `chore_body.md`.
*   **Novas Funcionalidades:** Issue `feature`, template `feature_body.md`.
*   **Testes:** Issue `test`, template `test_body.md`.
*   **Atualizações de Documentação:** Issue `docs`, trate como código.

A chave é a rastreabilidade via Issues e commits vinculados.

## 8. Ferramentas de Desenvolvimento e Automação

*   **Laravel Pint:** (`vendor/bin/pint`) Formatador PSR-12. Use antes de commitar.
*   **Larastan:** (`vendor/bin/phpstan analyse`) Análise estática. Execute regularmente.
*   **Script de Criação de Issues (`scripts/create_issue.py`):** Automatiza a criação/edição de Issues no GitHub a partir de planos `.txt`.
*   **Script de Geração de Contexto (`scripts/generate_context.py`):** Coleta contexto (`context_llm/code/<timestamp>/`) para LLMs. Execute antes de usar as ferramentas de LLM.
*   **Scripts de Interação com LLM (`scripts/llm_interact.py` e `scripts/tasks/llm_task_*.py`):**
    A ferramenta de interação com LLM foi modularizada. O script principal `scripts/llm_interact.py` agora funciona como um **dispatcher**. Você pode invocar tarefas específicas através dele ou executar os scripts de tarefa individuais diretamente.
    *   **Dispatcher:** `python scripts/llm_interact.py <nome_da_tarefa> [argumentos_da_tarefa...]`
        Ex: `python scripts/llm_interact.py resolve-ac --issue 123 --ac 1`
        Se `<nome_da_tarefa>` for omitido, o dispatcher listará as tarefas disponíveis interativamente.
    *   **Scripts de Tarefa Individuais:** Localizados em `scripts/tasks/`, podem ser executados diretamente.
        Ex: `python scripts/tasks/llm_task_resolve_ac.py --issue 123 --ac 1 [outros_argumentos_comuns...]`
    *   **Funcionalidades Comuns:** As funcionalidades centrais (configuração, parsing de argumentos comuns, carregamento de contexto, interação com API, I/O) estão em `scripts/llm_core/`.
    *   **Argumentos Comuns:** Use `-h` ou `--help` em qualquer script de tarefa ou no dispatcher para ver as opções comuns e específicas da tarefa (ex: `--issue`, `--ac`, `--observation`, `--two-stage`, `--select-context`, `--web-search`, `--generate-context`, etc.).
    *   Requer `google-genai`, `python-dotenv`, `tqdm` e uma `GEMINI_API_KEY` válida no arquivo `.env`.

## 9. Testes Automatizados

*   **Testes Unitários e de Feature (PHPUnit):**
    *   Focam em classes isoladas (Unit) ou na interação de vários objetos dentro do framework (Feature).
    *   Execução: `php artisan test`
    *   Localização: `tests/Unit`, `tests/Feature`
*   **Testes de Browser (Laravel Dusk):**
    *   Simulam a interação real do usuário com a aplicação através de um navegador Chrome.
    *   Verificam a UI, fluxos de trabalho completos e JavaScript.
    *   Localização: `tests/Browser`
    *   **Execução Local (Requer Atenção):**
        1.  **Certifique-se:** Google Chrome/Chromium está instalado. ChromeDriver correspondente está instalado (via `php artisan dusk:chrome-driver --detect`). O arquivo `.env.dusk.local` está configurado corretamente (especialmente `APP_URL` e `DB_DATABASE`).
        2.  **Terminal 1:** Inicie o servidor de desenvolvimento Laravel:
            ```bash
            php artisan serve --port=8000 # Ou a porta definida em APP_URL no .env.dusk.local
            ```
        3.  **Terminal 2:** Inicie o ChromeDriver **MANUALMENTE** na porta 9515 (padrão do Dusk):
            ```bash
            # Exemplo Linux (adapte o nome do executável para seu SO)
            ./vendor/laravel/dusk/bin/chromedriver-linux --port=9515
            ```
            *(Você deve ver uma mensagem "ChromeDriver was started successfully...")*
        4.  **Terminal 3:** Execute os testes Dusk:
            ```bash
            php artisan dusk
            ```
*   **Fakes para Dependências USP:** Utilize as classes `Tests\Fakes\FakeReplicadoService` e `Tests\Fakes\FakeSenhaUnicaSocialiteProvider` para mockar respostas dos serviços USP em testes de Feature, evitando chamadas reais e garantindo testes determinísticos. Consulte a Wiki para exemplos.

## 10. Uso de Termos RFC 2119 na Documentação

Ao escrever documentação, use os termos da [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119) para indicar níveis de obrigatoriedade:

| Inglês (RFC 2119)           | Português (Adotado)         | Significado                                     |
| :-------------------------- | :-------------------------- | :---------------------------------------------- |
| MUST, REQUIRED, SHALL       | **DEVE, DEVEM, REQUER**     | Obrigação absoluta.                             |
| MUST NOT, SHALL NOT         | **NÃO DEVE, NÃO DEVEM**     | Proibição absoluta.                           |
| SHOULD, RECOMMENDED         | **PODERIA, PODERIAM, RECOMENDÁVEL** | Forte recomendação, exceções justificadas. |
| SHOULD NOT, NOT RECOMMENDED | **NÃO PODERIA, NÃO RECOMENDÁVEL** | Forte desaconselhamento, exceções justificadas. |
| MAY, OPTIONAL               | **PODE, PODEM, OPCIONAL**   | Verdadeiramente opcional, sem preferência.      |

Exemplo: _"O Model **DEVE** ter a propriedade `$fillable` definida."_ vs. _"Você **PODERIA** usar um Service para encapsular a lógica de email."_ vs. _"Todo texto visível ao usuário **DEVE** usar a função `__()`."_