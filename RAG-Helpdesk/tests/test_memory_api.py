#!/usr/bin/env python3
# tests/test_memory_api.py

import os
import sys
import pytest
import requests
import json
import base64
import tempfile
import shutil
import time
from datetime import datetime
from unittest.mock import patch, MagicMock
from icecream import ic

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Import the module with the actual filename
import fdc_memory_api
from fdc_memory_api import app, get_weaviate_client, create_simple_vector

# Configure icecream for logging
ic.configureOutput(prefix=f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] [TEST_API] ')
ic.enable()

# Test log file
LOG_FILE = "test_api_log.txt"

def log_to_file(message):
    """Log a message to the test log file with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as log_file:
        log_file.write(f"[{timestamp}] {message}\n")

@pytest.fixture
def client():
    """Create a test client for the Flask app"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_weaviate_client():
    """Create a mock Weaviate client"""
    mock_client = MagicMock()
    mock_collection = MagicMock()
    mock_client.collections.get.return_value = mock_collection
    mock_client.get_meta.return_value = {"version": "1.30.4"}
    return mock_client

@pytest.fixture
def api_headers():
    """Headers for API requests including API key"""
    return {
        "Content-Type": "application/json",
        "X-API-Key": "test-api-key"
    }

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
    shutil.rmtree(temp_dir)

def test_health_check(client, mock_weaviate_client):
    """Test the health check endpoint"""
    log_to_file("Starting health check test")
    
    with patch('fdc_memory_api.get_weaviate_client', return_value=mock_weaviate_client):
        response = client.get('/health')
        data = json.loads(response.data)
        
        ic(f"Health check response: {data}")
        log_to_file(f"Health check test result: {data}")
        
        assert response.status_code == 200
        assert data['status'] == 'healthy'
        assert data['weaviate_version'] == '1.30.4'
        assert data['api_version'] == '1.0.0'

def test_health_check_no_connection(client):
    """Test the health check endpoint when Weaviate is not available"""
    log_to_file("Starting health check test with no connection")
    
    with patch('fdc_memory_api.get_weaviate_client', return_value=None):
        response = client.get('/health')
        data = json.loads(response.data)
        
        ic(f"Health check response with no connection: {data}")
        log_to_file(f"Health check test with no connection result: {data}")
        
        assert response.status_code == 500
        assert data['status'] == 'error'

def test_query_memory_bank(client, mock_weaviate_client, api_headers):
    """Test querying the Memory Bank"""
    log_to_file("Starting query memory bank test")
    
    # Mock the query result
    mock_obj = MagicMock()
    mock_obj.uuid = "test-uuid"
    mock_obj.properties = {
        'filename': 'test.md',
        'filepath': '/path/to/test.md',
        'section_title': 'Test Section',
        'content': 'Test content',
        'last_modified': '2023-01-01T00:00:00Z',
        'content_type': 'text'
    }
    
    mock_result = MagicMock()
    mock_result.objects = [mock_obj]
    
    mock_collection = mock_weaviate_client.collections.get.return_value
    mock_collection.query.bm25.return_value = mock_result
    
    with patch('fdc_memory_api.get_weaviate_client', return_value=mock_weaviate_client):
        response = client.post('/query', 
                              headers=api_headers, 
                              json={'query': 'test query', 'limit': 3})
        data = json.loads(response.data)
        
        ic(f"Query response: {data}")
        log_to_file(f"Query memory bank test result: {response.status_code}")
        
        assert response.status_code == 200
        assert data['query'] == 'test query'
        assert data['results_count'] == 1
        assert len(data['results']) == 1
        assert data['results'][0]['id'] == 'test-uuid'
        assert data['results'][0]['content'] == 'Test content'

