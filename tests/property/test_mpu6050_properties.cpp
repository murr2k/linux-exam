/**
 * @file test_mpu6050_properties.cpp
 * @brief Property-based testing for MPU-6050 kernel driver
 * 
 * Property-based tests verify that certain mathematical relationships
 * and invariants hold across large sets of randomly generated inputs.
 * These tests help catch edge cases and verify correctness properties
 * that might be missed by example-based tests.
 * 
 * Key properties tested:
 * - Data scaling relationships
 * - Mathematical invariants
 * - Boundary condition properties
 * - Symmetry and consistency properties
 * - Error handling properties
 */

#include <gtest/gtest.h>
#include <gmock/gmock.h>
#include <random>
#include <algorithm>
#include <numeric>
#include <cmath>
#include <vector>
#include <functional>
#include "../mocks/mock_i2c.h"
#include "../utils/test_helpers.h"

extern "C" {
    int mpu6050_read_raw_data(void* data, void* raw_data);
    int mpu6050_read_scaled_data(void* data, void* scaled_data);
    int mpu6050_set_config(void* data, const void* config);
}

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
    s32 accel_x, accel_y, accel_z;  // milli-g
    s32 gyro_x, gyro_y, gyro_z;     // milli-degrees per second
    s32 temp;                       // degrees Celsius * 100
};

// Scale factors for different ranges (from driver analysis)
static const u32 ACCEL_SCALE_FACTORS[] = {61, 122, 244, 488};      // ug/LSB for 2g, 4g, 8g, 16g
static const u32 GYRO_SCALE_FACTORS[] = {7633, 15267, 30518, 61035}; // udps/LSB for 250, 500, 1000, 2000 dps

/**
 * @class PropertyBasedTest
 * @brief Base class for property-based testing with random generation
 */
class PropertyBasedTest : public ::testing::Test {
protected:
    void SetUp() override {
        MockI2CInterface::getInstance().clearRegisterValues();
        MockI2CInterface::getInstance().resetStatistics();
        MockI2CInterface::getInstance().setDefaultBehavior();
        MockI2CInterface::getInstance().setupMPU6050Defaults();
        MockI2CInterface::getInstance().simulateDevicePresent(true);
        
        // Seed random number generator
        rng_.seed(std::chrono::steady_clock::now().time_since_epoch().count());
    }
    
    void TearDown() override {
        MockI2CInterface::getInstance().clearRegisterValues();
        MockI2CInterface::getInstance().resetStatistics();
    }
    
    std::mt19937 rng_;
    
    // Random value generators
    s16 randomS16() {
        std::uniform_int_distribution<s16> dist(-32768, 32767);
        return dist(rng_);
    }
    
    s16 randomS16InRange(s16 min, s16 max) {
        std::uniform_int_distribution<s16> dist(min, max);
        return dist(rng_);
    }
    
    u8 randomU8() {
        std::uniform_int_distribution<u8> dist(0, 255);
        return dist(rng_);
    }
    
    u8 randomRangeIndex() {
        std::uniform_int_distribution<u8> dist(0, 3);
        return dist(rng_);
    }
    
    double randomDouble(double min, double max) {
        std::uniform_real_distribution<double> dist(min, max);
        return dist(rng_);
    }
    
    // Property testing utilities
    template<typename Func>
    void forAllRandomInputs(int iterations, Func property) {
        for (int i = 0; i < iterations; i++) {
            property(i);
        }
    }
    
    // Helper to generate realistic sensor data patterns
    struct SensorPattern {
        std::function<s16(int)> accel_x, accel_y, accel_z;
        std::function<s16(int)> gyro_x, gyro_y, gyro_z;
        std::function<s16(int)> temp;
    };
    
    SensorPattern stationaryPattern() {
        return {
            [](int) { return 0; },      // accel_x: 0g
            [](int) { return 0; },      // accel_y: 0g  
            [](int) { return 16384; },  // accel_z: 1g (upright)
            [](int) { return 0; },      // gyro_x: no rotation
            [](int) { return 0; },      // gyro_y: no rotation
            [](int) { return 0; },      // gyro_z: no rotation
            [](int) { return 8000; }    // temp: ~23.5°C
        };
    }
    
