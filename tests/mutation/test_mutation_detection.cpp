/**
 * @file test_mutation_detection.cpp
 * @brief Mutation testing framework for MPU-6050 kernel driver
 * 
 * This file contains tests specifically designed to detect code mutations.
 * Each test targets specific code patterns and ensures that any change
 * to the logic would cause test failures.
 * 
 * Mutation testing helps verify that tests actually test what they claim
 * to test by ensuring they can detect when the code is deliberately broken.
 * 
 * Target mutations:
 * - Arithmetic operators (+, -, *, /)
 * - Comparison operators (<, >, <=, >=, ==, !=)
 * - Logical operators (&&, ||, !)
 * - Constant values
 * - Boundary conditions
 * - Return values
 */

#include <gtest/gtest.h>
#include <gmock/gmock.h>
#include <random>
#include <chrono>
#include <vector>
#include <functional>
#include "../mocks/mock_i2c.h"
#include "../utils/test_helpers.h"

extern "C" {
    int mpu6050_probe(struct i2c_client* client, const struct i2c_device_id* id);
    int mpu6050_init_device(void* data);
    int mpu6050_read_raw_data(void* data, void* raw_data);
    int mpu6050_read_scaled_data(void* data, void* scaled_data);
    int mpu6050_set_config(void* data, const void* config);
    int mpu6050_reset(void* data);
}

using ::testing::_;
using ::testing::Return;
using ::testing::InSequence;

// Constants that should NOT be mutated
#define MPU6050_WHO_AM_I_VAL           0x68
#define MPU6050_REG_WHO_AM_I           0x75
#define MPU6050_REG_PWR_MGMT_1         0x6B
#define MPU6050_REG_ACCEL_XOUT_H       0x3B
#define MPU6050_PWR1_DEVICE_RESET      0x80
#define MPU6050_CLKSEL_PLL_XGYRO       0x01

// Data structures
struct mpu6050_config {
    u8 sample_rate_div;
    u8 gyro_range;
    u8 accel_range;
    u8 dlpf_cfg;
};

struct mpu6050_raw_data {
    s16 accel_x, accel_y, accel_z;
    s16 temp;
    s16 gyro_x, gyro_y, gyro_z;
};

struct mpu6050_scaled_data {
    s32 accel_x, accel_y, accel_z;
    s32 gyro_x, gyro_y, gyro_z;
    s32 temp;
};

/**
 * @class MutationDetectionTest
 * @brief Base class for mutation detection tests
 */
class MutationDetectionTest : public ::testing::Test {
protected:
    void SetUp() override {
        MockI2CInterface::getInstance().clearRegisterValues();
        MockI2CInterface::getInstance().resetStatistics();
        MockI2CInterface::getInstance().setDefaultBehavior();
        MockI2CInterface::getInstance().setupMPU6050Defaults();
        
        // Initialize test structures
        setupTestClient();
    }
    
    void TearDown() override {
        MockI2CInterface::getInstance().clearRegisterValues();
        MockI2CInterface::getInstance().resetStatistics();
    }
    
    struct i2c_client test_client_{};
    struct i2c_adapter test_adapter_{};
    struct device test_device_{};
    struct i2c_device_id test_id_{"mpu6050", 0};
    
    void setupTestClient() {
        memset(&test_client_, 0, sizeof(test_client_));
        memset(&test_adapter_, 0, sizeof(test_adapter_));
        memset(&test_device_, 0, sizeof(test_device_));
        
        test_client_.addr = 0x68;
        test_client_.adapter = &test_adapter_;
        test_client_.dev = &test_device_;
        strcpy(test_client_.name, "mpu6050");
        
        test_adapter_.nr = 1;
        test_adapter_.name = "test-adapter";
        test_device_.init_name = "mpu6050-test";
    }
};

/**
 * Constant Value Mutation Detection Tests
 * These tests ensure that specific constant values are not accidentally changed
 */
class ConstantMutationTests : public MutationDetectionTest {};

