# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/v2.0.0.html).

## [Não lançado]

### Adicionado

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
    *   Adicionada dependência `spatie/laravel-permission` via Composer.
    *   Adicionado Trait `HasRoles` ao Model `User`.
    *   Adicionada configuration `config/permission.php`.
    *   Adicionada migration para criar tabelas do `spatie/laravel-permission`.
    *   Model `User` básico com Factory (`UserFactory.php`).
*   **Qualidade de Código e Ferramentas:**
    *   Adicionado arquivo `.editorconfig` para padronização de estilo.
    *   Adicionada dependência `laravel/pint` para formatação PSR-12.
    *   Adicionada dependência `larastan/larastan` para análise estática.
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

[Não lançado]: https://github.com/ime-usp-br/laravel_12_starter_kit/compare/HEAD