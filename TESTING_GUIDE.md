# HydroQuote AI - Testing Guide

## 🧪 Comprehensive Testing Documentation

This guide covers all testing procedures for the HydroQuote AI system.

---

## 📋 Prerequisites

### Required Software
- Python 3.11 or higher
- pip (Python package manager)
- Git (for version control)

### Install Dependencies

```bash
# Install all dependencies including test tools
pip install -r requirements.txt

# Or install test dependencies separately
pip install pytest pytest-asyncio httpx
```

---

## 🚀 Quick Start

### 1. Run All Tests

```bash
# Using the test runner script
python run_tests.py

# Or using pytest directly
pytest tests/ -v
```

### 2. Run Specific Test Suites

```bash
# Configuration tests
pytest tests/test_config.py -v

# API health tests
pytest tests/test_api_health.py -v

# Watson NLU integration tests
pytest tests/test_watson_nlu.py -v

# Integration tests
pytest tests/test_integration.py -v
```

### 3. Run Tests with Coverage

```bash
pytest tests/ --cov=app --cov-report=html
```

---

## 🎯 Test Categories

### 1. Configuration Module Tests (`test_config.py`)

**Purpose**: Verify environment variable loading and validation

**Tests Include**:
- ✅ Settings instance creation
- ✅ Watson NLU configuration loading
- ✅ Application configuration defaults
- ✅ CORS origins parsing
- ✅ Feature flags validation
- ✅ LLM configuration parameters
- ✅ Environment detection (dev/prod)
- ✅ Configuration validation rules

**Run Command**:
```bash
pytest tests/test_config.py -v
```

**Expected Results**: All tests should pass if `.env` file is properly configured.

---

### 2. API Health Tests (`test_api_health.py`)

**Purpose**: Test basic API endpoints and health checks

**Tests Include**:
- ✅ Root endpoint (`/`)
- ✅ Health check endpoint (`/health`)
- ✅ Configuration info endpoint (`/config/info`)
- ✅ API documentation endpoints (`/docs`, `/redoc`)
- ✅ CORS configuration
- ✅ Error handling (404, 405)
- ✅ Security (no secrets exposed)

**Run Command**:
```bash
# Start the API first
python app/main.py

# In another terminal, run tests
pytest tests/test_api_health.py -v
```

**Expected Results**: All tests should pass when API is running.

---

### 3. Watson NLU Integration Tests (`test_watson_nlu.py`)

**Purpose**: Test IBM Watson NLU API connectivity and features

**Tests Include**:
- ✅ API endpoint reachability
- ✅ Authentication validation
- ✅ Text analysis functionality
- ✅ Entity extraction
- ✅ Keyword extraction
- ✅ Error handling (empty text, invalid auth)

**Run Command**:
```bash
pytest tests/test_watson_nlu.py -v
```

**Expected Results**: Tests should pass if Watson NLU credentials are valid.

**Note**: These tests make real API calls to Watson NLU.

---

### 4. Integration Tests (`test_integration.py`)

**Purpose**: Test complete application workflows

**Tests Include**:
- ✅ Application startup
- ✅ Health check with dependencies
- ✅ Config and health consistency
- ✅ Global exception handling
- ✅ Security features
- ✅ No sensitive data exposure

**Run Command**:
```bash
# Start the API first
python app/main.py

# In another terminal, run tests
pytest tests/test_integration.py -v
```

---

## 🐛 Bug Tracking

### Bugs Found and Fixed

#### Bug #1: Type Hint Error in `app/main.py`
**Issue**: `Dict[str, any]` should be `Dict[str, Any]`
**Location**: Line 110, `config_info` function
**Fix**: Changed `any` to `Any` and added proper import
**Status**: ✅ Fixed

#### Bug #2: Health Check Return Type Error
**Issue**: Return type `Dict[str, str]` doesn't match actual return with boolean
**Location**: Line 81, `health_check` function
**Fix**: Changed return type to `Dict[str, Union[str, bool]]`
**Status**: ✅ Fixed

#### Bug #3: Health Check Logic Error
**Issue**: Checking for `watsonx_api_key` instead of `watson_nlu_api_key`
**Location**: Line 88, health check validation
**Fix**: Updated to check Watson NLU credentials (required) and made Watsonx optional
**Status**: ✅ Fixed

