/**
 * @file test_helpers.h
 * @brief Utility functions and helpers for MPU-6050 driver testing
 * 
 * This file provides common utility functions, test data generators,
 * and helper classes to simplify test development and reduce code
 * duplication across test files.
 */

#ifndef TEST_HELPERS_H
#define TEST_HELPERS_H

#include <gtest/gtest.h>
#include <vector>
#include <memory>
#include <random>
#include <chrono>
#include <thread>

extern "C" {
    typedef unsigned char u8;
    typedef unsigned short u16;
    typedef signed short s16;
    typedef int s32;
}

/**
 * @namespace TestHelpers
 * @brief Collection of utility functions for testing
 */
namespace TestHelpers {

    /**
     * @class SensorDataGenerator
     * @brief Generates realistic sensor data for testing
     */
    class SensorDataGenerator {
    public:
        struct SensorReading {
            s16 accel_x, accel_y, accel_z;
            s16 gyro_x, gyro_y, gyro_z;
            s16 temperature;
            u64 timestamp;
        };
        
        /**
         * @brief Generate a single realistic sensor reading
         * @param motion_type Type of motion to simulate
         * @return Generated sensor reading
         */
        static SensorReading generateReading(const std::string& motion_type = "stationary");
        
        /**
         * @brief Generate a sequence of sensor readings
         * @param count Number of readings to generate
         * @param motion_type Type of motion to simulate
         * @param noise_level Amount of noise to add (0.0 to 1.0)
         * @return Vector of sensor readings
         */
        static std::vector<SensorReading> generateSequence(
            int count, 
            const std::string& motion_type = "stationary",
            double noise_level = 0.0
        );
        
        /**
         * @brief Generate calibration data (device at rest, Z-axis up)
         * @return Calibration sensor reading
         */
        static SensorReading generateCalibrationData();
        
        /**
         * @brief Generate self-test response data
         * @param enable_self_test Whether self-test is enabled
         * @return Self-test sensor reading
         */
        static SensorReading generateSelfTestData(bool enable_self_test);
        
    private:
        static std::mt19937& getRandomGenerator();
        static s16 addNoise(s16 value, double noise_level);
    };
    
    /**
     * @class I2CTransactionRecorder
     * @brief Records I2C transactions for verification
     */
    class I2CTransactionRecorder {
    public:
        struct Transaction {
            enum Type { READ, WRITE, BLOCK_READ, BLOCK_WRITE };
            Type type;
            u8 register_addr;
            u8 value;
            std::vector<u8> block_data;
            std::chrono::steady_clock::time_point timestamp;
            int result;
        };
        
        static I2CTransactionRecorder& getInstance() {
            static I2CTransactionRecorder instance;
            return instance;
        }
        
        void recordRead(u8 reg, u8 value, int result);
        void recordWrite(u8 reg, u8 value, int result);
        void recordBlockRead(u8 reg, const std::vector<u8>& data, int result);
        void recordBlockWrite(u8 reg, const std::vector<u8>& data, int result);
        
        const std::vector<Transaction>& getTransactions() const { return transactions_; }
        void clear() { transactions_.clear(); }
        
        // Analysis methods
        int countReads() const;
        int countWrites() const;
        int countErrors() const;
        bool hasTransaction(Transaction::Type type, u8 reg) const;
        
    private:
        std::vector<Transaction> transactions_;
        I2CTransactionRecorder() = default;
    };
    
    /**
     * @class PerformanceTimer
     * @brief Simple performance timing utility
     */
    class PerformanceTimer {
    public:
        PerformanceTimer() : start_time_(std::chrono::high_resolution_clock::now()) {}
        
        void reset() { start_time_ = std::chrono::high_resolution_clock::now(); }
        
        double elapsedMs() const {
            auto now = std::chrono::high_resolution_clock::now();
            auto duration = std::chrono::duration_cast<std::chrono::microseconds>(now - start_time_);
            return duration.count() / 1000.0;
        }
        
        double elapsedUs() const {
            auto now = std::chrono::high_resolution_clock::now();
            auto duration = std::chrono::duration_cast<std::chrono::microseconds>(now - start_time_);
            return static_cast<double>(duration.count());
        }
        
    private:
        std::chrono::high_resolution_clock::time_point start_time_;
    };
    
    /**
     * @class MockDataValidator
     * @brief Validates sensor data against expected ranges
     */
    class MockDataValidator {
    public:
        struct ValidationRules {
            struct Range {
                s16 min, max;
                Range(s16 min_val, s16 max_val) : min(min_val), max(max_val) {}
            };
            
            Range accel_range;
            Range gyro_range;
            Range temp_range;
            
            ValidationRules() : 
                accel_range(-32768, 32767),
                gyro_range(-32768, 32767),
                temp_range(-4000, 8500) {}
        };
        
        static bool validateSensorReading(const SensorDataGenerator::SensorReading& reading,
                                        const ValidationRules& rules = ValidationRules());
        
        static bool validateAccelerometerData(s16 x, s16 y, s16 z, int range_g = 2);
        static bool validateGyroscopeData(s16 x, s16 y, s16 z, int range_dps = 250);
        static bool validateTemperatureData(s16 temp);
        
