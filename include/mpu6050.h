/*
 * MPU-6050 6-axis motion tracking device driver header
 *
 * This file contains register definitions, data structures, and IOCTL commands
 * for the MPU-6050 accelerometer and gyroscope sensor driver.
 *
 * Copyright (C) 2025 Murray Kopit <murr2k@gmail.com>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 */

#ifndef _MPU6050_H_
#define _MPU6050_H_

#ifdef __KERNEL__
#include <linux/types.h>
#include <linux/ioctl.h>
#else
#include <stdint.h>
#include <sys/ioctl.h>
/* Define kernel types for userspace */
typedef uint8_t u8;
typedef int16_t s16;
typedef int32_t s32;
#endif

/* MPU-6050 I2C addresses */
#define MPU6050_I2C_ADDR_LOW	0x68	/* AD0 pin low */
#define MPU6050_I2C_ADDR_HIGH	0x69	/* AD0 pin high */

/* MPU-6050 Register Map */
#define MPU6050_REG_SELF_TEST_X		0x0D
#define MPU6050_REG_SELF_TEST_Y		0x0E
#define MPU6050_REG_SELF_TEST_Z		0x0F
#define MPU6050_REG_SELF_TEST_A		0x10
#define MPU6050_REG_SMPLRT_DIV		0x19
#define MPU6050_REG_CONFIG		0x1A
#define MPU6050_REG_GYRO_CONFIG		0x1B
#define MPU6050_REG_ACCEL_CONFIG	0x1C
#define MPU6050_REG_FIFO_EN		0x23
#define MPU6050_REG_I2C_MST_CTRL	0x24
#define MPU6050_REG_I2C_SLV0_ADDR	0x25
#define MPU6050_REG_I2C_SLV0_REG	0x26
#define MPU6050_REG_I2C_SLV0_CTRL	0x27
#define MPU6050_REG_INT_PIN_CFG		0x37
#define MPU6050_REG_INT_ENABLE		0x38
#define MPU6050_REG_INT_STATUS		0x3A

/* Sensor Data Registers */
#define MPU6050_REG_ACCEL_XOUT_H	0x3B
#define MPU6050_REG_ACCEL_XOUT_L	0x3C
#define MPU6050_REG_ACCEL_YOUT_H	0x3D
#define MPU6050_REG_ACCEL_YOUT_L	0x3E
#define MPU6050_REG_ACCEL_ZOUT_H	0x3F
#define MPU6050_REG_ACCEL_ZOUT_L	0x40

#define MPU6050_REG_TEMP_OUT_H		0x41
#define MPU6050_REG_TEMP_OUT_L		0x42

#define MPU6050_REG_GYRO_XOUT_H		0x43
#define MPU6050_REG_GYRO_XOUT_L		0x44
#define MPU6050_REG_GYRO_YOUT_H		0x45
#define MPU6050_REG_GYRO_YOUT_L		0x46
#define MPU6050_REG_GYRO_ZOUT_H		0x47
#define MPU6050_REG_GYRO_ZOUT_L		0x48

/* Power Management Registers */
#define MPU6050_REG_PWR_MGMT_1		0x6B
#define MPU6050_REG_PWR_MGMT_2		0x6C
#define MPU6050_REG_WHO_AM_I		0x75

/* Power Management 1 bits */
#define MPU6050_PWR1_DEVICE_RESET	BIT(7)
#define MPU6050_PWR1_SLEEP		BIT(6)
#define MPU6050_PWR1_CYCLE		BIT(5)
#define MPU6050_PWR1_TEMP_DIS		BIT(3)
#define MPU6050_PWR1_CLKSEL_MASK	0x07

/* Clock source selection */
#define MPU6050_CLKSEL_INTERNAL		0x00
#define MPU6050_CLKSEL_PLL_XGYRO	0x01
#define MPU6050_CLKSEL_PLL_YGYRO	0x02
#define MPU6050_CLKSEL_PLL_ZGYRO	0x03
#define MPU6050_CLKSEL_PLL_EXT32K	0x04
#define MPU6050_CLKSEL_PLL_EXT19M	0x05
#define MPU6050_CLKSEL_STOP		0x07

