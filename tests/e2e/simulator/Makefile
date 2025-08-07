# Makefile for I2C MPU-6050 Simulator
CC = gcc
CFLAGS = -Wall -Wextra -std=c99 -pthread -O2 -g
LDFLAGS = -lm -lpthread
INCLUDES = -I.

# Source files
LIB_SOURCES = i2c_simulator.c mpu6050_virtual.c
TEST_SOURCES = test_scenarios.c
MAIN_SOURCE = main.c

# Object files
LIB_OBJECTS = $(LIB_SOURCES:.c=.o)
TEST_OBJECTS = $(TEST_SOURCES:.c=.o)
MAIN_OBJECT = main.o

# Output files
LIB_TARGET = libi2csim.a
TEST_TARGET = simulator_test

# Default target
all: $(LIB_TARGET) $(TEST_TARGET)

# Library target
$(LIB_TARGET): $(LIB_OBJECTS)
	@echo "Creating static library $@"
	ar rcs $@ $^

# Test program target
$(TEST_TARGET): $(MAIN_OBJECT) $(TEST_OBJECTS) $(LIB_TARGET)
	@echo "Linking test program $@"
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

# Object file compilation
%.o: %.c simulator.h
	@echo "Compiling $<"
	$(CC) $(CFLAGS) $(INCLUDES) -c $< -o $@

# Test targets
test: $(TEST_TARGET)
	@echo "Running simulator tests..."
	./$(TEST_TARGET)

test-quick: $(TEST_TARGET)
	@echo "Running quick test suite..."
	./$(TEST_TARGET) -q

# Clean targets
clean:
	@echo "Cleaning build files..."
	rm -f *.o

distclean: clean
	@echo "Cleaning all generated files..."
	rm -f $(LIB_TARGET) $(TEST_TARGET)

.PHONY: all test test-quick clean distclean