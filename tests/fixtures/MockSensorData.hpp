
#ifndef MOCK_SENSOR_DATA_HPP
#define MOCK_SENSOR_DATA_HPP

#include <vector>
#include <random>
#include <cmath>

/**
 * Mock sensor data generator for C++ tests
 * Provides various sensor data patterns for comprehensive testing
 */
class MockSensorData {
public:
    struct SensorReading {
        int16_t accel_x, accel_y, accel_z;
        int16_t temp;
        int16_t gyro_x, gyro_y, gyro_z;
        
        SensorReading(int16_t ax=0, int16_t ay=0, int16_t az=0, int16_t t=0,
                     int16_t gx=0, int16_t gy=0, int16_t gz=0) 
            : accel_x(ax), accel_y(ay), accel_z(az), temp(t),
              gyro_x(gx), gyro_y(gy), gyro_z(gz) {}
    };
    
    enum class Pattern {
        NORMAL,
        SINE_WAVE,
        RANDOM_WALK,
        STEP_FUNCTION,
        NOISY_CONSTANT,
        EXTREME_VALUES
    };
    
private:
    std::mt19937 rng_;
    std::vector<SensorReading> data_;
    
public:
    MockSensorData(unsigned seed = 42) : rng_(seed) {}
    
    // Generate data with specific pattern
    std::vector<SensorReading> generate(Pattern pattern, size_t count = 100) {
        data_.clear();
        data_.reserve(count);
        
        switch (pattern) {
            case Pattern::NORMAL:
                generateNormal(count);
                break;
            case Pattern::SINE_WAVE:
                generateSineWave(count);
                break;
            case Pattern::RANDOM_WALK:
                generateRandomWalk(count);
                break;
            case Pattern::STEP_FUNCTION:
                generateStepFunction(count);
                break;
            case Pattern::NOISY_CONSTANT:
                generateNoisyConstant(count);
                break;
            case Pattern::EXTREME_VALUES:
                generateExtremeValues(count);
                break;
        }
        
        return data_;
    }
    
    // Get predefined test scenarios
    static SensorReading getScenario(const std::string& name) {
        if (name == "rest") {
            return SensorReading(0, 0, 16384, 23000, 0, 0, 0);  // At rest, gravity on Z
        } else if (name == "movement") {
            return SensorReading(5000, 3000, 14000, 23000, 1000, 500, 200);
        } else if (name == "high_g") {
            return SensorReading(30000, -20000, 25000, 23000, 100, 200, 300);
        } else if (name == "rotation") {
            return SensorReading(1000, 2000, 16000, 23000, 15000, -12000, 8000);
        } else if (name == "hot") {
            return SensorReading(1000, 2000, 16000, 35000, 100, 200, 300);  // ~67°C
        } else if (name == "cold") {
            return SensorReading(1000, 2000, 16000, -10000, 100, 200, 300);  // ~-66°C
        }
        return SensorReading();  // Default: all zeros
    }
    
private:
    void generateNormal(size_t count) {
        std::normal_distribution<float> accel_dist(0, 2000);
        std::normal_distribution<float> gyro_dist(0, 500);
        std::normal_distribution<float> temp_dist(23000, 1000);
        
        for (size_t i = 0; i < count; ++i) {
            data_.emplace_back(
                static_cast<int16_t>(accel_dist(rng_)),
                static_cast<int16_t>(accel_dist(rng_)),
                static_cast<int16_t>(16384 + accel_dist(rng_) * 0.1),  // Gravity + noise
                static_cast<int16_t>(temp_dist(rng_)),
                static_cast<int16_t>(gyro_dist(rng_)),
                static_cast<int16_t>(gyro_dist(rng_)),
                static_cast<int16_t>(gyro_dist(rng_))
            );
        }
    }
    
