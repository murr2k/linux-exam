/**
 * @file sensor_data.cpp
 * @brief Implementation of sensor data fixtures
 */

#include "sensor_data.h"
#include <cmath>
#include <random>
#include <algorithm>
#include <chrono>

namespace SensorDataFixtures {

// =============================================================================
// CalibrationData Implementation
// =============================================================================

CalibrationData::CalibrationData() {
    // Device flat, Z-axis up (standard gravity)
    flat_horizontal = SensorSample(0, 0, 16384, 0, 0, 0, 7000, "Flat horizontal, Z up");
    
    // Device flat, Z-axis down (inverted gravity)
    flat_inverted = SensorSample(0, 0, -16384, 0, 0, 0, 7000, "Flat inverted, Z down");
    
    // Device vertical, X-axis up
    vertical_x_up = SensorSample(16384, 0, 0, 0, 0, 0, 7000, "Vertical, X up");
    
    // Device vertical, X-axis down
    vertical_x_down = SensorSample(-16384, 0, 0, 0, 0, 0, 7000, "Vertical, X down");
    
    // Device vertical, Y-axis up
    vertical_y_up = SensorSample(0, 16384, 0, 0, 0, 0, 7000, "Vertical, Y up");
    
    // Device vertical, Y-axis down
    vertical_y_down = SensorSample(0, -16384, 0, 0, 0, 0, 7000, "Vertical, Y down");
}

// =============================================================================
// MotionPatterns Implementation
// =============================================================================

MotionPatterns::MotionPatterns() {
    // Stationary pattern - device at rest
    for (int i = 0; i < 100; i++) {
        SensorSample sample(0, 0, 16384, 0, 0, 0, 7000, "Stationary reading " + std::to_string(i));
        sample.timestamp_us = i * 10000; // 10ms intervals
        stationary.push_back(sample);
    }
    
    // Slow tilt pattern - device slowly tilting
    for (int i = 0; i < 50; i++) {
        double angle = (i * M_PI / 100.0); // 0 to π/2 radians
        s16 x = static_cast<s16>(16384 * sin(angle));
        s16 z = static_cast<s16>(16384 * cos(angle));
        SensorSample sample(x, 0, z, 50, 0, 0, 7050, "Slow tilt " + std::to_string(i));
        sample.timestamp_us = i * 20000; // 20ms intervals
        slow_tilt.push_back(sample);
    }
    
    // Fast rotation pattern
    for (int i = 0; i < 30; i++) {
        s16 gyro_magnitude = 15000 + (i % 10) * 1000;
        SensorSample sample(
            static_cast<s16>(5000 * sin(i * 0.5)),
            static_cast<s16>(5000 * cos(i * 0.5)),
            16384,
            gyro_magnitude,
            static_cast<s16>(gyro_magnitude * 0.8),
            static_cast<s16>(gyro_magnitude * 0.6),
            7200, "Fast rotation " + std::to_string(i)
        );
        sample.timestamp_us = i * 5000; // 5ms intervals
        fast_rotation.push_back(sample);
    }
    
    // Linear acceleration pattern
    for (int i = 0; i < 40; i++) {
        s16 accel = 16384 + i * 800; // Increasing acceleration
        SensorSample sample(accel, 0, 16384, 0, 0, 0, 7100, "Linear accel " + std::to_string(i));
        sample.timestamp_us = i * 25000; // 25ms intervals
        linear_acceleration.push_back(sample);
    }
    
    // Vibration pattern - high frequency, low amplitude
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<s16> vib_dis(-800, 800);
    
    for (int i = 0; i < 200; i++) {
        SensorSample sample(
            vib_dis(gen), vib_dis(gen), 16384 + vib_dis(gen),
            vib_dis(gen), vib_dis(gen), vib_dis(gen),
            7000, "Vibration " + std::to_string(i)
        );
        sample.timestamp_us = i * 1000; // 1ms intervals
        vibration.push_back(sample);
    }
    
    // Freefall pattern
    for (int i = 0; i < 20; i++) {
        SensorSample sample(0, 0, 0, 0, 0, 0, 7000, "Freefall " + std::to_string(i));
        sample.timestamp_us = i * 50000; // 50ms intervals
        freefall.push_back(sample);
    }
    
    // Tap detection pattern - sudden spike then return to normal
    tap_detection.push_back(SensorSample(0, 0, 16384, 0, 0, 0, 7000, "Pre-tap"));
    tap_detection.push_back(SensorSample(25000, 0, 16384, 0, 0, 0, 7000, "Tap impact"));
    tap_detection.push_back(SensorSample(15000, 0, 16384, 0, 0, 0, 7000, "Tap decay"));
    tap_detection.push_back(SensorSample(5000, 0, 16384, 0, 0, 0, 7000, "Post-tap"));
    tap_detection.push_back(SensorSample(0, 0, 16384, 0, 0, 0, 7000, "Return to normal"));
    
    // Shake gesture pattern - multiple axes movement
    for (int i = 0; i < 60; i++) {
        double phase = i * M_PI / 15.0;
        s16 shake_x = static_cast<s16>(8000 * sin(phase));
        s16 shake_y = static_cast<s16>(6000 * sin(phase * 1.2));
        s16 shake_z = static_cast<s16>(16384 + 4000 * sin(phase * 0.8));
        SensorSample sample(shake_x, shake_y, shake_z, 0, 0, 0, 7000, "Shake " + std::to_string(i));
        sample.timestamp_us = i * 16667; // ~60Hz
        shake_gesture.push_back(sample);
    }
}

// =============================================================================
// NoiseProfiles Implementation
// =============================================================================

NoiseProfiles::NoiseProfiles() {
    std::random_device rd;
    std::mt19937 gen(rd());
    
    // Low noise profile
    std::normal_distribution<> low_noise_dist(0.0, 50.0);
    SensorSample base = getStationaryReading();
    
    for (int i = 0; i < 100; i++) {
        SensorSample sample = base;
        sample.accel_x += static_cast<s16>(low_noise_dist(gen));
        sample.accel_y += static_cast<s16>(low_noise_dist(gen));
        sample.accel_z += static_cast<s16>(low_noise_dist(gen));
        sample.gyro_x += static_cast<s16>(low_noise_dist(gen) * 0.5);
        sample.gyro_y += static_cast<s16>(low_noise_dist(gen) * 0.5);
        sample.gyro_z += static_cast<s16>(low_noise_dist(gen) * 0.5);
        sample.description = "Low noise " + std::to_string(i);
        low_noise.push_back(sample);
    }
    
    // Medium noise profile
    std::normal_distribution<> med_noise_dist(0.0, 200.0);
    for (int i = 0; i < 100; i++) {
        SensorSample sample = base;
        sample.accel_x += static_cast<s16>(med_noise_dist(gen));
        sample.accel_y += static_cast<s16>(med_noise_dist(gen));
        sample.accel_z += static_cast<s16>(med_noise_dist(gen));
        sample.gyro_x += static_cast<s16>(med_noise_dist(gen) * 0.5);
        sample.gyro_y += static_cast<s16>(med_noise_dist(gen) * 0.5);
        sample.gyro_z += static_cast<s16>(med_noise_dist(gen) * 0.5);
        sample.description = "Medium noise " + std::to_string(i);
        medium_noise.push_back(sample);
    }
    
    // High noise profile
    std::normal_distribution<> high_noise_dist(0.0, 1000.0);
    for (int i = 0; i < 100; i++) {
        SensorSample sample = base;
        sample.accel_x += static_cast<s16>(high_noise_dist(gen));
        sample.accel_y += static_cast<s16>(high_noise_dist(gen));
        sample.accel_z += static_cast<s16>(high_noise_dist(gen));
        sample.gyro_x += static_cast<s16>(high_noise_dist(gen) * 0.5);
        sample.gyro_y += static_cast<s16>(high_noise_dist(gen) * 0.5);
        sample.gyro_z += static_cast<s16>(high_noise_dist(gen) * 0.5);
        sample.description = "High noise " + std::to_string(i);
        high_noise.push_back(sample);
    }
    
    // Intermittent spikes
    std::uniform_int_distribution<> spike_dis(0, 9);
    for (int i = 0; i < 100; i++) {
        SensorSample sample = base;
        if (spike_dis(gen) == 0) { // 10% chance of spike
            sample.accel_x += 10000;
            sample.accel_y += 8000;
            sample.description = "Spike " + std::to_string(i);
        } else {
            sample.description = "Normal " + std::to_string(i);
        }
        intermittent_spikes.push_back(sample);
    }
    
    // Temperature drift
    for (int i = 0; i < 100; i++) {
        SensorSample sample = base;
        // Simulate temperature-dependent drift
        s16 temp_effect = static_cast<s16>(i * 5); // Gradual drift
        sample.accel_x += temp_effect;
        sample.accel_y += temp_effect / 2;
        sample.accel_z += temp_effect / 3;
        sample.temperature = 7000 + i * 20; // Temperature rising
        sample.description = "Temp drift " + std::to_string(i);
        temperature_drift.push_back(sample);
    }
}

// =============================================================================
// ErrorConditions Implementation
// =============================================================================

ErrorConditions::ErrorConditions() {
    // Device disconnected - all zeros or impossible values
    device_disconnected = SensorSample(0, 0, 0, 0, 0, 0, -32768, "Device disconnected");
    
    // Sensor stuck - same values repeated
    sensor_stuck = SensorSample(12345, 6789, 9876, 1111, 2222, 3333, 7500, "Sensor stuck");
    
    // Out of range values
    out_of_range = SensorSample(32767, -32768, 32767, -32768, 32767, -32768, 10000, "Out of range");
    
    // Communication error - corrupted data patterns
    communication_error = SensorSample(-1, -1, -1, -1, -1, -1, -1, "Communication error");
    
    // Power fluctuation - erratic readings
    power_fluctuation = SensorSample(25000, -15000, 30000, 20000, -18000, 22000, 5000, "Power fluctuation");
}

// =============================================================================
// SelfTestData Implementation
// =============================================================================

SelfTestData::SelfTestData() {
    // Baseline reading - normal operation
    baseline_reading = getStationaryReading();
    
    // Accelerometer self-test - significant change in accelerometer readings
    accel_self_test = SensorSample(8000, 8000, 24000, 0, 0, 0, 7000, "Accel self-test");
    
    // Gyroscope self-test - significant change in gyroscope readings
    gyro_self_test = SensorSample(0, 0, 16384, 15000, 15000, 15000, 7000, "Gyro self-test");
    
    // Combined self-test - both accelerometer and gyroscope changes
    combined_self_test = SensorSample(8000, 8000, 24000, 15000, 15000, 15000, 7000, "Combined self-test");
    
    // Expected changes during self-test (typical values)
    expected_accel_change_x = 8000;
    expected_accel_change_y = 8000;
    expected_accel_change_z = 8000;
    expected_gyro_change_x = 15000;
    expected_gyro_change_y = 15000;
    expected_gyro_change_z = 15000;
}

// =============================================================================
// TemperatureProfiles Implementation
// =============================================================================

TemperatureProfiles::TemperatureProfiles() {
    // Cold conditions (-40°C to 0°C)
    for (int temp_c = -40; temp_c <= 0; temp_c += 10) {
        TempPoint point;
        point.temp_celsius = temp_c;
        point.temp_raw = static_cast<s16>((temp_c - 36.53) * 340.0);
        point.sensor_reading = getStationaryReading();
        point.sensor_reading.temperature = point.temp_raw;
        point.condition = "Cold: " + std::to_string(temp_c) + "°C";
        cold_conditions.push_back(point);
    }
    
    // Normal conditions (0°C to 40°C)
    for (int temp_c = 0; temp_c <= 40; temp_c += 5) {
        TempPoint point;
        point.temp_celsius = temp_c;
        point.temp_raw = static_cast<s16>((temp_c - 36.53) * 340.0);
        point.sensor_reading = getStationaryReading();
        point.sensor_reading.temperature = point.temp_raw;
        point.condition = "Normal: " + std::to_string(temp_c) + "°C";
        normal_conditions.push_back(point);
    }
    
    // Hot conditions (40°C to 85°C)
    for (int temp_c = 40; temp_c <= 85; temp_c += 10) {
        TempPoint point;
        point.temp_celsius = temp_c;
        point.temp_raw = static_cast<s16>((temp_c - 36.53) * 340.0);
        point.sensor_reading = getStationaryReading();
        point.sensor_reading.temperature = point.temp_raw;
        point.condition = "Hot: " + std::to_string(temp_c) + "°C";
        hot_conditions.push_back(point);
    }
    
    // Extreme conditions (beyond normal operating range)
    std::vector<int> extreme_temps = {-50, -45, 90, 95, 100};
    for (int temp_c : extreme_temps) {
        TempPoint point;
        point.temp_celsius = temp_c;
        point.temp_raw = static_cast<s16>((temp_c - 36.53) * 340.0);
        point.sensor_reading = getStationaryReading();
        point.sensor_reading.temperature = point.temp_raw;
        // Add some drift at extreme temperatures
        point.sensor_reading.accel_x += temp_c > 85 ? 500 : -300;
        point.condition = "Extreme: " + std::to_string(temp_c) + "°C";
        extreme_conditions.push_back(point);
    }
}

// =============================================================================
// FixtureManager Implementation
// =============================================================================

FixtureManager::FixtureManager() 
    : calibration_data_(), motion_patterns_(), noise_profiles_(), 
      error_conditions_(), self_test_data_(), temperature_profiles_() {
}

SensorSample FixtureManager::getSampleByName(const std::string& name) const {
    auto it = custom_samples_.find(name);
    if (it != custom_samples_.end()) {
        return it->second;
    }
    
    // Check predefined samples
    if (name == "stationary") return getStationaryReading();
    if (name == "freefall") return getFreefallReading();
    if (name == "tilted") return getTiltedReading();
    if (name == "rotation") return getRotationReading();
    if (name == "noisy") return getNoisyReading();
    
    // Return default if not found
    return getStationaryReading();
}

std::vector<SensorSample> FixtureManager::getSequenceByName(const std::string& name) const {
    auto it = custom_sequences_.find(name);
    if (it != custom_sequences_.end()) {
        return it->second;
    }
    
    // Check predefined sequences
    if (name == "stationary") return motion_patterns_.stationary;
    if (name == "slow_tilt") return motion_patterns_.slow_tilt;
    if (name == "fast_rotation") return motion_patterns_.fast_rotation;
    if (name == "linear_acceleration") return motion_patterns_.linear_acceleration;
    if (name == "vibration") return motion_patterns_.vibration;
    if (name == "freefall") return motion_patterns_.freefall;
    if (name == "tap_detection") return motion_patterns_.tap_detection;
    if (name == "shake_gesture") return motion_patterns_.shake_gesture;
    
    // Return empty sequence if not found
    return std::vector<SensorSample>();
}

void FixtureManager::addCustomSample(const std::string& name, const SensorSample& sample) {
    custom_samples_[name] = sample;
}

void FixtureManager::addCustomSequence(const std::string& name, const std::vector<SensorSample>& sequence) {
    custom_sequences_[name] = sequence;
}

bool FixtureManager::validateSample(const SensorSample& sample) const {
    // Check accelerometer range (±2g default)
    if (!isWithinRange(sample.accel_x, -32768, 32767)) return false;
    if (!isWithinRange(sample.accel_y, -32768, 32767)) return false;
    if (!isWithinRange(sample.accel_z, -32768, 32767)) return false;
    
    // Check gyroscope range (±250°/s default)
    if (!isWithinRange(sample.gyro_x, -32768, 32767)) return false;
    if (!isWithinRange(sample.gyro_y, -32768, 32767)) return false;
    if (!isWithinRange(sample.gyro_z, -32768, 32767)) return false;
    
    // Check temperature range
    if (!isWithinRange(sample.temperature, Ranges::TEMP_MIN, Ranges::TEMP_MAX)) return false;
    
    return true;
}

bool FixtureManager::isWithinRange(s16 value, s16 min, s16 max) const {
    return value >= min && value <= max;
}

SensorSample FixtureManager::addNoise(const SensorSample& base, double noise_level) const {
    if (noise_level <= 0.0) return base;
    
    std::random_device rd;
    std::mt19937 gen(rd());
    std::normal_distribution<> noise_dist(0.0, noise_level * 1000.0);
    
    SensorSample noisy = base;
    noisy.accel_x += static_cast<s16>(noise_dist(gen));
    noisy.accel_y += static_cast<s16>(noise_dist(gen));
    noisy.accel_z += static_cast<s16>(noise_dist(gen));
    noisy.gyro_x += static_cast<s16>(noise_dist(gen) * 0.5);
    noisy.gyro_y += static_cast<s16>(noise_dist(gen) * 0.5);
    noisy.gyro_z += static_cast<s16>(noise_dist(gen) * 0.5);
    noisy.temperature += static_cast<s16>(noise_dist(gen) * 0.1);
    noisy.description = base.description + " (with noise)";
    
    return noisy;
}

std::vector<SensorSample> FixtureManager::interpolateSequence(const SensorSample& start, 
                                                             const SensorSample& end, 
                                                             int steps) const {
    std::vector<SensorSample> sequence;
    sequence.reserve(steps);
    
    for (int i = 0; i < steps; i++) {
        double t = static_cast<double>(i) / (steps - 1);
        
        SensorSample interpolated;
        interpolated.accel_x = static_cast<s16>(start.accel_x + t * (end.accel_x - start.accel_x));
        interpolated.accel_y = static_cast<s16>(start.accel_y + t * (end.accel_y - start.accel_y));
        interpolated.accel_z = static_cast<s16>(start.accel_z + t * (end.accel_z - start.accel_z));
        interpolated.gyro_x = static_cast<s16>(start.gyro_x + t * (end.gyro_x - start.gyro_x));
        interpolated.gyro_y = static_cast<s16>(start.gyro_y + t * (end.gyro_y - start.gyro_y));
        interpolated.gyro_z = static_cast<s16>(start.gyro_z + t * (end.gyro_z - start.gyro_z));
        interpolated.temperature = static_cast<s16>(start.temperature + t * (end.temperature - start.temperature));
        interpolated.description = "Interpolated step " + std::to_string(i);
        interpolated.timestamp_us = start.timestamp_us + static_cast<u64>(t * (end.timestamp_us - start.timestamp_us));
        
        sequence.push_back(interpolated);
    }
    
    return sequence;
}

// =============================================================================
// TestScenarios Implementation
// =============================================================================

namespace TestScenarios {
    const std::vector<SensorSample> INITIALIZATION_SEQUENCE = {
        SensorSample(0, 0, 0, 0, 0, 0, -32768, "Power on - invalid readings"),
        SensorSample(-1, -1, -1, -1, -1, -1, -1, "Communication establishing"),
        SensorSample(0, 0, 0, 0, 0, 0, 6000, "Device reset state"),
        SensorSample(0, 0, 16384, 0, 0, 0, 7000, "Normal operation achieved")
    };
    
