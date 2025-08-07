#!/bin/bash

# Docker Build Script for MPU-6050 Development Environment
# Author: Murray Kopit <murr2k@gmail.com>

set -e
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $*${NC}" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS] $*${NC}" >&2
}

warn() {
    echo -e "${YELLOW}[WARNING] $*${NC}" >&2
}

error() {
    echo -e "${RED}[ERROR] $*${NC}" >&2
}

show_help() {
    cat << EOF
Docker Build Script for MPU-6050 Development Environment

Usage: $0 [OPTIONS]

OPTIONS:
    --build         Build the Docker image
    --run           Run interactive container
    --test          Run tests in container
    --clean         Remove container and image
    --push          Push to registry (if configured)
    --help          Show this help

EXAMPLES:
    $0 --build                  # Build development image
    $0 --run                    # Start interactive development session
    $0 --test                   # Run full test suite in container
    $0 --clean                  # Clean up containers and images
EOF
}

build_image() {
    log "Building MPU-6050 development environment..."
    
    cd "${PROJECT_ROOT}"
    
    # Build arguments
    local build_args=(
        --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
        --build-arg VCS_REF="$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
        --build-arg VERSION="1.0.0"
    )
    
    # Build the image
    if docker build \
        "${build_args[@]}" \
        -f docker/Dockerfile \
        -t mpu6050-dev:latest \
        -t mpu6050-dev:$(date +%Y%m%d) \
        .; then
        success "Docker image built successfully"
        
        # Show image info
        log "Image details:"
        docker images mpu6050-dev:latest
    else
        error "Failed to build Docker image"
        exit 1
    fi
}

run_container() {
    log "Starting interactive development container..."
    
    local run_args=(
        --rm
        --interactive
        --tty
        --volume "${PROJECT_ROOT}:/workspace"
        --workdir /workspace
        --name mpu6050-dev-$(date +%s)
    )
    
    # Add privileged mode for kernel module development
    run_args+=(--privileged)
    
    # Mount kernel headers if available
    if [[ -d "/lib/modules/$(uname -r)" ]]; then
        run_args+=(--volume "/lib/modules/$(uname -r):/lib/modules/$(uname -r):ro")
    fi
    
    docker run "${run_args[@]}" mpu6050-dev:latest
}

run_tests() {
    log "Running tests in container..."
    
    local test_args=(
        --rm
        --volume "${PROJECT_ROOT}:/workspace"
        --workdir /workspace
        --name mpu6050-test-$(date +%s)
    )
    
    # Run full test suite
    if docker run "${test_args[@]}" mpu6050-dev:latest ./scripts/build.sh --all; then
        success "All tests passed in container"
    else
        error "Tests failed in container"
        exit 1
    fi
    
    # Copy results out of container if needed
    log "Test results available in project directory"
}

clean_containers() {
    log "Cleaning up Docker containers and images..."
    
    # Stop and remove containers
    local containers
    containers=$(docker ps -a -q --filter "ancestor=mpu6050-dev" 2>/dev/null || true)
    if [[ -n "${containers}" ]]; then
        log "Removing containers..."
        docker rm -f ${containers}
    fi
    
    # Remove images
    local images
    images=$(docker images -q mpu6050-dev 2>/dev/null || true)
    if [[ -n "${images}" ]]; then
        log "Removing images..."
        docker rmi -f ${images}
    fi
    
    # Prune build cache
    docker builder prune -f
    
    success "Cleanup completed"
}

push_image() {
    log "Pushing image to registry..."
    
    # This would need to be configured with your registry
    warn "Push functionality not configured"
    warn "Configure your Docker registry and update this script"
    
    # Example:
    # docker tag mpu6050-dev:latest your-registry/mpu6050-dev:latest
    # docker push your-registry/mpu6050-dev:latest
}

main() {
    local build=0
    local run=0
    local test=0
    local clean=0
    local push=0
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --build)
                build=1
                shift
                ;;
            --run)
                run=1
                shift
                ;;
            --test)
                test=1
                shift
                ;;
            --clean)
                clean=1
                shift
                ;;
            --push)
                push=1
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Default to build if no options specified
    if [[ $build -eq 0 && $run -eq 0 && $test -eq 0 && $clean -eq 0 && $push -eq 0 ]]; then
        build=1
    fi
    
    # Check Docker availability
    if ! command -v docker >/dev/null 2>&1; then
        error "Docker not found. Please install Docker first."
        exit 1
    fi
    
    # Execute requested actions
    [[ $clean -eq 1 ]] && clean_containers
    [[ $build -eq 1 ]] && build_image
    [[ $test -eq 1 ]] && run_tests
    [[ $run -eq 1 ]] && run_container
    [[ $push -eq 1 ]] && push_image
    
    success "Docker operations completed successfully"
}

main "$@"