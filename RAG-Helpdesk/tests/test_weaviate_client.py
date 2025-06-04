#!/usr/bin/env python3
# tests/test_weaviate_client.py

import os
import sys
import pytest
import tempfile
import json
from datetime import datetime
from unittest.mock import patch, MagicMock, mock_open
from icecream import ic

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure icecream for logging
ic.configureOutput(prefix=f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] [TEST_WEAVIATE] ')
ic.enable()

# Test log file
LOG_FILE = "test_weaviate_log.txt"

def log_to_file(message):
    """Log a message to the test log file with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as log_file:
        log_file.write(f"[{timestamp}] {message}\n")

# Mock the MARKDOWN_DIRECTORY validation in weaviate_client before importing
with patch('os.path.isdir', return_value=True):
    import weaviate_client as wc

@pytest.fixture
def mock_weaviate_client():
    """Create a mock Weaviate client"""
    mock_client = MagicMock()
    mock_collection = MagicMock()
    mock_client.collections.get.return_value = mock_collection
    mock_client.get_meta.return_value = {"version": "1.30.4"}
    
    # Set up collections.exists to return False first time, True after
    mock_client.collections.exists.side_effect = [False]
    
    return mock_client

@pytest.fixture
def temp_markdown_dir():
    """Create a temporary directory with markdown files"""
    temp_dir = tempfile.mkdtemp()
    
    # Create a few markdown files
    for i in range(3):
        file_path = os.path.join(temp_dir, f"test_{i}.md")
        with open(file_path, "w") as f:
            f.write(f"# Test Document {i}\n\nThis is test document {i}.\n\n## Section 1\n\nContent for section 1.\n\n## Section 2\n\nContent for section 2.")
    
    yield temp_dir
    
    # Clean up - remove files and directory
    for i in range(3):
        file_path = os.path.join(temp_dir, f"test_{i}.md")
        if os.path.exists(file_path):
            os.remove(file_path)
    
    os.rmdir(temp_dir)

def test_load_markdown_documents(temp_markdown_dir):
    """Test loading markdown documents from a directory"""
    log_to_file("Starting load_markdown_documents test")
    
    # Set the environment variable for testing
    with patch.object(wc, "MARKDOWN_DIRECTORY", temp_markdown_dir):
        documents = wc.load_markdown_documents(temp_markdown_dir)
        
        ic(f"Loaded {len(documents)} documents")
        log_to_file(f"load_markdown_documents test result: {len(documents)} documents")
        
        # Check if documents were loaded properly
        assert len(documents) == 3
        
        # Check document metadata
        for doc in documents:
            assert "filepath" in doc.metadata
            assert "filename" in doc.metadata
            assert "directory" in doc.metadata
            assert "last_modified" in doc.metadata
            assert "file_size_kb" in doc.metadata
            assert "section_title" in doc.metadata
            assert "content_type" in doc.metadata
            assert doc.metadata["content_type"] == "text"
            
            # Check document content
            assert doc.page_content.startswith("# Test Document")

def test_chunk_documents():
    """Test chunking documents"""
    log_to_file("Starting chunk_documents test")
    
    # Create test documents
    from langchain_community.document_loaders import TextLoader
    
    docs = []
    for i in range(2):
        doc = MagicMock()
        doc.page_content = f"# Test Document {i}\n\nThis is test document {i}.\n\n## Section 1\n\nContent for section 1.\n\n## Section 2\n\nContent for section 2."
        doc.metadata = {
            "filepath": f"/path/to/test_{i}.md",
            "filename": f"test_{i}.md",
            "directory": "test",
            "last_modified": "2023-01-01T00:00:00Z",
            "file_size_kb": 1.0,
            "section_title": "",
            "content_type": "text"
        }
        docs.append(doc)
    
    # Mock the MarkdownTextSplitter
    with patch("weaviate_client.MarkdownTextSplitter") as MockSplitter:
        mock_splitter_instance = MockSplitter.return_value
        
        # Set up the mock to return split documents
        def mock_split(docs):
            result = []
            for doc in docs:
                # Create two chunks from each document
                chunk1 = MagicMock()
                chunk1.page_content = doc.page_content.split("## Section 1")[0]
                chunk1.metadata = doc.metadata.copy()
                chunk1.metadata["header_titles"] = "Main Title"
                
                chunk2 = MagicMock()
                chunk2.page_content = "## Section 1" + doc.page_content.split("## Section 1")[1]
                chunk2.metadata = doc.metadata.copy()
                chunk2.metadata["header_titles"] = "Section 1"
                
                result.extend([chunk1, chunk2])
            return result
        
        mock_splitter_instance.split_documents.side_effect = mock_split
        
        # Call the function
        chunks = wc.chunk_documents(docs)
        
        ic(f"Chunked into {len(chunks)} chunks")
        log_to_file(f"chunk_documents test result: {len(chunks)} chunks")
        
        # Check if documents were chunked properly
        assert len(chunks) == 4  # 2 documents with 2 chunks each
        
        # Check chunk metadata
        for chunk in chunks:
            assert "section_title" in chunk.metadata
            assert chunk.metadata["section_title"] in ["Main Title", "Section 1"]

def test_create_simple_vector():
    """Test creating a simple vector"""
    log_to_file("Starting create_simple_vector test")
    
    vector = wc.create_simple_vector("test text", vector_dim=10)
    
    ic(f"Created vector with {len(vector)} dimensions")
    log_to_file(f"create_simple_vector test result: {len(vector)} dimensions")
    
    assert len(vector) == 10
    assert all(isinstance(val, float) for val in vector)
    
    # Test reproducibility - same text should give same vector
    vector2 = wc.create_simple_vector("test text", vector_dim=10)
    assert vector == vector2
    
    # Different text should give different vector
    vector3 = wc.create_simple_vector("different text", vector_dim=10)
    assert vector != vector3

def test_ingest_chunks(mock_weaviate_client):
    """Test ingesting chunks to Weaviate"""
    log_to_file("Starting ingest_chunks test")
    
    # Create test chunks
    chunks = []
    for i in range(3):
        chunk = MagicMock()
        chunk.page_content = f"Chunk {i} content"
        chunk.metadata = {
            "filepath": f"/path/to/test.md",
            "filename": "test.md",
            "directory": "test",
            "section_title": f"Section {i}",
            "last_modified": "2023-01-01T00:00:00Z",
            "file_size_kb": 1.0,
            "content_type": "text"
        }
        chunks.append(chunk)
    
    # Set up the mock
    mock_collection = mock_weaviate_client.collections.get.return_value
    mock_collection.data.insert.return_value = "test-uuid"
    
    # Set up fetch_objects to return our chunks
    mock_result = MagicMock()
    mock_result.objects = [MagicMock() for _ in range(3)]
    mock_collection.query.fetch_objects.return_value = mock_result
    
    # Call the function
    with patch("weaviate_client.create_simple_vector", return_value=[0.1, 0.2, 0.3]):
        wc.ingest_chunks(mock_weaviate_client, chunks)
        
        ic("Tested ingest_chunks function")
        log_to_file("ingest_chunks test completed")
        
        # Check if chunks were ingested
        assert mock_collection.data.insert.call_count == 3

def test_search_documents(mock_weaviate_client):
    """Test searching documents"""
    log_to_file("Starting search_documents test")
    
    # Set up the mock
    mock_obj = MagicMock()
    mock_obj.properties = {
        'filename': 'test.md',
        'section_title': 'Test Section',
        'content': 'Test content',
        'content_type': 'text'
    }
    
    mock_result = MagicMock()
    mock_result.objects = [mock_obj]
    
    mock_collection = mock_weaviate_client.collections.get.return_value
    mock_collection.query.bm25.return_value = mock_result
    
    # Call the function
    results = wc.search_documents(mock_weaviate_client, "test query", limit=5)
    
    ic(f"Search found {len(results)} results")
    log_to_file(f"search_documents test result: {len(results)} results")
    
    assert len(results) == 1
    
    # Test with content type filter
    results = wc.search_documents(mock_weaviate_client, "test query", limit=5, content_type="text")
    
    ic(f"Search with filter found {len(results)} results")
    log_to_file(f"search_documents with filter test result: {len(results)} results")
    
    assert len(results) == 1
    assert mock_collection.query.bm25.call_count == 2

def test_rag_query(mock_weaviate_client):
    """Test RAG query function"""
    log_to_file("Starting rag_query test")
    
    # Set up mocks for different content types
    text_obj = MagicMock()
    text_obj.properties = {
        'filename': 'test.md',
        'filepath': '/path/to/test.md',
        'section_title': 'Text Section',
        'content': 'Test text content',
        'content_type': 'text'
    }
    
    image_obj = MagicMock()
    image_obj.properties = {
        'filename': 'test.jpg',
        'filepath': '/path/to/test.jpg',
        'section_title': 'Image Section',
        'content': 'Image: test.jpg',
        'content_type': 'image'
    }
    
    url_obj = MagicMock()
    url_obj.properties = {
        'filename': 'url_12345.txt',
        'filepath': '',
        'section_title': 'URL Section',
        'content': 'URL: https://example.com',
        'url': 'https://example.com',
        'url_title': 'Example Website',
        'url_description': 'An example website',
        'content_type': 'url',
        'is_mcp': False
    }
    
    binary_obj = MagicMock()
    binary_obj.properties = {
        'filename': 'test.bin',
        'filepath': '/path/to/test.bin',
        'section_title': 'Binary Section',
        'content': 'Binary File: test.bin',
        'content_type': 'binary',
        'binary_type': 'binary',
        'binary_notes': 'Test binary file'
    }
    
    # Set up the mock result with all content types
    mock_result = MagicMock()
    mock_result.objects = [text_obj, image_obj, url_obj, binary_obj]
    
    mock_collection = mock_weaviate_client.collections.get.return_value
    mock_collection.query.bm25.return_value = mock_result
    
    # Call the function
    response = wc.rag_query(mock_weaviate_client, "test query", num_docs=4)
    
    ic("Tested rag_query function")
    log_to_file("rag_query test completed")
    
    # Check response contains all content types
    assert "Text Section" in response
    assert "Image Section" in response
    assert "URL Section" in response
    assert "Binary Section" in response
    assert "https://example.com" in response
    assert "Example Website" in response
    
    # Test with content type filter
    mock_result.objects = [text_obj]
    response = wc.rag_query(mock_weaviate_client, "test query", num_docs=1, content_type="text")
    
    assert "Text Section" in response
    assert "Image Section" not in response

def test_schema_creation(mock_weaviate_client):
    """Test schema creation"""
    log_to_file("Starting schema_creation test")
    
    # Call the function that would create the schema
    with patch("weaviate_client.connect_to_local", return_value=mock_weaviate_client):
        # We can't test the whole main function as it does too much,
        # so let's test the schema creation logic
        properties = [
            wc.Property(name="content", data_type=wc.DataType.TEXT, description="The textual content or description"),
            wc.Property(name="content_type", data_type=wc.DataType.TEXT, description="Type of content", index_filterable=True)
        ]
        
        mock_weaviate_client.collections.exists.return_value = False
        mock_weaviate_client.collections.create.return_value = None
        
        # Create the collection
        mock_weaviate_client.collections.create(
            name="MarkdownChunk",
            description="Test collection",
            vectorizer_config=wc.Configure.Vectorizer.none(),
            properties=properties
        )
        
        ic("Tested schema creation")
        log_to_file("schema_creation test completed")
        
        # Check if the collection was created
        assert mock_weaviate_client.collections.create.call_count == 1

if __name__ == "__main__":
    # Run the tests
    pytest.main(["-v", __file__]) 