/**
 * @file mock_i2c.cpp
 * @brief Implementation of mock I2C interface for testing
 */

#include "mock_i2c.h"
#include <random>
#include <thread>
#include <chrono>
#include <cstring>

// C function implementations that delegate to the mock
extern "C" {
    int mock_i2c_transfer(struct i2c_adapter* adapter, struct i2c_msg* msgs, int num) {
        return MockI2CInterface::getInstance().i2c_transfer(adapter, msgs, num);
    }
    
    s32 mock_i2c_smbus_read_byte_data(const struct i2c_client* client, u8 command) {
        return MockI2CInterface::getInstance().i2c_smbus_read_byte_data(client, command);
    }
    
    s32 mock_i2c_smbus_write_byte_data(const struct i2c_client* client, u8 command, u8 value) {
        return MockI2CInterface::getInstance().i2c_smbus_write_byte_data(client, command, value);
    }
    
    s32 mock_i2c_smbus_read_word_data(const struct i2c_client* client, u8 command) {
        return MockI2CInterface::getInstance().i2c_smbus_read_word_data(client, command);
    }
    
    s32 mock_i2c_smbus_write_word_data(const struct i2c_client* client, u8 command, u16 value) {
        return MockI2CInterface::getInstance().i2c_smbus_write_word_data(client, command, value);
    }
    
    s32 mock_i2c_smbus_read_i2c_block_data(const struct i2c_client* client, u8 command, u8 length, u8* values) {
        return MockI2CInterface::getInstance().i2c_smbus_read_i2c_block_data(client, command, length, values);
    }
    
    s32 mock_i2c_smbus_write_i2c_block_data(const struct i2c_client* client, u8 command, u8 length, const u8* values) {
        return MockI2CInterface::getInstance().i2c_smbus_write_i2c_block_data(client, command, length, values);
    }
}

void MockI2CInterface::setDefaultBehavior() {
    using ::testing::_;
    using ::testing::Return;
    using ::testing::Invoke;
    using ::testing::DoAll;
    using ::testing::IncrementStatistic;
    
    // Set up default successful behavior
    ON_CALL(*this, i2c_transfer(_, _, _))
        .WillByDefault(Invoke([this](struct i2c_adapter* adapter, struct i2c_msg* msgs, int num) -> int {
            transfer_count_++;
            
            if (!register_bank_.device_present) {
                return -ENODEV;
            }
            
            if (shouldInjectError()) {
                return -register_bank_.error_code;
            }
            
            if (register_bank_.transfer_delay_ms > 0) {
                std::this_thread::sleep_for(std::chrono::milliseconds(register_bank_.transfer_delay_ms));
            }
            
            // Process each message
            for (int i = 0; i < num; i++) {
                if (msgs[i].flags & I2C_M_RD) {
                    // Read operation
                    read_count_++;
                    // Simulate reading from register bank
                    // This is a simplified implementation
                } else {
                    // Write operation
                    write_count_++;
                    // Simulate writing to register bank
                }
            }
            
            return num; // Success: return number of messages processed
        }));
    
    ON_CALL(*this, i2c_smbus_read_byte_data(_, _))
        .WillByDefault(Invoke([this](const struct i2c_client* client, u8 command) -> s32 {
            read_count_++;
            
            if (!register_bank_.device_present) {
                return -ENODEV;
            }
            
            if (shouldInjectError()) {
                return -register_bank_.error_code;
            }
            
            auto it = register_bank_.byte_registers.find(command);
            if (it != register_bank_.byte_registers.end()) {
                u8 value = it->second;
                if (register_bank_.noise_enabled) {
                    value = addNoise(value);
                }
                return value;
            }
            
            return 0; // Default value for uninitialized registers
        }));
    
    ON_CALL(*this, i2c_smbus_write_byte_data(_, _, _))
        .WillByDefault(Invoke([this](const struct i2c_client* client, u8 command, u8 value) -> s32 {
            write_count_++;
            
            if (!register_bank_.device_present) {
                return -ENODEV;
            }
            
            if (shouldInjectError()) {
                return -register_bank_.error_code;
            }
            
            register_bank_.byte_registers[command] = value;
            return 0; // Success
        }));
    
    ON_CALL(*this, i2c_smbus_read_word_data(_, _))
        .WillByDefault(Invoke([this](const struct i2c_client* client, u8 command) -> s32 {
            read_count_++;
            
            if (!register_bank_.device_present) {
                return -ENODEV;
            }
            
            if (shouldInjectError()) {
                return -register_bank_.error_code;
            }
            
            auto it = register_bank_.word_registers.find(command);
            if (it != register_bank_.word_registers.end()) {
                s16 value = static_cast<s16>(it->second);
                if (register_bank_.noise_enabled) {
                    value = addNoise(value);
                }
                return value;
            }
            
            return 0; // Default value
        }));
    
    ON_CALL(*this, i2c_smbus_write_word_data(_, _, _))
        .WillByDefault(Invoke([this](const struct i2c_client* client, u8 command, u16 value) -> s32 {
            write_count_++;
            
            if (!register_bank_.device_present) {
                return -ENODEV;
            }
            
            if (shouldInjectError()) {
                return -register_bank_.error_code;
            }
            
            register_bank_.word_registers[command] = value;
            return 0; // Success
        }));
    
    ON_CALL(*this, i2c_smbus_read_i2c_block_data(_, _, _, _))
        .WillByDefault(Invoke([this](const struct i2c_client* client, u8 command, u8 length, u8* values) -> s32 {
            read_count_++;
            
            if (!register_bank_.device_present) {
                return -ENODEV;
            }
            
            if (shouldInjectError()) {
                return -register_bank_.error_code;
            }
            
            // Read consecutive registers starting from command
            for (u8 i = 0; i < length; i++) {
                auto it = register_bank_.byte_registers.find(command + i);
                if (it != register_bank_.byte_registers.end()) {
                    values[i] = it->second;
                    if (register_bank_.noise_enabled) {
                        values[i] = addNoise(values[i]);
                    }
                } else {
                    values[i] = 0;
                }
            }
            
            return length; // Return number of bytes read
        }));
    
    ON_CALL(*this, i2c_smbus_write_i2c_block_data(_, _, _, _))
        .WillByDefault(Invoke([this](const struct i2c_client* client, u8 command, u8 length, const u8* values) -> s32 {
            write_count_++;
            
            if (!register_bank_.device_present) {
                return -ENODEV;
            }
            
            if (shouldInjectError()) {
                return -register_bank_.error_code;
            }
            
            // Write consecutive registers starting from command
            for (u8 i = 0; i < length; i++) {
                register_bank_.byte_registers[command + i] = values[i];
            }
            
            return 0; // Success
        }));
}

