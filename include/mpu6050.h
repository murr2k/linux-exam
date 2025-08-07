/* SPDX-License-Identifier: GPL-2.0 */
/*
 * MPU-6050 6-axis gyroscope and accelerometer driver
 * 
 * Copyright (C) 2025 Murray Kopit <murr2k@gmail.com>
 */

#ifndef _MPU6050_H_
#define _MPU6050_H_

#include <linux/device.h>
#include <linux/i2c.h>
#include <linux/ioctl.h>
#include <linux/mutex.h>
#include <linux/regmap.h>
#include <linux/types.h>

/* MPU-6050 I2C addresses */
#define MPU6050_I2C_ADDR_AD0_LOW	0x68
#define MPU6050_I2C_ADDR_AD0_HIGH	0x69
#define MPU6050_I2C_ADDR		MPU6050_I2C_ADDR_AD0_LOW

/* Device identification */
#define MPU6050_WHO_AM_I_VAL		0x68
#define MPU6050_DEVICE_ID		0x68

/* Register definitions */
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
#define MPU6050_REG_I2C_SLV1_ADDR	0x28
#define MPU6050_REG_I2C_SLV1_REG	0x29
#define MPU6050_REG_I2C_SLV1_CTRL	0x2A
#define MPU6050_REG_I2C_SLV2_ADDR	0x2B
#define MPU6050_REG_I2C_SLV2_REG	0x2C
#define MPU6050_REG_I2C_SLV2_CTRL	0x2D
#define MPU6050_REG_I2C_SLV3_ADDR	0x2E
#define MPU6050_REG_I2C_SLV3_REG	0x2F
#define MPU6050_REG_I2C_SLV3_CTRL	0x30
#define MPU6050_REG_I2C_SLV4_ADDR	0x31
#define MPU6050_REG_I2C_SLV4_REG	0x32
#define MPU6050_REG_I2C_SLV4_DO		0x33
#define MPU6050_REG_I2C_SLV4_CTRL	0x34
#define MPU6050_REG_I2C_SLV4_DI		0x35
#define MPU6050_REG_I2C_MST_STATUS	0x36
#define MPU6050_REG_INT_PIN_CFG		0x37
#define MPU6050_REG_INT_ENABLE		0x38
#define MPU6050_REG_INT_STATUS		0x3A
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
#define MPU6050_REG_EXT_SENS_DATA_00	0x49
#define MPU6050_REG_EXT_SENS_DATA_01	0x4A
#define MPU6050_REG_EXT_SENS_DATA_02	0x4B
#define MPU6050_REG_EXT_SENS_DATA_03	0x4C
#define MPU6050_REG_EXT_SENS_DATA_04	0x4D
#define MPU6050_REG_EXT_SENS_DATA_05	0x4E
#define MPU6050_REG_EXT_SENS_DATA_06	0x4F
#define MPU6050_REG_EXT_SENS_DATA_07	0x50
#define MPU6050_REG_EXT_SENS_DATA_08	0x51
#define MPU6050_REG_EXT_SENS_DATA_09	0x52
#define MPU6050_REG_EXT_SENS_DATA_10	0x53
#define MPU6050_REG_EXT_SENS_DATA_11	0x54
#define MPU6050_REG_EXT_SENS_DATA_12	0x55
#define MPU6050_REG_EXT_SENS_DATA_13	0x56
#define MPU6050_REG_EXT_SENS_DATA_14	0x57
#define MPU6050_REG_EXT_SENS_DATA_15	0x58
#define MPU6050_REG_EXT_SENS_DATA_16	0x59
#define MPU6050_REG_EXT_SENS_DATA_17	0x5A
#define MPU6050_REG_EXT_SENS_DATA_18	0x5B
#define MPU6050_REG_EXT_SENS_DATA_19	0x5C
#define MPU6050_REG_EXT_SENS_DATA_20	0x5D
#define MPU6050_REG_EXT_SENS_DATA_21	0x5E
#define MPU6050_REG_EXT_SENS_DATA_22	0x5F
#define MPU6050_REG_EXT_SENS_DATA_23	0x60
#define MPU6050_REG_I2C_SLV0_DO		0x63
#define MPU6050_REG_I2C_SLV1_DO		0x64
#define MPU6050_REG_I2C_SLV2_DO		0x65
#define MPU6050_REG_I2C_SLV3_DO		0x66
#define MPU6050_REG_I2C_MST_DELAY_CTRL	0x67
#define MPU6050_REG_SIGNAL_PATH_RESET	0x68
#define MPU6050_REG_USER_CTRL		0x6A
#define MPU6050_REG_PWR_MGMT_1		0x6B
#define MPU6050_REG_PWR_MGMT_2		0x6C
#define MPU6050_REG_FIFO_COUNTH		0x72
#define MPU6050_REG_FIFO_COUNTL		0x73
#define MPU6050_REG_FIFO_R_W		0x74
#define MPU6050_REG_WHO_AM_I		0x75