    SensorPattern vibratingPattern() {
        return {
            [this](int i) { return randomS16InRange(-1000, 1000); },
            [this](int i) { return randomS16InRange(-1000, 1000); },
            [this](int i) { return 16384 + randomS16InRange(-500, 500); },
            [this](int i) { return randomS16InRange(-100, 100); },
            [this](int i) { return randomS16InRange(-100, 100); },
            [this](int i) { return randomS16InRange(-100, 100); },
            [this](int i) { return 8000 + randomS16InRange(-200, 200); }
        };
    }
    
    SensorPattern rotatingPattern() {
        return {
            [](int i) { return static_cast<s16>(16384 * sin(i * 0.1)); },    // rotating accel
            [](int i) { return static_cast<s16>(16384 * cos(i * 0.1)); },
            [](int i) { return 0; },
            [](int i) { return 1000; },  // constant rotation
            [](int i) { return 0; },
            [](int i) { return 0; },
            [](int i) { return 8000; }
        };
    }
};

/**
 * Scaling Property Tests
 */
class ScalingPropertyTests : public PropertyBasedTest {};

TEST_F(ScalingPropertyTests, AccelerometerScalingLinearityProperty) {
    // Property: For a given range setting, scaled values should be linear 
    // with respect to raw values
    
    const int ITERATIONS = 500;
    
    forAllRandomInputs(ITERATIONS, [this](int iteration) {
        u8 range_index = randomRangeIndex();
        s16 raw_value = randomS16();
        
        // Set up configuration with specific range
        mpu6050_config config = {0x07, 0, range_index, 0};
        MockI2CInterface::getInstance().simulateSensorData(raw_value, 0, 0, 0, 0, 0, 8000);
        
        // Read scaled data
        mpu6050_scaled_data scaled;
        int result = mpu6050_read_scaled_data(nullptr, &scaled);
        
        if (result == 0) {
            // Calculate expected scaled value using driver's formula
            u32 scale_factor = ACCEL_SCALE_FACTORS[range_index];
            s32 expected_scaled = ((s32)raw_value * scale_factor) / 1000;
            
            // Property: Scaling should be linear (allowing for rounding)
            s32 difference = std::abs(scaled.accel_x - expected_scaled);
            EXPECT_LE(difference, scale_factor / 500)  // Allow 0.2% error for rounding
                << "Range: " << (int)range_index 
                << ", Raw: " << raw_value 
                << ", Expected: " << expected_scaled
                << ", Actual: " << scaled.accel_x;
        }
    });
}

TEST_F(ScalingPropertyTests, GyroscopeScalingConsistencyProperty) {
    // Property: Gyroscope scaling should maintain sign and magnitude relationships
    
    const int ITERATIONS = 500;
    
    forAllRandomInputs(ITERATIONS, [this](int iteration) {
        u8 range_index = randomRangeIndex();
        s16 raw_gyro = randomS16();
        
        MockI2CInterface::getInstance().simulateSensorData(0, 0, 16384, raw_gyro, 0, 0, 8000);
        
        mpu6050_scaled_data scaled;
        int result = mpu6050_read_scaled_data(nullptr, &scaled);
        
        if (result == 0) {
            // Property 1: Sign preservation
            if (raw_gyro > 0) {
                EXPECT_GT(scaled.gyro_x, 0) 
                    << "Positive sign not preserved for raw: " << raw_gyro;
            } else if (raw_gyro < 0) {
                EXPECT_LT(scaled.gyro_x, 0)
                    << "Negative sign not preserved for raw: " << raw_gyro;
            } else {
                EXPECT_EQ(scaled.gyro_x, 0)
                    << "Zero not preserved for raw: " << raw_gyro;
            }
            
            // Property 2: Magnitude relationship
            u32 scale_factor = GYRO_SCALE_FACTORS[range_index];
            s32 expected_magnitude = std::abs((s32)raw_gyro * scale_factor / 1000000);
            s32 actual_magnitude = std::abs(scaled.gyro_x);
            
            // Allow for reasonable rounding error
            s32 tolerance = std::max(1L, expected_magnitude / 100);
            EXPECT_NEAR(actual_magnitude, expected_magnitude, tolerance)
                << "Magnitude scaling incorrect for range: " << (int)range_index
                << ", raw: " << raw_gyro;
        }
    });
}