void MockI2CInterface::simulateDevicePresent(bool present) {
    register_bank_.device_present = present;
}

void MockI2CInterface::simulateI2CError(int error_code) {
    register_bank_.error_code = error_code;
    register_bank_.error_injection_enabled = true;
    register_bank_.error_injection_rate = 1.0; // Always inject error
}

void MockI2CInterface::setRegisterValue(u8 reg, u8 value) {
    register_bank_.byte_registers[reg] = value;
}

void MockI2CInterface::setRegisterValue(u8 reg, u16 value) {
    register_bank_.word_registers[reg] = value;
}

u8 MockI2CInterface::getRegisterValue(u8 reg) const {
    auto it = register_bank_.byte_registers.find(reg);
    return (it != register_bank_.byte_registers.end()) ? it->second : 0;
}

void MockI2CInterface::clearRegisterValues() {
    register_bank_.byte_registers.clear();
    register_bank_.word_registers.clear();
}

void MockI2CInterface::enableErrorInjection(bool enable) {
    register_bank_.error_injection_enabled = enable;
}

void MockI2CInterface::setErrorInjectionRate(double rate) {
    register_bank_.error_injection_rate = std::max(0.0, std::min(1.0, rate));
}

void MockI2CInterface::simulateNoiseInReads(bool enable, double noise_level) {
    register_bank_.noise_enabled = enable;
    register_bank_.noise_level = std::max(0.0, std::min(1.0, noise_level));
}

void MockI2CInterface::setTransferDelay(int delay_ms) {
    register_bank_.transfer_delay_ms = std::max(0, delay_ms);
}

void MockI2CInterface::resetStatistics() {
    transfer_count_ = 0;
    read_count_ = 0;
    write_count_ = 0;
}

void MockI2CInterface::setupMPU6050Defaults() {
    // Set up typical MPU-6050 register values
    setRegisterValue(MPU6050_Registers::WHO_AM_I, MPU6050_Registers::WHO_AM_I_VALUE);
    setRegisterValue(MPU6050_Registers::PWR_MGMT_1, MPU6050_Registers::PWR_MGMT_1_RESET);
    setRegisterValue(MPU6050_Registers::PWR_MGMT_2, 0x00);
    setRegisterValue(MPU6050_Registers::CONFIG, 0x00);
    setRegisterValue(MPU6050_Registers::GYRO_CONFIG, 0x00);
    setRegisterValue(MPU6050_Registers::ACCEL_CONFIG, 0x00);
}

