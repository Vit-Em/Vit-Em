#!/usr/bin/env python3
# 040/FlightDealClub/Weaviate/fdc-memory-api.py

import weaviate
import os
import numpy as np
import base64
import re
import requests
import mimetypes
from urllib.parse import urlparse
import hashlib
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
# from weaviate.auth import AuthApiKey # Not needed for local anonymous access
# from weaviate.classes.config import Property, DataType # Not strictly needed here, as schema is created by weaviate-client.py
from functools import wraps
from dotenv import load_dotenv
from langchain_text_splitters import MarkdownTextSplitter

# Load environment variables
load_dotenv()

# --- LOCAL WEAVIATE DETAILS ---
# These are no longer needed as we're connecting to local Weaviate
# WCS_URL = os.getenv("WCS_URL")
# WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")

# API Key for this Flask application (not Weaviate)
API_KEY = os.getenv("FDC_API_KEY", "test-api-key") # Add this to your .env file: FDC_API_KEY=your_secret_api_key
API_PORT = int(os.getenv("FDC_API_PORT", "5000"))

# Initialize Flask app
app = Flask(__name__)
CORS(app) # Enable CORS for all routes

# API key authentication for this Flask API
def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        provided_key = request.headers.get('X-API-Key')
        if not provided_key or provided_key != API_KEY:
            return jsonify({"error": "Unauthorized - Invalid API Key"}), 401
        return f(*args, **kwargs)
    return decorated

# Connect to Weaviate (MODIFIED FOR LOCAL DOCKER)
def get_weaviate_client():
    try:
        client = weaviate.connect_to_local(
            host="localhost", # Connect to the Docker container on your local machine
            port=8080,        # Default Weaviate port mapped by docker-compose
            # No auth_credentials needed because AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED is 'true' in docker-compose.yml
        )
        return client
    except Exception as e:
        print(f"Error connecting to Weaviate: {e}")
        return None

# Text splitter for chunking (remains the same)
def get_text_splitter():
    return MarkdownTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )

# Create simple random vectors for testing
def create_simple_vector(text, vector_dim=384):
    """Create a simple random vector for testing purposes."""
    # Use a seed based on the text to ensure consistency
    seed = sum(ord(c) for c in text)
    np.random.seed(seed)
    # Generate a random vector
    vector = np.random.rand(vector_dim).tolist()
    return vector

# New helper functions for handling different media types
def is_image_file(filename):
    """Check if a file is an image based on its extension"""
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'}
    return os.path.splitext(filename.lower())[1] in image_extensions