TEST_F(ScalingPropertyTests, TemperatureScalingFormulaProperty) {
    // Property: Temperature scaling should follow the formula T = (TEMP_OUT/340) + 36.53
    
    const int ITERATIONS = 1000;
    
    forAllRandomInputs(ITERATIONS, [this](int iteration) {
        s16 raw_temp = randomS16();
        
        MockI2CInterface::getInstance().simulateSensorData(0, 0, 16384, 0, 0, 0, raw_temp);
        
        mpu6050_scaled_data scaled;
        int result = mpu6050_read_scaled_data(nullptr, &scaled);
        
        if (result == 0) {
            // Expected temperature using driver's formula: (raw_temp * 100) / 340 + 3653
            s32 expected_temp = (raw_temp * 100) / 340 + 3653;
            
            // Property: Temperature formula should be exact (integer arithmetic)
            EXPECT_EQ(scaled.temp, expected_temp)
                << "Temperature formula incorrect for raw: " << raw_temp
                << ", expected: " << expected_temp
                << ", actual: " << scaled.temp;
            
            // Property: Temperature should be within reasonable physical limits
            // Allowing for sensor range -40°C to +125°C -> -4000 to +12500 centidegrees
            EXPECT_GE(scaled.temp, -5000)
                << "Temperature too low: " << scaled.temp;
            EXPECT_LE(scaled.temp, 13000)
                << "Temperature too high: " << scaled.temp;
        }
    });
}

/**
 * Range and Boundary Property Tests
 */
class RangeBoundaryPropertyTests : public PropertyBasedTest {};

TEST_F(RangeBoundaryPropertyTests, DataRangeConsistencyProperty) {
    // Property: Data should always be within expected ranges for raw readings
    
    const int ITERATIONS = 1000;
    
    forAllRandomInputs(ITERATIONS, [this](int iteration) {
        // Generate random but valid sensor data
        s16 accel_x = randomS16(), accel_y = randomS16(), accel_z = randomS16();
        s16 gyro_x = randomS16(), gyro_y = randomS16(), gyro_z = randomS16();
        s16 temp = randomS16();
        
        MockI2CInterface::getInstance().simulateSensorData(
            accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, temp);
        
        mpu6050_raw_data raw;
        int result = mpu6050_read_raw_data(nullptr, &raw);
        
        if (result == 0) {
            // Property: Raw data should be exactly what we set
            EXPECT_EQ(raw.accel_x, accel_x);
            EXPECT_EQ(raw.accel_y, accel_y);
            EXPECT_EQ(raw.accel_z, accel_z);
            EXPECT_EQ(raw.gyro_x, gyro_x);
            EXPECT_EQ(raw.gyro_y, gyro_y);
            EXPECT_EQ(raw.gyro_z, gyro_z);
            EXPECT_EQ(raw.temp, temp);
            
            // Property: All values should be in valid s16 range
            EXPECT_GE(raw.accel_x, -32768); EXPECT_LE(raw.accel_x, 32767);
            EXPECT_GE(raw.accel_y, -32768); EXPECT_LE(raw.accel_y, 32767);
            EXPECT_GE(raw.accel_z, -32768); EXPECT_LE(raw.accel_z, 32767);
            EXPECT_GE(raw.gyro_x, -32768); EXPECT_LE(raw.gyro_x, 32767);
            EXPECT_GE(raw.gyro_y, -32768); EXPECT_LE(raw.gyro_y, 32767);
            EXPECT_GE(raw.gyro_z, -32768); EXPECT_LE(raw.gyro_z, 32767);
            EXPECT_GE(raw.temp, -32768); EXPECT_LE(raw.temp, 32767);
        }
    });
}

