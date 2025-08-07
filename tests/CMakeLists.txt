# CMakeLists.txt for MPU-6050 Kernel Driver Unit Tests
cmake_minimum_required(VERSION 3.16)
project(mpu6050_tests 
    VERSION 1.0.0
    DESCRIPTION "Unit tests for MPU-6050 Linux kernel driver"
    LANGUAGES CXX
)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Build configuration
set(CMAKE_BUILD_TYPE Debug CACHE STRING "Build type")

# Compiler flags
set(CMAKE_CXX_FLAGS_DEBUG "-g -O0 -Wall -Wextra -Wpedantic -Werror")
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -DNDEBUG -Wall")

# Enable testing
enable_testing()

# Find required packages
find_package(PkgConfig REQUIRED)

# Google Test
find_package(GTest REQUIRED)
if(NOT GTest_FOUND)
    message(STATUS "GTest not found via find_package, trying pkg-config")
    pkg_check_modules(GTEST REQUIRED gtest)
    pkg_check_modules(GMOCK REQUIRED gmock)
endif()

# Threads (required by Google Test)
find_package(Threads REQUIRED)

# Include directories
include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/mocks
    ${CMAKE_CURRENT_SOURCE_DIR}/utils
    ${CMAKE_CURRENT_SOURCE_DIR}/fixtures
    ${CMAKE_CURRENT_SOURCE_DIR}/../src  # Kernel driver source (if available)
)

# Compiler definitions for kernel-like environment simulation
add_compile_definitions(
    UNIT_TEST_BUILD=1
    LINUX_KERNEL_MOCK=1
    __KERNEL__=1
    MODULE=1
)

# Source files
set(MOCK_SOURCES
    mocks/mock_i2c.cpp
)

set(UTILS_SOURCES
    utils/test_helpers.cpp
)

set(FIXTURES_SOURCES
    fixtures/sensor_data.cpp
)

set(TEST_SOURCES
    unit/test_main.cpp
    unit/test_mpu6050.cpp
)

# Create a library for mocks and utilities (reusable across test executables)
add_library(test_support STATIC
    ${MOCK_SOURCES}
    ${UTILS_SOURCES}
    ${FIXTURES_SOURCES}
)

target_include_directories(test_support PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/mocks
    ${CMAKE_CURRENT_SOURCE_DIR}/utils
    ${CMAKE_CURRENT_SOURCE_DIR}/fixtures
)

# Link against Google Test and Google Mock
if(GTest_FOUND)
    target_link_libraries(test_support
        GTest::gtest
        GTest::gmock
        Threads::Threads
    )
else()
    target_link_libraries(test_support
        ${GTEST_LIBRARIES}
        ${GMOCK_LIBRARIES}
        Threads::Threads
    )
    target_include_directories(test_support PUBLIC ${GTEST_INCLUDE_DIRS})
endif()

# Main test executable
add_executable(mpu6050_unit_tests ${TEST_SOURCES})

target_link_libraries(mpu6050_unit_tests
    test_support
)

# Add test to CTest
add_test(NAME MPU6050UnitTests COMMAND mpu6050_unit_tests)

# Additional test executables for specific test categories
add_executable(mpu6050_integration_tests
    unit/test_main.cpp
    # Add integration test files here when created
)

target_link_libraries(mpu6050_integration_tests
    test_support
)

# Performance tests
add_executable(mpu6050_performance_tests
    unit/test_main.cpp
    # Add performance test files here when created
)

target_link_libraries(mpu6050_performance_tests
    test_support
)

# Custom targets for different test types

# Run all tests
add_custom_target(test_all
    DEPENDS mpu6050_unit_tests
    COMMAND ${CMAKE_CTEST_COMMAND} --output-on-failure
    COMMENT "Running all MPU-6050 tests"
)

# Run tests with verbose output
add_custom_target(test_verbose
    DEPENDS mpu6050_unit_tests
    COMMAND ./mpu6050_unit_tests --verbose
    COMMENT "Running tests with verbose output"
)

