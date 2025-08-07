/**
 * @file sensor_data.c
 * @brief Implementation of sensor test data fixtures for MPU-6050 testing
 * 
 * This file provides pre-defined sensor data scenarios for comprehensive
 * testing of the MPU-6050 driver under various conditions.
 *
 * Copyright (C) 2025 Murray Kopit <murr2k@gmail.com>
 */

#include "sensor_data.h"
#include <string.h>
#include <math.h>

/* Pre-defined test scenarios */
static const struct sensor_test_scenario test_scenarios[] = {
    {
        .name = "device_stationary",
        .description = "Device at rest, Z-axis pointing up",
        .duration_ms = 1000,
        .sample_count = 100,
        .expected_motion = MOTION_STATIONARY,
        .base_data = {
            .accel_x = 0, .accel_y = 0, .accel_z = 16384,
            .gyro_x = 0, .gyro_y = 0, .gyro_z = 0,
            .temperature = 8653  /* 25°C */
        },
        .noise_level = 0.02,  /* 2% noise */
        .validation_tolerance = 0.1
    },
    {
        .name = "device_tilted_45deg",
        .description = "Device tilted 45 degrees around X-axis",
        .duration_ms = 1000,
        .sample_count = 100,
        .expected_motion = MOTION_TILTED,
        .base_data = {
            .accel_x = 0, .accel_y = -11585, .accel_z = 11585,  /* 45° tilt */
            .gyro_x = 0, .gyro_y = 0, .gyro_z = 0,
            .temperature = 8653
        },
        .noise_level = 0.02,
        .validation_tolerance = 0.15
    },
    {
        .name = "device_rotating_x",
        .description = "Device rotating around X-axis at 90°/s",
        .duration_ms = 2000,
        .sample_count = 200,
        .expected_motion = MOTION_ROTATING,
        .base_data = {
            .accel_x = 0, .accel_y = 0, .accel_z = 16384,
            .gyro_x = 2730, .gyro_y = 0, .gyro_z = 0,  /* ~90°/s */
            .temperature = 8753  /* Slightly warmer due to motion */
        },
        .noise_level = 0.05,
        .validation_tolerance = 0.2
    },
    {
        .name = "device_shaking",
        .description = "Device being shaken vigorously",
        .duration_ms = 3000,
        .sample_count = 300,
        .expected_motion = MOTION_VIBRATING,
        .base_data = {
            .accel_x = 0, .accel_y = 0, .accel_z = 16384,
            .gyro_x = 0, .gyro_y = 0, .gyro_z = 0,
            .temperature = 8853  /* Warmer due to vigorous motion */
        },
        .noise_level = 0.3,  /* High noise for shaking */
        .validation_tolerance = 0.5
    },
    {
        .name = "device_freefall",
        .description = "Device in free fall",
        .duration_ms = 500,
        .sample_count = 50,
        .expected_motion = MOTION_FREEFALL,
        .base_data = {
            .accel_x = 0, .accel_y = 0, .accel_z = 0,  /* No gravity in freefall */
            .gyro_x = 100, .gyro_y = -150, .gyro_z = 75,  /* Slight tumbling */
            .temperature = 8653
        },
        .noise_level = 0.05,
        .validation_tolerance = 0.1
    },
    {
        .name = "temperature_variation",
        .description = "Device warming up from -10°C to 60°C",
        .duration_ms = 5000,
        .sample_count = 100,
        .expected_motion = MOTION_STATIONARY,
        .base_data = {
            .accel_x = 0, .accel_y = 0, .accel_z = 16384,
            .gyro_x = 0, .gyro_y = 0, .gyro_z = 0,
            .temperature = 5253  /* Starting at -10°C */
        },
        .noise_level = 0.01,
        .validation_tolerance = 0.05
    },
    {
        .name = "sensor_saturation",
        .description = "High acceleration causing sensor saturation",
        .duration_ms = 1000,
        .sample_count = 100,
        .expected_motion = MOTION_HIGH_G,
        .base_data = {
            .accel_x = 30000, .accel_y = -25000, .accel_z = 20000,  /* Near saturation */
            .gyro_x = 15000, .gyro_y = -18000, .gyro_z = 22000,
            .temperature = 9053  /* Hot due to high forces */
        },
        .noise_level = 0.02,
        .validation_tolerance = 0.3
    },
    {
        .name = "low_noise_precision",
        .description = "Very stable conditions for precision testing",
        .duration_ms = 10000,
        .sample_count = 1000,
        .expected_motion = MOTION_STATIONARY,
        .base_data = {
            .accel_x = 0, .accel_y = 0, .accel_z = 16384,
            .gyro_x = 0, .gyro_y = 0, .gyro_z = 0,
            .temperature = 8653
        },
        .noise_level = 0.001,  /* Very low noise */
        .validation_tolerance = 0.02
    }
};

