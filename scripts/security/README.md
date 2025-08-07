# Security Testing Scripts and Configuration

This directory contains security testing tools, configurations, and utilities for the MPU-6050 kernel driver project.

## Files Overview

### Security Scanning Scripts
- `security_scan.sh` - Main security scanning orchestration script
- `dependency_scan.py` - Dependency vulnerability scanner
- `fuzzing_harness.c` - Fuzzing test harness for input validation
- `memory_test_utils.c` - Memory safety testing utilities

### Configuration Files
- `cppcheck_security_rules.xml` - Cppcheck security analysis rules
- `flawfinder.conf` - Flawfinder security scanner configuration
- `bandit.yaml` - Bandit Python security scanner configuration
- `sparse_config.txt` - Sparse semantic analyzer configuration

### Test Data
- `fuzz_inputs/` - Fuzzing test input patterns
- `test_vectors/` - Security test vectors and payloads
- `vulnerability_db/` - Local vulnerability database cache

## Usage

### Quick Security Scan
```bash
# Run all security tests
../security_scan.sh --all

# Run specific test category
../security_scan.sh --sast --sca
```

### Dependency Scanning
```bash
# Scan Python dependencies
../dependency_scan.py --python-only --output-format json

# Full dependency scan
../dependency_scan.py --output-format sarif
```

### Configuration Updates

When updating security tool configurations:

1. Test configuration locally
2. Update version in CI/CD pipeline
3. Document changes in commit message
4. Verify CI/CD integration

## Integration with CI/CD

These tools are automatically executed in the GitHub Actions security pipeline:

- **SAST**: Static application security testing
- **SCA**: Software composition analysis  
- **DAST**: Dynamic application security testing
- **Fuzzing**: Input validation and boundary testing

## Maintenance

Security configurations should be reviewed and updated:
- Monthly for tool updates
- After security advisories
- Before major releases
- When adding new dependencies

## Contact

For security tool issues: Murray Kopit <murr2k@gmail.com>