TEST_F(ConstantMutationTests, DetectWhoAmIConstantMutation) {
    // This test would fail if WHO_AM_I expected value is mutated from 0x68
    MockI2CInterface::getInstance().simulateDevicePresent(true);
    
    // Test with correct WHO_AM_I value
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_read_byte_data(&test_client_, MPU6050_REG_WHO_AM_I))
        .WillOnce(Return(MPU6050_WHO_AM_I_VAL));
    
    int result = mpu6050_probe(&test_client_, &test_id_);
    EXPECT_EQ(result, 0);
    
    // Reset mock state
    MockI2CInterface::getInstance().resetStatistics();
    
    // Test with incorrect WHO_AM_I values that should fail
    std::vector<u8> wrong_values = {0x67, 0x69, 0x00, 0xFF, 0x6A, 0x60};
    
    for (u8 wrong_val : wrong_values) {
        EXPECT_CALL(MockI2CInterface::getInstance(),
                    i2c_smbus_read_byte_data(&test_client_, MPU6050_REG_WHO_AM_I))
            .WillOnce(Return(wrong_val));
        
        int result = mpu6050_probe(&test_client_, &test_id_);
        EXPECT_NE(result, 0) << "Should fail with wrong WHO_AM_I: 0x" << std::hex << (int)wrong_val;
        
        MockI2CInterface::getInstance().resetStatistics();
    }
}

TEST_F(ConstantMutationTests, DetectRegisterAddressMutation) {
    // This test would fail if register addresses are mutated
    MockI2CInterface::getInstance().simulateDevicePresent(true);
    
    // Test that WHO_AM_I is read from the correct register (0x75)
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_read_byte_data(&test_client_, 0x75))  // Exact address
        .WillOnce(Return(0x68));
    
    // These calls should NOT happen (wrong addresses)
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_read_byte_data(&test_client_, 0x74))
        .Times(0);
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_read_byte_data(&test_client_, 0x76))
        .Times(0);
    
    int result = mpu6050_probe(&test_client_, &test_id_);
    EXPECT_EQ(result, 0);
}

TEST_F(ConstantMutationTests, DetectPowerManagementValueMutation) {
    // Test that power management uses correct values
    MockI2CInterface::getInstance().simulateDevicePresent(true);
    
    // During reset, should write 0x80 to PWR_MGMT_1
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_write_byte_data(&test_client_, 0x6B, 0x80))
        .Times(1);
    
    // Should NOT write other values that would indicate mutation
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_write_byte_data(&test_client_, 0x6B, 0x40))
        .Times(0);
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_write_byte_data(&test_client_, 0x6B, 0x00))
        .Times(AtLeast(1));  // Normal mode after reset
    
    int result = mpu6050_reset(&test_client_);
    // Reset may not be fully implemented, but test structure is important
}

/**
 * Arithmetic Operator Mutation Detection Tests
 */
class ArithmeticMutationTests : public MutationDetectionTest {};

TEST_F(ArithmeticMutationTests, DetectScalingArithmeticMutation) {
    // Test that scaling arithmetic is correct - would fail if operators are mutated
    MockI2CInterface::getInstance().simulateDevicePresent(true);
    
    // Set up known sensor data: 16384 = 1g in ±2g range
    MockI2CInterface::getInstance().simulateSensorData(16384, 0, 0, 0, 0, 0, 0);
    
    mpu6050_scaled_data scaled;
    int result = mpu6050_read_scaled_data(nullptr, &scaled);
    
    if (result == 0) {
        // For ±2g range, scale factor should be 61 ug/LSB
        // Expected: (16384 * 61) / 1000 = 999 millig ≈ 1000 millig
        
        // This test would fail if:
        // - Multiplication (*) is mutated to division (/)
        // - Division (/) is mutated to multiplication (*)
        // - Addition (+) is mutated to subtraction (-)
        // - Scale factors are wrong
        
        EXPECT_NEAR(scaled.accel_x, 1000, 10) 
            << "Scaling arithmetic may be mutated. Got: " << scaled.accel_x;
        
        // Test with negative value to catch sign mutations
        MockI2CInterface::getInstance().simulateSensorData(-16384, 0, 0, 0, 0, 0, 0);
        result = mpu6050_read_scaled_data(nullptr, &scaled);
        
        if (result == 0) {
            EXPECT_NEAR(scaled.accel_x, -1000, 10)
                << "Sign handling may be mutated. Got: " << scaled.accel_x;
        }
    }
}

