/**
 * @file test_helpers.cpp
 * @brief Implementation of test helper utilities
 */

#include "test_helpers.h"
#include "../mocks/mock_i2c.h"
#include <algorithm>
#include <cmath>
#include <iostream>

namespace TestHelpers {

// =============================================================================
// SensorDataGenerator Implementation
// =============================================================================

std::mt19937& SensorDataGenerator::getRandomGenerator() {
    static std::random_device rd;
    static std::mt19937 gen(rd());
    return gen;
}

s16 SensorDataGenerator::addNoise(s16 value, double noise_level) {
    if (noise_level <= 0.0) return value;
    
    std::normal_distribution<> dis(0.0, noise_level * 1000.0);
    double noisy_value = value + dis(getRandomGenerator());
    return static_cast<s16>(std::max(-32768.0, std::min(32767.0, noisy_value)));
}

SensorDataGenerator::SensorReading SensorDataGenerator::generateReading(const std::string& motion_type) {
    SensorReading reading;
    reading.timestamp = std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
    
    if (motion_type == "stationary") {
        // Device at rest, Z-axis pointing up
        reading.accel_x = 0;
        reading.accel_y = 0;
        reading.accel_z = 16384; // 1g in ±2g range
        reading.gyro_x = 0;
        reading.gyro_y = 0;
        reading.gyro_z = 0;
        reading.temperature = 7000; // ~21°C
        
    } else if (motion_type == "rotating") {
        // Device rotating around various axes
        std::uniform_int_distribution<s16> accel_dis(-2000, 2000);
        std::uniform_int_distribution<s16> gyro_dis(-10000, 10000);
        
        reading.accel_x = accel_dis(getRandomGenerator());
        reading.accel_y = accel_dis(getRandomGenerator());
        reading.accel_z = 16384 + accel_dis(getRandomGenerator());
        reading.gyro_x = gyro_dis(getRandomGenerator());
        reading.gyro_y = gyro_dis(getRandomGenerator());
        reading.gyro_z = gyro_dis(getRandomGenerator());
        reading.temperature = 7000;
        
    } else if (motion_type == "linear_acceleration") {
        // Device experiencing linear acceleration
        std::uniform_int_distribution<s16> accel_dis(5000, 20000);
        
        reading.accel_x = accel_dis(getRandomGenerator());
        reading.accel_y = accel_dis(getRandomGenerator());
        reading.accel_z = 16384;
        reading.gyro_x = 0;
        reading.gyro_y = 0;
        reading.gyro_z = 0;
        reading.temperature = 7200; // Slightly warmer due to motion
        
    } else if (motion_type == "vibration") {
        // High-frequency vibration
        std::uniform_int_distribution<s16> vib_dis(-1000, 1000);
        
        reading.accel_x = vib_dis(getRandomGenerator());
        reading.accel_y = vib_dis(getRandomGenerator());
        reading.accel_z = 16384 + vib_dis(getRandomGenerator());
        reading.gyro_x = vib_dis(getRandomGenerator());
        reading.gyro_y = vib_dis(getRandomGenerator());
        reading.gyro_z = vib_dis(getRandomGenerator());
        reading.temperature = 7000;
        
    } else if (motion_type == "freefall") {
        // Device in freefall (all accelerometer readings near zero)
        std::uniform_int_distribution<s16> small_dis(-100, 100);
        
        reading.accel_x = small_dis(getRandomGenerator());
        reading.accel_y = small_dis(getRandomGenerator());
        reading.accel_z = small_dis(getRandomGenerator());
        reading.gyro_x = 0;
        reading.gyro_y = 0;
        reading.gyro_z = 0;
        reading.temperature = 7000;
        
    } else {
        // Default to stationary
        return generateReading("stationary");
    }
    
    return reading;
}

std::vector<SensorDataGenerator::SensorReading> SensorDataGenerator::generateSequence(
    int count, const std::string& motion_type, double noise_level) {
    
    std::vector<SensorReading> sequence;
    sequence.reserve(count);
    
    for (int i = 0; i < count; i++) {
        SensorReading reading = generateReading(motion_type);
        
        // Add noise if requested
        if (noise_level > 0.0) {
            reading.accel_x = addNoise(reading.accel_x, noise_level);
            reading.accel_y = addNoise(reading.accel_y, noise_level);
            reading.accel_z = addNoise(reading.accel_z, noise_level);
            reading.gyro_x = addNoise(reading.gyro_x, noise_level);
            reading.gyro_y = addNoise(reading.gyro_y, noise_level);
            reading.gyro_z = addNoise(reading.gyro_z, noise_level);
            reading.temperature = addNoise(reading.temperature, noise_level * 0.1);
        }
        
        sequence.push_back(reading);
        
        // Add small delay between readings to simulate realistic timing
        std::this_thread::sleep_for(std::chrono::microseconds(100));
    }
    
    return sequence;
}

SensorDataGenerator::SensorReading SensorDataGenerator::generateCalibrationData() {
    SensorReading reading;
    reading.timestamp = std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
    
    // Perfect calibration data - device flat, Z-axis up
    reading.accel_x = 0;
    reading.accel_y = 0;
    reading.accel_z = 16384; // Exactly 1g
    reading.gyro_x = 0;
    reading.gyro_y = 0;
    reading.gyro_z = 0;
    reading.temperature = 7000; // Room temperature
    
    return reading;
}

SensorDataGenerator::SensorReading SensorDataGenerator::generateSelfTestData(bool enable_self_test) {
    SensorReading reading;
    reading.timestamp = std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
    
    if (enable_self_test) {
        // Self-test enabled - readings should change significantly
        reading.accel_x = 8000;   // Significant change from normal
        reading.accel_y = 8000;
        reading.accel_z = 20000;
        reading.gyro_x = 15000;
        reading.gyro_y = 15000;
        reading.gyro_z = 15000;
        reading.temperature = 7000;
    } else {
        // Self-test disabled - normal readings
        reading.accel_x = 0;
        reading.accel_y = 0;
        reading.accel_z = 16384;
        reading.gyro_x = 0;
        reading.gyro_y = 0;
        reading.gyro_z = 0;
        reading.temperature = 7000;
    }
    
    return reading;
}

// =============================================================================
// I2CTransactionRecorder Implementation
// =============================================================================

void I2CTransactionRecorder::recordRead(u8 reg, u8 value, int result) {
    Transaction trans;
    trans.type = Transaction::READ;
    trans.register_addr = reg;
    trans.value = value;
    trans.timestamp = std::chrono::steady_clock::now();
    trans.result = result;
    transactions_.push_back(trans);
}

void I2CTransactionRecorder::recordWrite(u8 reg, u8 value, int result) {
    Transaction trans;
    trans.type = Transaction::WRITE;
    trans.register_addr = reg;
    trans.value = value;
    trans.timestamp = std::chrono::steady_clock::now();
    trans.result = result;
    transactions_.push_back(trans);
}

void I2CTransactionRecorder::recordBlockRead(u8 reg, const std::vector<u8>& data, int result) {
    Transaction trans;
    trans.type = Transaction::BLOCK_READ;
    trans.register_addr = reg;
    trans.block_data = data;
    trans.timestamp = std::chrono::steady_clock::now();
    trans.result = result;
    transactions_.push_back(trans);
}

void I2CTransactionRecorder::recordBlockWrite(u8 reg, const std::vector<u8>& data, int result) {
    Transaction trans;
    trans.type = Transaction::BLOCK_WRITE;
    trans.register_addr = reg;
    trans.block_data = data;
    trans.timestamp = std::chrono::steady_clock::now();
    trans.result = result;
    transactions_.push_back(trans);
}

int I2CTransactionRecorder::countReads() const {
    return std::count_if(transactions_.begin(), transactions_.end(),
        [](const Transaction& t) { return t.type == Transaction::READ || t.type == Transaction::BLOCK_READ; });
}

int I2CTransactionRecorder::countWrites() const {
    return std::count_if(transactions_.begin(), transactions_.end(),
        [](const Transaction& t) { return t.type == Transaction::WRITE || t.type == Transaction::BLOCK_WRITE; });
}

int I2CTransactionRecorder::countErrors() const {
    return std::count_if(transactions_.begin(), transactions_.end(),
        [](const Transaction& t) { return t.result < 0; });
}

bool I2CTransactionRecorder::hasTransaction(Transaction::Type type, u8 reg) const {
    return std::any_of(transactions_.begin(), transactions_.end(),
        [type, reg](const Transaction& t) { return t.type == type && t.register_addr == reg; });
}

// =============================================================================
// MockDataValidator Implementation
// =============================================================================

bool MockDataValidator::validateSensorReading(const SensorDataGenerator::SensorReading& reading,
                                             const ValidationRules& rules) {
    return (reading.accel_x >= rules.accel_range.min && reading.accel_x <= rules.accel_range.max) &&
           (reading.accel_y >= rules.accel_range.min && reading.accel_y <= rules.accel_range.max) &&
           (reading.accel_z >= rules.accel_range.min && reading.accel_z <= rules.accel_range.max) &&
           (reading.gyro_x >= rules.gyro_range.min && reading.gyro_x <= rules.gyro_range.max) &&
           (reading.gyro_y >= rules.gyro_range.min && reading.gyro_y <= rules.gyro_range.max) &&
           (reading.gyro_z >= rules.gyro_range.min && reading.gyro_z <= rules.gyro_range.max) &&
           (reading.temperature >= rules.temp_range.min && reading.temperature <= rules.temp_range.max);
}

bool MockDataValidator::validateAccelerometerData(s16 x, s16 y, s16 z, int range_g) {
    s16 max_value = (32767 * range_g) / 2;  // Theoretical maximum for the range
    s16 min_value = -max_value;
    
    return (x >= min_value && x <= max_value) &&
           (y >= min_value && y <= max_value) &&
           (z >= min_value && z <= max_value);
}

bool MockDataValidator::validateGyroscopeData(s16 x, s16 y, s16 z, int range_dps) {
    s16 max_value = (32767 * range_dps) / 250;  // Scale based on 250 dps base
    s16 min_value = -max_value;
    
    return (x >= min_value && x <= max_value) &&
           (y >= min_value && y <= max_value) &&
           (z >= min_value && z <= max_value);
}

bool MockDataValidator::validateTemperatureData(s16 temp) {
    // Valid temperature range: approximately -40°C to +85°C
    // Raw values: roughly -4760 to +8500
    return temp >= -5000 && temp <= 9000;
}

bool MockDataValidator::isDeviceStationary(const SensorDataGenerator::SensorReading& reading,
                                          double tolerance) {
    double accel_magnitude = std::sqrt(
        static_cast<double>(reading.accel_x * reading.accel_x) +
        static_cast<double>(reading.accel_y * reading.accel_y) +
        static_cast<double>(reading.accel_z * reading.accel_z)
    );
    
    double expected_1g = 16384.0; // 1g in ±2g range
    double gyro_magnitude = std::sqrt(
        static_cast<double>(reading.gyro_x * reading.gyro_x) +
        static_cast<double>(reading.gyro_y * reading.gyro_y) +
        static_cast<double>(reading.gyro_z * reading.gyro_z)
    );
    
    return (std::abs(accel_magnitude - expected_1g) < (expected_1g * tolerance)) &&
           (gyro_magnitude < (1000.0 * tolerance)); // Low gyro activity
}

bool MockDataValidator::isDeviceInFreefall(const SensorDataGenerator::SensorReading& reading,
                                          double tolerance) {
    double accel_magnitude = std::sqrt(
        static_cast<double>(reading.accel_x * reading.accel_x) +
        static_cast<double>(reading.accel_y * reading.accel_y) +
        static_cast<double>(reading.accel_z * reading.accel_z)
    );
    
    return accel_magnitude < (16384.0 * tolerance); // Near zero acceleration
}

double MockDataValidator::calculateTiltAngle(s16 accel_x, s16 accel_y, s16 accel_z) {
    // Calculate tilt angle from vertical (Z-axis)
    double magnitude = std::sqrt(
        static_cast<double>(accel_x * accel_x) +
        static_cast<double>(accel_y * accel_y) +
        static_cast<double>(accel_z * accel_z)
    );
    
    if (magnitude == 0.0) return 0.0;
    
    double cos_angle = static_cast<double>(accel_z) / magnitude;
    return std::acos(std::max(-1.0, std::min(1.0, cos_angle))) * 180.0 / M_PI;
}

// =============================================================================
// TestEnvironmentSetup Implementation
// =============================================================================

void TestEnvironmentSetup::setupMinimalI2C() {
    MockI2CInterface::getInstance().setDefaultBehavior();
    MockI2CInterface::getInstance().simulateDevicePresent(true);
    MockI2CInterface::getInstance().clearRegisterValues();
}

void TestEnvironmentSetup::setupFullI2CEnvironment() {
    setupMinimalI2C();
    MockI2CInterface::getInstance().setupMPU6050Defaults();
    MockI2CInterface::getInstance().resetStatistics();
    I2CTransactionRecorder::getInstance().clear();
}

void TestEnvironmentSetup::cleanupI2CEnvironment() {
    MockI2CInterface::getInstance().clearRegisterValues();
    MockI2CInterface::getInstance().resetStatistics();
    I2CTransactionRecorder::getInstance().clear();
}

void TestEnvironmentSetup::enableDetailedLogging() {
    // Would enable detailed logging in a real implementation
    std::cout << "Detailed logging enabled for test session" << std::endl;
}

void TestEnvironmentSetup::disableDetailedLogging() {
    // Would disable detailed logging in a real implementation
}

void TestEnvironmentSetup::setupPerformanceMonitoring() {
    // Reset performance counters
    MockI2CInterface::getInstance().resetStatistics();
}

void TestEnvironmentSetup::reportPerformanceMetrics() {
    auto& mock = MockI2CInterface::getInstance();
    std::cout << "\n=== Performance Metrics ===" << std::endl;
    std::cout << "Total I2C transfers: " << mock.getTransferCount() << std::endl;
    std::cout << "Total reads: " << mock.getReadCount() << std::endl;
    std::cout << "Total writes: " << mock.getWriteCount() << std::endl;
    
    auto& recorder = I2CTransactionRecorder::getInstance();
    std::cout << "Recorded transactions: " << recorder.getTransactions().size() << std::endl;
    std::cout << "Error count: " << recorder.countErrors() << std::endl;
    std::cout << "============================" << std::endl;
}

// =============================================================================
// Utility Functions Implementation
// =============================================================================

std::vector<u8> generateRandomBytes(int count) {
    std::vector<u8> bytes;
    bytes.reserve(count);
    
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<u8> dis(0, 255);
    
    for (int i = 0; i < count; i++) {
        bytes.push_back(dis(gen));
    }
    
    return bytes;
}

std::string formatTestDescription(const std::string& test_name, const std::string& description) {
    return "[" + test_name + "] " + description;
}

bool verifyTransactionCounts(int expected_reads, int expected_writes) {
    auto& recorder = I2CTransactionRecorder::getInstance();
    int actual_reads = recorder.countReads();
    int actual_writes = recorder.countWrites();
    
    bool success = (actual_reads == expected_reads) && (actual_writes == expected_writes);
    
    if (!success) {
        std::cout << "Transaction count mismatch:" << std::endl;
        std::cout << "  Expected reads: " << expected_reads << ", actual: " << actual_reads << std::endl;
        std::cout << "  Expected writes: " << expected_writes << ", actual: " << actual_writes << std::endl;
    }
    
    return success;
}

} // namespace TestHelpers