/* Power management 1 register bits */
#define MPU6050_PWR1_CLKSEL_MASK	0x07
#define MPU6050_PWR1_TEMP_DIS		BIT(3)
#define MPU6050_PWR1_CYCLE		BIT(5)
#define MPU6050_PWR1_SLEEP		BIT(6)
#define MPU6050_PWR1_DEVICE_RESET	BIT(7)

/* Clock source selection */
#define MPU6050_CLKSEL_INTERNAL		0x00
#define MPU6050_CLKSEL_PLL_XGYRO	0x01
#define MPU6050_CLKSEL_PLL_YGYRO	0x02
#define MPU6050_CLKSEL_PLL_ZGYRO	0x03
#define MPU6050_CLKSEL_PLL_EXT32K	0x04
#define MPU6050_CLKSEL_PLL_EXT19M	0x05
#define MPU6050_CLKSEL_STOP		0x07

/* Power management 2 register bits */
#define MPU6050_PWR2_STBY_ZG		BIT(0)
#define MPU6050_PWR2_STBY_YG		BIT(1)
#define MPU6050_PWR2_STBY_XG		BIT(2)
#define MPU6050_PWR2_STBY_ZA		BIT(3)
#define MPU6050_PWR2_STBY_YA		BIT(4)
#define MPU6050_PWR2_STBY_XA		BIT(5)
#define MPU6050_PWR2_LP_WAKE_CTRL_MASK	0xC0

/* Gyroscope configuration */
#define MPU6050_GYRO_FS_SEL_MASK	0x18
#define MPU6050_GYRO_FS_250		0x00
#define MPU6050_GYRO_FS_500		0x01
#define MPU6050_GYRO_FS_1000		0x02
#define MPU6050_GYRO_FS_2000		0x03

/* Accelerometer configuration */
#define MPU6050_ACCEL_FS_SEL_MASK	0x18
#define MPU6050_ACCEL_FS_2G		0x00
#define MPU6050_ACCEL_FS_4G		0x01
#define MPU6050_ACCEL_FS_8G		0x02
#define MPU6050_ACCEL_FS_16G		0x03

/* Digital Low Pass Filter (DLPF) configuration */
#define MPU6050_DLPF_CFG_MASK		0x07
#define MPU6050_DLPF_CFG_260HZ		0x00
#define MPU6050_DLPF_CFG_184HZ		0x01
#define MPU6050_DLPF_CFG_94HZ		0x02
#define MPU6050_DLPF_CFG_44HZ		0x03
#define MPU6050_DLPF_CFG_21HZ		0x04
#define MPU6050_DLPF_CFG_10HZ		0x05
#define MPU6050_DLPF_CFG_5HZ		0x06

/* Default configuration values */
#define MPU6050_DEFAULT_SMPLRT_DIV	0x07  /* 1kHz / (1 + 7) = 125Hz */
#define MPU6050_DEFAULT_DLPF_CFG	0x01  /* 184Hz */

/* Self-test limits */
#define MPU6050_ST_ACCEL_MIN		225   /* LSB, equivalent to 14% */
#define MPU6050_ST_ACCEL_MAX		675   /* LSB, equivalent to 50% */
#define MPU6050_ST_GYRO_MIN		20    /* LSB */
#define MPU6050_ST_GYRO_MAX		60    /* LSB */

/* Data structures */

/**
 * struct mpu6050_raw_data - Raw sensor data from MPU-6050
 * @accel_x: Raw X-axis accelerometer reading
 * @accel_y: Raw Y-axis accelerometer reading
 * @accel_z: Raw Z-axis accelerometer reading
 * @temp: Raw temperature reading
 * @gyro_x: Raw X-axis gyroscope reading
 * @gyro_y: Raw Y-axis gyroscope reading
 * @gyro_z: Raw Z-axis gyroscope reading
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
 * struct mpu6050_scaled_data - Scaled sensor data from MPU-6050
 * @accel_x: X-axis acceleration in milli-g (mg)
 * @accel_y: Y-axis acceleration in milli-g (mg)
 * @accel_z: Z-axis acceleration in milli-g (mg)
 * @gyro_x: X-axis angular velocity in milli-degrees per second (mdps)
 * @gyro_y: Y-axis angular velocity in milli-degrees per second (mdps)
 * @gyro_z: Z-axis angular velocity in milli-degrees per second (mdps)
 * @temp: Temperature in hundredths of degrees Celsius
 */