# Run specific test categories
add_custom_target(test_probe
    DEPENDS mpu6050_unit_tests
    COMMAND ./mpu6050_unit_tests --gtest_filter="*Probe*"
    COMMENT "Running device probe tests"
)

add_custom_target(test_data_reading
    DEPENDS mpu6050_unit_tests
    COMMAND ./mpu6050_unit_tests --gtest_filter="*ReadSensor*"
    COMMENT "Running sensor data reading tests"
)

add_custom_target(test_error_handling
    DEPENDS mpu6050_unit_tests
    COMMAND ./mpu6050_unit_tests --gtest_filter="*Error*:*Handle*"
    COMMENT "Running error handling tests"
)

add_custom_target(test_performance
    DEPENDS mpu6050_performance_tests
    COMMAND ./mpu6050_performance_tests
    COMMENT "Running performance tests"
)

# Code coverage (if gcov/lcov available)
option(ENABLE_COVERAGE "Enable code coverage" OFF)

if(ENABLE_COVERAGE)
    find_program(GCOV_PATH gcov)
    find_program(LCOV_PATH lcov)
    find_program(GENHTML_PATH genhtml)
    
    if(GCOV_PATH AND LCOV_PATH AND GENHTML_PATH)
        message(STATUS "Code coverage enabled")
        
        # Add coverage flags
        set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS_DEBUG} --coverage -fno-inline")
        set(CMAKE_EXE_LINKER_FLAGS_DEBUG "${CMAKE_EXE_LINKER_FLAGS_DEBUG} --coverage")
        
        # Coverage target
        add_custom_target(coverage
            COMMAND ${LCOV_PATH} --directory . --zerocounters
            COMMAND ${CMAKE_CTEST_COMMAND} --output-on-failure
            COMMAND ${LCOV_PATH} --directory . --capture --output-file coverage.info
            COMMAND ${LCOV_PATH} --remove coverage.info '/usr/*' '*/tests/*' --output-file coverage.info.cleaned
            COMMAND ${GENHTML_PATH} -o coverage coverage.info.cleaned
            COMMAND ${CMAKE_COMMAND} -E echo "Coverage report generated in coverage/index.html"
            WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
            DEPENDS mpu6050_unit_tests
            COMMENT "Generating code coverage report"
        )
    else()
        message(WARNING "Code coverage requested but tools not found")
        set(ENABLE_COVERAGE OFF)
    endif()
endif()

# Valgrind memory checking (if available)
find_program(VALGRIND_PATH valgrind)
if(VALGRIND_PATH)
    add_custom_target(test_memcheck
        DEPENDS mpu6050_unit_tests
        COMMAND ${VALGRIND_PATH} --tool=memcheck --leak-check=full --show-leak-kinds=all --track-origins=yes --error-exitcode=1 ./mpu6050_unit_tests
        COMMENT "Running tests with Valgrind memory checking"
    )
endif()

# Static analysis with cppcheck (if available)
find_program(CPPCHECK_PATH cppcheck)
if(CPPCHECK_PATH)
    add_custom_target(static_analysis
        COMMAND ${CPPCHECK_PATH} --enable=all --std=c++17 --platform=unix64 --suppress=missingIncludeSystem ${CMAKE_CURRENT_SOURCE_DIR}
        COMMENT "Running static analysis with cppcheck"
    )
endif()

# Clang-tidy (if available)
find_program(CLANG_TIDY_PATH clang-tidy)
if(CLANG_TIDY_PATH)
    set_target_properties(test_support PROPERTIES
        CXX_CLANG_TIDY "${CLANG_TIDY_PATH};-checks=-*,readability-*,performance-*,modernize-*"
    )
endif()

