#!/bin/bash

# Robust Test Execution Wrapper
# Handles missing components gracefully and provides comprehensive reporting
# Author: Murray Kopit <murr2k@gmail.com>

set -euo pipefail

# Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly TEST_DIR="$PROJECT_ROOT/tests"
readonly RESULTS_DIR="$PROJECT_ROOT/test-results"
readonly FIXTURES_DIR="$TEST_DIR/fixtures"

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Test categories
declare -a TEST_CATEGORIES=(
    "unit"
    "integration" 
    "e2e"
    "performance"
    "property"
    "mutation"
    "coverage"
)

# Required dependencies for each test type
declare -A TEST_DEPENDENCIES=(
    ["unit"]="gcc g++ cunit"
    ["integration"]="gcc g++ cunit"
    ["e2e"]="python3 pytest docker"
    ["performance"]="gcc g++ cunit"
    ["property"]="gcc g++ cunit"
    ["mutation"]="gcc g++ cunit"
    ["coverage"]="gcc g++ lcov gcov"
)

# Global variables
declare -a AVAILABLE_TESTS=()
declare -a SKIPPED_TESTS=()
declare -a FAILED_TESTS=()
declare -a PASSED_TESTS=()
declare -i TOTAL_TESTS=0
declare -i PASSED_COUNT=0
declare -i FAILED_COUNT=0
declare -i SKIPPED_COUNT=0

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check dependencies for a test category
check_dependencies() {
    local category="$1"
    local deps="${TEST_DEPENDENCIES[$category]:-}"
    local missing=()
    
    if [[ -z "$deps" ]]; then
        return 0
    fi
    
    for dep in $deps; do
        if ! command_exists "$dep"; then
            missing+=("$dep")
        fi
    done
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        log_warning "Missing dependencies for $category tests: ${missing[*]}"
        return 1
    fi
    
    return 0
}

# Discover available test files
discover_tests() {
    local category="$1"
    local test_files=()
    
    case "$category" in
        "unit")
            mapfile -t test_files < <(find "$TEST_DIR/unit" -name "*.cpp" -o -name "*.c" 2>/dev/null || true)
            ;;
        "integration")
            mapfile -t test_files < <(find "$TEST_DIR/integration" -name "*.cpp" -o -name "*.c" 2>/dev/null || true)
            ;;
        "e2e")
            mapfile -t test_files < <(find "$TEST_DIR/e2e" -name "*.py" -o -name "*.c" 2>/dev/null || true)
            ;;
        "performance")
            mapfile -t test_files < <(find "$TEST_DIR/performance" -name "*.cpp" -o -name "*.c" 2>/dev/null || true)
            ;;
        "property")
            mapfile -t test_files < <(find "$TEST_DIR/property" -name "*.cpp" -o -name "*.c" 2>/dev/null || true)
            ;;
        "mutation")
            mapfile -t test_files < <(find "$TEST_DIR/mutation" -name "*.cpp" -o -name "*.c" 2>/dev/null || true)
            ;;
        "coverage")
            mapfile -t test_files < <(find "$TEST_DIR/coverage" -name "*.cpp" -o -name "*.c" 2>/dev/null || true)
            ;;
    esac
    
    printf '%s\n' "${test_files[@]}"
}