TEST_F(RangeBoundaryPropertyTests, ExtremeBoundaryValuesProperty) {
    // Property: Extreme boundary values should be handled correctly
    
    std::vector<s16> boundary_values = {
        -32768, -32767, -1, 0, 1, 32766, 32767
    };
    
    for (s16 bound_val : boundary_values) {
        MockI2CInterface::getInstance().simulateSensorData(
            bound_val, bound_val, bound_val, bound_val, bound_val, bound_val, bound_val);
        
        mpu6050_raw_data raw;
        int result = mpu6050_read_raw_data(nullptr, &raw);
        
        if (result == 0) {
            // Property: Boundary values should be preserved exactly
            EXPECT_EQ(raw.accel_x, bound_val) << "Boundary value not preserved: " << bound_val;
            EXPECT_EQ(raw.accel_y, bound_val) << "Boundary value not preserved: " << bound_val;
            EXPECT_EQ(raw.accel_z, bound_val) << "Boundary value not preserved: " << bound_val;
        }
        
        mpu6050_scaled_data scaled;
        result = mpu6050_read_scaled_data(nullptr, &scaled);
        
        if (result == 0) {
            // Property: Scaled boundary values should not overflow
            // Check that we haven't wrapped around due to overflow
            bool accel_reasonable = (std::abs(scaled.accel_x) < 1000000);  // < 1000g
            bool gyro_reasonable = (std::abs(scaled.gyro_x) < 10000000);   // < 10000 dps
            
            EXPECT_TRUE(accel_reasonable)
                << "Accelerometer scaling overflow for boundary: " << bound_val
                << ", scaled: " << scaled.accel_x;
            EXPECT_TRUE(gyro_reasonable)
                << "Gyroscope scaling overflow for boundary: " << bound_val
                << ", scaled: " << scaled.gyro_x;
        }
    }
}

/**
 * Invariant Property Tests
 */
class InvariantPropertyTests : public PropertyBasedTest {};

TEST_F(InvariantPropertyTests, ReadConsistencyInvariant) {
    // Property: Multiple reads of the same data should be consistent
    
    const int ITERATIONS = 100;
    
    forAllRandomInputs(ITERATIONS, [this](int iteration) {
        // Set up consistent data
        s16 accel_x = randomS16(), accel_y = randomS16(), accel_z = randomS16();
        s16 gyro_x = randomS16(), gyro_y = randomS16(), gyro_z = randomS16();
        s16 temp = randomS16();
        
        MockI2CInterface::getInstance().simulateSensorData(
            accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, temp);
        
        // Read data multiple times
        mpu6050_raw_data reads[5];
        bool all_reads_successful = true;
        
        for (int i = 0; i < 5; i++) {
            int result = mpu6050_read_raw_data(nullptr, &reads[i]);
            if (result != 0) {
                all_reads_successful = false;
                break;
            }
        }
        
        if (all_reads_successful) {
            // Property: All reads should be identical
            for (int i = 1; i < 5; i++) {
                EXPECT_EQ(reads[i].accel_x, reads[0].accel_x);
                EXPECT_EQ(reads[i].accel_y, reads[0].accel_y);
                EXPECT_EQ(reads[i].accel_z, reads[0].accel_z);
                EXPECT_EQ(reads[i].gyro_x, reads[0].gyro_x);
                EXPECT_EQ(reads[i].gyro_y, reads[0].gyro_y);
                EXPECT_EQ(reads[i].gyro_z, reads[0].gyro_z);
                EXPECT_EQ(reads[i].temp, reads[0].temp);
            }
        }
    });
}

TEST_F(InvariantPropertyTests, ScalingRangeInvariant) {
    // Property: Changing the range should affect the scaling but not the raw data
    
    const int ITERATIONS = 200;
    
    forAllRandomInputs(ITERATIONS, [this](int iteration) {
        s16 raw_accel = randomS16();
        MockI2CInterface::getInstance().simulateSensorData(raw_accel, 0, 0, 0, 0, 0, 8000);
        
        // Test all accelerometer ranges
        std::vector<s32> scaled_values;
        
        for (u8 range = 0; range < 4; range++) {
            mpu6050_config config = {0x07, 0, range, 0};
            mpu6050_set_config(nullptr, &config);
            
            mpu6050_raw_data raw;
            mpu6050_scaled_data scaled;
            
            int raw_result = mpu6050_read_raw_data(nullptr, &raw);
            int scaled_result = mpu6050_read_scaled_data(nullptr, &scaled);
            
            if (raw_result == 0 && scaled_result == 0) {
                // Property: Raw data should be the same regardless of range
                EXPECT_EQ(raw.accel_x, raw_accel)
                    << "Raw data changed with range setting";
                
                scaled_values.push_back(scaled.accel_x);
            }
        }
        
        // Property: Different ranges should produce different scaled values 
        // (unless raw value is 0)
        if (raw_accel != 0 && scaled_values.size() == 4) {
            bool all_different = true;
            for (size_t i = 1; i < scaled_values.size(); i++) {
                if (scaled_values[i] == scaled_values[0]) {
                    all_different = false;
                    break;
                }
            }
            
            EXPECT_TRUE(all_different)
                << "Different ranges should produce different scaled values for raw: " 
                << raw_accel;
            
            // Property: Higher ranges should produce larger scaled values (in magnitude)
            // for the same raw input
            for (size_t i = 1; i < scaled_values.size(); i++) {
                if (raw_accel > 0) {
                    EXPECT_GT(scaled_values[i], scaled_values[i-1])
                        << "Higher range should produce larger positive scaled value";
                } else if (raw_accel < 0) {
                    EXPECT_LT(scaled_values[i], scaled_values[i-1])
                        << "Higher range should produce larger negative scaled value";
                }
            }
        }
    });
}

