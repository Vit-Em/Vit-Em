#!/usr/bin/env python3
# 040/FlightDealClub/Weaviate/cursor-memory-client.py

import requests
import os
import re
import json
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API details
API_URL = os.getenv("FDC_API_URL", "http://localhost:5000")
API_KEY = os.getenv("FDC_API_KEY", "test-api-key")

# Headers for API requests
HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

def check_api_connection():
    """Check if the Memory Bank API is running"""
    try:
        response = requests.get(f"{API_URL}/health")
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                print("✅ Connected to Memory Bank API")
                print(f"   Weaviate version: {data.get('weaviate_version')}")
                print(f"   API version: {data.get('api_version', 'unknown')}")
                return True
            else:
                print(f"❌ Memory Bank API is running but not healthy: {data.get('message', 'No message')}")
                return False
        else:
            print(f"❌ Memory Bank API returned status code: {response.status_code}")
        return False
    except Exception as e:
        print(f"❌ Error connecting to Memory Bank API: {e}")
        print(f"   API URL: {API_URL}")
        return False

def query_memory_bank(query_text, limit=3, content_type='all'):
    """Query the Memory Bank with a natural language question"""
    try:
        payload = {
            "query": query_text,
            "limit": limit
        }
        
        if content_type != 'all':
            payload["content_type"] = content_type
            
        response = requests.post(f"{API_URL}/query", headers=HEADERS, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data.get('results_count', 0)} results for query: '{query_text}'")
            
            for i, result in enumerate(data.get("results", [])):
                content_type = result.get('content_type', 'text')
                print(f"\n--- Result {i+1} ---")
                print(f"ID: {result.get('id')}")
                print(f"File: {result.get('filename')}")
                print(f"Type: {content_type}")
                
                if content_type == 'text':
                    # For text content, show a preview
                    content = result.get("content", "")
                    preview = content[:200] + "..." if len(content) > 200 else content
                    print(f"Content Preview: {preview}")
                elif content_type == 'image':
                    print(f"Image: {result.get('filename')}")
                    print(f"Image format: {result.get('image_format', 'unknown')}")
                elif content_type == 'url':
                    print(f"URL: {result.get('url')}")
                    print(f"Title: {result.get('url_title', 'N/A')}")
                    print(f"Is MCP: {result.get('is_mcp', False)}")
                elif content_type == 'binary':
                    print(f"Binary file: {result.get('filename')}")
                    print(f"Binary type: {result.get('binary_type', 'unknown')}")
                    print(f"Binary size: {result.get('binary_size', 0)/1024/1024:.2f} MB")
                
            return data
        else:
            print(f"❌ Error querying Memory Bank: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error querying Memory Bank: {e}")
        return None

