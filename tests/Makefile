# Makefile for MPU-6050 Kernel Driver Unit Tests
# Alternative build system for environments where CMake is not available

# Project settings
PROJECT_NAME = mpu6050_tests
VERSION = 1.0.0

# Directories
SRC_DIR = .
BUILD_DIR = build
BIN_DIR = $(BUILD_DIR)/bin
OBJ_DIR = $(BUILD_DIR)/obj
MOCK_DIR = mocks
UTILS_DIR = utils
FIXTURES_DIR = fixtures
UNIT_DIR = unit

# Compiler settings
CXX = g++
CXXSTD = -std=c++17
CXXFLAGS = -Wall -Wextra -Wpedantic -g -O0 $(CXXSTD)
LDFLAGS = 
INCLUDES = -I$(SRC_DIR) -I$(MOCK_DIR) -I$(UTILS_DIR) -I$(FIXTURES_DIR)

# Preprocessor definitions
DEFINES = -DUNIT_TEST_BUILD=1 -DLINUX_KERNEL_MOCK=1 -D__KERNEL__=1 -DMODULE=1

# Library detection and flags
GTEST_CFLAGS = $(shell pkg-config --cflags gtest gmock 2>/dev/null || echo "-I/usr/include/gtest -I/usr/include/gmock")
GTEST_LIBS = $(shell pkg-config --libs gtest gmock 2>/dev/null || echo "-lgtest -lgmock")

# Thread support
THREAD_LIBS = -lpthread

# All flags combined
ALL_CXXFLAGS = $(CXXFLAGS) $(INCLUDES) $(DEFINES) $(GTEST_CFLAGS)
ALL_LDFLAGS = $(LDFLAGS) $(GTEST_LIBS) $(THREAD_LIBS)

