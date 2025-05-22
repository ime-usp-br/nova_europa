# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/v2.0.0.html).

## [Não lançado]

### Adicionado

*   **[TEST][AUTH] Adiciona testes de Feature (PHPUnit) e Browser (Dusk) para a UI de login local (#20), incluindo configuração, ambiente de teste dedicado (`.env.dusk.local`), integração CI e documentação de execução local para Dusk. (#31)**
*   **[DevTools] Ferramenta de Interação com LLM (`scripts/llm_interact.py`):** Adiciona script Python para automatizar tarefas de desenvolvimento (geração de código para ACs, mensagens de commit, criação de PRs, atualização de documentação, análise de ACs) usando a API Gemini e o contexto do projeto. Inclui flags para geração de contexto (`-g`), pesquisa web (`-w`), confirmação automática (`-y`), modo apenas meta-prompt (`-om`), espera (`-ws`), seleção de arquivo de doc (`-d`), criação de PRs (`create-pr` com `-i`, `-b`, `--draft`), tratamento de rate limit e mais. (Refs #28)
*   **[DevTools] Meta-prompts para LLM:** Adicionados templates (`project_templates/meta-prompts/`) para guiar a IA na geração de código, mensagens de commit, análises de AC, atualizações de documentação e criação de PRs.
*   **[DevTools] Planos de Desenvolvimento:** Adicionados arquivos de plano (`planos/`) para documentar o desenvolvimento futuro e servir de exemplo para o script `criar_issues_script.sh`.
*   **Estrutura Base do Projeto:**
    *   Configuração inicial do projeto Laravel 12.
    *   Dependências padrão do Laravel via `composer.json` e `package.json`.
    *   Configuração do Vite com plugin Laravel e Tailwind CSS (`vite.config.js`, `resources/css/app.css`, `resources/js/app.js`).
    *   Estrutura de diretórios padrão do Laravel (`app`, `bootstrap`, `config`, `database`, `public`, `resources`, `routes`, `storage`, `tests`).
    *   Comando `artisan` funcional.
    *   Arquivo `README.md` inicial com visão geral, instalação e uso básico.
    *   Licença MIT (`LICENSE`).
    *   Arquivos de configuração base (`.env.example`, `.gitattributes`, `.gitignore`, `phpunit.xml`).
*   **Integrações USP:**
    *   Adicionada dependência `uspdev/senhaunica-socialite` via Composer.
    *   Adicionada dependência `uspdev/replicado` via Composer.
    *   Adicionado Trait `HasSenhaunica` ao Model `User`.
    *   Adicionada migration para incluir campo `codpes` na tabela `users`.
*   **Autenticação e Permissões:**
    *   Adicionado scaffolding de autenticação local via **Laravel Breeze (Stack Livewire/Volt)** (commit `00c6c06c`). Inclui telas para login, registro, reset de senha, verificação de email, confirmação de senha e gerenciamento de perfil.
    *   Adicionada dependência `spatie/laravel-permission` via Composer.
    *   Adicionado Trait `HasRoles` ao Model `User`.
    *   Adicionada configuration `config/permission.php`.
    *   Adicionada migration para criar tabelas do `spatie/laravel-permission`.
    *   Model `User` básico com Factory (`UserFactory.php`).
    *   Rota de login local movida para `/login/local` (`login.local`) para acomodar login Senha Única na rota `/login` (commit `feed175`).
    *   Adicionado botão "Login com Senha Única USP" na tela de login local (`login.blade.php`).
    *   Adicionado link "Register" na tela de login local (commit `7f1e7d6`).
    *   Ajustado link "Already registered?" na tela de registro para apontar para `login.local` (commit `7f1e7d6`).
*   **Qualidade de Código e Ferramentas:**
    *   Adicionado arquivo `.editorconfig` para padronização de estilo.
    *   Adicionada dependência `laravel/pint` para formatação PSR-12.
    *   Adicionada dependência `larastan/larastan` para análise estática (nível 10).
    *   Adicionado arquivo de configuração `phpstan.neon`.
    *   Adicionada dependência `nunomaduro/collision` para melhor tratamento de erros CLI.
    *   Adicionada dependência `laravel/tinker` para REPL.
    *   Adicionada dependência `laravel/sail` (opcional para ambiente Docker).
    *   Adicionada dependência `laravel/pail` para tail de logs via CLI.
*   **Banco de Dados e Infraestrutura:**
    *   Migrations padrão do Laravel para `users`, `password_reset_tokens`, `sessions`, `cache`, `jobs`, `job_batches`, `failed_jobs`.
    *   Seeder padrão `DatabaseSeeder.php` (cria usuário `test@example.com`).
    *   Configuração de Cache padrão para `database` (`config/cache.php`, `.env.example`).
    *   Configuração de Filas (Queue) padrão para `database` (`config/queue.php`, `.env.example`).
    *   Configuração de Sessão padrão para `database` (`config/session.php`, `.env.example`).
*   **Documentação e Processo de Desenvolvimento:**
    *   Adicionado `docs/termo_abertura_projeto.md` (v0.1.0) definindo escopo e objetivos.
    *   Adicionado `docs/guia_de_desenvolvimento.md` (v0.1.0) detalhando metodologia e fluxo de trabalho.
    *   Adicionado `docs/padroes_codigo_boas_praticas.md` (v0.1.0) definindo convenções.
    *   Adicionado `docs/versionamento_documentacao.md` (v0.1.0) definindo a estratégia de versionamento para arquivos `.md`.
    *   Adicionado ADR `docs/adr/001-criar-issues-script-challenges.md` (v0.1.0) sobre o script de automação.
    *   Adicionado script de automação `criar_issues_script.sh` para criação/edição de Issues no GitHub.
    *   Adicionados templates de corpo de Issue para o script (`project_templates/issue_bodies/`).
    *   Adicionado arquivo de exemplo para o script de issues (`planos/plano_exemplo.txt`).
    *   Criado `CHANGELOG.md` inicial.
*   **Localização:**
    *   Adicionado pacote `laravel-lang/common` e suas dependências para traduções padronizadas (commit `d097fb3`).
    *   Arquivos de tradução `pt_BR` e `en` para strings do framework e pacotes comuns.
    *   Atualização da view `login.blade.php` para usar `__()`.
*   **Layout:**
    *   Adicionado componente Blade `x-usp.header` para cabeçalho padrão USP (commit `87f46f7`).
    *   Integrado cabeçalho USP nos layouts `app.blade.php` e `guest.blade.php`, e na `welcome.blade.php` (commits `87f46f7`, `2695909`).
    *   Adicionado logo do IME à tela de login (`login.blade.php`) (commit `2695909`).

### Alterado
-   **[DevTools]** Refatorado o script `scripts/llm_interact.py` para uma arquitetura modular. O script principal agora atua como um dispatcher, e as tarefas individuais foram movidas para scripts dedicados em `scripts/tasks/` (ex: `llm_task_resolve_ac.py`). Funcionalidades centrais foram movidas para `scripts/llm_core/`. (Resolve #57)
*   **[DevTools] Script de geração de contexto migrado de Bash (`gerar_contexto_llm.sh`) para Python (`scripts/generate_context.py`) para melhor manutenibilidade, robustez e extensibilidade, mantendo a funcionalidade de coleta original. (#35)**
*   Nível de análise do PHPStan elevado para 10.
*   README.md atualizado para refletir o estado do projeto (v0.1.0).
*   Guias de desenvolvimento e ADRs movidos para o diretório `docs/`.
*   Cabeçalhos de versão/data adicionados aos documentos `.md` versionados.
*   Estrutura de saída do script `gerar_contexto_llm.sh` modificada para colocar todos os arquivos no diretório raiz do timestamp.
*   View `welcome.blade.php` reformulada para usar o cabeçalho USP e fornecer links básicos.
*   View `login.blade.php` modificada para localização e adição de botões Senha Única/Registro.
*   Layout `guest.blade.php` modificado para usar o cabeçalho USP e remover logo de aplicação padrão.

### Removido

*   Conteúdo padrão do `README.md` do Laravel.
*   Logo `<x-application-logo />` do layout `guest.blade.php`.

[Não lançado]: https://github.com/ime-usp-br/laravel_12_starter_kit/compare/HEAD