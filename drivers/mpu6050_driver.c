/*
 * MPU-6050 6-axis motion tracking device driver
 *
 * This driver provides support for the InvenSense MPU-6050 accelerometer
 * and gyroscope sensor via I2C interface. It creates a character device
 * interface for userspace applications to read sensor data.
 *
 * Features:
 * - I2C communication with MPU-6050
 * - Character device interface (/dev/mpu6050)
 * - Raw and scaled sensor data reading
 * - Configurable sample rates and ranges
 * - IOCTL interface for advanced operations
 * - Comprehensive error handling
 *
 * Copyright (C) 2025 Murray Kopit <murr2k@gmail.com>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/slab.h>
#include <linux/i2c.h>
#include <linux/mutex.h>
#include <linux/delay.h>
#include <linux/cdev.h>
#include <linux/fs.h>
#include <linux/device.h>
#include <linux/uaccess.h>
#include <linux/of.h>
#include <linux/of_device.h>
#include <linux/regmap.h>
#include <asm/byteorder.h>

#include "../include/mpu6050.h"

#define DRIVER_NAME		"mpu6050"
#define DRIVER_VERSION		"1.0.0"

/* Device-specific data structure */
struct mpu6050_data {
	struct i2c_client *client;
	struct mutex lock;
	struct regmap *regmap;
	struct mpu6050_config config;
	
	/* Character device */
	struct cdev cdev;
	dev_t devt;
	struct class *class;
	struct device *device;
	
	/* Scaling factors */
	u32 accel_scale;	/* Accelerometer scale factor (ug/LSB) */
	u32 gyro_scale;		/* Gyroscope scale factor (udps/LSB) */
};

/* Global variables for character device */
static struct mpu6050_data *mpu6050_dev_data = NULL;
static int mpu6050_major = 0;

/* Regmap configuration */
static const struct regmap_config mpu6050_regmap_config = {
	.reg_bits = 8,
	.val_bits = 8,
	.max_register = MPU6050_REG_WHO_AM_I,
};

/**
 * mpu6050_update_scale_factors - Update scaling factors based on configuration
 * @data: Device data structure
 *
 * This function updates the scaling factors used to convert raw sensor
 * data to meaningful units based on the current configuration.
 */
static void mpu6050_update_scale_factors(struct mpu6050_data *data)
{
	/* Accelerometer scale factors (micro-g per LSB) */
	switch (data->config.accel_range) {
	case MPU6050_ACCEL_FS_2G:
		data->accel_scale = 61;		/* 61 ug/LSB */
		break;
	case MPU6050_ACCEL_FS_4G:
		data->accel_scale = 122;	/* 122 ug/LSB */
		break;
	case MPU6050_ACCEL_FS_8G:
		data->accel_scale = 244;	/* 244 ug/LSB */
		break;
	case MPU6050_ACCEL_FS_16G:
		data->accel_scale = 488;	/* 488 ug/LSB */
		break;
	default:
		data->accel_scale = 61;
		break;
	}
	
	/* Gyroscope scale factors (micro-degrees per second per LSB) */
	switch (data->config.gyro_range) {
	case MPU6050_GYRO_FS_250:
		data->gyro_scale = 7633;	/* 7.633 udps/LSB */
		break;
	case MPU6050_GYRO_FS_500:
		data->gyro_scale = 15267;	/* 15.267 udps/LSB */
		break;
	case MPU6050_GYRO_FS_1000:
		data->gyro_scale = 30518;	/* 30.518 udps/LSB */
		break;
	case MPU6050_GYRO_FS_2000:
		data->gyro_scale = 61035;	/* 61.035 udps/LSB */
		break;
	default:
		data->gyro_scale = 7633;
		break;
	}
}

/**
 * mpu6050_read_raw_data - Read raw sensor data from MPU-6050
 * @data: Device data structure
 * @raw_data: Pointer to store raw data
 *
 * Returns: 0 on success, negative error code on failure
 */
static int mpu6050_read_raw_data(struct mpu6050_data *data,
				 struct mpu6050_raw_data *raw_data)
{
	u8 sensor_data[14];
	int ret;
	
	mutex_lock(&data->lock);
	
	/* Read all sensor data in one burst (14 bytes starting from ACCEL_XOUT_H) */
	ret = regmap_bulk_read(data->regmap, MPU6050_REG_ACCEL_XOUT_H,
			       sensor_data, sizeof(sensor_data));
	if (ret) {
		dev_err(&data->client->dev, "Failed to read sensor data: %d\n", ret);
		goto out;
	}
	
