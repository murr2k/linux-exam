#!/bin/bash
#
# MPU-6050 E2E Docker Test Runner
# Author: Murray Kopit <murr2k@gmail.com>
#
# This script orchestrates the complete Docker-based E2E testing workflow
# including image building, container management, test execution, and cleanup.

set -euo pipefail

# Script configuration
SCRIPT_NAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../../" && pwd)"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
PID=$$

# Docker configuration
DOCKER_IMAGE_NAME="mpu6050-e2e-test"
DOCKER_IMAGE_TAG="latest"
DOCKER_CONTAINER_NAME="mpu6050-e2e-tests-${TIMESTAMP}"
DOCKER_COMPOSE_PROJECT="mpu6050-test-${TIMESTAMP}"
DOCKER_NETWORK_NAME="mpu6050-test-network-${TIMESTAMP}"

# Test configuration
TEST_MODE="${TEST_MODE:-e2e}"
TEST_VERBOSE="${TEST_VERBOSE:-false}"
TEST_CONTINUOUS="${TEST_CONTINUOUS:-false}"
TEST_TIMEOUT="${TEST_TIMEOUT:-300}"
TEST_RETRIES="${TEST_RETRIES:-3}"
TEST_PARALLEL="${TEST_PARALLEL:-true}"

# Environment configuration
SIMULATE_HARDWARE="${SIMULATE_HARDWARE:-true}"
SIMULATOR_ENABLED="${SIMULATOR_ENABLED:-true}"
COVERAGE_ENABLED="${COVERAGE_ENABLED:-true}"
PERF_TEST_ENABLED="${PERF_TEST_ENABLED:-true}"

# Output configuration
COLORIZED_OUTPUT="${COLORIZED_OUTPUT:-true}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"
QUIET_MODE="${QUIET_MODE:-false}"

# CI/CD integration
CI="${CI:-false}"
GITHUB_ACTIONS="${GITHUB_ACTIONS:-false}"
BUILD_NUMBER="${BUILD_NUMBER:-0}"
GIT_COMMIT="${GIT_COMMIT:-$(git rev-parse HEAD 2>/dev/null || echo 'unknown')}"
GIT_BRANCH="${GIT_BRANCH:-$(git branch --show-current 2>/dev/null || echo 'main')}"

# Result directories
RESULTS_DIR="${SCRIPT_DIR}/test-results"
LOGS_DIR="${SCRIPT_DIR}/test-logs"
ARTIFACTS_DIR="${SCRIPT_DIR}/artifacts"

# Color codes
if [ "${COLORIZED_OUTPUT}" = "true" ] && [ -t 1 ]; then
    export COLOR_RED="\033[31m"
    export COLOR_GREEN="\033[32m"
    export COLOR_YELLOW="\033[33m"
    export COLOR_BLUE="\033[34m"
    export COLOR_MAGENTA="\033[35m"
    export COLOR_CYAN="\033[36m"
    export COLOR_RESET="\033[0m"
else
    export COLOR_RED=""
    export COLOR_GREEN=""
    export COLOR_YELLOW=""
    export COLOR_BLUE=""
    export COLOR_MAGENTA=""
    export COLOR_CYAN=""
    export COLOR_RESET=""
fi

# Logging functions
log() {
    local level="$1"
    shift
    local timestamp=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
    if [ "${QUIET_MODE}" != "true" ] || [ "${level}" = "ERROR" ]; then
        echo -e "[${timestamp}] [${level}] [${SCRIPT_NAME}:${PID}] $*" >&2
    fi
    # Also log to file if directory exists
    if [ -d "${LOGS_DIR}" ]; then
        echo "[${timestamp}] [${level}] [${SCRIPT_NAME}:${PID}] $*" >> "${LOGS_DIR}/docker-runner.log"
    fi
}

log_info() {
    log "INFO" "${COLOR_BLUE}$*${COLOR_RESET}"
}

log_warn() {
    log "WARN" "${COLOR_YELLOW}$*${COLOR_RESET}"
}

log_error() {
    log "ERROR" "${COLOR_RED}$*${COLOR_RESET}"
}

log_success() {
    log "SUCCESS" "${COLOR_GREEN}$*${COLOR_RESET}"
}

log_debug() {
    if [ "${LOG_LEVEL}" = "DEBUG" ]; then
        log "DEBUG" "$*"
    fi
}