def test_query_with_content_type_filter(client, mock_weaviate_client, api_headers):
    """Test querying the Memory Bank with content type filter"""
    log_to_file("Starting query with content type filter test")
    
    # Mock the query result
    mock_obj = MagicMock()
    mock_obj.uuid = "test-uuid"
    mock_obj.properties = {
        'filename': 'test.jpg',
        'filepath': '/path/to/test.jpg',
        'section_title': 'Test Image',
        'content': 'Image: test.jpg',
        'last_modified': '2023-01-01T00:00:00Z',
        'content_type': 'image',
        'image_data': 'base64data',
        'image_format': 'jpg'
    }
    
    mock_result = MagicMock()
    mock_result.objects = [mock_obj]
    
    mock_collection = mock_weaviate_client.collections.get.return_value
    mock_collection.query.bm25.return_value = mock_result
    
    with patch('fdc_memory_api.get_weaviate_client', return_value=mock_weaviate_client):
        response = client.post('/query', 
                              headers=api_headers, 
                              json={'query': 'test image', 'limit': 3, 'content_type': 'image'})
        data = json.loads(response.data)
        
        ic(f"Query with content type filter response: {data}")
        log_to_file(f"Query with content type filter test result: {response.status_code}")
        
        assert response.status_code == 200
        assert data['query'] == 'test image'
        assert data['results_count'] == 1
        assert data['results'][0]['content_type'] == 'image'
        assert 'image_data' in data['results'][0]

def test_add_text(client, mock_weaviate_client, api_headers):
    """Test adding text to the Memory Bank"""
    log_to_file("Starting add text test")
    
    mock_collection = mock_weaviate_client.collections.get.return_value
    mock_collection.data.insert.return_value = "new-text-uuid"
    
    with patch('fdc_memory_api.get_weaviate_client', return_value=mock_weaviate_client):
        with patch('fdc_memory_api.create_simple_vector', return_value=[0.1, 0.2, 0.3]):
            response = client.post('/add', 
                                  headers=api_headers, 
                                  json={
                                      'content': 'Test content',
                                      'filename': 'test.md',
                                      'directory': 'test_dir',
                                      'section_title': 'Test Section',
                                      'content_type': 'text'
                                  })
            data = json.loads(response.data)
            
            ic(f"Add text response: {data}")
            log_to_file(f"Add text test result: {response.status_code}")
            
            assert response.status_code == 200
            assert data['status'] == 'success'
            assert 'chunk_ids' in data
            assert data['filename'] == 'test.md'
            assert data['content_type'] == 'text'

def test_add_image(client, mock_weaviate_client, api_headers, temp_image):
    """Test adding an image to the Memory Bank"""
    log_to_file("Starting add image test")
    
    mock_collection = mock_weaviate_client.collections.get.return_value
    mock_collection.data.insert.return_value = "new-image-uuid"
    
    with patch('fdc_memory_api.get_weaviate_client', return_value=mock_weaviate_client):
        with patch('fdc_memory_api.create_simple_vector', return_value=[0.1, 0.2, 0.3]):
            with patch('fdc_memory_api.encode_image_to_base64', return_value="base64_encoded_data"):
                response = client.post('/add', 
                                      headers=api_headers, 
                                      json={
                                          'content': temp_image,
                                          'section_title': 'Test Image',
                                          'content_type': 'image'
                                      })
                data = json.loads(response.data)
                
                ic(f"Add image response: {data}")
                log_to_file(f"Add image test result: {response.status_code}")
                
                assert response.status_code == 200
                assert data['status'] == 'success'
                assert data['id'] == 'new-image-uuid'
                assert data['content_type'] == 'image'
                assert os.path.basename(temp_image) == data['filename']

def test_add_url(client, mock_weaviate_client, api_headers):
    """Test adding a URL to the Memory Bank"""
    log_to_file("Starting add URL test")
    
    mock_collection = mock_weaviate_client.collections.get.return_value
    mock_collection.data.insert.return_value = "new-url-uuid"
    
    url_metadata = {
        'url': 'https://example.com',
        'title': 'Example Website',
        'description': 'An example website for testing',
        'is_mcp': False
    }
    
    with patch('fdc_memory_api.get_weaviate_client', return_value=mock_weaviate_client):
        with patch('fdc_memory_api.create_simple_vector', return_value=[0.1, 0.2, 0.3]):
            with patch('fdc_memory_api.is_url', return_value=True):
                with patch('fdc_memory_api.fetch_url_metadata', return_value=url_metadata):
                    response = client.post('/add', 
                                          headers=api_headers, 
                                          json={
                                              'content': 'https://example.com',
                                              'section_title': 'Test URL',
                                              'content_type': 'url'
                                          })
                    data = json.loads(response.data)
                    
                    ic(f"Add URL response: {data}")
                    log_to_file(f"Add URL test result: {response.status_code}")
                    
                    assert response.status_code == 200
                    assert data['status'] == 'success'
                    assert data['id'] == 'new-url-uuid'
                    assert data['content_type'] == 'url'
                    assert data['url'] == 'https://example.com'
                    assert data['title'] == 'Example Website'
                    assert data['is_mcp'] == False

