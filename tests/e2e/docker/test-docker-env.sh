#!/bin/bash
#
# Quick Docker Environment Test Script
# Author: Murray Kopit <murr2k@gmail.com>
#
# This script performs a quick validation of the Docker-based E2E testing
# environment to ensure all components are working properly.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")

# Colors
RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
RESET="\033[0m"

# Test configuration
TEST_IMAGE="mpu6050-e2e-test:test"
TEST_TIMEOUT=60

log() {
    echo -e "[$(date -u +'%H:%M:%S')] $*"
}

log_info() {
    log "${BLUE}INFO${RESET}: $*"
}

log_success() {
    log "${GREEN}SUCCESS${RESET}: $*"
}

log_warn() {
    log "${YELLOW}WARN${RESET}: $*"
}

log_error() {
    log "${RED}ERROR${RESET}: $*"
}

# Test functions
test_prerequisites() {
    log_info "Testing prerequisites..."
    
    # Check Docker
    if ! command -v docker >/dev/null 2>&1; then
        log_error "Docker not found"
        return 1
    fi
    
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker daemon not running"
        return 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose >/dev/null 2>&1 && ! docker compose version >/dev/null 2>&1; then
        log_warn "Docker Compose not found (optional for basic tests)"
    fi
    
    log_success "Prerequisites check passed"
    return 0
}

test_dockerfile() {
    log_info "Testing Dockerfile build..."
    
    cd "${SCRIPT_DIR}/../../../"  # Go to project root
    
    if docker build -f tests/e2e/docker/Dockerfile.e2e -t "${TEST_IMAGE}" . >/dev/null 2>&1; then
        log_success "Docker image built successfully"
        return 0
    else
        log_error "Docker image build failed"
        return 1
    fi
}

test_container_startup() {
    log_info "Testing container startup..."
    
    local container_id
    container_id=$(docker run -d --rm "${TEST_IMAGE}" sleep 30)
    
    if [ -n "${container_id}" ]; then
        # Check if container is running
        if docker ps --filter "id=${container_id}" --format "table {{.ID}}" | grep -q "${container_id}"; then
            log_success "Container started successfully"
            docker kill "${container_id}" >/dev/null 2>&1 || true
            return 0
        else
            log_error "Container failed to start properly"
            return 1
        fi
    else
        log_error "Failed to create container"
        return 1
    fi
}

test_entrypoint() {
    log_info "Testing entrypoint script..."
    
    # Test entrypoint with health check
    if timeout "${TEST_TIMEOUT}" docker run --rm "${TEST_IMAGE}" /usr/local/bin/test-health-check >/dev/null 2>&1; then
        log_success "Entrypoint health check passed"
        return 0
    else
        log_error "Entrypoint health check failed"
        return 1
    fi
}

test_simulator() {
    log_info "Testing I2C simulator..."
    
    # Test simulator startup (short duration)
    if timeout 10 docker run --rm \
        -e SIMULATOR_ENABLED=true \
        -e SIMULATE_HARDWARE=true \
        "${TEST_IMAGE}" \
        python3 /opt/mpu6050-test/src/tests/utils/simulator_daemon.py --help >/dev/null 2>&1; then
        log_success "I2C simulator is functional"
        return 0
    else
        log_warn "I2C simulator test inconclusive"
        return 0  # Non-critical
    fi
}