# Cleanup function
cleanup() {
    local exit_code=$?
    log_info "Starting cleanup process..."
    
    # Stop and remove containers
    cleanup_containers
    
    # Clean up networks
    cleanup_networks
    
    # Collect final artifacts
    collect_artifacts
    
    # Generate final report
    generate_summary_report "${exit_code}"
    
    log_info "Cleanup completed with exit code: ${exit_code}"
    
    # For CI environments, ensure proper exit
    if [ "${CI}" = "true" ]; then
        exit "${exit_code}"
    fi
}

# Set up trap for cleanup
trap cleanup EXIT
trap 'log_error "Received SIGTERM, initiating graceful shutdown..."; exit 143' TERM
trap 'log_error "Received SIGINT, initiating graceful shutdown..."; exit 130' INT

# Prerequisites check
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker >/dev/null 2>&1; then
        log_error "Docker is required but not installed"
        return 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose >/dev/null 2>&1 && ! docker compose version >/dev/null 2>&1; then
        log_error "Docker Compose is required but not installed"
        return 1
    fi
    
    # Check Docker daemon
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker daemon is not running"
        return 1
    fi
    
    # Check project structure
    if [ ! -d "${PROJECT_ROOT}" ]; then
        log_error "Project root directory not found: ${PROJECT_ROOT}"
        return 1
    fi
    
    if [ ! -f "${PROJECT_ROOT}/Makefile" ]; then
        log_error "Project Makefile not found"
        return 1
    fi
    
    # Check available disk space (at least 2GB)
    local available_space
    available_space=$(df "${PROJECT_ROOT}" | tail -1 | awk '{print $4}')
    if [ "${available_space}" -lt 2097152 ]; then  # 2GB in KB
        log_warn "Low disk space: $(( available_space / 1024 ))MB available"
    fi
    
    log_success "Prerequisites check completed"
    return 0
}

# Directory setup
setup_directories() {
    log_info "Setting up test directories..."
    
    # Create result directories
    mkdir -p "${RESULTS_DIR}" "${LOGS_DIR}" "${ARTIFACTS_DIR}"
    
    # Create bind mount directories for Docker
    mkdir -p "${SCRIPT_DIR}/test-results" "${SCRIPT_DIR}/test-logs"
    
    # Set permissions
    chmod 755 "${RESULTS_DIR}" "${LOGS_DIR}" "${ARTIFACTS_DIR}"
    chmod 777 "${SCRIPT_DIR}/test-results" "${SCRIPT_DIR}/test-logs"  # For container access
    
    log_success "Directories setup completed"
}

# Docker image building
build_docker_image() {
    log_info "Building Docker image: ${DOCKER_IMAGE_NAME}:${DOCKER_IMAGE_TAG}..."
    
    cd "${PROJECT_ROOT}"
    
    # Build arguments
    local build_args=()
    build_args+=("--build-arg" "BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')")
    build_args+=("--build-arg" "VCS_REF=${GIT_COMMIT}")
    build_args+=("--build-arg" "BUILD_NUMBER=${BUILD_NUMBER}")
    
    # Add cache options for CI
    if [ "${CI}" = "true" ]; then
        build_args+=("--no-cache")
    fi
    
    # Add progress output
    if [ "${QUIET_MODE}" != "true" ]; then
        build_args+=("--progress=plain")
    fi
    
    # Build the image
    if docker build \
        "${build_args[@]}" \
        -f "tests/e2e/docker/Dockerfile.e2e" \
        -t "${DOCKER_IMAGE_NAME}:${DOCKER_IMAGE_TAG}" \
        . >> "${LOGS_DIR}/docker-build.log" 2>&1; then
        log_success "Docker image built successfully"
    else
        log_error "Docker image build failed"
        cat "${LOGS_DIR}/docker-build.log"
        return 1
    fi
    
    # Show image information
    docker images "${DOCKER_IMAGE_NAME}:${DOCKER_IMAGE_TAG}" >> "${LOGS_DIR}/docker-build.log"
    
    return 0
}

