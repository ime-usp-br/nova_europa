# Browsershot/Puppeteer Setup para Laravel Sail

**Documento:** Configuração completa do Browsershot com Puppeteer para geração de PDFs em ambiente Docker (Laravel Sail)

**Data:** 2025-10-08

**Versões:**
- Laravel Sail (Ubuntu 24.04 Noble base image)
- Browsershot: ^5.0
- Puppeteer: Latest (141.0.7390.54 no momento da configuração)
- Chrome Headless Shell: 141.0.7390.54

---

## ⚠️ IMPORTANTE: Integração Futura no Dockerfile

**ESTE DOCUMENTO DESCREVE CONFIGURAÇÃO MANUAL TEMPORÁRIA.**

As soluções descritas aqui precisam ser **incorporadas ao Dockerfile do Laravel Sail** para que funcionem automaticamente em novos ambientes. Atualmente, estas configurações foram aplicadas **manualmente** em um container já em execução.

**Próximos passos obrigatórios:**
1. Modificar o Dockerfile do Sail para incluir todas as dependências do sistema
2. Adicionar instalação do Puppeteer ao processo de build da imagem
3. Configurar variáveis de ambiente necessárias
4. Documentar no README do projeto

---

## Contexto

O projeto Nova Europa utiliza **Spatie Browsershot** para gerar PDFs complexos de evolução acadêmica de estudantes. O Browsershot depende do **Puppeteer** (biblioteca Node.js) que por sua vez depende do **Chrome/Chromium headless browser**.

**Por que Browsershot?**
- PDFs complexos com layouts sofisticados
- Suporte completo a HTML/CSS moderno (muito mais fácil que bibliotecas de geração programática)
- Renderização idêntica ao navegador
- Suporte a tabelas complexas, grids CSS, cores, fontes personalizadas

**Desafio:**
Laravel Sail é um ambiente Docker, e configurar Chrome/Puppeteer em containers Docker requer dependências de sistema específicas e configurações de segurança.

---

## Problemas Encontrados e Soluções

### Problema 1: Puppeteer não instalado

**Erro:**
```
Cannot find module 'puppeteer'
Error: Cannot find module 'puppeteer'
    at Module._resolveFilename (node:internal/modules/cjs/loader:1225:15)
```

**Causa:**
O Browsershot depende do Puppeteer (pacote npm), mas ele não vem instalado por padrão no Laravel Sail.

**Solução Manual (temporária):**
```bash
./vendor/bin/sail exec laravel.test npm install puppeteer
```

**Solução Permanente (para Dockerfile):**
Adicionar ao Dockerfile do Sail, na seção de instalação de dependências Node.js:
```dockerfile
# Instalar Puppeteer globalmente
RUN npm install -g puppeteer
```

---

### Problema 2: Chrome/Chromium não instalado

**Erro:**
```
Error: Could not find Chrome (ver. 141.0.7390.54). This can occur if either
 1. you did not perform an installation before running the script (e.g. `npx puppeteer browsers install chrome-headless-shell`) or
 2. your cache path is incorrectly configured (which is: /home/sail/.cache/puppeteer).
```

**Causa:**
O Puppeteer precisa de um navegador Chrome/Chromium para funcionar. Por padrão, ele tenta baixar automaticamente, mas em ambientes Docker isso pode falhar.

**Tentativa 1 (não funcionou):**
```bash
npx puppeteer browsers install chrome
```
- Problema: Instalou em `/root/.cache/puppeteer` mas Puppeteer procura em `/home/sail/.cache/puppeteer`

**Solução Manual Correta (temporária):**
```bash
# Instalar chrome-headless-shell (versão otimizada para headless)
# com cache path correto para o usuário 'sail'
./vendor/bin/sail exec laravel.test bash -c "PUPPETEER_CACHE_DIR=/home/sail/.cache/puppeteer npx puppeteer browsers install chrome-headless-shell"
```