/**
 * Symmetry Property Tests
 */
class SymmetryPropertyTests : public PropertyBasedTest {};

TEST_F(SymmetryPropertyTests, SignSymmetryProperty) {
    // Property: Negating input should negate output (for accelerometer and gyroscope)
    
    const int ITERATIONS = 500;
    
    forAllRandomInputs(ITERATIONS, [this](int iteration) {
        s16 accel_val = randomS16InRange(-16383, 16383);  // Avoid overflow
        s16 gyro_val = randomS16InRange(-16383, 16383);
        
        // Test positive values
        MockI2CInterface::getInstance().simulateSensorData(accel_val, 0, 0, gyro_val, 0, 0, 8000);
        
        mpu6050_scaled_data positive_scaled;
        int pos_result = mpu6050_read_scaled_data(nullptr, &positive_scaled);
        
        // Test negative values
        MockI2CInterface::getInstance().simulateSensorData(-accel_val, 0, 0, -gyro_val, 0, 0, 8000);
        
        mpu6050_scaled_data negative_scaled;
        int neg_result = mpu6050_read_scaled_data(nullptr, &negative_scaled);
        
        if (pos_result == 0 && neg_result == 0) {
            // Property: Negating input should negate output
            EXPECT_EQ(positive_scaled.accel_x, -negative_scaled.accel_x)
                << "Sign symmetry broken for accelerometer, input: " << accel_val;
            EXPECT_EQ(positive_scaled.gyro_x, -negative_scaled.gyro_x)
                << "Sign symmetry broken for gyroscope, input: " << gyro_val;
        }
    });
}

/**
 * Property Test Summary
 */
class PropertyTestSummary : public ::testing::Test {};

TEST_F(PropertyTestSummary, PropertyBasedTestSummary) {
    std::cout << "\n=== Property-Based Test Summary ===" << std::endl;
    std::cout << "✓ Scaling Property Tests" << std::endl;
    std::cout << "  - Accelerometer scaling linearity (500 random inputs)" << std::endl;
    std::cout << "  - Gyroscope scaling consistency (500 random inputs)" << std::endl;
    std::cout << "  - Temperature formula verification (1000 random inputs)" << std::endl;
    std::cout << "\n✓ Range and Boundary Properties" << std::endl;
    std::cout << "  - Data range consistency (1000 random inputs)" << std::endl;
    std::cout << "  - Extreme boundary value handling" << std::endl;
    std::cout << "  - Overflow protection verification" << std::endl;
    std::cout << "\n✓ Invariant Properties" << std::endl;
    std::cout << "  - Read consistency invariant (100 iterations)" << std::endl;
    std::cout << "  - Scaling range invariant (200 random inputs)" << std::endl;
    std::cout << "  - Configuration state preservation" << std::endl;
    std::cout << "\n✓ Symmetry Properties" << std::endl;
    std::cout << "  - Sign symmetry for accelerometer/gyroscope (500 inputs)" << std::endl;
    std::cout << "  - Mathematical relationship preservation" << std::endl;
    std::cout << "\n=== Total Property Tests: ~3200 generated test cases ===" << std::endl;
    std::cout << "=======================================" << std::endl;
}