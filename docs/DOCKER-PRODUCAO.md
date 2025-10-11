# Docker em Produção - Nova Europa

**Versão:** 1.0.0
**Data:** 2025-10-11
**Autor:** IME-USP Development Team

---

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Arquitetura](#arquitetura)
3. [Pré-requisitos](#pré-requisitos)
4. [Configuração Inicial](#configuração-inicial)
5. [Deploy](#deploy)
6. [Monitoramento](#monitoramento)
7. [Backup e Restore](#backup-e-restore)
8. [Troubleshooting](#troubleshooting)
9. [Segurança](#segurança)
10. [Manutenção](#manutenção)

---

## Visão Geral

Esta documentação descreve a configuração Docker para produção do sistema Nova Europa, incluindo todas as dependências críticas e boas práticas implementadas.

### Componentes Principais

- **PHP-FPM 8.2**: Servidor de aplicação Laravel
- **Nginx 1.27**: Reverse proxy e servidor web
- **MySQL 8.0**: Banco de dados local da aplicação
- **Redis 7**: Cache e sessões
- **Supervisor**: Gerenciamento de processos (queue workers, scheduler)
- **Puppeteer/Chrome**: Geração de PDFs
- **FreeTDS**: Conexão com SQL Server legado (Replicado USP)

### Características de Produção

✅ **Multi-stage build** - Otimização de tamanho de imagem
✅ **Health checks** - Monitoramento automático de saúde dos containers
✅ **Resource limits** - Limites de CPU e memória
✅ **Restart policies** - Alta disponibilidade
✅ **Volume persistence** - Dados persistentes
✅ **Security hardening** - Usuário não-root, security headers
✅ **Logging centralizado** - Logs para stdout/stderr
✅ **Zero-downtime deployment** - Deploy sem interrupção

---

## Arquitetura

### Diagrama de Containers

```
┌─────────────────────────────────────────────────┐
│                  Internet                       │
└────────────────────┬────────────────────────────┘
                     │
              ┌──────▼──────┐
              │   Nginx     │ :80/:443
              │  (Reverse   │
              │   Proxy)    │
              └──────┬──────┘
                     │
         ┌───────────┴───────────┐
         │                       │
    ┌────▼─────┐          ┌─────▼────┐
    │   App    │◄─────────┤  Queue   │
    │ (PHP-FPM)│          │  Worker  │
    └────┬─────┘          └─────┬────┘
         │                      │
    ┌────▼────────────┬─────────▼──┐
    │                 │            │
┌───▼───┐      ┌──────▼──┐   ┌────▼────┐
│ MySQL │      │  Redis  │   │Scheduler│
│  :3306│      │  :6379  │   │ (Cron)  │
└───────┘      └─────────┘   └─────────┘
```

### Volumes Persistentes

| Volume | Descrição | Criticidade |
|--------|-----------|-------------|
| `nova-europa-mysql-data` | Dados do MySQL | **CRÍTICO** - Backup obrigatório |
| `nova-europa-storage` | Storage do Laravel | **CRÍTICO** - Backup obrigatório |
| `nova-europa-puppeteer` | Cache do Puppeteer | Baixa - Regenerável |
| `nova-europa-redis-data` | Dados do Redis | Média - Cache/sessões |
| `nova-europa-nginx-cache` | Cache do Nginx | Baixa - Regenerável |

---

## Pré-requisitos

### Servidor de Produção

**Hardware mínimo recomendado:**
- CPU: 4 cores
- RAM: 8 GB
- Disco: 50 GB SSD
- Rede: Conexão estável com 100 Mbps

**Software:**
- Ubuntu 24.04 LTS (ou similar)
- Docker Engine 24.0+
- Docker Compose 2.20+
- Acesso root ou sudo

### Instalação do Docker

```bash
# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependências
sudo apt install -y ca-certificates curl gnupg lsb-release

# Adicionar repositório oficial do Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Instalar Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Verificar instalação
docker --version
docker-compose --version

# Adicionar usuário ao grupo docker (opcional)
sudo usermod -aG docker $USER
```

### Configurações de Rede

**Firewall:**
```bash
# Permitir HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Permitir SSH (se necessário)
sudo ufw allow 22/tcp

# Ativar firewall
sudo ufw enable
```

**Conexão com Replicado USP:**
- Garantir que o servidor de produção tem acesso ao IP `replicado.usp.br:1433`
- Testar conectividade: telnet replicado.usp.br 1433

---

## Configuração Inicial

### 1. Clonar Repositório

```bash
cd /opt
sudo git clone https://github.com/ime-usp/nova-europa.git
cd nova-europa
```

### 2. Configurar Variáveis de Ambiente

```bash
# Copiar template
sudo cp .env.production.example .env.production

# Editar configurações
sudo nano .env.production
```

**Configurações obrigatórias:**

```bash
# Aplicação
APP_KEY=                           # Gerar com: php artisan key:generate
APP_URL=https://europa.ime.usp.br
APP_DEBUG=false

# Banco de dados local
DB_DATABASE=europa
DB_USERNAME=europa_user
DB_PASSWORD=SENHA_FORTE_AQUI       # Mínimo 16 caracteres
DB_ROOT_PASSWORD=SENHA_ROOT_AQUI   # Mínimo 16 caracteres

# Replicado USP (CRÍTICO)
REPLICADO_HOST=replicado.usp.br
REPLICADO_PORT=1433
REPLICADO_USERNAME=usuario_replicado
REPLICADO_PASSWORD=senha_replicado

# Senha Única USP (OAuth)
SENHAUNICA_KEY=chave_senhaunica
SENHAUNICA_SECRET=secret_senhaunica
SENHAUNICA_CALLBACK_ID=callback_id

# Email (SMTP)
MAIL_HOST=smtp.gmail.com
MAIL_USERNAME=sistemas@ime.usp.br
MAIL_PASSWORD=senha_email
```

### 3. Gerar APP_KEY

```bash
# Build da imagem primeiro (necessário para rodar artisan)
sudo docker build -f docker/production/Dockerfile -t nova-europa:latest .

# Gerar chave
sudo docker run --rm -v $(pwd):/app nova-europa:latest php artisan key:generate --show

# Copiar a chave gerada e adicionar no .env.production
```

### 4. Ajustar Permissões

```bash
sudo chown -R 1000:1000 storage bootstrap/cache
sudo chmod -R 775 storage bootstrap/cache
```

---

## Deploy

### Deploy Inicial

```bash
# Tornar script executável
sudo chmod +x scripts/deploy.sh

# Executar deploy
sudo ./scripts/deploy.sh
```

O script `deploy.sh` executa automaticamente:

1. ✅ Validação de pré-requisitos
2. ✅ Build da imagem Docker
3. ✅ Backup do banco de dados (se existir)
4. ✅ Deploy dos containers
5. ✅ Execução de migrations
6. ✅ Otimização de cache (config, routes, views)
7. ✅ Health checks
8. ✅ Limpeza de imagens antigas

### Deploy Manual (Passo a Passo)

```bash
# 1. Build da imagem
sudo docker build -f docker/production/Dockerfile -t nova-europa:latest .

# 2. Parar containers antigos (se existirem)
sudo docker-compose -f docker-compose.prod.yml down

# 3. Iniciar novos containers
sudo docker-compose -f docker-compose.prod.yml up -d

# 4. Verificar status
sudo docker-compose -f docker-compose.prod.yml ps

# 5. Ver logs
sudo docker-compose -f docker-compose.prod.yml logs -f app
```

### Verificação do Deploy

```bash
# Health check
curl http://localhost/health

# Verificar containers
sudo docker ps

# Logs da aplicação
sudo docker-compose -f docker-compose.prod.yml logs --tail=100 app

# Entrar no container (debug)
sudo docker-compose -f docker-compose.prod.yml exec app bash
```

---

## Monitoramento

### Logs em Tempo Real

```bash
# Todos os containers
sudo docker-compose -f docker-compose.prod.yml logs -f

# Apenas aplicação
sudo docker-compose -f docker-compose.prod.yml logs -f app

# Apenas Nginx
sudo docker-compose -f docker-compose.prod.yml logs -f nginx

# Queue worker
sudo docker-compose -f docker-compose.prod.yml logs -f queue
```

### Status dos Containers

```bash
# Status geral
sudo docker-compose -f docker-compose.prod.yml ps

# Health checks
sudo docker inspect nova-europa-app | grep -A 10 "Health"

# Uso de recursos
sudo docker stats
```

### Monitoramento do Banco de Dados

```bash
# Entrar no MySQL
sudo docker-compose -f docker-compose.prod.yml exec mysql mysql -u root -p

# Verificar conexões ativas
SHOW PROCESSLIST;

# Tamanho dos bancos
SELECT table_schema AS "Database",
       ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS "Size (MB)"
FROM information_schema.TABLES
GROUP BY table_schema;
```

### Monitoramento de Performance

```bash
# PHP-FPM status
curl http://localhost/fpm-status

# PHP-FPM ping
curl http://localhost/fpm-ping

# Verificar slow queries
sudo docker-compose -f docker-compose.prod.yml exec mysql \
  tail -f /var/log/mysql/slow-query.log
```

---

## Backup e Restore

### Backup Automático

O script `backup.sh` cria backups completos do sistema:

```bash
# Tornar executável
sudo chmod +x scripts/backup.sh

# Executar backup
sudo ./scripts/backup.sh
```

**O que é copiado:**
- ✅ Dump completo do MySQL
- ✅ Volume de storage do Laravel
- ✅ Arquivo `.env.production`
- ✅ Manifest com instruções de restore

**Localização:** `/backups/backup-YYYYMMDD-HHMMSS/`

### Agendar Backups (Cron)

```bash
# Editar crontab do root
sudo crontab -e

# Adicionar linha (backup diário às 2h da manhã)
0 2 * * * /opt/nova-europa/scripts/backup.sh >> /var/log/nova-europa-backup.log 2>&1
```

### Restore Manual

```bash
# 1. Parar containers
sudo docker-compose -f docker-compose.prod.yml down

# 2. Restore do banco de dados
gunzip -c /backups/backup-YYYYMMDD-HHMMSS/mysql-database.sql.gz | \
  sudo docker-compose -f docker-compose.prod.yml exec -T mysql \
  mysql -u root -p

# 3. Restore do storage
sudo docker run --rm \
  -v nova-europa-storage:/target \
  -v /backups/backup-YYYYMMDD-HHMMSS:/backup \
  ubuntu:24.04 \
  tar xzf /backup/storage-volume.tar.gz -C /target

# 4. Restore do .env (se necessário)
sudo cp /backups/backup-YYYYMMDD-HHMMSS/.env.production.backup .env.production

# 5. Reiniciar containers
sudo docker-compose -f docker-compose.prod.yml up -d
```

---

## Troubleshooting

### Container não Inicia

```bash
# Verificar logs
sudo docker-compose -f docker-compose.prod.yml logs app

# Verificar configuração
sudo docker-compose -f docker-compose.prod.yml config

# Verificar saúde
sudo docker inspect nova-europa-app
```

**Problemas comuns:**

1. **APP_KEY não definida**
   ```bash
   sudo docker run --rm -v $(pwd):/app nova-europa:latest php artisan key:generate --force
   ```

2. **Erro de permissão em storage**
   ```bash
   sudo docker-compose -f docker-compose.prod.yml exec app chown -R www-data:www-data storage bootstrap/cache
   ```

3. **Banco de dados não conecta**
   - Verificar `DB_HOST=mysql` (nome do serviço Docker)
   - Verificar credenciais no `.env.production`
   - Testar conectividade: `docker-compose exec app php artisan db:show`

### Erro de Conexão com Replicado

```bash
# Verificar conectividade
telnet 200.144.255.61 62433

# Verificar FreeTDS
sudo docker-compose -f docker-compose.prod.yml exec app cat /etc/freetds/freetds.conf

# Testar conexão manualmente
sudo docker-compose -f docker-compose.prod.yml exec app php artisan tinker
>>> DB::connection('replicado')->getPdo();
```

### PDF não Gera (Puppeteer)

```bash
# Verificar se Chrome está instalado
sudo docker-compose -f docker-compose.prod.yml exec app \
  ls -la /var/www/.cache/puppeteer

# Reinstalar Chrome
sudo docker-compose -f docker-compose.prod.yml exec app \
  rm /var/www/.cache/puppeteer/.chrome-installed

# Reiniciar container (reinstala automaticamente)
sudo docker-compose -f docker-compose.prod.yml restart app
```

### Alto Uso de Memória

```bash
# Verificar uso
sudo docker stats

# Limpar cache do OPcache
sudo docker-compose -f docker-compose.prod.yml exec app php artisan optimize:clear

# Limpar cache do Redis
sudo docker-compose -f docker-compose.prod.yml exec redis redis-cli FLUSHALL
```

---

## Segurança

### Checklist de Segurança

- [ ] Firewall configurado (apenas portas 80, 443, 22)
- [ ] Senhas fortes (mínimo 16 caracteres)
- [ ] APP_DEBUG=false em produção
- [ ] SSL/TLS configurado (HTTPS)
- [ ] Credenciais do Replicado protegidas
- [ ] Backups criptografados
- [ ] Logs de acesso monitorados
- [ ] Atualizações de segurança aplicadas
- [ ] Rate limiting ativo (Nginx)
- [ ] Security headers configurados

### Configurar HTTPS (SSL/TLS)

**Usando Let's Encrypt (Certbot):**

```bash
# Instalar Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obter certificado
sudo certbot --nginx -d europa.ime.usp.br

# Renovação automática (já configurado pelo Certbot)
sudo certbot renew --dry-run
```

**Configurar Nginx para HTTPS:**

Editar `docker/production/nginx.conf` e descomentar as linhas de SSL.

### Rotação de Senhas

```bash
# Banco de dados
sudo docker-compose -f docker-compose.prod.yml exec mysql mysql -u root -p
ALTER USER 'europa_user'@'%' IDENTIFIED BY 'nova_senha_forte';
FLUSH PRIVILEGES;

# Atualizar .env.production
sudo nano .env.production

# Reiniciar containers
sudo docker-compose -f docker-compose.prod.yml restart
```

---

## Manutenção

### Atualização da Aplicação

```bash
# 1. Pull das últimas mudanças
cd /opt/nova-europa
sudo git pull origin main

# 2. Deploy
sudo ./scripts/deploy.sh
```

### Atualização do Docker

```bash
# Atualizar Docker Engine
sudo apt update
sudo apt upgrade -y docker-ce docker-ce-cli containerd.io

# Verificar versão
docker --version
```

### Limpeza de Disco

```bash
# Remover imagens não utilizadas
sudo docker image prune -a

# Remover volumes órfãos (cuidado!)
sudo docker volume prune

# Remover containers parados
sudo docker container prune

# Limpeza completa (CUIDADO!)
sudo docker system prune -a --volumes
```

### Escalabilidade

**Aumentar workers de Queue:**

Editar `docker-compose.prod.yml`:

```yaml
queue:
  deploy:
    replicas: 3  # Número de workers
```

**Aumentar PHP-FPM workers:**

Editar `docker/production/php-fpm.conf`:

```ini
pm.max_children = 100
pm.start_servers = 20
pm.min_spare_servers = 10
pm.max_spare_servers = 40
```

---

## Comandos Úteis

```bash
# Parar todos os containers
sudo docker-compose -f docker-compose.prod.yml stop

# Reiniciar containers
sudo docker-compose -f docker-compose.prod.yml restart

# Remover tudo (CUIDADO - perde dados!)
sudo docker-compose -f docker-compose.prod.yml down -v

# Rebuild forçado
sudo docker-compose -f docker-compose.prod.yml build --no-cache

# Executar comando no container
sudo docker-compose -f docker-compose.prod.yml exec app php artisan [comando]

# Shell interativo
sudo docker-compose -f docker-compose.prod.yml exec app bash

# Ver uso de disco dos volumes
sudo docker system df -v
```

---

## Suporte

**Problemas ou dúvidas:**

- GitHub Issues: https://github.com/ime-usp/nova-europa/issues
- Email: sistemas@ime.usp.br
- Documentação: `/docs/`

---

**Última atualização:** 2025-01-11
**Versão do documento:** 1.0.0