**Por que `chrome-headless-shell` e não `chrome` completo?**
- Versão mais leve e otimizada para uso em servidor
- Sem interface gráfica desnecessária
- Menor tamanho de download e armazenamento
- Recomendado para ambientes de produção

**Solução Permanente (para Dockerfile):**
```dockerfile
# Definir cache path do Puppeteer
ENV PUPPETEER_CACHE_DIR=/home/sail/.cache/puppeteer

# Criar diretório de cache com permissões corretas
RUN mkdir -p /home/sail/.cache/puppeteer && \
    chown -R sail:sail /home/sail/.cache

# Instalar chrome-headless-shell
RUN npx puppeteer browsers install chrome-headless-shell

# Garantir permissões corretas
RUN chown -R sail:sail /home/sail/.cache/puppeteer
```

---

### Problema 3: Bibliotecas de sistema ausentes

**Erro:**
```
Error: Failed to launch the browser process: Code: 127

stderr:
/home/sail/.cache/puppeteer/chrome-headless-shell/linux-141.0.7390.54/chrome-headless-shell-linux64/chrome-headless-shell: error while loading shared libraries: libnspr4.so: cannot open shared object file: No such file or directory
```

**Causa:**
O Chrome/Chromium depende de várias bibliotecas de sistema Linux que não vêm instaladas por padrão na imagem base do Laravel Sail.

**Bibliotecas necessárias:**
- `libnspr4` - Netscape Portable Runtime (biblioteca de tempo de execução)
- `libnss3` - Network Security Services (segurança de rede)
- Várias bibliotecas X11 para renderização (mesmo em modo headless)
- Bibliotecas de áudio (ALSA)

**Solução Manual (temporária):**
```bash
./vendor/bin/sail exec laravel.test apt-get update

./vendor/bin/sail exec laravel.test apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2t64 \
    libxtst6 \
    libxshmfence1
```

**Nota sobre Ubuntu 24.04:**
Ubuntu 24.04 (Noble) usa sufixo `t64` em alguns pacotes (transição para time64_t). Por exemplo: `libasound2` → `libasound2t64`.

**Solução Permanente (para Dockerfile):**
```dockerfile
# Instalar dependências do Chrome/Chromium
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2t64 \
    libxtst6 \
    libxshmfence1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
```

---

### Problema 4: Sandbox do Chrome em ambiente Docker

**Erro:**
```
Error: Failed to launch the browser process: Code: null

stderr:
[1008/215845.206675:FATAL:content/browser/zygote_host/zygote_host_impl_linux.cc:128] No usable sandbox! If you are running on Ubuntu 23.10+ or another Linux distro that has disabled unprivileged user namespaces with AppArmor, see https://chromium.googlesource.com/chromium/src/+/main/docs/security/apparmor-userns-restrictions.md. Otherwise see https://chromium.googlesource.com/chromium/src/+/main/docs/linux/suid_sandbox_development.md for more information on developing with the (older) SUID sandbox. If you want to live dangerously and need an immediate workaround, you can try using --no-sandbox.
```

**Causa:**
O Chrome usa sandboxing (isolamento de processos) por segurança. Em containers Docker, o sandboxing do Chrome entra em conflito com o isolamento do próprio Docker, causando falha na inicialização.

**Solução no Código (PdfGenerationService.php):**
```php
$pdfContent = Browsershot::html($html)
    ->setNodeBinary('/usr/bin/node')
    ->setNpmBinary('/usr/bin/npm')
    ->noSandbox() // ← ADICIONAR ESTA LINHA
    ->format('A4')
    ->margins(10, 10, 10, 10)
    ->showBackground()
    ->pdf();
```

**Por que isso é seguro?**
- O Docker já fornece isolamento através de containers
- O código é executado em ambiente controlado (não acessa internet arbitrária)
- Alternativa comum e documentada para ambientes Docker/CI
- Recomendado oficialmente pelo Puppeteer para containers

