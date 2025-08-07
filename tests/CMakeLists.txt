# CMakeLists.txt for MPU-6050 Driver Enhanced Test Suite
# 
# This build system supports comprehensive testing including:
# - Unit tests with Google Test/Mock
# - Integration tests
# - Property-based tests
# - Mutation testing
# - Coverage analysis
# - Performance testing
# - Stress testing

cmake_minimum_required(VERSION 3.16)
project(MPU6050DriverTests 
    VERSION 1.0.0 
    LANGUAGES CXX C
    DESCRIPTION "Comprehensive test suite for MPU-6050 kernel driver")

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Compiler options
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -Wpedantic")
set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS_DEBUG} -g -O0 -DDEBUG")
set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -O2 -DNDEBUG")

# Enable testing
enable_testing()

# Coverage options
option(ENABLE_COVERAGE "Enable code coverage" OFF)
option(ENABLE_SANITIZERS "Enable address and undefined behavior sanitizers" OFF)
option(ENABLE_MUTATION_TESTING "Enable mutation testing" OFF)
option(ENABLE_PERFORMANCE_TESTS "Enable performance tests" ON)

if(ENABLE_COVERAGE)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} --coverage -fprofile-arcs -ftest-coverage")
    set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} --coverage")
endif()

if(ENABLE_SANITIZERS)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fsanitize=address,undefined -fno-omit-frame-pointer")
    set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -fsanitize=address,undefined")
endif()

# Find required packages
find_package(PkgConfig REQUIRED)
find_package(Threads REQUIRED)

# Find Google Test
find_package(GTest REQUIRED)
find_package(GMock REQUIRED)

if(NOT GTest_FOUND)
    message(STATUS "Google Test not found, downloading...")
    
    include(FetchContent)
    FetchContent_Declare(
        googletest
        URL https://github.com/google/googletest/archive/03597a01ee50a057e821f8e3e4a9a1b9f11c6b14.zip
    )
    
    set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
    FetchContent_MakeAvailable(googletest)
    
    set(GTEST_LIBRARIES gtest gtest_main gmock gmock_main)
else()
    set(GTEST_LIBRARIES ${GTEST_LIBRARIES} ${GMOCK_LIBRARIES})
endif()

# Include directories
include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/mocks
    ${CMAKE_CURRENT_SOURCE_DIR}/utils
    ${CMAKE_CURRENT_SOURCE_DIR}/fixtures
    ${CMAKE_CURRENT_SOURCE_DIR}/../include
    ${CMAKE_CURRENT_SOURCE_DIR}/../drivers
)

# Mock and utility libraries
add_library(test_mocks STATIC
    mocks/mock_i2c.cpp
    mocks/mock_i2c.h
)

add_library(test_utils STATIC
    utils/test_helpers.cpp
    utils/test_helpers.h
)

add_library(test_fixtures STATIC
    fixtures/sensor_data.cpp
    fixtures/sensor_data.h
)

target_link_libraries(test_mocks ${GTEST_LIBRARIES})
target_link_libraries(test_utils ${GTEST_LIBRARIES})
target_link_libraries(test_fixtures ${GTEST_LIBRARIES})

# Test executables
set(TEST_LIBRARIES test_mocks test_utils test_fixtures ${GTEST_LIBRARIES} Threads::Threads)

# Unit Tests
add_executable(test_mpu6050_unit
    unit/test_mpu6050.cpp
)
target_link_libraries(test_mpu6050_unit ${TEST_LIBRARIES})

# Enhanced Unit Tests
add_executable(test_mpu6050_enhanced
    unit/test_mpu6050_enhanced.cpp
)
target_link_libraries(test_mpu6050_enhanced ${TEST_LIBRARIES})

# Integration Tests
add_executable(test_mpu6050_integration
    integration/test_mpu6050_integration.cpp
)
target_link_libraries(test_mpu6050_integration ${TEST_LIBRARIES})

# Property-Based Tests
add_executable(test_mpu6050_properties
    property/test_mpu6050_properties.cpp
)
target_link_libraries(test_mpu6050_properties ${TEST_LIBRARIES})

# Mutation Detection Tests
add_executable(test_mutation_detection
    mutation/test_mutation_detection.cpp
)
target_link_libraries(test_mutation_detection ${TEST_LIBRARIES})

# Coverage Analysis Tests
add_executable(test_coverage_analysis
    coverage/coverage_analysis.cpp
)
target_link_libraries(test_coverage_analysis ${TEST_LIBRARIES})

# Performance Tests (optional)
if(ENABLE_PERFORMANCE_TESTS)
    add_executable(test_performance_stress
        performance/test_performance_stress.cpp
    )
    target_link_libraries(test_performance_stress ${TEST_LIBRARIES})
endif()

# Register tests with CTest
add_test(NAME UnitTests COMMAND test_mpu6050_unit)
add_test(NAME EnhancedUnitTests COMMAND test_mpu6050_enhanced)
add_test(NAME IntegrationTests COMMAND test_mpu6050_integration)
add_test(NAME PropertyBasedTests COMMAND test_mpu6050_properties)
add_test(NAME MutationDetectionTests COMMAND test_mutation_detection)
add_test(NAME CoverageAnalysisTests COMMAND test_coverage_analysis)

if(ENABLE_PERFORMANCE_TESTS)
    add_test(NAME PerformanceStressTests COMMAND test_performance_stress)
endif()

