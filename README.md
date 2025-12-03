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
    -   **Edite o arquivo `.env`** e configure as variáveis.
    -   **Atenção:** Se você já possui um serviço MySQL rodando na porta 3306, altere a porta do banco no `.env`:
        ```env
        FORWARD_DB_PORT=3307
        ```

3.  **Instalar Dependências (Ovo e Galinha):**
    Para rodar o Sail, precisamos instalar as dependências do Composer primeiro.

    **Opção A: Se você tem PHP e Composer instalados localmente:**
    ```bash
    composer install --ignore-platform-reqs
    ```

    **Opção B: Se você NÃO tem PHP instalado (via Docker):**
    ```bash
    docker run --rm \
        -u "$(id -u):$(id -g)" \
        -v "$(pwd):/var/www/html" \
        -w /var/www/html \
        laravelsail/php83-composer:latest \
        composer install --ignore-platform-reqs
    ```

4.  **Subir os Containers:**
    Agora que o `vendor/` existe, podemos iniciar o Sail:
    ```bash
    ./vendor/bin/sail up -d
    ```

5.  **Gerar Chave e Executar Migrações:**
    ```bash
    ./vendor/bin/sail artisan key:generate
    ./vendor/bin/sail artisan migrate:fresh --seed
    ```

6.  **Instalar Dependências de Frontend:**
    ```bash
    ./vendor/bin/sail npm install
    ```

7.  **Compilar Assets:**
    ```bash
    ./vendor/bin/sail npm run dev
    ```
    *(Mantenha este comando executando em um terminal separado).*

8.  **Acessar a Aplicação:**
    -   **URL:** `http://localhost` (ou a porta definida em `APP_PORT`).
    -   **Usuário Admin:** `admin@usp.br`
    -   **Senha:** `password`

### Troubleshooting (Problemas Comuns)

#### Erro: "Address already in use" (Porta 3306)
Se ao rodar `./vendor/bin/sail up -d` você ver um erro como:
`driver failed programming external connectivity ... failed to bind host port ... 0.0.0.0:3306 ... address already in use`

Isso significa que você já tem um MySQL rodando na sua máquina (fora do Docker).
**Solução:** Edite o arquivo `.env` e mude a porta externa do banco:
```env
FORWARD_DB_PORT=3313
```
Depois, reinicie o Sail:
```bash
./vendor/bin/sail down
./vendor/bin/sail up -d
```

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

## 6. Deploy em Produção

O sistema está preparado para deploy automatizado via Docker em ambiente de produção.

### 6.1. Pré-requisitos

Antes de realizar o deploy, certifique-se de que o servidor de produção possui:

-   **Docker Engine** (versão 20.10 ou superior)
-   **Docker Compose** v2 (plugin, não standalone)
    ```bash
    # Verificar instalação
    docker compose version
    # Se não estiver instalado (Ubuntu/Debian):
    sudo apt install docker-compose-plugin
    ```
-   **Permissões:** Acesso root ou sudo
-   **Firewall:** Liberar portas necessárias:
    -   Porta da aplicação (ex: 8016 ou 80/443)
    -   Porta do Replicado (geralmente 1433) - conectividade de saída
-   **Recursos:** Mínimo 2GB RAM, 20GB disco

### 6.2. Configuração Inicial

1.  **Clonar o Repositório:**
    ```bash
    cd /var/www  # ou diretório de sua escolha
    git clone https://github.com/ime-usp-br/nova-europa.git
    cd nova-europa
    ```

2.  **Configurar Variáveis de Ambiente:**
    ```bash
    cp .env.example .env
    nano .env  # ou seu editor preferido
    ```