**Referências:**
- [Puppeteer Troubleshooting - Running in Docker](https://pptr.dev/troubleshooting#running-puppeteer-in-docker)
- [Browsershot Documentation - noSandbox()](https://spatie.be/docs/browsershot/v4/usage/creating-pdfs)

---

## Configuração de Paths do Node.js

**Problema:**
Por padrão, o Browsershot tenta detectar automaticamente os binários do Node.js, mas em ambientes Docker pode falhar.

**Solução aplicada:**
```php
Browsershot::html($html)
    ->setNodeBinary('/usr/bin/node') // Path explícito do Node.js
    ->setNpmBinary('/usr/bin/npm')   // Path explícito do npm
```

**Como encontrar os paths corretos:**
```bash
./vendor/bin/sail exec laravel.test which node
# Output: /usr/bin/node

./vendor/bin/sail exec laravel.test which npm
# Output: /usr/bin/npm
```

**Verificar versões instaladas:**
```bash
./vendor/bin/sail exec laravel.test node --version
./vendor/bin/sail exec laravel.test npm --version
```

---

## Checklist de Verificação

Para verificar se a configuração está correta:

### 1. Puppeteer instalado
```bash
./vendor/bin/sail exec laravel.test npm list puppeteer
# Deve mostrar versão instalada
```

### 2. Chrome headless shell instalado
```bash
./vendor/bin/sail exec laravel.test ls -la /home/sail/.cache/puppeteer/chrome-headless-shell/
# Deve listar diretório com versão do Chrome
```

### 3. Bibliotecas de sistema instaladas
```bash
./vendor/bin/sail exec laravel.test dpkg -l | grep libnspr4
./vendor/bin/sail exec laravel.test dpkg -l | grep libnss3
# Ambos devem retornar pacotes instalados
```

### 4. Paths do Node.js corretos
```bash
./vendor/bin/sail exec laravel.test which node
./vendor/bin/sail exec laravel.test which npm
```

### 5. Teste de geração de PDF
```bash
# Usando a rota de teste temporária
curl "http://localhost:8000/test-pdf?codpes=13687352&codcrl=450620000261" -o test.pdf
file test.pdf
# Deve retornar: "test.pdf: PDF document, version 1.4"
```

---

## Dockerfile Completo Recomendado

Seção a ser adicionada ao Dockerfile do Laravel Sail:

```dockerfile
# ============================================
# Browsershot/Puppeteer Configuration
# ============================================

# Instalar dependências do Chrome/Chromium
RUN apt-get update && apt-get install -y \
    # Core Chrome dependencies
    libnss3 \
    libnspr4 \
    # X11 and rendering libraries
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxtst6 \
    libxshmfence1 \
    # Audio library (Ubuntu 24.04 time64 version)
    libasound2t64 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Configurar variável de ambiente do Puppeteer
ENV PUPPETEER_CACHE_DIR=/home/sail/.cache/puppeteer

# Criar diretório de cache com permissões corretas
RUN mkdir -p /home/sail/.cache/puppeteer && \
    chown -R sail:sail /home/sail/.cache

# Instalar Puppeteer globalmente
RUN npm install -g puppeteer

# Instalar Chrome Headless Shell
RUN npx puppeteer browsers install chrome-headless-shell

# Garantir permissões corretas no cache do Puppeteer
RUN chown -R sail:sail /home/sail/.cache/puppeteer

# Verificar instalação
RUN npx puppeteer browsers list
```

---

## Variáveis de Ambiente Recomendadas

Adicionar ao `.env` (opcional, para customização):

```env
# Browsershot/Puppeteer Configuration
PUPPETEER_CACHE_DIR=/home/sail/.cache/puppeteer
PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=false
NODE_BINARY_PATH=/usr/bin/node
NPM_BINARY_PATH=/usr/bin/npm
```

---

## Otimizações de Performance

### 1. Reutilizar instância do Chrome
Para geração de múltiplos PDFs, considerar usar modo "keep alive" do Browsershot:

```php
// Em vez de criar nova instância para cada PDF
Browsershot::html($html)
    ->setOption('browserWSEndpoint', 'ws://localhost:3000') // Chrome rodando em modo daemon
    ->pdf();
```

### 2. Timeout apropriado
Para PDFs complexos com muitas páginas:

```php
Browsershot::html($html)
    ->timeout(120) // 120 segundos para PDFs grandes
    ->pdf();
```

### 3. Qualidade do PDF
Ajustar qualidade para balancear tamanho de arquivo vs. qualidade:

```php
Browsershot::html($html)
    ->scale(0.8) // Reduz tamanho do arquivo em ~40%
    ->pdf();
```

---

## Troubleshooting

### PDF em branco ou vazio

**Causa possível:** Template Blade com erros ou dados vazios

**Debug:**
```php
// Renderizar apenas HTML sem gerar PDF
$html = View::make('pdf.evolucao-padrao', [
    'dados' => $evolucaoDTO,
    'colorido' => true
])->render();

// Salvar HTML para inspecionar
file_put_contents(storage_path('app/debug.html'), $html);
```

### Erro "Protocol error"

**Causa possível:** Timeout ou página muito complexa

**Solução:**
```php
Browsershot::html($html)
    ->timeout(300) // Aumentar timeout
    ->waitUntilNetworkIdle() // Aguardar recursos carregarem
    ->pdf();
```

### Fontes não aparecendo no PDF

**Solução:** Usar fontes web-safe ou incluir @font-face no CSS:

```css
@font-face {
    font-family: 'CustomFont';
    src: url('data:font/woff2;base64,...');
}
```

### Imagens não aparecem no PDF

**Causa:** Paths relativos não funcionam em Browsershot

**Solução:** Usar URLs absolutas ou data URIs:

```html
<!-- Não funciona -->
<img src="/images/logo.png">

<!-- Funciona -->
<img src="{{ asset('images/logo.png') }}">
<img src="data:image/png;base64,...">
```

---

## Logs Úteis para Debug

### Ativar logs do Puppeteer
```php
Browsershot::html($html)
    ->setOption('dumpio', true) // Mostra logs do Chrome no stderr
    ->pdf();
```

### Verificar comando executado
O Browsershot executa um comando Node.js internamente. Para ver o comando:

```php
try {
    $pdf = Browsershot::html($html)->pdf();
} catch (\Exception $e) {
    // A exceção contém o comando executado
    Log::error('Browsershot error', [
        'message' => $e->getMessage(),
        'trace' => $e->getTraceAsString()
    ]);
}
```

---

## Recursos Adicionais

**Documentação Oficial:**
- [Spatie Browsershot](https://spatie.be/docs/browsershot)
- [Puppeteer Documentation](https://pptr.dev/)
- [Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/)

**Troubleshooting:**
- [Puppeteer Troubleshooting](https://pptr.dev/troubleshooting)
- [Running Puppeteer in Docker](https://github.com/puppeteer/puppeteer/blob/main/docs/troubleshooting.md#running-puppeteer-in-docker)

**Comunidade:**
- [Browsershot GitHub Issues](https://github.com/spatie/browsershot/issues)
- [Puppeteer GitHub Issues](https://github.com/puppeteer/puppeteer/issues)

---

## Próximas Ações

- [ ] Incorporar configurações ao Dockerfile do Laravel Sail
- [ ] Testar build da imagem Docker com todas as dependências
- [ ] Documentar no README.md do projeto
- [ ] Criar script de verificação de ambiente (`php artisan check:browsershot`)
- [ ] Adicionar testes automatizados de geração de PDF
- [ ] Considerar cache de PDFs gerados para performance

---

**Documento mantido por:** Equipe de Desenvolvimento Nova Europa
**Última atualização:** 2025-10-08
**Versão:** 1.0