	/* Convert big-endian data to host format */
	raw_data->accel_x = be16_to_cpup((__be16 *)&sensor_data[0]);
	raw_data->accel_y = be16_to_cpup((__be16 *)&sensor_data[2]);
	raw_data->accel_z = be16_to_cpup((__be16 *)&sensor_data[4]);
	raw_data->temp = be16_to_cpup((__be16 *)&sensor_data[6]);
	raw_data->gyro_x = be16_to_cpup((__be16 *)&sensor_data[8]);
	raw_data->gyro_y = be16_to_cpup((__be16 *)&sensor_data[10]);
	raw_data->gyro_z = be16_to_cpup((__be16 *)&sensor_data[12]);
	
out:
	mutex_unlock(&data->lock);
	return ret;
}

/**
 * mpu6050_read_scaled_data - Read and scale sensor data
 * @data: Device data structure
 * @scaled_data: Pointer to store scaled data
 *
 * Returns: 0 on success, negative error code on failure
 */
static int mpu6050_read_scaled_data(struct mpu6050_data *data,
				    struct mpu6050_scaled_data *scaled_data)
{
	struct mpu6050_raw_data raw_data;
	int ret;
	
	ret = mpu6050_read_raw_data(data, &raw_data);
	if (ret)
		return ret;
	
	/* Scale accelerometer data to milli-g */
	scaled_data->accel_x = ((s32)raw_data.accel_x * data->accel_scale) / 1000;
	scaled_data->accel_y = ((s32)raw_data.accel_y * data->accel_scale) / 1000;
	scaled_data->accel_z = ((s32)raw_data.accel_z * data->accel_scale) / 1000;
	
	/* Scale gyroscope data to milli-degrees per second */
	scaled_data->gyro_x = ((s32)raw_data.gyro_x * data->gyro_scale) / 1000000;
	scaled_data->gyro_y = ((s32)raw_data.gyro_y * data->gyro_scale) / 1000000;
	scaled_data->gyro_z = ((s32)raw_data.gyro_z * data->gyro_scale) / 1000000;
	
	/* Convert temperature to degrees Celsius * 100 */
	/* Temperature formula: Temperature = (TEMP_OUT/340) + 36.53 */
	scaled_data->temp = (raw_data.temp * 100) / 340 + 3653;
	
	return 0;
}

/**
 * mpu6050_set_config - Configure MPU-6050 settings
 * @data: Device data structure
 * @config: Configuration parameters
 *
 * Returns: 0 on success, negative error code on failure
 */
static int mpu6050_set_config(struct mpu6050_data *data,
			      const struct mpu6050_config *config)
{
	int ret;
	
	mutex_lock(&data->lock);
	
	/* Set sample rate divider */
	ret = regmap_write(data->regmap, MPU6050_REG_SMPLRT_DIV,
			   config->sample_rate_div);
	if (ret) {
		dev_err(&data->client->dev, "Failed to set sample rate: %d\n", ret);
		goto out;
	}
	
	/* Configure DLPF */
	ret = regmap_write(data->regmap, MPU6050_REG_CONFIG, config->dlpf_cfg);
	if (ret) {
		dev_err(&data->client->dev, "Failed to set DLPF config: %d\n", ret);
		goto out;
	}
	
	/* Configure gyroscope full scale range */
	ret = regmap_write(data->regmap, MPU6050_REG_GYRO_CONFIG,
			   (config->gyro_range << 3) & MPU6050_GYRO_FS_SEL_MASK);
	if (ret) {
		dev_err(&data->client->dev, "Failed to set gyro config: %d\n", ret);
		goto out;
	}
	
	/* Configure accelerometer full scale range */
	ret = regmap_write(data->regmap, MPU6050_REG_ACCEL_CONFIG,
			   (config->accel_range << 3) & MPU6050_ACCEL_FS_SEL_MASK);
	if (ret) {
		dev_err(&data->client->dev, "Failed to set accel config: %d\n", ret);
		goto out;
	}
	
	/* Update local configuration and scaling factors */
	data->config = *config;
	mpu6050_update_scale_factors(data);
	
out:
	mutex_unlock(&data->lock);
	return ret;
}

