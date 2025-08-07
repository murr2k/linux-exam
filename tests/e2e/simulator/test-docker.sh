#!/bin/bash

# Test script to verify Docker compatibility

set -e

echo "Building Docker test image..."
docker build -f Dockerfile.test -t mpu6050-simulator-test .

echo "Running simulator tests in Docker..."
docker run --rm mpu6050-simulator-test

echo "Docker tests completed successfully!"