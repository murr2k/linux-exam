/**
 * @file test_mpu6050.cpp
 * @brief Comprehensive unit tests for MPU-6050 kernel driver
 * 
 * This file contains extensive unit tests covering all aspects of the MPU-6050
 * kernel driver including initialization, data reading, error handling, and
 * edge cases. Tests are designed to run without actual hardware using mocks.
 */

#include <gtest/gtest.h>
#include <gmock/gmock.h>
#include "../mocks/mock_i2c.h"
#include "../utils/test_helpers.h"
#include "../fixtures/sensor_data.h"

// Include the driver header (would normally be included)
// For testing, we'll define the interface we expect the driver to provide
extern "C" {
    // Driver function prototypes (these would normally be in a header)
    int mpu6050_probe(struct i2c_client* client);
    void mpu6050_remove(struct i2c_client* client);
    int mpu6050_init_device(struct i2c_client* client);
    int mpu6050_read_sensor_data(struct i2c_client* client, s16* accel_x, s16* accel_y, s16* accel_z,
                                s16* gyro_x, s16* gyro_y, s16* gyro_z, s16* temp);
    int mpu6050_set_power_mode(struct i2c_client* client, bool power_on);
    int mpu6050_configure_ranges(struct i2c_client* client, int accel_range, int gyro_range);
    int mpu6050_calibrate(struct i2c_client* client);
    int mpu6050_self_test(struct i2c_client* client);
    bool mpu6050_device_present(struct i2c_client* client);
}

using ::testing::_;
using ::testing::Return;
using ::testing::InSequence;
using ::testing::StrictMock;
using ::testing::NiceMock;
using ::testing::AtLeast;
using ::testing::Exactly;

/**
 * @class MPU6050DriverTest
 * @brief Test fixture for MPU-6050 driver tests
 * 
 * Provides common setup and teardown for all driver tests,
 * including mock I2C interface configuration and test client setup.
 */
class MPU6050DriverTest : public ::testing::Test {
protected:
    void SetUp() override {
        // Reset mock state
        MockI2CInterface::getInstance().clearRegisterValues();
        MockI2CInterface::getInstance().resetStatistics();
        MockI2CInterface::getInstance().setDefaultBehavior();
        MockI2CInterface::getInstance().setupMPU6050Defaults();
        
        // Set up test I2C client
        test_client_.addr = 0x68; // Standard MPU-6050 address
        test_client_.adapter = &test_adapter_;
        test_client_.dev = &test_device_;
        strcpy(test_client_.name, "mpu6050");
        
        // Set up test adapter
        test_adapter_.nr = 1;
        test_adapter_.name = "test-i2c-adapter";
        
        // Set up test device
        test_device_.init_name = "mpu6050-test";
    }
    
    void TearDown() override {
        // Cleanup after each test
        MockI2CInterface::getInstance().clearRegisterValues();
        MockI2CInterface::getInstance().resetStatistics();
    }
    
    // Test objects
    struct i2c_client test_client_{};
    struct i2c_adapter test_adapter_{};
    struct device test_device_{};
    
    // Helper methods
    void setupSuccessfulProbe() {
        SETUP_I2C_SUCCESS();
        MockI2CInterface::getInstance().simulateDevicePresent(true);
    }
    
    void setupFailedProbe() {
        SETUP_I2C_DEVICE_NOT_FOUND();
    }
    
    void setupValidSensorData() {
        MockI2CInterface::getInstance().simulateSensorData(
            1000, 2000, 16384,  // Accelerometer (X, Y, Z) - Z shows 1g
            100, 200, 300,      // Gyroscope (X, Y, Z)
            8000                // Temperature
        );
    }
};

// =============================================================================
// Device Probe and Initialization Tests
// =============================================================================

