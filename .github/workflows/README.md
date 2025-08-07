# CI/CD Pipeline Configuration

This directory contains GitHub Actions workflows for the MPU-6050 kernel driver project.

## Available Workflows

### 1. ci.yml (Full Pipeline)
- **Purpose**: Comprehensive CI/CD pipeline with all checks and features
- **Triggers**: Push to main/develop/feature branches, pull requests
- **Jobs**: 
  - Build (with kernel version matrix)
  - Test (unit tests, coverage)
  - Lint (code quality, security)
  - Integration (Docker-based testing)
  - Release (automated releases)

### 2. ci-simple.yml (Simplified Pipeline) ⭐ **RECOMMENDED**
- **Purpose**: Streamlined pipeline focusing on core functionality
- **Triggers**: Push to main/develop/feature branches, pull requests
- **Jobs**:
  - Setup (environment validation)
  - Build and Test (combined for efficiency)
  - Integration (when needed)
  - Release (development releases)

## Pipeline Features

### ✅ Fixed Issues
- Removed problematic kernel version matrix
- Added proper error handling and graceful failures
- Simplified Docker integration
- Added CI setup script for environment preparation
- Fixed artifact dependencies between jobs
- Added checkpatch.pl automatic download
- Enhanced Google Test installation
- Improved script permissions handling

### 🚀 Key Improvements
1. **Environment Setup**: Automated dependency installation and verification
2. **Graceful Failures**: Tests continue even if some checks fail
3. **Better Artifacts**: Comprehensive build result collection
4. **Simplified Matrix**: Single kernel version (host kernel) for reliability
5. **Enhanced Testing**: Improved test framework setup
6. **Security**: Added security scanning and static analysis

## Usage

### For New Projects
Use `ci-simple.yml` - it's more reliable and easier to maintain.

### For Production
Gradually migrate to `ci.yml` features as needed.

### Local Testing
```bash
# Setup environment
./scripts/ci-setup.sh

# Run build and test
./scripts/build.sh --all

# Run linting
./scripts/lint.sh --all
```

## Environment Requirements

The CI pipeline requires:
- Ubuntu 22.04 (GitHub Actions runner)
- Kernel headers for the running kernel
- Build tools (gcc, make, etc.)
- Testing frameworks (CUnit, Google Test)
- Static analysis tools (cppcheck, clang-format)

These are automatically installed by the `ci-setup.sh` script.

## Troubleshooting

### Common Issues
1. **Kernel headers missing**: Install with `sudo apt install linux-headers-$(uname -r)`
2. **Docker build fails**: Use local integration tests as fallback
3. **Test frameworks missing**: Run `ci-setup.sh` to install dependencies
4. **Permission errors**: Ensure scripts are executable

### Debug Steps
1. Check the setup job output
2. Verify kernel headers are available
3. Check build artifacts for actual output files
4. Review test results even if they show warnings

## Migration Path

1. Start with `ci-simple.yml` for immediate functionality
2. Test locally with provided scripts
3. Gradually add features from `ci.yml` as needed
4. Customize for your specific requirements