void MockI2CInterface::simulateCalibrationData() {
    // Simulate typical calibration offsets
    setRegisterValue(MPU6050_Registers::ACCEL_XOUT_H, 0x00);
    setRegisterValue(MPU6050_Registers::ACCEL_XOUT_L, 0x00);
    setRegisterValue(MPU6050_Registers::ACCEL_YOUT_H, 0x00);
    setRegisterValue(MPU6050_Registers::ACCEL_YOUT_L, 0x00);
    setRegisterValue(MPU6050_Registers::ACCEL_ZOUT_H, 0x40);
    setRegisterValue(MPU6050_Registers::ACCEL_ZOUT_L, 0x00);
    setRegisterValue(MPU6050_Registers::GYRO_XOUT_H, 0x00);
    setRegisterValue(MPU6050_Registers::GYRO_XOUT_L, 0x00);
    setRegisterValue(MPU6050_Registers::GYRO_YOUT_H, 0x00);
    setRegisterValue(MPU6050_Registers::GYRO_YOUT_L, 0x00);
    setRegisterValue(MPU6050_Registers::GYRO_ZOUT_H, 0x00);
    setRegisterValue(MPU6050_Registers::GYRO_ZOUT_L, 0x00);
}

void MockI2CInterface::simulateSensorData(s16 accel_x, s16 accel_y, s16 accel_z,
                                         s16 gyro_x, s16 gyro_y, s16 gyro_z, s16 temp) {
    // Set accelerometer data
    setRegisterValue(MPU6050_Registers::ACCEL_XOUT_H, static_cast<u8>(accel_x >> 8));
    setRegisterValue(MPU6050_Registers::ACCEL_XOUT_L, static_cast<u8>(accel_x & 0xFF));
    setRegisterValue(MPU6050_Registers::ACCEL_YOUT_H, static_cast<u8>(accel_y >> 8));
    setRegisterValue(MPU6050_Registers::ACCEL_YOUT_L, static_cast<u8>(accel_y & 0xFF));
    setRegisterValue(MPU6050_Registers::ACCEL_ZOUT_H, static_cast<u8>(accel_z >> 8));
    setRegisterValue(MPU6050_Registers::ACCEL_ZOUT_L, static_cast<u8>(accel_z & 0xFF));
    
    // Set temperature data
    setRegisterValue(MPU6050_Registers::TEMP_OUT_H, static_cast<u8>(temp >> 8));
    setRegisterValue(MPU6050_Registers::TEMP_OUT_L, static_cast<u8>(temp & 0xFF));
    
    // Set gyroscope data
    setRegisterValue(MPU6050_Registers::GYRO_XOUT_H, static_cast<u8>(gyro_x >> 8));
    setRegisterValue(MPU6050_Registers::GYRO_XOUT_L, static_cast<u8>(gyro_x & 0xFF));
    setRegisterValue(MPU6050_Registers::GYRO_YOUT_H, static_cast<u8>(gyro_y >> 8));
    setRegisterValue(MPU6050_Registers::GYRO_YOUT_L, static_cast<u8>(gyro_y & 0xFF));
    setRegisterValue(MPU6050_Registers::GYRO_ZOUT_H, static_cast<u8>(gyro_z >> 8));
    setRegisterValue(MPU6050_Registers::GYRO_ZOUT_L, static_cast<u8>(gyro_z & 0xFF));
}

bool MockI2CInterface::shouldInjectError() const {
    if (!register_bank_.error_injection_enabled) {
        return false;
    }
    
    static std::random_device rd;
    static std::mt19937 gen(rd());
    static std::uniform_real_distribution<> dis(0.0, 1.0);
    
    return dis(gen) < register_bank_.error_injection_rate;
}

u8 MockI2CInterface::addNoise(u8 value) const {
    static std::random_device rd;
    static std::mt19937 gen(rd());
    static std::normal_distribution<> dis(0.0, register_bank_.noise_level * 255.0);
    
    double noisy_value = value + dis(gen);
    return static_cast<u8>(std::max(0.0, std::min(255.0, noisy_value)));
}

s16 MockI2CInterface::addNoise(s16 value) const {
    static std::random_device rd;
    static std::mt19937 gen(rd());
    static std::normal_distribution<> dis(0.0, register_bank_.noise_level * 32767.0);
    
    double noisy_value = value + dis(gen);
    return static_cast<s16>(std::max(-32768.0, std::min(32767.0, noisy_value)));
}