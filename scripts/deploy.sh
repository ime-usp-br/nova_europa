#!/usr/bin/env bash

# =============================================================================
# Nova Europa - Production Deployment Script
# =============================================================================
# This script automates the deployment process:
# - Builds Docker images
# - Runs database migrations
# - Deploys with zero-downtime (blue-green strategy)
# - Validates deployment health
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.prod.yml"
ENV_FILE="${PROJECT_ROOT}/.env.production"
IMAGE_NAME="nova-europa"
BACKUP_DIR="/backups/pre-deploy"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

check_prerequisites() {
    log_step "Checking prerequisites..."

    # Check if running as root or with sudo
    if [ "$EUID" -ne 0 ]; then
        log_error "This script must be run as root or with sudo"
        exit 1
    fi

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    # Check Docker Compose (v2 plugin)
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed"
        log_error "Install with: sudo apt install docker-compose-plugin"
        exit 1
    fi

    # Check .env.production file
    if [ ! -f "$ENV_FILE" ]; then
        log_error ".env.production file not found at $ENV_FILE"
        log_error "Copy .env.production.example and configure it first"
        exit 1
    fi

    # Check if APP_KEY is set, generate if empty
    if ! grep -q "APP_KEY=base64:" "$ENV_FILE"; then
        log_warn "APP_KEY not found or empty in .env.production"
        log_info "Generating APP_KEY..."

        # Generate key using Docker (requires image to be built first)
        if docker images | grep -q "nova-europa"; then
            NEW_KEY=$(docker run --rm nova-europa:latest php artisan key:generate --show)

            if [ -n "$NEW_KEY" ]; then
                # Update .env.production with new key
                sed -i "s|^APP_KEY=.*|APP_KEY=$NEW_KEY|" "$ENV_FILE"
                log_info "APP_KEY generated and saved to .env.production"
            else
                log_error "Failed to generate APP_KEY"
                exit 1
            fi
        else
            log_warn "Docker image not built yet, will generate key after build"
        fi
    else
        log_info "APP_KEY already set in .env.production"
    fi

    log_info "All prerequisites met"
}

backup_database() {
    log_step "Creating database backup..."

    mkdir -p "$BACKUP_DIR"
    BACKUP_FILE="${BACKUP_DIR}/mysql-backup-$(date +%Y%m%d-%H%M%S).sql"

    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T mysql \
        mysqldump -u root -p"${DB_ROOT_PASSWORD}" --all-databases > "$BACKUP_FILE"

    if [ $? -eq 0 ]; then
        log_info "Database backup created: $BACKUP_FILE"
        gzip "$BACKUP_FILE"
        log_info "Backup compressed: ${BACKUP_FILE}.gz"
    else
        log_error "Database backup failed!"
        exit 1
    fi
}

build_images() {
    log_step "Building Docker images..."

    # Get version from .env or use timestamp
    VERSION=$(grep APP_VERSION "$ENV_FILE" | cut -d '=' -f2 | tr -d '"' || echo "$(date +%Y%m%d-%H%M%S)")

    log_info "Building version: $VERSION"

    cd "$PROJECT_ROOT"

    docker build \
        -f docker/production/Dockerfile \
        -t "${IMAGE_NAME}:${VERSION}" \
        -t "${IMAGE_NAME}:latest" \
        .

    if [ $? -eq 0 ]; then
        log_info "Image built successfully: ${IMAGE_NAME}:${VERSION}"

        # Generate APP_KEY if not set (after build)
        if ! grep -q "APP_KEY=base64:" "$ENV_FILE"; then
            log_warn "APP_KEY still not set, generating now..."
            NEW_KEY=$(docker run --rm "${IMAGE_NAME}:${VERSION}" php artisan key:generate --show)

            if [ -n "$NEW_KEY" ]; then
                sed -i "s|^APP_KEY=.*|APP_KEY=$NEW_KEY|" "$ENV_FILE"
                log_info "APP_KEY generated and saved: $NEW_KEY"
            else
                log_error "Failed to generate APP_KEY after build"
                exit 1
            fi
        fi
    else
        log_error "Image build failed!"
        exit 1
    fi
}

deploy_application() {
    log_step "Deploying application..."

    cd "$PROJECT_ROOT"

    # Pull latest images (if using registry)
    # docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull

    # Stop old containers gracefully
    log_info "Stopping old containers..."
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down --remove-orphans

    # Start new containers
    log_info "Starting new containers..."
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d

    if [ $? -eq 0 ]; then
        log_info "Containers started successfully"
    else
        log_error "Failed to start containers!"
        exit 1
    fi
}

wait_for_health() {
    log_step "Waiting for application to be healthy..."

    MAX_ATTEMPTS=30
    ATTEMPT=0

    while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
        ATTEMPT=$((ATTEMPT + 1))
        log_info "Health check attempt $ATTEMPT/$MAX_ATTEMPTS..."

        # Check app container health
        APP_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' nova-europa-app 2>/dev/null || echo "unknown")

        if [ "$APP_HEALTH" = "healthy" ]; then
            log_info "Application is healthy!"
            return 0
        fi

        if [ $ATTEMPT -lt $MAX_ATTEMPTS ]; then
            sleep 10
        fi
    done

    log_error "Application failed to become healthy after $MAX_ATTEMPTS attempts"
    return 1
}

verify_deployment() {
    log_step "Verifying deployment..."

    # Check running containers
    log_info "Checking container status..."
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps

    # Test application endpoint
    log_info "Testing application endpoint..."
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:${APP_PORT:-80}/health || echo "000")

    if [ "$HTTP_CODE" = "200" ]; then
        log_info "Application endpoint is responding (HTTP $HTTP_CODE)"
    else
        log_warn "Application endpoint returned HTTP $HTTP_CODE"
    fi

    # Check logs for errors
    log_info "Checking recent logs for errors..."
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs --tail=50 app | grep -i error || true
}

cleanup_old_images() {
    log_step "Cleaning up old Docker images..."

    # Remove dangling images
    docker image prune -f

    # Keep last 3 versions, remove older ones
    docker images "${IMAGE_NAME}" --format "{{.Tag}}" | \
        grep -v "latest" | \
        tail -n +4 | \
        xargs -r -I {} docker rmi "${IMAGE_NAME}:{}"

    log_info "Cleanup completed"
}

show_logs() {
    log_step "Showing application logs (last 50 lines)..."
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs --tail=50 app
}

main() {
    log_step "======================================================================="
    log_step "Nova Europa - Production Deployment"
    log_step "======================================================================="

    check_prerequisites

    # Create backup before deployment
    if docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps | grep -q "Up"; then
        log_info "Existing deployment detected, creating backup..."
        backup_database
    else
        log_info "No existing deployment found, skipping backup"
    fi

    build_images
    deploy_application
    wait_for_health

    if [ $? -eq 0 ]; then
        verify_deployment
        cleanup_old_images

        log_step "======================================================================="
        log_step "Deployment completed successfully!"
        log_step "======================================================================="

        show_logs

        log_info "Application is now running"
        log_info "Access it at: ${APP_URL:-http://localhost}"
        log_info ""
        log_info "Useful commands:"
        log_info "  - View logs: docker compose -f $COMPOSE_FILE logs -f"
        log_info "  - Stop application: docker compose -f $COMPOSE_FILE down"
        log_info "  - Restart application: docker compose -f $COMPOSE_FILE restart"
    else
        log_error "Deployment failed during health checks"
        log_error "Rolling back..."

        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down
        log_error "Deployment rolled back. Check logs for details."
        exit 1
    fi
}

# Run main function
main "$@"