# Docker container execution
run_docker_tests() {
    log_info "Running tests in Docker container..."
    
    local test_args="$1"
    local container_exit_code=0
    
    # Prepare environment variables for container
    local docker_env=()
    docker_env+=("-e" "TEST_ENV=docker")
    docker_env+=("-e" "TEST_MODE=${TEST_MODE}")
    docker_env+=("-e" "TEST_VERBOSE=${TEST_VERBOSE}")
    docker_env+=("-e" "TEST_CONTINUOUS=${TEST_CONTINUOUS}")
    docker_env+=("-e" "TEST_TIMEOUT=${TEST_TIMEOUT}")
    docker_env+=("-e" "TEST_RETRIES=${TEST_RETRIES}")
    docker_env+=("-e" "TEST_PARALLEL=${TEST_PARALLEL}")
    docker_env+=("-e" "SIMULATE_HARDWARE=${SIMULATE_HARDWARE}")
    docker_env+=("-e" "SIMULATOR_ENABLED=${SIMULATOR_ENABLED}")
    docker_env+=("-e" "COVERAGE_ENABLED=${COVERAGE_ENABLED}")
    docker_env+=("-e" "PERF_TEST_ENABLED=${PERF_TEST_ENABLED}")
    docker_env+=("-e" "LOG_LEVEL=${LOG_LEVEL}")
    docker_env+=("-e" "COLORIZED_OUTPUT=${COLORIZED_OUTPUT}")
    docker_env+=("-e" "CI=${CI}")
    docker_env+=("-e" "GITHUB_ACTIONS=${GITHUB_ACTIONS}")
    docker_env+=("-e" "BUILD_NUMBER=${BUILD_NUMBER}")
    docker_env+=("-e" "GIT_COMMIT=${GIT_COMMIT}")
    docker_env+=("-e" "GIT_BRANCH=${GIT_BRANCH}")
    
    # Prepare volume mounts
    local docker_volumes=()
    docker_volumes+=("-v" "${PROJECT_ROOT}:/opt/mpu6050-test/src:ro")
    docker_volumes+=("-v" "${SCRIPT_DIR}/test-results:/opt/mpu6050-test/results:rw")
    docker_volumes+=("-v" "${SCRIPT_DIR}/test-logs:/var/log/mpu6050-test:rw")
    docker_volumes+=("-v" "/lib/modules:/lib/modules:ro")
    docker_volumes+=("-v" "/proc:/host-proc:ro")
    docker_volumes+=("-v" "/etc/localtime:/etc/localtime:ro")
    
    # Add kernel source if available
    if [ -d "/usr/src/linux-headers-$(uname -r)" ]; then
        docker_volumes+=("-v" "/usr/src:/usr/src:ro")
    fi
    
    # Prepare Docker run arguments
    local docker_args=()
    docker_args+=("--name" "${DOCKER_CONTAINER_NAME}")
    docker_args+=("--hostname" "mpu6050-test-runner")
    docker_args+=("--privileged")  # Required for kernel module testing
    docker_args+=("--cap-add=SYS_MODULE")
    docker_args+=("--cap-add=SYS_ADMIN")
    docker_args+=("--rm")  # Remove container after completion
    
    # Network configuration
    docker_args+=("--network" "bridge")
    
    # Resource limits
    docker_args+=("--memory=4g")
    docker_args+=("--cpus=4.0")
    
    # Security options
    docker_args+=("--security-opt" "apparmor:unconfined")
    
    log_info "Starting Docker container: ${DOCKER_CONTAINER_NAME}"
    log_debug "Docker command: docker run ${docker_args[*]} ${docker_env[*]} ${docker_volumes[*]} ${DOCKER_IMAGE_NAME}:${DOCKER_IMAGE_TAG} ${test_args}"
    
    # Run the container
    if docker run \
        "${docker_args[@]}" \
        "${docker_env[@]}" \
        "${docker_volumes[@]}" \
        "${DOCKER_IMAGE_NAME}:${DOCKER_IMAGE_TAG}" \
        ${test_args} >> "${LOGS_DIR}/test-execution.log" 2>&1; then
        log_success "Docker tests completed successfully"
        container_exit_code=0
    else
        container_exit_code=$?
        log_error "Docker tests failed with exit code: ${container_exit_code}"
    fi
    
    # Show container logs if tests failed and not in quiet mode
    if [ ${container_exit_code} -ne 0 ] && [ "${QUIET_MODE}" != "true" ]; then
        log_info "Container execution logs:"
        tail -n 50 "${LOGS_DIR}/test-execution.log" || true
    fi
    
    return ${container_exit_code}
}