TEST_F(MPU6050DriverTest, ProbeDeviceSuccess) {
    setupSuccessfulProbe();
    
    EXPECT_CALL(MockI2CInterface::getInstance(), 
                i2c_smbus_read_byte_data(&test_client_, MPU6050_Registers::WHO_AM_I))
        .Times(1)
        .WillOnce(Return(MPU6050_Registers::WHO_AM_I_VALUE));
    
    int result = mpu6050_probe(&test_client_);
    
    EXPECT_EQ(result, 0);
    EXPECT_GT(MockI2CInterface::getInstance().getReadCount(), 0);
}

TEST_F(MPU6050DriverTest, ProbeDeviceNotFound) {
    setupFailedProbe();
    
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_read_byte_data(&test_client_, MPU6050_Registers::WHO_AM_I))
        .Times(1)
        .WillOnce(Return(-ENODEV));
    
    int result = mpu6050_probe(&test_client_);
    
    EXPECT_EQ(result, -ENODEV);
}

TEST_F(MPU6050DriverTest, ProbeDeviceWrongId) {
    setupSuccessfulProbe();
    
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_read_byte_data(&test_client_, MPU6050_Registers::WHO_AM_I))
        .Times(1)
        .WillOnce(Return(0x00)); // Wrong device ID
    
    int result = mpu6050_probe(&test_client_);
    
    EXPECT_NE(result, 0); // Should fail
}

TEST_F(MPU6050DriverTest, InitializeDeviceSuccess) {
    setupSuccessfulProbe();
    
    // Expect initialization sequence
    InSequence seq;
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_write_byte_data(&test_client_, MPU6050_Registers::PWR_MGMT_1, 
                                        MPU6050_Registers::PWR_MGMT_1_RESET))
        .Times(1);
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_write_byte_data(&test_client_, MPU6050_Registers::PWR_MGMT_1,
                                        MPU6050_Registers::PWR_MGMT_1_NORMAL))
        .Times(1);
    
    int result = mpu6050_init_device(&test_client_);
    
    EXPECT_EQ(result, 0);
    EXPECT_GT(MockI2CInterface::getInstance().getWriteCount(), 0);
}

TEST_F(MPU6050DriverTest, InitializeDeviceI2CError) {
    SETUP_I2C_ERROR(EIO);
    
    int result = mpu6050_init_device(&test_client_);
    
    EXPECT_EQ(result, -EIO);
}

// =============================================================================
// Sensor Data Reading Tests
// =============================================================================

TEST_F(MPU6050DriverTest, ReadSensorDataSuccess) {
    setupSuccessfulProbe();
    setupValidSensorData();
    
    s16 accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, temp;
    
    // Expect block read of all sensor data
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_read_i2c_block_data(&test_client_, MPU6050_Registers::ACCEL_XOUT_H, 14, _))
        .Times(1)
        .WillOnce(Return(14)); // Success: 14 bytes read
    
    int result = mpu6050_read_sensor_data(&test_client_, &accel_x, &accel_y, &accel_z,
                                         &gyro_x, &gyro_y, &gyro_z, &temp);
    
    EXPECT_EQ(result, 0);
    EXPECT_EQ(accel_x, 1000);
    EXPECT_EQ(accel_y, 2000);
    EXPECT_EQ(accel_z, 16384); // 1g in ±2g range
    EXPECT_EQ(gyro_x, 100);
    EXPECT_EQ(gyro_y, 200);
    EXPECT_EQ(gyro_z, 300);
    EXPECT_EQ(temp, 8000);
}

TEST_F(MPU6050DriverTest, ReadSensorDataPartialFailure) {
    setupSuccessfulProbe();
    
    s16 accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, temp;
    
    // Simulate partial read failure
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_read_i2c_block_data(&test_client_, MPU6050_Registers::ACCEL_XOUT_H, 14, _))
        .Times(1)
        .WillOnce(Return(7)); // Only read 7 bytes instead of 14
    
    int result = mpu6050_read_sensor_data(&test_client_, &accel_x, &accel_y, &accel_z,
                                         &gyro_x, &gyro_y, &gyro_z, &temp);
    
    EXPECT_NE(result, 0); // Should indicate failure
}

