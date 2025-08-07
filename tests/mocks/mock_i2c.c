/**
 * @file mock_i2c.c
 * @brief Mock I2C implementation for MPU-6050 kernel driver testing
 * 
 * This file provides the C implementation of the I2C mock interface,
 * supporting various test scenarios including success, failure, and edge cases.
 *
 * Copyright (C) 2025 Murray Kopit <murr2k@gmail.com>
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <time.h>

#include "mock_i2c.h"

/* Global mock state */
struct mock_i2c_state {
    /* Register simulation */
    unsigned char registers[256];
    int device_present;
    int error_code;
    int error_injection_enabled;
    double error_injection_rate;
    
    /* Statistics */
    int transfer_count;
    int read_count;
    int write_count;
    
    /* Behavior control */
    int noise_enabled;
    double noise_level;
    int transfer_delay_ms;
    int busy_duration_ms;
    int partial_transfers_enabled;
    
    /* MPU-6050 specific simulation */
    int mpu6050_initialized;
    struct {
        short accel_x, accel_y, accel_z;
        short gyro_x, gyro_y, gyro_z;
        short temperature;
    } sensor_data;
};

static struct mock_i2c_state mock_state = {
    .device_present = 1,
    .error_code = 0,
    .error_injection_enabled = 0,
    .error_injection_rate = 0.0,
    .transfer_count = 0,
    .read_count = 0,
    .write_count = 0,
    .noise_enabled = 0,
    .noise_level = 0.1,
    .transfer_delay_ms = 0,
    .busy_duration_ms = 0,
    .partial_transfers_enabled = 0,
    .mpu6050_initialized = 0
};

/* Helper functions */
static int should_inject_error(void)
{
    if (!mock_state.error_injection_enabled)
        return 0;
        
    return (double)rand() / RAND_MAX < mock_state.error_injection_rate;
}

static unsigned char add_noise_u8(unsigned char value)
{
    if (!mock_state.noise_enabled)
        return value;
        
    int noise = (int)((double)rand() / RAND_MAX * 256 * mock_state.noise_level) - 
                (int)(128 * mock_state.noise_level);
    int result = (int)value + noise;
    
    if (result < 0) result = 0;
    if (result > 255) result = 255;
    
    return (unsigned char)result;
}

static short add_noise_s16(short value)
{
    if (!mock_state.noise_enabled)
        return value;
        
    int noise = (int)((double)rand() / RAND_MAX * 65536 * mock_state.noise_level) - 
                (int)(32768 * mock_state.noise_level);
    int result = (int)value + noise;
    
    if (result < -32768) result = -32768;
    if (result > 32767) result = 32767;
    
    return (short)result;
}

static void simulate_transfer_delay(void)
{
    if (mock_state.transfer_delay_ms > 0) {
        usleep(mock_state.transfer_delay_ms * 1000);
    }
}

static void simulate_busy_bus(void)
{
    if (mock_state.busy_duration_ms > 0) {
        usleep(mock_state.busy_duration_ms * 1000);
        mock_state.busy_duration_ms = 0; /* One-time simulation */
    }
}

/* Initialize mock I2C system */
void mock_i2c_init(void)
{
    memset(&mock_state, 0, sizeof(mock_state));
    mock_state.device_present = 1;
    
    /* Initialize MPU-6050 default register values */
    mock_state.registers[0x75] = 0x68; /* WHO_AM_I */
    mock_state.registers[0x6B] = 0x40; /* PWR_MGMT_1, sleep mode */
    mock_state.registers[0x6C] = 0x00; /* PWR_MGMT_2 */
    mock_state.registers[0x1A] = 0x00; /* CONFIG */
    mock_state.registers[0x1B] = 0x00; /* GYRO_CONFIG */
    mock_state.registers[0x1C] = 0x00; /* ACCEL_CONFIG */
    mock_state.registers[0x19] = 0x00; /* SMPLRT_DIV */
    
    /* Initialize sensor data to reasonable values */
    mock_state.sensor_data.accel_x = 0;
    mock_state.sensor_data.accel_y = 0;
    mock_state.sensor_data.accel_z = 16384; /* 1g on Z-axis */
    mock_state.sensor_data.gyro_x = 0;
    mock_state.sensor_data.gyro_y = 0;
    mock_state.sensor_data.gyro_z = 0;
    mock_state.sensor_data.temperature = 8400; /* ~25°C */
}

/* Set device presence simulation */
void mock_i2c_set_device_present(int present)
{
    mock_state.device_present = present;
}

/* Set error code for simulation */
void mock_i2c_set_error(int error_code)
{
    mock_state.error_code = error_code;
}

