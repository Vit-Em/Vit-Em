#!/usr/bin/env python3
# tests/run_tests.py

import os
import sys
import pytest
import argparse
from datetime import datetime
from icecream import ic

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure icecream for logging
ic.configureOutput(prefix=f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] [TEST_RUNNER] ')
ic.enable()

def main():
    """Run all tests with detailed logging and reporting"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run tests for FDC Memory Bank")
    parser.add_argument("-v", "--verbose", action="store_true", help="Increase verbosity")
    parser.add_argument("-x", "--exitfirst", action="store_true", help="Exit on first failure")
    parser.add_argument("-s", "--showcapture", action="store_true", help="Show captured output")
    parser.add_argument("-m", "--module", type=str, help="Run tests only for this module (api, client, weaviate)")
    parser.add_argument("--html", action="store_true", help="Generate HTML report")
    parser.add_argument("--no-header", action="store_true", help="Hide header")
    args = parser.parse_args()
    
    # Build pytest arguments
    pytest_args = ["-v"] if args.verbose else []
    
    if args.exitfirst:
        pytest_args.append("-x")
    
    if args.showcapture:
        pytest_args.append("-s")
    
    if args.no_header:
        pytest_args.append("--no-header")
    
    # Module selection
    if args.module:
        if args.module.lower() == "api":
            pytest_args.append("test_memory_api.py")
        elif args.module.lower() == "client":
            pytest_args.append("test_memory_client.py")
        elif args.module.lower() == "weaviate":
            pytest_args.append("test_weaviate_client.py")
        else:
            print(f"Unknown module: {args.module}")
            return 1
    
    # HTML report
    if args.html:
        try:
            import pytest_html
            pytest_args.extend(["--html=test_report.html", "--self-contained-html"])
        except ImportError:
            print("Warning: pytest-html not installed. Skipping HTML report generation.")
            print("Install with: pip install pytest-html")
    
    # Log test start
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("fdc_test_log.txt", "a") as log_file:
        log_file.write(f"[{timestamp}] === Starting test run with args: {' '.join(pytest_args)} ===\n")
    
    print(f"Starting tests at {timestamp}")
    ic(f"Running tests with args: {pytest_args}")
    
    # Run the tests
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    return_code = pytest.main(pytest_args)
    
    # Log test completion
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("fdc_test_log.txt", "a") as log_file:
        log_file.write(f"[{timestamp}] === Test run completed with return code: {return_code} ===\n")
    
    print(f"Tests completed at {timestamp} with return code: {return_code}")
    
    return return_code

if __name__ == "__main__":
    sys.exit(main()) 