    const std::vector<SensorSample> CALIBRATION_SEQUENCE = {
        SensorSample(150, -80, 16500, 200, -150, 100, 6950, "Pre-calibration readings"),
        SensorSample(75, -40, 16450, 100, -75, 50, 6975, "Calibration in progress 1"),
        SensorSample(25, -15, 16400, 25, -25, 15, 6990, "Calibration in progress 2"),
        SensorSample(5, -2, 16390, 5, -5, 2, 6998, "Calibration converging"),
        SensorSample(0, 0, 16384, 0, 0, 0, 7000, "Calibration complete")
    };
    
    const std::vector<SensorSample> NORMAL_OPERATION_SEQUENCE = {
        SensorSample(0, 0, 16384, 0, 0, 0, 7000, "Stationary"),
        SensorSample(2000, 0, 16000, 500, 0, 0, 7010, "Minor movement"),
        SensorSample(5000, 1000, 15000, 2000, 1000, 500, 7025, "Moderate movement"),
        SensorSample(0, 0, 16384, 0, 0, 0, 7020, "Return to stationary")
    };
    
    const std::vector<SensorSample> ERROR_RECOVERY_SEQUENCE = {
        SensorSample(0, 0, 16384, 0, 0, 0, 7000, "Normal operation"),
        SensorSample(-1, -1, -1, -1, -1, -1, -1, "Communication error"),
        SensorSample(-1, -1, -1, -1, -1, -1, -1, "Error persists"),
        SensorSample(32767, -32768, 32767, -32768, 32767, -32768, 10000, "Invalid data"),
        SensorSample(0, 0, 16384, 0, 0, 0, 7000, "Recovery complete")
    };
    
    const std::vector<SensorSample> POWER_CYCLE_SEQUENCE = {
        SensorSample(0, 0, 16384, 0, 0, 0, 7000, "Normal operation"),
        SensorSample(0, 0, 0, 0, 0, 0, -32768, "Power off"),
        SensorSample(0, 0, 0, 0, 0, 0, -32768, "Power off state"),
        SensorSample(-1, -1, -1, -1, -1, -1, -1, "Power on - initializing"),
        SensorSample(0, 0, 16384, 0, 0, 0, 7000, "Power on complete")
    };
    
    const std::vector<SensorSample> SELF_TEST_SEQUENCE = {
        SensorSample(0, 0, 16384, 0, 0, 0, 7000, "Self-test baseline"),
        SensorSample(8000, 8000, 24000, 0, 0, 0, 7000, "Accel self-test enabled"),
        SensorSample(8000, 8000, 24000, 15000, 15000, 15000, 7000, "Full self-test enabled"),
        SensorSample(0, 0, 16384, 0, 0, 0, 7000, "Self-test disabled"),
        SensorSample(0, 0, 16384, 0, 0, 0, 7000, "Self-test complete")
    };
}

} // namespace SensorDataFixtures