3.  **Configurações Críticas no `.env`:**

    **Aplicação:**
    ```env
    APP_NAME="Nova Europa"
    APP_ENV=production
    APP_DEBUG=false
    APP_URL=https://europa.ime.usp.br
    APP_PORT=80  # ou 8016, 443, conforme necessário
    ```

    **Banco de Dados Local:**
    ```env
    DB_DATABASE=europa
    DB_USERNAME=europa_user
    DB_PASSWORD=SENHA_FORTE_AQUI
    DB_ROOT_PASSWORD=SENHA_ROOT_FORTE_AQUI
    ```

    **Replicado (Banco Corporativo USP):**
    ```env
    REPLICADO_HOST=replicado.usp.br
    REPLICADO_PORT=1433
    REPLICADO_DATABASE=replicado
    REPLICADO_USERNAME=SEU_USUARIO_REPLICADO
    REPLICADO_PASSWORD=SUA_SENHA_REPLICADO
    REPLICADO_CODUNDCLG=45  # Código da unidade (IME)
    ```

    **Senha Única (OAuth USP):**
    ```env
    SENHAUNICA_KEY=SUA_CHAVE_OAUTH
    SENHAUNICA_SECRET=SEU_SECRET_OAUTH
    SENHAUNICA_CALLBACK_ID=SEU_CALLBACK_ID
    ```

    **Email (Opcional):**
    ```env
    MAIL_MAILER=smtp
    MAIL_HOST=smtp.gmail.com
    MAIL_PORT=587
    MAIL_USERNAME=sistemas@ime.usp.br
    MAIL_PASSWORD=SENHA_EMAIL
    MAIL_ENCRYPTION=tls
    MAIL_FROM_ADDRESS=sistemas@ime.usp.br
    ```

    **Rede Docker (Importante para PHP-FPM):**
    ```env
    # Não altere estes valores a menos que haja conflito de rede
    DOCKER_NETWORK_SUBNET=172.27.0.0/16
    DOCKER_NETWORK_GATEWAY=172.27.0.1
    ```

    **Filas:**
    ```env
    QUEUE_CONNECTION=database
    ```

    **IMPORTANTE:**
    -   **Não commitar** o arquivo `.env` no Git (já está no `.gitignore`)
    -   Use senhas fortes (mínimo 16 caracteres, letras maiúsculas/minúsculas, números, símbolos)
    -   O `APP_KEY` será gerado automaticamente pelo script de deploy

### 6.3. Deploy Automatizado

O projeto inclui um script que automatiza todo o processo de deploy:

```bash
# Tornar o script executável
sudo chmod +x scripts/deploy.sh

# Executar deploy
sudo ./scripts/deploy.sh
```

**O que o script faz automaticamente:**

1.  ✅ Verifica pré-requisitos (Docker, Docker Compose, .env)
2.  ✅ Gera `APP_KEY` se não existir
3.  ✅ Cria backup do banco de dados (se já existir deploy anterior)
4.  ✅ Constrói imagens Docker otimizadas (multi-stage build)
5.  ✅ Para containers antigos de forma segura
6.  ✅ Inicia novos containers
7.  ✅ Aguarda health checks
8.  ✅ Executa migrações de banco de dados
9.  ✅ Otimiza cache de rotas e views
10. ✅ Remove imagens antigas (mantém últimas 3 versões)

**Exemplo de saída do script:**

```
[STEP] =======================================================================
[STEP] Nova Europa - Production Deployment
[STEP] =======================================================================
[INFO] All prerequisites met
[INFO] Existing deployment detected, creating backup...
[INFO] Database backup created: /backups/pre-deploy/mysql-backup-20251014-143022.sql
[INFO] Building version: 20251014-143022
[INFO] Image built successfully: nova-europa:20251014-143022
[INFO] Stopping old containers...
[INFO] Starting new containers...
[INFO] Containers started successfully
[INFO] Application is healthy!
[STEP] =======================================================================
[STEP] Deployment completed successfully!
[STEP] =======================================================================
```

### 6.4. Deploy Manual (Passo a Passo)

Se preferir executar manualmente ou entender cada etapa:

```bash
# 1. Gerar APP_KEY (se necessário)
docker run --rm -v $(pwd):/app -w /app php:8.2-cli php artisan key:generate

# 2. Construir imagem
docker build -f docker/production/Dockerfile -t nova-europa:latest .

# 3. Parar containers antigos
docker compose -f docker-compose.prod.yml down

# 4. Iniciar containers
docker compose -f docker-compose.prod.yml up -d

# 5. Verificar status
docker compose -f docker-compose.prod.yml ps

# 6. Executar migrações (dentro do container)
docker compose -f docker-compose.prod.yml exec app php artisan migrate --force

# 7. Verificar logs
docker compose -f docker-compose.prod.yml logs -f app
```

### 6.5. Arquitetura de Produção

O ambiente de produção utiliza uma arquitetura Docker simplificada:

```
┌─────────────────────────────────────────┐
│         Docker Host (Servidor)          │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │  Container: nova-europa-app     │   │
│  │  ┌───────────┐  ┌────────────┐  │   │
│  │  │   Nginx   │→ │  PHP-FPM   │  │   │
│  │  │   :80     │  │  Laravel   │  │   │
│  │  └───────────┘  └────────────┘  │   │
│  │       ↑              ↓           │   │
│  │    Requests    Puppeteer/PDF    │   │
│  └────────┬────────────┬────────────┘   │
│           │            │                │
│  ┌────────┴────────────┴────────────┐   │
│  │ Container: nova-europa-worker   │   │
│  │     Queue Worker (Supervisor)   │   │
│  └────────┬────────────────────────┘    │
│           │                            │
│  ┌────────┴────────────────────────┐   │
│  │  Container: nova-europa-mysql   │   │
│  │       MySQL 8.0 (Local DB)      │   │
│  └─────────────────────────────────┘   │
│                                         │
│         ↓ (Rede Externa)                │
└─────────┼───────────────────────────────┘
          │
    ┌─────┴──────────────────┐
    │  Replicado USP (1433)  │
    │   SQL Server (Leitura) │
    └────────────────────────┘
```

**Componentes:**

-   **app:** Nginx + PHP-FPM no mesmo container (simplificado)
-   **worker:** Container dedicado para processar filas (jobs assíncronos)
-   **mysql:** Banco de dados local da aplicação
-   **Replicado:** Banco corporativo USP (externo, acesso via FreeTDS/ODBC)

**Volumes Persistentes:**

-   `./storage` → Logs, cache, uploads, PDFs gerados
-   `mysql-data` → Dados do MySQL

### 6.6. Troubleshooting

Durante o desenvolvimento do deploy em produção, os seguintes problemas foram identificados e **resolvidos** (todas as soluções já estão integradas ao projeto):

#### 6.6.1. Problemas Resolvidos

