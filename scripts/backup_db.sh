#!/bin/bash
#
# Database Backup Script for guilde-lite-tdd-sprint
#
# This script creates PostgreSQL database backups with compression,
# supports both local and Docker deployments, and manages backup retention.
#
# Usage:
#   ./backup_db.sh                    # Create backup
#   ./backup_db.sh --restore <file>   # Restore from backup
#   ./backup_db.sh --list             # List available backups
#   ./backup_db.sh --help             # Show help
#
# Environment Variables:
#   BACKUP_DIR          - Directory to store backups (default: ./backups)
#   RETENTION_COUNT     - Number of backups to retain (default: 7)
#   POSTGRES_HOST       - Database host (default: localhost)
#   POSTGRES_PORT       - Database port (default: 5432)
#   POSTGRES_USER       - Database user (default: postgres)
#   POSTGRES_PASSWORD   - Database password (required)
#   POSTGRES_DB         - Database name (default: guilde_lite_tdd_sprint)
#   USE_DOCKER          - Use Docker container for backup (auto-detected)
#   DOCKER_CONTAINER    - Docker container name (default: guilde_lite_tdd_sprint_db)
#

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration with defaults
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_COUNT="${RETENTION_COUNT:-7}"
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-guilde_lite_tdd_sprint}"
DOCKER_CONTAINER="${DOCKER_CONTAINER:-guilde_lite_tdd_sprint_db}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILENAME="${POSTGRES_DB}_${TIMESTAMP}.sql.gz"

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Show help
show_help() {
    cat << EOF
Database Backup Script for guilde-lite-tdd-sprint

Usage:
  $(basename "$0") [OPTIONS]

Options:
  --restore <file>    Restore database from backup file
  --list              List available backups
  --help              Show this help message

Environment Variables:
  BACKUP_DIR          Directory to store backups (default: ./backups)
  RETENTION_COUNT     Number of backups to retain (default: 7)
  POSTGRES_HOST       Database host (default: localhost)
  POSTGRES_PORT       Database port (default: 5432)
  POSTGRES_USER       Database user (default: postgres)
  POSTGRES_PASSWORD   Database password (required for local mode)
  POSTGRES_DB         Database name (default: guilde_lite_tdd_sprint)
  USE_DOCKER          Force Docker mode (auto-detected if not set)
  DOCKER_CONTAINER    Docker container name (default: guilde_lite_tdd_sprint_db)

Examples:
  # Create a backup (auto-detects Docker vs local)
  ./backup_db.sh

  # Force local mode with custom settings
  POSTGRES_HOST=db.example.com POSTGRES_PASSWORD=secret ./backup_db.sh

  # Force Docker mode
  USE_DOCKER=true ./backup_db.sh

  # Restore from a backup
  ./backup_db.sh --restore ./backups/guilde_lite_tdd_sprint_20240115_120000.sql.gz

  # Keep last 14 backups
  RETENTION_COUNT=14 ./backup_db.sh
EOF
}

# Detect if we should use Docker
detect_docker() {
    if [[ -n "${USE_DOCKER:-}" ]]; then
        if [[ "$USE_DOCKER" == "true" ]]; then
            return 0
        else
            return 1
        fi
    fi

    # Check if Docker container is running
    if command -v docker &> /dev/null && docker ps --format '{{.Names}}' | grep -q "^${DOCKER_CONTAINER}$"; then
        return 0
    fi

    return 1
}

# Ensure backup directory exists
ensure_backup_dir() {
    if [[ ! -d "$BACKUP_DIR" ]]; then
        log_info "Creating backup directory: $BACKUP_DIR"
        mkdir -p "$BACKUP_DIR"
    fi
}

# Create backup using Docker
backup_docker() {
    log_info "Using Docker container: $DOCKER_CONTAINER"

    docker exec "$DOCKER_CONTAINER" \
        pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists \
        | gzip > "${BACKUP_DIR}/${BACKUP_FILENAME}"
}

# Create backup using local pg_dump
backup_local() {
    if [[ -z "${POSTGRES_PASSWORD:-}" ]]; then
        log_error "POSTGRES_PASSWORD environment variable is required for local backup"
        exit 1
    fi

    log_info "Using local pg_dump to connect to ${POSTGRES_HOST}:${POSTGRES_PORT}"

    PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
        -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        --clean \
        --if-exists \
        | gzip > "${BACKUP_DIR}/${BACKUP_FILENAME}"
}

