#!/bin/bash
# Test runner that properly reports failures while handling missing dependencies

set +e
TEST_FAILED=0

# Check what's available
if [ -f "ci-capabilities.json" ]; then
    CAPS=$(cat ci-capabilities.json)
    echo "Running with capabilities: $CAPS"
fi

# Run tests based on what's available
if [ "$SKIP_KERNEL_BUILD" = "1" ]; then
    echo "Skipping kernel module tests (no kernel headers)"
else
    if ! make test 2>/dev/null; then
        echo "ERROR: Tests failed"
        TEST_FAILED=1
    fi
fi

# Run Python tests if available
if command -v pytest >/dev/null 2>&1; then
    if ! pytest tests/ -v --tb=short 2>/dev/null; then
        echo "ERROR: Python tests failed"
        TEST_FAILED=1
    fi
else
    echo "Pytest not available, skipping Python tests"
fi

# Exit with proper status code
if [ $TEST_FAILED -eq 1 ]; then
    echo "Tests failed - exiting with error"
    exit 1
fi
exit 0
