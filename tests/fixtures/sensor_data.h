/**
 * @file sensor_data.h
 * @brief Predefined sensor data fixtures for comprehensive testing
 * 
 * This file contains realistic sensor data patterns, calibration values,
 * and test scenarios that can be used across multiple test cases to
 * ensure consistent and comprehensive testing of the MPU-6050 driver.
 */

#ifndef SENSOR_DATA_H
#define SENSOR_DATA_H

extern "C" {
    typedef signed short s16;
    typedef unsigned char u8;
}

#include <vector>
#include <map>
#include <string>

namespace SensorDataFixtures {

    /**
     * @struct SensorSample
     * @brief Single sensor reading with metadata
     */
    struct SensorSample {
        s16 accel_x, accel_y, accel_z;
        s16 gyro_x, gyro_y, gyro_z;
        s16 temperature;
        std::string description;
        u64 timestamp_us;
        
        SensorSample() : accel_x(0), accel_y(0), accel_z(0),
                        gyro_x(0), gyro_y(0), gyro_z(0),
                        temperature(7000), timestamp_us(0) {}
        
        SensorSample(s16 ax, s16 ay, s16 az, s16 gx, s16 gy, s16 gz, s16 temp, 
                    const std::string& desc = "") 
            : accel_x(ax), accel_y(ay), accel_z(az),
              gyro_x(gx), gyro_y(gy), gyro_z(gz),
              temperature(temp), description(desc), timestamp_us(0) {}
    };

    /**
     * @struct CalibrationData
     * @brief Calibration data for different orientations and conditions
     */
    struct CalibrationData {
        SensorSample flat_horizontal;      // Device flat, Z up
        SensorSample flat_inverted;        // Device flat, Z down
        SensorSample vertical_x_up;        // Device vertical, X up
        SensorSample vertical_x_down;      // Device vertical, X down
        SensorSample vertical_y_up;        // Device vertical, Y up
        SensorSample vertical_y_down;      // Device vertical, Y down
        
        CalibrationData();
    };

    /**
     * @struct MotionPatterns
     * @brief Common motion patterns for testing
     */
    struct MotionPatterns {
        std::vector<SensorSample> stationary;
        std::vector<SensorSample> slow_tilt;
        std::vector<SensorSample> fast_rotation;
        std::vector<SensorSample> linear_acceleration;
        std::vector<SensorSample> vibration;
        std::vector<SensorSample> freefall;
        std::vector<SensorSample> tap_detection;
        std::vector<SensorSample> shake_gesture;
        
        MotionPatterns();
    };

    /**
     * @struct NoiseProfiles
     * @brief Different noise patterns for robustness testing
     */
    struct NoiseProfiles {
        std::vector<SensorSample> low_noise;
        std::vector<SensorSample> medium_noise;
        std::vector<SensorSample> high_noise;
        std::vector<SensorSample> intermittent_spikes;
        std::vector<SensorSample> temperature_drift;
        
        NoiseProfiles();
    };

    /**
     * @struct ErrorConditions
     * @brief Sensor data representing various error conditions
     */
    struct ErrorConditions {
        SensorSample device_disconnected;     // All readings zero or invalid
        SensorSample sensor_stuck;            // Same readings repeated
        SensorSample out_of_range;           // Values exceeding sensor limits
        SensorSample communication_error;     // Corrupted readings
        SensorSample power_fluctuation;      // Inconsistent readings
        
        ErrorConditions();
    };

    /**
     * @struct SelfTestData
     * @brief Expected responses during self-test mode
     */
    struct SelfTestData {
        SensorSample baseline_reading;        // Normal operation baseline
        SensorSample accel_self_test;        // With accelerometer self-test enabled
        SensorSample gyro_self_test;         // With gyroscope self-test enabled
        SensorSample combined_self_test;     // Both self-tests enabled
        
        // Expected changes during self-test
        s16 expected_accel_change_x;
        s16 expected_accel_change_y;
        s16 expected_accel_change_z;
        s16 expected_gyro_change_x;
        s16 expected_gyro_change_y;
        s16 expected_gyro_change_z;
        
