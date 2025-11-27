# Correção: Mixed Content em HTTPS

## Problema

Quando a aplicação é acessada via HTTPS em produção, os assets (CSS, JS, imagens) são carregados com URLs `http://` em vez de `https://`, causando erros de "Mixed Content" no navegador que bloqueia o carregamento desses recursos.

**Exemplo de erro no console:**
```
Mixed Content: The page at 'https://europa.ime.usp.br/login/local' was loaded over HTTPS, 
but requested an insecure stylesheet 'http://europa.ime.usp.br/build/assets/app-DqK4rYDh.css'. 
This request has been blocked; the content must be served over HTTPS.
```

## Causa

O Laravel está gerando URLs com esquema `http://` porque:
1. A aplicação está rodando em um container Docker que recebe requisições HTTP na porta 80
2. O proxy reverso (Nginx externo) faz terminação SSL e encaminha requisições HTTP para o container
3. O Laravel não sabe que a requisição original veio via HTTPS

## Solução Implementada

Duas mudanças foram feitas para resolver o problema:

### 1. Forçar HTTPS em Produção

**Arquivo:** `app/Providers/AppServiceProvider.php`

```php
public function boot(): void
{
    // Force HTTPS URLs in production (when behind reverse proxy)
    if ($this->app->environment('production')) {
        \Illuminate\Support\Facades\URL::forceScheme('https');
    }
    
    // ... resto do código
}
```

Isso força o Laravel a gerar todas as URLs com `https://` quando `APP_ENV=production`.

### 2. Confiar em Proxies Reversos

**Arquivo:** `bootstrap/app.php`

```php
->withMiddleware(function (Middleware $middleware) {
    // Trust all proxies (for reverse proxy/load balancer)
    // In production, you should specify exact proxy IPs instead of '*'
    $middleware->trustProxies(at: '*', headers: Request::HEADER_X_FORWARDED_FOR |
        Request::HEADER_X_FORWARDED_HOST |
        Request::HEADER_X_FORWARDED_PORT |
        Request::HEADER_X_FORWARDED_PROTO |
        Request::HEADER_X_FORWARDED_AWS_ELB);
    
    // ... resto do código
})
```

Isso configura o Laravel para confiar nos headers `X-Forwarded-*` enviados pelo proxy reverso, permitindo detectar corretamente o esquema HTTPS original.

## Como Aplicar em Produção

### Opção 1: Deploy Automatizado (Recomendado)

```bash
# No servidor de produção
cd /var/www/nova-europa
git pull origin main
sudo ./scripts/deploy.sh
```

O script de deploy irá:
- Fazer backup do banco de dados
- Construir nova imagem Docker com as correções
- Parar containers antigos
- Iniciar novos containers
- Executar migrações
- Verificar saúde da aplicação

### Opção 2: Deploy Manual

```bash
# No servidor de produção
cd /var/www/nova-europa

# Atualizar código
git pull origin main

# Rebuild da imagem
docker build -f docker/production/Dockerfile -t nova-europa:latest .

# Parar containers
docker compose -f docker-compose.prod.yml down

# Iniciar novos containers
docker compose -f docker-compose.prod.yml up -d

# Verificar status
docker compose -f docker-compose.prod.yml ps

# Verificar logs
docker compose -f docker-compose.prod.yml logs -f app
```

## Verificação

Após o deploy, verifique:

1. **Acesse a aplicação via HTTPS:**
   ```
   https://europa.ime.usp.br
   ```

2. **Abra o Console do Navegador (F12):**
   - Não deve haver erros de "Mixed Content"
   - Todos os assets devem carregar com `https://`

3. **Inspecione o HTML:**
   - Todas as URLs de assets devem começar com `https://`
   - Exemplo: `https://europa.ime.usp.br/build/assets/app-DqK4rYDh.css`

## Configuração do Proxy Reverso

Certifique-se de que o Nginx (ou outro proxy reverso) está enviando os headers corretos:

```nginx
location / {
    proxy_pass http://localhost:8016;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-Port $server_port;
}
```

Os headers `X-Forwarded-*` são essenciais para que o Laravel detecte corretamente:
- `X-Forwarded-Proto`: Esquema original (https)
- `X-Forwarded-Host`: Host original (europa.ime.usp.br)
- `X-Forwarded-Port`: Porta original (443)

## Segurança: Especificar IPs de Proxies Confiáveis

⚠️ **IMPORTANTE:** Em produção, é recomendado especificar os IPs exatos dos proxies em vez de confiar em todos (`*`).

**Editar `bootstrap/app.php`:**

```php
$middleware->trustProxies(
    at: ['172.27.0.1', '10.0.0.1'], // IPs dos seus proxies
    headers: Request::HEADER_X_FORWARDED_FOR |
        Request::HEADER_X_FORWARDED_HOST |
        Request::HEADER_X_FORWARDED_PORT |
        Request::HEADER_X_FORWARDED_PROTO |
        Request::HEADER_X_FORWARDED_AWS_ELB
);
```

Para descobrir o IP do proxy:

```bash
# Dentro do container
docker compose -f docker-compose.prod.yml exec app ip route | grep default
```

## Troubleshooting

### Assets ainda carregam com HTTP

1. **Limpar cache do Laravel:**
   ```bash
   docker compose -f docker-compose.prod.yml exec app php artisan cache:clear
   docker compose -f docker-compose.prod.yml exec app php artisan config:clear
   docker compose -f docker-compose.prod.yml exec app php artisan route:clear
   docker compose -f docker-compose.prod.yml exec app php artisan view:clear
   ```

2. **Verificar variável APP_ENV:**
   ```bash
   docker compose -f docker-compose.prod.yml exec app php artisan env
   ```
   Deve mostrar `production`.

3. **Verificar headers do proxy:**
   ```bash
   # Ver headers recebidos pelo Laravel
   docker compose -f docker-compose.prod.yml exec app php artisan tinker
   >>> request()->headers->all()
   ```

### Erro "Too many redirects"

Se houver loop de redirecionamento, verifique:

1. **Proxy não está enviando X-Forwarded-Proto:**
   - Adicione `proxy_set_header X-Forwarded-Proto $scheme;` no Nginx

2. **APP_URL está incorreto:**
   - Deve ser `https://europa.ime.usp.br` (com HTTPS)

## Referências

- [Laravel Docs: Proxies](https://laravel.com/docs/12.x/requests#configuring-trusted-proxies)
- [Laravel Docs: URL Generation](https://laravel.com/docs/12.x/urls)
- [Chrome Mixed Content](https://developers.google.com/web/fundamentals/security/prevent-mixed-content/what-is-mixed-content)
