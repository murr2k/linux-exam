# MPU-6050 Linux Kernel Driver - Technical Documentation

## Table of Contents

- [Driver Architecture](#driver-architecture)
- [I2C Communication Protocol](#i2c-communication-protocol)
- [Character Device Interface](#character-device-interface)
- [IOCTL Commands Reference](#ioctl-commands-reference)
- [Error Codes and Handling](#error-codes-and-handling)
- [Performance Characteristics](#performance-characteristics)
- [Memory Management](#memory-management)
- [Interrupt Handling](#interrupt-handling)
- [Power Management](#power-management)
- [Device Tree Integration](#device-tree-integration)

## Driver Architecture

### Overview

The MPU-6050 kernel driver follows a modular architecture that separates concerns and provides multiple interfaces for userspace access. The driver is designed with robustness, performance, and maintainability in mind.

```
┌─────────────────────────────────────────────────────────────┐
│                    Userspace Applications                   │
├─────────────────────────┬───────────────────────────────────┤
│     Sysfs Interface     │       Character Device           │
│   /sys/class/mpu6050/   │        /dev/mpu6050              │
├─────────────────────────┴───────────────────────────────────┤
│                    MPU-6050 Core Driver                    │
│  ┌─────────────────┬──────────────────┬─────────────────┐  │
│  │   I2C Layer     │   Data Processing │  Power Mgmt     │  │
│  │  - Register R/W │   - Data Scaling  │  - Sleep/Wake   │  │
│  │  - Burst Read   │   - Calibration   │  - Clock Mgmt   │  │
│  │  - Error Check  │   - Filtering     │  - Reset Logic  │  │
│  └─────────────────┴──────────────────┴─────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                    Linux I2C Subsystem                     │
├─────────────────────────────────────────────────────────────┤
│                         Hardware                            │
│              MPU-6050 Sensor via I2C Bus                   │
└─────────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. Main Driver Module (`mpu6050_main.c`)

**Responsibilities:**
- Device probe and initialization
- Resource allocation and cleanup
- Power management implementation
- Core device operations
- Module loading/unloading

**Key Functions:**
```c
static int mpu6050_probe(struct i2c_client *client, 
                        const struct i2c_device_id *id);
static int mpu6050_remove(struct i2c_client *client);
static int mpu6050_init_device(struct mpu6050_data *data);
static int mpu6050_reset_device(struct mpu6050_data *data);
```

#### 2. I2C Communication Layer (`mpu6050_i2c.c`)

**Responsibilities:**
- Low-level register read/write operations
- I2C transaction management
- Error detection and recovery
- Burst read optimization

**Key Functions:**
```c
int mpu6050_i2c_read_reg(struct mpu6050_data *data, u8 reg, u8 *val);
int mpu6050_i2c_write_reg(struct mpu6050_data *data, u8 reg, u8 val);
int mpu6050_i2c_read_block(struct mpu6050_data *data, u8 reg, 
                          u8 *buf, size_t len);
int mpu6050_i2c_burst_read(struct mpu6050_data *data, 
                          struct mpu6050_raw_data *raw_data);
```

#### 3. Sysfs Interface (`mpu6050_sysfs.c`)

**Responsibilities:**
- Attribute file creation and management
- User-friendly data presentation
- Configuration parameter exposure
- Status reporting

**Attribute Groups:**
- **Data Attributes**: `accel_data`, `gyro_data`, `temp_data`
- **Scaled Attributes**: `accel_scale`, `gyro_scale`, `temp_celsius`
- **Config Attributes**: `accel_range`, `gyro_range`, `sample_rate`
- **Control Attributes**: `power_state`, `calibrate`, `self_test`

#### 4. Character Device Interface (`mpu6050_chardev.c`)

**Responsibilities:**
- Character device registration
- File operations implementation
- IOCTL command processing
- Direct hardware access

**File Operations:**
```c
static const struct file_operations mpu6050_fops = {
    .owner = THIS_MODULE,
    .open = mpu6050_open,
    .release = mpu6050_release,
    .read = mpu6050_read,
    .write = mpu6050_write,
    .unlocked_ioctl = mpu6050_ioctl,
    .compat_ioctl = mpu6050_compat_ioctl,
};
```

### Data Structures

#### Core Device Structure

```c
/**
 * struct mpu6050_data - Main device data structure
 * @client: I2C client structure
 * @dev: Device structure for sysfs and power management
 * @cdev: Character device structure
 * @class: Device class for automatic /dev node creation
 * @lock: Mutex for device access serialization
 * @data_lock: Spinlock for data structure protection
 * @regmap: Register map for efficient access
 * @config: Current device configuration
 * @calib_data: Calibration coefficients
 * @last_read: Timestamp of last sensor read
 * @read_count: Statistics counter
 * @error_count: Error statistics
 * @power_state: Current power management state
 * @irq: Interrupt number (if available)
 * @work: Work queue for interrupt handling
 */
struct mpu6050_data {
    struct i2c_client *client;
    struct device *dev;
    struct cdev cdev;
    struct class *class;
    
    /* Synchronization */
    struct mutex lock;
    spinlock_t data_lock;
    
    /* Hardware abstraction */
    struct regmap *regmap;
    
    /* Configuration and state */
    struct mpu6050_config config;
    struct mpu6050_calib_data calib_data;
    
    /* Statistics and debugging */
    ktime_t last_read;
    u32 read_count;
    u32 error_count;
    
    /* Power management */
    enum mpu6050_power_state power_state;
    
    /* Interrupt handling */
    int irq;
    struct work_struct work;
};
```

#### Configuration Structure

```c
/**
 * struct mpu6050_config - Device configuration
 * @sample_rate_div: Sample rate divider (0-255)
 * @dlpf_cfg: Digital Low Pass Filter configuration (0-7)
 * @gyro_range: Gyroscope full scale range (0-3)
 * @accel_range: Accelerometer full scale range (0-3)
 * @int_enable: Interrupt enable mask
 * @fifo_enable: FIFO enable mask
 */
struct mpu6050_config {
    u8 sample_rate_div;
    u8 dlpf_cfg;
    u8 gyro_range;
    u8 accel_range;
    u8 int_enable;
    u8 fifo_enable;
};
```

## I2C Communication Protocol

### Register Access Patterns

The MPU-6050 uses standard I2C protocol with the following characteristics:
- **Clock Speed**: Up to 400 kHz (Fast Mode)
- **Address Width**: 7-bit addressing
- **Data Width**: 8-bit registers
- **Byte Order**: Big-endian for multi-byte values

### I2C Transaction Types

#### 1. Single Register Read
```
START → ADDR+W → REG_ADDR → START → ADDR+R → DATA → STOP
```

#### 2. Single Register Write
```
START → ADDR+W → REG_ADDR → DATA → STOP
```

#### 3. Burst Read (Optimized for sensor data)
```
START → ADDR+W → START_REG → START → ADDR+R → DATA[0]...DATA[n] → STOP
```

### Implementation Details

```c
/**
 * mpu6050_i2c_read_reg - Read single register
 * @data: Device data structure
 * @reg: Register address
 * @val: Pointer to store value
 *
 * Returns: 0 on success, negative error code on failure
 */
static int mpu6050_i2c_read_reg(struct mpu6050_data *data, u8 reg, u8 *val)
{
    struct i2c_client *client = data->client;
    int ret;

    ret = i2c_smbus_read_byte_data(client, reg);
    if (ret < 0) {
        dev_err(&client->dev, "Failed to read reg 0x%02x: %d\n", reg, ret);
        data->error_count++;
        return ret;
    }

    *val = ret;
    return 0;
}

/**
 * mpu6050_i2c_burst_read - Optimized sensor data read
 * @data: Device data structure
 * @raw_data: Structure to store sensor readings
 *
 * Reads all sensor data in a single I2C transaction for better performance
 * and data coherency.
 */
static int mpu6050_i2c_burst_read(struct mpu6050_data *data,
                                 struct mpu6050_raw_data *raw_data)
{
    u8 buffer[14];
    int ret;

    /* Read all sensor registers in one burst (0x3B-0x48) */
    ret = i2c_smbus_read_i2c_block_data(data->client, 
                                       MPU6050_REG_ACCEL_XOUT_H,
                                       sizeof(buffer), buffer);
    if (ret < 0) {
        dev_err(data->dev, "Burst read failed: %d\n", ret);
        return ret;
    }

    /* Convert to host byte order */
    raw_data->accel_x = (s16)get_unaligned_be16(&buffer[0]);
    raw_data->accel_y = (s16)get_unaligned_be16(&buffer[2]);
    raw_data->accel_z = (s16)get_unaligned_be16(&buffer[4]);
    raw_data->temp = (s16)get_unaligned_be16(&buffer[6]);
    raw_data->gyro_x = (s16)get_unaligned_be16(&buffer[8]);
    raw_data->gyro_y = (s16)get_unaligned_be16(&buffer[10]);
    raw_data->gyro_z = (s16)get_unaligned_be16(&buffer[12]);

    data->read_count++;
    data->last_read = ktime_get();

    return 0;
}
```

### Error Handling and Recovery

The I2C layer implements several error recovery mechanisms:

1. **Timeout Handling**: Configurable timeouts for I2C transactions
2. **Retry Logic**: Automatic retry on temporary failures
3. **Bus Recovery**: I2C bus reset on communication errors
4. **Error Statistics**: Tracking for debugging and monitoring

```c
static int mpu6050_i2c_read_reg_retry(struct mpu6050_data *data, 
                                     u8 reg, u8 *val)
{
    int ret, retry = 3;

    do {
        ret = mpu6050_i2c_read_reg(data, reg, val);
        if (ret >= 0)
            break;
            
        if (ret == -EAGAIN || ret == -EBUSY) {
            usleep_range(1000, 2000);
            continue;
        }
        
        /* Fatal error */
        break;
        
    } while (--retry > 0);

    return ret;
}
```

## Character Device Interface

### Device Node Creation

The character device is automatically created at `/dev/mpu6050` with the following properties:
- **Major Number**: Dynamically allocated
- **Minor Number**: 0
- **Permissions**: 0666 (rw-rw-rw-)
- **Device Class**: `mpu6050`

### File Operations

#### Open Operation
```c
static int mpu6050_open(struct inode *inode, struct file *filp)
{
    struct mpu6050_data *data;
    
    data = container_of(inode->i_cdev, struct mpu6050_data, cdev);
    filp->private_data = data;
    
    mutex_lock(&data->lock);
    
    /* Wake up device if sleeping */
    if (data->power_state == MPU6050_POWER_SLEEP) {
        mpu6050_set_power_state(data, MPU6050_POWER_NORMAL);
    }
    
    mutex_unlock(&data->lock);
    
    return 0;
}
```

#### Read Operation
```c
static ssize_t mpu6050_read(struct file *filp, char __user *buf,
                           size_t count, loff_t *pos)
{
    struct mpu6050_data *data = filp->private_data;
    struct mpu6050_raw_data raw_data;
    int ret;

    if (count < sizeof(raw_data))
        return -EINVAL;

    mutex_lock(&data->lock);
    ret = mpu6050_read_sensor_data(data, &raw_data);
    mutex_unlock(&data->lock);

    if (ret < 0)
        return ret;

    if (copy_to_user(buf, &raw_data, sizeof(raw_data)))
        return -EFAULT;

    return sizeof(raw_data);
}
```

## IOCTL Commands Reference

### Command Structure

All IOCTL commands use the standard Linux IOCTL numbering scheme:
- **Magic Number**: 'M' (0x4D)
- **Direction**: `_IO`, `_IOR`, `_IOW`, `_IOWR`
- **Size**: Size of data structure being passed

### Available Commands

#### MPU6050_IOC_READ_RAW
```c
#define MPU6050_IOC_READ_RAW _IOR(MPU6050_IOC_MAGIC, 0, struct mpu6050_raw_data)
```
**Description**: Read raw sensor data directly from registers  
**Parameters**: Pointer to `struct mpu6050_raw_data`  
**Returns**: 0 on success, negative error code on failure

**Usage Example**:
```c
struct mpu6050_raw_data raw;
if (ioctl(fd, MPU6050_IOC_READ_RAW, &raw) == 0) {
    printf("Accel: %d, %d, %d\n", raw.accel_x, raw.accel_y, raw.accel_z);
    printf("Gyro: %d, %d, %d\n", raw.gyro_x, raw.gyro_y, raw.gyro_z);
}
```

#### MPU6050_IOC_READ_SCALED
```c
#define MPU6050_IOC_READ_SCALED _IOR(MPU6050_IOC_MAGIC, 1, struct mpu6050_scaled_data)
```
**Description**: Read sensor data scaled to physical units  
**Parameters**: Pointer to `struct mpu6050_scaled_data`  
**Units**: 
- Accelerometer: millig (mg)
- Gyroscope: millidegrees per second (mdps)
- Temperature: degrees Celsius × 100

#### MPU6050_IOC_SET_CONFIG
```c
#define MPU6050_IOC_SET_CONFIG _IOW(MPU6050_IOC_MAGIC, 2, struct mpu6050_config)
```
**Description**: Configure sensor parameters  
**Parameters**: Pointer to `struct mpu6050_config`

**Configuration Example**:
```c
struct mpu6050_config config = {
    .sample_rate_div = 7,        /* 125 Hz sample rate */
    .gyro_range = MPU6050_GYRO_FS_500,    /* ±500°/s */
    .accel_range = MPU6050_ACCEL_FS_4G,   /* ±4g */
    .dlpf_cfg = 3                /* 44 Hz low-pass filter */
};
ioctl(fd, MPU6050_IOC_SET_CONFIG, &config);
```

#### MPU6050_IOC_GET_CONFIG
```c
#define MPU6050_IOC_GET_CONFIG _IOR(MPU6050_IOC_MAGIC, 3, struct mpu6050_config)
```
**Description**: Read current sensor configuration  
**Parameters**: Pointer to `struct mpu6050_config`

#### MPU6050_IOC_RESET
```c
#define MPU6050_IOC_RESET _IO(MPU6050_IOC_MAGIC, 4)
```
**Description**: Reset sensor to default state  
**Parameters**: None  
**Effect**: Resets all registers to power-on defaults

#### MPU6050_IOC_SELF_TEST
```c
#define MPU6050_IOC_SELF_TEST _IOR(MPU6050_IOC_MAGIC, 5, u32)
```
**Description**: Run hardware self-test  
**Parameters**: Pointer to `u32` for result mask  
**Returns**: Bit mask indicating test results

**Self-Test Result Bits**:
- Bit 0: Accelerometer X-axis test result
- Bit 1: Accelerometer Y-axis test result  
- Bit 2: Accelerometer Z-axis test result
- Bit 3: Gyroscope X-axis test result
- Bit 4: Gyroscope Y-axis test result
- Bit 5: Gyroscope Z-axis test result

#### MPU6050_IOC_WHO_AM_I
```c
#define MPU6050_IOC_WHO_AM_I _IOR(MPU6050_IOC_MAGIC, 6, u8)
```
**Description**: Read device identification  
**Parameters**: Pointer to `u8`  
**Expected Value**: `0x68` for MPU-6050

### IOCTL Implementation

```c
static long mpu6050_ioctl(struct file *filp, unsigned int cmd, unsigned long arg)
{
    struct mpu6050_data *data = filp->private_data;
    int ret = 0;

    /* Validate IOCTL command */
    if (_IOC_TYPE(cmd) != MPU6050_IOC_MAGIC) {
        return -ENOTTY;
    }
    
    if (_IOC_NR(cmd) > MPU6050_IOC_MAXNR) {
        return -ENOTTY;
    }

    mutex_lock(&data->lock);

    switch (cmd) {
    case MPU6050_IOC_READ_RAW: {
        struct mpu6050_raw_data raw_data;
        
        ret = mpu6050_read_sensor_data(data, &raw_data);
        if (ret == 0) {
            if (copy_to_user((void __user *)arg, &raw_data, sizeof(raw_data)))
                ret = -EFAULT;
        }
        break;
    }
    
    case MPU6050_IOC_SET_CONFIG: {
        struct mpu6050_config config;
        
        if (copy_from_user(&config, (void __user *)arg, sizeof(config))) {
            ret = -EFAULT;
            break;
        }
        
        ret = mpu6050_set_config(data, &config);
        break;
    }
    
    case MPU6050_IOC_RESET:
        ret = mpu6050_reset_device(data);
        break;
        
    default:
        ret = -ENOTTY;
    }

    mutex_unlock(&data->lock);
    return ret;
}
```

## Error Codes and Handling

### Standard Error Codes

The driver uses standard Linux kernel error codes:

| Code | Meaning | Common Causes |
|------|---------|---------------|
| `-ENODEV` | No such device | I2C device not responding, wrong address |
| `-EIO` | I/O error | I2C communication failure, bus error |
| `-ENOMEM` | Out of memory | Failed memory allocation |
| `-EINVAL` | Invalid argument | Bad parameter values, out of range |
| `-EBUSY` | Device or resource busy | Device in use, I2C bus busy |
| `-EAGAIN` | Try again | Temporary failure, retry recommended |
| `-ETIMEDOUT` | Timeout | I2C transaction timeout |
| `-EFAULT` | Bad address | Invalid userspace pointer |

### Driver-Specific Error Codes

```c
/* Custom error codes defined in mpu6050.h */
#define MPU6050_ERR_I2C_FAILED     -1
#define MPU6050_ERR_INVALID_CHIP   -2  
#define MPU6050_ERR_CONFIG_FAILED  -3
#define MPU6050_ERR_READ_FAILED    -4
#define MPU6050_ERR_CALIBRATION    -5
#define MPU6050_ERR_SELF_TEST      -6
```

### Error Handling Strategy

#### 1. I2C Communication Errors
```c
static int mpu6050_handle_i2c_error(struct mpu6050_data *data, int error)
{
    switch (error) {
    case -EAGAIN:
    case -EBUSY:
        /* Temporary error - can retry */
        data->stats.retry_count++;
        return error;
        
    case -ENXIO:
    case -EIO:
        /* Bus error - reset I2C bus */
        dev_warn(data->dev, "I2C bus error, attempting recovery\n");
        i2c_recover_bus(data->client->adapter);
        data->stats.bus_error_count++;
        return error;
        
    case -ETIMEDOUT:
        /* Timeout - device may be stuck */
        dev_err(data->dev, "I2C timeout, device may need reset\n");
        data->stats.timeout_count++;
        return error;
        
    default:
        /* Unknown error */
        dev_err(data->dev, "Unknown I2C error: %d\n", error);
        data->stats.unknown_error_count++;
        return error;
    }
}
```

#### 2. Device State Errors
```c
static int mpu6050_check_device_state(struct mpu6050_data *data)
{
    u8 who_am_i, pwr_mgmt1;
    int ret;

    /* Verify device identity */
    ret = mpu6050_i2c_read_reg(data, MPU6050_REG_WHO_AM_I, &who_am_i);
    if (ret < 0)
        return ret;
        
    if (who_am_i != MPU6050_WHO_AM_I_VAL) {
        dev_err(data->dev, "Invalid device ID: 0x%02x\n", who_am_i);
        return -ENODEV;
    }

    /* Check power management state */
    ret = mpu6050_i2c_read_reg(data, MPU6050_REG_PWR_MGMT_1, &pwr_mgmt1);
    if (ret < 0)
        return ret;
        
    if (pwr_mgmt1 & MPU6050_PWR1_SLEEP) {
        dev_info(data->dev, "Device is in sleep mode\n");
        return -EAGAIN;  /* Not an error, just needs wake up */
    }

    return 0;
}
```

#### 3. Error Recovery Mechanisms
```c
/**
 * mpu6050_recover_device - Attempt to recover from error state
 * @data: Device data structure
 *
 * Implements escalating recovery strategy:
 * 1. Soft reset
 * 2. Hard reset
 * 3. Full reinitialization
 */
static int mpu6050_recover_device(struct mpu6050_data *data)
{
    int ret;
    
    dev_info(data->dev, "Attempting device recovery\n");
    
    /* Step 1: Soft reset */
    ret = mpu6050_soft_reset(data);
    if (ret == 0) {
        ret = mpu6050_check_device_state(data);
        if (ret == 0) {
            dev_info(data->dev, "Soft reset successful\n");
            return 0;
        }
    }
    
    /* Step 2: Hard reset */
    ret = mpu6050_hard_reset(data);
    if (ret == 0) {
        ret = mpu6050_check_device_state(data);
        if (ret == 0) {
            dev_info(data->dev, "Hard reset successful\n");
            return 0;
        }
    }
    
    /* Step 3: Full reinitialization */
    ret = mpu6050_init_device(data);
    if (ret == 0) {
        dev_info(data->dev, "Full reinitialization successful\n");
        return 0;
    }
    
    dev_err(data->dev, "Device recovery failed\n");
    return ret;
}
```

## Performance Characteristics

### Timing Specifications

| Parameter | Typical | Maximum | Unit | Notes |
|-----------|---------|---------|------|-------|
| I2C Clock Speed | 100 | 400 | kHz | Fast mode supported |
| Single Register Read | 50 | 100 | μs | Including I2C overhead |
| Burst Read (14 bytes) | 180 | 300 | μs | All sensor data |
| Power-on Time | 30 | 100 | ms | From sleep to active |
| Reset Recovery | 100 | 200 | ms | Full reset sequence |

### Throughput Analysis

#### Maximum Sample Rates

The MPU-6050 can achieve different sample rates depending on the Digital Low Pass Filter (DLPF) configuration:

| DLPF Setting | Gyro Rate | Accel Rate | Combined Rate |
|--------------|-----------|------------|---------------|
| 0 (260 Hz) | 8 kHz | 1 kHz | 1 kHz |
| 1 (184 Hz) | 1 kHz | 1 kHz | 1 kHz |
| 2 (94 Hz) | 1 kHz | 1 kHz | 1 kHz |
| 3 (44 Hz) | 1 kHz | 1 kHz | 1 kHz |
| 4 (21 Hz) | 1 kHz | 1 kHz | 1 kHz |
| 5 (10 Hz) | 1 kHz | 1 kHz | 1 kHz |
| 6 (5 Hz) | 1 kHz | 1 kHz | 1 kHz |

#### I2C Bus Utilization

For continuous reading at maximum sample rate (1 kHz):

```
Bus utilization = (Transaction time × Sample rate) / Available bandwidth

Single read: 50 μs × 1000 Hz = 5% bus utilization
Burst read: 180 μs × 1000 Hz = 18% bus utilization
```

### Memory Usage

#### Static Memory (per device instance)
```c
sizeof(struct mpu6050_data) ≈ 512 bytes
```

#### Dynamic Memory
- **I2C buffers**: ~100 bytes per transaction
- **Sysfs attributes**: ~50 bytes per attribute × 15 attributes = ~750 bytes
- **Character device**: ~200 bytes
- **Total per device**: ~1.5 KB

### CPU Usage

#### Interrupt-Driven Mode
- **Context switch overhead**: ~5 μs
- **Data processing**: ~10 μs
- **Total CPU time per sample**: ~15 μs

#### Polling Mode
- **Register access**: ~50 μs
- **Data processing**: ~10 μs
- **Total CPU time per sample**: ~60 μs

### Optimization Techniques

#### 1. Burst Reading
```c
/* Instead of 7 separate register reads (350 μs) */
for (i = 0; i < 7; i++) {
    mpu6050_i2c_read_reg(data, MPU6050_REG_ACCEL_XOUT_H + i*2, &buffer[i]);
}

/* Use single burst read (180 μs) */
mpu6050_i2c_read_block(data, MPU6050_REG_ACCEL_XOUT_H, buffer, 14);
```

#### 2. Register Caching
```c
/**
 * Cache frequently accessed configuration registers
 * to avoid unnecessary I2C transactions
 */
struct mpu6050_reg_cache {
    u8 pwr_mgmt1;
    u8 gyro_config;
    u8 accel_config;
    u8 sample_rate_div;
    bool valid;
};
```

#### 3. Interrupt Optimization
```c
/**
 * Use bottom-half processing to minimize
 * interrupt handler execution time
 */
static irqreturn_t mpu6050_irq_handler(int irq, void *dev_id)
{
    struct mpu6050_data *data = dev_id;
    
    /* Quick acknowledgment */
    schedule_work(&data->work);
    
    return IRQ_HANDLED;
}

static void mpu6050_work_handler(struct work_struct *work)
{
    struct mpu6050_data *data = container_of(work, struct mpu6050_data, work);
    
    /* Time-consuming data processing here */
    mpu6050_process_data(data);
}
```

This comprehensive technical documentation provides detailed insight into the MPU-6050 kernel driver's architecture, implementation, and performance characteristics. The driver is designed to be robust, efficient, and maintainable while providing multiple interfaces for userspace access.