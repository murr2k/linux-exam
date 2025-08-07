
#ifndef MOCK_SENSOR_DATA_H
#define MOCK_SENSOR_DATA_H

// Mock MPU-6050 sensor data for testing
static const struct {
    int16_t accel_x;
    int16_t accel_y;
    int16_t accel_z;
    int16_t temp;
    int16_t gyro_x;
    int16_t gyro_y;
    int16_t gyro_z;
} mock_sensor_readings[] = {
    {1000, 2000, 15000, 23000, 100, 200, 300},
    {-500, 1500, 14000, 22500, -50, 150, 250},
    {800, -300, 16000, 24000, 75, -25, 175},
    // Add more test data as needed
};

#define MOCK_SENSOR_DATA_COUNT (sizeof(mock_sensor_readings) / sizeof(mock_sensor_readings[0]))

#endif // MOCK_SENSOR_DATA_H
