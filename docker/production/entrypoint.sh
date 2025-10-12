#!/bin/bash
set -e

echo "🚀 Starting Nova Europa container..."

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

# Clear and cache configuration (production optimization)
echo "⚡ Optimizing application..."
php artisan config:cache
php artisan route:cache
php artisan view:cache

echo "✨ Container ready! Starting services..."

# Start supervisor (Nginx + PHP-FPM)
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