/**
 * mpu6050_reset - Reset the MPU-6050 device
 * @data: Device data structure
 *
 * Returns: 0 on success, negative error code on failure
 */
static int mpu6050_reset(struct mpu6050_data *data)
{
	int ret;
	
	mutex_lock(&data->lock);
	
	/* Trigger device reset */
	ret = regmap_write(data->regmap, MPU6050_REG_PWR_MGMT_1,
			   MPU6050_PWR1_DEVICE_RESET);
	if (ret) {
		dev_err(&data->client->dev, "Failed to reset device: %d\n", ret);
		goto out;
	}
	
	/* Wait for reset to complete */
	msleep(100);
	
	/* Re-initialize the device with default settings */
	ret = mpu6050_set_config(data, &data->config);
	
out:
	mutex_unlock(&data->lock);
	return ret;
}

/**
 * mpu6050_init_device - Initialize MPU-6050 device
 * @data: Device data structure
 *
 * Returns: 0 on success, negative error code on failure
 */
static int mpu6050_init_device(struct mpu6050_data *data)
{
	unsigned int val;
	int ret;
	
	/* Check WHO_AM_I register */
	ret = regmap_read(data->regmap, MPU6050_REG_WHO_AM_I, &val);
	if (ret) {
		dev_err(&data->client->dev, "Failed to read WHO_AM_I: %d\n", ret);
		return ret;
	}
	
	if (val != MPU6050_WHO_AM_I_VAL) {
		dev_err(&data->client->dev, "Invalid WHO_AM_I value: 0x%02x\n", val);
		return -ENODEV;
	}
	
	dev_info(&data->client->dev, "MPU-6050 detected (WHO_AM_I: 0x%02x)\n", val);
	
	/* Wake up from sleep mode and set clock source */
	ret = regmap_write(data->regmap, MPU6050_REG_PWR_MGMT_1,
			   MPU6050_CLKSEL_PLL_XGYRO);
	if (ret) {
		dev_err(&data->client->dev, "Failed to wake up device: %d\n", ret);
		return ret;
	}
	
	/* Wait for device to stabilize */
	msleep(50);
	
	/* Set default configuration */
	data->config.sample_rate_div = MPU6050_DEFAULT_SMPLRT_DIV;
	data->config.gyro_range = MPU6050_GYRO_FS_250;
	data->config.accel_range = MPU6050_ACCEL_FS_2G;
	data->config.dlpf_cfg = 0x00;  /* No DLPF */
	
	ret = mpu6050_set_config(data, &data->config);
	if (ret) {
		dev_err(&data->client->dev, "Failed to set default config: %d\n", ret);
		return ret;
	}
	
	dev_info(&data->client->dev, "MPU-6050 initialized successfully\n");
	return 0;
}

/* Character device file operations */

static int mpu6050_open(struct inode *inode, struct file *file)
{
	struct mpu6050_data *data = mpu6050_dev_data;
	
	if (!data) {
		pr_err("MPU-6050: Device data not available\n");
		return -ENODEV;
	}
	
	file->private_data = data;
	return nonseekable_open(inode, file);
}

static int mpu6050_release(struct inode *inode, struct file *file)
{
	return 0;
}

static ssize_t mpu6050_read(struct file *file, char __user *buf,
			    size_t count, loff_t *ppos)
{
	struct mpu6050_data *data = file->private_data;
	struct mpu6050_raw_data raw_data;
	int ret;
	
	if (count < sizeof(struct mpu6050_raw_data))
		return -EINVAL;
	
	ret = mpu6050_read_raw_data(data, &raw_data);
	if (ret)
		return ret;
	
	if (copy_to_user(buf, &raw_data, sizeof(raw_data)))
		return -EFAULT;
	
	return sizeof(raw_data);
}