TEST_F(MPU6050DriverTest, ReadSensorDataI2CTimeout) {
    SETUP_I2C_ERROR(ETIMEDOUT);
    
    s16 accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, temp;
    
    int result = mpu6050_read_sensor_data(&test_client_, &accel_x, &accel_y, &accel_z,
                                         &gyro_x, &gyro_y, &gyro_z, &temp);
    
    EXPECT_EQ(result, -ETIMEDOUT);
}

TEST_F(MPU6050DriverTest, ReadSensorDataWithNoise) {
    setupSuccessfulProbe();
    setupValidSensorData();
    
    // Enable noise simulation
    MockI2CInterface::getInstance().simulateNoiseInReads(true, 0.1);
    
    s16 accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, temp;
    
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_read_i2c_block_data(&test_client_, MPU6050_Registers::ACCEL_XOUT_H, 14, _))
        .Times(1)
        .WillOnce(Return(14));
    
    int result = mpu6050_read_sensor_data(&test_client_, &accel_x, &accel_y, &accel_z,
                                         &gyro_x, &gyro_y, &gyro_z, &temp);
    
    EXPECT_EQ(result, 0);
    // Values should be close to expected but may have noise
    EXPECT_NEAR(accel_x, 1000, 100);
    EXPECT_NEAR(accel_y, 2000, 100);
    EXPECT_NEAR(accel_z, 16384, 100);
}

// =============================================================================
// Power Management Tests
// =============================================================================

TEST_F(MPU6050DriverTest, SetPowerModeOn) {
    setupSuccessfulProbe();
    
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_write_byte_data(&test_client_, MPU6050_Registers::PWR_MGMT_1, 0x00))
        .Times(1)
        .WillOnce(Return(0));
    
    int result = mpu6050_set_power_mode(&test_client_, true);
    
    EXPECT_EQ(result, 0);
}

TEST_F(MPU6050DriverTest, SetPowerModeOff) {
    setupSuccessfulProbe();
    
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_write_byte_data(&test_client_, MPU6050_Registers::PWR_MGMT_1, 0x40))
        .Times(1)
        .WillOnce(Return(0));
    
    int result = mpu6050_set_power_mode(&test_client_, false);
    
    EXPECT_EQ(result, 0);
}

// =============================================================================
// Configuration Tests
// =============================================================================

TEST_F(MPU6050DriverTest, ConfigureAccelerometerRange2G) {
    setupSuccessfulProbe();
    
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_write_byte_data(&test_client_, MPU6050_Registers::ACCEL_CONFIG, 0x00))
        .Times(1)
        .WillOnce(Return(0));
    
    int result = mpu6050_configure_ranges(&test_client_, 2, 250); // ±2g, ±250°/s
    
    EXPECT_EQ(result, 0);
}

TEST_F(MPU6050DriverTest, ConfigureAccelerometerRange16G) {
    setupSuccessfulProbe();
    
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_write_byte_data(&test_client_, MPU6050_Registers::ACCEL_CONFIG, 0x18))
        .Times(1)
        .WillOnce(Return(0));
    
    int result = mpu6050_configure_ranges(&test_client_, 16, 2000); // ±16g, ±2000°/s
    
    EXPECT_EQ(result, 0);
}

TEST_F(MPU6050DriverTest, ConfigureInvalidRange) {
    setupSuccessfulProbe();
    
    int result = mpu6050_configure_ranges(&test_client_, 32, 250); // Invalid range
    
    EXPECT_EQ(result, -EINVAL);
}

// =============================================================================
// Calibration Tests
// =============================================================================

TEST_F(MPU6050DriverTest, CalibrateDeviceSuccess) {
    setupSuccessfulProbe();
    MockI2CInterface::getInstance().simulateCalibrationData();
    
    // Expect multiple reads during calibration process
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_read_i2c_block_data(&test_client_, MPU6050_Registers::ACCEL_XOUT_H, 14, _))
        .Times(AtLeast(10)) // Multiple samples for averaging
        .WillRepeatedly(Return(14));
    
    int result = mpu6050_calibrate(&test_client_);
    
    EXPECT_EQ(result, 0);
}