static const int num_test_scenarios = sizeof(test_scenarios) / sizeof(test_scenarios[0]);

/* Get test scenario by name */
const struct sensor_test_scenario* get_sensor_test_scenario(const char* name)
{
    if (!name) return NULL;
    
    for (int i = 0; i < num_test_scenarios; i++) {
        if (strcmp(test_scenarios[i].name, name) == 0) {
            return &test_scenarios[i];
        }
    }
    return NULL;
}

/* Get test scenario by index */
const struct sensor_test_scenario* get_sensor_test_scenario_by_index(int index)
{
    if (index < 0 || index >= num_test_scenarios) {
        return NULL;
    }
    return &test_scenarios[index];
}

/* Get number of available test scenarios */
int get_sensor_test_scenario_count(void)
{
    return num_test_scenarios;
}

/* Generate sensor data for a scenario */
struct sensor_reading generate_sensor_data_for_scenario(const struct sensor_test_scenario* scenario, 
                                                       int sample_index, 
                                                       uint64_t timestamp_us)
{
    struct sensor_reading reading = scenario->base_data;
    reading.timestamp = timestamp_us;
    
    if (!scenario) {
        return reading;
    }
    
    /* Add time-based variations for certain scenarios */
    if (strcmp(scenario->name, "temperature_variation") == 0) {
        /* Temperature rises linearly over time */
        double progress = (double)sample_index / scenario->sample_count;
        int temp_delta = (int)((20453 - 5253) * progress);  /* -10°C to 60°C */
        reading.temperature = 5253 + temp_delta;
    }
    else if (strcmp(scenario->name, "device_rotating_x") == 0) {
        /* Sinusoidal motion for rotation */
        double angle = 2.0 * M_PI * sample_index / 50.0;  /* Period of ~50 samples */
        reading.accel_y = (int16_t)(8000 * sin(angle));
        reading.accel_z = (int16_t)(16384 * cos(angle) * 0.7 + 16384 * 0.3);
    }
    else if (strcmp(scenario->name, "device_shaking") == 0) {
        /* Random vibrations */
        int seed = sample_index * 1234567;
        srand(seed);
        reading.accel_x += (rand() % 10000) - 5000;
        reading.accel_y += (rand() % 10000) - 5000;
        reading.accel_z += (rand() % 10000) - 5000;
        reading.gyro_x += (rand() % 4000) - 2000;
        reading.gyro_y += (rand() % 4000) - 2000;
        reading.gyro_z += (rand() % 4000) - 2000;
    }
    
    /* Add noise based on scenario noise level */
    if (scenario->noise_level > 0.0) {
        int seed = sample_index * 7654321;
        srand(seed);
        
        int accel_noise = (int)(scenario->noise_level * 1000);
        int gyro_noise = (int)(scenario->noise_level * 500);
        int temp_noise = (int)(scenario->noise_level * 100);
        
        reading.accel_x += (rand() % (2 * accel_noise)) - accel_noise;
        reading.accel_y += (rand() % (2 * accel_noise)) - accel_noise;
        reading.accel_z += (rand() % (2 * accel_noise)) - accel_noise;
        reading.gyro_x += (rand() % (2 * gyro_noise)) - gyro_noise;
        reading.gyro_y += (rand() % (2 * gyro_noise)) - gyro_noise;
        reading.gyro_z += (rand() % (2 * gyro_noise)) - gyro_noise;
        reading.temperature += (rand() % (2 * temp_noise)) - temp_noise;
    }
    
    return reading;
}

