# MPU-6050 Kernel Driver - API Reference

## Table of Contents

- [Overview](#overview)
- [Data Structures](#data-structures)
- [Function Reference](#function-reference)
- [Sysfs Interface](#sysfs-interface)
- [IOCTL Commands](#ioctl-commands)
- [Error Codes](#error-codes)
- [Usage Examples](#usage-examples)
- [Best Practices](#best-practices)

## Overview

The MPU-6050 kernel driver provides three main interfaces for userspace applications:

1. **Sysfs Interface** - Simple file-based access via `/sys/class/mpu6050/`
2. **Character Device** - Direct device access via `/dev/mpu6050`
3. **IOCTL Commands** - Advanced control and configuration

This document provides complete API reference for all interfaces, data structures, and functions.

## Data Structures

### Core Data Structures

#### `struct mpu6050_raw_data`

Raw sensor data directly from hardware registers.

```c
struct mpu6050_raw_data {
    s16 accel_x;    /* Raw accelerometer X-axis */
    s16 accel_y;    /* Raw accelerometer Y-axis */
    s16 accel_z;    /* Raw accelerometer Z-axis */
    s16 temp;       /* Raw temperature */
    s16 gyro_x;     /* Raw gyroscope X-axis */
    s16 gyro_y;     /* Raw gyroscope Y-axis */
    s16 gyro_z;     /* Raw gyroscope Z-axis */
};
```

**Fields:**
- `accel_x`, `accel_y`, `accel_z`: 16-bit signed accelerometer readings
- `temp`: 16-bit signed temperature reading
- `gyro_x`, `gyro_y`, `gyro_z`: 16-bit signed gyroscope readings

**Notes:**
- Values are in hardware units and require scaling for physical interpretation
- Big-endian byte order from hardware is automatically converted to host order

#### `struct mpu6050_scaled_data`

Sensor data converted to standard physical units.

```c
struct mpu6050_scaled_data {
    s32 accel_x;    /* Accelerometer X-axis in mg */
    s32 accel_y;    /* Accelerometer Y-axis in mg */
    s32 accel_z;    /* Accelerometer Z-axis in mg */
    s32 temp;       /* Temperature in degrees Celsius × 100 */
    s32 gyro_x;     /* Gyroscope X-axis in mdps */
    s32 gyro_y;     /* Gyroscope Y-axis in mdps */
    s32 gyro_z;     /* Gyroscope Z-axis in mdps */
};
```

**Fields:**
- `accel_x`, `accel_y`, `accel_z`: Acceleration in millig (mg) - 1g = 1000mg
- `temp`: Temperature in degrees Celsius × 100 (e.g., 2537 = 25.37°C)
- `gyro_x`, `gyro_y`, `gyro_z`: Angular velocity in millidegrees per second (mdps)

**Scaling Formulas:**
```c
/* Accelerometer scaling based on range setting */
static const int accel_scale_factors[] = {
    16384,  /* ±2g range */
    8192,   /* ±4g range */
    4096,   /* ±8g range */
    2048    /* ±16g range */
};

/* Gyroscope scaling based on range setting */
static const int gyro_scale_factors[] = {
    131,    /* ±250°/s range */
    66,     /* ±500°/s range */
    33,     /* ±1000°/s range */
    16      /* ±2000°/s range */
};

/* Temperature scaling */
temp_celsius = (raw_temp / 340.0) + 36.53;
```

#### `struct mpu6050_config`

Device configuration parameters.

```c
struct mpu6050_config {
    u8 sample_rate_div;  /* Sample rate divider (0-255) */
    u8 gyro_range;       /* Gyroscope range (0-3) */
    u8 accel_range;      /* Accelerometer range (0-3) */
    u8 dlpf_cfg;         /* Digital Low Pass Filter config (0-7) */
};
```

**Fields:**
- `sample_rate_div`: Sample Rate = Internal_Sample_Rate / (1 + sample_rate_div)
- `gyro_range`: Gyroscope full scale range selection
- `accel_range`: Accelerometer full scale range selection  
- `dlpf_cfg`: Digital Low Pass Filter bandwidth configuration

**Range Values:**

| `gyro_range` | Full Scale Range | Sensitivity |
|--------------|------------------|-------------|
| 0 | ±250°/s | 131 LSB/°/s |
| 1 | ±500°/s | 65.5 LSB/°/s |
| 2 | ±1000°/s | 32.8 LSB/°/s |
| 3 | ±2000°/s | 16.4 LSB/°/s |

| `accel_range` | Full Scale Range | Sensitivity |
|---------------|------------------|-------------|
| 0 | ±2g | 16384 LSB/g |
| 1 | ±4g | 8192 LSB/g |
| 2 | ±8g | 4096 LSB/g |
| 3 | ±16g | 2048 LSB/g |

| `dlpf_cfg` | Accelerometer BW | Gyroscope BW | Delay |
|------------|------------------|--------------|-------|
| 0 | 260 Hz | 256 Hz | 0 ms |
| 1 | 184 Hz | 188 Hz | 2.0 ms |
| 2 | 94 Hz | 98 Hz | 3.0 ms |
| 3 | 44 Hz | 42 Hz | 4.9 ms |
| 4 | 21 Hz | 20 Hz | 8.5 ms |
| 5 | 10 Hz | 10 Hz | 13.8 ms |
| 6 | 5 Hz | 5 Hz | 19.0 ms |
| 7 | Reserved | Reserved | Reserved |

### Register Constants

#### Device Identification
```c
#define MPU6050_I2C_ADDR_LOW     0x68  /* AD0 pin low */
#define MPU6050_I2C_ADDR_HIGH    0x69  /* AD0 pin high */
#define MPU6050_WHO_AM_I_VAL     0x68  /* WHO_AM_I register value */
```

#### Key Registers
```c
#define MPU6050_REG_WHO_AM_I         0x75
#define MPU6050_REG_PWR_MGMT_1       0x6B
#define MPU6050_REG_PWR_MGMT_2       0x6C
#define MPU6050_REG_SMPLRT_DIV       0x19
#define MPU6050_REG_CONFIG           0x1A
#define MPU6050_REG_GYRO_CONFIG      0x1B
#define MPU6050_REG_ACCEL_CONFIG     0x1C
#define MPU6050_REG_INT_ENABLE       0x38
#define MPU6050_REG_INT_STATUS       0x3A
```

#### Sensor Data Registers
```c
#define MPU6050_REG_ACCEL_XOUT_H     0x3B
#define MPU6050_REG_ACCEL_XOUT_L     0x3C
#define MPU6050_REG_ACCEL_YOUT_H     0x3D
#define MPU6050_REG_ACCEL_YOUT_L     0x3E
#define MPU6050_REG_ACCEL_ZOUT_H     0x3F
#define MPU6050_REG_ACCEL_ZOUT_L     0x40
#define MPU6050_REG_TEMP_OUT_H       0x41
#define MPU6050_REG_TEMP_OUT_L       0x42
#define MPU6050_REG_GYRO_XOUT_H      0x43
#define MPU6050_REG_GYRO_XOUT_L      0x44
#define MPU6050_REG_GYRO_YOUT_H      0x45
#define MPU6050_REG_GYRO_YOUT_L      0x46
#define MPU6050_REG_GYRO_ZOUT_H      0x47
#define MPU6050_REG_GYRO_ZOUT_L      0x48
```

## Function Reference

### Core Driver Functions

#### `mpu6050_probe`

```c
static int mpu6050_probe(struct i2c_client *client, 
                        const struct i2c_device_id *id);
```

**Description:** I2C device probe function called when device is detected.

**Parameters:**
- `client`: I2C client structure
- `id`: Device ID structure

**Returns:**
- `0`: Success
- `negative`: Error code

**Details:**
- Verifies device identity via WHO_AM_I register
- Allocates and initializes device data structure
- Creates sysfs attributes and character device
- Initializes sensor to default configuration

#### `mpu6050_remove`

```c
static void mpu6050_remove(struct i2c_client *client);
```

**Description:** Device removal function for cleanup.

**Parameters:**
- `client`: I2C client structure

**Details:**
- Removes sysfs attributes
- Unregisters character device
- Frees allocated resources
- Puts device to sleep mode

### I2C Communication Functions

#### `mpu6050_read_raw_data`

```c
int mpu6050_read_raw_data(struct mpu6050_data *data,
                         struct mpu6050_raw_data *raw_data);
```

**Description:** Read all sensor data in single burst transaction.

**Parameters:**
- `data`: Device data structure
- `raw_data`: Pointer to store raw sensor readings

**Returns:**
- `0`: Success
- `-EIO`: I2C communication error
- `-EBUSY`: Device busy

**Usage:**
```c
struct mpu6050_raw_data raw;
int ret = mpu6050_read_raw_data(data, &raw);
if (ret == 0) {
    printf(\"Accel: %d, %d, %d\\n\", raw.accel_x, raw.accel_y, raw.accel_z);
}
```

#### `mpu6050_read_scaled_data`

```c
int mpu6050_read_scaled_data(struct mpu6050_data *data,
                           struct mpu6050_scaled_data *scaled_data);
```

**Description:** Read sensor data converted to physical units.

**Parameters:**
- `data`: Device data structure  
- `scaled_data`: Pointer to store scaled readings

**Returns:**
- `0`: Success
- `negative`: Error code

**Usage:**
```c
struct mpu6050_scaled_data scaled;
int ret = mpu6050_read_scaled_data(data, &scaled);
if (ret == 0) {
    printf(\"Accel: %d mg, Gyro: %d mdps\\n\", 
           scaled.accel_x, scaled.gyro_x);
}
```

#### `mpu6050_write_reg`

```c
int mpu6050_write_reg(struct mpu6050_data *data, u8 reg, u8 value);
```

**Description:** Write single register value.

**Parameters:**
- `data`: Device data structure
- `reg`: Register address
- `value`: Value to write

**Returns:**
- `0`: Success
- `negative`: Error code

#### `mpu6050_read_reg`

```c
int mpu6050_read_reg(struct mpu6050_data *data, u8 reg, u8 *value);
```

**Description:** Read single register value.

**Parameters:**
- `data`: Device data structure
- `reg`: Register address
- `value`: Pointer to store read value

**Returns:**
- `0`: Success
- `negative`: Error code

### Configuration Functions

#### `mpu6050_set_config`

```c
int mpu6050_set_config(struct mpu6050_data *data,
                      const struct mpu6050_config *config);
```

**Description:** Apply complete device configuration.

**Parameters:**
- `data`: Device data structure
- `config`: Configuration parameters

**Returns:**
- `0`: Success
- `-EINVAL`: Invalid parameters
- `-EIO`: Communication error

**Usage:**
```c
struct mpu6050_config config = {
    .sample_rate_div = 7,        /* 125 Hz */
    .gyro_range = 1,             /* ±500°/s */
    .accel_range = 1,            /* ±4g */
    .dlpf_cfg = 3                /* 44 Hz LPF */
};
int ret = mpu6050_set_config(data, &config);
```

#### `mpu6050_get_config`

```c
int mpu6050_get_config(struct mpu6050_data *data,
                      struct mpu6050_config *config);
```

**Description:** Read current device configuration.

**Parameters:**
- `data`: Device data structure
- `config`: Pointer to store current configuration

**Returns:**
- `0`: Success
- `negative`: Error code

### Power Management Functions

#### `mpu6050_set_power_mode`

```c
int mpu6050_set_power_mode(struct mpu6050_data *data, bool sleep);
```

**Description:** Control device power state.

**Parameters:**
- `data`: Device data structure
- `sleep`: `true` to sleep, `false` to wake up

**Returns:**
- `0`: Success
- `negative`: Error code

**Details:**
- Sleep mode reduces power consumption to ~6μA
- Wake-up time from sleep is ~30ms
- All registers retain values during sleep

#### `mpu6050_reset_device`

```c
int mpu6050_reset_device(struct mpu6050_data *data);
```

**Description:** Perform device reset to default state.

**Parameters:**
- `data`: Device data structure

**Returns:**
- `0`: Success
- `negative`: Error code

**Details:**
- Resets all registers to power-on defaults
- Device enters sleep mode after reset
- Reset takes ~100ms to complete

### Self-Test Functions

#### `mpu6050_self_test`

```c
int mpu6050_self_test(struct mpu6050_data *data, u32 *result);
```

**Description:** Run hardware self-test sequence.

**Parameters:**
- `data`: Device data structure
- `result`: Pointer to store test result bitmask

**Returns:**
- `0`: Success (check result for individual tests)
- `negative`: Error code

**Result Bitmask:**
- Bit 0: Accelerometer X-axis test passed
- Bit 1: Accelerometer Y-axis test passed
- Bit 2: Accelerometer Z-axis test passed
- Bit 3: Gyroscope X-axis test passed
- Bit 4: Gyroscope Y-axis test passed
- Bit 5: Gyroscope Z-axis test passed

**Usage:**
```c
u32 test_result;
int ret = mpu6050_self_test(data, &test_result);
if (ret == 0) {
    if (test_result == 0x3F) {
        printf(\"All self-tests passed\\n\");
    } else {
        printf(\"Some self-tests failed: 0x%02X\\n\", test_result);
    }
}
```

## Sysfs Interface

### Device Path
```
/sys/class/mpu6050/mpu6050/
```

### Data Attributes (Read-Only)

#### `accel_data`
**Format:** `\"<x> <y> <z>\"`  
**Units:** Raw 16-bit signed values  
**Example:** `\"1024 -512 16384\"`

```bash
cat /sys/class/mpu6050/mpu6050/accel_data
```

#### `gyro_data`
**Format:** `\"<x> <y> <z>\"`  
**Units:** Raw 16-bit signed values  
**Example:** `\"100 -200 50\"`

```bash
cat /sys/class/mpu6050/mpu6050/gyro_data
```

#### `temp_data`
**Format:** `\"<temperature>\"`  
**Units:** Raw 16-bit signed value  
**Example:** `\"512\"`

```bash
cat /sys/class/mpu6050/mpu6050/temp_data
```

#### `accel_scale`
**Format:** `\"<x> <y> <z>\"`  
**Units:** Millig (mg)  
**Example:** `\"62 -31 1000\"`

```bash
cat /sys/class/mpu6050/mpu6050/accel_scale
```

#### `gyro_scale`
**Format:** `\"<x> <y> <z>\"`  
**Units:** Millidegrees per second (mdps)  
**Example:** `\"763 -1526 381\"`

```bash
cat /sys/class/mpu6050/mpu6050/gyro_scale
```

#### `temp_celsius`
**Format:** `\"<temperature>\"`  
**Units:** Degrees Celsius × 100  
**Example:** `\"2537\"` (25.37°C)

```bash
cat /sys/class/mpu6050/mpu6050/temp_celsius
```

### Configuration Attributes (Read-Write)

#### `accel_range`
**Values:** `0`, `1`, `2`, `3` (±2g, ±4g, ±8g, ±16g)  
**Default:** `0`

```bash
# Read current range
cat /sys/class/mpu6050/mpu6050/accel_range

# Set to ±4g range
echo \"1\" > /sys/class/mpu6050/mpu6050/accel_range
```

#### `gyro_range`
**Values:** `0`, `1`, `2`, `3` (±250°/s, ±500°/s, ±1000°/s, ±2000°/s)  
**Default:** `0`

```bash
# Set to ±500°/s range
echo \"1\" > /sys/class/mpu6050/mpu6050/gyro_range
```

#### `sample_rate`
**Values:** `0-255` (sample rate divider)  
**Formula:** Sample Rate = 1000 Hz / (1 + sample_rate)  
**Default:** `7` (125 Hz)

```bash
# Set to 250 Hz (divider = 3)
echo \"3\" > /sys/class/mpu6050/mpu6050/sample_rate
```

#### `dlpf_config`
**Values:** `0-6` (low pass filter configuration)  
**Default:** `0` (260 Hz bandwidth)

```bash
# Set to 44 Hz low pass filter
echo \"3\" > /sys/class/mpu6050/mpu6050/dlpf_config
```

### Control Attributes (Read-Write)

#### `power_state`
**Values:** `0` (sleep), `1` (normal)  
**Default:** `1`

```bash
# Put device to sleep
echo \"0\" > /sys/class/mpu6050/mpu6050/power_state

# Wake up device
echo \"1\" > /sys/class/mpu6050/mpu6050/power_state
```

#### `calibrate`
**Values:** `1` (trigger calibration)  
**Write-Only**

```bash
# Trigger calibration (device must be stationary)
echo \"1\" > /sys/class/mpu6050/mpu6050/calibrate
```

### Status Attributes (Read-Only)

#### `self_test`
**Format:** `\"<result_mask>\"`  
**Units:** 6-bit mask (accelerometer XYZ, gyroscope XYZ)

```bash
cat /sys/class/mpu6050/mpu6050/self_test
```

#### `device_id`
**Format:** `\"<device_id>\"`  
**Expected:** `\"68\"` (hex 0x68)

```bash
cat /sys/class/mpu6050/mpu6050/device_id
```

#### `status`
**Format:** Multi-line status information

```bash
cat /sys/class/mpu6050/mpu6050/status
```

Example output:
```
Device ID: 0x68
Power State: Normal
Accelerometer Range: ±2g
Gyroscope Range: ±250°/s
Sample Rate: 125 Hz
DLPF: 260 Hz
Temperature: 25.4°C
Read Count: 1234
Error Count: 0
```

## IOCTL Commands

### Command Definitions

```c
#define MPU6050_IOC_MAGIC           'M'
#define MPU6050_IOC_READ_RAW        _IOR(MPU6050_IOC_MAGIC, 0, struct mpu6050_raw_data)
#define MPU6050_IOC_READ_SCALED     _IOR(MPU6050_IOC_MAGIC, 1, struct mpu6050_scaled_data)
#define MPU6050_IOC_SET_CONFIG      _IOW(MPU6050_IOC_MAGIC, 2, struct mpu6050_config)
#define MPU6050_IOC_GET_CONFIG      _IOR(MPU6050_IOC_MAGIC, 3, struct mpu6050_config)
#define MPU6050_IOC_RESET           _IO(MPU6050_IOC_MAGIC, 4)
#define MPU6050_IOC_SELF_TEST       _IOR(MPU6050_IOC_MAGIC, 5, u32)
#define MPU6050_IOC_WHO_AM_I        _IOR(MPU6050_IOC_MAGIC, 6, u8)
#define MPU6050_IOC_CALIBRATE       _IO(MPU6050_IOC_MAGIC, 7)
#define MPU6050_IOC_SET_POWER       _IOW(MPU6050_IOC_MAGIC, 8, u8)
#define MPU6050_IOC_GET_STATUS      _IOR(MPU6050_IOC_MAGIC, 9, struct mpu6050_status)
```

### Usage Examples

#### Reading Sensor Data

```c
#include <sys/ioctl.h>
#include <fcntl.h>
#include <unistd.h>
#include \"mpu6050.h\"

int fd = open(\"/dev/mpu6050\", O_RDWR);
if (fd < 0) {
    perror(\"open\");
    return -1;
}

/* Read raw data */
struct mpu6050_raw_data raw;
if (ioctl(fd, MPU6050_IOC_READ_RAW, &raw) == 0) {
    printf(\"Raw: accel(%d,%d,%d) gyro(%d,%d,%d) temp(%d)\\n\",
           raw.accel_x, raw.accel_y, raw.accel_z,
           raw.gyro_x, raw.gyro_y, raw.gyro_z, raw.temp);
}

/* Read scaled data */
struct mpu6050_scaled_data scaled;
if (ioctl(fd, MPU6050_IOC_READ_SCALED, &scaled) == 0) {
    printf(\"Scaled: accel(%d,%d,%d)mg gyro(%d,%d,%d)mdps temp(%d)\\n\",
           scaled.accel_x, scaled.accel_y, scaled.accel_z,
           scaled.gyro_x, scaled.gyro_y, scaled.gyro_z, scaled.temp);
}

close(fd);
```

#### Configuration Management

```c
/* Get current configuration */
struct mpu6050_config config;
if (ioctl(fd, MPU6050_IOC_GET_CONFIG, &config) == 0) {
    printf(\"Current config: rate_div=%d, gyro_range=%d, accel_range=%d\\n\",
           config.sample_rate_div, config.gyro_range, config.accel_range);
}

/* Set new configuration */
config.sample_rate_div = 15;    /* 62.5 Hz */
config.gyro_range = 2;          /* ±1000°/s */
config.accel_range = 2;         /* ±8g */
config.dlpf_cfg = 4;            /* 21 Hz LPF */

if (ioctl(fd, MPU6050_IOC_SET_CONFIG, &config) == 0) {
    printf(\"Configuration updated successfully\\n\");
} else {
    perror(\"ioctl set config\");
}
```

#### Device Control

```c
/* Device reset */
if (ioctl(fd, MPU6050_IOC_RESET) == 0) {
    printf(\"Device reset successful\\n\");
}

/* Self-test */
u32 test_result;
if (ioctl(fd, MPU6050_IOC_SELF_TEST, &test_result) == 0) {
    printf(\"Self-test result: 0x%02X\\n\", test_result);
    if (test_result == 0x3F) {
        printf(\"All tests passed\\n\");
    }
}

/* Check device identity */
u8 who_am_i;
if (ioctl(fd, MPU6050_IOC_WHO_AM_I, &who_am_i) == 0) {
    printf(\"Device ID: 0x%02X\\n\", who_am_i);
    if (who_am_i != MPU6050_WHO_AM_I_VAL) {
        printf(\"WARNING: Unexpected device ID\\n\");
    }
}

/* Power management */
u8 power_mode = 0;  /* Sleep */
if (ioctl(fd, MPU6050_IOC_SET_POWER, &power_mode) == 0) {
    printf(\"Device put to sleep\\n\");
}

power_mode = 1;  /* Normal */
if (ioctl(fd, MPU6050_IOC_SET_POWER, &power_mode) == 0) {
    printf(\"Device woken up\\n\");
}
```

## Error Codes

### Standard Linux Error Codes

| Code | Symbol | Description | Common Causes |
|------|--------|-------------|---------------|
| -1 | EPERM | Operation not permitted | Insufficient privileges |
| -2 | ENOENT | No such file or directory | Device not found |
| -5 | EIO | Input/output error | I2C communication failure |
| -9 | EBADF | Bad file descriptor | Invalid file descriptor |
| -12 | ENOMEM | Cannot allocate memory | Memory allocation failed |
| -14 | EFAULT | Bad address | Invalid userspace pointer |
| -16 | EBUSY | Device or resource busy | Device in use |
| -19 | ENODEV | No such device | Device not responding |
| -22 | EINVAL | Invalid argument | Bad parameter values |
| -25 | ENOTTY | Inappropriate ioctl | Invalid IOCTL command |
| -110 | ETIMEDOUT | Connection timed out | I2C timeout |

### Driver-Specific Error Codes

```c
#define MPU6050_ERR_I2C_FAILED      -1000  /* I2C communication error */
#define MPU6050_ERR_INVALID_CHIP    -1001  /* Wrong device ID */
#define MPU6050_ERR_CONFIG_FAILED   -1002  /* Configuration error */
#define MPU6050_ERR_READ_FAILED     -1003  /* Sensor read error */
#define MPU6050_ERR_CALIBRATION     -1004  /* Calibration failed */
#define MPU6050_ERR_SELF_TEST       -1005  /* Self-test failed */
#define MPU6050_ERR_POWER_MGMT      -1006  /* Power management error */
#define MPU6050_ERR_TIMEOUT         -1007  /* Operation timeout */
```

### Error Handling Best Practices

```c
int handle_mpu6050_error(int error) {
    switch (error) {
    case 0:
        return 0;  /* Success */
        
    case -EAGAIN:
    case -EBUSY:
        /* Temporary error - can retry */
        usleep(10000);  /* Wait 10ms */
        return 1;       /* Indicate retry possible */
        
    case -EIO:
    case MPU6050_ERR_I2C_FAILED:
        /* I2C communication error */
        fprintf(stderr, \"I2C communication failed\\n\");
        return -1;
        
    case -ENODEV:
    case MPU6050_ERR_INVALID_CHIP:
        /* Device not found or wrong device */
        fprintf(stderr, \"MPU-6050 device not found\\n\");
        return -1;
        
    case -EINVAL:
    case MPU6050_ERR_CONFIG_FAILED:
        /* Invalid configuration */
        fprintf(stderr, \"Invalid configuration parameters\\n\");
        return -1;
        
    case -ETIMEDOUT:
    case MPU6050_ERR_TIMEOUT:
        /* Operation timeout */
        fprintf(stderr, \"Operation timed out\\n\");
        return -1;
        
    default:
        fprintf(stderr, \"Unknown error: %d\\n\", error);
        return -1;
    }
}

/* Example usage with retry logic */
int read_sensor_with_retry(int fd, struct mpu6050_scaled_data *data) {
    int retry_count = 3;
    int ret;
    
    while (retry_count-- > 0) {
        ret = ioctl(fd, MPU6050_IOC_READ_SCALED, data);
        if (ret == 0) {
            return 0;  /* Success */
        }
        
        int action = handle_mpu6050_error(ret);
        if (action < 0) {
            return ret;  /* Fatal error */
        }
        
        if (action == 0) {
            break;  /* Don't retry */
        }
        
        /* Retry after delay */
        usleep(1000);
    }
    
    return ret;
}
```

## Usage Examples

### Complete C Application

```c
/* mpu6050_example.c - Complete usage example */
#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <errno.h>
#include <string.h>
#include <signal.h>
#include \"mpu6050.h\"

static volatile int running = 1;

void signal_handler(int sig) {
    running = 0;
}

int main(int argc, char *argv[]) {
    int fd;
    struct mpu6050_config config;
    struct mpu6050_scaled_data data;
    u32 self_test_result;
    int ret;
    
    /* Install signal handler for graceful shutdown */
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    
    /* Open device */
    fd = open(\"/dev/mpu6050\", O_RDWR);
    if (fd < 0) {
        fprintf(stderr, \"Error opening device: %s\\n\", strerror(errno));
        return EXIT_FAILURE;
    }
    
    printf(\"MPU-6050 Example Application\\n\");
    printf(\"Press Ctrl+C to exit\\n\\n\");
    
    /* Verify device identity */
    u8 device_id;
    ret = ioctl(fd, MPU6050_IOC_WHO_AM_I, &device_id);
    if (ret < 0 || device_id != MPU6050_WHO_AM_I_VAL) {
        fprintf(stderr, \"Device identity verification failed\\n\");
        close(fd);
        return EXIT_FAILURE;
    }
    printf(\"Device ID verified: 0x%02X\\n\", device_id);
    
    /* Run self-test */
    ret = ioctl(fd, MPU6050_IOC_SELF_TEST, &self_test_result);
    if (ret == 0) {
        printf(\"Self-test result: 0x%02X\\n\", self_test_result);
        if (self_test_result != 0x3F) {
            printf(\"WARNING: Some self-tests failed\\n\");
        }
    }
    
    /* Configure sensor */
    config.sample_rate_div = 7;     /* 125 Hz */
    config.gyro_range = 1;          /* ±500°/s */
    config.accel_range = 1;         /* ±4g */
    config.dlpf_cfg = 3;            /* 44 Hz LPF */
    
    ret = ioctl(fd, MPU6050_IOC_SET_CONFIG, &config);
    if (ret < 0) {
        fprintf(stderr, \"Configuration failed: %s\\n\", strerror(errno));
        close(fd);
        return EXIT_FAILURE;
    }
    
    printf(\"Sensor configured successfully\\n\");
    printf(\"Sample Rate: %d Hz\\n\", 1000 / (1 + config.sample_rate_div));
    printf(\"Gyro Range: ±%d°/s\\n\", (250 << config.gyro_range));
    printf(\"Accel Range: ±%dg\\n\", (2 << config.accel_range));
    printf(\"\\n\");
    
    /* Main reading loop */
    printf(\"%-8s %-8s %-8s | %-8s %-8s %-8s | %-8s\\n\",
           \"AccelX\", \"AccelY\", \"AccelZ\", \"GyroX\", \"GyroY\", \"GyroZ\", \"Temp\");
    printf(\"%-8s %-8s %-8s | %-8s %-8s %-8s | %-8s\\n\",
           \"(mg)\", \"(mg)\", \"(mg)\", \"(mdps)\", \"(mdps)\", \"(mdps)\", \"(°C)\");
    printf(\"------------------------------------------------------------------------\\n\");
    
    while (running) {
        ret = ioctl(fd, MPU6050_IOC_READ_SCALED, &data);
        if (ret < 0) {
            if (errno == EAGAIN || errno == EBUSY) {
                usleep(1000);
                continue;
            }
            fprintf(stderr, \"Read failed: %s\\n\", strerror(errno));
            break;
        }
        
        printf(\"%-8d %-8d %-8d | %-8d %-8d %-8d | %-8.2f\\r\",
               data.accel_x, data.accel_y, data.accel_z,
               data.gyro_x, data.gyro_y, data.gyro_z,
               data.temp / 100.0);
        
        fflush(stdout);
        usleep(100000);  /* 10 Hz display update */
    }
    
    printf(\"\\n\\nShutting down...\\n\");
    
    /* Put device to sleep before closing */
    u8 power_mode = 0;
    ioctl(fd, MPU6050_IOC_SET_POWER, &power_mode);
    
    close(fd);
    return EXIT_SUCCESS;
}
```

### Python Wrapper Class

```python
#!/usr/bin/env python3
\"\"\"
Python wrapper for MPU-6050 kernel driver
\"\"\"

import os
import fcntl
import struct
import ctypes
from dataclasses import dataclass
from typing import Tuple, Optional

# IOCTL command definitions
MPU6050_IOC_MAGIC = ord('M')
MPU6050_IOC_READ_RAW = 0x40384D00      # _IOR('M', 0, struct mpu6050_raw_data)
MPU6050_IOC_READ_SCALED = 0x401C4D01   # _IOR('M', 1, struct mpu6050_scaled_data)
MPU6050_IOC_SET_CONFIG = 0x40044D02    # _IOW('M', 2, struct mpu6050_config)
MPU6050_IOC_GET_CONFIG = 0x80044D03    # _IOR('M', 3, struct mpu6050_config)
MPU6050_IOC_RESET = 0x00004D04         # _IO('M', 4)
MPU6050_IOC_SELF_TEST = 0x80044D05     # _IOR('M', 5, u32)
MPU6050_IOC_WHO_AM_I = 0x80014D06      # _IOR('M', 6, u8)

@dataclass
class RawData:
    \"\"\"Raw sensor data from MPU-6050\"\"\"
    accel_x: int
    accel_y: int
    accel_z: int
    temp: int
    gyro_x: int
    gyro_y: int
    gyro_z: int

@dataclass
class ScaledData:
    \"\"\"Scaled sensor data in physical units\"\"\"
    accel_x: int    # mg
    accel_y: int    # mg
    accel_z: int    # mg
    temp: int       # degrees Celsius × 100
    gyro_x: int     # mdps
    gyro_y: int     # mdps
    gyro_z: int     # mdps

@dataclass
class Config:
    \"\"\"MPU-6050 configuration parameters\"\"\"
    sample_rate_div: int
    gyro_range: int
    accel_range: int
    dlpf_cfg: int

class MPU6050:
    \"\"\"Python interface to MPU-6050 kernel driver\"\"\"
    
    DEVICE_PATH = \"/dev/mpu6050\"
    
    # Range constants
    ACCEL_RANGE_2G = 0
    ACCEL_RANGE_4G = 1
    ACCEL_RANGE_8G = 2
    ACCEL_RANGE_16G = 3
    
    GYRO_RANGE_250 = 0
    GYRO_RANGE_500 = 1
    GYRO_RANGE_1000 = 2
    GYRO_RANGE_2000 = 3
    
    def __init__(self, device_path: str = None):
        self.device_path = device_path or self.DEVICE_PATH
        self._fd = None
    
    def __enter__(self):
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def open(self) -> None:
        \"\"\"Open connection to MPU-6050 device\"\"\"
        if self._fd is not None:
            raise RuntimeError(\"Device already open\")
        
        try:
            self._fd = os.open(self.device_path, os.O_RDWR)
        except OSError as e:
            raise RuntimeError(f\"Failed to open {self.device_path}: {e}\")
    
    def close(self) -> None:
        \"\"\"Close connection to device\"\"\"
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
    
    def _ioctl(self, cmd: int, arg=None):
        \"\"\"Perform IOCTL operation\"\"\"
        if self._fd is None:
            raise RuntimeError(\"Device not open\")
        
        try:
            return fcntl.ioctl(self._fd, cmd, arg)
        except OSError as e:
            raise RuntimeError(f\"IOCTL failed: {e}\")
    
    def read_raw(self) -> RawData:
        \"\"\"Read raw sensor data\"\"\"
        # struct mpu6050_raw_data: 7 × int16 (14 bytes)
        fmt = \"<7h\"  # little-endian, 7 signed shorts
        buf = bytearray(struct.calcsize(fmt))
        
        self._ioctl(MPU6050_IOC_READ_RAW, buf)
        
        values = struct.unpack(fmt, buf)
        return RawData(*values)
    
    def read_scaled(self) -> ScaledData:
        \"\"\"Read scaled sensor data\"\"\"
        # struct mpu6050_scaled_data: 7 × int32 (28 bytes)
        fmt = \"<7i\"  # little-endian, 7 signed ints
        buf = bytearray(struct.calcsize(fmt))
        
        self._ioctl(MPU6050_IOC_READ_SCALED, buf)
        
        values = struct.unpack(fmt, buf)
        return ScaledData(*values)
    
    def get_config(self) -> Config:
        \"\"\"Get current device configuration\"\"\"
        # struct mpu6050_config: 4 × uint8 (4 bytes)
        fmt = \"<4B\"  # little-endian, 4 unsigned bytes
        buf = bytearray(struct.calcsize(fmt))
        
        self._ioctl(MPU6050_IOC_GET_CONFIG, buf)
        
        values = struct.unpack(fmt, buf)
        return Config(*values)
    
    def set_config(self, config: Config) -> None:
        \"\"\"Set device configuration\"\"\"
        fmt = \"<4B\"
        buf = struct.pack(fmt, 
                         config.sample_rate_div,
                         config.gyro_range,
                         config.accel_range,
                         config.dlpf_cfg)
        
        self._ioctl(MPU6050_IOC_SET_CONFIG, buf)
    
    def reset(self) -> None:
        \"\"\"Reset device to default state\"\"\"
        self._ioctl(MPU6050_IOC_RESET)
    
    def self_test(self) -> int:
        \"\"\"Run self-test and return result mask\"\"\"
        fmt = \"<I\"  # unsigned int
        buf = bytearray(struct.calcsize(fmt))
        
        self._ioctl(MPU6050_IOC_SELF_TEST, buf)
        
        return struct.unpack(fmt, buf)[0]
    
    def who_am_i(self) -> int:
        \"\"\"Get device ID\"\"\"
        fmt = \"<B\"  # unsigned byte
        buf = bytearray(struct.calcsize(fmt))
        
        self._ioctl(MPU6050_IOC_WHO_AM_I, buf)
        
        return struct.unpack(fmt, buf)[0]
    
    def read_accel_mg(self) -> Tuple[float, float, float]:
        \"\"\"Read accelerometer data in g units\"\"\"
        data = self.read_scaled()
        return (data.accel_x / 1000.0, 
                data.accel_y / 1000.0, 
                data.accel_z / 1000.0)
    
    def read_gyro_dps(self) -> Tuple[float, float, float]:
        \"\"\"Read gyroscope data in degrees per second\"\"\"
        data = self.read_scaled()
        return (data.gyro_x / 1000.0,
                data.gyro_y / 1000.0,
                data.gyro_z / 1000.0)
    
    def read_temp_celsius(self) -> float:
        \"\"\"Read temperature in degrees Celsius\"\"\"
        data = self.read_scaled()
        return data.temp / 100.0

# Example usage
if __name__ == \"__main__\":
    import time
    
    try:
        with MPU6050() as mpu:
            # Verify device
            device_id = mpu.who_am_i()
            print(f\"Device ID: 0x{device_id:02X}\")
            
            if device_id != 0x68:
                print(\"Warning: Unexpected device ID\")
            
            # Run self-test
            test_result = mpu.self_test()
            print(f\"Self-test result: 0x{test_result:02X}\")
            
            # Configure device
            config = Config(
                sample_rate_div=7,      # 125 Hz
                gyro_range=mpu.GYRO_RANGE_500,    # ±500°/s
                accel_range=mpu.ACCEL_RANGE_4G,   # ±4g
                dlpf_cfg=3              # 44 Hz LPF
            )
            mpu.set_config(config)
            
            print(\"\\nStarting data acquisition...\")
            print(\"Accel (g)\\t\\tGyro (°/s)\\t\\tTemp (°C)\")
            print(\"-\" * 60)
            
            # Read data continuously
            for i in range(100):
                accel = mpu.read_accel_mg()
                gyro = mpu.read_gyro_dps()
                temp = mpu.read_temp_celsius()
                
                print(f\"{accel[0]:6.3f} {accel[1]:6.3f} {accel[2]:6.3f}\\t\"
                      f\"{gyro[0]:7.1f} {gyro[1]:7.1f} {gyro[2]:7.1f}\\t\"
                      f\"{temp:6.2f}\")
                
                time.sleep(0.1)
    
    except Exception as e:
        print(f\"Error: {e}\")
```

## Best Practices

### Performance Optimization

1. **Use Burst Reading**: Read all sensor data in single IOCTL call
2. **Minimize I2C Transactions**: Cache configuration when possible
3. **Choose Appropriate Sample Rate**: Match application requirements
4. **Use Interrupts**: When available, use interrupt-driven reading

### Error Handling

1. **Always Check Return Values**: Handle all error conditions
2. **Implement Retry Logic**: For transient errors like -EAGAIN
3. **Validate Device Identity**: Check WHO_AM_I register
4. **Monitor Error Statistics**: Use sysfs status for debugging

### Power Management

1. **Use Sleep Mode**: Put device to sleep when not in use
2. **Configure Appropriately**: Lower sample rates reduce power consumption
3. **Disable Unused Features**: Turn off FIFO, interrupts if not needed

### Thread Safety

1. **Single Writer**: Only one thread should configure device
2. **Multiple Readers**: Reading is thread-safe within same process
3. **Use Locking**: Implement application-level locking for complex scenarios

### Hardware Considerations

1. **I2C Pull-ups**: Ensure proper pull-up resistors on I2C lines
2. **Power Supply**: Stable 3.3V supply required
3. **Mounting**: Secure mounting affects measurement accuracy
4. **Calibration**: Regular calibration improves accuracy

This comprehensive API reference provides complete documentation for all aspects of the MPU-6050 kernel driver interface.