def add_to_memory_bank(content, filename=None, directory=None, section_title=None, content_type='text'):
    """Add a document to the Memory Bank"""
    try:
        payload = {
            "content": content,
            "content_type": content_type
        }
        
        if filename:
            payload["filename"] = filename
        if directory:
            payload["directory"] = directory
        if section_title:
            payload["section_title"] = section_title
            
        response = requests.post(f"{API_URL}/add", headers=HEADERS, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Successfully added to Memory Bank")
            
            if content_type == 'text':
            print(f"   Filename: {data.get('filename')}")
            print(f"   Chunks: {len(data.get('chunk_ids', []))}")
            elif content_type == 'image':
                print(f"   Image: {data.get('filename')}")
            elif content_type == 'url':
                print(f"   URL: {data.get('url')}")
                print(f"   Title: {data.get('title', 'N/A')}")
                print(f"   Is MCP: {data.get('is_mcp', False)}")
            elif content_type == 'binary':
                print(f"   Binary file: {data.get('filename')}")
                print(f"   File type: {data.get('file_type')}")
                print(f"   File hash: {data.get('file_hash')}")
                
            return data
        else:
            print(f"❌ Error adding to Memory Bank: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error adding to Memory Bank: {e}")
        return None

def add_image_to_memory_bank(image_path, section_title=None):
    """Add an image to the Memory Bank"""
    if not os.path.exists(image_path):
        print(f"❌ Image file not found: {image_path}")
        return None
        
    return add_to_memory_bank(
        content=image_path,
        filename=os.path.basename(image_path),
        directory=os.path.dirname(image_path),
        section_title=section_title or f"Image: {os.path.basename(image_path)}",
        content_type='image'
    )

def add_url_to_memory_bank(url, section_title=None):
    """Add a URL to the Memory Bank"""
    # Basic URL validation
    if not url.startswith(('http://', 'https://')):
        print(f"❌ Invalid URL: {url}. Must start with http:// or https://")
        return None
        
    return add_to_memory_bank(
        content=url,
        section_title=section_title or f"URL: {url}",
        content_type='url'
    )

def add_binary_to_memory_bank(file_path, notes=None, section_title=None):
    """Add a binary file to the Memory Bank"""
    if not os.path.exists(file_path):
        print(f"❌ Binary file not found: {file_path}")
        return None
    
    payload = {
        "content": file_path,
        "content_type": 'binary',
        "filename": os.path.basename(file_path),
        "directory": os.path.dirname(file_path),
        "section_title": section_title or f"Binary: {os.path.basename(file_path)}"
    }
    
    if notes:
        payload["notes"] = notes
            
    try:
        response = requests.post(f"{API_URL}/add", headers=HEADERS, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Successfully added binary file to Memory Bank")
            print(f"   Filename: {data.get('filename')}")
            print(f"   File type: {data.get('file_type')}")
            print(f"   File hash: {data.get('file_hash')}")
            return data
        else:
            print(f"❌ Error adding binary file to Memory Bank: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error adding binary file to Memory Bank: {e}")
        return None

def update_memory_bank(doc_id, content, section_title=None, content_type=None):
    """Update a document in the Memory Bank"""
    try:
        payload = {
            "id": doc_id,
            "content": content
        }
        
        if section_title:
            payload["section_title"] = section_title
            
        if content_type:
            payload["content_type"] = content_type
            
        response = requests.put(f"{API_URL}/update", headers=HEADERS, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Successfully updated document in Memory Bank")
            print(f"   ID: {data.get('id')}")
            return data
        else:
            print(f"❌ Error updating Memory Bank: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error updating Memory Bank: {e}")
        return None

def delete_from_memory_bank(doc_id):
    """Delete a document from the Memory Bank"""
    try:
        payload = {
            "id": doc_id
        }
            
        response = requests.delete(f"{API_URL}/delete", headers=HEADERS, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Successfully deleted document from Memory Bank")
            print(f"   ID: {data.get('id')}")
            return data
        else:
            print(f"❌ Error deleting from Memory Bank: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error deleting from Memory Bank: {e}")
        return None

# Main function for CLI usage
def main():
    """Main function for CLI usage"""
    if not check_api_connection():
        print("Exiting due to connection issues.")
        sys.exit(1)
        
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python cursor-memory-client.py query <question> [--limit=N] [--type=TYPE]")
        print("  python cursor-memory-client.py add-text <content> [--filename=NAME] [--directory=DIR] [--title=TITLE]")
        print("  python cursor-memory-client.py add-image <file_path> [--title=TITLE]")
        print("  python cursor-memory-client.py add-url <url> [--title=TITLE]")
        print("  python cursor-memory-client.py add-binary <file_path> [--notes=NOTES] [--title=TITLE]")
        print("  python cursor-memory-client.py update <id> <content> [--title=TITLE] [--type=TYPE]")
        print("  python cursor-memory-client.py delete <id>")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "query":
        if len(sys.argv) < 3:
            print("Error: No query specified")
            sys.exit(1)
        
        query_text = sys.argv[2]
        limit = 3
        content_type = 'all'
        
        # Parse additional arguments
        for arg in sys.argv[3:]:
            if arg.startswith("--limit="):
                try:
                    limit = int(arg.split("=")[1])
                except:
                    print(f"Warning: Invalid limit format: {arg}")
            elif arg.startswith("--type="):
                content_type = arg.split("=")[1]
        
        query_memory_bank(query_text, limit, content_type)
    
    elif command == "add-text":
        if len(sys.argv) < 3:
            print("Error: No content specified")
            sys.exit(1)
        
        content = sys.argv[2]
        filename = None
        directory = None
        title = None
        
        # Parse additional arguments
        for arg in sys.argv[3:]:
            if arg.startswith("--filename="):
                filename = arg.split("=")[1]
            elif arg.startswith("--directory="):
                directory = arg.split("=")[1]
            elif arg.startswith("--title="):
                title = arg.split("=")[1]
        
        add_to_memory_bank(content, filename, directory, title, 'text')
    
    elif command == "add-image":
        if len(sys.argv) < 3:
            print("Error: No image path specified")
            sys.exit(1)
        
        image_path = sys.argv[2]
        title = None
        
        # Parse additional arguments
        for arg in sys.argv[3:]:
            if arg.startswith("--title="):
                title = arg.split("=")[1]
        
        add_image_to_memory_bank(image_path, title)
    
    elif command == "add-url":
        if len(sys.argv) < 3:
            print("Error: No URL specified")
            sys.exit(1)
        
        url = sys.argv[2]
        title = None
        
        # Parse additional arguments
        for arg in sys.argv[3:]:
            if arg.startswith("--title="):
                title = arg.split("=")[1]
        
        add_url_to_memory_bank(url, title)
    
    elif command == "add-binary":
        if len(sys.argv) < 3:
            print("Error: No file path specified")
            sys.exit(1)
            
        file_path = sys.argv[2]
        notes = None
        title = None
        
        # Parse additional arguments
        for arg in sys.argv[3:]:
            if arg.startswith("--notes="):
                notes = arg.split("=")[1]
            elif arg.startswith("--title="):
                title = arg.split("=")[1]
        
        add_binary_to_memory_bank(file_path, notes, title)
    
    elif command == "update":
        if len(sys.argv) < 4:
            print("Error: ID and content required")
            sys.exit(1)
            
        doc_id = sys.argv[2]
        content = sys.argv[3]
        title = None
        content_type = None
        
        # Parse additional arguments
        for arg in sys.argv[4:]:
            if arg.startswith("--title="):
                title = arg.split("=")[1]
            elif arg.startswith("--type="):
                content_type = arg.split("=")[1]
        
        update_memory_bank(doc_id, content, title, content_type)
    
    elif command == "delete":
        if len(sys.argv) < 3:
            print("Error: No ID specified")
            sys.exit(1)
        
        doc_id = sys.argv[2]
        delete_from_memory_bank(doc_id)
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main() 