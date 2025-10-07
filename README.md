# Laravel 12 USP Starter Kit

**Versão:** 0.1.0<br>
**Data:** 2025-05-29

[![Status da Build](https://github.com/ime-usp-br/laravel_12_starter_kit/actions/workflows/laravel.yml/badge.svg)](https://github.com/ime-usp-br/laravel_12_starter_kit/actions/workflows/laravel.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 1. Introdução

O **Laravel 12 USP Starter Kit** é um ponto de partida acelerado para o desenvolvimento de aplicações web com Laravel 12, especificamente adaptado para as necessidades e o ecossistema da Universidade de São Paulo (USP).

**Propósito e Justificativa:** Este kit foi criado para padronizar e agilizar o desenvolvimento de aplicações Laravel na USP, eliminando a necessidade Recorrente de configurar manualmente integrações comuns como autenticação (Senha Única USP e local), gerenciamento de permissões e acesso aos dados corporativos (Replicado). O objetivo é fornecer uma base de código robusta, pré-configurada e alinhada com boas práticas, reduzindo o tempo inicial de setup e promovendo a consistência entre os sistemas desenvolvidos na universidade.

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
    *   **Larastan (PHPStan):** Para análise estática de código.
    *   **EditorConfig:** Para manter a consistência de estilo entre editores.
*   **Testes Automatizados:**
    *   Estrutura inicial com testes unitários e de feature (**PHPUnit** como framework padrão, configurado pelo Breeze).
    *   Testes básicos de autenticação adicionados pelo Breeze.
    *   **Laravel Dusk:** Para testes de browser End-to-End.
    *   Facilitadores (`Fakes`) para testar integrações com Senha Única e Replicado sem depender dos serviços reais (Planejado).
*   **Documentação:** README detalhado e [Wiki do Projeto](https://github.com/ime-usp-br/laravel_12_starter_kit/wiki) para guias aprofundados.
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

## 5. Instalação

Este Starter Kit já vem com o Laravel Breeze (Stack TALL - Livewire Class API, Alpine.js, Tailwind CSS com Dark Mode) e Laravel Dusk pré-instalados e configurados. Você pode escolher entre instalação tradicional ou usando Docker com Laravel Sail.

### 5.1. Instalação com Laravel Sail (Recomendado)

Laravel Sail fornece um ambiente Docker completo com PHP, MySQL, Redis, Selenium e outras dependências pré-configuradas.

1.  **Pré-requisitos:**
    *   Docker e Docker Compose instalados
    *   Git

2.  **Clonar o Repositório:**
    ```bash
    git clone https://github.com/ime-usp-br/laravel_12_starter_kit.git seu-novo-projeto
    cd seu-novo-projeto
    ```

3.  **Configurar Ambiente:**
    *   Copie o arquivo de exemplo `.env`:
        ```bash
        cp .env.example .env
        ```
    *   **Edite o arquivo `.env`** e configure as variáveis essenciais para Sail:
        ```bash
        APP_NAME=Laravel
        APP_URL=http://localhost
        APP_PORT=8000

        # Configuração do banco de dados para Sail
        DB_CONNECTION=mysql
        DB_HOST=mysql
        DB_PORT=3306
        DB_DATABASE=laravel12_usp_starter_kit
        DB_USERNAME=sail
        DB_PASSWORD=password

        # Configuração de usuário Docker
        WWWUSER=1000
        WWWGROUP=1000
        ```
    *   **Credenciais USP:** Adicione e configure as variáveis para `uspdev/senhaunica-socialite` e `uspdev/replicado` (veja a seção 7).

4.  **Iniciar Containers Docker:**
    ```bash
    ./vendor/bin/sail up -d
    ```
    *(Na primeira execução, as imagens Docker serão construídas, o que pode levar alguns minutos)*

5.  **Gerar Chave da Aplicação:**
    ```bash
    ./vendor/bin/sail artisan key:generate
    ```

6.  **Instalar Dependências Frontend:**
    ```bash
    ./vendor/bin/sail npm install
    ```

7.  **Executar Migrações e Seeders:**
    ```bash
    ./vendor/bin/sail artisan migrate --seed
    ```

8.  **Compilar Assets Frontend:**
    ```bash
    ./vendor/bin/sail npm run dev
    ```
    *(Mantenha este comando rodando em um terminal separado durante o desenvolvimento)*

9.  **Configurar Usuário Admin:**

    Após a migração e seeding, você pode atribuir o perfil Admin a um usuário:
    ```bash
    ./vendor/bin/sail artisan tinker
    ```
    No tinker, execute:
    ```php
    $user = App\Models\User::where('email', 'seu-email@usp.br')->first();
    $user->assignRole('Admin');
    ```

**Atalho:** Para simplificar comandos, você pode criar um alias:
```bash
alias sail='./vendor/bin/sail'
```

Agora você pode usar `sail up -d`, `sail artisan migrate`, `sail npm run dev`, etc.

### 5.2. Instalação Tradicional (Sem Docker)

1.  **Pré-requisitos:**
    *   PHP >= 8.2 (com extensões comuns do Laravel: ctype, fileinfo, json, mbstring, openssl, PDO, tokenizer, xml, etc.)
    *   Composer
    *   Node.js (v18+) e NPM
    *   Git
    *   MySQL/MariaDB ou outro banco de dados compatível
    *   **Google Chrome** ou **Chromium** instalado (para testes Dusk)

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
    *   **Criar/Verificar `.env.dusk.local`:** Crie este arquivo na raiz do projeto (se não existir) e configure-o para o ambiente de teste do Dusk. Um exemplo (`.env.dusk.local`) já está incluído neste repositório. Preste atenção especial a:
        *   `APP_URL=http://127.0.0.1:8000` (ou a URL que `php artisan serve` usa)
        *   `DB_CONNECTION=sqlite` e `DB_DATABASE=database/testing/dusk.sqlite` (recomendado usar um banco de dados SQLite separado para testes Dusk)

Seu ambiente de desenvolvimento com o Starter Kit deve estar pronto para uso.

## 6. Uso Básico

### 6.1. Com Laravel Sail

1.  **Iniciar Containers (se não estiverem rodando):**
    ```bash
    ./vendor/bin/sail up -d
    ```

2.  **Acessar a Aplicação:**
    *   Abra seu navegador e acesse `http://localhost:8000` (ou a porta definida em `APP_PORT`).
    *   Páginas de autenticação: `/login` (Senha Única), `/login/local`, `/register`.
    *   Painel administrativo: `/admin` (requer autenticação e role Admin)

3.  **Parar Containers:**
    ```bash
    ./vendor/bin/sail down
    ```

4.  **Comandos Úteis:**
    ```bash
    # Executar comandos Artisan
    ./vendor/bin/sail artisan migrate

    # Executar npm
    ./vendor/bin/sail npm run dev

    # Acessar shell do container
    ./vendor/bin/sail shell

    # Ver logs
    ./vendor/bin/sail logs
    ```

### 6.2. Instalação Tradicional

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
    *   Painel administrativo: `/admin` (requer autenticação e role Admin)

### 6.3. Credenciais Padrão

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
*   **Fakes para Dependências USP:** O kit inclui classes `Fake` (ex: `FakeReplicadoService`, `FakeSenhaUnicaSocialiteProvider`) para facilitar a escrita de testes que interagem com as funcionalidades da Senha Única ou Replicado sem depender dos serviços reais (Planejado).

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

## 12. Licença

Este projeto é licenciado sob a **Licença MIT**. Veja o arquivo [LICENSE](./LICENSE) para mais detalhes.