/* Gyroscope Configuration bits */
#define MPU6050_GYRO_FS_250		0x00
#define MPU6050_GYRO_FS_500		0x01
#define MPU6050_GYRO_FS_1000		0x02
#define MPU6050_GYRO_FS_2000		0x03
#define MPU6050_GYRO_FS_SEL_MASK	0x18

/* Accelerometer Configuration bits */
#define MPU6050_ACCEL_FS_2G		0x00
#define MPU6050_ACCEL_FS_4G		0x01
#define MPU6050_ACCEL_FS_8G		0x02
#define MPU6050_ACCEL_FS_16G		0x03
#define MPU6050_ACCEL_FS_SEL_MASK	0x18

/* WHO_AM_I register value */
#define MPU6050_WHO_AM_I_VAL		0x68

/* Default sample rate divider (1kHz / (1 + 7) = 125Hz) */
#define MPU6050_DEFAULT_SMPLRT_DIV	0x07

/* Data structures */

/**
 * struct mpu6050_raw_data - Raw sensor data from MPU-6050
 * @accel_x: Raw accelerometer X-axis data
 * @accel_y: Raw accelerometer Y-axis data
 * @accel_z: Raw accelerometer Z-axis data
 * @temp: Raw temperature data
 * @gyro_x: Raw gyroscope X-axis data
 * @gyro_y: Raw gyroscope Y-axis data
 * @gyro_z: Raw gyroscope Z-axis data
 */
struct mpu6050_raw_data {
	s16 accel_x;
	s16 accel_y;
	s16 accel_z;
	s16 temp;
	s16 gyro_x;
	s16 gyro_y;
	s16 gyro_z;
};

/**
 * struct mpu6050_config - MPU-6050 configuration parameters
 * @sample_rate_div: Sample rate divider (0-255)
 * @gyro_range: Gyroscope full scale range
 * @accel_range: Accelerometer full scale range
 * @dlpf_cfg: Digital Low Pass Filter configuration
 */
struct mpu6050_config {
	u8 sample_rate_div;
	u8 gyro_range;
	u8 accel_range;
	u8 dlpf_cfg;
};

/**
 * struct mpu6050_scaled_data - Scaled sensor data
 * @accel_x: Accelerometer X-axis (mg)
 * @accel_y: Accelerometer Y-axis (mg)
 * @accel_z: Accelerometer Z-axis (mg)
 * @temp: Temperature (degrees Celsius * 100)
 * @gyro_x: Gyroscope X-axis (mdps - millidegrees per second)
 * @gyro_y: Gyroscope Y-axis (mdps)
 * @gyro_z: Gyroscope Z-axis (mdps)
 */
struct mpu6050_scaled_data {
	s32 accel_x;
	s32 accel_y;
	s32 accel_z;
	s32 temp;
	s32 gyro_x;
	s32 gyro_y;
	s32 gyro_z;
};

/* IOCTL commands */
#define MPU6050_IOC_MAGIC		'M'
#define MPU6050_IOC_READ_RAW		_IOR(MPU6050_IOC_MAGIC, 0, struct mpu6050_raw_data)
#define MPU6050_IOC_READ_SCALED		_IOR(MPU6050_IOC_MAGIC, 1, struct mpu6050_scaled_data)
#define MPU6050_IOC_SET_CONFIG		_IOW(MPU6050_IOC_MAGIC, 2, struct mpu6050_config)
#define MPU6050_IOC_GET_CONFIG		_IOR(MPU6050_IOC_MAGIC, 3, struct mpu6050_config)
#define MPU6050_IOC_RESET		_IO(MPU6050_IOC_MAGIC, 4)
#define MPU6050_IOC_SELF_TEST		_IOR(MPU6050_IOC_MAGIC, 5, u32)
#define MPU6050_IOC_WHO_AM_I		_IOR(MPU6050_IOC_MAGIC, 6, u8)

#define MPU6050_IOC_MAXNR		6

/* Error codes */
#define MPU6050_ERR_I2C_FAILED		-1
#define MPU6050_ERR_INVALID_CHIP	-2
#define MPU6050_ERR_CONFIG_FAILED	-3
#define MPU6050_ERR_READ_FAILED		-4

#endif /* _MPU6050_H_ */