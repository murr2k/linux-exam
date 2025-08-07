/* SPDX-License-Identifier: GPL-2.0 */
/*
 * MPU-6050 6-axis gyroscope and accelerometer driver
 * 
 * Copyright (C) 2024 Murray Kopit <murr2k@gmail.com>
 */

#ifndef _MPU6050_H_
#define _MPU6050_H_

#include <linux/device.h>
#include <linux/i2c.h>
#include <linux/mutex.h>
#include <linux/types.h>

/* MPU-6050 I2C address */
#define MPU6050_I2C_ADDR		0x68

/* Register definitions */
#define MPU6050_REG_PWR_MGMT_1		0x6B
#define MPU6050_REG_GYRO_CONFIG		0x1B
#define MPU6050_REG_ACCEL_CONFIG	0x1C
#define MPU6050_REG_ACCEL_XOUT_H	0x3B
#define MPU6050_REG_GYRO_XOUT_H		0x43

/* Power management bits */
#define MPU6050_PWR_MGMT_1_SLEEP	BIT(6)
#define MPU6050_PWR_MGMT_1_RESET	BIT(7)

/**
 * struct mpu6050_data - MPU-6050 device data
 * @client: I2C client
 * @dev: Device structure
 * @lock: Mutex for device access
 * @gyro_range: Current gyroscope range setting
 * @accel_range: Current accelerometer range setting
 */
struct mpu6050_data {
	struct i2c_client *client;
	struct device *dev;
	struct mutex lock;
	u8 gyro_range;
	u8 accel_range;
};

/* Function prototypes */
int mpu6050_read_raw(struct mpu6050_data *data, u8 reg, s16 *val);
int mpu6050_write_reg(struct mpu6050_data *data, u8 reg, u8 val);

#endif /* _MPU6050_H_ */