# Documentation generation with Doxygen (if available)
find_package(Doxygen)
if(DOXYGEN_FOUND)
    set(DOXYGEN_IN ${CMAKE_CURRENT_SOURCE_DIR}/Doxyfile.in)
    set(DOXYGEN_OUT ${CMAKE_CURRENT_BINARY_DIR}/Doxyfile)
    
    if(EXISTS ${DOXYGEN_IN})
        configure_file(${DOXYGEN_IN} ${DOXYGEN_OUT} @ONLY)
        
        add_custom_target(docs
            COMMAND ${DOXYGEN_EXECUTABLE} ${DOXYGEN_OUT}
            WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
            COMMENT "Generating API documentation with Doxygen"
            VERBATIM
        )
    endif()
endif()

# Installation (for CI/CD environments)
install(TARGETS mpu6050_unit_tests
    DESTINATION bin
    COMPONENT tests
)

install(FILES 
    ${CMAKE_CURRENT_SOURCE_DIR}/README_Tests.md
    DESTINATION share/doc/mpu6050-tests
    COMPONENT documentation
    OPTIONAL
)

# CTest configuration
set(CTEST_OUTPUT_ON_FAILURE ON)
set_tests_properties(MPU6050UnitTests PROPERTIES
    TIMEOUT 300
    PASS_REGULAR_EXPRESSION ".*tests.*passed"
    FAIL_REGULAR_EXPRESSION ".*tests.*FAILED"
)

# Package configuration (for distribution)
set(CPACK_PACKAGE_NAME "mpu6050-unit-tests")
set(CPACK_PACKAGE_VERSION "${PROJECT_VERSION}")
set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "Unit tests for MPU-6050 kernel driver")
set(CPACK_PACKAGE_VENDOR "Linux Kernel Development")
set(CPACK_GENERATOR "TGZ;DEB")

if(CPACK_GENERATOR MATCHES "DEB")
    set(CPACK_DEBIAN_PACKAGE_DEPENDS "libgtest-dev, libgmock-dev, build-essential")
    set(CPACK_DEBIAN_PACKAGE_MAINTAINER "developer@example.com")
endif()

include(CPack)

# Print configuration summary
message(STATUS "")
message(STATUS "MPU-6050 Test Configuration Summary:")
message(STATUS "  Build type: ${CMAKE_BUILD_TYPE}")
message(STATUS "  C++ standard: C++${CMAKE_CXX_STANDARD}")
message(STATUS "  Google Test found: ${GTest_FOUND}")
message(STATUS "  Code coverage: ${ENABLE_COVERAGE}")
message(STATUS "  Valgrind available: ${VALGRIND_PATH}")
message(STATUS "  Cppcheck available: ${CPPCHECK_PATH}")
message(STATUS "  Clang-tidy available: ${CLANG_TIDY_PATH}")
message(STATUS "  Doxygen available: ${DOXYGEN_FOUND}")
message(STATUS "")

# Help target
add_custom_target(help_tests
    COMMAND ${CMAKE_COMMAND} -E echo ""
    COMMAND ${CMAKE_COMMAND} -E echo "Available test targets:"
    COMMAND ${CMAKE_COMMAND} -E echo "  test_all          - Run all tests"
    COMMAND ${CMAKE_COMMAND} -E echo "  test_verbose      - Run tests with verbose output"
    COMMAND ${CMAKE_COMMAND} -E echo "  test_probe        - Run device probe tests only"
    COMMAND ${CMAKE_COMMAND} -E echo "  test_data_reading - Run sensor data reading tests only"
    COMMAND ${CMAKE_COMMAND} -E echo "  test_error_handling - Run error handling tests only"
    COMMAND ${CMAKE_COMMAND} -E echo "  test_performance  - Run performance tests"
    COMMAND ${CMAKE_COMMAND} -E echo "  test_memcheck     - Run tests with Valgrind (if available)"
    COMMAND ${CMAKE_COMMAND} -E echo "  static_analysis   - Run cppcheck static analysis"
    COMMAND ${CMAKE_COMMAND} -E echo "  coverage          - Generate code coverage report (if enabled)"
    COMMAND ${CMAKE_COMMAND} -E echo "  docs              - Generate documentation"
    COMMAND ${CMAKE_COMMAND} -E echo ""
    COMMENT "Display available test targets"
)