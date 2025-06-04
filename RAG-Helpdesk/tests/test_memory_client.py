#!/usr/bin/env python3
# tests/test_memory_client.py

import os
import sys
import pytest
import json
import tempfile
from datetime import datetime
from unittest.mock import patch, MagicMock
from icecream import ic

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cursor_memory_client as client

# Configure icecream for logging
ic.configureOutput(prefix=f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] [TEST_CLIENT] ')
ic.enable()

# Test log file
LOG_FILE = "test_client_log.txt"

def log_to_file(message):
    """Log a message to the test log file with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as log_file:
        log_file.write(f"[{timestamp}] {message}\n")

@pytest.fixture
def mock_response():
    """Create a mock response object for requests"""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"status": "success"}
    return mock_resp

@pytest.fixture
def mock_error_response():
    """Create a mock error response for requests"""
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = '{"error": "Bad request"}'
    return mock_resp

@pytest.fixture
def temp_image():
    """Create a temporary image file for testing"""
    from PIL import Image
    
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    
    # Create a simple image
    img_path = os.path.join(temp_dir, "test_image.jpg")
    img = Image.new('RGB', (100, 100), color='red')
    img.save(img_path)
    
    yield img_path
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)

@pytest.fixture
def temp_binary_file():
    """Create a temporary binary file for testing"""
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    
    # Create a simple binary file
    bin_path = os.path.join(temp_dir, "test_binary.bin")
    with open(bin_path, 'wb') as f:
        f.write(os.urandom(1024))  # 1KB random data
    
    yield bin_path
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)

def test_check_api_connection(mock_response):
    """Test checking API connection"""
    log_to_file("Starting check_api_connection test")
    
    # Set up mock for successful connection
    mock_response.json.return_value = {"status": "healthy", "weaviate_version": "1.30.4", "api_version": "1.0.0"}
    
    with patch('requests.get', return_value=mock_response):
        result = client.check_api_connection()
        
        ic(f"API connection check result: {result}")
        log_to_file(f"check_api_connection test result: {result}")
        
        assert result is True

def test_check_api_connection_failure(mock_error_response):
    """Test checking API connection when it fails"""
    log_to_file("Starting check_api_connection_failure test")
    
    with patch('requests.get', return_value=mock_error_response):
        result = client.check_api_connection()
        
        ic(f"API connection failure check result: {result}")
        log_to_file(f"check_api_connection_failure test result: {result}")
        
        assert result is False
    
    # Test connection error
    with patch('requests.get', side_effect=Exception("Connection error")):
        result = client.check_api_connection()
        
        ic(f"API connection error check result: {result}")
        log_to_file(f"check_api_connection_error test result: {result}")
        
        assert result is False

def test_query_memory_bank(mock_response):
    """Test querying the Memory Bank"""
    log_to_file("Starting query_memory_bank test")
    
    # Set up mock response
    mock_response.json.return_value = {
        "query": "test query",
        "results_count": 2,
        "results": [
            {
                "id": "uuid1",
                "filename": "test1.md",
                "content": "Test content 1",
                "content_type": "text"
            },
            {
                "id": "uuid2",
                "filename": "test2.jpg",
                "content": "Image: test2.jpg",
                "content_type": "image",
                "image_format": "jpg"
            }
        ]
    }
    
    with patch('requests.post', return_value=mock_response):
        result = client.query_memory_bank("test query", limit=3, content_type="all")
        
        ic(f"Query result: {result['results_count']} results")
        log_to_file(f"query_memory_bank test result: {result['results_count']} results")
        
        assert result is not None
        assert result['query'] == "test query"
        assert result['results_count'] == 2
        assert len(result['results']) == 2
        assert result['results'][0]['content_type'] == "text"
        assert result['results'][1]['content_type'] == "image"

def test_query_memory_bank_failure(mock_error_response):
    """Test querying the Memory Bank when it fails"""
    log_to_file("Starting query_memory_bank_failure test")
    
    with patch('requests.post', return_value=mock_error_response):
        result = client.query_memory_bank("test query")
        
        ic("Query failure test completed")
        log_to_file("query_memory_bank_failure test completed")
        
        assert result is None
    
    # Test connection error
    with patch('requests.post', side_effect=Exception("Connection error")):
        result = client.query_memory_bank("test query")
        
        ic("Query error test completed")
        log_to_file("query_memory_bank_error test completed")
        
        assert result is None

def test_add_to_memory_bank(mock_response):
    """Test adding to the Memory Bank"""
    log_to_file("Starting add_to_memory_bank test")
    
    # Set up mock response
    mock_response.json.return_value = {
        "status": "success",
        "message": "Added 1 chunks to Memory Bank",
        "chunk_ids": ["uuid1"],
        "filename": "test.md",
        "content_type": "text"
    }
    
    with patch('requests.post', return_value=mock_response):
        result = client.add_to_memory_bank(
            content="Test content",
            filename="test.md",
            directory="test_dir",
            section_title="Test Section",
            content_type="text"
        )
        
        ic(f"Add result: {result['status']}")
        log_to_file(f"add_to_memory_bank test result: {result['status']}")
        
        assert result is not None
        assert result['status'] == "success"
        assert result['filename'] == "test.md"
        assert result['content_type'] == "text"
        assert len(result['chunk_ids']) == 1

def test_add_to_memory_bank_failure(mock_error_response):
    """Test adding to the Memory Bank when it fails"""
    log_to_file("Starting add_to_memory_bank_failure test")
    
    with patch('requests.post', return_value=mock_error_response):
        result = client.add_to_memory_bank("Test content")
        
        ic("Add failure test completed")
        log_to_file("add_to_memory_bank_failure test completed")
        
        assert result is None
    
    # Test connection error
    with patch('requests.post', side_effect=Exception("Connection error")):
        result = client.add_to_memory_bank("Test content")
        
        ic("Add error test completed")
        log_to_file("add_to_memory_bank_error test completed")
        
        assert result is None

def test_add_image_to_memory_bank(mock_response, temp_image):
    """Test adding an image to the Memory Bank"""
    log_to_file("Starting add_image_to_memory_bank test")
    
    # Set up mock response
    mock_response.json.return_value = {
        "status": "success",
        "message": "Added image to Memory Bank",
        "id": "image-uuid",
        "filename": os.path.basename(temp_image),
        "content_type": "image"
    }
    
    with patch('requests.post', return_value=mock_response):
        result = client.add_image_to_memory_bank(temp_image, "Test Image")
        
        ic(f"Add image result: {result['status']}")
        log_to_file(f"add_image_to_memory_bank test result: {result['status']}")
        
        assert result is not None
        assert result['status'] == "success"
        assert result['filename'] == os.path.basename(temp_image)
        assert result['content_type'] == "image"

def test_add_image_nonexistent_file():
    """Test adding a non-existent image file"""
    log_to_file("Starting add_image_nonexistent_file test")
    
    result = client.add_image_to_memory_bank("/path/to/nonexistent/image.jpg")
    
    ic("Add non-existent image test completed")
    log_to_file("add_image_nonexistent_file test completed")
    
    assert result is None

def test_add_url_to_memory_bank(mock_response):
    """Test adding a URL to the Memory Bank"""
    log_to_file("Starting add_url_to_memory_bank test")
    
    # Set up mock response
    mock_response.json.return_value = {
        "status": "success",
        "message": "Added URL to Memory Bank",
        "id": "url-uuid",
        "url": "https://example.com",
        "title": "Example Website",
        "is_mcp": False,
        "content_type": "url"
    }
    
    with patch('requests.post', return_value=mock_response):
        result = client.add_url_to_memory_bank("https://example.com", "Test URL")
        
        ic(f"Add URL result: {result['status']}")
        log_to_file(f"add_url_to_memory_bank test result: {result['status']}")
        
        assert result is not None
        assert result['status'] == "success"
        assert result['url'] == "https://example.com"
        assert result['content_type'] == "url"

def test_add_url_invalid_url():
    """Test adding an invalid URL"""
    log_to_file("Starting add_url_invalid_url test")
    
    result = client.add_url_to_memory_bank("invalid-url")
    
    ic("Add invalid URL test completed")
    log_to_file("add_url_invalid_url test completed")
    
    assert result is None

def test_add_binary_to_memory_bank(mock_response, temp_binary_file):
    """Test adding a binary file to the Memory Bank"""
    log_to_file("Starting add_binary_to_memory_bank test")
    
    # Set up mock response
    mock_response.json.return_value = {
        "status": "success",
        "message": "Added binary file to Memory Bank",
        "id": "binary-uuid",
        "filename": os.path.basename(temp_binary_file),
        "file_type": "binary",
        "file_hash": "abc123hash",
        "content_type": "binary"
    }
    
    with patch('requests.post', return_value=mock_response):
        result = client.add_binary_to_memory_bank(
            temp_binary_file,
            notes="Test binary file",
            section_title="Test Binary"
        )
        
        ic(f"Add binary result: {result['status']}")
        log_to_file(f"add_binary_to_memory_bank test result: {result['status']}")
        
        assert result is not None
        assert result['status'] == "success"
        assert result['filename'] == os.path.basename(temp_binary_file)
        assert result['file_type'] == "binary"
        assert result['content_type'] == "binary"

def test_add_binary_nonexistent_file():
    """Test adding a non-existent binary file"""
    log_to_file("Starting add_binary_nonexistent_file test")
    
    result = client.add_binary_to_memory_bank("/path/to/nonexistent/file.bin")
    
    ic("Add non-existent binary test completed")
    log_to_file("add_binary_nonexistent_file test completed")
    
    assert result is None

def test_update_memory_bank(mock_response):
    """Test updating content in the Memory Bank"""
    log_to_file("Starting update_memory_bank test")
    
    # Set up mock response
    mock_response.json.return_value = {
        "status": "success",
        "message": "Updated document test-uuid",
        "id": "test-uuid",
        "content_type": "text"
    }
    
    with patch('requests.put', return_value=mock_response):
        result = client.update_memory_bank(
            doc_id="test-uuid",
            content="Updated content",
            section_title="Updated Section",
            content_type="text"
        )
        
        ic(f"Update result: {result['status']}")
        log_to_file(f"update_memory_bank test result: {result['status']}")
        
        assert result is not None
        assert result['status'] == "success"
        assert result['id'] == "test-uuid"
        assert result['content_type'] == "text"

def test_update_memory_bank_failure(mock_error_response):
    """Test updating content when it fails"""
    log_to_file("Starting update_memory_bank_failure test")
    
    with patch('requests.put', return_value=mock_error_response):
        result = client.update_memory_bank("test-uuid", "Updated content")
        
        ic("Update failure test completed")
        log_to_file("update_memory_bank_failure test completed")
        
        assert result is None
    
    # Test connection error
    with patch('requests.put', side_effect=Exception("Connection error")):
        result = client.update_memory_bank("test-uuid", "Updated content")
        
        ic("Update error test completed")
        log_to_file("update_memory_bank_error test completed")
        
        assert result is None

def test_delete_from_memory_bank(mock_response):
    """Test deleting content from the Memory Bank"""
    log_to_file("Starting delete_from_memory_bank test")
    
    # Set up mock response
    mock_response.json.return_value = {
        "status": "success",
        "message": "Deleted document with ID: test-uuid",
        "id": "test-uuid"
    }
    
    with patch('requests.delete', return_value=mock_response):
        result = client.delete_from_memory_bank("test-uuid")
        
        ic(f"Delete result: {result['status']}")
        log_to_file(f"delete_from_memory_bank test result: {result['status']}")
        
        assert result is not None
        assert result['status'] == "success"
        assert result['id'] == "test-uuid"

def test_delete_from_memory_bank_failure(mock_error_response):
    """Test deleting content when it fails"""
    log_to_file("Starting delete_from_memory_bank_failure test")
    
    with patch('requests.delete', return_value=mock_error_response):
        result = client.delete_from_memory_bank("test-uuid")
        
        ic("Delete failure test completed")
        log_to_file("delete_from_memory_bank_failure test completed")
        
        assert result is None
    
    # Test connection error
    with patch('requests.delete', side_effect=Exception("Connection error")):
        result = client.delete_from_memory_bank("test-uuid")
        
        ic("Delete error test completed")
        log_to_file("delete_from_memory_bank_error test completed")
        
        assert result is None

def test_main_function_query(mock_response):
    """Test main function with query command"""
    log_to_file("Starting main_function_query test")
    
    # Set up mock response
    mock_response.json.return_value = {
        "query": "test query",
        "results_count": 1,
        "results": [
            {
                "id": "uuid1",
                "filename": "test1.md",
                "content": "Test content 1",
                "content_type": "text"
            }
        ]
    }
    
    # Mock sys.argv
    test_args = ["cursor-memory-client.py", "query", "test query", "--limit=2", "--type=text"]
    
    with patch('sys.argv', test_args):
        with patch('requests.get', return_value=mock_response):  # For connection check
            with patch('requests.post', return_value=mock_response):  # For query
                with patch('cursor_memory_client.check_api_connection', return_value=True):
                    with patch('cursor_memory_client.query_memory_bank') as mock_query:
                        client.main()
                        
                        ic("Main function query test completed")
                        log_to_file("main_function_query test completed")
                        
                        # Check if query_memory_bank was called with correct args
                        mock_query.assert_called_once_with("test query", 2, "text")

def test_main_function_add_text(mock_response):
    """Test main function with add-text command"""
    log_to_file("Starting main_function_add_text test")
    
    # Mock sys.argv
    test_args = ["cursor-memory-client.py", "add-text", "Test content", "--filename=test.md", "--title=Test Title"]
    
    with patch('sys.argv', test_args):
        with patch('cursor_memory_client.check_api_connection', return_value=True):
            with patch('cursor_memory_client.add_to_memory_bank') as mock_add:
                client.main()
                
                ic("Main function add-text test completed")
                log_to_file("main_function_add_text test completed")
                
                # Check if add_to_memory_bank was called with correct args
                mock_add.assert_called_once_with("Test content", "test.md", None, "Test Title", 'text')

if __name__ == "__main__":
    # Run the tests
    pytest.main(["-v", __file__]) 