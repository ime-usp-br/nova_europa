# Laravel 12 USP Starter Kit

[![Status da Build](https://github.com/ime-usp-br/laravel_12_starter_kit/actions/workflows/ci.yml/badge.svg)](https://github.com/ime-usp-br/laravel_12_starter_kit/actions/workflows/ci.yml) <!-- Placeholder: Ajustar URL quando o repositório existir -->
[![Latest Stable Version](https://img.shields.io/packagist/v/uspdev/laravel-usp-starter-kit)](https://packagist.org/packages/uspdev/laravel-usp-starter-kit) <!-- Placeholder: Ajustar URL quando o pacote existir -->
[![Total Downloads](https://img.shields.io/packagist/dt/uspdev/laravel-usp-starter-kit)](https://packagist.org/packages/uspdev/laravel-usp-starter-kit) <!-- Placeholder: Ajustar URL quando o pacote existir -->
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
    *   **Senha Única USP:** Integração completa e funcional via `uspdev/senhaunica-socialite`.
    *   **Autenticação Local:** Sistema de Login/Registro/Reset de Senha baseado no Laravel Breeze (TALL Stack), com verificação de e-mail.
    *   **Registro Unificado:** Formulário que diferencia usuários USP (com validação de Nº USP e e-mail via Replicado) e externos.
*   **Integração com Replicado:**
    *   Biblioteca `uspdev/replicado` configurada.
    *   `ReplicadoService`: Uma classe de serviço com métodos comuns para consulta de dados pessoais e vínculos.
*   **Gerenciamento de Permissões:**
    *   Integração com `spatie/laravel-permission`.
    *   Roles padrão pré-definidos (`Admin`, `User`, `usp_user`, `external_user`).
    *   Atribuição automática de roles no registro.
    *   Interface básica (TALL Stack) para gerenciamento de Usuários, Roles e Permissões (guard `web`).
    *   Aplicação de permissões hierárquicas e de vínculo vindas da Senha Única (guard `senhaunica`).
*   **Stack Frontend TALL:**
    *   Preset Breeze com **Livewire**, **Alpine.js** e **Tailwind CSS**.
    *   Componentes Blade básicos e reutilizáveis, adaptados visualmente às diretrizes da USP.
*   **Ferramentas de Qualidade:**
    *   **Laravel Pint:** Para formatação automática de código (PSR-12).
    *   **Larastan (PHPStan):** Para análise estática de código focada em Laravel.
    *   **EditorConfig:** Para manter a consistência de estilo entre editores.
*   **Testes Automatizados:**
    *   Estrutura inicial com testes unitários e de feature (PHPUnit).
    *   Facilitadores (`Fakes`) para testar integrações com Senha Única e Replicado sem depender dos serviços reais.
*   **Documentação:** README detalhado e [Wiki do Projeto](https://github.com/uspdev/laravel-usp-starter-kit/wiki) <!-- Placeholder: Ajustar URL quando o repositório existir --> para guias aprofundados.
*   **Configurações Adicionais:** Filas com driver `database`, exemplo de `supervisor.conf`, LogViewer básico.

*Para uma lista completa de funcionalidades incluídas e excluídas, consulte o [Termo de Abertura do Projeto](link-para-termo-abertura-na-wiki).* <!-- Placeholder: Link para Wiki -->

## 4. Stack Tecnológica

*   **Framework:** Laravel 12
*   **Linguagem:** PHP >= 8.2
*   **Frontend:**
    *   Vite
    *   Tailwind CSS 4
    *   Livewire 3
    *   Alpine.js 3
*   **Banco de Dados:** Suporte padrão do Laravel (MySQL, MariaDB, PostgreSQL, SQLite)
*   **Integrações USP:**
    *   `uspdev/senhaunica-socialite`
    *   `uspdev/replicado`
*   **Permissões:** `spatie/laravel-permission`
*   **Testes:** PHPUnit
*   **Qualidade:** Laravel Pint, Larastan

## 5. Instalação

Siga os passos abaixo para iniciar um novo projeto usando este Starter Kit:

1.  **Pré-requisitos:**
    *   PHP >= 8.2 (com extensões comuns do Laravel: ctype, fileinfo, json, mbstring, openssl, PDO, tokenizer, xml, etc.)
    *   Composer
    *   Node.js (v18+) e NPM
    *   Git

2.  **Clonar o Repositório:**
    ```bash
    git clone https://github.com/uspdev/laravel-usp-starter-kit.git seu-novo-projeto
    cd seu-novo-projeto
    ```
    <!-- Placeholder: Ajustar URL quando o repositório existir -->

3.  **Instalar Dependências:**
    ```bash
    composer install
    npm install
    ```

4.  **Configurar Ambiente:**
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
        *   `MAIL_*`: Configurações de e-mail (importante para verificação de e-mail no registro local).
        *   **Credenciais USP:** Adicione e configure as variáveis necessárias para `uspdev/senhaunica-socialite` e `uspdev/replicado` (veja a seção 7).

5.  **Banco de Dados e Dados Iniciais:**
    *   Execute as migrações para criar as tabelas no banco de dados:
        ```bash
        php artisan migrate
        ```
    *   (Opcional, mas recomendado) Execute os seeders para popular o banco com dados iniciais (ex: roles/permissions padrão, usuário de teste):
        ```bash
        php artisan migrate --seed
        ```
        *Nota: Por padrão, isso cria um usuário local `test@example.com` com senha `password`.*

6.  **Compilar Assets Frontend:**
    ```bash
    npm run build
    ```

## 6. Uso Básico

1.  **Iniciar Servidores:**
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
    *   Páginas de autenticação: `/login`, `/register`.

3.  **Credenciais Padrão:**
    *   Se você rodou `php artisan migrate --seed`, pode usar o usuário local:
        *   **Email:** `test@example.com`
        *   **Senha:** `password`

## 7. Configurações Específicas da USP

Para que as funcionalidades de integração com a USP funcionem corretamente, você **precisa** configurar as credenciais apropriadas no seu arquivo `.env`.

*   **Senha Única:** Adicione e preencha as variáveis `SENHAUNICA_CALLBACK`, `SENHAUNICA_KEY`, `SENHAUNICA_SECRET`. Consulte a [documentação do `uspdev/senhaunica-socialite`](https://github.com/uspdev/senhaunica-socialite) para detalhes sobre como obter essas credenciais.
*   **Replicado:** Adicione e preencha as variáveis `REPLICADO_HOST`, `REPLICADO_PORT`, `REPLICADO_DATABASE`, `REPLICADO_USERNAME`, `REPLICADO_PASSWORD`, `REPLICADO_CODUND`, `REPLICADO_CODBAS`. Consulte a [documentação do `uspdev/replicado`](https://github.com/uspdev/replicado) para detalhes.

*Instruções detalhadas sobre a configuração e uso dessas integrações podem ser encontradas na [Wiki do Projeto](https://github.com/uspdev/laravel-usp-starter-kit/wiki).* <!-- Placeholder: Ajustar URL -->

## 8. Ferramentas e Qualidade de Código

Este Starter Kit inclui ferramentas para ajudar a manter a qualidade e a consistência do código:

*   **Laravel Pint:** Formatador de código automático (PSR-12).
    *   Para formatar: `vendor/bin/pint`
*   **Larastan (PHPStan):** Ferramenta de análise estática para encontrar erros sem executar o código.
    *   Para analisar: `vendor/bin/phpstan analyse`
*   **EditorConfig:** Arquivo `.editorconfig` na raiz para padronizar configurações básicas do editor (indentação, fim de linha, etc.). Garanta que seu editor tenha o plugin EditorConfig instalado e ativado.

## 9. Testes

*   **Executando Testes:** Use o comando Artisan:
    ```bash
    php artisan test
    ```
*   **Fakes para Dependências USP:** O kit inclui classes `Fake` (ex: `FakeReplicadoService`, `FakeSenhaUnicaSocialiteProvider`) para facilitar a escrita de testes que interagem com as funcionalidades da Senha Única ou Replicado sem depender dos serviços externos reais. Consulte a [Wiki](link-para-wiki) para exemplos. <!-- Placeholder: Ajustar URL -->

## 10. Documentação

A documentação principal e mais detalhada deste Starter Kit reside na **[Wiki do GitHub](https://github.com/uspdev/laravel-usp-starter-kit/wiki)**. <!-- Placeholder: Ajustar URL -->

Lá você encontrará:

*   Este README.md.
*   O [Guia de Estratégia de Desenvolvimento](./guia_de_desenvolvimento.md) completo. <!-- Ou link para a Wiki -->
*   Detalhes sobre a arquitetura do código (Services, Repositories).
*   Explicações sobre o sistema de permissões e autenticação.
*   Tutoriais sobre como estender o kit.
*   Guias de configuração avançada e deploy (se aplicável).
*   Como usar os fakes para testes.

## 11. Como Contribuir

Contribuições são bem-vindas! Para garantir um desenvolvimento organizado e rastreável, siga o fluxo descrito no **[Guia de Estratégia de Desenvolvimento](link-para-guia-na-wiki)**. <!-- Placeholder: Ajustar URL -->

Em resumo:

1.  Identifique ou crie uma **Issue** atômica no GitHub descrevendo a tarefa (bug, feature, chore).
2.  Crie um **Branch** específico para a Issue a partir do branch principal (`main` ou `develop`).
3.  Faça **Commits Atômicos** e frequentes, sempre referenciando a Issue ID na mensagem (`#<ID>`).
4.  Abra um **Pull Request (PR)** claro, vinculando-o à Issue (`Closes #<ID>`).
5.  Aguarde a revisão (mesmo que seja auto-revisão) e a passagem da CI.
6.  Faça o **Merge** do PR.

## 12. Licença

Este projeto é licenciado sob a **Licença MIT**. Veja o arquivo [LICENSE](./LICENSE) para mais detalhes.
