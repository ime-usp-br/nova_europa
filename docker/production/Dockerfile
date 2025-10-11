# =============================================================================
# STAGE 1: Build Assets and Dependencies
# =============================================================================
FROM ubuntu:24.04 AS builder

ARG NODE_VERSION=22

WORKDIR /build

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install build dependencies
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && apt-get update \
    && apt-get install -y \
        curl \
        ca-certificates \
        gnupg \
        git \
        unzip \
        zip \
    && rm -rf /var/lib/apt/lists/*

# Install PHP 8.2 and required extensions (including sybase for pdo_dblib)
RUN curl -sS 'https://keyserver.ubuntu.com/pks/lookup?op=get&search=0xb8dc7e53946656efbce4c1dd71daeaab4ad4cab6' | gpg --dearmor | tee /etc/apt/keyrings/ppa_ondrej_php.gpg > /dev/null \
    && echo "deb [signed-by=/etc/apt/keyrings/ppa_ondrej_php.gpg] https://ppa.launchpadcontent.net/ondrej/php/ubuntu noble main" > /etc/apt/sources.list.d/ppa_ondrej_php.list \
    && apt-get update \
    && apt-get install -y \
        php8.2-cli \
        php8.2-fpm \
        php8.2-mysql \
        php8.2-xml \
        php8.2-mbstring \
        php8.2-curl \
        php8.2-zip \
        php8.2-bcmath \
        php8.2-intl \
        php8.2-gd \
        php8.2-sybase \
    && rm -rf /var/lib/apt/lists/*

# Install Composer
RUN curl -sLS https://getcomposer.org/installer | php -- --install-dir=/usr/bin/ --filename=composer

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_VERSION.x nodistro main" > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y nodejs \
    && npm install -g npm \
    && rm -rf /var/lib/apt/lists/*

# Copy application files
COPY composer.json composer.lock ./
COPY package.json package-lock.json ./

# Install PHP dependencies (production only, optimized)
RUN composer install \
    --no-dev \
    --no-interaction \
    --no-progress \
    --no-scripts \
    --prefer-dist \
    --optimize-autoloader

# Install Node dependencies
RUN npm ci --production=false

# Copy application source
COPY . .

# Build frontend assets
RUN npm run build

# Generate optimized autoloader
RUN composer dump-autoload --optimize --no-dev

# =============================================================================
# STAGE 2: Production Runtime
# =============================================================================
FROM ubuntu:24.04

LABEL maintainer="IME-USP Development Team"
LABEL description="Nova Europa - Production Docker Image"

ARG WWWGROUP=1000
ARG WWWUSER=1000
ARG NODE_VERSION=22
ARG POSTGRES_VERSION=17

WORKDIR /var/www/html

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Sao_Paulo
ENV ACCEPT_EULA=Y

# Set PHP-FPM as the supervisor command
ENV SUPERVISOR_PHP_COMMAND="/usr/sbin/php-fpm8.2 -F -R"
ENV SUPERVISOR_PHP_USER="www-data"

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Configure APT for better reliability
RUN echo "Acquire::http::Pipeline-Depth 0;" > /etc/apt/apt.conf.d/99custom && \
    echo "Acquire::http::No-Cache true;" >> /etc/apt/apt.conf.d/99custom && \
    echo "Acquire::BrokenProxy    true;" >> /etc/apt/apt.conf.d/99custom

# Install runtime dependencies
RUN apt-get update && apt-get upgrade -y \
    && mkdir -p /etc/apt/keyrings \
    && apt-get install -y \
        gnupg \
        gosu \
        curl \
        ca-certificates \
        zip \
        unzip \
        git \
        supervisor \
        sqlite3 \
        libcap2-bin \
        libpng-dev \
        dnsutils \
        librsvg2-bin \
        nano \
        # FreeTDS and ODBC dependencies for SQL Server
        unixodbc-dev \
        freetds-bin \
        freetds-common \
        freetds-dev \
    # Add PHP repository
    && curl -sS 'https://keyserver.ubuntu.com/pks/lookup?op=get&search=0xb8dc7e53946656efbce4c1dd71daeaab4ad4cab6' | gpg --dearmor | tee /etc/apt/keyrings/ppa_ondrej_php.gpg > /dev/null \
    && echo "deb [signed-by=/etc/apt/keyrings/ppa_ondrej_php.gpg] https://ppa.launchpadcontent.net/ondrej/php/ubuntu noble main" > /etc/apt/sources.list.d/ppa_ondrej_php.list \
    # Add Microsoft ODBC repository
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /etc/apt/keyrings/microsoft.gpg \
    && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/ubuntu/24.04/prod noble main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    # Install Microsoft ODBC Driver
    && apt-get install -y msodbcsql18 \
    # Install PHP 8.2 FPM and extensions
    && apt-get install -y \
        php8.2-fpm \
        php8.2-cli \
        php8.2-dev \
        php8.2-mysql \
        php8.2-pgsql \
        php8.2-sqlite3 \
        php8.2-gd \
        php8.2-curl \
        php8.2-imap \
        php8.2-mbstring \
        php8.2-xml \
        php8.2-zip \
        php8.2-bcmath \
        php8.2-soap \
        php8.2-intl \
        php8.2-readline \
        php8.2-ldap \
        php8.2-redis \
        php8.2-sybase \
        php8.2-opcache \
    # Install SQL Server PDO extension
    && pecl install pdo_sqlsrv \
    && echo "extension=pdo_sqlsrv.so" > /etc/php/8.2/fpm/conf.d/20-pdo_sqlsrv.ini \
    && echo "extension=pdo_sqlsrv.so" > /etc/php/8.2/cli/conf.d/20-pdo_sqlsrv.ini \
    # Install Composer
    && curl -sLS https://getcomposer.org/installer | php -- --install-dir=/usr/bin/ --filename=composer \
    # Install Node.js
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_VERSION.x nodistro main" > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y nodejs \
    && npm install -g npm \
    # Install database clients
    && apt-get install -y mysql-client \
    && curl -sS https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor | tee /etc/apt/keyrings/pgdg.gpg >/dev/null \
    && echo "deb [signed-by=/etc/apt/keyrings/pgdg.gpg] http://apt.postgresql.org/pub/repos/apt noble-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update \
    && apt-get install -y postgresql-client-$POSTGRES_VERSION \
    # Install Browsershot/Puppeteer dependencies (Chrome Headless)
    && apt-get install -y \
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
    # Clean up
    && apt-get -y autoremove \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Configure FreeTDS for legacy TLS support
RUN mkdir -p /etc/gnutls \
    && echo 'LEGACY' > /etc/gnutls/config.tds

# Set PHP-FPM to bind to port 9000 (no special capabilities needed)
# Configure PHP-FPM
RUN sed -i 's/^listen = .*/listen = 9000/' /etc/php/8.2/fpm/pool.d/www.conf \
    && sed -i 's/^;listen.allowed_clients/listen.allowed_clients/' /etc/php/8.2/fpm/pool.d/www.conf \
    && sed -i 's/^user = .*/user = www-data/' /etc/php/8.2/fpm/pool.d/www.conf \
    && sed -i 's/^group = .*/group = www-data/' /etc/php/8.2/fpm/pool.d/www.conf \
    # Fix PHP-FPM global error_log path
    && sed -i 's|^error_log = .*|error_log = /var/www/html/storage/logs/php8.2-fpm.log|' /etc/php/8.2/fpm/php-fpm.conf