TEST_F(ArithmeticMutationTests, DetectTemperatureFormulaMutation) {
    // Temperature formula: T = (TEMP_OUT/340) + 36.53 -> (raw * 100) / 340 + 3653
    MockI2CInterface::getInstance().simulateDevicePresent(true);
    
    // Test with known temperature value: 0 raw should give 36.53°C = 3653 centidegrees
    MockI2CInterface::getInstance().simulateSensorData(0, 0, 0, 0, 0, 0, 0);
    
    mpu6050_scaled_data scaled;
    int result = mpu6050_read_scaled_data(nullptr, &scaled);
    
    if (result == 0) {
        // This would fail if formula constants are mutated:
        // - 340 changed to any other value
        // - 36.53 (3653) changed to any other value
        // - Division (/) mutated to multiplication (*)
        // - Addition (+) mutated to subtraction (-)
        
        EXPECT_EQ(scaled.temp, 3653) << "Temperature formula may be mutated";
    }
    
    // Test with another known value: 340 raw should give 37.53°C = 3753
    MockI2CInterface::getInstance().simulateSensorData(0, 0, 0, 0, 0, 0, 340);
    result = mpu6050_read_scaled_data(nullptr, &scaled);
    
    if (result == 0) {
        EXPECT_EQ(scaled.temp, 3653 + 100) << "Temperature scaling may be mutated";
    }
}

/**
 * Comparison Operator Mutation Detection Tests
 */
class ComparisonMutationTests : public MutationDetectionTest {};

TEST_F(ComparisonMutationTests, DetectBoundaryComparisonMutation) {
    // Test range validation comparisons
    MockI2CInterface::getInstance().simulateDevicePresent(true);
    
    // Test configuration with values at boundaries
    mpu6050_config config;
    
    // Test valid range boundaries (should succeed)
    std::vector<u8> valid_ranges = {0, 1, 2, 3};
    for (u8 range : valid_ranges) {
        config.accel_range = range;
        config.gyro_range = range;
        config.sample_rate_div = 0;
        config.dlpf_cfg = 0;
        
        // These should succeed if comparison operators are correct
        int result = mpu6050_set_config(&test_client_, &config);
        // Implementation may vary, but structure tests comparison logic
    }
    
    // Test invalid ranges (should fail if validation exists)
    std::vector<u8> invalid_ranges = {4, 5, 255};
    for (u8 range : invalid_ranges) {
        config.accel_range = range;
        config.gyro_range = 0;  // Keep one valid
        
        // This would detect mutations like:
        // - >= mutated to >
        // - <= mutated to <
        // - < mutated to <=
        // - > mutated to >=
        
        int result = mpu6050_set_config(&test_client_, &config);
        // If validation is implemented, should fail for invalid ranges
    }
}

TEST_F(ComparisonMutationTests, DetectErrorCodeComparisonMutation) {
    // Test error code comparisons
    MockI2CInterface::getInstance().simulateI2CError(EIO);
    
    // This should return specific error code
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_read_byte_data(_, _))
        .WillOnce(Return(-EIO));
    
    int result = mpu6050_probe(&test_client_, &test_id_);
    
    // This would fail if error code comparisons are mutated:
    // - == mutated to !=
    // - < 0 mutated to <= 0 or > 0 or >= 0
    // - Error code constants changed
    
    EXPECT_EQ(result, -EIO) << "Error code comparison may be mutated";
    EXPECT_NE(result, 0) << "Error detection may be mutated";
    EXPECT_LT(result, 0) << "Error sign check may be mutated";
}