# Source files
MOCK_SOURCES = $(wildcard $(MOCK_DIR)/*.cpp)
UTILS_SOURCES = $(wildcard $(UTILS_DIR)/*.cpp)
FIXTURES_SOURCES = $(wildcard $(FIXTURES_DIR)/*.cpp)
UNIT_SOURCES = $(wildcard $(UNIT_DIR)/*.cpp)

# Object files
MOCK_OBJECTS = $(MOCK_SOURCES:$(MOCK_DIR)/%.cpp=$(OBJ_DIR)/mock_%.o)
UTILS_OBJECTS = $(UTILS_SOURCES:$(UTILS_DIR)/%.cpp=$(OBJ_DIR)/utils_%.o)
FIXTURES_OBJECTS = $(FIXTURES_SOURCES:$(FIXTURES_DIR)/%.cpp=$(OBJ_DIR)/fixtures_%.o)
UNIT_OBJECTS = $(UNIT_SOURCES:$(UNIT_DIR)/%.cpp=$(OBJ_DIR)/unit_%.o)

# Support library objects (mocks, utils, fixtures)
SUPPORT_OBJECTS = $(MOCK_OBJECTS) $(UTILS_OBJECTS) $(FIXTURES_OBJECTS)

# All object files
ALL_OBJECTS = $(SUPPORT_OBJECTS) $(UNIT_OBJECTS)

# Executables
MAIN_EXECUTABLE = $(BIN_DIR)/$(PROJECT_NAME)
TEST_EXECUTABLES = $(MAIN_EXECUTABLE)

# Default target
.PHONY: all
all: check-deps $(TEST_EXECUTABLES)

# Check dependencies
.PHONY: check-deps
check-deps:
	@echo "Checking dependencies..."
	@command -v $(CXX) >/dev/null 2>&1 || { echo "Error: $(CXX) not found"; exit 1; }
	@echo "#include <gtest/gtest.h>" | $(CXX) $(GTEST_CFLAGS) -x c++ -c - -o /dev/null 2>/dev/null || { echo "Error: Google Test not found. Install with: sudo apt-get install libgtest-dev libgmock-dev"; exit 1; }
	@echo "Dependencies OK"

# Create directories
$(BUILD_DIR) $(BIN_DIR) $(OBJ_DIR):
	mkdir -p $@

# Build main test executable
$(MAIN_EXECUTABLE): $(ALL_OBJECTS) | $(BIN_DIR)
	@echo "Linking $@..."
	$(CXX) $(ALL_OBJECTS) -o $@ $(ALL_LDFLAGS)

# Compile mock sources
$(OBJ_DIR)/mock_%.o: $(MOCK_DIR)/%.cpp | $(OBJ_DIR)
	@echo "Compiling $<..."
	$(CXX) $(ALL_CXXFLAGS) -c $< -o $@

# Compile utils sources
$(OBJ_DIR)/utils_%.o: $(UTILS_DIR)/%.cpp | $(OBJ_DIR)
	@echo "Compiling $<..."
	$(CXX) $(ALL_CXXFLAGS) -c $< -o $@

# Compile fixtures sources
$(OBJ_DIR)/fixtures_%.o: $(FIXTURES_DIR)/%.cpp | $(OBJ_DIR)
	@echo "Compiling $<..."
	$(CXX) $(ALL_CXXFLAGS) -c $< -o $@

# Compile unit test sources
$(OBJ_DIR)/unit_%.o: $(UNIT_DIR)/%.cpp | $(OBJ_DIR)
	@echo "Compiling $<..."
	$(CXX) $(ALL_CXXFLAGS) -c $< -o $@

# Test targets
.PHONY: test
test: $(MAIN_EXECUTABLE)
	@echo "Running all tests..."
	$(MAIN_EXECUTABLE)

.PHONY: test-verbose
test-verbose: $(MAIN_EXECUTABLE)
	@echo "Running tests with verbose output..."
	$(MAIN_EXECUTABLE) --verbose

.PHONY: test-probe
test-probe: $(MAIN_EXECUTABLE)
	@echo "Running device probe tests..."
	$(MAIN_EXECUTABLE) --gtest_filter="*Probe*"

.PHONY: test-data-reading
test-data-reading: $(MAIN_EXECUTABLE)
	@echo "Running sensor data reading tests..."
	$(MAIN_EXECUTABLE) --gtest_filter="*ReadSensor*"

.PHONY: test-error-handling
test-error-handling: $(MAIN_EXECUTABLE)
	@echo "Running error handling tests..."
	$(MAIN_EXECUTABLE) --gtest_filter="*Error*:*Handle*"

.PHONY: test-xml
test-xml: $(MAIN_EXECUTABLE)
	@echo "Running tests with XML output..."
	$(MAIN_EXECUTABLE) --gtest_output=xml:$(BUILD_DIR)/test_results.xml

# Code quality targets
.PHONY: static-analysis
static-analysis:
	@echo "Running static analysis..."
	@command -v cppcheck >/dev/null 2>&1 && \
		cppcheck --enable=all --std=c++17 --platform=unix64 --suppress=missingIncludeSystem $(SRC_DIR) || \
		echo "cppcheck not found, skipping static analysis"

.PHONY: format-check
format-check:
	@echo "Checking code formatting..."
	@command -v clang-format >/dev/null 2>&1 && \
		find $(SRC_DIR) -name "*.cpp" -o -name "*.h" | xargs clang-format --dry-run --Werror || \
		echo "clang-format not found, skipping format check"

.PHONY: format
format:
	@echo "Formatting code..."
	@command -v clang-format >/dev/null 2>&1 && \
		find $(SRC_DIR) -name "*.cpp" -o -name "*.h" | xargs clang-format -i || \
		echo "clang-format not found, skipping formatting"

# Memory checking with Valgrind
.PHONY: memcheck
memcheck: $(MAIN_EXECUTABLE)
	@echo "Running tests with Valgrind memory checking..."
	@command -v valgrind >/dev/null 2>&1 && \
		valgrind --tool=memcheck --leak-check=full --show-leak-kinds=all --track-origins=yes --error-exitcode=1 $(MAIN_EXECUTABLE) || \
		echo "Valgrind not found, skipping memory check"

# Performance profiling
.PHONY: profile
profile: CXXFLAGS += -pg
profile: $(MAIN_EXECUTABLE)
	@echo "Running tests with profiling..."
	$(MAIN_EXECUTABLE)
	@command -v gprof >/dev/null 2>&1 && \
		gprof $(MAIN_EXECUTABLE) gmon.out > $(BUILD_DIR)/profile_report.txt && \
		echo "Profile report generated: $(BUILD_DIR)/profile_report.txt" || \
		echo "gprof not found, profiling data not analyzed"

# Code coverage (requires GCC with --coverage support)
.PHONY: coverage
coverage: CXXFLAGS += --coverage -fno-inline
coverage: LDFLAGS += --coverage
coverage: clean $(MAIN_EXECUTABLE)
	@echo "Running tests with code coverage..."
	$(MAIN_EXECUTABLE)
	@command -v gcov >/dev/null 2>&1 && command -v lcov >/dev/null 2>&1 && \
		lcov --directory $(OBJ_DIR) --capture --output-file $(BUILD_DIR)/coverage.info && \
		lcov --remove $(BUILD_DIR)/coverage.info '/usr/*' --output-file $(BUILD_DIR)/coverage.info.cleaned && \
		command -v genhtml >/dev/null 2>&1 && \
		genhtml -o $(BUILD_DIR)/coverage $(BUILD_DIR)/coverage.info.cleaned && \
		echo "Coverage report generated: $(BUILD_DIR)/coverage/index.html" || \
		echo "Coverage tools not found, generating gcov reports..." && \
		find $(OBJ_DIR) -name "*.gcno" -exec gcov {} \; && \
		mv *.gcov $(BUILD_DIR)/ 2>/dev/null || true

# Installation
.PHONY: install
install: $(MAIN_EXECUTABLE)
	@echo "Installing test executable..."
	install -d $(DESTDIR)/usr/local/bin
	install -m 755 $(MAIN_EXECUTABLE) $(DESTDIR)/usr/local/bin/

# Packaging
.PHONY: package
package: $(MAIN_EXECUTABLE)
	@echo "Creating package..."
	mkdir -p $(BUILD_DIR)/package/usr/local/bin
	cp $(MAIN_EXECUTABLE) $(BUILD_DIR)/package/usr/local/bin/
	tar -czf $(BUILD_DIR)/$(PROJECT_NAME)-$(VERSION).tar.gz -C $(BUILD_DIR)/package .

# Clean targets
.PHONY: clean
clean:
	@echo "Cleaning build files..."
	rm -rf $(BUILD_DIR)
	rm -f *.gcov gmon.out

.PHONY: distclean
distclean: clean
	@echo "Cleaning all generated files..."
	rm -f *~ *.tmp

# Help
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  all               - Build all test executables (default)"
	@echo "  test              - Run all tests"
	@echo "  test-verbose      - Run tests with verbose output"
	@echo "  test-probe        - Run device probe tests only"
	@echo "  test-data-reading - Run sensor data reading tests only"
	@echo "  test-error-handling - Run error handling tests only"
	@echo "  test-xml          - Run tests with XML output"
	@echo "  static-analysis   - Run cppcheck static analysis"
	@echo "  format-check      - Check code formatting"
	@echo "  format            - Format code with clang-format"
	@echo "  memcheck          - Run tests with Valgrind memory checking"
	@echo "  profile           - Run tests with profiling"
	@echo "  coverage          - Generate code coverage report"
	@echo "  install           - Install test executable"
	@echo "  package           - Create distribution package"
	@echo "  clean             - Remove build files"
	@echo "  distclean         - Remove all generated files"
	@echo "  check-deps        - Check build dependencies"
	@echo "  help              - Show this help message"

# Debug information
.PHONY: debug-info
debug-info:
	@echo "Build configuration:"
	@echo "  CXX: $(CXX)"
	@echo "  CXXFLAGS: $(ALL_CXXFLAGS)"
	@echo "  LDFLAGS: $(ALL_LDFLAGS)"
	@echo "  Sources: $(words $(MOCK_SOURCES) $(UTILS_SOURCES) $(FIXTURES_SOURCES) $(UNIT_SOURCES)) files"
	@echo "  Objects: $(words $(ALL_OBJECTS)) files"

# Dependency tracking (optional, for incremental builds)
-include $(ALL_OBJECTS:.o=.d)

%.d: %.cpp
	@set -e; rm -f $@; \
	$(CXX) -MM $(ALL_CXXFLAGS) $< > $@.$$$$; \
	sed 's,\($*\)\.o[ :]*,\1.o $@ : ,g' < $@.$$$$ > $@; \
	rm -f $@.$$$$

# CI/CD support
.PHONY: ci-build
ci-build: check-deps all test-xml static-analysis

.PHONY: ci-test
ci-test: test-xml memcheck

# Make sure intermediate files are not deleted
.PRECIOUS: $(OBJ_DIR)/%.o $(BUILD_DIR)/%.d

# Default goal
.DEFAULT_GOAL := all