| Problema | Sintoma | Solução (Commit) |
|----------|---------|------------------|
| **PDF não gera** | Erro ao gerar documentos | `proc_open` removido de `disable_functions` no PHP-FPM ([874ae95](https://github.com/ime-usp-br/nova_europa/commit/874ae95)) |
| **Conexão Replicado falha** | Erro TLS/SSL com SQL Server | FreeTDS configurado com suporte legacy TLS, driver Sybase instalado ([803edf3](https://github.com/ime-usp-br/nova_europa/commit/803edf3), [f30a384](https://github.com/ime-usp-br/nova_europa/commit/f30a384)) |
| **PHP-FPM não responde** | Nginx retorna 502/504 | Configuração dinâmica de `listen.allowed_clients` baseada na subnet Docker ([ddfde08](https://github.com/ime-usp-br/nova_europa/commit/ddfde08)) |
| **Logs não aparecem** | Dificuldade para debugar | Logs do PHP-FPM redirecionados para `storage/logs/` ([f6b8d7d](https://github.com/ime-usp-br/nova_europa/commit/f6b8d7d)) |
| **Build muito pesado** | Imagens Docker grandes | Multi-stage build: builder stage separado para compilação ([8cdd706](https://github.com/ime-usp-br/nova_europa/commit/8cdd706)) |
| **Puppeteer falha** | Chrome não encontrado | Puppeteer instalado durante build do Dockerfile, não no runtime ([0d63df4](https://github.com/ime-usp-br/nova_europa/commit/0d63df4)) |
| **Complexidade desnecessária** | Múltiplos containers difíceis de gerenciar | Arquitetura simplificada: Nginx + PHP-FPM no mesmo container ([ef934d8](https://github.com/ime-usp-br/nova_europa/commit/ef934d8)) |

#### 6.6.2. Verificação de Logs

```bash
# Logs do container app (Nginx + PHP-FPM + Laravel)
docker compose -f docker-compose.prod.yml logs -f app

# Logs do worker (filas)
docker compose -f docker-compose.prod.yml logs -f worker

# Logs do MySQL
docker compose -f docker-compose.prod.yml logs -f mysql

# Logs específicos do Laravel (dentro do container)
docker compose -f docker-compose.prod.yml exec app tail -f storage/logs/laravel.log

# Verificar processos em execução
docker compose -f docker-compose.prod.yml exec app ps aux
```

#### 6.6.3. Reiniciar Containers

```bash
# Reiniciar apenas o app
docker compose -f docker-compose.prod.yml restart app

# Reiniciar todos os serviços
docker compose -f docker-compose.prod.yml restart

# Rebuild completo (se houver mudanças no código)
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d --build
```

#### 6.6.4. Limpar e Reconstruir do Zero

```bash
# Parar e remover tudo (CUIDADO: remove volumes!)
docker compose -f docker-compose.prod.yml down --volumes

# Limpar imagens antigas
docker system prune -a

# Rebuild completo
sudo ./scripts/deploy.sh
```

#### 6.6.5. Testar Conectividade com Replicado

```bash
# Entrar no container
docker compose -f docker-compose.prod.yml exec app bash

# Testar conexão FreeTDS
tsql -H replicado.usp.br -p 1433 -U seu_usuario

# Testar via PHP (dentro do container)
php artisan tinker
>>> DB::connection('replicado')->getPdo();
```

### 6.7. Verificação Pós-Deploy

Após o deploy bem-sucedido, verifique:

1.  **Containers rodando:**
    ```bash
    docker compose -f docker-compose.prod.yml ps
    ```
    Deve mostrar: `app`, `worker`, `mysql` todos com status `Up`

2.  **Aplicação respondendo:**
    ```bash
    curl http://localhost:8016/health
    # Deve retornar HTTP 200
    ```

3.  **Banco de dados:**
    ```bash
    docker compose -f docker-compose.prod.yml exec app php artisan db:show
    ```

4.  **Logs sem erros críticos:**
    ```bash
    docker compose -f docker-compose.prod.yml logs app | grep -i error
    ```

5.  **Acessar via navegador:**
    -   URL: `http://<seu-servidor>:8016` (ou porta configurada)
    -   Login via Senha Única USP deve funcionar

### 6.8. Manutenção

**Backup Automático:**

O script `scripts/backup.sh` pode ser configurado no cron para backups periódicos:

```bash
# Executar backup manualmente
sudo ./scripts/backup.sh

# Agendar no cron (exemplo: todo dia às 2h)
sudo crontab -e
# Adicionar linha:
0 2 * * * /var/www/nova-europa/scripts/backup.sh
```

**Atualizar Aplicação:**

```bash
cd /var/www/nova-europa
git pull origin main
sudo ./scripts/deploy.sh  # Faz deploy automático da nova versão
```

**Monitoramento:**

-   Logs centralizados em `storage/logs/laravel.log`
-   Considere integrar com ferramentas como: Sentry, NewRelic, ou ELK Stack

## 7. Documentação e Contribuição

-   **Guia de Desenvolvimento:** Para um guia detalhado sobre o fluxo de trabalho, padrões de código e arquitetura, consulte o documento [**GEMINI.md**](./GEMINI.md).
-   **Documentação de Análise e Arquitetura:** A pasta [`docs/`](./docs/) contém toda a documentação funcional e técnica do projeto.

Contribuições devem seguir o fluxo descrito no guia de desenvolvimento, utilizando Issues e Pull Requests no GitHub.

## 8. Licença

Este projeto é licenciado sob a **Licença MIT**. Veja o arquivo [LICENSE](./LICENSE) para mais detalhes.