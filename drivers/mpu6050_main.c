// SPDX-License-Identifier: GPL-2.0
/*
 * MPU-6050 6-axis gyroscope and accelerometer driver
 * 
 * Copyright (C) 2024 Murray Kopit <murr2k@gmail.com>
 */

#include <linux/delay.h>
#include <linux/device.h>
#include <linux/i2c.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/slab.h>

#include "../include/mpu6050.h"

static const struct i2c_device_id mpu6050_id[] = {
	{ "mpu6050", 0 },
	{ }
};
MODULE_DEVICE_TABLE(i2c, mpu6050_id);

static const struct of_device_id mpu6050_of_match[] = {
	{ .compatible = "invensense,mpu6050" },
	{ }
};
MODULE_DEVICE_TABLE(of, mpu6050_of_match);

/**
 * mpu6050_write_reg - Write to MPU-6050 register
 * @data: Device data structure
 * @reg: Register address
 * @val: Value to write
 *
 * Return: 0 on success, negative error code on failure
 */
int mpu6050_write_reg(struct mpu6050_data *data, u8 reg, u8 val)
{
	int ret;
	
	mutex_lock(&data->lock);
	ret = i2c_smbus_write_byte_data(data->client, reg, val);
	mutex_unlock(&data->lock);
	
	if (ret < 0)
		dev_err(data->dev, "Failed to write reg 0x%02x: %d\n", reg, ret);
	
	return ret;
}

/**
 * mpu6050_read_raw - Read raw data from MPU-6050
 * @data: Device data structure  
 * @reg: Starting register address
 * @val: Pointer to store the read value
 *
 * Return: 0 on success, negative error code on failure
 */
int mpu6050_read_raw(struct mpu6050_data *data, u8 reg, s16 *val)
{
	int ret;
	__be16 raw_val;
	
	mutex_lock(&data->lock);
	ret = i2c_smbus_read_i2c_block_data(data->client, reg, 
					    sizeof(raw_val), (u8 *)&raw_val);
	mutex_unlock(&data->lock);
	
	if (ret < 0) {
		dev_err(data->dev, "Failed to read reg 0x%02x: %d\n", reg, ret);
		return ret;
	}
	
	*val = be16_to_cpu(raw_val);
	return 0;
}

/**
 * mpu6050_init_device - Initialize MPU-6050 device
 * @data: Device data structure
 *
 * Return: 0 on success, negative error code on failure
 */
static int mpu6050_init_device(struct mpu6050_data *data)
{
	int ret;
	
	/* Reset device */
	ret = mpu6050_write_reg(data, MPU6050_REG_PWR_MGMT_1, 
				MPU6050_PWR_MGMT_1_RESET);
	if (ret < 0)
		return ret;
	
	msleep(100);
	
	/* Wake up device */
	ret = mpu6050_write_reg(data, MPU6050_REG_PWR_MGMT_1, 0);
	if (ret < 0)
		return ret;
	
	/* Set default ranges */
	data->gyro_range = 0;	/* ±250°/s */
	data->accel_range = 0;	/* ±2g */
	
	dev_info(data->dev, "MPU-6050 initialized successfully\n");
	return 0;
}

/**
 * mpu6050_probe - I2C probe function
 * @client: I2C client
 * @id: I2C device ID
 *
 * Return: 0 on success, negative error code on failure
 */
static int mpu6050_probe(struct i2c_client *client,
			 const struct i2c_device_id *id)
{
	struct mpu6050_data *data;
	int ret;
	
	if (!i2c_check_functionality(client->adapter, I2C_FUNC_SMBUS_I2C_BLOCK)) {
		dev_err(&client->dev, "I2C adapter doesn't support block transfers\n");
		return -ENODEV;
	}
	
	data = devm_kzalloc(&client->dev, sizeof(*data), GFP_KERNEL);
	if (!data)
		return -ENOMEM;
	
	data->client = client;
	data->dev = &client->dev;
	mutex_init(&data->lock);
	
	i2c_set_clientdata(client, data);
	
	ret = mpu6050_init_device(data);
	if (ret < 0)
		return ret;
	
	dev_info(&client->dev, "MPU-6050 probe completed\n");
	return 0;
}

/**
 * mpu6050_remove - I2C remove function
 * @client: I2C client
 */
static void mpu6050_remove(struct i2c_client *client)
{
	struct mpu6050_data *data = i2c_get_clientdata(client);
	
	mutex_destroy(&data->lock);
	dev_info(&client->dev, "MPU-6050 removed\n");
}

static struct i2c_driver mpu6050_driver = {
	.driver = {
		.name = "mpu6050",
		.of_match_table = mpu6050_of_match,
	},
	.probe = mpu6050_probe,
	.remove = mpu6050_remove,
	.id_table = mpu6050_id,
};

module_i2c_driver(mpu6050_driver);

MODULE_AUTHOR("Murray Kopit <murr2k@gmail.com>");
MODULE_DESCRIPTION("MPU-6050 6-axis gyroscope and accelerometer driver");
MODULE_LICENSE("GPL v2");