static long mpu6050_ioctl(struct file *file, unsigned int cmd, unsigned long arg)
{
	struct mpu6050_data *data = file->private_data;
	int ret = 0;
	
	if (_IOC_TYPE(cmd) != MPU6050_IOC_MAGIC)
		return -ENOTTY;
	
	if (_IOC_NR(cmd) > MPU6050_IOC_MAXNR)
		return -ENOTTY;
	
	switch (cmd) {
	case MPU6050_IOC_READ_RAW: {
		struct mpu6050_raw_data raw_data;
		
		ret = mpu6050_read_raw_data(data, &raw_data);
		if (ret)
			return ret;
		
		if (copy_to_user((void __user *)arg, &raw_data, sizeof(raw_data)))
			return -EFAULT;
		break;
	}
	
	case MPU6050_IOC_READ_SCALED: {
		struct mpu6050_scaled_data scaled_data;
		
		ret = mpu6050_read_scaled_data(data, &scaled_data);
		if (ret)
			return ret;
		
		if (copy_to_user((void __user *)arg, &scaled_data, sizeof(scaled_data)))
			return -EFAULT;
		break;
	}
	
	case MPU6050_IOC_SET_CONFIG: {
		struct mpu6050_config config;
		
		if (copy_from_user(&config, (void __user *)arg, sizeof(config)))
			return -EFAULT;
		
		ret = mpu6050_set_config(data, &config);
		break;
	}
	
	case MPU6050_IOC_GET_CONFIG: {
		if (copy_to_user((void __user *)arg, &data->config,
				 sizeof(data->config)))
			return -EFAULT;
		break;
	}
	
	case MPU6050_IOC_RESET:
		ret = mpu6050_reset(data);
		break;
	
	case MPU6050_IOC_WHO_AM_I: {
		unsigned int val;
		
		mutex_lock(&data->lock);
		ret = regmap_read(data->regmap, MPU6050_REG_WHO_AM_I, &val);
		mutex_unlock(&data->lock);
		
		if (ret)
			return ret;
		
		if (copy_to_user((void __user *)arg, &val, sizeof(u8)))
			return -EFAULT;
		break;
	}
	
	default:
		return -ENOTTY;
	}
	
	return ret;
}

static const struct file_operations mpu6050_fops = {
	.owner = THIS_MODULE,
	.open = mpu6050_open,
	.release = mpu6050_release,
	.read = mpu6050_read,
	.unlocked_ioctl = mpu6050_ioctl,
	.llseek = no_llseek,
};

/**
 * mpu6050_create_cdev - Create character device
 * @data: Device data structure
 *
 * Returns: 0 on success, negative error code on failure
 */
static int mpu6050_create_cdev(struct mpu6050_data *data)
{
	int ret;
	
	/* Allocate character device number */
	if (mpu6050_major == 0) {
		ret = alloc_chrdev_region(&data->devt, 0, 1, DRIVER_NAME);
		if (ret) {
			dev_err(&data->client->dev, "Failed to allocate char dev region: %d\n", ret);
			return ret;
		}
		mpu6050_major = MAJOR(data->devt);
	} else {
		data->devt = MKDEV(mpu6050_major, 0);
		ret = register_chrdev_region(data->devt, 1, DRIVER_NAME);
		if (ret) {
			dev_err(&data->client->dev, "Failed to register char dev region: %d\n", ret);
			return ret;
		}
	}
	
	/* Initialize and add character device */
	cdev_init(&data->cdev, &mpu6050_fops);
	data->cdev.owner = THIS_MODULE;
	
	ret = cdev_add(&data->cdev, data->devt, 1);
	if (ret) {
		dev_err(&data->client->dev, "Failed to add char dev: %d\n", ret);
		goto err_cdev_add;
	}
	
	/* Create device class */
	data->class = class_create(THIS_MODULE, DRIVER_NAME);
	if (IS_ERR(data->class)) {
		ret = PTR_ERR(data->class);
		dev_err(&data->client->dev, "Failed to create device class: %d\n", ret);
		goto err_class_create;
	}
	
	/* Create device node */
	data->device = device_create(data->class, &data->client->dev,
				     data->devt, data, DRIVER_NAME);
	if (IS_ERR(data->device)) {
		ret = PTR_ERR(data->device);
		dev_err(&data->client->dev, "Failed to create device: %d\n", ret);
		goto err_device_create;
	}
	
	dev_info(&data->client->dev, "Character device created: /dev/%s (major: %d)\n",
		 DRIVER_NAME, mpu6050_major);
	
	return 0;
	
err_device_create:
	class_destroy(data->class);
err_class_create:
	cdev_del(&data->cdev);
err_cdev_add:
	unregister_chrdev_region(data->devt, 1);
	return ret;
}

/**
 * mpu6050_destroy_cdev - Destroy character device
 * @data: Device data structure
 */
