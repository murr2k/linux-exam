/**
 * @file mock_i2c.h
 * @brief Mock I2C interface for MPU-6050 kernel driver testing
 * 
 * This file provides a comprehensive mock implementation of the Linux I2C
 * subsystem, allowing unit tests to run without actual hardware. It supports
 * configurable return values, error injection, and behavior verification.
 */

#ifndef MOCK_I2C_H
#define MOCK_I2C_H

#include <gmock/gmock.h>
#include <map>
#include <vector>
#include <memory>
#include <functional>

extern "C" {
    // Mock Linux kernel types and constants
    typedef unsigned char u8;
    typedef unsigned short u16;
    typedef signed short s16;
    typedef int s32;
    
    #define EINVAL 22
    #define EIO 5
    #define ENODEV 19
    #define ETIMEDOUT 110
    #define EBUSY 16
    
    // I2C message flags
    #define I2C_M_RD 0x0001
    #define I2C_M_TEN 0x0010
    #define I2C_M_DMA_SAFE 0x0200
    #define I2C_M_RECV_LEN 0x0400
    #define I2C_M_NO_RD_ACK 0x0800
    #define I2C_M_IGNORE_NAK 0x1000
    #define I2C_M_REV_DIR_ADDR 0x2000
    #define I2C_M_NOSTART 0x4000
    #define I2C_M_STOP 0x8000
}

// Forward declarations for kernel structures
struct i2c_adapter;
struct i2c_client;
struct i2c_msg;
struct device;

// Mock I2C message structure
struct i2c_msg {
    u16 addr;
    u16 flags;
    u16 len;
    u8 *buf;
};

// Mock I2C adapter structure
struct i2c_adapter {
    int nr;
    const char* name;
    void* algo_data;
    
    // Mock methods
    int (*master_xfer)(struct i2c_adapter*, struct i2c_msg*, int);
    u32 (*functionality)(struct i2c_adapter*);
};

// Mock I2C client structure  
struct i2c_client {
    u16 flags;
    u16 addr;
    char name[20];
    struct i2c_adapter* adapter;
    struct device* dev;
};

// Mock device structure (minimal)
struct device {
    const char* init_name;
    void* driver_data;
};

/**
 * @class MockI2CInterface
 * @brief Comprehensive mock for I2C operations
 * 
 * This class provides a full mock implementation of I2C operations with
 * configurable behavior for testing various scenarios including success,
 * failure, and edge cases.
 */
class MockI2CInterface {
public:
    static MockI2CInterface& getInstance() {
        static MockI2CInterface instance;
        return instance;
    }
    
    // Mock methods that will be called by the driver
    MOCK_METHOD(int, i2c_transfer, (struct i2c_adapter* adapter, struct i2c_msg* msgs, int num));
    MOCK_METHOD(s32, i2c_smbus_read_byte_data, (const struct i2c_client* client, u8 command));
    MOCK_METHOD(s32, i2c_smbus_write_byte_data, (const struct i2c_client* client, u8 command, u8 value));
    MOCK_METHOD(s32, i2c_smbus_read_word_data, (const struct i2c_client* client, u8 command));
    MOCK_METHOD(s32, i2c_smbus_write_word_data, (const struct i2c_client* client, u8 command, u16 value));
    MOCK_METHOD(s32, i2c_smbus_read_i2c_block_data, (const struct i2c_client* client, u8 command, u8 length, u8* values));
    MOCK_METHOD(s32, i2c_smbus_write_i2c_block_data, (const struct i2c_client* client, u8 command, u8 length, const u8* values));
    
    // Configuration methods for test setup
    void setDefaultBehavior();
    void simulateDevicePresent(bool present);
    void simulateI2CError(int error_code);
    void setRegisterValue(u8 reg, u8 value);
    void setRegisterValue(u8 reg, u16 value);
    u8 getRegisterValue(u8 reg) const;
    void clearRegisterValues();
    void enableErrorInjection(bool enable);
    void setErrorInjectionRate(double rate);
    
    // Advanced simulation features
    void simulateNoiseInReads(bool enable, double noise_level = 0.1);
    void simulateBusyBus(int busy_duration_ms);
    void simulatePartialTransfers(bool enable);
    void setTransferDelay(int delay_ms);
    
    // Statistics and verification helpers
    int getTransferCount() const { return transfer_count_; }
    int getReadCount() const { return read_count_; }
    int getWriteCount() const { return write_count_; }
    void resetStatistics();
    