# Docker Compose execution
run_docker_compose_tests() {
    log_info "Running tests using Docker Compose..."
    
    cd "${SCRIPT_DIR}"
    
    # Prepare environment file
    cat > ".env" << EOF
# Docker Compose environment for MPU-6050 E2E tests
COMPOSE_PROJECT_NAME=${DOCKER_COMPOSE_PROJECT}
TEST_VERBOSE=${TEST_VERBOSE}
TEST_CONTINUOUS=${TEST_CONTINUOUS}
TEST_TIMEOUT=${TEST_TIMEOUT}
TEST_RETRIES=${TEST_RETRIES}
TEST_PARALLEL=${TEST_PARALLEL}
SIMULATE_HARDWARE=${SIMULATE_HARDWARE}
SIMULATOR_ENABLED=${SIMULATOR_ENABLED}
COVERAGE_ENABLED=${COVERAGE_ENABLED}
PERF_TEST_ENABLED=${PERF_TEST_ENABLED}
LOG_LEVEL=${LOG_LEVEL}
COLORIZED_OUTPUT=${COLORIZED_OUTPUT}
CI=${CI}
GITHUB_ACTIONS=${GITHUB_ACTIONS}
BUILD_NUMBER=${BUILD_NUMBER}
GIT_COMMIT=${GIT_COMMIT}
GIT_BRANCH=${GIT_BRANCH}
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VCS_REF=${GIT_COMMIT}
EOF
    
    # Check if docker-compose or docker compose is available
    local compose_cmd
    if command -v docker-compose >/dev/null 2>&1; then
        compose_cmd="docker-compose"
    else
        compose_cmd="docker compose"
    fi
    
    log_info "Using compose command: ${compose_cmd}"
    
    # Run the compose stack
    if ${compose_cmd} --project-name "${DOCKER_COMPOSE_PROJECT}" \
        up --build --abort-on-container-exit --exit-code-from mpu6050-e2e-tests \
        >> "${LOGS_DIR}/compose-execution.log" 2>&1; then
        log_success "Docker Compose tests completed successfully"
        return 0
    else
        local compose_exit_code=$?
        log_error "Docker Compose tests failed with exit code: ${compose_exit_code}"
        
        # Show compose logs
        log_info "Docker Compose logs:"
        ${compose_cmd} --project-name "${DOCKER_COMPOSE_PROJECT}" logs >> "${LOGS_DIR}/compose-execution.log" 2>&1 || true
        
        # Cleanup compose stack
        ${compose_cmd} --project-name "${DOCKER_COMPOSE_PROJECT}" down -v >> "${LOGS_DIR}/compose-execution.log" 2>&1 || true
        
        return ${compose_exit_code}
    fi
}

# Container cleanup
cleanup_containers() {
    log_info "Cleaning up Docker containers..."
    
    # Remove test container if it exists
    if docker ps -a --format "table {{.Names}}" | grep -q "${DOCKER_CONTAINER_NAME}"; then
        docker rm -f "${DOCKER_CONTAINER_NAME}" >> "${LOGS_DIR}/cleanup.log" 2>&1 || true
    fi
    
    # Cleanup compose stack
    cd "${SCRIPT_DIR}"
    local compose_cmd
    if command -v docker-compose >/dev/null 2>&1; then
        compose_cmd="docker-compose"
    else
        compose_cmd="docker compose"
    fi
    
    ${compose_cmd} --project-name "${DOCKER_COMPOSE_PROJECT}" down -v >> "${LOGS_DIR}/cleanup.log" 2>&1 || true
    
    # Clean up dangling images if not in CI
    if [ "${CI}" != "true" ]; then
        docker image prune -f >> "${LOGS_DIR}/cleanup.log" 2>&1 || true
    fi
    
    log_success "Container cleanup completed"
}

# Network cleanup
cleanup_networks() {
    log_info "Cleaning up Docker networks..."
    
    # Remove custom networks
    docker network ls --format "table {{.Name}}" | grep "mpu6050-test" | xargs -r docker network rm >> "${LOGS_DIR}/cleanup.log" 2>&1 || true
    
    # Prune unused networks if not in CI
    if [ "${CI}" != "true" ]; then
        docker network prune -f >> "${LOGS_DIR}/cleanup.log" 2>&1 || true
    fi
    
    log_success "Network cleanup completed"
}