/* Enable/disable error injection */
void mock_i2c_set_error_injection(int enabled, double rate)
{
    mock_state.error_injection_enabled = enabled;
    mock_state.error_injection_rate = rate;
}

/* Set register value */
void mock_i2c_set_register(unsigned char reg, unsigned char value)
{
    mock_state.registers[reg] = value;
}

/* Get register value */
unsigned char mock_i2c_get_register(unsigned char reg)
{
    return mock_state.registers[reg];
}

/* Enable noise simulation */
void mock_i2c_set_noise(int enabled, double level)
{
    mock_state.noise_enabled = enabled;
    mock_state.noise_level = level;
}

/* Set transfer delay */
void mock_i2c_set_delay(int delay_ms)
{
    mock_state.transfer_delay_ms = delay_ms;
}

/* Simulate busy bus */
void mock_i2c_simulate_busy(int duration_ms)
{
    mock_state.busy_duration_ms = duration_ms;
}

/* Enable partial transfers */
void mock_i2c_set_partial_transfers(int enabled)
{
    mock_state.partial_transfers_enabled = enabled;
}

/* Set sensor data for simulation */
void mock_i2c_set_sensor_data(short accel_x, short accel_y, short accel_z,
                             short gyro_x, short gyro_y, short gyro_z, short temp)
{
    mock_state.sensor_data.accel_x = accel_x;
    mock_state.sensor_data.accel_y = accel_y;
    mock_state.sensor_data.accel_z = accel_z;
    mock_state.sensor_data.gyro_x = gyro_x;
    mock_state.sensor_data.gyro_y = gyro_y;
    mock_state.sensor_data.gyro_z = gyro_z;
    mock_state.sensor_data.temperature = temp;
    
    /* Update register values to reflect sensor data */
    mock_state.registers[0x3B] = (accel_x >> 8) & 0xFF;
    mock_state.registers[0x3C] = accel_x & 0xFF;
    mock_state.registers[0x3D] = (accel_y >> 8) & 0xFF;
    mock_state.registers[0x3E] = accel_y & 0xFF;
    mock_state.registers[0x3F] = (accel_z >> 8) & 0xFF;
    mock_state.registers[0x40] = accel_z & 0xFF;
    mock_state.registers[0x41] = (temp >> 8) & 0xFF;
    mock_state.registers[0x42] = temp & 0xFF;
    mock_state.registers[0x43] = (gyro_x >> 8) & 0xFF;
    mock_state.registers[0x44] = gyro_x & 0xFF;
    mock_state.registers[0x45] = (gyro_y >> 8) & 0xFF;
    mock_state.registers[0x46] = gyro_y & 0xFF;
    mock_state.registers[0x47] = (gyro_z >> 8) & 0xFF;
    mock_state.registers[0x48] = gyro_z & 0xFF;
}

/* Get statistics */
int mock_i2c_get_transfer_count(void)
{
    return mock_state.transfer_count;
}

int mock_i2c_get_read_count(void)
{
    return mock_state.read_count;
}

int mock_i2c_get_write_count(void)
{
    return mock_state.write_count;
}

/* Reset statistics */
void mock_i2c_reset_stats(void)
{
    mock_state.transfer_count = 0;
    mock_state.read_count = 0;
    mock_state.write_count = 0;
}

/* Mock I2C transfer function */
int mock_i2c_transfer(struct i2c_adapter *adapter, struct i2c_msg *msgs, int num)
{
    if (!mock_state.device_present)
        return -ENODEV;
        
    if (mock_state.error_code != 0)
        return -mock_state.error_code;
        
    if (should_inject_error())
        return -EIO;
        
    simulate_busy_bus();
    simulate_transfer_delay();
    
    mock_state.transfer_count++;
    
    /* Process each message */
    for (int i = 0; i < num; i++) {
        struct i2c_msg *msg = &msgs[i];
        
        if (msg->flags & I2C_M_RD) {
            /* Read operation */
            mock_state.read_count++;
            for (int j = 0; j < msg->len; j++) {
                unsigned char reg = (i > 0) ? msgs[i-1].buf[0] + j : 0x75; /* Default to WHO_AM_I */
                msg->buf[j] = add_noise_u8(mock_state.registers[reg]);
            }
        } else {
            /* Write operation */
            mock_state.write_count++;
            if (msg->len >= 2) {
                unsigned char reg = msg->buf[0];
                unsigned char value = msg->buf[1];
                mock_state.registers[reg] = value;
                
                /* Handle special registers */
                if (reg == 0x6B && (value & 0x80)) {
                    /* Device reset */
                    mock_i2c_init();
                }
            }
        }
        
        if (mock_state.partial_transfers_enabled && (rand() % 4 == 0)) {
            /* Simulate partial transfer */
            return i; /* Return number of successful messages */
        }
    }
    
    return num; /* All messages successful */
}

