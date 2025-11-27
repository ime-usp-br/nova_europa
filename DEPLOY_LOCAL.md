# Deploy Local com Docker (Simulando Produção)

Este guia explica como fazer o deploy do **Nova Europa** na sua máquina de desenvolvimento usando Docker (não Laravel Sail) para simular o ambiente de produção.

## 📋 Pré-requisitos

Antes de começar, certifique-se de ter instalado:

- **Docker Engine** (versão 20.10 ou superior)
- **Docker Compose** v2 (plugin, não standalone)

### Verificar Instalação

```bash
# Verificar Docker
docker --version
# Deve retornar: Docker version 20.10.x ou superior

# Verificar Docker Compose (plugin v2)
docker compose version
# Deve retornar: Docker Compose version v2.x.x
```

### Instalar Docker Compose Plugin (se necessário)

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install docker-compose-plugin
```

## 🚀 Deploy Rápido (Automatizado)

A forma mais rápida de fazer o deploy é usar o script automatizado:

```bash
# Tornar o script executável
sudo chmod +x scripts/deploy.sh

# Executar deploy
sudo ./scripts/deploy.sh
```

O script faz automaticamente:
- ✅ Verifica pré-requisitos
- ✅ Gera `APP_KEY` se não existir
- ✅ Constrói imagens Docker
- ✅ Inicia containers
- ✅ Aguarda health checks
- ✅ Executa migrações
- ✅ Verifica deployment

**Tempo estimado:** 10-15 minutos no primeiro build.

## 📖 Deploy Manual (Passo a Passo)

Se preferir entender cada etapa ou fazer deploy manual:

### 1. Configurar Variáveis de Ambiente

O arquivo `.env` já existe e está configurado para desenvolvimento. Para simular produção localmente, você pode:

**Opção A: Usar o `.env` atual (recomendado para testes locais)**
```bash
# Não precisa fazer nada, o .env já está configurado
```

**Opção B: Criar um `.env.production.local` específico**
```bash
# Copiar exemplo
cp .env.example .env.production.local

# Editar e configurar
nano .env.production.local
```

**Variáveis importantes a verificar:**

```env
# Aplicação
APP_NAME="Nova Europa"
APP_ENV=production
APP_DEBUG=false
APP_URL=http://localhost
APP_PORT=8002  # IMPORTANTE: Deve corresponder ao callback do Senha Única

# Banco de Dados Local
DB_CONNECTION=mysql
DB_HOST=mysql
DB_PORT=3306
DB_DATABASE=europa
DB_USERNAME=europa_user
DB_PASSWORD=sua_senha_forte_aqui
DB_ROOT_PASSWORD=sua_senha_root_forte_aqui

# Rede Docker (não alterar)
DOCKER_NETWORK_SUBNET=172.27.0.0/16
DOCKER_NETWORK_GATEWAY=172.27.0.1

# Replicado USP (já configurado no .env atual)
REPLICADO_HOST=200.144.255.61
REPLICADO_PORT=62433
# ... (outras variáveis já estão corretas)
```

> [!IMPORTANT]
> **Configuração da Porta (APP_PORT):**
> - A porta deve corresponder ao callback configurado no Senha Única Socialite
> - Se você alterou `APP_PORT`, também deve alterar `SENHAUNICA_CALLBACK_ID` para corresponder
> - Exemplo: Se `APP_PORT=8002`, o callback deve estar registrado como `http://localhost:8002/...`
> - Em produção, use a porta configurada no servidor (geralmente 80 ou 443)

### 2. Gerar APP_KEY (se necessário)

```bash
# Verificar se APP_KEY existe no .env
grep APP_KEY .env

# Se estiver vazio, gerar (após build da imagem)
```

### 3. Construir Imagens Docker

```bash
# Build da imagem de produção
docker build \
  -f docker/production/Dockerfile \
  -t nova-europa:latest \
  .
```

**Nota:** Este processo pode demorar 10-15 minutos na primeira vez, pois:
- Instala todas as dependências PHP e Node.js
- Compila assets frontend (Vite)
- Instala Puppeteer e Chrome para geração de PDFs
- Configura Nginx, PHP-FPM, FreeTDS (SQL Server)

