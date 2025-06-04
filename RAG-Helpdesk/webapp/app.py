import os
from flask import Flask, render_template, request, redirect, url_for, flash
# We will create weaviate_service.py later
# from . import weaviate_service
import weaviate
import numpy as np
import requests
from icecream import ic
import datetime
import uuid

ic.configureOutput(includeContext=True)
ic('Starting Flask app and importing dependencies')

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For flash messages

# --- Weaviate Connection ---
try:
    # Attempt to connect to the local Weaviate instance as per docker-compose.yml
    client = weaviate.connect_to_local(
        host="localhost",
        port=8080,
        grpc_port=50051
    )
    client.is_ready() # Check if connection is successful
    ic("Successfully connected to Weaviate.")
except Exception as e:
    ic(f"Error connecting to Weaviate: {e}")
    client = None # Set client to None if connection fails

# Create simple random vectors for testing
def create_simple_vector(text, vector_dim=384):
    """Create a simple random vector for testing purposes."""
    # Use a seed based on the text to ensure consistency
    seed = sum(ord(c) for c in text)
    np.random.seed(seed)
    # Generate a random vector
    vector = np.random.rand(vector_dim).tolist()
    return vector

# --- REST Health and Metrics ---
def is_weaviate_ready():
    try:
        resp = requests.get("http://localhost:8080/v1/.well-known/ready", timeout=2)
        ic('Health check /v1/.well-known/ready', resp.status_code, resp.text)
        return resp.status_code == 200
    except Exception as e:
        ic(f"Weaviate health check failed: {e}")
        return False

def get_weaviate_meta():
    try:
        resp = requests.get("http://localhost:8080/v1/meta", timeout=2)
        ic('Meta /v1/meta', resp.status_code, resp.text)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        ic(f"Meta fetch failed: {e}")
    return {}

def get_weaviate_nodes():
    try:
        resp = requests.get("http://localhost:8080/v1/nodes", timeout=2)
        ic('Nodes /v1/nodes', resp.status_code, resp.text)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        ic(f"Nodes fetch failed: {e}")
    return {}

def get_weaviate_metrics():
    try:
        resp = requests.get("http://localhost:8080/metrics", timeout=2)
        ic('Metrics /metrics', resp.status_code)
        if resp.status_code == 200:
            # Return first 10 lines for brevity
            return '\n'.join(resp.text.splitlines()[:10])
    except Exception as e:
        ic(f"Metrics fetch failed: {e}")
    return ""

@app.route('/')
def index():
    stats = {}
    entries = []
    meta = {}
    nodes = {}
    metrics = ""
    no_entries_message = None
    if not is_weaviate_ready():
        stats['error'] = "Weaviate is not ready or not reachable at http://localhost:8080"
        stats['total_markdown_chunks'] = "N/A"
        ic(stats['error'])
        return render_template('index.html', stats=stats, entries=entries, meta=meta, nodes=nodes, metrics=metrics, no_entries_message=no_entries_message)
    meta = get_weaviate_meta()
    nodes = get_weaviate_nodes()
    metrics = get_weaviate_metrics()
    if client:
        try:
            if "MarkdownChunk" in client.collections.list_all():
                markdown_collection = client.collections.get("MarkdownChunk")
                response = markdown_collection.aggregate.over_all(total_count=True)
                stats['total_markdown_chunks'] = response.total_count
                ic(f"Total MarkdownChunk objects: {response.total_count}")

                # Fetch up to 20 entries for display
                objects_response = markdown_collection.query.fetch_objects(limit=20)
                ic("fetch_objects response:", objects_response)
                objects = getattr(objects_response, 'objects', [])
                if not objects:
                    ic("No objects found in MarkdownChunk collection.")
                    no_entries_message = "No entries found in MarkdownChunk collection."
                for obj in objects:
                    entry = {
                        'uuid': obj.uuid,
                        'filename': obj.properties.get('filename', 'N/A'),
                        'vector_weight': None
                    }
                    vector = obj.vector
                    ic(f"Object {obj.uuid} vector type: {type(vector)}")
                    
                    # Defensive: handle None, dict, empty, wrong type
                    if vector is not None:
                        if isinstance(vector, dict):
                            # Try common keys
                            if 'vector' in vector and vector['vector']:
                                vector = vector['vector']
                            elif 'embedding' in vector and vector['embedding']:
                                vector = vector['embedding']
                            elif vector:
                                # fallback: try first value if dict is not empty
                                try:
                                    vector = list(vector.values())[0]
                                except (IndexError, TypeError, ValueError):
                                    vector = []
                            else:
                                vector = []
                        
                        # Check if it's a valid vector with elements
                        if isinstance(vector, (list, tuple, np.ndarray)) and len(vector) > 0:
                            try:
                                # Convert all elements to float if needed
                                if not isinstance(vector, np.ndarray):
                                    vector = [float(v) if v is not None else 0.0 for v in vector]
                                entry['vector_weight'] = float(np.linalg.norm(vector))
                            except Exception as ve:
                                ic(f"Vector norm error for {obj.uuid}: {ve}")
                                entry['vector_weight'] = 'ERR'
                        else:
                            ic(f"Empty or invalid vector for {obj.uuid}")
                            entry['vector_weight'] = 'N/A'
                    else:
                        ic(f"No vector for {obj.uuid}")
                        entry['vector_weight'] = 'N/A'
                    
                    entries.append(entry)
                ic(f"Fetched {len(entries)} entries for display")
            else:
                stats['total_markdown_chunks'] = "Collection 'MarkdownChunk' not found."
                ic(stats['total_markdown_chunks'])
        except Exception as e:
            ic(f"Error fetching stats: {e}")
            stats['error'] = str(e)
    else:
        stats['error'] = "Not connected to Weaviate. Please check server logs."
        stats['total_markdown_chunks'] = "N/A"
        ic(stats['error'])
    return render_template('index.html', stats=stats, entries=entries, meta=meta, nodes=nodes, metrics=metrics, no_entries_message=no_entries_message)