/* Validate sensor reading against scenario expectations */
int validate_sensor_reading_against_scenario(const struct sensor_test_scenario* scenario,
                                           const struct sensor_reading* reading)
{
    if (!scenario || !reading) {
        return 0;
    }
    
    /* Check basic data validity */
    if (reading->accel_x < -32768 || reading->accel_x > 32767 ||
        reading->accel_y < -32768 || reading->accel_y > 32767 ||
        reading->accel_z < -32768 || reading->accel_z > 32767 ||
        reading->gyro_x < -32768 || reading->gyro_x > 32767 ||
        reading->gyro_y < -32768 || reading->gyro_y > 32767 ||
        reading->gyro_z < -32768 || reading->gyro_z > 32767) {
        return 0;  /* Data out of range */
    }
    
    /* Temperature range check (-40°C to +85°C) */
    if (reading->temperature < 5253 || reading->temperature > 20653) {
        /* Allow some flexibility for test scenarios */
        if (strcmp(scenario->name, "sensor_saturation") != 0) {
            return 0;
        }
    }
    
    /* Motion-specific validations */
    switch (scenario->expected_motion) {
    case MOTION_STATIONARY:
        /* Check if acceleration magnitude is close to 1g */
        {
            double accel_mag = sqrt((double)reading->accel_x * reading->accel_x +
                                  (double)reading->accel_y * reading->accel_y +
                                  (double)reading->accel_z * reading->accel_z);
            double expected_mag = 16384.0;  /* 1g at ±2g range */
            double tolerance = expected_mag * scenario->validation_tolerance;
            
            if (fabs(accel_mag - expected_mag) > tolerance) {
                return 0;
            }
        }
        /* Gyroscope should show minimal rotation */
        {
            int gyro_mag = abs(reading->gyro_x) + abs(reading->gyro_y) + abs(reading->gyro_z);
            if (gyro_mag > 1000) {  /* Allow small drift */
                return 0;
            }
        }
        break;
        
    case MOTION_FREEFALL:
        /* Acceleration should be near zero */
        {
            double accel_mag = sqrt((double)reading->accel_x * reading->accel_x +
                                  (double)reading->accel_y * reading->accel_y +
                                  (double)reading->accel_z * reading->accel_z);
            double tolerance = 16384.0 * scenario->validation_tolerance;
            
            if (accel_mag > tolerance) {
                return 0;
            }
        }
        break;
        
    case MOTION_HIGH_G:
        /* Allow high acceleration values */
        {
            double accel_mag = sqrt((double)reading->accel_x * reading->accel_x +
                                  (double)reading->accel_y * reading->accel_y +
                                  (double)reading->accel_z * reading->accel_z);
            if (accel_mag < 16384.0) {  /* Should be significantly above 1g */
                return 0;
            }
        }
        break;
        
    case MOTION_TILTED:
    case MOTION_ROTATING:
    case MOTION_VIBRATING:
        /* More flexible validation for dynamic scenarios */
        break;
    }
    
    return 1;  /* Validation passed */
}

/* Generate a sequence of sensor data for a scenario */
int generate_sensor_sequence_for_scenario(const struct sensor_test_scenario* scenario,
                                        struct sensor_reading* readings,
                                        int max_readings,
                                        uint64_t start_timestamp_us)
{
    if (!scenario || !readings || max_readings <= 0) {
        return 0;
    }
    
    int count = (scenario->sample_count < max_readings) ? 
                scenario->sample_count : max_readings;
    
    uint64_t time_step_us = (scenario->duration_ms * 1000ULL) / scenario->sample_count;
    
    for (int i = 0; i < count; i++) {
        uint64_t timestamp = start_timestamp_us + (i * time_step_us);
        readings[i] = generate_sensor_data_for_scenario(scenario, i, timestamp);
    }
    
    return count;
}

/* Print scenario information */
void print_sensor_test_scenario_info(const struct sensor_test_scenario* scenario)
{
    if (!scenario) {
        printf("Invalid scenario\n");
        return;
    }
    
    printf("Scenario: %s\n", scenario->name);
    printf("Description: %s\n", scenario->description);
    printf("Duration: %d ms\n", scenario->duration_ms);
    printf("Sample Count: %d\n", scenario->sample_count);
    printf("Expected Motion: %d\n", scenario->expected_motion);
    printf("Base Data:\n");
    printf("  Accel: [%d, %d, %d]\n", 
           scenario->base_data.accel_x, 
           scenario->base_data.accel_y, 
           scenario->base_data.accel_z);
    printf("  Gyro: [%d, %d, %d]\n", 
           scenario->base_data.gyro_x, 
           scenario->base_data.gyro_y, 
           scenario->base_data.gyro_z);
    printf("  Temperature: %d (%.2f°C)\n", 
           scenario->base_data.temperature,
           (scenario->base_data.temperature / 340.0) + 36.53);
    printf("Noise Level: %.3f\n", scenario->noise_level);
    printf("Validation Tolerance: %.3f\n", scenario->validation_tolerance);
    printf("\n");
}

/* List all available scenarios */
void list_all_sensor_test_scenarios(void)
{
    printf("Available sensor test scenarios:\n");
    printf("===============================\n");
    for (int i = 0; i < num_test_scenarios; i++) {
        printf("%d. %s - %s\n", i + 1, test_scenarios[i].name, test_scenarios[i].description);
    }
    printf("\n");
}