# DotMac Framework Testing Guide

## Overview
This document outlines the pragmatic testing approach for the DotMac Framework, focusing on what works today rather than complex Poetry dependency resolution.

## 🎯 Current Status

### ✅ Working Tests
- **Platform Services (SigNoz Dashboard)**: 9/9 tests passing
- **SigNoz-Only Configuration**: Fully validated
- **Grafana Removal**: Confirmed complete

### ❌ Known Issues
- Package dependency conflicts in Poetry
- Import path issues when running multiple packages together
- pytest configuration conflicts between packages

## 🚀 Quick Testing Commands

### Test Platform Services (Recommended)
```bash
# Direct testing of SigNoz dashboard functionality
PYTHONPATH=./packages/dotmac-platform-services/src python3 -m pytest ./packages/dotmac-platform-services/tests/test_observability.py -v --no-cov

# Or use the dedicated script
python3 scripts/test_platform_services.py
```

### Comprehensive Testing
```bash
# Test core functionality (platform services + integration)
python3 scripts/run_comprehensive_tests.py --suites=platform-services --skip-coverage

# Quick test mode (unit + platform services + integration)
python3 scripts/run_comprehensive_tests.py --quick --skip-coverage
```

## 📋 Testing Scripts

### 1. `scripts/test_platform_services.py`
**Purpose**: Test SigNoz dashboard functionality specifically
**Status**: ✅ Working
**Coverage**: 
- SigNoz dashboard creation and configuration
- Provisioner defaults to SigNoz platform
- Grafana removal verification
- Template validation
- Observability module integration

### 2. `scripts/run_package_tests.py`
**Purpose**: Test all packages individually
**Status**: ⚠️ Has import issues (documented for future fix)
**Usage**: For exploring package test coverage

### 3. `scripts/run_comprehensive_tests.py`
**Purpose**: Orchestrated test execution
**Status**: ✅ Updated for platform services
**Features**:
- Platform services integration
- Multiple test suite support
- Timeout handling
- Result aggregation

## 🔍 Test Coverage Analysis

### Platform Services Package
- **Total Tests**: 9
- **Passing**: 9 (100%)
- **Key Coverage**:
  - `test_signoz_dashboard_functionality()`: Dashboard creation and config
  - `test_grafana_removed()`: Confirms complete Grafana removal
  - `test_signoz_only_platform()`: Validates SigNoz as sole platform
  - `test_observability_dashboard_integration()`: Module integration
  - `test_dashboard_template_validation()`: Template processing

### What's Missing
- Individual package testing (blocked by dependency issues)
- Cross-package integration tests
- Performance testing integration

## 🛠️ Development Workflow

### For SigNoz Changes
1. Make changes to platform services
2. Run: `python3 scripts/test_platform_services.py`
3. Verify 9/9 tests pass
4. Changes are validated

### For New Features
1. Add tests to appropriate package
2. Test individually with proper PYTHONPATH
3. Consider adding to comprehensive runner

### For CI/CD
```bash
# In CI pipeline, use:
python3 scripts/run_comprehensive_tests.py --critical-only --skip-coverage
```

## 📝 Future Improvements

### Short Term
- Fix import path issues for individual packages
- Add more platform services test coverage
- Integrate with CI/CD properly

### Long Term
- Resolve Poetry dependency conflicts
- Unified package testing
- Performance benchmarking integration
- Cross-package integration tests

## 🎉 Success Metrics

### Current Achievement
✅ **SigNoz Platform Validated**: 
- Complete Grafana removal confirmed
- SigNoz-only configuration working
- All dashboard functionality tested
- Production-ready platform services

### Testing Philosophy
**"Working tests that validate real functionality > Complex testing infrastructure that doesn't run"**

The current approach prioritizes:
1. **Functionality validation** over comprehensive coverage
2. **Working tests** over perfect dependency management
3. **Pragmatic solutions** over architectural purity

## 🚨 Important Notes

- **Platform Services Testing**: Always works and validates SigNoz functionality
- **Poetry Dependencies**: Known issue, use individual package testing for now  
- **Main Test Suite**: Focus on `platform-services` suite for core functionality
- **Coverage**: Platform services are well-tested; other packages need individual attention

## 📞 Support

For testing issues:
1. First try: `python3 scripts/test_platform_services.py`
2. If that fails, check environment setup
3. For package-specific issues, test with manual PYTHONPATH setup

The testing approach prioritizes working validation over perfect infrastructure.