# Create www-data user with proper UID/GID
# Check if GID/UID already exists and handle accordingly
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

# Configure Puppeteer cache directory
ENV PUPPETEER_CACHE_DIR=/var/www/.cache/puppeteer

RUN mkdir -p /var/www/.cache/puppeteer \
    && chown -R www-data:www-data /var/www/.cache

# Install Puppeteer globally
RUN npm install -g puppeteer

# Copy application from builder stage
COPY --from=builder --chown=www-data:www-data /build /var/www/html

# Install the project-specific Chrome Headless Shell version
# This MUST come AFTER copying files, to use the project's puppeteer version
RUN gosu www-data npx puppeteer browsers install chrome-headless-shell


# Copy configuration files
COPY --chown=www-data:www-data docker/production/php.ini /etc/php/8.2/fpm/conf.d/99-production.ini
COPY --chown=www-data:www-data docker/production/php.ini /etc/php/8.2/cli/conf.d/99-production.ini
COPY --chown=www-data:www-data docker/production/php-fpm.conf /etc/php/8.2/fpm/pool.d/www.conf
COPY docker/production/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY docker/production/freetds.conf.template /etc/freetds/freetds.conf.template
COPY docker/production/start-container /usr/local/bin/start-container
COPY docker/production/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

RUN chmod +x /usr/local/bin/start-container \
    && chmod +x /usr/local/bin/docker-entrypoint.sh

# Create required directories with proper permissions
RUN mkdir -p \
        storage/framework/cache \
        storage/framework/sessions \
        storage/framework/views \
        storage/logs \
        bootstrap/cache \
    && chown -R www-data:www-data storage bootstrap/cache \
    && chmod -R 775 storage bootstrap/cache

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD php artisan inspire > /dev/null 2>&1 || exit 1

EXPOSE 9000

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["start-container"]