# Check if test files exist for category
has_test_files() {
    local category="$1"
    local files
    mapfile -t files < <(discover_tests "$category")
    [[ ${#files[@]} -gt 0 ]]
}

# Build C/C++ test
build_c_test() {
    local test_file="$1"
    local category="$2"
    local output_file="$RESULTS_DIR/${category}/$(basename "${test_file%.*}")"
    
    mkdir -p "$RESULTS_DIR/$category"
    
    local include_flags="-I$PROJECT_ROOT/include -I$TEST_DIR/mocks"
    local link_flags="-lcunit"
    
    if [[ "$test_file" == *.cpp ]]; then
        if ! g++ $include_flags "$test_file" $link_flags -o "$output_file" 2>"$RESULTS_DIR/${category}/build.log"; then
            log_error "Failed to build $test_file"
            return 1
        fi
    else
        if ! gcc $include_flags "$test_file" $link_flags -o "$output_file" 2>"$RESULTS_DIR/${category}/build.log"; then
            log_error "Failed to build $test_file"
            return 1
        fi
    fi
    
    echo "$output_file"
}

# Run C/C++ test
run_c_test() {
    local executable="$1"
    local category="$2"
    local test_name="$(basename "$executable")"
    local result_file="$RESULTS_DIR/${category}/${test_name}.xml"
    
    log_info "Running $category test: $test_name"
    
    if timeout 30 "$executable" > "$RESULTS_DIR/${category}/${test_name}.log" 2>&1; then
        log_success "$test_name passed"
        PASSED_TESTS+=("$category/$test_name")
        ((PASSED_COUNT++))
        
        # Generate basic JUnit XML for passed test
        cat > "$result_file" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="$category.$test_name" tests="1" failures="0" errors="0" time="0">
    <testcase classname="$category" name="$test_name" time="0"/>
</testsuite>
EOF
        return 0
    else
        log_error "$test_name failed"
        FAILED_TESTS+=("$category/$test_name")
        ((FAILED_COUNT++))
        
        # Generate JUnit XML for failed test
        cat > "$result_file" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="$category.$test_name" tests="1" failures="1" errors="0" time="0">
    <testcase classname="$category" name="$test_name" time="0">
        <failure message="Test execution failed">$(tail -10 "$RESULTS_DIR/${category}/${test_name}.log" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g')</failure>
    </testcase>
</testsuite>
EOF
        return 1
    fi
}

# Run Python tests
run_python_tests() {
    local category="$1"
    local test_dir="$TEST_DIR/$category"
    
    log_info "Running Python tests in $category"
    
    cd "$test_dir"
    
    local result_file="$RESULTS_DIR/${category}/pytest.xml"
    mkdir -p "$RESULTS_DIR/$category"
    
    if python3 -m pytest --junitxml="$result_file" --tb=short . 2>"$RESULTS_DIR/${category}/pytest.log"; then
        log_success "$category Python tests passed"
        PASSED_TESTS+=("$category/python")
        ((PASSED_COUNT++))
        return 0
    else
        log_error "$category Python tests failed"
        FAILED_TESTS+=("$category/python")
        ((FAILED_COUNT++))
        return 1
    fi
}

# Run tests for a category
run_category_tests() {
    local category="$1"
    
    log_info "Processing $category tests..."
    
    # Check if category directory exists
    if [[ ! -d "$TEST_DIR/$category" ]]; then
        log_warning "Test directory not found: $TEST_DIR/$category"
        SKIPPED_TESTS+=("$category (directory missing)")
        ((SKIPPED_COUNT++))
        return 0
    fi
    
    # Check dependencies
    if ! check_dependencies "$category"; then
        SKIPPED_TESTS+=("$category (missing dependencies)")
        ((SKIPPED_COUNT++))
        return 0
    fi
    
    # Check for test files
    if ! has_test_files "$category"; then
        log_warning "No test files found for $category"
        SKIPPED_TESTS+=("$category (no test files)")
        ((SKIPPED_COUNT++))
        return 0
    fi
    
    AVAILABLE_TESTS+=("$category")
    
    # Handle different test types
    case "$category" in
        "e2e")
            if command_exists python3 && command_exists pytest; then
                run_python_tests "$category"
            else
                # Try to run C e2e tests
                local test_files
                mapfile -t test_files < <(discover_tests "$category")
                for test_file in "${test_files[@]}"; do
                    if [[ "$test_file" == *.c || "$test_file" == *.cpp ]]; then
                        local executable
                        if executable=$(build_c_test "$test_file" "$category"); then
                            run_c_test "$executable" "$category"
                        else
                            FAILED_TESTS+=("$category/$(basename "$test_file")")
                            ((FAILED_COUNT++))
                        fi
                    fi
                done
            fi
            ;;
        *)
            # C/C++ tests
            local test_files
            mapfile -t test_files < <(discover_tests "$category")
            for test_file in "${test_files[@]}"; do
                ((TOTAL_TESTS++))
                local executable
                if executable=$(build_c_test "$test_file" "$category"); then
                    run_c_test "$executable" "$category"
                else
                    FAILED_TESTS+=("$category/$(basename "$test_file")")
                    ((FAILED_COUNT++))
                fi
            done
            ;;
    esac
}

# Generate test data if missing
ensure_test_data() {
    log_info "Ensuring test data is available..."
    
    if [[ -f "$TEST_DIR/test-discovery.py" ]]; then
        python3 "$TEST_DIR/test-discovery.py" --generate-data
    fi
    
    if [[ -f "$FIXTURES_DIR/generate_test_data.py" ]]; then
        cd "$FIXTURES_DIR"
        python3 generate_test_data.py
    fi
}

# Generate comprehensive summary report
generate_summary() {
    local summary_file="$RESULTS_DIR/test-summary.json"
    local html_file="$RESULTS_DIR/test-summary.html"
    
    mkdir -p "$RESULTS_DIR"
    
    # JSON Summary
    cat > "$summary_file" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "total_tests": $TOTAL_TESTS,
    "passed": $PASSED_COUNT,
    "failed": $FAILED_COUNT,
    "skipped": $SKIPPED_COUNT,
    "success_rate": "$(awk "BEGIN {printf \"%.1f\", $PASSED_COUNT*100/($TOTAL_TESTS > 0 ? $TOTAL_TESTS : 1)}")%",
    "available_categories": $(printf '%s\n' "${AVAILABLE_TESTS[@]}" | jq -R . | jq -s .),
    "passed_tests": $(printf '%s\n' "${PASSED_TESTS[@]}" | jq -R . | jq -s . 2>/dev/null || echo '[]'),
    "failed_tests": $(printf '%s\n' "${FAILED_TESTS[@]}" | jq -R . | jq -s . 2>/dev/null || echo '[]'),
    "skipped_tests": $(printf '%s\n' "${SKIPPED_TESTS[@]}" | jq -R . | jq -s . 2>/dev/null || echo '[]')
}
EOF

    # HTML Summary
    cat > "$html_file" << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Execution Summary</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { color: #2c3e50; }
        .stats { display: flex; gap: 20px; margin: 20px 0; }
        .stat-card { padding: 15px; border-radius: 8px; text-align: center; min-width: 100px; }
        .passed { background-color: #d4edda; color: #155724; }
        .failed { background-color: #f8d7da; color: #721c24; }
        .skipped { background-color: #fff3cd; color: #856404; }
        .total { background-color: #e2e3e5; color: #383d41; }
        .section { margin: 20px 0; }
        .test-list { background-color: #f8f9fa; padding: 15px; border-radius: 5px; }
        .test-item { margin: 5px 0; padding: 5px; border-left: 3px solid #007bff; background: white; }
    </style>
</head>
<body>
    <h1 class="header">Test Execution Summary</h1>
    <p><strong>Generated:</strong> TIMESTAMP_PLACEHOLDER</p>
    
    <div class="stats">
        <div class="stat-card total">
            <h3>TOTAL_TESTS</h3>
            <p>Total Tests</p>
        </div>
        <div class="stat-card passed">
            <h3>PASSED_COUNT</h3>
            <p>Passed</p>
        </div>
        <div class="stat-card failed">
            <h3>FAILED_COUNT</h3>
            <p>Failed</p>
        </div>
        <div class="stat-card skipped">
            <h3>SKIPPED_COUNT</h3>
            <p>Skipped</p>
        </div>
    </div>

    <div class="section">
        <h2>Available Test Categories</h2>
        <div class="test-list">
            AVAILABLE_TESTS_PLACEHOLDER
        </div>
    </div>

    <div class="section">
        <h2>Test Results</h2>
        
        <h3>Passed Tests</h3>
        <div class="test-list">
            PASSED_TESTS_PLACEHOLDER
        </div>
        
        <h3>Failed Tests</h3>
        <div class="test-list">
            FAILED_TESTS_PLACEHOLDER
        </div>
        
        <h3>Skipped Tests</h3>
        <div class="test-list">
            SKIPPED_TESTS_PLACEHOLDER
        </div>
    </div>
</body>
</html>
EOF

    # Replace placeholders
    sed -i "s/TIMESTAMP_PLACEHOLDER/$(date)/" "$html_file"
    sed -i "s/TOTAL_TESTS/$TOTAL_TESTS/" "$html_file"
    sed -i "s/PASSED_COUNT/$PASSED_COUNT/" "$html_file"
    sed -i "s/FAILED_COUNT/$FAILED_COUNT/" "$html_file"
    sed -i "s/SKIPPED_COUNT/$SKIPPED_COUNT/" "$html_file"
    
    # Generate test lists
    local available_list=""
    for test in "${AVAILABLE_TESTS[@]}"; do
        available_list+="<div class=\"test-item\">$test</div>"
    done
    sed -i "s/AVAILABLE_TESTS_PLACEHOLDER/$available_list/" "$html_file"
    
    local passed_list=""
    for test in "${PASSED_TESTS[@]}"; do
        passed_list+="<div class=\"test-item\">$test</div>"
    done
    sed -i "s/PASSED_TESTS_PLACEHOLDER/$passed_list/" "$html_file"
    
    local failed_list=""
    for test in "${FAILED_TESTS[@]}"; do
        failed_list+="<div class=\"test-item\">$test</div>"
    done
    sed -i "s/FAILED_TESTS_PLACEHOLDER/$failed_list/" "$html_file"
    
    local skipped_list=""
    for test in "${SKIPPED_TESTS[@]}"; do
        skipped_list+="<div class=\"test-item\">$test</div>"
    done
    sed -i "s/SKIPPED_TESTS_PLACEHOLDER/$skipped_list/" "$html_file"
}

# Print final summary
print_summary() {
    echo
    echo "=================================="
    echo "       TEST EXECUTION SUMMARY     "
    echo "=================================="
    echo
    printf "Total Tests:    %d\n" $TOTAL_TESTS
    printf "Passed:         %d\n" $PASSED_COUNT
    printf "Failed:         %d\n" $FAILED_COUNT
    printf "Skipped:        %d\n" $SKIPPED_COUNT
    echo
    
    if [[ $TOTAL_TESTS -gt 0 ]]; then
        local success_rate=$(awk "BEGIN {printf \"%.1f\", $PASSED_COUNT*100/$TOTAL_TESTS}")
        printf "Success Rate:   %s%%\n" "$success_rate"
    fi
    
    echo
    
    if [[ ${#AVAILABLE_TESTS[@]} -gt 0 ]]; then
        echo "Available Test Categories:"
        printf "  - %s\n" "${AVAILABLE_TESTS[@]}"
        echo
    fi
    
    if [[ ${#SKIPPED_TESTS[@]} -gt 0 ]]; then
        echo "Skipped Tests:"
        printf "  - %s\n" "${SKIPPED_TESTS[@]}"
        echo
    fi
    
    if [[ ${#FAILED_TESTS[@]} -gt 0 ]]; then
        echo "Failed Tests:"
        printf "  - %s\n" "${FAILED_TESTS[@]}"
        echo
    fi
    
    echo "Reports available at:"
    echo "  - JSON: $RESULTS_DIR/test-summary.json"
    echo "  - HTML: $RESULTS_DIR/test-summary.html"
    echo "  - JUnit XML files in $RESULTS_DIR/"
    echo
}

# Main execution
main() {
    local categories_to_run=("${TEST_CATEGORIES[@]}")
    local verbose=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --category)
                categories_to_run=("$2")
                shift 2
                ;;
            --verbose|-v)
                verbose=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo
                echo "Options:"
                echo "  --category CATEGORY  Run specific test category"
                echo "  --verbose, -v        Enable verbose output"
                echo "  --help, -h          Show this help"
                echo
                echo "Available categories: ${TEST_CATEGORIES[*]}"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    log_info "Starting test execution wrapper..."
    log_info "Project root: $PROJECT_ROOT"
    
    # Ensure test data exists
    ensure_test_data
    
    # Clean previous results
    rm -rf "$RESULTS_DIR"
    mkdir -p "$RESULTS_DIR"
    
    # Run tests for each category
    for category in "${categories_to_run[@]}"; do
        run_category_tests "$category"
    done
    
    # Generate reports
    generate_summary
    print_summary
    
    # Return appropriate exit code
    if [[ $FAILED_COUNT -gt 0 ]]; then
        log_error "Some tests failed"
        exit 1
    elif [[ $PASSED_COUNT -eq 0 ]] && [[ $SKIPPED_COUNT -eq 0 ]]; then
        log_error "No tests were executed"
        exit 1
    else
        log_success "All available tests passed"
        exit 0
    fi
}

# Run main function with all arguments
main "$@"