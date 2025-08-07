#!/usr/bin/env python3
"""
Advanced Property-Based Testing Framework for Linux Kernel Drivers
Implements QuickCheck-style property testing with generators, shrinking, and analysis.
"""

import random
import struct
import time
import itertools
from typing import Any, Callable, Dict, List, Optional, Tuple, Generator, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum, IntEnum
import json
from pathlib import Path
import subprocess
import tempfile

class TestResult(Enum):
    """Test execution results."""
    PASS = "pass"
    FAIL = "fail" 
    DISCARD = "discard"
    ERROR = "error"

class ShrinkResult(Enum):
    """Shrinking process results."""
    SHRUNK = "shrunk"
    NO_SHRINK = "no_shrink"
    FAILED = "failed"

@dataclass
class PropertyTestCase:
    """Individual property test case."""
    inputs: List[Any]
    expected: Any
    actual: Any
    result: TestResult
    execution_time: float
    error_message: Optional[str] = None
    shrink_steps: int = 0

@dataclass
class PropertyTestReport:
    """Comprehensive property test report."""
    property_name: str
    total_tests: int
    passed: int
    failed: int
    discarded: int
    errors: int
    success_rate: float
    average_execution_time: float
    failed_cases: List[PropertyTestCase]
    coverage_data: Dict[str, Any] = field(default_factory=dict)
    shrink_statistics: Dict[str, int] = field(default_factory=dict)

class Generator(ABC):
    """Base class for property test data generators."""
    
    @abstractmethod
    def generate(self) -> Any:
        """Generate a random value."""
        pass
        
    @abstractmethod
    def shrink(self, value: Any) -> Generator[Any]:
        """Generate smaller versions of the value."""
        pass