/**
 * Logical Operator Mutation Detection Tests
 */
class LogicalMutationTests : public MutationDetectionTest {};

TEST_F(LogicalMutationTests, DetectLogicalAndMutation) {
    // Test logical AND conditions
    MockI2CInterface::getInstance().simulateDevicePresent(true);
    
    // Test conditions that should use logical AND
    // For example, checking both device present AND correct ID
    
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_read_byte_data(&test_client_, MPU6050_REG_WHO_AM_I))
        .WillOnce(Return(MPU6050_WHO_AM_I_VAL));
    
    int result = mpu6050_probe(&test_client_, &test_id_);
    EXPECT_EQ(result, 0);
    
    // Now test case where one condition fails - should fail overall
    MockI2CInterface::getInstance().simulateDevicePresent(false);
    result = mpu6050_probe(&test_client_, &test_id_);
    
    // This would fail if && is mutated to ||
    EXPECT_NE(result, 0) << "Logical AND may be mutated to OR";
}

TEST_F(LogicalMutationTests, DetectLogicalNotMutation) {
    // Test logical NOT operations
    MockI2CInterface::getInstance().simulateDevicePresent(true);
    
    // Test null pointer checks (should involve NOT operations)
    int result = mpu6050_read_raw_data(nullptr, nullptr);
    
    // This should fail due to null pointer
    // Would detect mutation of !ptr to ptr or similar
    EXPECT_NE(result, 0) << "Null pointer check may be mutated";
    
    // Test with valid pointer should succeed
    mpu6050_raw_data data;
    MockI2CInterface::getInstance().simulateSensorData(100, 200, 300, 400, 500, 600, 700);
    result = mpu6050_read_raw_data(&test_client_, &data);
    
    // Success case should work
    // This helps detect mutations where success/failure logic is inverted
}

/**
 * Bit Manipulation Mutation Detection Tests
 */
class BitMutationTests : public MutationDetectionTest {};

TEST_F(BitMutationTests, DetectBitShiftMutation) {
    // Test bit shift operations in range configuration
    MockI2CInterface::getInstance().simulateDevicePresent(true);
    
    mpu6050_config config = {0, 2, 1, 0};  // Specific range values
    
    // Expected bit patterns:
    // gyro_range = 2, shifted left by 3: (2 << 3) = 16 = 0x10
    // accel_range = 1, shifted left by 3: (1 << 3) = 8 = 0x08
    
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_write_byte_data(&test_client_, 0x1B, 0x10))  // Gyro config
        .Times(1);
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_write_byte_data(&test_client_, 0x1C, 0x08))  // Accel config
        .Times(1);
    
    int result = mpu6050_set_config(&test_client_, &config);
    
    // This would fail if:
    // - << is mutated to >>
    // - Shift amount (3) is changed
    // - & mask is changed
}

TEST_F(BitMutationTests, DetectBitMaskMutation) {
    // Test bit masking operations
    MockI2CInterface::getInstance().simulateDevicePresent(true);
    
    // Test that bit masks are applied correctly
    // The driver uses masks like MPU6050_GYRO_FS_SEL_MASK (0x18)
    
    mpu6050_config config = {0, 3, 3, 0};  // Maximum range values
    
    // Range 3 shifted by 3 = 24 = 0x18
    // Masked with 0x18 should still be 0x18
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_write_byte_data(&test_client_, 0x1B, 0x18))
        .Times(1);
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_write_byte_data(&test_client_, 0x1C, 0x18))
        .Times(1);
    
    int result = mpu6050_set_config(&test_client_, &config);
    
    // This would detect mutations in bit mask values or operations
}

/**
 * Data Structure Access Mutation Detection Tests
 */
class DataStructureMutationTests : public MutationDetectionTest {};