    void generateSineWave(size_t count) {
        for (size_t i = 0; i < count; ++i) {
            float t = static_cast<float>(i) / 10.0f;  // Time scaling
            data_.emplace_back(
                static_cast<int16_t>(8000 * std::sin(t)),
                static_cast<int16_t>(8000 * std::cos(t)),
                static_cast<int16_t>(16384 + 2000 * std::sin(t * 0.5)),
                23000,  // Constant temperature
                static_cast<int16_t>(2000 * std::sin(t * 2)),
                static_cast<int16_t>(2000 * std::cos(t * 2)), 
                static_cast<int16_t>(1000 * std::sin(t * 3))
            );
        }
    }
    
    void generateRandomWalk(size_t count) {
        SensorReading current(1000, 2000, 16384, 23000, 100, 200, 300);
        std::normal_distribution<float> step(-100, 100);
        
        for (size_t i = 0; i < count; ++i) {
            current.accel_x += static_cast<int16_t>(step(rng_));
            current.accel_y += static_cast<int16_t>(step(rng_));
            current.accel_z += static_cast<int16_t>(step(rng_) * 0.1);
            current.temp += static_cast<int16_t>(step(rng_) * 0.01);
            current.gyro_x += static_cast<int16_t>(step(rng_) * 0.5);
            current.gyro_y += static_cast<int16_t>(step(rng_) * 0.5);
            current.gyro_z += static_cast<int16_t>(step(rng_) * 0.5);
            
            // Clamp to reasonable ranges
            current.accel_x = std::clamp(current.accel_x, static_cast<int16_t>(-32000), static_cast<int16_t>(32000));
            current.accel_y = std::clamp(current.accel_y, static_cast<int16_t>(-32000), static_cast<int16_t>(32000));
            current.accel_z = std::clamp(current.accel_z, static_cast<int16_t>(0), static_cast<int16_t>(32000));
            
            data_.push_back(current);
        }
    }
    
    void generateStepFunction(size_t count) {
        size_t step_size = count / 4;
        std::vector<SensorReading> steps = {
            SensorReading(0, 0, 16384, 23000, 0, 0, 0),        // Rest
            SensorReading(8000, 0, 16384, 25000, 2000, 0, 0),  // X acceleration
            SensorReading(0, 8000, 16384, 25000, 0, 2000, 0),  // Y acceleration  
            SensorReading(0, 0, 24000, 27000, 0, 0, 2000)      // Z acceleration
        };
        
        for (size_t i = 0; i < count; ++i) {
            size_t step_idx = i / step_size;
            if (step_idx >= steps.size()) step_idx = steps.size() - 1;
            data_.push_back(steps[step_idx]);
        }
    }
    
    void generateNoisyConstant(size_t count) {
        std::normal_distribution<float> noise(0, 50);
        SensorReading base(2000, 1000, 15000, 24000, 300, 200, 100);
        
        for (size_t i = 0; i < count; ++i) {
            data_.emplace_back(
                base.accel_x + static_cast<int16_t>(noise(rng_)),
                base.accel_y + static_cast<int16_t>(noise(rng_)),
                base.accel_z + static_cast<int16_t>(noise(rng_)),
                base.temp + static_cast<int16_t>(noise(rng_) * 0.1),
                base.gyro_x + static_cast<int16_t>(noise(rng_)),
                base.gyro_y + static_cast<int16_t>(noise(rng_)),
                base.gyro_z + static_cast<int16_t>(noise(rng_))
            );
        }
    }
    
    void generateExtremeValues(size_t count) {
        std::vector<SensorReading> extremes = {
            SensorReading(32767, 32767, 32767, 32767, 32767, 32767, 32767),   // Max
            SensorReading(-32768, -32768, -32768, -32768, -32768, -32768, -32768), // Min
            SensorReading(0, 0, 0, 0, 0, 0, 0),                              // Zero
            SensorReading(16384, 0, 0, 23000, 0, 0, 0),                      // 1g X only
            SensorReading(0, 16384, 0, 23000, 0, 0, 0),                      // 1g Y only
            SensorReading(0, 0, 16384, 23000, 0, 0, 0),                      // 1g Z only
        };
        
        for (size_t i = 0; i < count; ++i) {
            data_.push_back(extremes[i % extremes.size()]);
        }
    }
};

#endif // MOCK_SENSOR_DATA_HPP