class IntGenerator(Generator):
    """Integer generator with configurable bounds."""
    
    def __init__(self, min_val: int = 0, max_val: int = 2**31 - 1):
        self.min_val = min_val
        self.max_val = max_val
        
    def generate(self) -> int:
        return random.randint(self.min_val, self.max_val)
        
    def shrink(self, value: int) -> Generator[int]:
        """Shrink towards zero and bounds."""
        candidates = []
        
        # Shrink towards zero
        if value > 0:
            candidates.extend([0, value // 2, value - 1])
        elif value < 0:
            candidates.extend([0, value // 2, value + 1])
            
        # Shrink towards bounds
        if value != self.min_val:
            candidates.append(self.min_val)
        if value != self.max_val:
            candidates.append(self.max_val)
            
        # Remove duplicates and invalid values
        candidates = [c for c in set(candidates) 
                     if self.min_val <= c <= self.max_val and c != value]
                     
        for candidate in sorted(candidates, key=lambda x: abs(x)):
            yield candidate

class ByteArrayGenerator(Generator):
    """Byte array generator for I2C data testing."""
    
    def __init__(self, min_length: int = 1, max_length: int = 256):
        self.min_length = min_length
        self.max_length = max_length
        
    def generate(self) -> bytes:
        length = random.randint(self.min_length, self.max_length)
        return bytes([random.randint(0, 255) for _ in range(length)])
        
    def shrink(self, value: bytes) -> Generator[bytes]:
        """Shrink by reducing length and simplifying bytes."""
        if len(value) <= 1:
            return
            
        # Shrink length
        yield value[:len(value)//2]
        yield value[:1]
        
        # Simplify bytes
        if any(b != 0 for b in value):
            yield bytes(len(value))  # All zeros
            
        # Remove bytes from ends
        if len(value) > 1:
            yield value[1:]   # Remove first byte
            yield value[:-1]  # Remove last byte

class I2CAddressGenerator(Generator):
    """I2C address generator with valid 7-bit addresses."""
    
    def __init__(self, exclude_reserved: bool = True):
        self.exclude_reserved = exclude_reserved
        self.reserved_addresses = {0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
                                 0x78, 0x79, 0x7A, 0x7B, 0x7C, 0x7D, 0x7E, 0x7F}
        
    def generate(self) -> int:
        while True:
            addr = random.randint(0x08, 0x77)
            if not self.exclude_reserved or addr not in self.reserved_addresses:
                return addr
                
    def shrink(self, value: int) -> Generator[int]:
        """Shrink towards common I2C addresses."""
        common_addresses = [0x48, 0x50, 0x68, 0x76]  # Common sensor addresses
        
        for addr in common_addresses:
            if addr != value and (not self.exclude_reserved or 
                                addr not in self.reserved_addresses):
                yield addr
                
        # Shrink towards boundaries
        if value > 0x08:
            yield max(0x08, value - 1)
        if value < 0x77:
            yield min(0x77, value + 1)

class I2CTransactionGenerator(Generator):
    """Generator for complete I2C transaction patterns."""
    
    def __init__(self):
        self.addr_gen = I2CAddressGenerator()
        self.data_gen = ByteArrayGenerator(max_length=32)
        
    def generate(self) -> Dict[str, Any]:
        transaction_type = random.choice(['read', 'write', 'write_read'])
        addr = self.addr_gen.generate()
        
        if transaction_type == 'read':
            return {
                'type': 'read',
                'address': addr,
                'length': random.randint(1, 32)
            }
        elif transaction_type == 'write':
            return {
                'type': 'write', 
                'address': addr,
                'data': self.data_gen.generate()
            }
        else:  # write_read
            return {
                'type': 'write_read',
                'address': addr,
                'write_data': self.data_gen.generate(),
                'read_length': random.randint(1, 32)
            }
            
    def shrink(self, value: Dict[str, Any]) -> Generator[Dict[str, Any]]:
        """Shrink I2C transaction complexity."""
        # Shrink to simpler transaction types
        if value['type'] == 'write_read':
            yield {'type': 'read', 'address': value['address'], 'length': 1}
            yield {'type': 'write', 'address': value['address'], 'data': b'\x00'}
            
        # Shrink data/length
        if 'data' in value and len(value['data']) > 1:
            for shrunk_data in self.data_gen.shrink(value['data']):
                yield {**value, 'data': shrunk_data}
                
        if 'length' in value and value['length'] > 1:
            yield {**value, 'length': 1}
            
        # Shrink addresses
        for shrunk_addr in self.addr_gen.shrink(value['address']):
            yield {**value, 'address': shrunk_addr}

class ListGenerator(Generator):
    """Generate lists of values using another generator."""
    
    def __init__(self, element_generator: Generator, 
                 min_length: int = 0, max_length: int = 100):
        self.element_generator = element_generator
        self.min_length = min_length
        self.max_length = max_length
        
    def generate(self) -> List[Any]:
        length = random.randint(self.min_length, self.max_length)
        return [self.element_generator.generate() for _ in range(length)]
        
    def shrink(self, value: List[Any]) -> Generator[List[Any]]:
        """Shrink list by reducing length and shrinking elements."""
        if not value:
            return
            
        # Shrink length
        yield []
        if len(value) > 1:
            yield value[:len(value)//2]
            yield value[:1]
            yield value[1:]
            yield value[:-1]
            
        # Shrink individual elements
        for i, element in enumerate(value):
            for shrunk_element in self.element_generator.shrink(element):
                shrunk_list = value.copy()
                shrunk_list[i] = shrunk_element
                yield shrunk_list

class Property:
    """Property definition for testing."""
    
    def __init__(self, name: str, generators: List[Generator], 
                 test_function: Callable, precondition: Callable = None):
        self.name = name
        self.generators = generators  
        self.test_function = test_function
        self.precondition = precondition or (lambda *args: True)
        
    def check(self, *inputs) -> Tuple[TestResult, Any, float, Optional[str]]:
        """Check property with given inputs."""
        if not self.precondition(*inputs):
            return TestResult.DISCARD, None, 0.0, "Precondition failed"
            
        start_time = time.time()
        try:
            result = self.test_function(*inputs)
            execution_time = time.time() - start_time
            
            if result:
                return TestResult.PASS, result, execution_time, None
            else:
                return TestResult.FAIL, result, execution_time, "Property violated"
                
        except Exception as e:
            execution_time = time.time() - start_time
            return TestResult.ERROR, None, execution_time, str(e)

class PropertyTester:
    """Main property testing engine."""
    
    def __init__(self, max_tests: int = 100, max_shrinks: int = 100):
        self.max_tests = max_tests
        self.max_shrinks = max_shrinks
        self.random = random.Random()
        
    def test_property(self, prop: Property, seed: Optional[int] = None) -> PropertyTestReport:
        """Test a property with generated inputs."""
        if seed is not None:
            self.random.seed(seed)
            
        test_cases = []
        passed = 0
        failed = 0
        discarded = 0
        errors = 0
        
        print(f"Testing property: {prop.name}")
        
        for i in range(self.max_tests):
            # Generate test inputs
            inputs = [gen.generate() for gen in prop.generators]
            
            # Check property
            result, actual, exec_time, error_msg = prop.check(*inputs)
            
            test_case = PropertyTestCase(
                inputs=inputs,
                expected=True,  # Properties should always be true
                actual=actual,
                result=result,
                execution_time=exec_time,
                error_message=error_msg
            )
            
            if result == TestResult.PASS:
                passed += 1
            elif result == TestResult.FAIL:
                failed += 1
                # Try to shrink the failing case
                shrunk_case = self._shrink_failing_case(prop, test_case)
                test_cases.append(shrunk_case)
                print(f"  FAIL: {shrunk_case.inputs}")
            elif result == TestResult.DISCARD:
                discarded += 1
            else:  # ERROR
                errors += 1
                test_cases.append(test_case)
                print(f"  ERROR: {error_msg}")
                
            if (i + 1) % 10 == 0:
                print(f"  Progress: {i + 1}/{self.max_tests}")
                
        actual_tests = passed + failed + errors
        success_rate = (passed / actual_tests * 100) if actual_tests > 0 else 0
        avg_time = sum(tc.execution_time for tc in test_cases) / len(test_cases) if test_cases else 0
        
        return PropertyTestReport(
            property_name=prop.name,
            total_tests=actual_tests,
            passed=passed,
            failed=failed,
            discarded=discarded,
            errors=errors,
            success_rate=success_rate,
            average_execution_time=avg_time,
            failed_cases=[tc for tc in test_cases if tc.result == TestResult.FAIL]
        )
        
    def _shrink_failing_case(self, prop: Property, failing_case: PropertyTestCase) -> PropertyTestCase:
        """Shrink a failing test case to find minimal example."""
        current_inputs = failing_case.inputs.copy()
        shrink_steps = 0
        
        for _ in range(self.max_shrinks):
            shrunk = False
            
            # Try shrinking each input
            for i, (input_val, generator) in enumerate(zip(current_inputs, prop.generators)):
                for shrunk_val in generator.shrink(input_val):
                    test_inputs = current_inputs.copy()
                    test_inputs[i] = shrunk_val
                    
                    result, actual, exec_time, error_msg = prop.check(*test_inputs)
                    
                    if result == TestResult.FAIL:
                        # This shrunk version still fails, use it
                        current_inputs = test_inputs
                        shrink_steps += 1
                        shrunk = True
                        break
                        
                if shrunk:
                    break
                    
            if not shrunk:
                break
                
        # Return shrunk test case
        result, actual, exec_time, error_msg = prop.check(*current_inputs)
        return PropertyTestCase(
            inputs=current_inputs,
            expected=True,
            actual=actual,
            result=result,
            execution_time=exec_time,
            error_message=error_msg,
            shrink_steps=shrink_steps
        )

# Example I2C Driver Property Tests

def i2c_address_validity_property(address: int) -> bool:
    """Property: I2C addresses should be valid 7-bit values."""
    return 0x08 <= address <= 0x77

def i2c_transaction_length_property(transaction: Dict[str, Any]) -> bool:
    """Property: I2C transactions should have valid data lengths."""
    if 'data' in transaction:
        return 0 <= len(transaction['data']) <= 32
    if 'length' in transaction:
        return 0 < transaction['length'] <= 32
    if 'read_length' in transaction:
        return 0 < transaction['read_length'] <= 32
    return True

def i2c_write_read_consistency_property(address: int, write_data: bytes, read_length: int) -> bool:
    """Property: Write-read operations should be consistent."""
    # This would typically involve actual I2C operations
    # For testing, we simulate the behavior
    if not (0x08 <= address <= 0x77):
        return False
    if len(write_data) == 0 or len(write_data) > 32:
        return False
    if read_length <= 0 or read_length > 32:
        return False
    return True

def buffer_overflow_property(data: bytes, buffer_size: int) -> bool:
    """Property: Data should never exceed buffer boundaries."""
    return len(data) <= buffer_size

def create_i2c_property_suite() -> List[Property]:
    """Create comprehensive I2C driver property test suite."""
    return [
        Property(
            name="I2C Address Validity",
            generators=[I2CAddressGenerator()],
            test_function=i2c_address_validity_property
        ),
        Property(
            name="I2C Transaction Length",
            generators=[I2CTransactionGenerator()],
            test_function=i2c_transaction_length_property
        ),
        Property(
            name="I2C Write-Read Consistency",
            generators=[
                I2CAddressGenerator(),
                ByteArrayGenerator(max_length=32),
                IntGenerator(1, 32)
            ],
            test_function=i2c_write_read_consistency_property
        ),
        Property(
            name="Buffer Overflow Prevention",
            generators=[
                ByteArrayGenerator(max_length=64),
                IntGenerator(16, 32)
            ],
            test_function=buffer_overflow_property
        )
    ]

def generate_property_report(reports: List[PropertyTestReport], output_path: Path):
    """Generate comprehensive property testing report."""
    total_tests = sum(r.total_tests for r in reports)
    total_passed = sum(r.passed for r in reports)
    total_failed = sum(r.failed for r in reports)
    overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    report_data = {
        'summary': {
            'total_properties': len(reports),
            'total_tests': total_tests,
            'total_passed': total_passed,
            'total_failed': total_failed,
            'overall_success_rate': round(overall_success_rate, 2),
            'average_execution_time': round(
                sum(r.average_execution_time for r in reports) / len(reports), 4
            ) if reports else 0
        },
        'properties': [
            {
                'name': report.property_name,
                'tests': report.total_tests,
                'passed': report.passed,
                'failed': report.failed,
                'success_rate': round(report.success_rate, 2),
                'failed_examples': [
                    {
                        'inputs': case.inputs,
                        'error': case.error_message,
                        'shrink_steps': case.shrink_steps
                    }
                    for case in report.failed_cases[:5]  # Top 5 failures
                ]
            }
            for report in reports
        ]
    }
    
    with open(output_path, 'w') as f:
        json.dump(report_data, f, indent=2, default=str)
        
    print(f"\nProperty-Based Testing Report")
    print(f"=" * 50)
    print(f"Properties Tested: {len(reports)}")
    print(f"Total Test Cases: {total_tests}")
    print(f"Success Rate: {overall_success_rate:.2f}%")
    print(f"Failed Properties: {sum(1 for r in reports if r.failed > 0)}")
    print(f"\nReport saved to: {output_path}")

if __name__ == "__main__":
    # Example usage
    tester = PropertyTester(max_tests=200, max_shrinks=50)
    properties = create_i2c_property_suite()
    
    reports = []
    for prop in properties:
        report = tester.test_property(prop, seed=42)
        reports.append(report)
        
    generate_property_report(reports, Path("property_test_report.json"))