        // Specific validation for common scenarios
        static bool isDeviceStationary(const SensorDataGenerator::SensorReading& reading,
                                     double tolerance = 0.1);
        static bool isDeviceInFreefall(const SensorDataGenerator::SensorReading& reading,
                                     double tolerance = 0.2);
        static double calculateTiltAngle(s16 accel_x, s16 accel_y, s16 accel_z);
    };
    
    /**
     * @class TestEnvironmentSetup
     * @brief Manages test environment setup and cleanup
     */
    class TestEnvironmentSetup {
    public:
        static void setupMinimalI2C();
        static void setupFullI2CEnvironment();
        static void cleanupI2CEnvironment();
        
        static void enableDetailedLogging();
        static void disableDetailedLogging();
        
        static void setupPerformanceMonitoring();
        static void reportPerformanceMetrics();
    };
    
    // Utility functions
    
    /**
     * @brief Convert 16-bit value to high/low byte pair
     * @param value 16-bit value to split
     * @return Pair of (high_byte, low_byte)
     */
    inline std::pair<u8, u8> splitU16(u16 value) {
        return std::make_pair(
            static_cast<u8>((value >> 8) & 0xFF),
            static_cast<u8>(value & 0xFF)
        );
    }
    
    /**
     * @brief Combine high/low bytes into 16-bit value
     * @param high_byte High byte
     * @param low_byte Low byte
     * @return Combined 16-bit value
     */
    inline u16 combineBytes(u8 high_byte, u8 low_byte) {
        return (static_cast<u16>(high_byte) << 8) | static_cast<u16>(low_byte);
    }
    
    /**
     * @brief Convert raw accelerometer reading to g-force
     * @param raw_value Raw 16-bit reading
     * @param range_g Configured range in g (2, 4, 8, 16)
     * @return G-force value
     */
    inline double rawToGForce(s16 raw_value, int range_g = 2) {
        return (static_cast<double>(raw_value) * range_g) / 32768.0;
    }
    
    /**
     * @brief Convert raw gyroscope reading to degrees per second
     * @param raw_value Raw 16-bit reading
     * @param range_dps Configured range in degrees per second (250, 500, 1000, 2000)
     * @return Degrees per second value
     */
    inline double rawToDPS(s16 raw_value, int range_dps = 250) {
        return (static_cast<double>(raw_value) * range_dps) / 32768.0;
    }
    
    /**
     * @brief Convert raw temperature reading to Celsius
     * @param raw_value Raw 16-bit temperature reading
     * @return Temperature in Celsius
     */
    inline double rawToTemperature(s16 raw_value) {
        return (static_cast<double>(raw_value) / 340.0) + 36.53;
    }
    
    /**
     * @brief Sleep for specified milliseconds (for timing tests)
     * @param ms Milliseconds to sleep
     */
    inline void sleepMs(int ms) {
        std::this_thread::sleep_for(std::chrono::milliseconds(ms));
    }
    
    /**
     * @brief Generate random bytes for test data
     * @param count Number of bytes to generate
     * @return Vector of random bytes
     */
    std::vector<u8> generateRandomBytes(int count);
    
    /**
     * @brief Create a formatted test description
     * @param test_name Name of the test
     * @param description Description of what the test does
     * @return Formatted string for test output
     */
    std::string formatTestDescription(const std::string& test_name, 
                                    const std::string& description);
    
    /**
     * @brief Verify that all expected I2C transactions occurred
     * @param expected_reads Expected number of read operations
     * @param expected_writes Expected number of write operations
     * @return True if transaction counts match expectations
     */
    bool verifyTransactionCounts(int expected_reads, int expected_writes);
    
} // namespace TestHelpers

// Convenience macros for common test operations

#define EXPECT_VALID_SENSOR_DATA(x, y, z, range) \
    EXPECT_TRUE(TestHelpers::MockDataValidator::validateAccelerometerData(x, y, z, range))

#define EXPECT_DEVICE_STATIONARY(reading) \
    EXPECT_TRUE(TestHelpers::MockDataValidator::isDeviceStationary(reading))

#define EXPECT_TEMPERATURE_VALID(temp) \
    EXPECT_TRUE(TestHelpers::MockDataValidator::validateTemperatureData(temp))

#define TIME_OPERATION(operation) \
    do { \
        TestHelpers::PerformanceTimer timer; \
        operation; \
        double elapsed = timer.elapsedMs(); \
        std::cout << "Operation took " << elapsed << " ms" << std::endl; \
    } while(0)

#define EXPECT_OPERATION_TIME_UNDER(operation, max_ms) \
    do { \
        TestHelpers::PerformanceTimer timer; \
        operation; \
        double elapsed = timer.elapsedMs(); \
        EXPECT_LT(elapsed, max_ms) << "Operation took " << elapsed << " ms, expected < " << max_ms << " ms"; \
    } while(0)

// Test fixture macros

#define SETUP_MPU6050_TEST_FIXTURE() \
    protected: \
        void SetUp() override { \
            TestHelpers::TestEnvironmentSetup::setupFullI2CEnvironment(); \
        } \
        void TearDown() override { \
            TestHelpers::TestEnvironmentSetup::cleanupI2CEnvironment(); \
        }

#endif // TEST_HELPERS_H