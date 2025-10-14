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

# Wait for database
echo "⏳ Waiting for database..."
until php artisan db:show > /dev/null 2>&1; do
    sleep 2
done

echo "✅ Database is ready!"

# Ensure storage directories exist with correct permissions
echo "📁 Setting up storage directories..."
mkdir -p storage/framework/{cache,sessions,views}
mkdir -p storage/logs
mkdir -p bootstrap/cache

chown -R www-data:www-data storage bootstrap/cache
chmod -R 775 storage bootstrap/cache

# Run migrations if needed
echo "🔧 Running migrations..."
php artisan migrate --force --no-interaction || echo "⚠️  Migrations failed or not needed"

# Cache routes and views (production optimization)
# NOTE: config:cache is NOT used because uspdev/replicado reads env() directly
# and env() returns null when config is cached
echo "⚡ Optimizing application..."
php artisan route:cache
php artisan view:cache

echo "✨ Container ready! Starting services..."

# Start supervisor based on container role
if [ "$CONTAINER_ROLE" = "worker" ]; then
  echo "Starting worker supervisor..."
  exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.worker.conf
else
  echo "Starting app supervisor..."
  exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
fi
