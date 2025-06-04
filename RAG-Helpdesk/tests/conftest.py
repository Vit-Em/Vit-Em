#!/usr/bin/env python3
# tests/conftest.py

import os
import sys
import pytest
import tempfile
import shutil
from datetime import datetime
from unittest.mock import MagicMock
from icecream import ic

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure icecream for test logging
ic.configureOutput(prefix=f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] [TEST] ')
ic.enable()

# Global test log file - combine logs from all test files
LOG_FILE = "fdc_test_log.txt"

def log_to_file(message, module="MAIN"):
    """Log a message to the global test log file with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as log_file:
        log_file.write(f"[{timestamp}] [{module}] {message}\n")

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment before all tests and clean up after"""
    # Initialize log file
    with open(LOG_FILE, "w") as log_file:
        log_file.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] === FDC Memory Bank Test Run Started ===\n")
    
    ic("Setting up test environment")
    log_to_file("Setting up test environment")
    
    # Create test directories if needed
    os.makedirs("tests/test_data", exist_ok=True)
    
    yield
    
    # Clean up after all tests
    ic("Cleaning up test environment")
    log_to_file("Cleaning up test environment")
    
    # Log test completion
    with open(LOG_FILE, "a") as log_file:
        log_file.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] === FDC Memory Bank Test Run Completed ===\n")

@pytest.fixture
def test_data_dir():
    """Create a temporary directory for test data"""
    temp_dir = tempfile.mkdtemp(prefix="fdc_test_")
    
    log_to_file(f"Created test data directory: {temp_dir}")
    
    yield temp_dir
    
    # Clean up
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
        log_to_file(f"Cleaned up test data directory: {temp_dir}")

@pytest.fixture
def mock_weaviate_client():
    """Create a mock Weaviate client for testing"""
    mock_client = MagicMock()
    mock_collection = MagicMock()
    
    mock_client.collections.get.return_value = mock_collection
    mock_client.get_meta.return_value = {"version": "1.30.4"}
    
    # Set up collections.exists to return False by default
    mock_client.collections.exists.return_value = False
    
    log_to_file("Created mock Weaviate client")
    
    return mock_client

@pytest.fixture
def create_test_markdown_files(test_data_dir):
    """Create test markdown files in the test data directory"""
    # Create several markdown files with different content
    files = []
    
    for i in range(3):
        file_path = os.path.join(test_data_dir, f"test_doc_{i}.md")
        with open(file_path, "w") as f:
            f.write(f"# Test Document {i}\n\n")
            f.write(f"This is test document {i} for the FDC Memory Bank.\n\n")
            f.write(f"## Section 1\n\n")
            f.write(f"Content for section 1 of document {i}.\n\n")
            f.write(f"## Section 2\n\n")
            f.write(f"Content for section 2 of document {i}.\n\n")
        
        files.append(file_path)
    
    log_to_file(f"Created {len(files)} test markdown files")
    
    return files

@pytest.fixture
def create_test_image(test_data_dir):
    """Create a test image file"""
    try:
        from PIL import Image
        
        # Create a test image
        img_path = os.path.join(test_data_dir, "test_image.jpg")
        img = Image.new('RGB', (100, 100), color='blue')
        img.save(img_path)
        
        log_to_file(f"Created test image: {img_path}")
        
        return img_path
    except ImportError:
        log_to_file("PIL not available, skipping image creation", "WARNING")
        return None

@pytest.fixture
def create_test_binary(test_data_dir):
    """Create a test binary file"""
    bin_path = os.path.join(test_data_dir, "test_binary.bin")
    
    with open(bin_path, 'wb') as f:
        f.write(os.urandom(1024))  # 1KB of random data
    
    log_to_file(f"Created test binary file: {bin_path}")
    
    return bin_path

@pytest.fixture
def mock_http_response():
    """Create a mock HTTP response for requests"""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"status": "success"}
    
    log_to_file("Created mock HTTP response")
    
    return mock_resp

@pytest.fixture
def mock_error_response():
    """Create a mock error HTTP response"""
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = '{"error": "Bad request"}'
    
    log_to_file("Created mock error HTTP response")
    
    return mock_resp 