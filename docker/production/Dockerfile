# =============================================================================
# Nova Europa - Imagem de produção (Nginx + PHP-FPM no mesmo container)
# =============================================================================
# Base pronta: php:8.2-fpm oficial + mlocati/docker-php-extension-installer
# (elimina os steps frágeis de PPA/ODBC/pecl manuais).
# Mantidos por necessidade da aplicação:
#   - pdo_sqlsrv + pdo_dblib (SQL Server "Replicado" USP via FreeTDS/ODBC)
#   - Node.js + Puppeteer/Chrome (geração de PDFs via Browsershot)
# =============================================================================

# =============================================================================
# STAGE 1: Build de assets e dependências
# =============================================================================
FROM php:8.2-cli AS builder

ARG NODE_VERSION=22

WORKDIR /build

ENV DEBIAN_FRONTEND=noninteractive
ENV PUPPETEER_SKIP_DOWNLOAD=true

# Node.js para compilar os assets do Vite, Composer e extensões PHP
# (as mesmas do runtime, para o composer validar a plataforma corretamente)
RUN mkdir -p /etc/apt/apt.conf.d /etc/apt/keyrings \
    && echo 'Acquire::Retries "10";' > /etc/apt/apt.conf.d/80-retries \
    && apt-get update -o Acquire::Retries=10 \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        gnupg \
        curl \
        git \
        zip \
        unzip \
        libicu-dev \
        libzip-dev \
        libpng-dev \
        libfreetype6-dev \
        libjpeg62-turbo-dev \
        unixodbc-dev \
        freetds-dev \
    && rm -rf /var/lib/apt/lists/* \
    && for i in 1 2 3; do \
        curl -fsSL -o /usr/local/bin/install-php-extensions \
            https://github.com/mlocati/docker-php-extension-installer/releases/latest/download/install-php-extensions \
        && break; \
        sleep 15; \
    done \
    && chmod +x /usr/local/bin/install-php-extensions \
    && install-php-extensions \
        pdo_mysql \
        intl \
        gd \
        zip \
        bcmath \
        redis \
        opcache \
        sqlsrv \
        pdo_sqlsrv \
    && docker-php-ext-install pdo_dblib \
    && php -r "copy('https://getcomposer.org/installer', '/tmp/composer-setup.php');" \
    && php /tmp/composer-setup.php --install-dir=/usr/local/bin --filename=composer --quiet \
    && rm -f /tmp/composer-setup.php \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_VERSION.x nodistro main" > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update -o Acquire::Retries=10 \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências PHP (sem scripts, código ainda não copiado)
COPY composer.json composer.lock ./
COPY package.json package-lock.json ./

RUN composer install \
        --no-dev \
        --no-interaction \
        --no-progress \
        --no-scripts \
        --prefer-dist \
        --optimize-autoloader

# Copia o código e compila os assets
COPY . .

RUN npm ci --production=false \
    && npm run build \
    && composer dump-autoload --optimize --no-dev

# =============================================================================
# STAGE 2: Runtime (Nginx + PHP-FPM no mesmo container)
# =============================================================================
FROM php:8.2-fpm

LABEL maintainer="IME-USP Development Team"
LABEL description="Nova Europa - Production Image (Nginx + PHP-FPM)"

ARG NODE_VERSION=22
ARG WWWGROUP=1000
ARG WWWUSER=1000

WORKDIR /var/www/html

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Sao_Paulo
ENV ACCEPT_EULA=Y
ENV PUPPETEER_CACHE_DIR=/var/www/.cache/puppeteer

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && echo 'Acquire::Retries "10";' > /etc/apt/apt.conf.d/80-retries

# Dependências de sistema
RUN apt-get update -o Acquire::Retries=10 && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        gnupg \
        zip \
        unzip \
        git \
        supervisor \
        nginx \
        sqlite3 \
        libpng-dev \
        nano \
        libicu-dev \
        libzip-dev \
        libfreetype6-dev \
        libjpeg62-turbo-dev \
        # FreeTDS para o SQL Server (Replicado USP)
        unixodbc-dev \
        freetds-bin \
        freetds-common \
        freetds-dev \
        # Dependências do Chrome (Browsershot/Puppeteer - PDFs)
        fonts-dejavu-core \
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
        libasound2 \
        libxtst6 \
        libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

# FreeTDS com TLS legado (Replicado)
RUN mkdir -p /etc/gnutls \
    && echo 'LEGACY' > /etc/gnutls/config.tds

# Extensões PHP via docker-php-extension-installer
# (inclusive pdo_sqlsrv, que resolve o driver ODBC da Microsoft sozinho)
RUN for i in 1 2 3; do \
        curl -fsSL -o /usr/local/bin/install-php-extensions \
            https://github.com/mlocati/docker-php-extension-installer/releases/latest/download/install-php-extensions \
        && break; \
        sleep 15; \
    done \
    && chmod +x /usr/local/bin/install-php-extensions \
    && install-php-extensions \
        pdo_mysql \
        intl \
        gd \
        zip \
        bcmath \
        redis \
        opcache \
        sqlsrv \
        pdo_sqlsrv \
    && docker-php-ext-install pdo_dblib

# Node.js (Puppeteer)
RUN curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_VERSION.x nodistro main" > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update -o Acquire::Retries=10 \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g npm \
    && rm -rf /var/lib/apt/lists/*

# Composer (usado pelo entrypoint quando vendor está ausente - dev)
RUN curl -sLS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer

# Ajusta UID/GID do www-data
RUN if getent group $WWWGROUP > /dev/null 2>&1; then \
        echo "Group $WWWGROUP already exists"; \
    else \
        groupmod -g $WWWGROUP www-data; \
    fi \
    && if getent passwd $WWWUSER > /dev/null 2>&1; then \
        echo "User $WWWUSER already exists"; \
    else \
        usermod -u $WWWUSER www-data; \
    fi \
    && usermod -g www-data www-data

# Copia a aplicação compilada
COPY --from=builder --chown=www-data:www-data /build /var/www/html

# Chrome (geração de PDFs) - instalado com o @puppeteer/browsers da aplicação,
# na versão exata que o puppeteer-core espera (Chrome 141.x), no cache
# PUPPETEER_CACHE_DIR=/var/www/.cache/puppeteer.
RUN mkdir -p /var/www/.cache/puppeteer \
    && node -e "const {install}=require('@puppeteer/browsers'); const cacheDir=process.env.PUPPETEER_CACHE_DIR||'/var/www/.cache/puppeteer'; const v='141.0.7390.76'; Promise.all([install({browser:'chrome',buildId:v,cacheDir}),install({browser:'chrome-headless-shell',buildId:v,cacheDir})]).catch(e=>{console.error(e);process.exit(1)})" \
    && chown -R www-data:www-data /var/www/.cache

# Configuração dos serviços
COPY docker/production/nginx.conf /etc/nginx/nginx.conf
COPY docker/production/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY docker/production/supervisord.worker.conf /etc/supervisor/conf.d/supervisord.worker.conf
COPY docker/production/php-fpm.conf /usr/local/etc/php-fpm.d/www.conf
COPY docker/production/php.ini /usr/local/etc/php/conf.d/99-production.ini
COPY docker/production/freetds.conf.template /etc/freetds/freetds.conf.template
COPY docker/production/entrypoint.sh /usr/local/bin/entrypoint.sh

RUN chmod +x /usr/local/bin/entrypoint.sh

# Diretórios do Laravel
RUN mkdir -p \
        storage/framework/cache \
        storage/framework/sessions \
        storage/framework/views \
        storage/logs \
        bootstrap/cache \
    && chown -R www-data:www-data storage bootstrap/cache \
    && chmod -R 775 storage bootstrap/cache

EXPOSE 80

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]