# Add entries to Weaviate
@app.route('/add', methods=['POST'])
def add_entry():
    if not client:
        ic("Add entry failed: Not connected to Weaviate")
        return "Error: Not connected to Weaviate", 500
    
    content_type = request.form.get('content_type')
    ic(f"Received add request. Content type: {content_type}")
    
    try:
        # Check if MarkdownChunk collection exists
        if "MarkdownChunk" not in client.collections.list_all():
            # Create collection if it doesn't exist
            ic("Creating MarkdownChunk collection")
            client.collections.create(
                name="MarkdownChunk",
                properties=[
                    {"name": "content", "dataType": ["text"]},
                    {"name": "filepath", "dataType": ["text"]},
                    {"name": "filename", "dataType": ["text"]},
                    {"name": "directory", "dataType": ["text"]},
                    {"name": "section_title", "dataType": ["text"]},
                    {"name": "last_modified", "dataType": ["date"]},
                    {"name": "file_size_kb", "dataType": ["number"]},
                    {"name": "content_type", "dataType": ["text"]}
                ]
            )
        
        # Get the collection
        markdown_collection = client.collections.get("MarkdownChunk")
        
        # Prepare properties based on content type
        properties = {}
        filename = request.form.get('filename_add', '')
        tags = request.form.get('tags_add', '')
        
        # Set common properties
        properties["section_title"] = "Web UI Added"
        properties["last_modified"] = datetime.datetime.now().isoformat() + "Z"
        
        if content_type == 'text':
            text_content = request.form.get('text_content', '')
            ic(f"Text content: {text_content[:100]}...")
            
            # If no filename provided, generate one
            if not filename:
                filename = f"web_added_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            
            properties["content"] = text_content
            properties["filename"] = filename
            properties["filepath"] = f"/web_ui_added/{filename}"
            properties["directory"] = "web_ui_added"
            properties["file_size_kb"] = len(text_content) / 1024.0
            properties["content_type"] = "text"
            
            # Generate a random vector
            vector = create_simple_vector(text_content)
            
        elif content_type == 'file':
            uploaded_file = request.files.get('file_upload')
            
            if uploaded_file and uploaded_file.filename:
                file_content = uploaded_file.read()
                file_actual_type = request.form.get('file_actual_type', 'binary')
                
                # If no filename provided, use the uploaded filename
                if not filename:
                    filename = uploaded_file.filename
                
                ic(f"File uploaded: {filename}, type: {file_actual_type}")
                
                # For simplicity, store the first 1000 chars of binary files as content
                if file_actual_type in ['binary', 'image']:
                    # Store base64 or file info
                    properties["content"] = f"Binary file {filename} of type {file_actual_type}"
                else:
                    # For text-based files, try to decode
                    try:
                        decoded_content = file_content.decode('utf-8')
                        properties["content"] = decoded_content[:2000] + ("..." if len(decoded_content) > 2000 else "")
                    except UnicodeDecodeError:
                        properties["content"] = f"Binary file {filename} of type {file_actual_type}"
                
                properties["filename"] = filename
                properties["filepath"] = f"/web_ui_added/{filename}"
                properties["directory"] = "web_ui_added"
                properties["file_size_kb"] = len(file_content) / 1024.0
                properties["content_type"] = file_actual_type
                
                # Generate a random vector based on filename and type
                vector = create_simple_vector(f"{filename}_{file_actual_type}")
            else:
                ic("No file provided for upload.")
                flash("No file provided for upload.", "error")
                return redirect(url_for('index'))
        else:
            ic(f"Unsupported content type: {content_type}")
            flash(f"Unsupported content type: {content_type}", "error")
            return redirect(url_for('index'))
        
        # Add tags if provided
        if tags:
            properties["tags"] = tags
        
        # Add object with vector to Weaviate
        result = markdown_collection.data.insert(
            properties=properties,
            vector=vector
        )
        
        ic(f"Successfully added entry with ID: {result}")
        flash(f"Successfully added entry with ID: {result}", "success")
        
    except Exception as e:
        ic(f"Error adding entry: {e}")
        flash(f"Error adding entry: {e}", "error")
    
    return redirect(url_for('index'))

# Placeholder for deleting entries
@app.route('/delete', methods=['POST'])
def delete_entry():
    if not client:
        ic("Delete entry failed: Not connected to Weaviate")
        flash("Delete entry failed: Not connected to Weaviate", "error")
        return redirect(url_for('index'))
    
    entry_id = request.form.get('entry_id')
    ic(f"Received delete request for ID: {entry_id}")
    
    try:
        markdown_collection = client.collections.get("MarkdownChunk")
        markdown_collection.data.delete_by_id(uuid=entry_id)
        ic(f"Successfully deleted object with ID: {entry_id}")
        flash(f"Successfully deleted object with ID: {entry_id}", "success")
    except Exception as e:
        ic(f"Error deleting object {entry_id}: {e}")
        flash(f"Error deleting object {entry_id}: {e}", "error")
    
    return redirect(url_for('index'))

@app.teardown_appcontext
def close_weaviate_client(exception):
    if client is not None:
        ic("Closing Weaviate client connection")
        client.close()

if __name__ == '__main__':
    # Ensure the WEAVIATE_URL is correctly pointing to your instance
    # For local Docker setup, http://localhost:8080 is common.
    # The client connection is handled above.
    ic("Running Flask app on http://0.0.0.0:5001")
    app.run(debug=True, host='0.0.0.0', port=5001) # Running on a different port than Weaviate 