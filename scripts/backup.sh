#!/usr/bin/env bash

# =============================================================================
# Nova Europa - Database Backup Script
# =============================================================================
# This script creates backups of the MySQL database and Docker volumes
# Can be run manually or via cron
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
BACKUP_BASE_DIR="${BACKUP_PATH:-/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

# Generate timestamp
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="${BACKUP_BASE_DIR}/backup-${TIMESTAMP}"

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

    # Check if containers are running
    if ! docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps | grep -q "Up"; then
        log_error "Docker containers are not running"
        exit 1
    fi

    # Create backup directory
    mkdir -p "$BACKUP_DIR"

    log_info "Prerequisites met. Backup directory: $BACKUP_DIR"
}

backup_database() {
    log_step "Backing up MySQL database..."

    # Get database credentials from .env
    DB_ROOT_PASSWORD=$(grep DB_ROOT_PASSWORD "$ENV_FILE" | cut -d '=' -f2 | tr -d '"')

    if [ -z "$DB_ROOT_PASSWORD" ]; then
        log_error "DB_ROOT_PASSWORD not found in $ENV_FILE"
        exit 1
    fi

    MYSQL_BACKUP_FILE="${BACKUP_DIR}/mysql-database.sql"

    # Dump database
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T mysql \
        mysqldump -u root -p"${DB_ROOT_PASSWORD}" \
        --all-databases \
        --single-transaction \
        --quick \
        --lock-tables=false \
        --routines \
        --triggers \
        --events \
        > "$MYSQL_BACKUP_FILE"

    if [ $? -eq 0 ]; then
        log_info "Database dumped to: $MYSQL_BACKUP_FILE"

        # Compress backup
        gzip "$MYSQL_BACKUP_FILE"
        log_info "Database backup compressed: ${MYSQL_BACKUP_FILE}.gz"
    else
        log_error "Database backup failed!"
        exit 1
    fi
}

backup_storage() {
    log_step "Backing up storage volume..."

    STORAGE_BACKUP_FILE="${BACKUP_DIR}/storage-volume.tar.gz"

    # Backup storage volume
    docker run --rm \
        -v nova-europa-storage:/source:ro \
        -v "$BACKUP_DIR":/backup \
        ubuntu:24.04 \
        tar czf /backup/storage-volume.tar.gz -C /source .

    if [ $? -eq 0 ]; then
        log_info "Storage volume backed up: $STORAGE_BACKUP_FILE"
    else
        log_error "Storage volume backup failed!"
        exit 1
    fi
}

backup_env_file() {
    log_step "Backing up environment configuration..."

    cp "$ENV_FILE" "${BACKUP_DIR}/.env.production.backup"

    if [ $? -eq 0 ]; then
        log_info "Environment file backed up"
    else
        log_warn "Failed to backup environment file"
    fi
}

create_backup_manifest() {
    log_step "Creating backup manifest..."

    MANIFEST_FILE="${BACKUP_DIR}/MANIFEST.txt"

    cat > "$MANIFEST_FILE" <<EOF
Nova Europa - Backup Manifest
==============================

Backup Date: $(date)
Backup Directory: $BACKUP_DIR

Contents:
---------
- mysql-database.sql.gz: Full MySQL database dump
- storage-volume.tar.gz: Laravel storage volume
- .env.production.backup: Environment configuration

Docker Images:
--------------
$(docker images nova-europa --format "{{.Repository}}:{{.Tag}} ({{.Size}})")

Disk Usage:
-----------
$(du -sh "$BACKUP_DIR")

Restore Instructions:
---------------------
1. Stop running containers:
   docker-compose -f docker-compose.prod.yml down

2. Restore database:
   gunzip -c mysql-database.sql.gz | docker-compose exec -T mysql mysql -u root -p

3. Restore storage volume:
   docker run --rm -v nova-europa-storage:/target -v $BACKUP_DIR:/backup ubuntu:24.04 tar xzf /backup/storage-volume.tar.gz -C /target

4. Restore environment:
   cp .env.production.backup /path/to/nova_europa/.env.production

5. Restart containers:
   docker-compose -f docker-compose.prod.yml up -d

EOF

    log_info "Backup manifest created: $MANIFEST_FILE"
}

cleanup_old_backups() {
    log_step "Cleaning up old backups (retention: $RETENTION_DAYS days)..."

    # Find and remove backups older than retention period
    find "$BACKUP_BASE_DIR" -maxdepth 1 -type d -name "backup-*" -mtime +$RETENTION_DAYS -exec rm -rf {} \;

    REMAINING_BACKUPS=$(find "$BACKUP_BASE_DIR" -maxdepth 1 -type d -name "backup-*" | wc -l)
    log_info "Remaining backups: $REMAINING_BACKUPS"
}

verify_backup() {
    log_step "Verifying backup integrity..."

    # Check if all files exist
    local all_files_exist=true

    if [ ! -f "${BACKUP_DIR}/mysql-database.sql.gz" ]; then
        log_error "Missing: mysql-database.sql.gz"
        all_files_exist=false
    fi

    if [ ! -f "${BACKUP_DIR}/storage-volume.tar.gz" ]; then
        log_error "Missing: storage-volume.tar.gz"
        all_files_exist=false
    fi

    if [ ! -f "${BACKUP_DIR}/.env.production.backup" ]; then
        log_warn "Missing: .env.production.backup"
    fi

    if [ "$all_files_exist" = true ]; then
        # Test gzip integrity
        gzip -t "${BACKUP_DIR}/mysql-database.sql.gz" && \
        tar -tzf "${BACKUP_DIR}/storage-volume.tar.gz" > /dev/null

        if [ $? -eq 0 ]; then
            log_info "Backup integrity verified successfully"
            return 0
        else
            log_error "Backup files are corrupted!"
            return 1
        fi
    else
        log_error "Backup verification failed - missing files"
        return 1
    fi
}

main() {
    log_step "======================================================================="
    log_step "Nova Europa - Database Backup"
    log_step "======================================================================="

    check_prerequisites
    backup_database
    backup_storage
    backup_env_file
    create_backup_manifest

    if verify_backup; then
        cleanup_old_backups

        # Calculate backup size
        BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)

        log_step "======================================================================="
        log_step "Backup completed successfully!"
        log_step "======================================================================="
        log_info "Backup location: $BACKUP_DIR"
        log_info "Backup size: $BACKUP_SIZE"
        log_info "Retention policy: $RETENTION_DAYS days"
        log_info ""
        log_info "To restore this backup, see: ${BACKUP_DIR}/MANIFEST.txt"
    else
        log_error "Backup verification failed!"
        exit 1
    fi
}

# Run main function
main "$@"