        SelfTestData();
    };

    /**
     * @struct TemperatureProfiles
     * @brief Temperature-related data for testing thermal behavior
     */
    struct TemperatureProfiles {
        struct TempPoint {
            s16 temp_raw;
            double temp_celsius;
            SensorSample sensor_reading;
            std::string condition;
        };
        
        std::vector<TempPoint> cold_conditions;     // -40°C to 0°C
        std::vector<TempPoint> normal_conditions;   // 0°C to 40°C
        std::vector<TempPoint> hot_conditions;      // 40°C to 85°C
        std::vector<TempPoint> extreme_conditions;  // Beyond normal range
        
        TemperatureProfiles();
    };

    /**
     * @class FixtureManager
     * @brief Manages and provides access to all test fixtures
     */
    class FixtureManager {
    public:
        static FixtureManager& getInstance() {
            static FixtureManager instance;
            return instance;
        }
        
        // Get fixture data
        const CalibrationData& getCalibrationData() const { return calibration_data_; }
        const MotionPatterns& getMotionPatterns() const { return motion_patterns_; }
        const NoiseProfiles& getNoiseProfiles() const { return noise_profiles_; }
        const ErrorConditions& getErrorConditions() const { return error_conditions_; }
        const SelfTestData& getSelfTestData() const { return self_test_data_; }
        const TemperatureProfiles& getTemperatureProfiles() const { return temperature_profiles_; }
        
        // Utility methods
        SensorSample getSampleByName(const std::string& name) const;
        std::vector<SensorSample> getSequenceByName(const std::string& name) const;
        
        // Add custom fixtures
        void addCustomSample(const std::string& name, const SensorSample& sample);
        void addCustomSequence(const std::string& name, const std::vector<SensorSample>& sequence);
        
        // Data validation
        bool validateSample(const SensorSample& sample) const;
        bool isWithinRange(s16 value, s16 min, s16 max) const;
        
        // Generate variations
        SensorSample addNoise(const SensorSample& base, double noise_level) const;
        std::vector<SensorSample> interpolateSequence(const SensorSample& start, 
                                                     const SensorSample& end, 
                                                     int steps) const;

    private:
        CalibrationData calibration_data_;
        MotionPatterns motion_patterns_;
        NoiseProfiles noise_profiles_;
        ErrorConditions error_conditions_;
        SelfTestData self_test_data_;
        TemperatureProfiles temperature_profiles_;
        
        std::map<std::string, SensorSample> custom_samples_;
        std::map<std::string, std::vector<SensorSample>> custom_sequences_;
        
        FixtureManager();
        ~FixtureManager() = default;
        FixtureManager(const FixtureManager&) = delete;
        FixtureManager& operator=(const FixtureManager&) = delete;
    };

    // Convenience functions for quick access to common fixtures

    /**
     * @brief Get a stationary device reading (1g on Z-axis)
     * @return Standard stationary sensor reading
     */
    inline SensorSample getStationaryReading() {
        return SensorSample(0, 0, 16384, 0, 0, 0, 7000, "Device at rest, Z-axis up");
    }

    /**
     * @brief Get a reading representing freefall
     * @return Freefall sensor reading (near zero acceleration)
     */
    inline SensorSample getFreefallReading() {
        return SensorSample(0, 0, 0, 0, 0, 0, 7000, "Device in freefall");
    }

    /**
     * @brief Get a reading with device tilted 45 degrees
     * @return 45-degree tilt sensor reading
     */
    inline SensorSample getTiltedReading() {
        s16 tilted_value = static_cast<s16>(16384 / 1.414); // cos(45°) * 1g
        return SensorSample(tilted_value, 0, tilted_value, 0, 0, 0, 7000, "45-degree tilt");
    }

    /**
     * @brief Get a reading simulating rapid rotation
     * @return High gyroscope activity reading
     */
    inline SensorSample getRotationReading() {
        return SensorSample(2000, 1000, 14000, 15000, 12000, 8000, 7200, "Device rotating rapidly");
    }

