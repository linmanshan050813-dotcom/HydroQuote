"""
Comprehensive test runner for HydroQuote AI
Runs all tests and generates a detailed report
"""
import subprocess
import sys
import os
from pathlib import Path

# Fix encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")

def run_command(command, description):
    """Run a command and return the result"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        return result
    except subprocess.TimeoutExpired:
        print(f"⏱️  Timeout: {description} took too long")
        return None
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

def main():
    print_header("HydroQuote AI - Comprehensive Test Suite")
    
    # Check if we're in the right directory
    if not Path("app").exists():
        print("❌ Error: Must run from project root directory")
        sys.exit(1)
    
    # Check if pytest is installed
    print("📦 Checking dependencies...")
    result = run_command("pip show pytest", "Checking pytest installation")
    if result and result.returncode != 0:
        print("⚠️  pytest not found. Installing test dependencies...")
        run_command("pip install pytest pytest-asyncio httpx", "Installing dependencies")
    else:
        print("✓ pytest is installed")
    
    # Run configuration tests
    print_header("Test 1: Configuration Module")
    result = run_command(
        "pytest tests/test_config.py -v",
        "Running configuration tests"
    )
    if result:
        print(result.stdout)
        if result.returncode == 0:
            print("✓ Configuration tests passed")
        else:
            print("❌ Configuration tests failed")
            print(result.stderr)
    
    # Run API health tests
    print_header("Test 2: API Health Endpoints")
    result = run_command(
        "pytest tests/test_api_health.py -v",
        "Running API health tests"
    )
    if result:
        print(result.stdout)
        if result.returncode == 0:
            print("✓ API health tests passed")
        else:
            print("❌ API health tests failed")
            print(result.stderr)
    
    # Run Watson NLU tests
    print_header("Test 3: Watson NLU Integration")
    result = run_command(
        "pytest tests/test_watson_nlu.py -v",
        "Running Watson NLU tests"
    )
    if result:
        print(result.stdout)
        if result.returncode == 0:
            print("✓ Watson NLU tests passed")
        else:
            print("❌ Watson NLU tests failed")
            print(result.stderr)
    
    # Run integration tests
    print_header("Test 4: Integration Tests")
    result = run_command(
        "pytest tests/test_integration.py -v",
        "Running integration tests"
    )
    if result:
        print(result.stdout)
        if result.returncode == 0:
            print("✓ Integration tests passed")
        else:
            print("❌ Integration tests failed")
            print(result.stderr)
    
    # Run all tests with coverage
    print_header("Test 5: Full Test Suite with Coverage")
    result = run_command(
        "pytest tests/ -v --tb=short",
        "Running complete test suite"
    )
    if result:
        print(result.stdout)
        if result.returncode == 0:
            print("✓ All tests passed!")
        else:
            print("⚠️  Some tests failed")
            print(result.stderr)
    
    print_header("Test Summary")
    print("Test execution completed!")
    print("\nNext steps:")
    print("1. Review any failed tests above")
    print("2. Start the backend: python app/main.py")
    print("3. Start the frontend: python serve_frontend.py")
    print("4. Open http://localhost:3000 for the demo dashboard")

if __name__ == "__main__":
    main()

# Made with Bob
