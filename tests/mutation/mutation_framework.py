#!/usr/bin/env python3
"""
Enhanced Mutation Testing Framework for Kernel Code
Provides comprehensive mutation operators and automated test execution.
"""

import ast
import random
import subprocess
import json
import time
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
from pathlib import Path
import tempfile
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum
import re

class MutationType(Enum):
    """Types of mutations that can be applied to kernel code."""
    ARITHMETIC_OPERATOR = "arithmetic_operator"
    RELATIONAL_OPERATOR = "relational_operator" 
    LOGICAL_OPERATOR = "logical_operator"
    ASSIGNMENT_OPERATOR = "assignment_operator"
    STATEMENT_DELETION = "statement_deletion"
    CONSTANT_REPLACEMENT = "constant_replacement"
    POINTER_DEREFERENCE = "pointer_dereference"
    MEMORY_ALLOCATION = "memory_allocation"
    LOCK_MECHANISM = "lock_mechanism"
    ERROR_HANDLING = "error_handling"
    REGISTER_ACCESS = "register_access"
    TIMING_CRITICAL = "timing_critical"

@dataclass
class MutationResult:
    """Result of a single mutation test."""
    mutation_id: str
    mutation_type: MutationType
    original_code: str
    mutated_code: str
    file_path: str
    line_number: int
    test_passed: bool
    killed: bool  # Whether the mutation was detected
    execution_time: float
    error_output: Optional[str] = None
    coverage_data: Dict[str, float] = field(default_factory=dict)

@dataclass
class MutationReport:
    """Comprehensive mutation testing report."""
    total_mutations: int
    killed_mutations: int
    survived_mutations: int
    mutation_score: float
    test_results: List[MutationResult]
    execution_time: float
    coverage_by_file: Dict[str, float]
    mutation_hotspots: List[Tuple[str, int, float]]  # File, line, mutation_count

class KernelMutationOperator:
    """Base class for kernel-specific mutation operators."""
    
    def __init__(self, mutation_type: MutationType):
        self.mutation_type = mutation_type
        
    def can_mutate(self, code: str, line_num: int) -> bool:
        """Check if this operator can mutate the given line."""
        raise NotImplementedError
        
    def mutate(self, code: str, line_num: int) -> List[str]:
        """Generate all possible mutations for the given line."""
        raise NotImplementedError

class ArithmeticMutator(KernelMutationOperator):
    """Mutates arithmetic operators in kernel code."""
    
    OPERATORS = {
        '+': ['-', '*', '/', '%'],
        '-': ['+', '*', '/', '%'], 
        '*': ['+', '-', '/', '%'],
        '/': ['+', '-', '*', '%'],
        '%': ['+', '-', '*', '/'],
        '++': ['--', '+2', '-1'],
        '--': ['++', '+1', '-2']
    }
    
    def __init__(self):
        super().__init__(MutationType.ARITHMETIC_OPERATOR)
        
    def can_mutate(self, code: str, line_num: int) -> bool:
        line = code.split('\n')[line_num - 1] if line_num <= len(code.split('\n')) else ""
        return any(op in line for op in self.OPERATORS.keys())
        
    def mutate(self, code: str, line_num: int) -> List[str]:
        lines = code.split('\n')
        if line_num > len(lines):
            return []
            
        original_line = lines[line_num - 1]
        mutations = []
        
        for original_op, replacement_ops in self.OPERATORS.items():
            if original_op in original_line:
                for replacement_op in replacement_ops:
                    mutated_line = original_line.replace(original_op, replacement_op, 1)
                    mutated_lines = lines.copy()
                    mutated_lines[line_num - 1] = mutated_line
                    mutations.append('\n'.join(mutated_lines))
                    
        return mutations

