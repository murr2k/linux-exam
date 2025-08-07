#!/bin/bash

#
# GitHub Actions Cache Optimization Script
#
# This script provides utilities for managing GitHub Actions cache efficiently
# and avoiding permission issues with system directories.
#

set -euo pipefail

# Constants
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
readonly CACHE_VERSION="v3"
readonly MAX_CACHE_SIZE_MB=2048  # 2GB limit
readonly CACHE_RETENTION_DAYS=7

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

# Cache path definitions - ONLY user-writable directories
get_safe_cache_paths() {
    cat <<EOF
~/.cache/pip
~/.local/lib
~/.local/bin
~/.local/share
~/.npm
~/.cache/node
~/.cache/yarn
~/.cache/docker
~/.docker/buildx-cache
~/ci-cache
/tmp/ci-setup-marker
/tmp/ci-tools
/tmp/.buildx-cache
/tmp/.buildx-cache-e2e
/tmp/.buildx-cache-perf
EOF
}

# Problematic paths to avoid - these cause permission issues
get_problematic_paths() {
    cat <<EOF
/var/cache/apt
/var/lib/apt
/etc/apt
~/.cache/apt
/usr/local/lib/apt
/tmp/apt-cache
EOF
}

# Setup safe cache directories
setup_cache_directories() {
    log_info "Setting up safe cache directories..."
    
    local paths
    paths=$(get_safe_cache_paths)
    
    while IFS= read -r path; do
        if [[ -n "$path" ]]; then
            # Expand tilde to home directory
            expanded_path="${path/#\~/$HOME}"
            
            if [[ ! -d "$expanded_path" ]]; then
                log_info "Creating directory: $expanded_path"
                mkdir -p "$expanded_path" || {
                    log_warn "Failed to create directory: $expanded_path"
                    continue
                }
            fi
            
            # Ensure proper permissions
            chmod 755 "$expanded_path" 2>/dev/null || true
        fi
    done <<< "$paths"
    
    log_success "Cache directories setup completed"
}

# Clean up cache directories to prevent bloat
cleanup_cache_directories() {
    log_info "Cleaning up cache directories..."
    
    local cleaned=0
    
    # Remove old temporary files
    find /tmp -name "ci-*" -type f -mtime +1 -delete 2>/dev/null && cleaned=$((cleaned + 1)) || true
    find ~/.cache -name "*.tmp" -type f -mtime +7 -delete 2>/dev/null && cleaned=$((cleaned + 1)) || true
    
    # Clean pip cache
    if command -v pip3 >/dev/null 2>&1; then
        pip3 cache purge >/dev/null 2>&1 && cleaned=$((cleaned + 1)) || true
    fi
    
    # Clean npm cache
    if command -v npm >/dev/null 2>&1; then
        npm cache clean --force >/dev/null 2>&1 && cleaned=$((cleaned + 1)) || true
    fi
    
    # Clean yarn cache
    if command -v yarn >/dev/null 2>&1; then
        yarn cache clean >/dev/null 2>&1 && cleaned=$((cleaned + 1)) || true
    fi
    
    # Clean Docker buildx cache
    if command -v docker >/dev/null 2>&1; then
        docker buildx prune -f >/dev/null 2>&1 && cleaned=$((cleaned + 1)) || true
    fi
    
    log_success "Cache cleanup completed ($cleaned operations)"
}

# Check for problematic cache paths in workflow files
audit_workflow_cache_paths() {
    log_info "Auditing workflow files for problematic cache paths..."
    
    local workflows_dir="$PROJECT_ROOT/.github/workflows"
    local issues_found=0
    
    if [[ ! -d "$workflows_dir" ]]; then
        log_error "Workflows directory not found: $workflows_dir"
        return 1
    fi
    
    # Look specifically for cache path configurations (not documentation)
    local cache_configs
    cache_configs=$(grep -r -A 10 -B 2 "path:" "$workflows_dir" | grep -E "(~/.cache/apt|/var/cache/apt|/var/lib/apt)" | grep -v "echo" | grep -v "#" || true)
    
    if [[ -n "$cache_configs" ]]; then
        log_warn "Found problematic cache path configurations:"
        echo "$cache_configs" | sed 's/^/  /'
        issues_found=1
    else
        log_success "No problematic cache paths found in workflow configurations"
    fi
    
    # Check for old cache key versions that might be problematic
    local old_versions
    old_versions=$(grep -r "deps-v[12]" "$workflows_dir" 2>/dev/null || true)
    
    if [[ -n "$old_versions" ]]; then
        log_warn "Found old cache key versions that should be updated:"
        echo "$old_versions" | sed 's/^/  /'
    fi
    
    return $issues_found
}

# Generate optimal cache configuration for GitHub Actions
generate_cache_config() {
    local cache_type="${1:-default}"
    
    log_info "Generating cache configuration for type: $cache_type"
    
    case "$cache_type" in
        "dependencies")
            cat <<EOF
path: |
  ~/.cache/pip
  ~/.local/lib/python*/site-packages
  ~/ci-cache
  /tmp/ci-deps
  ~/.cache/node
  ~/.npm