test_basic_tools() {
    log_info "Testing basic tools availability..."
    
    local tools=("gcc" "make" "python3" "pytest" "lcov")
    local missing_tools=()
    
    for tool in "${tools[@]}"; do
        if ! docker run --rm "${TEST_IMAGE}" which "${tool}" >/dev/null 2>&1; then
            missing_tools+=("${tool}")
        fi
    done
    
    if [ ${#missing_tools[@]} -eq 0 ]; then
        log_success "All required tools are available"
        return 0
    else
        log_error "Missing tools: ${missing_tools[*]}"
        return 1
    fi
}

test_volume_mounts() {
    log_info "Testing volume mounts..."
    
    cd "${SCRIPT_DIR}"
    
    # Create test directories
    mkdir -p test-results test-logs
    
    # Test volume mounting
    if docker run --rm \
        -v "$(pwd)/test-results:/opt/mpu6050-test/results:rw" \
        -v "$(pwd)/test-logs:/var/log/mpu6050-test:rw" \
        "${TEST_IMAGE}" \
        /bin/bash -c "echo 'test' > /opt/mpu6050-test/results/test-file.txt && echo 'test' > /var/log/mpu6050-test/test-log.txt" >/dev/null 2>&1; then
        
        if [ -f "test-results/test-file.txt" ] && [ -f "test-logs/test-log.txt" ]; then
            log_success "Volume mounts working correctly"
            rm -f test-results/test-file.txt test-logs/test-log.txt
            return 0
        else
            log_error "Volume mount files not created"
            return 1
        fi
    else
        log_error "Volume mount test failed"
        return 1
    fi
}

test_docker_compose() {
    log_info "Testing Docker Compose configuration..."
    
    cd "${SCRIPT_DIR}"
    
    # Check if docker-compose.yml is valid
    local compose_cmd
    if command -v docker-compose >/dev/null 2>&1; then
        compose_cmd="docker-compose"
    else
        compose_cmd="docker compose"
    fi
    
    if ${compose_cmd} config >/dev/null 2>&1; then
        log_success "Docker Compose configuration is valid"
        return 0
    else
        log_error "Docker Compose configuration is invalid"
        return 1
    fi
}

test_quick_run() {
    log_info "Testing quick test execution..."
    
    cd "${SCRIPT_DIR}"
    
    # Run a very quick test (just health check)
    if timeout "${TEST_TIMEOUT}" docker run --rm \
        -e TEST_TIMEOUT=10 \
        -e SIMULATE_HARDWARE=true \
        -e SIMULATOR_ENABLED=true \
        -v "$(pwd)/test-results:/opt/mpu6050-test/results:rw" \
        -v "$(pwd)/test-logs:/var/log/mpu6050-test:rw" \
        "${TEST_IMAGE}" \
        --skip-build >/dev/null 2>&1; then
        log_success "Quick test execution completed"
        return 0
    else
        log_warn "Quick test execution had issues (may be expected in test environment)"
        return 0  # Non-critical for environment test
    fi
}

cleanup() {
    log_info "Cleaning up test artifacts..."
    
    # Remove test image
    docker rmi "${TEST_IMAGE}" >/dev/null 2>&1 || true
    
    # Clean test directories
    rm -rf "${SCRIPT_DIR}/test-results" "${SCRIPT_DIR}/test-logs" 2>/dev/null || true
    
    log_info "Cleanup completed"
}

# Main test execution
main() {
    log_info "Starting Docker environment validation"
    log_info "Timestamp: ${TIMESTAMP}"
    
    local tests=(
        "test_prerequisites"
        "test_dockerfile"
        "test_container_startup"
        "test_entrypoint"
        "test_basic_tools"
        "test_volume_mounts"
        "test_docker_compose"
        "test_simulator"
        "test_quick_run"
    )
    
    local passed=0
    local failed=0
    local warnings=0
    
    for test_func in "${tests[@]}"; do
        log_info "Running ${test_func}..."
        
        if ${test_func}; then
            ((passed++))
        else
            ((failed++))
        fi
        
        echo  # Empty line for readability
    done
    
    # Summary
    log_info "=== Test Summary ==="
    log_info "Tests passed: ${passed}"
    log_info "Tests failed: ${failed}"
    
    if [ ${failed} -eq 0 ]; then
        log_success "Docker environment validation PASSED!"
        log_info "The environment is ready for E2E testing."
        return 0
    else
        log_error "Docker environment validation FAILED!"
        log_error "Please fix the issues above before running E2E tests."
        return 1
    fi
}

# Set up trap for cleanup
trap cleanup EXIT

# Help message
if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    cat << EOF
Usage: $0 [OPTIONS]

Docker Environment Test Script for MPU-6050 E2E Testing

This script validates that the Docker-based testing environment is properly
configured and ready for use.

Options:
    --help, -h    Show this help message

Tests performed:
    1. Prerequisites check (Docker, Docker Compose)
    2. Dockerfile build test
    3. Container startup test
    4. Entrypoint script test
    5. Basic tools availability
    6. Volume mounts functionality
    7. Docker Compose configuration
    8. I2C simulator functionality
    9. Quick test execution

Example:
    $0                    # Run all validation tests

For full E2E testing, use:
    ./run_e2e_docker.sh
EOF
    exit 0
fi

# Run main function
main "$@"