def encode_image_to_base64(image_path):
    """Encode an image file to base64"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Error encoding image: {e}")
        return None

def is_url(text):
    """Check if a string is a URL"""
    url_pattern = re.compile(
        r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)'
    )
    return bool(url_pattern.match(text))

def fetch_url_metadata(url):
    """Fetch basic metadata from a URL"""
    try:
        response = requests.get(url, timeout=5)
        content_type = response.headers.get('Content-Type', '')
        
        metadata = {
            'url': url,
            'status_code': response.status_code,
            'content_type': content_type,
            'domain': urlparse(url).netloc,
            'title': None,
            'description': None,
            'is_mcp': is_mcp_service(url)
        }
        
        # Try to extract title and description if it's HTML
        if 'text/html' in content_type:
            title_match = re.search(r'<title>(.*?)</title>', response.text, re.IGNORECASE | re.DOTALL)
            if title_match:
                metadata['title'] = title_match.group(1).strip()
            
            desc_match = re.search(r'<meta\s+name=["\'](description|summary)["\'][\s+]content=["\'](.*?)["\']', 
                                 response.text, re.IGNORECASE)
            if desc_match:
                metadata['description'] = desc_match.group(2).strip()
        
        return metadata
    except Exception as e:
        print(f"Error fetching URL metadata: {e}")
        return {'url': url, 'error': str(e), 'is_mcp': is_mcp_service(url)}

def is_mcp_service(url):
    """Check if a URL is an MCP (Management Control Panel) service"""
    # Common MCP domains and patterns
    mcp_patterns = [
        r'admin\.', r'manage\.', r'dashboard\.', r'control\.',
        r'cpanel', r'plesk', r'whm', r'webmin', r'admin-console',
        r'management', r'manage', r'controlpanel'
    ]
    
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.lower()
    path = parsed_url.path.lower()
    
    for pattern in mcp_patterns:
        if re.search(pattern, domain) or re.search(pattern, path):
            return True
    
    return False

def detect_file_type(file_path):
    """Detect the file type based on extension and mime type"""
    mime_type, _ = mimetypes.guess_type(file_path)
    extension = os.path.splitext(file_path)[1].lower()
    
    if mime_type:
        if mime_type.startswith('image/'):
            return 'image'
        elif mime_type.startswith('text/'):
            return 'text'
        elif mime_type in ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
            return 'document'
        elif mime_type.startswith('application/'):
            return 'binary'
        else:
            return 'other'
    
    # Fallback to extension-based detection
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']
    text_extensions = ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml']
    document_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
    
    if extension in image_extensions:
        return 'image'
    elif extension in text_extensions:
        return 'text'
    elif extension in document_extensions:
        return 'document'
    else:
        return 'binary'

def hash_binary_file(file_path):
    """Create a hash for a binary file"""
    try:
        with open(file_path, 'rb') as f:
            file_hash = hashlib.md5()
            chunk = f.read(8192)
            while chunk:
                file_hash.update(chunk)
                chunk = f.read(8192)
        return file_hash.hexdigest()
    except Exception as e:
        print(f"Error hashing file: {e}")
        return None

# API Routes
@app.route('/health', methods=['GET'])
def health_check():
    """Check if the API is running and can connect to Weaviate"""
    client = get_weaviate_client()
    if client is None:
        return jsonify({"status": "error", "message": "Could not connect to Weaviate"}), 500
    
    try:
        meta = client.get_meta()
        version = meta.get('version', 'unknown')
        client.close()
        return jsonify({
            "status": "healthy", 
            "weaviate_version": version,
            "api_version": "1.0.0"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/query', methods=['POST'])
@require_api_key
def query_memory_bank():
    """Query the Memory Bank with a natural language question"""
    data = request.json
    if not data or 'query' not in data:
        return jsonify({"error": "Missing 'query' in request body"}), 400
    
    query_text = data['query'] 
    limit = data.get('limit', 3)
    content_type = data.get('content_type', 'all')  # New parameter to filter by content type
    
    client = get_weaviate_client()
    if client is None:
        return jsonify({"error": "Could not connect to Weaviate"}), 500
    
    try:
        # Get the collection
        markdown_collection = client.collections.get("MarkdownChunk")
        
        # Add filters based on content_type if specified
        filters = None
        if content_type != 'all':
            filters = {
                "path": ["content_type"],
                "operator": "Equal",
                "valueText": content_type
            }
        
        # Since we can't use vector search easily, use BM25 text search instead
        if filters:
            results = markdown_collection.query.bm25(
                query=query_text,
                limit=limit,
                filters=filters
            )
        else:
        results = markdown_collection.query.bm25(
                query=query_text,
            limit=limit
        )
        
        # Format results
        formatted_results = []
        for obj in results.objects:
            result = {
                "id": obj.uuid,
                "filename": obj.properties['filename'],
                "filepath": obj.properties['filepath'],
                "section_title": obj.properties['section_title'],
                "content": obj.properties['content'],
                "last_modified": obj.properties['last_modified'],
                "content_type": obj.properties.get('content_type', 'text')
            }
            
            # Add type-specific fields if they exist
            if 'image_data' in obj.properties:
                result['image_data'] = obj.properties['image_data']
            
            if 'url' in obj.properties:
                result['url'] = obj.properties['url']
                result['url_title'] = obj.properties.get('url_title')
                result['url_description'] = obj.properties.get('url_description')
                result['is_mcp'] = obj.properties.get('is_mcp', False)
            
            if 'binary_hash' in obj.properties:
                result['binary_hash'] = obj.properties['binary_hash']
                result['binary_size'] = obj.properties.get('binary_size')
            
            formatted_results.append(result)
        
        client.close()
        return jsonify({
            "query": query_text,
            "results_count": len(formatted_results),
            "results": formatted_results
        })
    except Exception as e:
        if client:
            client.close()
        return jsonify({"error": str(e)}), 500

@app.route('/add', methods=['POST'])
@require_api_key
def add_to_memory_bank():
    """Add a new document to the Memory Bank"""
    data = request.json
    if not data or 'content' not in data:
        return jsonify({"error": "Missing 'content' in request body"}), 400
    
    content = data['content']
    filename = data.get('filename', f"generated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
    directory = data.get('directory', "cursor_generated")
    section_title = data.get('section_title', "Generated Content")
    content_type = data.get('content_type', 'text')  # Default to text if not specified
    
    client = get_weaviate_client()
    if client is None:
        return jsonify({"error": "Could not connect to Weaviate"}), 500
    
    try:
        # Get the collection
        markdown_collection = client.collections.get("MarkdownChunk")
        
        # Handle different content types
        if content_type == 'text':
        # Split content into chunks if it's large
        chunks = []
        if len(content) > 1000: # Check if splitting is necessary
            splitter = get_text_splitter()
            chunks = splitter.split_text(content)
        else:
            chunks = [content] # Treat whole content as one chunk
        
        # Add chunks to Weaviate
        chunk_ids = []
        for i, chunk_content in enumerate(chunks):
                # Create a vector for the chunk
                vector = create_simple_vector(chunk_content)
            
            # Create a consistent filepath for generated content
            filepath = f"/home/oem/Dokumente/_Python/100_Days/040/FlightDealClub/FDC_MemoryBank/{directory}/{filename}"
            
            # Create object properties for Weaviate
            properties = {
                "content": chunk_content,
                "filepath": filepath,
                "filename": filename,
                "directory": directory,
                "section_title": f"{section_title} (Part {i+1})" if len(chunks) > 1 else section_title,
                "last_modified": datetime.now().isoformat() + "Z",
                "file_size_kb": len(chunk_content) / 1024.0,
                    "content_type": "text"
            }
            
                # Add to collection with the explicit vector
            result = markdown_collection.data.insert(
                    properties=properties,
                    vector=vector
            )
            chunk_ids.append(result)
        
        client.close()
        return jsonify({
            "status": "success",
            "message": f"Added {len(chunks)} chunks to Memory Bank",
            "chunk_ids": chunk_ids,
                "filename": filename,
                "content_type": "text"
        })
        
        elif content_type == 'image':
            # For images, the content field should contain the path to the image file
            image_path = content
            if not os.path.exists(image_path):
                return jsonify({"error": f"Image file not found: {image_path}"}), 404
            
            # Encode the image as base64
            image_data = encode_image_to_base64(image_path)
            if not image_data:
                return jsonify({"error": f"Failed to encode image: {image_path}"}), 500
            
            # Create a vector based on the image filename and metadata
            vector = create_simple_vector(os.path.basename(image_path))
            
            # Create properties for the image
            properties = {
                "content": f"Image: {os.path.basename(image_path)}",
                "filepath": image_path,
                "filename": os.path.basename(image_path),
                "directory": directory,
                "section_title": section_title,
                "last_modified": datetime.now().isoformat() + "Z",
                "file_size_kb": os.path.getsize(image_path) / 1024.0,
                "content_type": "image",
                "image_data": image_data,
                "image_format": os.path.splitext(image_path)[1].lower()[1:]
            }
            
            # Add to collection
            result = markdown_collection.data.insert(
                properties=properties,
                vector=vector
            )
            
            client.close()
            return jsonify({
                "status": "success",
                "message": f"Added image to Memory Bank",
                "id": result,
                "filename": os.path.basename(image_path),
                "content_type": "image"
            })
        
        elif content_type == 'url':
            # For URLs, the content field should contain the URL
            url = content
            if not is_url(url):
                return jsonify({"error": f"Invalid URL: {url}"}), 400
            
            # Fetch metadata from the URL
            metadata = fetch_url_metadata(url)
            
            # Create a vector based on the URL and its metadata
            vector_text = url
            if metadata.get('title'):
                vector_text += " " + metadata['title']
            if metadata.get('description'):
                vector_text += " " + metadata['description']
            
            vector = create_simple_vector(vector_text)
            
            # Create properties for the URL
            properties = {
                "content": f"URL: {url}\nTitle: {metadata.get('title', 'N/A')}\nDescription: {metadata.get('description', 'N/A')}",
                "filepath": "",
                "filename": f"url_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                "directory": directory,
                "section_title": section_title,
                "last_modified": datetime.now().isoformat() + "Z",
                "file_size_kb": 0.1,  # Nominal size
                "content_type": "url",
                "url": url,
                "url_title": metadata.get('title'),
                "url_description": metadata.get('description'),
                "is_mcp": metadata.get('is_mcp', False)
            }
            
            # Add to collection
            result = markdown_collection.data.insert(
                properties=properties,
                vector=vector
            )
            
            client.close()
            return jsonify({
                "status": "success",
                "message": f"Added URL to Memory Bank",
                "id": result,
                "url": url,
                "title": metadata.get('title'),
                "is_mcp": metadata.get('is_mcp', False),
                "content_type": "url"
            })
        
        elif content_type == 'binary':
            # For binary files, the content field should contain the path to the file
            file_path = content
            if not os.path.exists(file_path):
                return jsonify({"error": f"File not found: {file_path}"}), 404
            
            # Get file type and hash
            file_type = detect_file_type(file_path)
            file_hash = hash_binary_file(file_path)
            
            # Create a vector based on the filename and hash
            vector = create_simple_vector(os.path.basename(file_path) + file_hash)
            
            # Get any additional notes
            notes = data.get('notes', 'No additional notes')
            
            # Create properties for the binary file
            properties = {
                "content": f"Binary File: {os.path.basename(file_path)}\nType: {file_type}\nNotes: {notes}",
                "filepath": file_path,
                "filename": os.path.basename(file_path),
                "directory": directory,
                "section_title": section_title,
                "last_modified": datetime.now().isoformat() + "Z",
                "file_size_kb": os.path.getsize(file_path) / 1024.0,
                "content_type": "binary",
                "binary_hash": file_hash,
                "binary_type": file_type,
                "binary_notes": notes,
                "binary_size": os.path.getsize(file_path)
            }
            
            # Add to collection
            result = markdown_collection.data.insert(
                properties=properties,
                vector=vector
            )
            
            client.close()
            return jsonify({
                "status": "success",
                "message": f"Added binary file to Memory Bank",
                "id": result,
                "filename": os.path.basename(file_path),
                "file_type": file_type,
                "file_hash": file_hash,
                "content_type": "binary"
            })
        
        else:
            return jsonify({"error": f"Unsupported content type: {content_type}"}), 400
        
    except Exception as e:
        if client:
            client.close()
        return jsonify({"error": str(e)}), 500

@app.route('/update', methods=['PUT'])
@require_api_key
def update_memory_bank():
    """Update an existing document in the Memory Bank"""
    data = request.json
    if not data or 'id' not in data or 'content' not in data:
        return jsonify({"error": "Missing 'id' or 'content' in request body"}), 400
    
    doc_id = data['id']
    content = data['content']
    section_title = data.get('section_title')
    content_type = data.get('content_type')
    
    client = get_weaviate_client()
    if client is None:
        return jsonify({"error": "Could not connect to Weaviate"}), 500
    
    try:
        # Get the collection
        markdown_collection = client.collections.get("MarkdownChunk")
        
        # Get the existing object to determine its content type
        existing_obj = markdown_collection.query.fetch_object_by_id(doc_id)
        if not existing_obj:
            return jsonify({"error": f"Document with ID {doc_id} not found"}), 404
        
        existing_content_type = existing_obj.properties.get('content_type', 'text')
        
        # If content_type is provided, use it, otherwise use the existing one
        if not content_type:
            content_type = existing_content_type
        
        # Create update properties based on content type
        if content_type == 'text':
        properties = {
            "content": content,
            "last_modified": datetime.now().isoformat() + "Z",
            "file_size_kb": len(content) / 1024.0,
        }
        
        # Add section_title if provided
        if section_title:
            properties["section_title"] = section_title
        
            # Create a vector for the updated content
            vector = create_simple_vector(content)
        
        elif content_type == 'url':
            # For URLs, the content field should contain the URL
            url = content
            if not is_url(url):
                return jsonify({"error": f"Invalid URL: {url}"}), 400
            
            # Fetch metadata from the URL
            metadata = fetch_url_metadata(url)
            
            # Create a vector based on the URL and its metadata
            vector_text = url
            if metadata.get('title'):
                vector_text += " " + metadata['title']
            if metadata.get('description'):
                vector_text += " " + metadata['description']
            
            vector = create_simple_vector(vector_text)
            
            # Create properties for the URL
            properties = {
                "content": f"URL: {url}\nTitle: {metadata.get('title', 'N/A')}\nDescription: {metadata.get('description', 'N/A')}",
                "last_modified": datetime.now().isoformat() + "Z",
                "url": url,
                "url_title": metadata.get('title'),
                "url_description": metadata.get('description'),
                "is_mcp": metadata.get('is_mcp', False)
            }
            
            # Add section_title if provided
            if section_title:
                properties["section_title"] = section_title
        
        elif content_type == 'binary':
            # For binary files, only update the notes
            notes = data.get('notes', 'No additional notes')
            
            properties = {
                "content": f"Binary File: {existing_obj.properties.get('filename')}\nType: {existing_obj.properties.get('binary_type')}\nNotes: {notes}",
                "last_modified": datetime.now().isoformat() + "Z",
                "binary_notes": notes
            }
            
            # Add section_title if provided
            if section_title:
                properties["section_title"] = section_title
            
            # Use the existing vector
            vector = None
        
        else:
            return jsonify({"error": f"Updates not supported for content type: {content_type}"}), 400
        
        # Update in Weaviate with explicit vector
        if vector:
            markdown_collection.data.update(
                uuid=doc_id,
                properties=properties,
                vector=vector
            )
        else:
        markdown_collection.data.update(
            uuid=doc_id,
            properties=properties
        )
        
        client.close()
        return jsonify({
            "status": "success",
            "message": f"Updated document {doc_id}",
            "id": doc_id,
            "content_type": content_type
        })
    except Exception as e:
        if client:
            client.close()
        return jsonify({"error": str(e)}), 500

@app.route('/delete', methods=['DELETE'])
@require_api_key
def delete_from_memory_bank():
    """Delete a document from the Memory Bank"""
    data = request.json
    if not data or 'id' not in data:
        return jsonify({"error": "Missing 'id' in request body"}), 400
    
    doc_id = data['id']
    
    client = get_weaviate_client()
    if client is None:
        return jsonify({"error": "Could not connect to Weaviate"}), 500
    
    try:
        # Get the collection
        markdown_collection = client.collections.get("MarkdownChunk")
        
        # Delete from Weaviate
        markdown_collection.data.delete(uuid=doc_id)
        
        client.close()
        return jsonify({
            "status": "success",
            "message": f"Deleted document with ID: {doc_id}",
            "id": doc_id
        })
    except Exception as e:
        if client:
            client.close()
        return jsonify({"error": str(e)}), 500

# Main execution
if __name__ == '__main__':
    print(f"Starting FDC Memory API on port {API_PORT}...")
    # Note: For production, use a WSGI server like Gunicorn instead of app.run()
    # Example: gunicorn --bind 0.0.0.0:5000 fdc-memory-api:app
    # The systemd service should handle this.
    app.run(host='0.0.0.0', port=API_PORT, debug=False) # Set debug=False for production-like behavior
