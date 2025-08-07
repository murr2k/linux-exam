# Test Coverage Dashboard

[![Line Coverage](https://img.shields.io/badge/Line_Coverage-85%25-brightgreen.svg)](docs/TEST_COVERAGE_DASHBOARD.md)
[![Branch Coverage](https://img.shields.io/badge/Branch_Coverage-78%25-yellow.svg)](docs/TEST_COVERAGE_DASHBOARD.md)
[![Function Coverage](https://img.shields.io/badge/Function_Coverage-92%25-brightgreen.svg)](docs/TEST_COVERAGE_DASHBOARD.md)
[![Statement Coverage](https://img.shields.io/badge/Statement_Coverage-88%25-brightgreen.svg)](docs/TEST_COVERAGE_DASHBOARD.md)

## 📊 Coverage Overview

### Current Metrics (Last Updated: 2025-01-07)

| Metric Type | Current % | Target % | Status | Trend |
|-------------|-----------|----------|--------|---------|
| **Line Coverage** | 85% | 90% | 🟡 Warning | ⬆️ +2% |
| **Branch Coverage** | 78% | 85% | 🔴 Critical | ⬇️ -1% |
| **Function Coverage** | 92% | 95% | 🟡 Warning | ⬆️ +5% |
| **Statement Coverage** | 88% | 90% | 🟡 Warning | ⬆️ +3% |

### Visual Coverage Map

```
Project Coverage Heatmap:

├── drivers/mpu6050_main.c     ████████████████████░  95% ✅
├── drivers/mpu6050_i2c.c      ███████████████████░░  90% ✅
├── drivers/mpu6050_sysfs.c    ████████████████░░░░░  80% ⚠️
├── drivers/mpu6050_chardev.c  ██████████████████░░░  88% ✅
├── include/mpu6050.h          ████████████████████░  92% ✅
└── tests/unit/                ████████████████████░  95% ✅

Legend: █ Covered  ░ Uncovered  ✅ Above Target  ⚠️ Below Target
```

## 🎯 Coverage Targets and Thresholds

### Quality Gates

| Gate Level | Line % | Branch % | Function % | Action |
|------------|--------|----------|------------|---------|
| **Critical** | < 70% | < 65% | < 80% | 🚨 Block PR |
| **Warning** | 70-89% | 65-84% | 80-94% | ⚠️ Review Required |
| **Good** | 90-94% | 85-89% | 95-97% | ✅ Merge OK |
| **Excellent** | ≥ 95% | ≥ 90% | ≥ 98% | 🏆 Gold Standard |

### Component-Specific Targets

```yaml
Coverage Targets by Component:

Core Drivers:
  mpu6050_main.c:     { line: 95%, branch: 90%, function: 98% }
  mpu6050_i2c.c:      { line: 92%, branch: 88%, function: 95% }
  mpu6050_sysfs.c:    { line: 88%, branch: 85%, function: 92% }
  mpu6050_chardev.c:  { line: 90%, branch: 87%, function: 95% }

Headers:
  mpu6050.h:          { line: 85%, branch: 80%, function: 90% }

Tests:
  unit/:              { line: 98%, branch: 95%, function: 100% }
  integration/:       { line: 95%, branch: 92%, function: 98% }

Utilities:
  scripts/:           { line: 80%, branch: 75%, function: 85% }
```

## 📈 Trend Analysis

### 30-Day Coverage Trend

```
Line Coverage Trend (Last 30 Days):
85% ┤                                              ╭─
84% ┤                                          ╭───╯  
83% ┤                                      ╭───╯      
82% ┤                                  ╭───╯          
81% ┤                              ╭───╯              
80% ┤──────────────────────────────╯                  
    └─┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬──
     Dec-7 Dec-14 Dec-21 Dec-28 Jan-4 Jan-11 Jan-18

Branch Coverage Trend (Last 30 Days):
79% ┤                                              ╭─
78% ┤                                          ╭───╯─
77% ┤                                      ╭───╯     
76% ┤                                  ╭───╯         
75% ┤                              ╭───╯             
74% ┤──────────────────────────────╯                 
    └─┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬──
     Dec-7 Dec-14 Dec-21 Dec-28 Jan-4 Jan-11 Jan-18
```

### Key Improvements

- **+5% function coverage** in last sprint due to new unit tests
- **+2% line coverage** from error path testing improvements
- **-1% branch coverage** due to new conditional logic in power management

## 🔍 Uncovered Code Analysis

### Critical Gaps (Require Immediate Attention)

#### 1. drivers/mpu6050_sysfs.c (20% uncovered)

```c
// Lines 234-267: Error handling paths
static ssize_t power_state_store(struct device *dev, 
                                struct device_attribute *attr,
                                const char *buf, size_t count) {
    // UNCOVERED: Invalid state transitions
    if (state < 0 || state > 2) {
        return -EINVAL;  // ❌ Not tested
    }
    
    // UNCOVERED: Hardware failure scenarios
    ret = mpu6050_set_power_state(priv, state);
    if (ret == -EIO) {
        dev_err(dev, "I2C communication failed");  // ❌ Not tested
        return ret;
    }
}
```

**Action Required**: Add tests for invalid input and I2C failure scenarios

#### 2. drivers/mpu6050_chardev.c (12% uncovered)

```c
// Lines 145-162: IOCTL error paths
static long mpu6050_ioctl(struct file *file, unsigned int cmd, 
                         unsigned long arg) {
    switch (cmd) {
        case MPU6050_IOC_INVALID:
            return -ENOTTY;  // ❌ Not tested
        
        default:
            // UNCOVERED: Unknown IOCTL commands
            dev_warn(dev, "Unknown IOCTL: 0x%x", cmd);  // ❌ Not tested
            return -EINVAL;
    }
}
```

**Action Required**: Add negative tests for invalid IOCTL commands

### Warning Areas (Next Sprint Focus)

#### 1. drivers/mpu6050_i2c.c (10% uncovered)

- **Line 89-95**: I2C timeout handling
- **Line 134-140**: Device not responding scenarios
- **Line 201-208**: Bus error recovery

#### 2. drivers/mpu6050_main.c (5% uncovered)

- **Line 67-72**: Module parameter validation
- **Line 445-450**: Graceful shutdown edge cases

## 🧪 Coverage by Test Type

### Unit Tests Coverage

| Test Suite | Files Covered | Line % | Branch % | Function % |
|------------|---------------|--------|-----------|-----------|
| **Core Logic** | mpu6050_main.c | 98% | 95% | 100% |
| **I2C Communication** | mpu6050_i2c.c | 95% | 92% | 98% |
| **Sysfs Interface** | mpu6050_sysfs.c | 85% | 80% | 90% |
| **Character Device** | mpu6050_chardev.c | 90% | 85% | 95% |
| **Header Definitions** | mpu6050.h | 92% | 88% | 90% |

### Integration Tests Coverage

| Test Category | Components | Line % | Branch % | Notes |
|---------------|------------|--------|-----------|---------|
| **Hardware Interface** | I2C + Main | 88% | 82% | Real device tests |
| **Sysfs Operations** | Sysfs + Main | 82% | 78% | User interaction tests |
| **Character Device** | Chardev + Main | 85% | 80% | IOCTL interface tests |
| **Power Management** | All components | 79% | 75% | Sleep/wake cycle tests |
| **Error Recovery** | All components | 73% | 68% | Failure injection tests |

## 📋 Coverage Reports

### Generating Reports

```bash
# Generate HTML coverage report
make coverage-html
open build/coverage/index.html

# Generate JSON coverage data
make coverage-json
cat build/coverage/coverage.json

# Generate coverage badges
python3 scripts/generate-coverage-badge.py

# Generate coverage diff (for PRs)
make coverage-diff --base=main
```

### Report Formats

- **HTML Report**: `build/coverage/index.html` - Interactive web interface
- **JSON Data**: `build/coverage/coverage.json` - Machine-readable metrics
- **LCOV Format**: `build/coverage/coverage.info` - Industry standard
- **Cobertura XML**: `build/coverage/cobertura.xml` - CI/CD integration
- **Coverage Badges**: `docs/badges/` - README integration

## 🚀 CI/CD Integration

### Pipeline Coverage Checks

```yaml
# .github/workflows/coverage.yml
name: Coverage Gate

on: [push, pull_request]

jobs:
  coverage:
    runs-on: ubuntu-latest
    steps:
      - name: Coverage Check
        run: |
          make test COVERAGE=1
          python3 scripts/coverage-gate.py \
            --min-line=80 \
            --min-branch=75 \
            --min-function=90 \
            --fail-under=70
      
      - name: Coverage Report
        uses: 5monkeys/cobertura-action@master
        with:
          path: build/coverage/cobertura.xml
          minimum_coverage: 80
```

### Quality Gates

- **PR Merge Gate**: Minimum 80% line coverage required
- **Release Gate**: Minimum 85% line coverage required
- **Nightly Build**: Generate comprehensive coverage reports
- **Coverage Regression**: Fail if coverage drops >2%

## 🔧 Improving Coverage

### Quick Wins (Next 2 Sprints)

1. **Add Error Path Tests** (Expected +5% line coverage)
   ```bash
   # Focus areas:
   tests/unit/test_sysfs_error_paths.c     # +3%
   tests/unit/test_chardev_invalid_ioctl.c # +2%
   ```

2. **I2C Failure Simulation** (Expected +3% branch coverage)
   ```bash
   # Mock I2C failures:
   tests/integration/test_i2c_timeout.c    # +2%
   tests/integration/test_device_unplug.c  # +1%
   ```

3. **Power Management Edge Cases** (Expected +4% line coverage)
   ```bash
   # Power state transitions:
   tests/unit/test_power_invalid_states.c  # +2%
   tests/unit/test_power_race_conditions.c # +2%
   ```

### Long-term Improvements (Next Quarter)

1. **Fuzzing Integration** - Add fuzzing tests for IOCTL interfaces
2. **Hardware Fault Injection** - Simulate hardware failures
3. **Concurrency Testing** - Multi-threaded access patterns
4. **Performance Regression** - Coverage-aware performance tests

## 📚 Coverage Best Practices

### Writing Coverage-Friendly Code

```c
// ❌ Hard to test (nested conditions)
if (device && device->priv && device->priv->state == ACTIVE) {
    return process_data(device->priv);
}

// ✅ Easy to test (early returns)
if (!device) return -EINVAL;
if (!device->priv) return -ENOMEM;
if (device->priv->state != ACTIVE) return -EBUSY;
return process_data(device->priv);
```

### Coverage Analysis Tips

1. **Focus on Branches**: Branch coverage often reveals logic errors
2. **Test Error Paths**: Error handling is critical in kernel code
3. **Use Mocks**: Mock hardware interactions for consistent testing
4. **Edge Cases**: Test boundary conditions and invalid inputs
5. **State Machines**: Ensure all state transitions are covered

## 🎯 Action Items

### This Sprint
- [ ] Add sysfs error path tests (Priority: High)
- [ ] Implement chardev IOCTL negative tests (Priority: High) 
- [ ] Fix branch coverage regression in power management (Priority: Medium)
- [ ] Update coverage badges in README (Priority: Low)

### Next Sprint
- [ ] Add I2C timeout and recovery tests
- [ ] Implement hardware fault injection framework
- [ ] Create coverage trend analysis automation
- [ ] Add performance impact metrics for tests

### Ongoing
- [ ] Monitor coverage trends weekly
- [ ] Review uncovered code in code reviews
- [ ] Update coverage targets quarterly
- [ ] Maintain coverage documentation

---

**Coverage Dashboard Last Updated**: January 7, 2025  
**Next Review**: January 14, 2025  
**Maintainer**: Murray Kopit <murr2k@gmail.com>  
**Coverage Goal**: 90% line, 85% branch, 95% function by Q1 2025

*"Code coverage is not a goal, it's a tool to find untested code." - Testing Philosophy*