static void mpu6050_destroy_cdev(struct mpu6050_data *data)
{
	if (data->device) {
		device_destroy(data->class, data->devt);
		data->device = NULL;
	}
	
	if (data->class) {
		class_destroy(data->class);
		data->class = NULL;
	}
	
	cdev_del(&data->cdev);
	unregister_chrdev_region(data->devt, 1);
}

/* I2C driver functions */

static int mpu6050_probe(struct i2c_client *client,
			 const struct i2c_device_id *id)
{
	struct mpu6050_data *data;
	int ret;
	
	dev_info(&client->dev, "Probing MPU-6050 at address 0x%02x\n",
		 client->addr);
	
	/* Check I2C functionality */
	if (!i2c_check_functionality(client->adapter, I2C_FUNC_SMBUS_BYTE_DATA)) {
		dev_err(&client->dev, "I2C adapter doesn't support required functionality\n");
		return -EOPNOTSUPP;
	}
	
	/* Allocate device data structure */
	data = devm_kzalloc(&client->dev, sizeof(*data), GFP_KERNEL);
	if (!data)
		return -ENOMEM;
	
	data->client = client;
	mutex_init(&data->lock);
	
	/* Initialize regmap for I2C communication */
	data->regmap = devm_regmap_init_i2c(client, &mpu6050_regmap_config);
	if (IS_ERR(data->regmap)) {
		ret = PTR_ERR(data->regmap);
		dev_err(&client->dev, "Failed to initialize regmap: %d\n", ret);
		return ret;
	}
	
	/* Set client data */
	i2c_set_clientdata(client, data);
	
	/* Initialize the MPU-6050 device */
	ret = mpu6050_init_device(data);
	if (ret) {
		dev_err(&client->dev, "Failed to initialize device: %d\n", ret);
		return ret;
	}
	
	/* Create character device (only for first instance) */
	if (!mpu6050_dev_data) {
		ret = mpu6050_create_cdev(data);
		if (ret) {
			dev_err(&client->dev, "Failed to create character device: %d\n", ret);
			return ret;
		}
		mpu6050_dev_data = data;
	}
	
	dev_info(&client->dev, "MPU-6050 probe completed successfully\n");
	return 0;
}

static int mpu6050_remove(struct i2c_client *client)
{
	struct mpu6050_data *data = i2c_get_clientdata(client);
	
	dev_info(&client->dev, "Removing MPU-6050 driver\n");
	
	/* Destroy character device if this is the main instance */
	if (data == mpu6050_dev_data) {
		mpu6050_destroy_cdev(data);
		mpu6050_dev_data = NULL;
		mpu6050_major = 0;
	}
	
	return 0;
}

/* Device tree and I2C device ID tables */
static const struct i2c_device_id mpu6050_id[] = {
	{ "mpu6050", 0 },
	{ }
};
MODULE_DEVICE_TABLE(i2c, mpu6050_id);

#ifdef CONFIG_OF
static const struct of_device_id mpu6050_of_match[] = {
	{ .compatible = "invensense,mpu6050" },
	{ }
};
MODULE_DEVICE_TABLE(of, mpu6050_of_match);
#endif

static struct i2c_driver mpu6050_driver = {
	.driver = {
		.name = DRIVER_NAME,
		.of_match_table = of_match_ptr(mpu6050_of_match),
	},
	.probe = mpu6050_probe,
	.remove = mpu6050_remove,
	.id_table = mpu6050_id,
};

/* Module initialization and cleanup */

static int __init mpu6050_init(void)
{
	int ret;
	
	pr_info("MPU-6050 driver v%s initializing\n", DRIVER_VERSION);
	
	ret = i2c_add_driver(&mpu6050_driver);
	if (ret) {
		pr_err("Failed to register MPU-6050 I2C driver: %d\n", ret);
		return ret;
	}
	
	pr_info("MPU-6050 driver registered successfully\n");
	return 0;
}

static void __exit mpu6050_exit(void)
{
	pr_info("MPU-6050 driver exiting\n");
	i2c_del_driver(&mpu6050_driver);
}

module_init(mpu6050_init);
module_exit(mpu6050_exit);

/* Module information */
MODULE_AUTHOR("Murray Kopit <murr2k@gmail.com>");
MODULE_DESCRIPTION("MPU-6050 6-axis motion tracking device driver");
MODULE_LICENSE("GPL v2");
MODULE_VERSION(DRIVER_VERSION);
MODULE_ALIAS("i2c:mpu6050");