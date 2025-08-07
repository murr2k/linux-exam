# Environment Validation and Management System
# Comprehensive test environment validation, isolation, and management

from .validation.env_validator import EnvironmentValidator, EnvironmentConfig, ValidationResult
from .validation.dependency_checker import DependencyChecker, DependencySet, Dependency
from .isolation.test_sandbox import TestSandbox, SandboxConfig, test_sandbox
from .consistency.env_consistency import EnvironmentConsistencyManager, ConsistencyConfig, EnvironmentSnapshot
from .monitoring.env_monitor import EnvironmentMonitor, MonitoringConfig, HealthMetric, DiagnosticResult
from .config.environment_manager import EnvironmentManager, EnvironmentProfile
from .troubleshoot import AutoTroubleshooter, TroubleshootResult

__version__ = "1.0.0"
__author__ = "Test Environment Management System"

__all__ = [
    # Validation
    "EnvironmentValidator",
    "EnvironmentConfig", 
    "ValidationResult",
    "DependencyChecker",
    "DependencySet",
    "Dependency",
    
    # Isolation
    "TestSandbox",
    "SandboxConfig",
    "test_sandbox",
    
    # Consistency
    "EnvironmentConsistencyManager",
    "ConsistencyConfig",
    "EnvironmentSnapshot",
    
    # Monitoring
    "EnvironmentMonitor",
    "MonitoringConfig",
    "HealthMetric",
    "DiagnosticResult",
    
    # Management
    "EnvironmentManager",
    "EnvironmentProfile",
    
    # Troubleshooting
    "AutoTroubleshooter",
    "TroubleshootResult"
]