    /**
     * @brief Get a reading with typical noise levels
     * @return Noisy sensor reading
     */
    inline SensorSample getNoisyReading() {
        return SensorSample(150, -80, 16500, 200, -150, 100, 6950, "Reading with typical noise");
    }

    // Range validation constants
    namespace Ranges {
        // Accelerometer ranges (raw values for ±2g, ±4g, ±8g, ±16g)
        constexpr s16 ACCEL_2G_MAX = 32767;
        constexpr s16 ACCEL_4G_MAX = 32767;
        constexpr s16 ACCEL_8G_MAX = 32767;
        constexpr s16 ACCEL_16G_MAX = 32767;
        
        // Gyroscope ranges (raw values for ±250, ±500, ±1000, ±2000 °/s)
        constexpr s16 GYRO_250_MAX = 32767;
        constexpr s16 GYRO_500_MAX = 32767;
        constexpr s16 GYRO_1000_MAX = 32767;
        constexpr s16 GYRO_2000_MAX = 32767;
        
        // Temperature range (raw values approximately -40°C to +85°C)
        constexpr s16 TEMP_MIN = -4760;  // Approximately -40°C
        constexpr s16 TEMP_MAX = 8500;   // Approximately +85°C
        
        // 1g reference values for different accelerometer ranges
        constexpr s16 ACCEL_1G_2G_RANGE = 16384;   // 1g in ±2g range
        constexpr s16 ACCEL_1G_4G_RANGE = 8192;    // 1g in ±4g range
        constexpr s16 ACCEL_1G_8G_RANGE = 4096;    // 1g in ±8g range
        constexpr s16 ACCEL_1G_16G_RANGE = 2048;   // 1g in ±16g range
    }

    // Common test scenarios as pre-defined data sets
    namespace TestScenarios {
        extern const std::vector<SensorSample> INITIALIZATION_SEQUENCE;
        extern const std::vector<SensorSample> CALIBRATION_SEQUENCE;
        extern const std::vector<SensorSample> NORMAL_OPERATION_SEQUENCE;
        extern const std::vector<SensorSample> ERROR_RECOVERY_SEQUENCE;
        extern const std::vector<SensorSample> POWER_CYCLE_SEQUENCE;
        extern const std::vector<SensorSample> SELF_TEST_SEQUENCE;
    }

} // namespace SensorDataFixtures

// Convenience macros for accessing fixtures in tests

#define GET_FIXTURE_MANAGER() SensorDataFixtures::FixtureManager::getInstance()

#define GET_STATIONARY_READING() SensorDataFixtures::getStationaryReading()

#define GET_CALIBRATION_DATA() GET_FIXTURE_MANAGER().getCalibrationData()

#define GET_MOTION_PATTERNS() GET_FIXTURE_MANAGER().getMotionPatterns()

#define VALIDATE_SENSOR_SAMPLE(sample) \
    EXPECT_TRUE(GET_FIXTURE_MANAGER().validateSample(sample))

#define EXPECT_ACCELEROMETER_IN_RANGE(x, y, z, range_g) \
    do { \
        s16 max_val = SensorDataFixtures::Ranges::ACCEL_##range_g##G_MAX; \
        EXPECT_GE(x, -max_val); EXPECT_LE(x, max_val); \
        EXPECT_GE(y, -max_val); EXPECT_LE(y, max_val); \
        EXPECT_GE(z, -max_val); EXPECT_LE(z, max_val); \
    } while(0)

#define EXPECT_GYROSCOPE_IN_RANGE(x, y, z, range_dps) \
    do { \
        s16 max_val = SensorDataFixtures::Ranges::GYRO_##range_dps##_MAX; \
        EXPECT_GE(x, -max_val); EXPECT_LE(x, max_val); \
        EXPECT_GE(y, -max_val); EXPECT_LE(y, max_val); \
        EXPECT_GE(z, -max_val); EXPECT_LE(z, max_val); \
    } while(0)

#define EXPECT_TEMPERATURE_VALID(temp) \
    EXPECT_GE(temp, SensorDataFixtures::Ranges::TEMP_MIN); \
    EXPECT_LE(temp, SensorDataFixtures::Ranges::TEMP_MAX)

#endif // SENSOR_DATA_H