### 4. Iniciar Containers

```bash
# Iniciar todos os serviços
docker compose -f docker-compose.prod.yml up -d

# Verificar status
docker compose -f docker-compose.prod.yml ps
```

**Containers esperados:**
- `nova-europa-app` - Nginx + PHP-FPM (porta 8016)
- `nova-europa-worker` - Queue worker (Supervisor)
- `nova-europa-mysql` - MySQL 8.0

### 5. Aguardar Health Checks

```bash
# Verificar logs do container app
docker compose -f docker-compose.prod.yml logs -f app

# Aguardar até ver:
# [INFO] Application is ready
```

### 6. Executar Migrações (se necessário)

```bash
# Executar migrações
docker compose -f docker-compose.prod.yml exec app php artisan migrate --force

# Executar seeders (opcional, para dados de teste)
docker compose -f docker-compose.prod.yml exec app php artisan db:seed --force
```

### 7. Verificar Deployment

```bash
# Verificar containers rodando
docker compose -f docker-compose.prod.yml ps

# Testar endpoint de saúde
curl http://localhost:8016/health

# Verificar logs sem erros críticos
docker compose -f docker-compose.prod.yml logs app | grep -i error
```

### 8. Acessar Aplicação

Abra o navegador em: **http://localhost:8016**

**Credenciais padrão (se seeders foram executados):**
- **Email:** `admin@usp.br`
- **Senha:** `password`

## 🛠️ Comandos Úteis

### Gerenciamento de Containers

```bash
# Ver status dos containers
docker compose -f docker-compose.prod.yml ps

# Ver logs em tempo real
docker compose -f docker-compose.prod.yml logs -f

# Ver logs apenas do app
docker compose -f docker-compose.prod.yml logs -f app

# Ver logs do worker
docker compose -f docker-compose.prod.yml logs -f worker

# Reiniciar containers
docker compose -f docker-compose.prod.yml restart

# Parar containers
docker compose -f docker-compose.prod.yml down

# Parar e remover volumes (CUIDADO: apaga banco de dados!)
docker compose -f docker-compose.prod.yml down --volumes
```

### Executar Comandos Artisan

```bash
# Sintaxe geral
docker compose -f docker-compose.prod.yml exec app php artisan <comando>

# Exemplos:
docker compose -f docker-compose.prod.yml exec app php artisan migrate
docker compose -f docker-compose.prod.yml exec app php artisan db:seed
docker compose -f docker-compose.prod.yml exec app php artisan cache:clear
docker compose -f docker-compose.prod.yml exec app php artisan config:clear
docker compose -f docker-compose.prod.yml exec app php artisan route:list
docker compose -f docker-compose.prod.yml exec app php artisan tinker
```

### Executar Composer

```bash
# Instalar dependências
docker compose -f docker-compose.prod.yml exec app composer install

# Atualizar dependências
docker compose -f docker-compose.prod.yml exec app composer update

# Adicionar pacote
docker compose -f docker-compose.prod.yml exec app composer require vendor/package
```

### Executar Testes

```bash
# PHPUnit
docker compose -f docker-compose.prod.yml exec app php artisan test

# Pint (code style)
docker compose -f docker-compose.prod.yml exec app ./vendor/bin/pint

# Larastan (análise estática)
docker compose -f docker-compose.prod.yml exec app ./vendor/bin/phpstan analyse
```

### Acessar Shell do Container

```bash
# Bash no container app
docker compose -f docker-compose.prod.yml exec app bash

# Bash no container worker
docker compose -f docker-compose.prod.yml exec worker bash

# MySQL CLI
docker compose -f docker-compose.prod.yml exec mysql mysql -u root -p
```

### Rebuild Após Mudanças no Código

```bash
# Rebuild e reiniciar
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d --build

# Ou usar o script de deploy
sudo ./scripts/deploy.sh
```

## 🔍 Troubleshooting

### Container não inicia