TEST_F(MPU6050DriverTest, CalibrateDeviceTimeout) {
    setupSuccessfulProbe();
    
    // Simulate very noisy data that won't converge
    MockI2CInterface::getInstance().simulateNoiseInReads(true, 0.9);
    
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_read_i2c_block_data(&test_client_, MPU6050_Registers::ACCEL_XOUT_H, 14, _))
        .Times(AtLeast(100)) // Many attempts before timeout
        .WillRepeatedly(Return(14));
    
    int result = mpu6050_calibrate(&test_client_);
    
    EXPECT_EQ(result, -ETIMEDOUT);
}

// =============================================================================
// Self-Test Tests
// =============================================================================

TEST_F(MPU6050DriverTest, SelfTestSuccess) {
    setupSuccessfulProbe();
    
    // Set up expected self-test sequence
    InSequence seq;
    
    // Read baseline values
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_read_i2c_block_data(&test_client_, MPU6050_Registers::ACCEL_XOUT_H, 14, _))
        .Times(1)
        .WillOnce(Return(14));
    
    // Enable self-test
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_write_byte_data(&test_client_, MPU6050_Registers::ACCEL_CONFIG, 0xE0))
        .Times(1)
        .WillOnce(Return(0));
    
    // Read self-test values
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_read_i2c_block_data(&test_client_, MPU6050_Registers::ACCEL_XOUT_H, 14, _))
        .Times(1)
        .WillOnce(Return(14));
    
    // Disable self-test
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_write_byte_data(&test_client_, MPU6050_Registers::ACCEL_CONFIG, 0x00))
        .Times(1)
        .WillOnce(Return(0));
    
    int result = mpu6050_self_test(&test_client_);
    
    EXPECT_EQ(result, 0);
}

// =============================================================================
// Error Handling and Edge Cases
// =============================================================================

TEST_F(MPU6050DriverTest, HandleNullPointers) {
    s16 accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, temp;
    
    // Test with null client
    int result = mpu6050_read_sensor_data(nullptr, &accel_x, &accel_y, &accel_z,
                                         &gyro_x, &gyro_y, &gyro_z, &temp);
    EXPECT_EQ(result, -EINVAL);
    
    // Test with null data pointers
    result = mpu6050_read_sensor_data(&test_client_, nullptr, &accel_y, &accel_z,
                                     &gyro_x, &gyro_y, &gyro_z, &temp);
    EXPECT_EQ(result, -EINVAL);
}

TEST_F(MPU6050DriverTest, HandleI2CBusyError) {
    SETUP_I2C_ERROR(EBUSY);
    
    int result = mpu6050_init_device(&test_client_);
    
    EXPECT_EQ(result, -EBUSY);
}

TEST_F(MPU6050DriverTest, HandleRepeatedI2CErrors) {
    setupSuccessfulProbe();
    
    // Inject errors with 50% probability
    MockI2CInterface::getInstance().enableErrorInjection(true);
    MockI2CInterface::getInstance().setErrorInjectionRate(0.5);
    MockI2CInterface::getInstance().simulateI2CError(EIO);
    
    s16 accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, temp;
    
    // Multiple attempts should eventually succeed or fail consistently
    int success_count = 0;
    int attempts = 100;
    
    for (int i = 0; i < attempts; i++) {
        int result = mpu6050_read_sensor_data(&test_client_, &accel_x, &accel_y, &accel_z,
                                             &gyro_x, &gyro_y, &gyro_z, &temp);
        if (result == 0) {
            success_count++;
        }
    }
    
    // With 50% error rate, we should have roughly 50% success
    EXPECT_GT(success_count, attempts * 0.3);
    EXPECT_LT(success_count, attempts * 0.7);
}

// =============================================================================
// Device Detection Tests
// =============================================================================