    // Register access simulation
    struct RegisterBank {
        std::map<u8, u8> byte_registers;
        std::map<u8, u16> word_registers;
        bool device_present = true;
        int error_code = 0;
        bool error_injection_enabled = false;
        double error_injection_rate = 0.0;
        bool noise_enabled = false;
        double noise_level = 0.1;
        int transfer_delay_ms = 0;
    };
    
    RegisterBank& getRegisterBank() { return register_bank_; }
    
    // Test helper methods
    void setupMPU6050Defaults();
    void simulateCalibrationData();
    void simulateSensorData(s16 accel_x, s16 accel_y, s16 accel_z,
                           s16 gyro_x, s16 gyro_y, s16 gyro_z, s16 temp);

private:
    RegisterBank register_bank_;
    mutable int transfer_count_ = 0;
    mutable int read_count_ = 0;
    mutable int write_count_ = 0;
    
    MockI2CInterface() = default;
    ~MockI2CInterface() = default;
    MockI2CInterface(const MockI2CInterface&) = delete;
    MockI2CInterface& operator=(const MockI2CInterface&) = delete;
    
    // Internal helper methods
    bool shouldInjectError() const;
    u8 addNoise(u8 value) const;
    s16 addNoise(s16 value) const;
};

// C function wrappers that delegate to the mock
extern "C" {
    int mock_i2c_transfer(struct i2c_adapter* adapter, struct i2c_msg* msgs, int num);
    s32 mock_i2c_smbus_read_byte_data(const struct i2c_client* client, u8 command);
    s32 mock_i2c_smbus_write_byte_data(const struct i2c_client* client, u8 command, u8 value);
    s32 mock_i2c_smbus_read_word_data(const struct i2c_client* client, u8 command);
    s32 mock_i2c_smbus_write_word_data(const struct i2c_client* client, u8 command, u16 value);
    s32 mock_i2c_smbus_read_i2c_block_data(const struct i2c_client* client, u8 command, u8 length, u8* values);
    s32 mock_i2c_smbus_write_i2c_block_data(const struct i2c_client* client, u8 command, u8 length, const u8* values);
}

// Convenience macros for test setup
#define SETUP_I2C_SUCCESS() \
    MockI2CInterface::getInstance().setDefaultBehavior(); \
    MockI2CInterface::getInstance().simulateDevicePresent(true)

#define SETUP_I2C_DEVICE_NOT_FOUND() \
    MockI2CInterface::getInstance().simulateDevicePresent(false)

#define SETUP_I2C_ERROR(error) \
    MockI2CInterface::getInstance().simulateI2CError(error)

#define EXPECT_I2C_READ(reg, value) \
    MockI2CInterface::getInstance().setRegisterValue(reg, value)

#define EXPECT_I2C_TRANSFER_COUNT(count) \
    EXPECT_EQ(MockI2CInterface::getInstance().getTransferCount(), count)

// MPU-6050 specific register definitions for testing
namespace MPU6050_Registers {
    constexpr u8 WHO_AM_I = 0x75;
    constexpr u8 PWR_MGMT_1 = 0x6B;
    constexpr u8 PWR_MGMT_2 = 0x6C;
    constexpr u8 CONFIG = 0x1A;
    constexpr u8 GYRO_CONFIG = 0x1B;
    constexpr u8 ACCEL_CONFIG = 0x1C;
    constexpr u8 ACCEL_XOUT_H = 0x3B;
    constexpr u8 ACCEL_XOUT_L = 0x3C;
    constexpr u8 ACCEL_YOUT_H = 0x3D;
    constexpr u8 ACCEL_YOUT_L = 0x3E;
    constexpr u8 ACCEL_ZOUT_H = 0x3F;
    constexpr u8 ACCEL_ZOUT_L = 0x40;
    constexpr u8 TEMP_OUT_H = 0x41;
    constexpr u8 TEMP_OUT_L = 0x42;
    constexpr u8 GYRO_XOUT_H = 0x43;
    constexpr u8 GYRO_XOUT_L = 0x44;
    constexpr u8 GYRO_YOUT_H = 0x45;
    constexpr u8 GYRO_YOUT_L = 0x46;
    constexpr u8 GYRO_ZOUT_H = 0x47;
    constexpr u8 GYRO_ZOUT_L = 0x48;
    
    // Expected values
    constexpr u8 WHO_AM_I_VALUE = 0x68;
    constexpr u8 PWR_MGMT_1_RESET = 0x80;
    constexpr u8 PWR_MGMT_1_NORMAL = 0x00;
}

#endif // MOCK_I2C_H