```bash
# Ver logs detalhados
docker compose -f docker-compose.prod.yml logs app

# Verificar se porta 8016 está livre
sudo lsof -i :8016

# Verificar se MySQL está saudável
docker compose -f docker-compose.prod.yml exec mysql mysqladmin ping -h localhost -u root -p
```

### Erro de conexão com banco de dados

```bash
# Verificar se MySQL está rodando
docker compose -f docker-compose.prod.yml ps mysql

# Testar conexão manualmente
docker compose -f docker-compose.prod.yml exec app php artisan tinker
# Dentro do tinker:
DB::connection()->getPdo();
```

### Erro de geração de PDF

```bash
# Verificar se Puppeteer está instalado
docker compose -f docker-compose.prod.yml exec app which node
docker compose -f docker-compose.prod.yml exec app which npx

# Verificar cache do Puppeteer
docker compose -f docker-compose.prod.yml exec app ls -la /var/www/.cache/puppeteer
```

### Erro de conexão com Replicado USP

```bash
# Testar conexão FreeTDS
docker compose -f docker-compose.prod.yml exec app bash
# Dentro do container:
tsql -H 200.144.255.61 -p 62433 -U sa

# Testar via PHP
docker compose -f docker-compose.prod.yml exec app php artisan tinker
# Dentro do tinker:
DB::connection('replicado')->getPdo();
```

### Limpar tudo e recomeçar

```bash
# Parar e remover tudo
docker compose -f docker-compose.prod.yml down --volumes

# Remover imagens
docker rmi nova-europa:latest

# Limpar sistema Docker
docker system prune -a

# Rebuild completo
sudo ./scripts/deploy.sh
```

## 📊 Monitoramento

### Verificar uso de recursos

```bash
# Ver uso de CPU/RAM dos containers
docker stats

# Ver espaço em disco dos volumes
docker system df
```

### Verificar logs da aplicação Laravel

```bash
# Logs do Laravel (dentro do container)
docker compose -f docker-compose.prod.yml exec app tail -f storage/logs/laravel.log

# Logs do PHP-FPM
docker compose -f docker-compose.prod.yml exec app tail -f storage/logs/php-fpm.log

# Logs do Nginx
docker compose -f docker-compose.prod.yml exec app tail -f /var/log/nginx/error.log
```

## 🔄 Atualizar Aplicação

Quando houver mudanças no código:

```bash
# Opção 1: Usar script de deploy (recomendado)
sudo ./scripts/deploy.sh

# Opção 2: Manual
git pull origin main
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec app php artisan migrate --force
```

## 🆚 Diferenças entre Deploy Local e Produção

| Aspecto | Deploy Local | Produção |
|---------|--------------|----------|
| **Ambiente** | Máquina de desenvolvimento | Servidor dedicado |
| **APP_ENV** | `production` (simulado) | `production` |
| **APP_DEBUG** | `false` | `false` |
| **Porta** | 8016 (customizável) | 80/443 |
| **SSL/HTTPS** | Não | Sim (certificados) |
| **Banco de Dados** | MySQL local (container) | MySQL local (container) |
| **Replicado** | Acesso direto (mesmas credenciais) | Acesso via firewall |
| **Backups** | Manual | Automatizado (cron) |
| **Monitoramento** | Logs locais | Sentry/NewRelic/ELK |

## 📝 Notas Importantes

1. **Este setup usa as mesmas imagens Docker de produção**, garantindo paridade entre ambientes
2. **Mudanças no código requerem rebuild** da imagem Docker (diferente do Sail que monta volumes)
3. **O build inicial é lento** (10-15 min), mas builds subsequentes são mais rápidos (cache)
4. **Use `sudo` para o script de deploy**, pois ele precisa acessar Docker como root
5. **Não commite o `.env`** com credenciais reais no Git

## 🔗 Links Úteis

- [README.md](./README.md) - Documentação geral do projeto
- [GEMINI.md](./GEMINI.md) - Guia de desenvolvimento
- [docker-compose.prod.yml](./docker-compose.prod.yml) - Configuração Docker
- [scripts/deploy.sh](./scripts/deploy.sh) - Script de deploy automatizado