TEST_F(MPU6050DriverTest, DevicePresentDetection) {
    setupSuccessfulProbe();
    
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_read_byte_data(&test_client_, MPU6050_Registers::WHO_AM_I))
        .Times(1)
        .WillOnce(Return(MPU6050_Registers::WHO_AM_I_VALUE));
    
    bool present = mpu6050_device_present(&test_client_);
    
    EXPECT_TRUE(present);
}

TEST_F(MPU6050DriverTest, DeviceNotPresentDetection) {
    setupFailedProbe();
    
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_read_byte_data(&test_client_, MPU6050_Registers::WHO_AM_I))
        .Times(1)
        .WillOnce(Return(-ENODEV));
    
    bool present = mpu6050_device_present(&test_client_);
    
    EXPECT_FALSE(present);
}

// =============================================================================
// Performance and Stress Tests
// =============================================================================

TEST_F(MPU6050DriverTest, HighFrequencyDataReading) {
    setupSuccessfulProbe();
    setupValidSensorData();
    
    s16 accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, temp;
    const int iterations = 1000;
    
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_read_i2c_block_data(&test_client_, MPU6050_Registers::ACCEL_XOUT_H, 14, _))
        .Times(iterations)
        .WillRepeatedly(Return(14));
    
    auto start = std::chrono::high_resolution_clock::now();
    
    for (int i = 0; i < iterations; i++) {
        int result = mpu6050_read_sensor_data(&test_client_, &accel_x, &accel_y, &accel_z,
                                             &gyro_x, &gyro_y, &gyro_z, &temp);
        EXPECT_EQ(result, 0);
    }
    
    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
    
    // Each read should complete in reasonable time (< 1ms average)
    EXPECT_LT(duration.count() / iterations, 1000);
}

TEST_F(MPU6050DriverTest, ConcurrentOperations) {
    setupSuccessfulProbe();
    setupValidSensorData();
    
    // Simulate concurrent reads (this would be more complex in real kernel environment)
    std::vector<std::thread> threads;
    std::atomic<int> success_count{0};
    std::atomic<int> error_count{0};
    
    const int num_threads = 10;
    const int reads_per_thread = 100;
    
    for (int t = 0; t < num_threads; t++) {
        threads.emplace_back([&]() {
            s16 accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, temp;
            
            for (int i = 0; i < reads_per_thread; i++) {
                int result = mpu6050_read_sensor_data(&test_client_, &accel_x, &accel_y, &accel_z,
                                                     &gyro_x, &gyro_y, &gyro_z, &temp);
                if (result == 0) {
                    success_count++;
                } else {
                    error_count++;
                }
            }
        });
    }
    
    for (auto& thread : threads) {
        thread.join();
    }
    
    // Most operations should succeed even under concurrent load
    EXPECT_GT(success_count.load(), num_threads * reads_per_thread * 0.8);
}

// =============================================================================
// Test Suite Information
// =============================================================================

// This would typically be in a separate file, but included here for completeness
class MPU6050TestInfo : public ::testing::Test {
public:
    static void PrintTestCoverage() {
        std::cout << "\n=== MPU-6050 Driver Test Coverage ===" << std::endl;
        std::cout << "✓ Device probe and identification" << std::endl;
        std::cout << "✓ Device initialization and reset" << std::endl;
        std::cout << "✓ Sensor data reading (accelerometer, gyroscope, temperature)" << std::endl;
        std::cout << "✓ Power management" << std::endl;
        std::cout << "✓ Range configuration" << std::endl;
        std::cout << "✓ Device calibration" << std::endl;
        std::cout << "✓ Self-test functionality" << std::endl;
        std::cout << "✓ Error handling and recovery" << std::endl;
        std::cout << "✓ Edge cases and invalid inputs" << std::endl;
        std::cout << "✓ Performance under load" << std::endl;
        std::cout << "✓ Concurrent operations" << std::endl;
        std::cout << "✓ I2C communication failures" << std::endl;
        std::cout << "====================================" << std::endl;
    }
};

TEST_F(MPU6050TestInfo, DisplayTestCoverage) {
    PrintTestCoverage();
}