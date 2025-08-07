#!/bin/bash

# CI Cache Optimization Script
# This script optimizes GitHub Actions cache performance and prevents permission issues
set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running in GitHub Actions
is_github_actions() {
    [[ "${GITHUB_ACTIONS:-}" == "true" ]]
}

# Check if running as root (which we want to avoid for caching)
is_root() {
    [[ $EUID -eq 0 ]]
}

# Create user-writable cache directories
create_cache_dirs() {
    log_info "Creating user-writable cache directories..."
    
    local cache_dirs=(
        "$HOME/.cache/pip"
        "$HOME/.cache/apt"
        "$HOME/.cache/docker"
        "$HOME/.local/lib"
        "$HOME/ci-cache"
        "/tmp/ci-tools"
        "/tmp/ci-deps"
    )
    
    for dir in "${cache_dirs[@]}"; do
        if mkdir -p "$dir" 2>/dev/null; then
            log_success "Created cache directory: $dir"
            # Set proper permissions
            chmod 755 "$dir" 2>/dev/null || log_warn "Could not set permissions on $dir"
        else
            log_warn "Could not create cache directory: $dir"
        fi
    done
}

# Clean up old cache files to prevent bloat
cleanup_cache_bloat() {
    log_info "Cleaning up cache bloat..."
    
    # Clean up files older than 7 days in user cache directories
    find "$HOME/.cache" -type f -mtime +7 -delete 2>/dev/null || true
    find "/tmp/ci-"* -type f -mtime +1 -delete 2>/dev/null || true
    
    # Clean up Docker cache if it gets too large (> 2GB)
    if [[ -d "$HOME/.cache/docker" ]]; then
        local docker_cache_size
        docker_cache_size=$(du -sb "$HOME/.cache/docker" 2>/dev/null | cut -f1 || echo "0")
        local max_size=$((2 * 1024 * 1024 * 1024)) # 2GB in bytes
        
        if [[ $docker_cache_size -gt $max_size ]]; then
            log_warn "Docker cache size ($docker_cache_size bytes) exceeds limit, cleaning up..."
            find "$HOME/.cache/docker" -type f -mtime +3 -delete 2>/dev/null || true
        fi
    fi
    
    log_success "Cache cleanup completed"
}

# Check for problematic system directories in cache paths
check_system_cache_paths() {
    log_info "Checking for problematic system cache paths..."
    
    local problematic_paths=(
        "/var/cache/apt"
        "/usr/local/lib"
        "/var/lib/apt"
        "/etc/apt"
    )
    
    local found_issues=false
    for path in "${problematic_paths[@]}"; do
        if [[ -d "$path" ]] && [[ ! -w "$path" ]]; then
            log_error "Found non-writable system path that should not be cached: $path"
            found_issues=true
        fi
    done
    
    if [[ "$found_issues" == "true" ]]; then
        log_error "System paths detected that may cause cache permission issues!"
        log_info "Use only user-writable paths like ~/.cache/, ~/ci-cache/, and /tmp/ for caching"
        return 1
    else
        log_success "No problematic system cache paths detected"
    fi
}

# Optimize pip caching
optimize_pip_cache() {
    log_info "Optimizing pip cache..."
    
    # Ensure pip cache directory exists and is writable
    local pip_cache_dir="$HOME/.cache/pip"
    if [[ ! -d "$pip_cache_dir" ]]; then
        mkdir -p "$pip_cache_dir"
        log_success "Created pip cache directory: $pip_cache_dir"
    fi
    
    # Set pip to use the cache directory
    export PIP_CACHE_DIR="$pip_cache_dir"
    
    # Clean up old pip cache files
    if command -v pip3 &> /dev/null; then
        pip3 cache purge 2>/dev/null || true
        log_success "Pip cache optimized"
    fi
}

# Optimize Docker cache
optimize_docker_cache() {
    log_info "Optimizing Docker cache..."
    
    if command -v docker &> /dev/null; then
        # Clean up Docker system to free space
        docker system prune -f 2>/dev/null || true
        
        # Remove dangling images older than 24 hours
        docker image prune -a --filter "until=24h" -f 2>/dev/null || true
        
        log_success "Docker cache optimized"
    else
        log_warn "Docker not available, skipping Docker cache optimization"
    fi
}