struct mpu6050_scaled_data {
	s32 accel_x;
	s32 accel_y;
	s32 accel_z;
	s32 gyro_x;
	s32 gyro_y;
	s32 gyro_z;
	s32 temp;
};

/**
 * struct mpu6050_config - MPU-6050 configuration parameters
 * @sample_rate_div: Sample rate divider (0-255)
 * @gyro_range: Gyroscope full scale range (0-3)
 * @accel_range: Accelerometer full scale range (0-3)
 * @dlpf_cfg: Digital Low Pass Filter configuration (0-6)
 */
struct mpu6050_config {
	u8 sample_rate_div;
	u8 gyro_range;
	u8 accel_range;
	u8 dlpf_cfg;
};

/**
 * struct mpu6050_data - MPU-6050 device data
 * @client: I2C client
 * @dev: Device structure
 * @lock: Mutex for device access
 * @regmap: Register map for I2C communication
 * @config: Current device configuration
 * @gyro_range: Current gyroscope range setting
 * @accel_range: Current accelerometer range setting
 */
struct mpu6050_data {
	struct i2c_client *client;
	struct device *dev;
	struct mutex lock;
	struct regmap *regmap;
	struct mpu6050_config config;
	u8 gyro_range;
	u8 accel_range;
};

/* IOCTL interface */
#define MPU6050_IOC_MAGIC		'm'
#define MPU6050_IOC_MAXNR		6

/* IOCTL commands */
#define MPU6050_IOC_READ_RAW		_IOR(MPU6050_IOC_MAGIC, 0, struct mpu6050_raw_data)
#define MPU6050_IOC_READ_SCALED		_IOR(MPU6050_IOC_MAGIC, 1, struct mpu6050_scaled_data)
#define MPU6050_IOC_SET_CONFIG		_IOW(MPU6050_IOC_MAGIC, 2, struct mpu6050_config)
#define MPU6050_IOC_GET_CONFIG		_IOR(MPU6050_IOC_MAGIC, 3, struct mpu6050_config)
#define MPU6050_IOC_RESET		_IO(MPU6050_IOC_MAGIC, 4)
#define MPU6050_IOC_WHO_AM_I		_IOR(MPU6050_IOC_MAGIC, 5, u8)
#define MPU6050_IOC_SELF_TEST		_IO(MPU6050_IOC_MAGIC, 6)

/* Function prototypes */
int mpu6050_read_raw(struct mpu6050_data *data, u8 reg, s16 *val);
int mpu6050_write_reg(struct mpu6050_data *data, u8 reg, u8 val);
int mpu6050_read_raw_data(struct mpu6050_data *data, struct mpu6050_raw_data *raw_data);
int mpu6050_read_scaled_data(struct mpu6050_data *data, struct mpu6050_scaled_data *scaled_data);
int mpu6050_set_config(struct mpu6050_data *data, const struct mpu6050_config *config);
int mpu6050_get_config(struct mpu6050_data *data, struct mpu6050_config *config);
int mpu6050_reset_device(struct mpu6050_data *data);
int mpu6050_self_test(struct mpu6050_data *data);

/* Utility functions */
static inline int mpu6050_accel_range_to_scale(u8 range)
{
	switch (range) {
	case MPU6050_ACCEL_FS_2G:
		return 61;      /* 61 ug/LSB for ±2g */
	case MPU6050_ACCEL_FS_4G:
		return 122;     /* 122 ug/LSB for ±4g */
	case MPU6050_ACCEL_FS_8G:
		return 244;     /* 244 ug/LSB for ±8g */
	case MPU6050_ACCEL_FS_16G:
		return 488;     /* 488 ug/LSB for ±16g */
	default:
		return 61;
	}
}

static inline int mpu6050_gyro_range_to_scale(u8 range)
{
	switch (range) {
	case MPU6050_GYRO_FS_250:
		return 7633;    /* 7.633 udps/LSB for ±250°/s */
	case MPU6050_GYRO_FS_500:
		return 15267;   /* 15.267 udps/LSB for ±500°/s */
	case MPU6050_GYRO_FS_1000:
		return 30518;   /* 30.518 udps/LSB for ±1000°/s */
	case MPU6050_GYRO_FS_2000:
		return 61035;   /* 61.035 udps/LSB for ±2000°/s */
	default:
		return 7633;
	}
}

#endif /* _MPU6050_H_ */