# Laravel 12 USP Starter Kit

**Versão:** 0.1.0<br>
**Data:** 2025-04-17

[![Status da Build](https://github.com/ime-usp-br/laravel_12_starter_kit/actions/workflows/laravel.yml/badge.svg)](https://github.com/ime-usp-br/laravel_12_starter_kit/actions/workflows/laravel.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 1. Introdução

O **Laravel 12 USP Starter Kit** é um ponto de partida acelerado para o desenvolvimento de aplicações web com Laravel 12, especificamente adaptado para as necessidades e o ecossistema da Universidade de São Paulo (USP).

**Propósito e Justificativa:** Este kit foi criado para padronizar e agilizar o desenvolvimento de aplicações Laravel na USP, eliminando a necessidade recorrente de configurar manualmente integrações comuns como autenticação (Senha Única USP e local), gerenciamento de permissões e acesso aos dados corporativos (Replicado). O objetivo é fornecer uma base de código robusta, pré-configurada e alinhada com boas práticas, reduzindo o tempo inicial de setup e promovendo a consistência entre os sistemas desenvolvidos na universidade.

## 2. Público-Alvo

Este Starter Kit destina-se principalmente a:

*   Desenvolvedores da USP (Júnior, Estagiários, Plenos, Sêniores).
*   Equipes responsáveis pelo desenvolvimento e manutenção de sistemas departamentais ou centrais da USP.

Assume-se um conhecimento básico de PHP, Laravel, Git e linha de comando.

## 3. Principais Funcionalidades

Este Starter Kit vem pré-configurado com:

*   **Base Laravel 12:** Estrutura inicial pronta para uso.
*   **Autenticação Dupla:**
    *   **Senha Única USP:** Integração completa e funcional via `uspdev/senhaunica-socialite` (a ser totalmente implementada no backend e UI).
    *   **Autenticação Local (Scaffolding via Breeze):** Sistema de Login/Registro/Reset de Senha/Verificação de Email baseado no **Laravel Breeze (Stack Livewire Class API)**, pronto para customização visual e integração com a lógica de validação USP.
    *   **Registro Unificado (Planejado):** Formulário de registro único que diferenciará usuários USP (com validação de Nº USP e e-mail via Replicado) e externos, utilizando a base do Breeze.
*   **Integração com Replicado:**
    *   Biblioteca `uspdev/replicado` configurada.
    *   `ReplicadoService` (Planejado): Uma classe de serviço com métodos comuns para consulta de dados pessoais e vínculos, usada na validação do registro.
*   **Gerenciamento de Permissões:**
    *   Integração com `spatie/laravel-permission`.
    *   Roles padrão pré-definidos (Planejado: `Admin`, `User`, `usp_user`, `external_user`).
    *   Atribuição automática de roles no registro (Planejado).
    *   Interface básica TALL Stack para gerenciamento de Usuários, Roles e Permissões (Planejado).
    *   Aplicação de permissões hierárquicas e de vínculo vindas da Senha Única (guard `senhaunica`).
*   **Stack Frontend TALL (via Breeze):**
    *   **Livewire 3 (Class API):** Para componentes PHP interativos.
    *   **Alpine.js 3:** Para interatividade leve no frontend.
    *   **Tailwind CSS 4:** Para estilização moderna e utilitária.
    *   **Vite:** Para compilação de assets.
    *   **Suporte a Dark Mode:** Pré-configurado pelo Breeze.
    *   Componentes Blade básicos e reutilizáveis, adaptados visualmente às diretrizes da USP (Planejado).
*   **Ferramentas de Qualidade:**
    *   **Laravel Pint:** Para formatação automática de código (PSR-12).
    *   **Larastan (PHPStan):** Para análise estática de código focada em Laravel.
    *   **EditorConfig:** Para manter a consistência de estilo entre editores.
*   **Testes Automatizados:**
    *   Estrutura inicial com testes unitários e de feature (**PHPUnit** como framework padrão, configurado pelo Breeze).
    *   Testes básicos de autenticação adicionados pelo Breeze.
    *   **Laravel Dusk:** Para testes de browser End-to-End.
    *   Facilitadores (`Fakes`) para testar integrações com Senha Única e Replicado sem depender dos serviços reais (Planejado).
*   **Documentação:** README detalhado e [Wiki do Projeto](https://github.com/ime-usp-br/laravel_12_starter_kit/wiki) para guias aprofundados.
*   **Ferramentas de Desenvolvimento:**
    *   Script Python (`scripts/create_issue.py`) para automação de criação/edição de Issues no GitHub a partir de arquivos de plano (`planos/*.txt`) e templates (`templates/issue_bodies/*.md`).
    *   Script Python (`scripts/generate_context.py`) para coletar contexto abrangente do projeto e ambiente para uso por LLMs.
    *   **Scripts de Interação com LLM:**
        A ferramenta de interação com LLM foi modularizada. O script principal `scripts/llm_interact.py` agora funciona como um **dispatcher**. Você pode invocar tarefas específicas através dele ou executar os scripts de tarefa individuais diretamente.
        *   **Dispatcher:** `python scripts/llm_interact.py <nome_da_tarefa> [argumentos_da_tarefa...]`
            Ex: `python scripts/llm_interact.py resolve-ac --issue 123 --ac 1`
            Se `<nome_da_tarefa>` for omitido, o dispatcher listará as tarefas disponíveis interativamente.
        *   **Scripts de Tarefa Individuais:** Localizados em `scripts/tasks/`, podem ser executados diretamente.
            Ex: `python scripts/tasks/llm_task_resolve_ac.py --issue 123 --ac 1 [outros_argumentos_comuns...]`
        *   **Funcionalidades Comuns:** As funcionalidades centrais (configuração, parsing de argumentos comuns, carregamento de contexto, interação com API, I/O) estão em `scripts/llm_core/`. Incluem: pré-injeção de arquivos essenciais no contexto da LLM seletora; gerenciamento proativo de limites de tokens e RPM da API Gemini (cálculo dinâmico de `MAX_INPUT_TOKENS_PER_CALL`, redução de contexto por sumário/truncamento e rate limiter de chamadas); e melhorias na experiência do usuário ao selecionar contexto interativamente.
        *   **Argumentos Comuns:** Use `-h` ou `--help` em qualquer script de tarefa ou no dispatcher para ver as opções comuns e específicas da tarefa. Destacam-se: `--issue`, `--ac`, `--observation`, `--two-stage` (fluxo com meta-prompt), `--select-context` (para seleção interativa de contexto, agora com exibição de contagem de tokens e tratamento de arquivos ausentes/truncados), `--web-search` (com tool calling), `--generate-context` (para acionar o script de geração de contexto), etc.
    * Requer `google-genai`, `python-dotenv`, `tqdm` e uma `GEMINI_API_KEY` válida no arquivo `.env`.
*   **Configurações Adicionais:** Filas com driver `database`, exemplo de `supervisor.conf`, LogViewer básico (Planejado).

*Para uma lista completa de funcionalidades incluídas e excluídas, consulte o [Termo de Abertura do Projeto](./docs/termo_abertura_projeto.md).*

## 4. Stack Tecnológica

*   **Framework:** Laravel 12
*   **Linguagem:** PHP >= 8.2
*   **Frontend (Stack TALL via Laravel Breeze):**
    *   **Livewire 3 (Class API)**
    *   **Alpine.js 3**
    *   **Tailwind CSS 4** (com suporte a Dark Mode)
    *   **Vite**
*   **Banco de Dados:** Suporte padrão do Laravel (MySQL, MariaDB, PostgreSQL, SQLite)
*   **Integrações USP:**
    *   `uspdev/senhaunica-socialite`
    *   `uspdev/replicado`
*   **Autenticação Scaffolding:** `laravel/breeze`
*   **Permissões:** `spatie/laravel-permission`
*   **Testes:** **PHPUnit**, **Laravel Dusk**
*   **Qualidade:** Laravel Pint, Larastan
*   **Ferramentas Dev:** Python 3.x, `google-genai`, `python-dotenv`, `tqdm` (para scripts LLM)

## 5. Instalação

Este Starter Kit já vem com o Laravel Breeze (Stack TALL - Livewire Class API, Alpine.js, Tailwind CSS com Dark Mode) e Laravel Dusk pré-instalados e configurados. Siga os passos abaixo para iniciar seu projeto:

1.  **Pré-requisitos:**
    *   PHP >= 8.2 (com extensões comuns do Laravel: ctype, fileinfo, json, mbstring, openssl, PDO, tokenizer, xml, etc.)
    *   Composer
    *   Node.js (v18+) e NPM
    *   Git
    *   **Google Chrome** ou **Chromium** instalado (para testes Dusk)
    *   (Opcional, para ferramentas de dev) Python >= 3.10, Pip, `gh` CLI, `jq`

2.  **Clonar o Repositório:**
    ```bash
    git clone https://github.com/ime-usp-br/laravel_12_starter_kit.git seu-novo-projeto
    cd seu-novo-projeto
    ```

3.  **Instalar Dependências PHP:**
    ```bash
    composer install
    ```

4.  **Instalar Dependências Frontend:**
    ```bash
    npm install
    ```

5.  **Configurar Ambiente:**
    *   Copie o arquivo de exemplo `.env`:
        ```bash
        cp .env.example .env
        ```
    *   Gere a chave da aplicação:
        ```bash
        php artisan key:generate
        ```
    *   **Edite o arquivo `.env`:** Configure as variáveis de ambiente, especialmente:
        *   `APP_NAME`: Nome da sua aplicação.
        *   `APP_URL`: URL base da sua aplicação (ex: `http://localhost:8000`).
        *   `DB_CONNECTION`, `DB_HOST`, `DB_PORT`, `DB_DATABASE`, `DB_USERNAME`, `DB_PASSWORD`: Credenciais do seu banco de dados.
        *   `MAIL_*`: Configurações de e-mail (importante para verificação de e-mail).
        *   **Credenciais USP:** Adicione e configure as variáveis para `uspdev/senhaunica-socialite` e `uspdev/replicado` (veja a seção 7).
        *   **(Opcional) `GEMINI_API_KEY`:** Adicione sua chave da API Google Gemini para usar os scripts de LLM. Pode conter múltiplas chaves separadas por `|`.

6.  **Banco de Dados e Dados Iniciais:**
    *   Execute as migrações para criar todas as tabelas necessárias:
        ```bash
        php artisan migrate
        ```
    *   (Opcional, mas recomendado) Execute os seeders para popular o banco com dados iniciais (ex: usuário de teste local `test@example.com`):
        ```bash
        php artisan db:seed
        ```

7.  **Compilar Assets Frontend:**
    ```bash
    npm run build
    ```
    *(Ou use `npm run dev` durante o desenvolvimento para compilação automática).*

8.  **Configuração Inicial do Dusk (Importante):**
    *   **Verificar Instalação:** Confirme se o Dusk está instalado (já deveria estar no `composer.json`). Se necessário, rode `php artisan dusk:install`.
    *   **Instalar ChromeDriver:** Instale o driver correto para sua versão do Chrome/Chromium:
        ```bash
        php artisan dusk:chrome-driver --detect
        ```
        *(Se encontrar erros de conexão SSL/TLS (`cURL error 28`), resolva problemas de rede/firewall/certificados antes de continuar).*
    *   **Criar/Verificar `.env.dusk.local`:** Crie este arquivo na raiz do projeto (se não existir) e configure-o para o ambiente de teste do Dusk. Um exemplo (`.env.dusk.local`) já está incluído neste repositório. Preste atenção especial a:
        *   `APP_URL=http://127.0.0.1:8000` (ou a URL que `php artisan serve` usa)
        *   `DB_CONNECTION=sqlite` e `DB_DATABASE=database/testing/dusk.sqlite` (recomendado usar um banco de dados SQLite separado para testes Dusk)

9.  **(Opcional) Configurar Ferramentas de Desenvolvimento:**
    *   Instale Python 3.10+ e Pip, se necessário.
    *   Instale as dependências Python para os scripts LLM:
        ```bash
        pip install google-genai python-dotenv tqdm
        ```
    *   Instale a `gh` CLI e `jq` se for usar os scripts `scripts/create_issue.py` ou algum script de tarefa LLM (ex: `scripts/tasks/llm_task_create_pr.py`).
    *   Torne os scripts Python executáveis: `chmod +x scripts/*.py scripts/tasks/*.py`.

Seu ambiente de desenvolvimento com o Starter Kit deve estar pronto para uso.

## 6. Uso Básico

1.  **Iniciar Servidores (Desenvolvimento):**
    *   Para o servidor web PHP embutido:
        ```bash
        php artisan serve
        ```
    *   Para o servidor de desenvolvimento Vite (compilação de assets em tempo real):
        ```bash
        npm run dev
        ```

2.  **Acessar a Aplicação:**
    *   Abra seu navegador e acesse a `APP_URL` definida no `.env` (geralmente `http://localhost:8000`).
    *   Páginas de autenticação: `/login` (Senha Única), `/login/local`, `/register`.

3.  **Credenciais Padrão:**
    *   Se você rodou `php artisan db:seed` (ou `migrate --seed`) após a instalação, pode usar o usuário local criado:
        *   **Email:** `test@example.com`
        *   **Senha:** `password`

## 7. Configurações Específicas da USP

Para que as funcionalidades de integração com a USP funcionem corretamente, você **precisa** configurar as credenciais apropriadas no seu arquivo `.env`.

*   **Senha Única:** Adicione e preencha as variáveis `SENHAUNICA_CALLBACK`, `SENHAUNICA_KEY`, `SENHAUNICA_SECRET`. Consulte a [documentação do `uspdev/senhaunica-socialite`](https://github.com/uspdev/senhaunica-socialite) para detalhes sobre como obter essas credenciais.
*   **Replicado:** Adicione e preencha as variáveis `REPLICADO_HOST`, `REPLICADO_PORT`, `REPLICADO_DATABASE`, `REPLICADO_USERNAME`, `REPLICADO_PASSWORD`, `REPLICADO_CODUND`, `REPLICADO_CODBAS`. Consulte a [documentação do `uspdev/replicado`](https://github.com/uspdev/replicado) para detalhes.

*Instruções detalhadas sobre a configuração e uso dessas integrações podem ser encontradas na [Wiki do Projeto](https://github.com/ime-usp-br/laravel_12_starter_kit/wiki).*

## 8. Ferramentas e Qualidade de Código

Este Starter Kit inclui ferramentas para ajudar a manter a qualidade e a consistência do código:

*   **Laravel Pint:** Formatador de código automático (PSR-12).
    *   Para formatar: `vendor/bin/pint`
    *   Para verificar (CI): `vendor/bin/pint --test`
*   **Larastan (PHPStan):** Ferramenta de análise estática para encontrar erros sem executar o código.
    *   Para analisar: `vendor/bin/phpstan analyse`
*   **EditorConfig:** Arquivo `.editorconfig` na raiz para padronizar configurações básicas do editor (indentação, fim de linha, etc.). Garanta que seu editor tenha o plugin EditorConfig instalado e ativado.
*   **Script de Criação de Issues (`scripts/create_issue.py`):** Ferramenta Python para automação de criação/edição de Issues no GitHub a partir de arquivos de plano (`planos/*.txt`) e templates (`templates/issue_bodies/*.md`).
*   **Script de Geração de Contexto LLM (`scripts/generate_context.py`):** Ferramenta Python para coletar informações abrangentes do projeto (código, Git, GitHub, ambiente, etc.) e salvá-las em `context_llm/code/<timestamp>/` para uso por LLMs.
*   **Scripts de Interação com LLM (`scripts/llm_interact.py` e `scripts/tasks/llm_task_*.py`):**
    A ferramenta de interação com LLM foi modularizada. O script principal `scripts/llm_interact.py` agora funciona como um **dispatcher**. Você pode invocar tarefas específicas através dele ou executar os scripts de tarefa individuais diretamente.
    *   **Dispatcher:** `python scripts/llm_interact.py <nome_da_tarefa> [argumentos_da_tarefa...]`
        Ex: `python scripts/llm_interact.py resolve-ac --issue 123 --ac 1`
        Se `<nome_da_tarefa>` for omitido, o dispatcher listará as tarefas disponíveis interativamente.
    *   **Scripts de Tarefa Individuais:** Localizados em `scripts/tasks/`, podem ser executados diretamente.
        Ex: `python scripts/tasks/llm_task_resolve_ac.py --issue 123 --ac 1 [outros_argumentos_comuns...]`
    *   **Funcionalidades Comuns:** As funcionalidades centrais (configuração, parsing de argumentos comuns, carregamento de contexto, interação com API, I/O) estão em `scripts/llm_core/`. Incluem: pré-injeção de arquivos essenciais no contexto da LLM seletora; gerenciamento proativo de limites de tokens e RPM da API Gemini (cálculo dinâmico de `MAX_INPUT_TOKENS_PER_CALL`, redução de contexto por sumário/truncamento e rate limiter de chamadas); e melhorias na experiência do usuário ao selecionar contexto interativamente.
    *   **Argumentos Comuns:** Use `-h` ou `--help` em qualquer script de tarefa ou no dispatcher para ver as opções comuns e específicas da tarefa. Destacam-se: `--issue`, `--ac`, `--observation`, `--two-stage` (fluxo com meta-prompt), `--select-context` (para seleção interativa de contexto, agora com exibição de contagem de tokens e tratamento de arquivos ausentes/truncados), `--web-search` (com tool calling), `--generate-context` (para acionar o script de geração de contexto), etc.
    * Requer `google-genai`, `python-dotenv`, `tqdm` e uma `GEMINI_API_KEY` válida no arquivo `.env`.

## 9. Testes

*   **Executando Testes PHPUnit (Unitários e Feature):** Use o comando Artisan:
    ```bash
    php artisan test
    ```
*   **Executando Testes Dusk (Browser / End-to-End):** Rodar testes Dusk requer que **o servidor da aplicação e o ChromeDriver estejam rodando simultaneamente** antes de executar o comando de teste.
    1.  **Terminal 1 - Servidor da Aplicação:**
        ```bash
        php artisan serve
        ```
        *(Mantenha este terminal rodando)*
    2.  **Terminal 2 - ChromeDriver:**
        *   **Problema Comum:** Em alguns ambientes, o comando `php artisan dusk:chrome-driver` pode *não* manter o processo rodando como esperado, saindo imediatamente após confirmar a instalação.
        *   **Solução Manual:** Se o comando acima sair imediatamente, inicie o ChromeDriver manualmente, **especificando a porta 9515** (ou a porta definida em `DUSK_DRIVER_URL` no seu `.env.dusk.local`). Encontre o executável correto para seu sistema operacional dentro de `./vendor/laravel/dusk/bin/` e execute-o com a flag `--port`:
          ```bash
          # Exemplo para Linux:
          ./vendor/laravel/dusk/bin/chromedriver-linux --port=9515

          # Exemplo para macOS (Intel):
          # ./vendor/laravel/dusk/bin/chromedriver-mac-x64 --port=9515

          # Exemplo para macOS (Apple Silicon):
          # ./vendor/laravel/dusk/bin/chromedriver-mac-arm64 --port=9515

          # Exemplo para Windows (use Git Bash ou similar):
          # ./vendor/laravel/dusk/bin/chromedriver-win.exe --port=9515
          ```
        *(Mantenha este terminal rodando. Você deve ver uma mensagem como "ChromeDriver was started successfully on port 9515.")*
    3.  **Terminal 3 - Executar Testes Dusk:**
        ```bash
        php artisan dusk
        ```
*   **Fakes para Dependências USP:** O kit inclui classes `Fake` (ex: `FakeReplicadoService`, `FakeSenhaUnicaSocialiteProvider`) para facilitar a escrita de testes que interagem com as funcionalidades da Senha Única ou Replicado sem depender dos serviços externos reais. Consulte a [Wiki](https://github.com/ime-usp-br/laravel_12_starter_kit/wiki) para exemplos.

## 10. Documentação

A documentação principal e mais detalhada deste Starter Kit reside na **[Wiki do GitHub](https://github.com/ime-usp-br/laravel_12_starter_kit/wiki)**.

Lá você encontrará:

*   Este README.md.
*   O [Guia de Estratégia de Desenvolvimento](./docs/guia_de_desenvolvimento.md) completo (v0.1.0).
*   Os [Padrões de Código e Boas Práticas](./docs/padroes_codigo_boas_praticas.md) (v0.1.0).
*   A [Estratégia de Versionamento da Documentação](./docs/versionamento_documentacao.md) (v0.1.0).
*   O [Termo de Abertura do Projeto](./docs/termo_abertura_projeto.md) (v0.1.0).
*   Registros de Decisão de Arquitetura (ADRs) em `docs/adr/`.
*   Detalhes sobre a arquitetura do código (Services, Repositories).
*   Explicações sobre o sistema de permissões e autenticação.
*   Tutoriais sobre como estender o kit.
*   Guias de configuração avançada e deploy (se aplicável).
*   Como usar os fakes para testes.

## 11. Como Contribuir

Contribuições são bem-vindas! Para garantir um desenvolvimento organizado e rastreável, siga o fluxo descrito no **[Guia de Estratégia de Desenvolvimento](./docs/guia_de_desenvolvimento.md)**.

Em resumo:

1.  Identifique ou crie uma **Issue** atômica no GitHub descrevendo a tarefa (bug, feature, chore).
2.  Crie um **Branch** específico para a Issue a partir do branch principal (`main` ou `develop`).
3.  Faça **Commits Atômicos** e frequentes, sempre referenciando a Issue ID na mensagem (`#<ID>`).
4.  Abra um **Pull Request (PR)** claro, vinculando-o à Issue (`Closes #<ID>`).
5.  Aguarde a revisão (mesmo que seja auto-revisão) e a passagem da CI.
6.  Faça o **Merge** do PR.

*(Considere usar os scripts `scripts/create_issue.py` e `scripts/llm_interact.py` (ou os scripts de tarefa em `scripts/tasks/`) para agilizar a criação de issues e a geração de commits/PRs)*.

## 12. Licença

Este projeto é licenciado sob a **Licença MIT**. Veja o arquivo [LICENSE](./LICENSE) para mais detalhes.