# Test properties for timeout and parallel execution
set_tests_properties(UnitTests PROPERTIES TIMEOUT 300)
set_tests_properties(EnhancedUnitTests PROPERTIES TIMEOUT 600)
set_tests_properties(IntegrationTests PROPERTIES TIMEOUT 300)
set_tests_properties(PropertyBasedTests PROPERTIES TIMEOUT 900)
set_tests_properties(MutationDetectionTests PROPERTIES TIMEOUT 300)
set_tests_properties(CoverageAnalysisTests PROPERTIES TIMEOUT 180)

if(ENABLE_PERFORMANCE_TESTS)
    set_tests_properties(PerformanceStressTests PROPERTIES TIMEOUT 1800)
endif()

# Custom targets for different test suites
add_custom_target(test_quick
    COMMAND ${CMAKE_CTEST_COMMAND} -R "UnitTests|MutationDetectionTests"
    DEPENDS test_mpu6050_unit test_mutation_detection
    COMMENT "Running quick test suite"
)

add_custom_target(test_comprehensive
    COMMAND ${CMAKE_CTEST_COMMAND}
    DEPENDS test_mpu6050_unit test_mpu6050_enhanced test_mpu6050_integration 
            test_mpu6050_properties test_mutation_detection test_coverage_analysis
    COMMENT "Running comprehensive test suite"
)

add_custom_target(test_all
    COMMAND ${CMAKE_CTEST_COMMAND}
    COMMENT "Running all tests including performance tests"
)

# Coverage report generation
if(ENABLE_COVERAGE)
    find_program(GCOV_PATH gcov)
    find_program(LCOV_PATH lcov)
    find_program(GENHTML_PATH genhtml)
    
    if(GCOV_PATH AND LCOV_PATH AND GENHTML_PATH)
        add_custom_target(coverage
            COMMAND ${LCOV_PATH} --directory . --capture --output-file coverage.info
            COMMAND ${LCOV_PATH} --remove coverage.info '/usr/*' --output-file coverage.info
            COMMAND ${LCOV_PATH} --list coverage.info
            COMMAND ${GENHTML_PATH} -o coverage coverage.info
            WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
            COMMENT "Generating coverage report"
        )
        
        add_custom_target(coverage_clean
            COMMAND ${LCOV_PATH} --directory . --zerocounters
            WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
            COMMENT "Cleaning coverage data"
        )
    endif()
endif()

# Mutation testing support
if(ENABLE_MUTATION_TESTING)
    find_program(MUTATE_PATH mutate++)
    
    if(MUTATE_PATH)
        add_custom_target(mutation_test
            COMMAND ${MUTATE_PATH} --target test_mpu6050_enhanced --mutant-timeout 30
            DEPENDS test_mpu6050_enhanced
            COMMENT "Running mutation testing"
        )
    endif()
endif()

# Static analysis support
find_program(CPPCHECK_PATH cppcheck)
if(CPPCHECK_PATH)
    add_custom_target(static_analysis
        COMMAND ${CPPCHECK_PATH} 
            --enable=all 
            --std=c++17 
            --verbose 
            --error-exitcode=1
            --suppress=missingIncludeSystem
            ${CMAKE_CURRENT_SOURCE_DIR}
        COMMENT "Running static analysis"
    )
endif()

# Memory leak detection with Valgrind
find_program(VALGRIND_PATH valgrind)
if(VALGRIND_PATH)
    add_custom_target(memcheck
        COMMAND ${VALGRIND_PATH} 
            --leak-check=full 
            --show-leak-kinds=all 
            --track-origins=yes 
            --error-exitcode=1
            $<TARGET_FILE:test_mpu6050_enhanced>
        DEPENDS test_mpu6050_enhanced
        COMMENT "Running memory leak detection"
    )
endif()

# Benchmark target
add_custom_target(benchmark
    COMMAND $<TARGET_FILE:test_performance_stress> --gtest_filter="*Benchmark*"
    DEPENDS test_performance_stress
    COMMENT "Running performance benchmarks"
)

# Test report generation
add_custom_target(test_report
    COMMAND ${CMAKE_CTEST_COMMAND} --output-on-failure --verbose
    COMMENT "Generating detailed test report"
)

# Installation of test executables (for CI/CD systems)
install(TARGETS 
    test_mpu6050_unit
    test_mpu6050_enhanced
    test_mpu6050_integration
    test_mpu6050_properties
    test_mutation_detection
    test_coverage_analysis
    DESTINATION bin/tests
)

if(ENABLE_PERFORMANCE_TESTS)
    install(TARGETS test_performance_stress DESTINATION bin/tests)
endif()

# Print configuration summary
message(STATUS "MPU-6050 Test Suite Configuration:")
message(STATUS "  Build type: ${CMAKE_BUILD_TYPE}")
message(STATUS "  Coverage enabled: ${ENABLE_COVERAGE}")
message(STATUS "  Sanitizers enabled: ${ENABLE_SANITIZERS}")
message(STATUS "  Mutation testing: ${ENABLE_MUTATION_TESTING}")
message(STATUS "  Performance tests: ${ENABLE_PERFORMANCE_TESTS}")
message(STATUS "  Google Test found: ${GTest_FOUND}")

if(ENABLE_COVERAGE AND LCOV_PATH)
    message(STATUS "  Coverage reporting available")
endif()

if(VALGRIND_PATH)
    message(STATUS "  Memory leak detection available")
endif()

if(CPPCHECK_PATH)
    message(STATUS "  Static analysis available")
endif()