# Artifact collection
collect_artifacts() {
    log_info "Collecting test artifacts..."
    
    # Copy test results
    if [ -d "${SCRIPT_DIR}/test-results" ]; then
        cp -r "${SCRIPT_DIR}/test-results"/* "${ARTIFACTS_DIR}/" 2>/dev/null || true
    fi
    
    # Copy test logs
    if [ -d "${SCRIPT_DIR}/test-logs" ]; then
        cp -r "${SCRIPT_DIR}/test-logs"/* "${LOGS_DIR}/" 2>/dev/null || true
    fi
    
    # Create artifact archive
    cd "${SCRIPT_DIR}"
    tar -czf "${ARTIFACTS_DIR}/test-artifacts-${TIMESTAMP}.tar.gz" \
        test-results test-logs *.log .env 2>/dev/null || true
    
    log_success "Artifact collection completed"
}

# Summary report generation
generate_summary_report() {
    local exit_code=$1
    log_info "Generating test summary report..."
    
    local report_file="${ARTIFACTS_DIR}/test-summary-${TIMESTAMP}.md"
    
    {
        echo "# MPU-6050 Docker E2E Test Summary"
        echo ""
        echo "**Execution Date:** $(date -u)"
        echo "**Test Mode:** ${TEST_MODE}"
        echo "**Environment:** Docker"
        echo "**Exit Code:** ${exit_code}"
        echo "**Build Number:** ${BUILD_NUMBER}"
        echo "**Git Commit:** ${GIT_COMMIT}"
        echo "**Git Branch:** ${GIT_BRANCH}"
        echo ""
        echo "## Configuration"
        echo ""
        echo "- **Test Verbose:** ${TEST_VERBOSE}"
        echo "- **Test Continuous:** ${TEST_CONTINUOUS}"
        echo "- **Test Timeout:** ${TEST_TIMEOUT}s"
        echo "- **Test Retries:** ${TEST_RETRIES}"
        echo "- **Simulate Hardware:** ${SIMULATE_HARDWARE}"
        echo "- **Coverage Enabled:** ${COVERAGE_ENABLED}"
        echo "- **Performance Tests:** ${PERF_TEST_ENABLED}"
        echo ""
        echo "## Docker Configuration"
        echo ""
        echo "- **Image:** ${DOCKER_IMAGE_NAME}:${DOCKER_IMAGE_TAG}"
        echo "- **Container:** ${DOCKER_CONTAINER_NAME}"
        echo "- **Project:** ${DOCKER_COMPOSE_PROJECT}"
        echo ""
        echo "## Results"
        echo ""
        if [ ${exit_code} -eq 0 ]; then
            echo "✅ **Overall Result: PASSED**"
        else
            echo "❌ **Overall Result: FAILED**"
        fi
        echo ""
        echo "## Artifacts"
        echo ""
        echo "### Log Files"
        find "${LOGS_DIR}" -name "*.log" -type f 2>/dev/null | sort | sed 's/^/- /' || echo "- No log files found"
        echo ""
        echo "### Result Files"
        find "${ARTIFACTS_DIR}" -type f 2>/dev/null | sort | sed 's/^/- /' || echo "- No result files found"
        echo ""
        echo "## System Information"
        echo ""
        echo "- **Host OS:** $(uname -s)"
        echo "- **Host Kernel:** $(uname -r)"
        echo "- **Docker Version:** $(docker --version)"
        echo "- **Available Memory:** $(free -h | awk 'NR==2{print $7}')"
        echo "- **Available Disk:** $(df -h . | tail -1 | awk '{print $4}')"
        echo ""
        echo "---"
        echo "*Generated by MPU-6050 Docker E2E Test Runner*"
        echo "*Timestamp: ${TIMESTAMP}*"
        echo "*Process ID: ${PID}*"
    } > "${report_file}"
    
    log_success "Summary report generated: $(basename "${report_file}")"
    
    # Show summary on console if not in quiet mode
    if [ "${QUIET_MODE}" != "true" ]; then
        echo ""
        cat "${report_file}"
        echo ""
    fi
}

# Help message
show_help() {
    cat << EOF
Usage: $0 [OPTIONS] [TEST_ARGS]

Options:
    --build-only          Build Docker image only, don't run tests
    --run-only            Run tests only, skip building (image must exist)
    --use-compose         Use Docker Compose instead of direct docker run
    --clean-first         Clean up existing containers and images first
    --quiet               Quiet mode - minimal output
    --verbose             Verbose mode - detailed output
    --help                Show this help message

Test Arguments (passed to container):
    --run-all             Run all test suites (default)
    --c-tests-only        Run only C-based tests
    --python-tests-only   Run only Python-based tests
    --performance-only    Run only performance tests
    --skip-build          Skip module building in container

Environment Variables:
    TEST_VERBOSE          Enable verbose test output (true/false)
    TEST_CONTINUOUS       Run tests continuously (true/false)
    TEST_TIMEOUT          Test timeout in seconds (default: 300)
    TEST_RETRIES          Number of test retries (default: 3)
    SIMULATE_HARDWARE     Enable hardware simulation (true/false)
    COVERAGE_ENABLED      Enable coverage collection (true/false)
    PERF_TEST_ENABLED     Enable performance tests (true/false)
    QUIET_MODE            Quiet runner output (true/false)
    LOG_LEVEL             Log level (DEBUG/INFO/WARN/ERROR)

Examples:
    $0                                    # Build and run all tests
    $0 --run-only --c-tests-only          # Run only C tests (skip build)
    $0 --use-compose                      # Use Docker Compose
    $0 --verbose --performance-only       # Verbose performance tests
    TEST_VERBOSE=true $0                  # Run with verbose test output
    SIMULATE_HARDWARE=false $0            # Run with real hardware
    CI=true $0                            # Run in CI mode

Directories:
    Results:    ${RESULTS_DIR}
    Logs:       ${LOGS_DIR}
    Artifacts:  ${ARTIFACTS_DIR}
EOF
}

# Main execution function
main() {
    log_info "Starting MPU-6050 Docker E2E Test Runner"
    log_info "Process ID: ${PID}, Timestamp: ${TIMESTAMP}"
    log_info "Project Root: ${PROJECT_ROOT}"
    
    # Parse command line arguments
    local build_only=false
    local run_only=false
    local use_compose=false
    local clean_first=false
    local test_args="--run-all"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --build-only)
                build_only=true
                shift
                ;;
            --run-only)
                run_only=true
                shift
                ;;
            --use-compose)
                use_compose=true
                shift
                ;;
            --clean-first)
                clean_first=true
                shift
                ;;
            --quiet)
                QUIET_MODE=true
                shift
                ;;
            --verbose)
                TEST_VERBOSE=true
                LOG_LEVEL=DEBUG
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            --run-all|--c-tests-only|--python-tests-only|--performance-only|--skip-build)
                test_args="$1"
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Step 1: Check prerequisites
    if ! check_prerequisites; then
        log_error "Prerequisites check failed"
        exit 1
    fi
    
    # Step 2: Setup directories
    setup_directories
    
    # Step 3: Clean up first if requested
    if [ "$clean_first" = true ]; then
        log_info "Cleaning up existing containers and images..."
        cleanup_containers
        cleanup_networks
        # Remove existing image
        docker rmi "${DOCKER_IMAGE_NAME}:${DOCKER_IMAGE_TAG}" >> "${LOGS_DIR}/cleanup.log" 2>&1 || true
    fi
    
    # Step 4: Build Docker image (unless run-only)
    if [ "$run_only" = false ]; then
        if ! build_docker_image; then
            log_error "Docker image build failed"
            exit 1
        fi
    fi
    
    # Step 5: Run tests (unless build-only)
    local test_exit_code=0
    if [ "$build_only" = false ]; then
        if [ "$use_compose" = true ]; then
            if ! run_docker_compose_tests; then
                test_exit_code=1
            fi
        else
            if ! run_docker_tests "${test_args}"; then
                test_exit_code=1
            fi
        fi
    fi
    
    # Test execution completed - cleanup will be handled by trap
    if [ ${test_exit_code} -eq 0 ]; then
        log_success "Docker E2E test execution completed successfully!"
    else
        log_error "Docker E2E test execution failed!"
    fi
    
    exit ${test_exit_code}
}

# Run main function with all arguments
main "$@"