/* Mock SMBUS read byte data */
int mock_i2c_smbus_read_byte_data(const struct i2c_client *client, unsigned char command)
{
    if (!mock_state.device_present)
        return -ENODEV;
        
    if (mock_state.error_code != 0)
        return -mock_state.error_code;
        
    if (should_inject_error())
        return -EIO;
        
    simulate_transfer_delay();
    mock_state.transfer_count++;
    mock_state.read_count++;
    
    return add_noise_u8(mock_state.registers[command]);
}

/* Mock SMBUS write byte data */
int mock_i2c_smbus_write_byte_data(const struct i2c_client *client, unsigned char command, unsigned char value)
{
    if (!mock_state.device_present)
        return -ENODEV;
        
    if (mock_state.error_code != 0)
        return -mock_state.error_code;
        
    if (should_inject_error())
        return -EIO;
        
    simulate_transfer_delay();
    mock_state.transfer_count++;
    mock_state.write_count++;
    
    mock_state.registers[command] = value;
    
    /* Handle special registers */
    if (command == 0x6B && (value & 0x80)) {
        /* Device reset */
        mock_i2c_init();
    }
    
    return 0;
}

/* Mock SMBUS read word data */
int mock_i2c_smbus_read_word_data(const struct i2c_client *client, unsigned char command)
{
    if (!mock_state.device_present)
        return -ENODEV;
        
    if (mock_state.error_code != 0)
        return -mock_state.error_code;
        
    if (should_inject_error())
        return -EIO;
        
    simulate_transfer_delay();
    mock_state.transfer_count++;
    mock_state.read_count++;
    
    /* Return little-endian word */
    unsigned short word = (mock_state.registers[command + 1] << 8) | mock_state.registers[command];
    return add_noise_s16((short)word);
}

/* Mock SMBUS write word data */
int mock_i2c_smbus_write_word_data(const struct i2c_client *client, unsigned char command, unsigned short value)
{
    if (!mock_state.device_present)
        return -ENODEV;
        
    if (mock_state.error_code != 0)
        return -mock_state.error_code;
        
    if (should_inject_error())
        return -EIO;
        
    simulate_transfer_delay();
    mock_state.transfer_count++;
    mock_state.write_count++;
    
    mock_state.registers[command] = value & 0xFF;
    mock_state.registers[command + 1] = (value >> 8) & 0xFF;
    
    return 0;
}

/* Mock SMBUS read I2C block data */
int mock_i2c_smbus_read_i2c_block_data(const struct i2c_client *client, unsigned char command, 
                                      unsigned char length, unsigned char *values)
{
    if (!mock_state.device_present)
        return -ENODEV;
        
    if (mock_state.error_code != 0)
        return -mock_state.error_code;
        
    if (should_inject_error())
        return -EIO;
        
    simulate_transfer_delay();
    mock_state.transfer_count++;
    mock_state.read_count++;
    
    /* Read block of data */
    for (int i = 0; i < length; i++) {
        values[i] = add_noise_u8(mock_state.registers[command + i]);
    }
    
    if (mock_state.partial_transfers_enabled && (rand() % 4 == 0)) {
        /* Return partial read */
        return length / 2;
    }
    
    return length;
}

/* Mock SMBUS write I2C block data */
int mock_i2c_smbus_write_i2c_block_data(const struct i2c_client *client, unsigned char command,
                                       unsigned char length, const unsigned char *values)
{
    if (!mock_state.device_present)
        return -ENODEV;
        
    if (mock_state.error_code != 0)
        return -mock_state.error_code;
        
    if (should_inject_error())
        return -EIO;
        
    simulate_transfer_delay();
    mock_state.transfer_count++;
    mock_state.write_count++;
    
    /* Write block of data */
    for (int i = 0; i < length; i++) {
        mock_state.registers[command + i] = values[i];
    }
    
    return 0;
}

/* Check I2C functionality */
int mock_i2c_check_functionality(struct i2c_adapter *adapter, unsigned int func)
{
    /* Simulate full I2C functionality */
    return 1;
}

/* Setup default MPU-6050 behavior */
void mock_i2c_setup_mpu6050_defaults(void)
{
    mock_i2c_init();
    mock_state.mpu6050_initialized = 1;
    
    /* Set realistic sensor values */
    mock_i2c_set_sensor_data(100, -200, 16000,  /* Slight tilt */
                            50, -30, 10,         /* Minimal rotation */
                            8500);               /* ~25°C */
}

/* Cleanup mock I2C system */
void mock_i2c_cleanup(void)
{
    memset(&mock_state, 0, sizeof(mock_state));
}