class RelationalMutator(KernelMutationOperator):
    """Mutates relational operators in kernel code."""
    
    OPERATORS = {
        '==': ['!=', '>', '<', '>=', '<='],
        '!=': ['==', '>', '<', '>=', '<='],
        '>': ['<', '>=', '<=', '==', '!='],
        '<': ['>', '>=', '<=', '==', '!='],
        '>=': ['<=', '>', '<', '==', '!='],
        '<=': ['>=', '>', '<', '==', '!=']
    }
    
    def __init__(self):
        super().__init__(MutationType.RELATIONAL_OPERATOR)
        
    def can_mutate(self, code: str, line_num: int) -> bool:
        line = code.split('\n')[line_num - 1] if line_num <= len(code.split('\n')) else ""
        return any(op in line for op in self.OPERATORS.keys())
        
    def mutate(self, code: str, line_num: int) -> List[str]:
        lines = code.split('\n')
        if line_num > len(lines):
            return []
            
        original_line = lines[line_num - 1]
        mutations = []
        
        # Sort operators by length to avoid partial replacements
        sorted_ops = sorted(self.OPERATORS.keys(), key=len, reverse=True)
        
        for original_op in sorted_ops:
            if original_op in original_line:
                for replacement_op in self.OPERATORS[original_op]:
                    mutated_line = original_line.replace(original_op, replacement_op, 1)
                    mutated_lines = lines.copy()
                    mutated_lines[line_num - 1] = mutated_line
                    mutations.append('\n'.join(mutated_lines))
                break  # Only mutate first found operator per line
                    
        return mutations

class PointerDereferenceMutator(KernelMutationOperator):
    """Mutates pointer dereference patterns in kernel code."""
    
    def __init__(self):
        super().__init__(MutationType.POINTER_DEREFERENCE)
        
    def can_mutate(self, code: str, line_num: int) -> bool:
        line = code.split('\n')[line_num - 1] if line_num <= len(code.split('\n')) else ""
        # Look for pointer dereferences
        patterns = [r'\*\w+', r'\w+->\w+', r'&\w+']
        return any(re.search(pattern, line) for pattern in patterns)
        
    def mutate(self, code: str, line_num: int) -> List[str]:
        lines = code.split('\n')
        if line_num > len(lines):
            return []
            
        original_line = lines[line_num - 1]
        mutations = []
        
        # Mutation: Remove dereference operator
        if '*' in original_line:
            mutated_line = re.sub(r'\*(\w+)', r'\1', original_line, count=1)
            if mutated_line != original_line:
                mutated_lines = lines.copy()
                mutated_lines[line_num - 1] = mutated_line
                mutations.append('\n'.join(mutated_lines))
        
        # Mutation: Change -> to .
        if '->' in original_line:
            mutated_line = original_line.replace('->', '.', 1)
            mutated_lines = lines.copy()
            mutated_lines[line_num - 1] = mutated_line
            mutations.append('\n'.join(mutated_lines))
            
        return mutations

class ErrorHandlingMutator(KernelMutationOperator):
    """Mutates error handling patterns in kernel code."""
    
    ERROR_CODES = ['0', '-1', '-ENOMEM', '-EINVAL', '-EIO', '-EBUSY']
    
    def __init__(self):
        super().__init__(MutationType.ERROR_HANDLING)
        
    def can_mutate(self, code: str, line_num: int) -> bool:
        line = code.split('\n')[line_num - 1] if line_num <= len(code.split('\n')) else ""
        return 'return' in line and any(code in line for code in self.ERROR_CODES)
        
    def mutate(self, code: str, line_num: int) -> List[str]:
        lines = code.split('\n')
        if line_num > len(lines):
            return []
            
        original_line = lines[line_num - 1]
        mutations = []
        
        for original_code in self.ERROR_CODES:
            if original_code in original_line:
                for replacement_code in self.ERROR_CODES:
                    if replacement_code != original_code:
                        mutated_line = original_line.replace(original_code, replacement_code, 1)
                        mutated_lines = lines.copy()
                        mutated_lines[line_num - 1] = mutated_line
                        mutations.append('\n'.join(mutated_lines))
                break
                
        return mutations

class LockMechanismMutator(KernelMutationOperator):
    """Mutates locking mechanisms in kernel code."""
    
    LOCK_FUNCTIONS = {
        'spin_lock': ['spin_unlock', 'mutex_lock', 'raw_spin_lock'],
        'spin_unlock': ['spin_lock', 'mutex_unlock', 'raw_spin_unlock'],
        'mutex_lock': ['mutex_unlock', 'spin_lock', 'down'],
        'mutex_unlock': ['mutex_lock', 'spin_unlock', 'up']
    }
    
    def __init__(self):
        super().__init__(MutationType.LOCK_MECHANISM)
        
    def can_mutate(self, code: str, line_num: int) -> bool:
        line = code.split('\n')[line_num - 1] if line_num <= len(code.split('\n')) else ""
        return any(func in line for func in self.LOCK_FUNCTIONS.keys())
        
    def mutate(self, code: str, line_num: int) -> List[str]:
        lines = code.split('\n')
        if line_num > len(lines):
            return []
            
        original_line = lines[line_num - 1]
        mutations = []
        
        for original_func, replacement_funcs in self.LOCK_FUNCTIONS.items():
            if original_func in original_line:
                for replacement_func in replacement_funcs:
                    mutated_line = original_line.replace(original_func, replacement_func, 1)
                    mutated_lines = lines.copy()
                    mutated_lines[line_num - 1] = mutated_line
                    mutations.append('\n'.join(mutated_lines))
                break
                
        return mutations