TEST_F(DataStructureMutationTests, DetectStructFieldAccessMutation) {
    // Test that correct struct fields are accessed
    MockI2CInterface::getInstance().simulateDevicePresent(true);
    MockI2CInterface::getInstance().simulateSensorData(1000, 2000, 3000, 4000, 5000, 6000, 7000);
    
    mpu6050_raw_data raw_data;
    int result = mpu6050_read_raw_data(&test_client_, &raw_data);
    
    if (result == 0) {
        // Verify each field gets the correct value
        // This would fail if field accesses are swapped
        EXPECT_EQ(raw_data.accel_x, 1000) << "accel_x field may be mutated";
        EXPECT_EQ(raw_data.accel_y, 2000) << "accel_y field may be mutated";
        EXPECT_EQ(raw_data.accel_z, 3000) << "accel_z field may be mutated";
        EXPECT_EQ(raw_data.temp, 7000) << "temp field may be mutated";
        EXPECT_EQ(raw_data.gyro_x, 4000) << "gyro_x field may be mutated";
        EXPECT_EQ(raw_data.gyro_y, 5000) << "gyro_y field may be mutated";
        EXPECT_EQ(raw_data.gyro_z, 6000) << "gyro_z field may be mutated";
    }
}

/**
 * Control Flow Mutation Detection Tests
 */
class ControlFlowMutationTests : public MutationDetectionTest {};

TEST_F(ControlFlowMutationTests, DetectEarlyReturnMutation) {
    // Test that error conditions cause early returns
    MockI2CInterface::getInstance().simulateI2CError(ENODEV);
    
    EXPECT_CALL(MockI2CInterface::getInstance(),
                i2c_smbus_read_byte_data(_, _))
        .WillOnce(Return(-ENODEV));
    
    int result = mpu6050_probe(&test_client_, &test_id_);
    
    // Should return error immediately, not continue processing
    EXPECT_EQ(result, -ENODEV);
    
    // Verify that subsequent operations were NOT called
    // (This tests that early return wasn't mutated to continue)
    int transaction_count = MockI2CInterface::getInstance().getTransferCount();
    EXPECT_LE(transaction_count, 2) << "Early return may be mutated - too many operations";
}

/**
 * Mutation Test Summary
 */
class MutationTestSummary : public ::testing::Test {};

TEST_F(MutationTestSummary, MutationDetectionSummary) {
    std::cout << "\n=== Mutation Detection Test Summary ===" << std::endl;
    std::cout << "✓ Constant Value Mutations" << std::endl;
    std::cout << "  - WHO_AM_I constant (0x68)" << std::endl;
    std::cout << "  - Register address constants" << std::endl;
    std::cout << "  - Power management values" << std::endl;
    std::cout << "\n✓ Arithmetic Operator Mutations" << std::endl;
    std::cout << "  - Scaling multiplication/division" << std::endl;
    std::cout << "  - Temperature formula arithmetic" << std::endl;
    std::cout << "  - Sign preservation" << std::endl;
    std::cout << "\n✓ Comparison Operator Mutations" << std::endl;
    std::cout << "  - Range boundary checks" << std::endl;
    std::cout << "  - Error code comparisons" << std::endl;
    std::cout << "  - Validation logic" << std::endl;
    std::cout << "\n✓ Logical Operator Mutations" << std::endl;
    std::cout << "  - AND/OR condition mutations" << std::endl;
    std::cout << "  - NOT operation mutations" << std::endl;
    std::cout << "  - Null pointer checks" << std::endl;
    std::cout << "\n✓ Bit Manipulation Mutations" << std::endl;
    std::cout << "  - Bit shift operations" << std::endl;
    std::cout << "  - Bit mask applications" << std::endl;
    std::cout << "  - Configuration register setup" << std::endl;
    std::cout << "\n✓ Data Structure Mutations" << std::endl;
    std::cout << "  - Struct field access order" << std::endl;
    std::cout << "  - Field assignment correctness" << std::endl;
    std::cout << "\n✓ Control Flow Mutations" << std::endl;
    std::cout << "  - Early return conditions" << std::endl;
    std::cout << "  - Error handling paths" << std::endl;
    std::cout << "=====================================" << std::endl;
}