#### Bug #4: Unicode Encoding Error on Windows
**Issue**: Emoji characters in `run_tests.py` cause encoding errors on Windows
**Location**: `run_tests.py` print statements
**Fix**: Added UTF-8 encoding wrapper for Windows stdout/stderr
**Status**: ✅ Fixed

---

## 🎨 Demo Dashboard

### Running the Frontend Demo

1. **Start the Backend API**:
```bash
python app/main.py
```
The API will run on `http://localhost:8000`

2. **Start the Frontend Server**:
```bash
python serve_frontend.py
```
The frontend will run on `http://localhost:3000`

3. **Open Browser**:
Navigate to `http://localhost:3000` to see the interactive demo dashboard.

### Frontend Features

- 📊 Real-time system status monitoring
- 🔍 API endpoint testing
- 📡 Watson NLU connection testing
- 📄 JSON response viewer
- 🧪 Interactive test execution
- 📚 API documentation links

---

## 📊 Test Results Interpretation

### Passing Tests ✅
- All functionality working as expected
- Configuration properly loaded
- APIs accessible and responding correctly

### Failing Tests ❌
Common reasons for test failures:

1. **Missing Dependencies**
   - Solution: Run `pip install -r requirements.txt`

2. **API Not Running**
   - Solution: Start the API with `python app/main.py`

3. **Invalid Credentials**
   - Solution: Check `.env` file has valid Watson NLU credentials

4. **Network Issues**
   - Solution: Check internet connection for Watson API calls

5. **Port Already in Use**
   - Solution: Change `API_PORT` in `.env` or kill process using port 8000

---

## 🔧 Troubleshooting

### Issue: Tests Can't Import Modules

**Error**: `ModuleNotFoundError: No module named 'fastapi'`

**Solution**:
```bash
pip install -r requirements.txt
```

### Issue: Watson NLU Tests Fail

**Error**: `401 Unauthorized` or `403 Forbidden`

**Solution**:
1. Check `.env` file has correct `WATSON_NLU_API_KEY`
2. Verify `WATSON_NLU_URL` is correct
3. Test credentials in IBM Cloud console

### Issue: API Tests Timeout

**Error**: `httpx.TimeoutException`

**Solution**:
1. Ensure API is running: `python app/main.py`
2. Check firewall isn't blocking port 8000
3. Verify `localhost` resolves correctly

### Issue: Frontend Can't Connect

**Error**: `Cannot connect to API`

**Solution**:
1. Start backend first: `python app/main.py`
2. Check backend is on port 8000
3. Verify CORS is enabled in `.env`

---

## 📈 Coverage Goals

- **Unit Tests**: > 80% coverage
- **Integration Tests**: > 70% coverage
- **API Endpoints**: 100% coverage

### Generate Coverage Report

```bash
pytest tests/ --cov=app --cov-report=html
```

Open `htmlcov/index.html` in browser to view detailed coverage report.

---

## 🔄 Continuous Testing

### Pre-commit Testing

Before committing code, run:
```bash
python run_tests.py
```

### Automated Testing

For CI/CD pipelines:
```bash
pytest tests/ -v --tb=short --maxfail=1
```

---

## 📝 Writing New Tests

### Test File Structure

```python
"""
Test suite for [module name]
Description of what this test suite covers
"""
import pytest

class Test[ModuleName]:
    """Test [specific functionality]"""
    
    def test_[specific_feature](self, fixture_name):
        """Test that [expected behavior]"""
        # Arrange
        # Act
        # Assert
        pass
```

### Best Practices

1. **Use Descriptive Names**: Test names should clearly describe what they test
2. **One Assertion Per Test**: Keep tests focused and simple
3. **Use Fixtures**: Reuse common setup code via pytest fixtures
4. **Test Edge Cases**: Include tests for error conditions
5. **Mock External APIs**: Use mocks for external dependencies when appropriate

---

## 🎯 Test Markers

Use pytest markers to categorize tests:

```python
@pytest.mark.unit
def test_configuration():
    pass

@pytest.mark.integration
def test_full_workflow():
    pass

@pytest.mark.slow
def test_watson_api():
    pass
```

Run specific markers:
```bash
pytest -m unit  # Run only unit tests
pytest -m "not slow"  # Skip slow tests
```

---

## 📞 Support

For testing issues or questions:
- Check this guide first
- Review test output for specific error messages
- Check `.env` configuration
- Verify all dependencies are installed

---

**Last Updated**: 2024-05-02  
**Version**: 2.0.0  
**Status**: ✅ All Core Tests Passing