class MutationTester:
    """Main mutation testing engine."""
    
    def __init__(self, source_dir: Path, test_command: str, 
                 operators: Optional[List[KernelMutationOperator]] = None,
                 parallel_jobs: int = None):
        self.source_dir = Path(source_dir)
        self.test_command = test_command
        self.operators = operators or self._get_default_operators()
        self.parallel_jobs = parallel_jobs or mp.cpu_count()
        self.mutation_counter = 0
        
    def _get_default_operators(self) -> List[KernelMutationOperator]:
        """Get default set of mutation operators."""
        return [
            ArithmeticMutator(),
            RelationalMutator(),
            PointerDereferenceMutator(),
            ErrorHandlingMutator(),
            LockMechanismMutator()
        ]
        
    def find_target_files(self, extensions: List[str] = None) -> List[Path]:
        """Find all target files for mutation testing."""
        extensions = extensions or ['.c', '.h']
        target_files = []
        
        for ext in extensions:
            target_files.extend(self.source_dir.rglob(f'*{ext}'))
            
        return target_files
        
    def generate_mutations(self, file_path: Path) -> List[Tuple[str, int, MutationType, str, str]]:
        """Generate all possible mutations for a file."""
        with open(file_path, 'r') as f:
            original_code = f.read()
            
        mutations = []
        lines = original_code.split('\n')
        
        for line_num in range(1, len(lines) + 1):
            for operator in self.operators:
                if operator.can_mutate(original_code, line_num):
                    mutated_codes = operator.mutate(original_code, line_num)
                    for mutated_code in mutated_codes:
                        self.mutation_counter += 1
                        mutation_id = f"mut_{self.mutation_counter:06d}"
                        mutations.append((
                            mutation_id, 
                            line_num, 
                            operator.mutation_type,
                            original_code,
                            mutated_code
                        ))
                        
        return mutations
        
    def _run_single_mutation_test(self, args: Tuple) -> MutationResult:
        """Run a single mutation test."""
        mutation_id, file_path, line_num, mutation_type, original_code, mutated_code = args
        
        start_time = time.time()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as temp_file:
            temp_file.write(mutated_code)
            temp_file.flush()
            
            try:
                # Replace original file temporarily
                original_path = Path(file_path)
                backup_content = original_path.read_text()
                original_path.write_text(mutated_code)
                
                # Run tests
                result = subprocess.run(
                    self.test_command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                
                test_passed = result.returncode == 0
                killed = not test_passed  # Mutation killed if tests fail
                
                execution_time = time.time() - start_time
                
                return MutationResult(
                    mutation_id=mutation_id,
                    mutation_type=mutation_type,
                    original_code=original_code,
                    mutated_code=mutated_code,
                    file_path=str(file_path),
                    line_number=line_num,
                    test_passed=test_passed,
                    killed=killed,
                    execution_time=execution_time,
                    error_output=result.stderr if result.stderr else None
                )
                
            except subprocess.TimeoutExpired:
                return MutationResult(
                    mutation_id=mutation_id,
                    mutation_type=mutation_type,
                    original_code=original_code,
                    mutated_code=mutated_code,
                    file_path=str(file_path),
                    line_number=line_num,
                    test_passed=False,
                    killed=True,
                    execution_time=300.0,
                    error_output="Test timeout"
                )
                
            except Exception as e:
                return MutationResult(
                    mutation_id=mutation_id,
                    mutation_type=mutation_type,
                    original_code=original_code,
                    mutated_code=mutated_code,
                    file_path=str(file_path),
                    line_number=line_num,
                    test_passed=False,
                    killed=True,
                    execution_time=time.time() - start_time,
                    error_output=str(e)
                )
                
            finally:
                # Restore original file
                original_path.write_text(backup_content)
                Path(temp_file.name).unlink(missing_ok=True)
    
    def run_mutation_tests(self, target_files: List[Path] = None) -> MutationReport:
        """Run mutation tests on target files."""
        if target_files is None:
            target_files = self.find_target_files()
            
        print(f"Starting mutation testing on {len(target_files)} files...")
        
        # Generate all mutations
        all_mutations = []
        for file_path in target_files:
            mutations = self.generate_mutations(file_path)
            for mutation in mutations:
                mutation_id, line_num, mutation_type, original_code, mutated_code = mutation
                all_mutations.append((
                    mutation_id, file_path, line_num, mutation_type, 
                    original_code, mutated_code
                ))
        
        print(f"Generated {len(all_mutations)} mutations")
        
        # Run tests in parallel
        start_time = time.time()
        test_results = []
        
        with ThreadPoolExecutor(max_workers=self.parallel_jobs) as executor:
            futures = {
                executor.submit(self._run_single_mutation_test, mutation): mutation 
                for mutation in all_mutations
            }
            
            for i, future in enumerate(as_completed(futures)):
                result = future.result()
                test_results.append(result)
                
                if (i + 1) % 100 == 0:
                    print(f"Completed {i + 1}/{len(all_mutations)} mutations")
        
        total_time = time.time() - start_time
        
        # Calculate statistics
        killed_mutations = sum(1 for r in test_results if r.killed)
        survived_mutations = len(test_results) - killed_mutations
        mutation_score = (killed_mutations / len(test_results)) * 100 if test_results else 0
        
        # Calculate coverage by file
        coverage_by_file = {}
        for file_path in target_files:
            file_results = [r for r in test_results if r.file_path == str(file_path)]
            if file_results:
                killed_count = sum(1 for r in file_results if r.killed)
                coverage_by_file[str(file_path)] = (killed_count / len(file_results)) * 100
        
        # Find mutation hotspots
        mutation_counts = {}
        for result in test_results:
            key = (result.file_path, result.line_number)
            mutation_counts[key] = mutation_counts.get(key, 0) + 1
            
        mutation_hotspots = sorted(
            [(file_path, line_num, count) for (file_path, line_num), count in mutation_counts.items()],
            key=lambda x: x[2], 
            reverse=True
        )[:20]  # Top 20 hotspots
        
        return MutationReport(
            total_mutations=len(test_results),
            killed_mutations=killed_mutations,
            survived_mutations=survived_mutations,
            mutation_score=mutation_score,
            test_results=test_results,
            execution_time=total_time,
            coverage_by_file=coverage_by_file,
            mutation_hotspots=mutation_hotspots
        )
        
    def generate_report(self, report: MutationReport, output_path: Path):
        """Generate comprehensive mutation testing report."""
        report_data = {
            'summary': {
                'total_mutations': report.total_mutations,
                'killed_mutations': report.killed_mutations,
                'survived_mutations': report.survived_mutations,
                'mutation_score': round(report.mutation_score, 2),
                'execution_time': round(report.execution_time, 2)
            },
            'coverage_by_file': {
                file_path: round(coverage, 2) 
                for file_path, coverage in report.coverage_by_file.items()
            },
            'mutation_hotspots': [
                {'file': file_path, 'line': line_num, 'mutation_count': count}
                for file_path, line_num, count in report.mutation_hotspots
            ],
            'survived_mutations': [
                {
                    'id': result.mutation_id,
                    'file': result.file_path,
                    'line': result.line_number,
                    'type': result.mutation_type.value,
                    'execution_time': round(result.execution_time, 2)
                }
                for result in report.test_results if not result.killed
            ]
        }
        
        with open(output_path, 'w') as f:
            json.dump(report_data, f, indent=2)
            
        print(f"\nMutation Testing Report")
        print(f"=" * 50)
        print(f"Total Mutations: {report.total_mutations}")
        print(f"Killed Mutations: {report.killed_mutations}")
        print(f"Survived Mutations: {report.survived_mutations}")
        print(f"Mutation Score: {report.mutation_score:.2f}%")
        print(f"Execution Time: {report.execution_time:.2f} seconds")
        print(f"\nReport saved to: {output_path}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Kernel Mutation Testing Framework")
    parser.add_argument("--source-dir", required=True, help="Source code directory")
    parser.add_argument("--test-command", required=True, help="Test command to execute")
    parser.add_argument("--output", default="mutation_report.json", help="Output report file")
    parser.add_argument("--jobs", type=int, help="Number of parallel jobs")
    
    args = parser.parse_args()
    
    tester = MutationTester(
        source_dir=args.source_dir,
        test_command=args.test_command,
        parallel_jobs=args.jobs
    )
    
    report = tester.run_mutation_tests()
    tester.generate_report(report, Path(args.output))