def test_add_binary(client, mock_weaviate_client, api_headers, temp_binary_file):
    """Test adding a binary file to the Memory Bank"""
    log_to_file("Starting add binary file test")
    
    mock_collection = mock_weaviate_client.collections.get.return_value
    mock_collection.data.insert.return_value = "new-binary-uuid"
    
    with patch('fdc_memory_api.get_weaviate_client', return_value=mock_weaviate_client):
        with patch('fdc_memory_api.create_simple_vector', return_value=[0.1, 0.2, 0.3]):
            with patch('fdc_memory_api.detect_file_type', return_value='binary'):
                with patch('fdc_memory_api.hash_binary_file', return_value='abc123hash'):
                    response = client.post('/add', 
                                          headers=api_headers, 
                                          json={
                                              'content': temp_binary_file,
                                              'section_title': 'Test Binary',
                                              'notes': 'Test binary file notes',
                                              'content_type': 'binary'
                                          })
                    data = json.loads(response.data)
                    
                    ic(f"Add binary file response: {data}")
                    log_to_file(f"Add binary file test result: {response.status_code}")
                    
                    assert response.status_code == 200
                    assert data['status'] == 'success'
                    assert data['id'] == 'new-binary-uuid'
                    assert data['content_type'] == 'binary'
                    assert data['file_type'] == 'binary'
                    assert data['file_hash'] == 'abc123hash'
                    assert os.path.basename(temp_binary_file) == data['filename']

def test_update_text(client, mock_weaviate_client, api_headers):
    """Test updating text in the Memory Bank"""
    log_to_file("Starting update text test")
    
    # Mock the existing object
    mock_obj = MagicMock()
    mock_obj.properties = {
        'content_type': 'text',
        'filename': 'test.md'
    }
    
    mock_collection = mock_weaviate_client.collections.get.return_value
    mock_collection.query.fetch_object_by_id.return_value = mock_obj
    
    with patch('fdc_memory_api.get_weaviate_client', return_value=mock_weaviate_client):
        with patch('fdc_memory_api.create_simple_vector', return_value=[0.1, 0.2, 0.3]):
            response = client.put('/update', 
                                 headers=api_headers, 
                                 json={
                                     'id': 'test-uuid',
                                     'content': 'Updated content',
                                     'section_title': 'Updated Section'
                                 })
            data = json.loads(response.data)
            
            ic(f"Update text response: {data}")
            log_to_file(f"Update text test result: {response.status_code}")
            
            assert response.status_code == 200
            assert data['status'] == 'success'
            assert data['id'] == 'test-uuid'
            assert data['content_type'] == 'text'

def test_delete(client, mock_weaviate_client, api_headers):
    """Test deleting content from the Memory Bank"""
    log_to_file("Starting delete test")
    
    mock_collection = mock_weaviate_client.collections.get.return_value
    
    with patch('fdc_memory_api.get_weaviate_client', return_value=mock_weaviate_client):
        response = client.delete('/delete', 
                               headers=api_headers, 
                               json={'id': 'test-uuid'})
        data = json.loads(response.data)
        
        ic(f"Delete response: {data}")
        log_to_file(f"Delete test result: {response.status_code}")
        
        assert response.status_code == 200
        assert data['status'] == 'success'
        assert data['id'] == 'test-uuid'

def test_auth_required(client):
    """Test that API key is required for protected endpoints"""
    log_to_file("Starting auth required test")
    
    # Test query endpoint without API key
    response = client.post('/query', 
                          json={'query': 'test'})
    data = json.loads(response.data)
    
    ic(f"Auth required response: {data}")
    log_to_file(f"Auth required test result: {response.status_code}")
    
    assert response.status_code == 401
    assert 'error' in data
    assert 'Unauthorized' in data['error']

def test_create_simple_vector():
    """Test the create_simple_vector function"""
    log_to_file("Starting create_simple_vector test")
    
    vector = create_simple_vector("test text", vector_dim=10)
    
    ic(f"Simple vector: {vector}")
    log_to_file(f"Create simple vector test result: {len(vector)} dimensions")
    
    assert len(vector) == 10
    assert all(isinstance(val, float) for val in vector)

if __name__ == "__main__":
    # Run the tests
    pytest.main(["-v", __file__]) 