# Clean up old backups
cleanup_old_backups() {
    log_info "Cleaning up old backups (keeping last $RETENTION_COUNT)"

    local backup_count
    backup_count=$(find "$BACKUP_DIR" -name "${POSTGRES_DB}_*.sql.gz" -type f | wc -l | tr -d ' ')

    if (( backup_count > RETENTION_COUNT )); then
        local to_delete=$((backup_count - RETENTION_COUNT))
        log_info "Removing $to_delete old backup(s)"

        # Find and delete oldest backups
        find "$BACKUP_DIR" -name "${POSTGRES_DB}_*.sql.gz" -type f -print0 \
            | xargs -0 ls -t \
            | tail -n "$to_delete" \
            | xargs rm -f
    else
        log_info "No old backups to remove ($backup_count backups exist)"
    fi
}

# Restore from backup
restore_backup() {
    local backup_file="$1"

    if [[ ! -f "$backup_file" ]]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi

    log_warn "This will OVERWRITE the existing database: $POSTGRES_DB"
    read -p "Are you sure you want to continue? (y/N) " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Restore cancelled"
        exit 0
    fi

    log_info "Restoring database from: $backup_file"

    if detect_docker; then
        log_info "Using Docker container: $DOCKER_CONTAINER"
        gunzip -c "$backup_file" | docker exec -i "$DOCKER_CONTAINER" \
            psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
    else
        if [[ -z "${POSTGRES_PASSWORD:-}" ]]; then
            log_error "POSTGRES_PASSWORD environment variable is required for local restore"
            exit 1
        fi

        log_info "Using local psql to connect to ${POSTGRES_HOST}:${POSTGRES_PORT}"
        gunzip -c "$backup_file" | PGPASSWORD="$POSTGRES_PASSWORD" psql \
            -h "$POSTGRES_HOST" \
            -p "$POSTGRES_PORT" \
            -U "$POSTGRES_USER" \
            -d "$POSTGRES_DB"
    fi

    log_info "Database restored successfully"
}

# List available backups
list_backups() {
    log_info "Available backups in $BACKUP_DIR:"
    echo ""

    if [[ ! -d "$BACKUP_DIR" ]]; then
        log_warn "Backup directory does not exist"
        return
    fi

    local backup_files
    backup_files=$(find "$BACKUP_DIR" -name "${POSTGRES_DB}_*.sql.gz" -type f 2>/dev/null | sort -r)

    if [[ -z "$backup_files" ]]; then
        log_warn "No backups found"
        return
    fi

    printf "%-50s %10s %s\n" "FILENAME" "SIZE" "DATE"
    printf "%-50s %10s %s\n" "--------" "----" "----"

    while IFS= read -r file; do
        local filename
        local size
        local date_modified

        filename=$(basename "$file")
        size=$(du -h "$file" | cut -f1)
        date_modified=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M" "$file" 2>/dev/null || stat -c "%y" "$file" 2>/dev/null | cut -d'.' -f1)

        printf "%-50s %10s %s\n" "$filename" "$size" "$date_modified"
    done <<< "$backup_files"
}

# Create backup
create_backup() {
    log_info "Starting database backup for: $POSTGRES_DB"

    ensure_backup_dir

    if detect_docker; then
        backup_docker
    else
        backup_local
    fi

    local backup_path="${BACKUP_DIR}/${BACKUP_FILENAME}"
    local backup_size
    backup_size=$(du -h "$backup_path" | cut -f1)

    log_info "Backup created successfully: $backup_path ($backup_size)"

    cleanup_old_backups

    log_info "Backup complete!"
}

# Main entry point
main() {
    case "${1:-}" in
        --help|-h)
            show_help
            exit 0
            ;;
        --restore|-r)
            if [[ -z "${2:-}" ]]; then
                log_error "Please specify a backup file to restore"
                echo "Usage: $(basename "$0") --restore <backup_file>"
                exit 1
            fi
            restore_backup "$2"
            ;;
        --list|-l)
            list_backups
            ;;
        "")
            create_backup
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