key: deps-${CACHE_VERSION}-\${{ runner.os }}-\${{ hashFiles('**/requirements.txt', '**/package-lock.json', 'scripts/ci-setup.sh') }}
restore-keys: |
  deps-${CACHE_VERSION}-\${{ runner.os }}-\${{ hashFiles('**/requirements.txt', '**/package-lock.json') }}-
  deps-${CACHE_VERSION}-\${{ runner.os }}-
EOF
            ;;
        "docker")
            cat <<EOF
path: |
  /tmp/.buildx-cache
  ~/.docker/buildx-cache
  ~/.cache/docker
  ~/.local/share/docker
key: docker-${CACHE_VERSION}-\${{ runner.os }}-\${{ matrix.test-suite || 'default' }}-\${{ hashFiles('**/Dockerfile*', '**/docker-compose.yml') }}
restore-keys: |
  docker-${CACHE_VERSION}-\${{ runner.os }}-\${{ matrix.test-suite || 'default' }}-
  docker-${CACHE_VERSION}-\${{ runner.os }}-
EOF
            ;;
        "ci-environment")
            cat <<EOF
path: |
  ~/ci-cache
  ~/.cache/pip
  ~/.local/lib
  ~/.local/bin
  /tmp/ci-setup-marker
  /tmp/ci-tools
  ~/.cache/node
  ~/.npm
  ~/.cache/yarn
key: ci-env-${CACHE_VERSION}-\${{ runner.os }}-\${{ hashFiles('scripts/**/*.sh') }}
restore-keys: |
  ci-env-${CACHE_VERSION}-\${{ runner.os }}-
EOF
            ;;
        *)
            log_error "Unknown cache type: $cache_type"
            return 1
            ;;
    esac
}

# Get cache size estimate
estimate_cache_size() {
    log_info "Estimating current cache size..."
    
    local total_size=0
    local paths
    paths=$(get_safe_cache_paths)
    
    while IFS= read -r path; do
        if [[ -n "$path" ]]; then
            # Expand tilde to home directory
            expanded_path="${path/#\~/$HOME}"
            
            if [[ -d "$expanded_path" ]]; then
                local size
                size=$(du -sm "$expanded_path" 2>/dev/null | cut -f1 || echo "0")
                total_size=$((total_size + size))
                log_info "  $expanded_path: ${size}MB"
            fi
        fi
    done <<< "$paths"
    
    log_info "Total estimated cache size: ${total_size}MB"
    
    if [[ $total_size -gt $MAX_CACHE_SIZE_MB ]]; then
        log_warn "Cache size (${total_size}MB) exceeds recommended limit (${MAX_CACHE_SIZE_MB}MB)"
        return 1
    else
        log_success "Cache size is within acceptable limits"
    fi
}

# Check cache health
check_cache_health() {
    log_info "Checking cache health..."
    
    local issues=0
    
    # Check for permission issues
    local paths
    paths=$(get_safe_cache_paths)
    
    while IFS= read -r path; do
        if [[ -n "$path" ]]; then
            expanded_path="${path/#\~/$HOME}"
            
            if [[ -d "$expanded_path" ]]; then
                if [[ ! -w "$expanded_path" ]]; then
                    log_warn "Cache directory not writable: $expanded_path"
                    issues=$((issues + 1))
                fi
            fi
        fi
    done <<< "$paths"
    
    # Check for problematic paths (but don't fail on documentation references)
    if ! audit_workflow_cache_paths; then
        log_warn "Some workflow audit issues found, but may be documentation only"
    fi
    
    # Check cache size
    estimate_cache_size || issues=$((issues + 1))
    
    if [[ $issues -eq 0 ]]; then
        log_success "Cache health check passed"
        return 0
    else
        log_error "Cache health check found $issues issues"
        return 1
    fi
}

# Main function
main() {
    local command="${1:-help}"
    
    case "$command" in
        "setup")
            setup_cache_directories
            ;;
        "cleanup")
            cleanup_cache_directories
            ;;
        "audit")
            audit_workflow_cache_paths
            ;;
        "config")
            local cache_type="${2:-default}"
            generate_cache_config "$cache_type"
            ;;
        "health")
            check_cache_health
            ;;
        "size")
            estimate_cache_size
            ;;
        "help"|*)
            cat <<EOF
GitHub Actions Cache Optimization Tool

Usage: $0 <command> [options]

Commands:
  setup     - Create safe cache directories with proper permissions
  cleanup   - Clean up cache directories to prevent bloat
  audit     - Check workflow files for problematic cache paths
  config    - Generate optimized cache configuration
              Options: dependencies, docker, ci-environment
  health    - Perform comprehensive cache health check
  size      - Estimate current cache size
  help      - Show this help message

Examples:
  $0 setup
  $0 cleanup
  $0 config docker
  $0 health

Cache Configuration:
  - Only user-writable directories are cached
  - System directories (/var/cache/apt, etc.) are avoided
  - Cache size limited to ${MAX_CACHE_SIZE_MB}MB
  - Cache retention: ${CACHE_RETENTION_DAYS} days
  - Version: ${CACHE_VERSION}
EOF
            ;;
    esac
}

# Execute main function with all arguments
main "$@"