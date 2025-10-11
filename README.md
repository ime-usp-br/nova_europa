# Nova Europa

**Versão:** 1.0.0  
**Data:** 2025-10-10

[![Status da Build](https://github.com/ime-usp-br/nova_europa/actions/workflows/laravel.yml/badge.svg)](https://github.com/ime-usp-br/nova_europa/actions/workflows/laravel.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 1. Introdução

O **Nova Europa** é a versão moderna e migrada do legado sistema acadêmico "Europa" do Instituto de Matemática, Estatística e Ciencia da Computação da Universidade de São Paulo (IME-USP). Desenvolvido em **Laravel 12**, o sistema tem como principal finalidade a geração de documentos acadêmicos em PDF para estudantes, com destaque para o relatório de evolução do aluno.

A migração moveu as regras de negócio, antes fixas em código Java, para uma arquitetura flexível e orientada a dados, onde a lógica é gerenciada através de um painel administrativo, garantindo maior manutenibilidade e agilidade para futuras atualizações curriculares.

## 2. Funcionalidades Principais

-   **Relatório de Evolução do Aluno:** Analisa o histórico de disciplinas cursadas pelo aluno em comparação com as exigências de seu currículo, classificando-as (obrigatórias, eletivas, livres, extracurriculares) e consolidando os créditos obtidos e necessários.
-   **Lógica Curricular Específica:**
    -   **Blocos (Licenciatura em Matemática):** Gerencia os requisitos de blocos de disciplinas.
    -   **Trilhas (Ciência da Computação):** Valida as regras das trilhas de especialização.
-   **Atestado de Matrícula:** Gera atestados simples em PDF para comprovação de matrícula.
-   **Painel Administrativo:** Interface construída com **Filament** para que administradores possam gerenciar usuários, permissões e, crucialmente, as regras de negócio (Blocos e Trilhas) sem a necessidade de alterar o código-fonte.

## 3. Arquitetura e Stack Tecnológica

O sistema foi construído sobre uma base moderna, priorizando a separação de responsabilidades e a testabilidade.

-   **Framework:** Laravel 12
-   **Frontend:** Stack TALL (Tailwind CSS, Alpine.js, Livewire)
-   **Painel Admin:** Filament v3
-   **Banco de Dados:** MySQL (para dados da aplicação) e SQL Server (leitura do Replicado USP)
-   **Geração de PDF:** `spatie/laravel-browsershot` (utilizando Puppeteer/Chrome)

### Principais Pacotes e Integrações

-   `uspdev/replicado`: Para integração com a base de dados corporativa da USP.
-   `spatie/laravel-permission`: Para gerenciamento de perfis e permissões.
-   `owen-it/laravel-auditing`: Para auditoria de alterações nos modelos.

### Arquitetura de Software

-   **Controllers Finos:** Responsáveis apenas por receber requisições e retornar respostas.
-   **Camada de Serviço:** A lógica de negócio é encapsulada em classes de serviço, como:
    -   `ReplicadoService`: Ponto central de acesso aos dados acadêmicos da USP.
    -   `EvolucaoService`: Orquestra o cálculo da evolução acadêmica do aluno.
    -   `PdfGenerationService`: Responsável por gerar os documentos em PDF.
-   **Regras de Negócio no Banco:** Blocos e Trilhas são armazenados no banco de dados e gerenciados via Filament, permitindo flexibilidade para futuras mudanças curriculares.

## 4. Instalação (Ambiente de Desenvolvimento)

A instalação é gerenciada via Docker e Laravel Sail.

### Pré-requisitos

-   Docker e Docker Compose
-   Git

### Passos para Instalação

1.  **Clonar o Repositório:**
    ```bash
    git clone https://github.com/ime-usp-br/nova-europa.git
    cd nova-europa
    ```

2.  **Configurar o Ambiente:**
    -   Copie o arquivo de configuração de ambiente:
        ```bash
        cp .env.example .env
        ```
    -   **Edite o arquivo `.env`** e configure as variáveis do banco de dados e da aplicação. As credenciais para o `ReplicadoService` também devem ser preenchidas.

3.  **Subir os Containers:**
    ```bash
    ./vendor/bin/sail up -d
    ```
    *(A primeira execução pode demorar alguns minutos para construir as imagens Docker).*

4.  **Instalar Dependências:**
    ```bash
    ./vendor/bin/sail composer install
    ./vendor/bin/sail npm install
    ```

5.  **Gerar Chave e Executar Migrações:**
    ```bash
    ./vendor/bin/sail artisan key:generate
    ./vendor/bin/sail artisan migrate --seed
    ```

6.  **Compilar Assets:**
    ```bash
    ./vendor/bin/sail npm run dev
    ```
    *(Mantenha este comando executando em um terminal separado durante o desenvolvimento).*

7.  **Acessar a Aplicação:**
    -   **URL:** `http://localhost` (ou a porta definida em `APP_PORT`).
    -   **Usuário Admin:** `admin@usp.br`
    -   **Senha:** `password`

## 5. Ferramentas de Qualidade e Testes

O projeto utiliza um conjunto de ferramentas para garantir a qualidade do código. Antes de realizar um commit, execute os seguintes comandos:

1.  **Formatação de Código (Pint):**
    ```bash
    ./vendor/bin/sail pint
    ```

2.  **Análise Estática (Larastan):**
    ```bash
    ./vendor/bin/sail phpstan analyse
    ```
    *(Todos os erros reportados pelo Larastan DEVEM ser corrigidos).*

3.  **Testes Automatizados (PHPUnit):**
    ```bash
    ./vendor/bin/sail artisan test
    ```

## 6. Documentação e Contribuição

-   **Guia de Desenvolvimento:** Para um guia detalhado sobre o fluxo de trabalho, padrões de código e arquitetura, consulte o documento [**GEMINI.md**](./GEMINI.md).
-   **Documentação de Análise e Arquitetura:** A pasta [`docs/`](./docs/) contém toda a documentação funcional e técnica do projeto.

Contribuições devem seguir o fluxo descrito no guia de desenvolvimento, utilizando Issues e Pull Requests no GitHub.

## 7. Licença

Este projeto é licenciado sob a **Licença MIT**. Veja o arquivo [LICENSE](./LICENSE) para mais detalhes.