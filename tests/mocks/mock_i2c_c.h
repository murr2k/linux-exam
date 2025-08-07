/**
 * @file mock_i2c_c.h
 * @brief C-compatible mock I2C interface for MPU-6050 kernel driver testing
 * 
 * This file provides a C-compatible mock implementation of the Linux I2C
 * subsystem, allowing unit tests to run without actual hardware.
 *
 * Copyright (C) 2025 Murray Kopit <murr2k@gmail.com>
 */

#ifndef MOCK_I2C_C_H
#define MOCK_I2C_C_H

#ifdef __cplusplus
extern "C" {
#endif

/* Linux kernel type definitions for testing */
typedef unsigned char u8;
typedef unsigned short u16;
typedef signed short s16;
typedef signed int s32;

/* Error codes */
#define MOCK_EINVAL     22
#define MOCK_EIO        5
#define MOCK_ENODEV     19
#define MOCK_ETIMEDOUT  110
#define MOCK_EBUSY      16

/* I2C message flags */
#define MOCK_I2C_M_RD           0x0001
#define MOCK_I2C_M_TEN          0x0010
#define MOCK_I2C_M_DMA_SAFE     0x0200
#define MOCK_I2C_M_RECV_LEN     0x0400
#define MOCK_I2C_M_NO_RD_ACK    0x0800
#define MOCK_I2C_M_IGNORE_NAK   0x1000
#define MOCK_I2C_M_REV_DIR_ADDR 0x2000
#define MOCK_I2C_M_NOSTART      0x4000
#define MOCK_I2C_M_STOP         0x8000

/* Mock structure definitions */
struct i2c_msg {
    u16 addr;
    u16 flags;
    u16 len;
    u8 *buf;
};

struct i2c_adapter {
    int nr;
    const char* name;
    void* algo_data;
    int (*master_xfer)(struct i2c_adapter*, struct i2c_msg*, int);
    u32 (*functionality)(struct i2c_adapter*);
};

struct i2c_client {
    u16 flags;
    u16 addr;
    char name[20];
    struct i2c_adapter* adapter;
    struct device* dev;
};

struct device {
    const char* init_name;
    void* driver_data;
};

/* Mock I2C initialization and cleanup */
void mock_i2c_init(void);
void mock_i2c_cleanup(void);

/* Configuration functions */
void mock_i2c_set_device_present(int present);
void mock_i2c_set_error(int error_code);
void mock_i2c_set_error_injection(int enabled, double rate);
void mock_i2c_set_register(u8 reg, u8 value);
u8 mock_i2c_get_register(u8 reg);
void mock_i2c_set_noise(int enabled, double level);
void mock_i2c_set_delay(int delay_ms);
void mock_i2c_simulate_busy(int duration_ms);
void mock_i2c_set_partial_transfers(int enabled);

/* Sensor data simulation */
void mock_i2c_set_sensor_data(s16 accel_x, s16 accel_y, s16 accel_z,
                             s16 gyro_x, s16 gyro_y, s16 gyro_z, s16 temp);

/* Statistics functions */
int mock_i2c_get_transfer_count(void);
int mock_i2c_get_read_count(void);
int mock_i2c_get_write_count(void);
void mock_i2c_reset_stats(void);

/* Mock I2C operation functions */
int mock_i2c_transfer(struct i2c_adapter *adapter, struct i2c_msg *msgs, int num);
int mock_i2c_smbus_read_byte_data(const struct i2c_client *client, u8 command);
int mock_i2c_smbus_write_byte_data(const struct i2c_client *client, u8 command, u8 value);
int mock_i2c_smbus_read_word_data(const struct i2c_client *client, u8 command);
int mock_i2c_smbus_write_word_data(const struct i2c_client *client, u8 command, u16 value);
int mock_i2c_smbus_read_i2c_block_data(const struct i2c_client *client, u8 command, 
                                      u8 length, u8 *values);
int mock_i2c_smbus_write_i2c_block_data(const struct i2c_client *client, u8 command,
                                       u8 length, const u8 *values);
int mock_i2c_check_functionality(struct i2c_adapter *adapter, u32 func);

/* High-level test setup functions */
void mock_i2c_setup_mpu6050_defaults(void);

/* Convenience macros for test setup */
#define SETUP_MOCK_I2C_SUCCESS() \
    do { \
        mock_i2c_init(); \
        mock_i2c_set_device_present(1); \
        mock_i2c_set_error(0); \
    } while(0)

#define SETUP_MOCK_I2C_DEVICE_NOT_FOUND() \
    do { \
        mock_i2c_init(); \
        mock_i2c_set_device_present(0); \
    } while(0)

#define SETUP_MOCK_I2C_ERROR(error) \
    do { \
        mock_i2c_init(); \
        mock_i2c_set_device_present(1); \
        mock_i2c_set_error(error); \
    } while(0)

#define SETUP_MOCK_I2C_MPU6050() \
    do { \
        mock_i2c_setup_mpu6050_defaults(); \
    } while(0)

#define EXPECT_MOCK_I2C_TRANSFER_COUNT(expected) \
    do { \
        int actual = mock_i2c_get_transfer_count(); \
        if (actual != expected) { \
            printf("FAIL: Expected %d transfers, got %d\n", expected, actual); \
        } else { \
            printf("PASS: Transfer count matches (%d)\n", expected); \
        } \
    } while(0)

#define EXPECT_MOCK_I2C_READ_COUNT(expected) \
    do { \
        int actual = mock_i2c_get_read_count(); \
        if (actual != expected) { \
            printf("FAIL: Expected %d reads, got %d\n", expected, actual); \
        } else { \
            printf("PASS: Read count matches (%d)\n", expected); \
        } \
    } while(0)

#define EXPECT_MOCK_I2C_WRITE_COUNT(expected) \
    do { \
        int actual = mock_i2c_get_write_count(); \
        if (actual != expected) { \
            printf("FAIL: Expected %d writes, got %d\n", expected, actual); \
        } else { \
            printf("PASS: Write count matches (%d)\n", expected); \
        } \
    } while(0)

/* MPU-6050 specific register definitions for testing */
#define MPU6050_REG_WHO_AM_I        0x75
#define MPU6050_REG_PWR_MGMT_1      0x6B
#define MPU6050_REG_PWR_MGMT_2      0x6C
#define MPU6050_REG_CONFIG          0x1A
#define MPU6050_REG_GYRO_CONFIG     0x1B
#define MPU6050_REG_ACCEL_CONFIG    0x1C
#define MPU6050_REG_ACCEL_XOUT_H    0x3B
#define MPU6050_REG_ACCEL_XOUT_L    0x3C
#define MPU6050_REG_ACCEL_YOUT_H    0x3D
#define MPU6050_REG_ACCEL_YOUT_L    0x3E
#define MPU6050_REG_ACCEL_ZOUT_H    0x3F
#define MPU6050_REG_ACCEL_ZOUT_L    0x40
#define MPU6050_REG_TEMP_OUT_H      0x41
#define MPU6050_REG_TEMP_OUT_L      0x42
#define MPU6050_REG_GYRO_XOUT_H     0x43
#define MPU6050_REG_GYRO_XOUT_L     0x44
#define MPU6050_REG_GYRO_YOUT_H     0x45
#define MPU6050_REG_GYRO_YOUT_L     0x46
#define MPU6050_REG_GYRO_ZOUT_H     0x47
#define MPU6050_REG_GYRO_ZOUT_L     0x48

/* Expected values */
#define MPU6050_WHO_AM_I_VALUE      0x68
#define MPU6050_PWR_MGMT_1_RESET    0x80
#define MPU6050_PWR_MGMT_1_NORMAL   0x00

/* Helper functions for common test scenarios */

/**
 * @brief Setup mock for successful MPU-6050 initialization test
 */
static inline void setup_mock_mpu6050_init_success(void) {
    SETUP_MOCK_I2C_SUCCESS();
    mock_i2c_set_register(MPU6050_REG_WHO_AM_I, MPU6050_WHO_AM_I_VALUE);
    mock_i2c_set_register(MPU6050_REG_PWR_MGMT_1, 0x40);  /* Sleep mode initially */
}

/**
 * @brief Setup mock for failed MPU-6050 initialization (wrong device ID)
 */
static inline void setup_mock_mpu6050_init_wrong_id(void) {
    SETUP_MOCK_I2C_SUCCESS();
    mock_i2c_set_register(MPU6050_REG_WHO_AM_I, 0x69);  /* Wrong device ID */
}

/**
 * @brief Setup mock for I2C communication failure
 */
static inline void setup_mock_mpu6050_i2c_failure(void) {
    SETUP_MOCK_I2C_ERROR(MOCK_EIO);
}

/**
 * @brief Setup mock with realistic sensor data
 */
static inline void setup_mock_mpu6050_with_sensor_data(void) {
    SETUP_MOCK_I2C_MPU6050();
    /* Set realistic stationary sensor data */
    mock_i2c_set_sensor_data(0, 0, 16384, 0, 0, 0, 8400);  /* 1g on Z, 25°C */
}

/**
 * @brief Setup mock with noisy sensor data
 */
static inline void setup_mock_mpu6050_with_noise(void) {
    setup_mock_mpu6050_with_sensor_data();
    mock_i2c_set_noise(1, 0.1);  /* 10% noise level */
}

/**
 * @brief Verify basic MPU-6050 register access
 * @return 1 if successful, 0 if failed
 */
int verify_mock_mpu6050_basic_access(void);

/**
 * @brief Verify sensor data reading functionality
 * @return 1 if successful, 0 if failed
 */
int verify_mock_mpu6050_sensor_data(void);

/**
 * @brief Verify error handling in mock
 * @return 1 if successful, 0 if failed
 */
int verify_mock_mpu6050_error_handling(void);

#ifdef __cplusplus
}
#endif

#endif /* MOCK_I2C_C_H */