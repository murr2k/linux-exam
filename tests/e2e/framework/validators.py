#!/usr/bin/env python3
"""
MPU-6050 Data Validators

This module provides comprehensive data validation, statistical analysis,
noise characterization, drift detection, and anomaly detection for MPU-6050
sensor data.

Copyright (C) 2025 Murray Kopit <murr2k@gmail.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""

import numpy as np
import statistics
import math
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from collections import deque
from scipy import signal, stats
import warnings

# Suppress scipy warnings for cleaner output
warnings.filterwarnings('ignore', category=RuntimeWarning)

@dataclass
class SensorLimits:
    """Physical limits for sensor data validation"""
    # Accelerometer limits (mg)
    accel_min_2g: int = -2048
    accel_max_2g: int = 2047
    accel_min_4g: int = -4096
    accel_max_4g: int = 4095
    accel_min_8g: int = -8192
    accel_max_8g: int = 8191
    accel_min_16g: int = -16384
    accel_max_16g: int = 16383
    
    # Gyroscope limits (mdps - milli degrees per second)
    gyro_min_250: int = -250000
    gyro_max_250: int = 249999
    gyro_min_500: int = -500000
    gyro_max_500: int = 499999
    gyro_min_1000: int = -1000000
    gyro_max_1000: int = 999999
    gyro_min_2000: int = -2000000
    gyro_max_2000: int = 1999999
    
    # Temperature limits (degrees Celsius * 100)
    temp_min: int = -4000  # -40°C
    temp_max: int = 8500   # 85°C
    
    # Noise thresholds
    accel_noise_threshold: float = 50.0  # mg
    gyro_noise_threshold: float = 25.0   # mdps
    temp_noise_threshold: float = 2.0    # °C


@dataclass
class ValidationResult:
    """Result of data validation"""
    valid: bool
    errors: List[str]
    warnings: List[str]
    metrics: Dict[str, Any]


@dataclass
class StatisticalMetrics:
    """Statistical metrics for sensor data"""
    mean: float
    median: float
    std_dev: float
    variance: float
    min_val: float
    max_val: float
    range_val: float
    rms: float
    skewness: float
    kurtosis: float
    percentile_5: float
    percentile_95: float


@dataclass
class NoiseAnalysis:
    """Noise analysis results"""
    noise_level: float
    snr: float  # Signal-to-noise ratio
    noise_frequency_content: Dict[str, float]
    noise_type: str  # white, pink, brown, etc.
    periodicity_detected: bool
    dominant_frequencies: List[float]


@dataclass
class DriftAnalysis:
    """Drift analysis results"""
    has_drift: bool
    drift_rate: float  # units per second
    drift_type: str  # linear, exponential, polynomial
    r_squared: float
    time_constant: Optional[float]
    offset_change: float


@dataclass
class AnomalyResult:
    """Anomaly detection result"""
    anomalies_detected: int
    anomaly_indices: List[int]
    anomaly_scores: List[float]
    threshold_used: float
    anomaly_types: List[str]  # spike, dropout, step, drift


class DataValidator:
    """Comprehensive data validation for MPU-6050 sensor data"""
    
    def __init__(self, limits: Optional[SensorLimits] = None):
        self.limits = limits or SensorLimits()
        
    def validate_raw_data(self, data: Tuple[int, ...]) -> ValidationResult:
        """Validate raw sensor data tuple (accel_x, accel_y, accel_z, temp, gyro_x, gyro_y, gyro_z)"""
        errors = []
        warnings = []
        metrics = {}
        
        if len(data) != 7:
            errors.append(f"Invalid data length: expected 7 values, got {len(data)}")
            return ValidationResult(False, errors, warnings, metrics)
        
        accel_x, accel_y, accel_z, temp, gyro_x, gyro_y, gyro_z = data
        
        # Validate accelerometer data (assuming ±2g range for raw data)
        for axis, value in [('X', accel_x), ('Y', accel_y), ('Z', accel_z)]:
            if not (-32768 <= value <= 32767):  # 16-bit signed integer range
                errors.append(f"Accelerometer {axis} out of range: {value}")
        
        # Validate gyroscope data
        for axis, value in [('X', gyro_x), ('Y', gyro_y), ('Z', gyro_z)]:
            if not (-32768 <= value <= 32767):  # 16-bit signed integer range
                errors.append(f"Gyroscope {axis} out of range: {value}")
        
        # Validate temperature data
        if not (-32768 <= temp <= 32767):  # 16-bit signed integer range
            errors.append(f"Temperature out of range: {temp}")
        
        # Check for suspicious patterns
        if all(v == 0 for v in data):
            warnings.append("All sensor readings are zero - possible sensor failure")
        
        if all(v == data[0] for v in data):
            warnings.append("All sensor readings identical - possible communication error")
        
        metrics['data_type'] = 'raw'
        metrics['value_ranges'] = {
            'accel': [min(accel_x, accel_y, accel_z), max(accel_x, accel_y, accel_z)],
            'gyro': [min(gyro_x, gyro_y, gyro_z), max(gyro_x, gyro_y, gyro_z)],
            'temp': temp
        }
        
        return ValidationResult(len(errors) == 0, errors, warnings, metrics)
    
    def validate_scaled_data(self, data: Tuple[int, ...]) -> ValidationResult:
        """Validate scaled sensor data tuple (accel_x_mg, accel_y_mg, accel_z_mg, temp_c100, gyro_x_mdps, gyro_y_mdps, gyro_z_mdps)"""
        errors = []
        warnings = []
        metrics = {}
        
        if len(data) != 7:
            errors.append(f"Invalid data length: expected 7 values, got {len(data)}")
            return ValidationResult(False, errors, warnings, metrics)
        
        accel_x, accel_y, accel_z, temp, gyro_x, gyro_y, gyro_z = data
        
        # Validate accelerometer data (mg) - assume ±16g max range
        for axis, value in [('X', accel_x), ('Y', accel_y), ('Z', accel_z)]:
            if not (self.limits.accel_min_16g <= value <= self.limits.accel_max_16g):
                errors.append(f"Accelerometer {axis} out of physical range: {value} mg")
            
            # Check for unrealistic values (greater than ±10g for normal operation)
            if abs(value) > 10000:
                warnings.append(f"Accelerometer {axis} unusually high: {value} mg")
        
        # Validate gyroscope data (mdps) - assume ±2000°/s max range
        for axis, value in [('X', gyro_x), ('Y', gyro_y), ('Z', gyro_z)]:
            if not (self.limits.gyro_min_2000 <= value <= self.limits.gyro_max_2000):
                errors.append(f"Gyroscope {axis} out of physical range: {value} mdps")
            
            # Check for unrealistic values (greater than ±1000°/s for normal operation)
            if abs(value) > 1000000:
                warnings.append(f"Gyroscope {axis} unusually high: {value} mdps")
        
        # Validate temperature data
        if not (self.limits.temp_min <= temp <= self.limits.temp_max):
            errors.append(f"Temperature out of physical range: {temp/100.0}°C")
        
        # Physics-based validation
        # Check if accelerometer magnitude is reasonable (should include gravity)
        accel_magnitude = math.sqrt(accel_x**2 + accel_y**2 + accel_z**2)
        if accel_magnitude < 800:  # Less than 0.8g - possible free fall or error
            warnings.append(f"Low accelerometer magnitude: {accel_magnitude:.1f} mg")
        elif accel_magnitude > 1200:  # More than 1.2g - possible acceleration or error
            warnings.append(f"High accelerometer magnitude: {accel_magnitude:.1f} mg")
        
        metrics['data_type'] = 'scaled'
        metrics['accel_magnitude'] = accel_magnitude
        metrics['temp_celsius'] = temp / 100.0
        metrics['value_ranges'] = {
            'accel': [min(accel_x, accel_y, accel_z), max(accel_x, accel_y, accel_z)],
            'gyro': [min(gyro_x, gyro_y, gyro_z), max(gyro_x, gyro_y, gyro_z)],
            'temp': temp
        }
        
        return ValidationResult(len(errors) == 0, errors, warnings, metrics)
    
    def validate_data_sequence(self, data_sequence: List[Tuple[int, ...]], 
                             is_scaled: bool = True) -> ValidationResult:
        """Validate a sequence of sensor data for consistency and patterns"""
        errors = []
        warnings = []
        metrics = {}
        
        if len(data_sequence) < 2:
            errors.append("Insufficient data for sequence validation")
            return ValidationResult(False, errors, warnings, metrics)
        
        # Validate each individual reading
        invalid_count = 0
        for i, data in enumerate(data_sequence):
            if is_scaled:
                result = self.validate_scaled_data(data)
            else:
                result = self.validate_raw_data(data)
            
            if not result.valid:
                invalid_count += 1
                if invalid_count <= 5:  # Report first 5 errors
                    errors.append(f"Sample {i}: {', '.join(result.errors)}")
        
        if invalid_count > 0:
            errors.append(f"Total invalid samples: {invalid_count}/{len(data_sequence)}")
        
        # Check for data sticking (same values repeated)
        sticking_count = 0
        for i in range(1, len(data_sequence)):
            if data_sequence[i] == data_sequence[i-1]:
                sticking_count += 1
        
        sticking_ratio = sticking_count / len(data_sequence)
        if sticking_ratio > 0.1:  # More than 10% stuck samples
            warnings.append(f"High data sticking ratio: {sticking_ratio:.1%}")
        
        # Check for unrealistic jumps
        if is_scaled:
            self._check_unrealistic_jumps(data_sequence, warnings)
        
        metrics['sequence_length'] = len(data_sequence)
        metrics['invalid_samples'] = invalid_count
        metrics['sticking_ratio'] = sticking_ratio
        metrics['valid_ratio'] = 1.0 - (invalid_count / len(data_sequence))
        
        return ValidationResult(len(errors) == 0, errors, warnings, metrics)
    
    def _check_unrealistic_jumps(self, data_sequence: List[Tuple], warnings: List[str]):
        """Check for unrealistic jumps between consecutive samples"""
        max_accel_jump = 1000  # mg
        max_gyro_jump = 50000  # mdps
        max_temp_jump = 500    # 5°C in units of °C*100
        
        jump_counts = {'accel': 0, 'gyro': 0, 'temp': 0}
        
        for i in range(1, len(data_sequence)):
            prev_data = data_sequence[i-1]
            curr_data = data_sequence[i]
            
            # Check accelerometer jumps
            for j in range(3):  # X, Y, Z axes
                jump = abs(curr_data[j] - prev_data[j])
                if jump > max_accel_jump:
                    jump_counts['accel'] += 1
            
            # Check temperature jump
            temp_jump = abs(curr_data[3] - prev_data[3])
            if temp_jump > max_temp_jump:
                jump_counts['temp'] += 1
            
            # Check gyroscope jumps
            for j in range(4, 7):  # Gyro X, Y, Z
                jump = abs(curr_data[j] - prev_data[j])
                if jump > max_gyro_jump:
                    jump_counts['gyro'] += 1
        
        for sensor_type, count in jump_counts.items():
            if count > len(data_sequence) * 0.05:  # More than 5% of samples
                warnings.append(f"High number of unrealistic {sensor_type} jumps: {count}")


class StatisticalAnalyzer:
    """Statistical analysis of sensor data"""
    
    def __init__(self):
        self.history = deque(maxlen=10000)  # Keep last 10k samples
    
    def calculate_metrics(self, data: List[float]) -> StatisticalMetrics:
        """Calculate comprehensive statistical metrics for a data series"""
        if len(data) < 2:
            raise ValueError("Insufficient data for statistical analysis")
        
        data_array = np.array(data)
        
        return StatisticalMetrics(
            mean=float(np.mean(data_array)),
            median=float(np.median(data_array)),
            std_dev=float(np.std(data_array)),
            variance=float(np.var(data_array)),
            min_val=float(np.min(data_array)),
            max_val=float(np.max(data_array)),
            range_val=float(np.ptp(data_array)),
            rms=float(np.sqrt(np.mean(data_array**2))),
            skewness=float(stats.skew(data_array)) if len(data_array) > 2 else 0.0,
            kurtosis=float(stats.kurtosis(data_array)) if len(data_array) > 3 else 0.0,
            percentile_5=float(np.percentile(data_array, 5)),
            percentile_95=float(np.percentile(data_array, 95))
        )
    
    def analyze_dataset(self, data_sequence: List[Tuple]) -> Dict[str, Any]:
        """Analyze complete dataset and return comprehensive statistics"""
        if not data_sequence:
            return {'error': 'Empty dataset'}
        
        # Separate data by axis
        accel_data = {
            'x': [sample[0] for sample in data_sequence],
            'y': [sample[1] for sample in data_sequence],
            'z': [sample[2] for sample in data_sequence]
        }
        
        gyro_data = {
            'x': [sample[4] for sample in data_sequence],
            'y': [sample[5] for sample in data_sequence],
            'z': [sample[6] for sample in data_sequence]
        }
        
        temp_data = [sample[3] for sample in data_sequence]
        
        results = {
            'sample_count': len(data_sequence),
            'accel_stats': {},
            'gyro_stats': {},
            'temp_stats': {},
            'correlation_analysis': {},
            'quality_metrics': {}
        }
        
        # Calculate statistics for each axis
        try:
            for axis in ['x', 'y', 'z']:
                results['accel_stats'][axis] = self.calculate_metrics(accel_data[axis])
                results['gyro_stats'][axis] = self.calculate_metrics(gyro_data[axis])
            
            results['temp_stats'] = self.calculate_metrics(temp_data)
            
            # Calculate correlations
            results['correlation_analysis'] = self._calculate_correlations(
                accel_data, gyro_data, temp_data)
            
            # Calculate quality metrics
            results['quality_metrics'] = self._calculate_quality_metrics(
                accel_data, gyro_data, temp_data)
            
        except Exception as e:
            results['error'] = f"Analysis failed: {str(e)}"
        
        return results
    
    def _calculate_correlations(self, accel_data: Dict, gyro_data: Dict, 
                              temp_data: List) -> Dict[str, float]:
        """Calculate cross-correlations between different sensors"""
        correlations = {}
        
        try:
            # Accelerometer cross-correlations
            correlations['accel_xy'] = float(np.corrcoef(accel_data['x'], accel_data['y'])[0, 1])
            correlations['accel_xz'] = float(np.corrcoef(accel_data['x'], accel_data['z'])[0, 1])
            correlations['accel_yz'] = float(np.corrcoef(accel_data['y'], accel_data['z'])[0, 1])
            
            # Gyroscope cross-correlations
            correlations['gyro_xy'] = float(np.corrcoef(gyro_data['x'], gyro_data['y'])[0, 1])
            correlations['gyro_xz'] = float(np.corrcoef(gyro_data['x'], gyro_data['z'])[0, 1])
            correlations['gyro_yz'] = float(np.corrcoef(gyro_data['y'], gyro_data['z'])[0, 1])
            
            # Temperature correlations
            correlations['temp_accel_x'] = float(np.corrcoef(temp_data, accel_data['x'])[0, 1])
            correlations['temp_gyro_x'] = float(np.corrcoef(temp_data, gyro_data['x'])[0, 1])
            
        except Exception:
            # Handle cases where correlation calculation fails (e.g., constant data)
            pass
        
        return correlations
    
    def _calculate_quality_metrics(self, accel_data: Dict, gyro_data: Dict, 
                                 temp_data: List) -> Dict[str, float]:
        """Calculate data quality metrics"""
        metrics = {}
        
        try:
            # Calculate noise levels (standard deviation)
            accel_noise = np.mean([np.std(accel_data[axis]) for axis in ['x', 'y', 'z']])
            gyro_noise = np.mean([np.std(gyro_data[axis]) for axis in ['x', 'y', 'z']])
            temp_noise = np.std(temp_data)
            
            metrics['accel_noise_level'] = float(accel_noise)
            metrics['gyro_noise_level'] = float(gyro_noise)
            metrics['temp_noise_level'] = float(temp_noise)
            
            # Calculate stability (coefficient of variation)
            metrics['accel_stability'] = float(accel_noise / np.mean([np.mean(np.abs(accel_data[axis])) for axis in ['x', 'y', 'z']]))
            metrics['gyro_stability'] = float(gyro_noise / (np.mean([np.mean(np.abs(gyro_data[axis])) for axis in ['x', 'y', 'z']]) + 1e-6))
            
            # Calculate effective resolution (LSB equivalent noise)
            metrics['accel_effective_resolution'] = float(accel_noise)
            metrics['gyro_effective_resolution'] = float(gyro_noise)
            
        except Exception:
            pass
        
        return metrics


class NoiseAnalyzer:
    """Advanced noise analysis for sensor data"""
    
    def __init__(self, sample_rate: float = 100.0):
        self.sample_rate = sample_rate
    
    def analyze_noise(self, data: List[float], signal_level: Optional[float] = None) -> NoiseAnalysis:
        """Perform comprehensive noise analysis"""
        if len(data) < 10:
            raise ValueError("Insufficient data for noise analysis")
        
        data_array = np.array(data)
        
        # Remove DC component for noise analysis
        detrended = data_array - np.mean(data_array)
        
        # Calculate noise level (RMS)
        noise_level = float(np.sqrt(np.mean(detrended**2)))
        
        # Calculate SNR if signal level provided
        if signal_level is not None:
            snr = 20 * np.log10(abs(signal_level) / (noise_level + 1e-12))
        else:
            snr = 20 * np.log10(np.std(data_array) / (noise_level + 1e-12))
        
        # Frequency domain analysis
        freq_analysis = self._analyze_frequency_content(detrended)
        
        # Determine noise type
        noise_type = self._classify_noise_type(detrended)
        
        # Check for periodicity
        periodicity, dominant_freqs = self._detect_periodicity(detrended)
        
        return NoiseAnalysis(
            noise_level=noise_level,
            snr=float(snr),
            noise_frequency_content=freq_analysis,
            noise_type=noise_type,
            periodicity_detected=periodicity,
            dominant_frequencies=dominant_freqs
        )
    
    def _analyze_frequency_content(self, data: np.ndarray) -> Dict[str, float]:
        """Analyze frequency content of noise"""
        if len(data) < 16:
            return {}
        
        try:
            # Calculate power spectral density
            freqs, psd = signal.welch(data, fs=self.sample_rate, nperseg=min(256, len(data)//4))
            
            # Divide into frequency bands
            nyquist = self.sample_rate / 2
            bands = {
                'low': (0, nyquist * 0.1),
                'mid': (nyquist * 0.1, nyquist * 0.4),
                'high': (nyquist * 0.4, nyquist)
            }
            
            band_power = {}
            total_power = np.sum(psd)
            
            for band_name, (f_low, f_high) in bands.items():
                band_mask = (freqs >= f_low) & (freqs <= f_high)
                band_power[f'{band_name}_band_power'] = float(np.sum(psd[band_mask]) / (total_power + 1e-12))
            
            return band_power
            
        except Exception:
            return {}
    
    def _classify_noise_type(self, data: np.ndarray) -> str:
        """Classify noise type based on spectral characteristics"""
        try:
            freqs, psd = signal.welch(data, fs=self.sample_rate, nperseg=min(256, len(data)//4))
            
            # Exclude DC component
            valid_mask = freqs > 0.1
            freqs = freqs[valid_mask]
            psd = psd[valid_mask]
            
            if len(freqs) < 3:
                return "unknown"
            
            # Fit power law: PSD ~ f^(-alpha)
            log_freqs = np.log(freqs)
            log_psd = np.log(psd + 1e-12)
            
            slope, _, r_value, _, _ = stats.linregress(log_freqs, log_psd)
            
            # Classify based on slope
            if abs(slope) < 0.5:
                return "white"
            elif -1.5 < slope < -0.5:
                return "pink"
            elif slope < -1.5:
                return "brown"
            else:
                return "blue"
                
        except Exception:
            return "unknown"
    
    def _detect_periodicity(self, data: np.ndarray) -> Tuple[bool, List[float]]:
        """Detect periodic components in the data"""
        if len(data) < 32:
            return False, []
        
        try:
            # Calculate autocorrelation
            autocorr = np.correlate(data, data, mode='full')
            autocorr = autocorr[autocorr.size // 2:]
            autocorr = autocorr / autocorr[0]  # Normalize
            
            # Find peaks in autocorrelation (excluding zero lag)
            peaks, properties = signal.find_peaks(
                autocorr[1:], 
                height=0.3,  # Minimum correlation of 0.3
                distance=int(self.sample_rate / 50)  # Minimum 50Hz separation
            )
            
            # Convert peak locations to frequencies
            dominant_freqs = []
            for peak in peaks:
                period_samples = peak + 1  # +1 because we excluded zero lag
                frequency = self.sample_rate / period_samples
                if 0.1 <= frequency <= self.sample_rate / 4:  # Valid frequency range
                    dominant_freqs.append(float(frequency))
            
            periodicity_detected = len(dominant_freqs) > 0
            
            return periodicity_detected, dominant_freqs[:5]  # Return top 5 frequencies
            
        except Exception:
            return False, []


class DriftDetector:
    """Detect and analyze drift in sensor data"""
    
    def __init__(self, sample_rate: float = 100.0):
        self.sample_rate = sample_rate
    
    def analyze_drift(self, data: List[float], timestamps: Optional[List[float]] = None) -> DriftAnalysis:
        """Analyze drift in time series data"""
        if len(data) < 10:
            raise ValueError("Insufficient data for drift analysis")
        
        data_array = np.array(data)
        
        # Generate timestamps if not provided
        if timestamps is None:
            timestamps = np.arange(len(data)) / self.sample_rate
        else:
            timestamps = np.array(timestamps)
        
        # Fit different models to detect drift
        linear_fit = self._fit_linear_model(timestamps, data_array)
        poly_fit = self._fit_polynomial_model(timestamps, data_array)
        exp_fit = self._fit_exponential_model(timestamps, data_array)
        
        # Determine best fit
        best_fit = max([linear_fit, poly_fit, exp_fit], key=lambda x: x['r_squared'])
        
        # Calculate drift parameters
        has_drift = best_fit['r_squared'] > 0.7 and abs(best_fit['drift_rate']) > 1e-6
        
        # Calculate offset change
        offset_change = float(data_array[-1] - data_array[0])
        
        # Estimate time constant for exponential drift
        time_constant = None
        if best_fit['type'] == 'exponential' and best_fit['time_constant'] is not None:
            time_constant = best_fit['time_constant']
        
        return DriftAnalysis(
            has_drift=has_drift,
            drift_rate=best_fit['drift_rate'],
            drift_type=best_fit['type'],
            r_squared=best_fit['r_squared'],
            time_constant=time_constant,
            offset_change=offset_change
        )
    
    def _fit_linear_model(self, timestamps: np.ndarray, data: np.ndarray) -> Dict:
        """Fit linear drift model"""
        try:
            slope, intercept, r_value, _, _ = stats.linregress(timestamps, data)
            return {
                'type': 'linear',
                'drift_rate': float(slope),
                'r_squared': float(r_value**2),
                'time_constant': None
            }
        except Exception:
            return {
                'type': 'linear',
                'drift_rate': 0.0,
                'r_squared': 0.0,
                'time_constant': None
            }
    
    def _fit_polynomial_model(self, timestamps: np.ndarray, data: np.ndarray) -> Dict:
        """Fit polynomial drift model (quadratic)"""
        try:
            coeffs = np.polyfit(timestamps, data, 2)
            fitted = np.polyval(coeffs, timestamps)
            
            # Calculate R-squared
            ss_res = np.sum((data - fitted) ** 2)
            ss_tot = np.sum((data - np.mean(data)) ** 2)
            r_squared = 1 - (ss_res / (ss_tot + 1e-12))
            
            # Drift rate is derivative at midpoint
            mid_time = (timestamps[-1] + timestamps[0]) / 2
            drift_rate = 2 * coeffs[0] * mid_time + coeffs[1]
            
            return {
                'type': 'polynomial',
                'drift_rate': float(drift_rate),
                'r_squared': float(r_squared),
                'time_constant': None
            }
        except Exception:
            return {
                'type': 'polynomial',
                'drift_rate': 0.0,
                'r_squared': 0.0,
                'time_constant': None
            }
    
    def _fit_exponential_model(self, timestamps: np.ndarray, data: np.ndarray) -> Dict:
        """Fit exponential drift model"""
        try:
            # Simple exponential: y = a + b * exp(c * t)
            # Linearize by assuming small exponential component
            
            if len(data) < 5:
                return {
                    'type': 'exponential',
                    'drift_rate': 0.0,
                    'r_squared': 0.0,
                    'time_constant': None
                }
            
            # Fit exponential using linear approximation for small changes
            dt = np.diff(timestamps)
            dy = np.diff(data)
            
            if len(dt) == 0 or np.all(dt == 0):
                return {
                    'type': 'exponential',
                    'drift_rate': 0.0,
                    'r_squared': 0.0,
                    'time_constant': None
                }
            
            # Estimate exponential rate
            rate_estimates = dy / (dt * (data[:-1] + 1e-12))
            exp_rate = np.median(rate_estimates)
            
            # Simple R-squared estimate
            predicted = data[0] * np.exp(exp_rate * (timestamps - timestamps[0]))
            ss_res = np.sum((data - predicted) ** 2)
            ss_tot = np.sum((data - np.mean(data)) ** 2)
            r_squared = max(0, 1 - (ss_res / (ss_tot + 1e-12)))
            
            # Time constant
            time_constant = 1 / (abs(exp_rate) + 1e-12) if exp_rate != 0 else None
            
            return {
                'type': 'exponential',
                'drift_rate': float(exp_rate * np.mean(data)),
                'r_squared': float(r_squared),
                'time_constant': float(time_constant) if time_constant else None
            }
            
        except Exception:
            return {
                'type': 'exponential',
                'drift_rate': 0.0,
                'r_squared': 0.0,
                'time_constant': None
            }


class AnomalyDetector:
    """Detect anomalies in sensor data"""
    
    def __init__(self):
        self.baseline_stats = {}
    
    def detect_anomalies(self, data: List[float], 
                        method: str = 'statistical',
                        threshold: float = 3.0) -> AnomalyResult:
        """Detect anomalies using specified method"""
        if len(data) < 10:
            raise ValueError("Insufficient data for anomaly detection")
        
        data_array = np.array(data)
        
        if method == 'statistical':
            return self._statistical_anomaly_detection(data_array, threshold)
        elif method == 'isolation_forest':
            return self._isolation_forest_detection(data_array)
        elif method == 'change_point':
            return self._change_point_detection(data_array)
        else:
            raise ValueError(f"Unknown anomaly detection method: {method}")
    
    def _statistical_anomaly_detection(self, data: np.ndarray, threshold: float) -> AnomalyResult:
        """Statistical outlier detection using z-score"""
        mean = np.mean(data)
        std = np.std(data)
        
        if std == 0:
            return AnomalyResult(0, [], [], threshold, [])
        
        z_scores = np.abs((data - mean) / std)
        anomaly_mask = z_scores > threshold
        
        anomaly_indices = np.where(anomaly_mask)[0].tolist()
        anomaly_scores = z_scores[anomaly_mask].tolist()
        
        # Classify anomaly types
        anomaly_types = []
        for idx in anomaly_indices:
            if data[idx] > mean + threshold * std:
                anomaly_types.append('spike_high')
            elif data[idx] < mean - threshold * std:
                anomaly_types.append('spike_low')
            else:
                anomaly_types.append('outlier')
        
        return AnomalyResult(
            anomalies_detected=len(anomaly_indices),
            anomaly_indices=anomaly_indices,
            anomaly_scores=anomaly_scores,
            threshold_used=threshold,
            anomaly_types=anomaly_types
        )
    
    def _isolation_forest_detection(self, data: np.ndarray) -> AnomalyResult:
        """Isolation Forest anomaly detection (simplified implementation)"""
        try:
            # Simple implementation without sklearn
            # Use interquartile range method as approximation
            q1 = np.percentile(data, 25)
            q3 = np.percentile(data, 75)
            iqr = q3 - q1
            
            threshold_factor = 1.5
            lower_bound = q1 - threshold_factor * iqr
            upper_bound = q3 + threshold_factor * iqr
            
            anomaly_mask = (data < lower_bound) | (data > upper_bound)
            anomaly_indices = np.where(anomaly_mask)[0].tolist()
            
            # Calculate anomaly scores based on distance from bounds
            anomaly_scores = []
            anomaly_types = []
            
            for idx in anomaly_indices:
                if data[idx] < lower_bound:
                    score = (lower_bound - data[idx]) / (iqr + 1e-12)
                    anomaly_types.append('outlier_low')
                else:
                    score = (data[idx] - upper_bound) / (iqr + 1e-12)
                    anomaly_types.append('outlier_high')
                
                anomaly_scores.append(float(score))
            
            return AnomalyResult(
                anomalies_detected=len(anomaly_indices),
                anomaly_indices=anomaly_indices,
                anomaly_scores=anomaly_scores,
                threshold_used=threshold_factor,
                anomaly_types=anomaly_types
            )
            
        except Exception:
            return AnomalyResult(0, [], [], 1.5, [])
    
    def _change_point_detection(self, data: np.ndarray) -> AnomalyResult:
        """Change point detection for step changes"""
        if len(data) < 20:
            return AnomalyResult(0, [], [], 0.0, [])
        
        try:
            # Simple change point detection using moving window variance
            window_size = max(5, len(data) // 20)
            anomaly_indices = []
            anomaly_scores = []
            anomaly_types = []
            
            for i in range(window_size, len(data) - window_size):
                # Calculate variance before and after potential change point
                before = data[i-window_size:i]
                after = data[i:i+window_size]
                
                var_before = np.var(before)
                var_after = np.var(after)
                mean_before = np.mean(before)
                mean_after = np.mean(after)
                
                # Detect step change
                mean_change = abs(mean_after - mean_before)
                combined_std = np.sqrt((var_before + var_after) / 2 + 1e-12)
                
                if mean_change > 3 * combined_std:
                    anomaly_indices.append(i)
                    anomaly_scores.append(float(mean_change / combined_std))
                    if mean_after > mean_before:
                        anomaly_types.append('step_up')
                    else:
                        anomaly_types.append('step_down')
            
            return AnomalyResult(
                anomalies_detected=len(anomaly_indices),
                anomaly_indices=anomaly_indices,
                anomaly_scores=anomaly_scores,
                threshold_used=3.0,
                anomaly_types=anomaly_types
            )
            
        except Exception:
            return AnomalyResult(0, [], [], 3.0, [])
    
    def update_baseline(self, data: List[float], sensor_type: str):
        """Update baseline statistics for future anomaly detection"""
        if len(data) < 10:
            return
        
        data_array = np.array(data)
        self.baseline_stats[sensor_type] = {
            'mean': float(np.mean(data_array)),
            'std': float(np.std(data_array)),
            'median': float(np.median(data_array)),
            'q1': float(np.percentile(data_array, 25)),
            'q3': float(np.percentile(data_array, 75)),
            'min': float(np.min(data_array)),
            'max': float(np.max(data_array))
        }