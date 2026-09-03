#!/bin/bash
set -e

echo "🚀 Starting Nova Europa container..."

# Configure FreeTDS from template and environment variables
echo "🔧 Configuring FreeTDS for Replicado..."
REPLICADO_HOST_VAL=${REPLICADO_HOST:-localhost}
REPLICADO_PORT_VAL=${REPLICADO_PORT:-1433}

sed -e "s/__REPLICADO_HOST__/$REPLICADO_HOST_VAL/g" \
    -e "s/__REPLICADO_PORT__/$REPLICADO_PORT_VAL/g" \
    /etc/freetds/freetds.conf.template > /etc/freetds/freetds.conf

echo "✅ FreeTDS configured: $REPLICADO_HOST_VAL:$REPLICADO_PORT_VAL"

# Ensure storage directories exist with correct permissions
# (precisa ser ANTES de qualquer artisan: o bind-mount de ./storage pode
# sombrear os diretórios da imagem e o Laravel aborta sem eles)
echo "📁 Setting up storage directories..."
mkdir -p storage/framework/{cache,sessions,views}
mkdir -p storage/logs
mkdir -p storage/app/private
mkdir -p storage/app/public
mkdir -p bootstrap/cache

chown -R www-data:www-data storage bootstrap/cache
chmod -R 775 storage bootstrap/cache

# Generate APP_KEY automatically if missing/invalid (persisted in storage/app)
KEY_FILE=/var/www/html/storage/app/app_key
if [ -z "$APP_KEY" ] || ! printf '%s' "$APP_KEY" | grep -q '^base64:'; then
    echo "🔑 APP_KEY ausente, gerando..."
    if [ "$CONTAINER_ROLE" = "worker" ]; then
        # o container app gera e persiste; aguarda a mesma chave aparecer
        for i in $(seq 1 30); do
            [ -f "$KEY_FILE" ] && break
            sleep 2
        done
    fi
    if [ -f "$KEY_FILE" ]; then
        APP_KEY=$(cat "$KEY_FILE")
    else
        APP_KEY=$(php artisan key:generate --show --force)
        mkdir -p storage/app
        echo "$APP_KEY" > "$KEY_FILE"
        chown -R www-data:www-data storage/app
        chmod 600 "$KEY_FILE"
    fi
    export APP_KEY
    echo "✅ APP_KEY definida e persistida em $KEY_FILE"
fi

# Wait for database
echo "⏳ Waiting for database..."
until php artisan db:show > /dev/null 2>&1; do
    sleep 2
done

echo "✅ Database is ready!"

# Install dependencies if missing (development bind-mount)
if [ ! -d vendor ]; then
    echo "📦 Installing Composer dependencies..."
    composer install --no-interaction --no-progress --prefer-dist
fi

# Run migrations if needed (idempotente)
echo "🔧 Running migrations..."
php artisan migrate --force --no-interaction || echo "⚠️  Migrations failed or not needed"

# Run seeders (idempotentes), somente no container app para evitar corrida
if [ "$CONTAINER_ROLE" = "app" ]; then
    echo "🌱 Running seeders..."
    php artisan db:seed --force --no-interaction || echo "⚠️  Seeding failed"
fi

# Cache routes and views (production optimization only)
# NOTE: config:cache is NOT used because uspdev/replicado reads env() directly
# and env() returns null when config is cached
if [ "$APP_ENV" = "production" ]; then
    echo "⚡ Optimizing application..."
    php artisan route:cache
    php artisan view:cache
else
    echo "⚡ Skipping route/view cache (APP_ENV=$APP_ENV)"
fi

echo "✨ Container ready! Starting services..."

# Start supervisor based on container role
if [ "$CONTAINER_ROLE" = "worker" ]; then
  echo "Starting worker supervisor..."
  exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.worker.conf
else
  echo "Starting app supervisor..."
  exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
fi