# Generate cache optimization report
generate_cache_report() {
    log_info "Generating cache optimization report..."
    
    local report_file="/tmp/cache-optimization-report.json"
    
    cat > "$report_file" << EOF
{
  "timestamp": "$(date -Iseconds)",
  "github_actions": $(is_github_actions && echo "true" || echo "false"),
  "user": "$(whoami)",
  "home_dir": "$HOME",
  "cache_directories": {
    "pip_cache": "$HOME/.cache/pip",
    "apt_cache": "$HOME/.cache/apt",
    "docker_cache": "$HOME/.cache/docker",
    "local_lib": "$HOME/.local/lib",
    "ci_cache": "$HOME/ci-cache",
    "tmp_tools": "/tmp/ci-tools"
  },
  "cache_sizes": {
    "pip_cache_mb": $(du -sm "$HOME/.cache/pip" 2>/dev/null | cut -f1 || echo "0"),
    "total_cache_mb": $(du -sm "$HOME/.cache" 2>/dev/null | cut -f1 || echo "0"),
    "tmp_cache_mb": $(du -sm /tmp/ci-* 2>/dev/null | cut -f1 || echo "0")
  },
  "optimizations_applied": [
    "Created user-writable cache directories",
    "Cleaned up cache bloat",
    "Optimized pip caching",
    "Optimized Docker caching",
    "Avoided system directory caching"
  ]
}
EOF
    
    log_success "Cache report generated: $report_file"
    
    # Display summary
    echo "=== Cache Optimization Summary ==="
    echo "Pip cache size: $(du -sh "$HOME/.cache/pip" 2>/dev/null | cut -f1 || echo "0")B"
    echo "Total cache size: $(du -sh "$HOME/.cache" 2>/dev/null | cut -f1 || echo "0")B"
    echo "Temp cache size: $(du -sh /tmp/ci-* 2>/dev/null | cut -f1 || echo "0")B"
}

# Create cache optimization marker
create_cache_marker() {
    local marker_file="/tmp/ci-cache-optimized"
    cat > "$marker_file" << EOF
CI_CACHE_OPTIMIZED=true
CACHE_OPTIMIZATION_TIME=$(date -Iseconds)
CACHE_OPTIMIZATION_USER=$(whoami)
CACHE_OPTIMIZATION_HOME=$HOME
EOF
    log_success "Cache optimization marker created: $marker_file"
}

# Display help
show_help() {
    cat << EOF
CI Cache Optimization Script

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --help              Show this help message
    --check-only        Only check for issues, don't fix them
    --report-only       Generate report without optimizations
    --cleanup-only      Only perform cleanup operations
    --verbose           Enable verbose output

DESCRIPTION:
    This script optimizes GitHub Actions cache performance by:
    - Creating user-writable cache directories
    - Avoiding system directories that cause permission issues
    - Cleaning up cache bloat to improve performance
    - Optimizing Docker and pip caching strategies
    - Generating performance reports

EXAMPLES:
    $0                  # Run full optimization
    $0 --check-only     # Check for potential issues
    $0 --cleanup-only   # Clean up existing cache bloat
EOF
}

# Main execution
main() {
    local check_only=false
    local report_only=false
    local cleanup_only=false
    local verbose=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help)
                show_help
                exit 0
                ;;
            --check-only)
                check_only=true
                shift
                ;;
            --report-only)
                report_only=true
                shift
                ;;
            --cleanup-only)
                cleanup_only=true
                shift
                ;;
            --verbose)
                verbose=true
                set -x
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    log_info "Starting CI cache optimization..."
    
    if is_github_actions; then
        log_info "Running in GitHub Actions environment"
    else
        log_info "Running in local environment"
    fi
    
    if is_root; then
        log_warn "Running as root - cache may not be properly shared with user processes"
    fi
    
    # Execute based on options
    if [[ "$report_only" == "true" ]]; then
        generate_cache_report
        exit 0
    fi
    
    if [[ "$check_only" == "true" ]]; then
        check_system_cache_paths
        exit $?
    fi
    
    if [[ "$cleanup_only" == "true" ]]; then
        cleanup_cache_bloat
        exit 0
    fi
    
    # Full optimization
    check_system_cache_paths || log_warn "System cache path issues detected but continuing..."
    create_cache_dirs
    cleanup_cache_bloat
    optimize_pip_cache
    optimize_docker_cache
    generate_cache_report
    create_cache_marker
    
    log_success "CI cache optimization completed successfully!"
}

# Run main function with all arguments
main "$@"