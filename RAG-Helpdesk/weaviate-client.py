#!/usr/bin/env python3
# 040/FlightDealClub/Weaviate/weaviate-client.py
import weaviate
import os
import numpy as np  # Add this import for random vector generation
from weaviate.classes.config import Property, DataType, Configure
# from weaviate.auth import AuthApiKey # We won't need this for anonymous access
from icecream import ic
from dotenv import load_dotenv

# Langchain imports for document loading and splitting
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import MarkdownTextSplitter
from datetime import datetime

# Load environment variables from .env file (if still used for MARKDOWN_DIRECTORY)
load_dotenv()

ic.enable()

# --- LOCAL WEAVIATE DETAILS ---
# Remove or comment out WCS_URL and WEAVIATE_API_KEY if they are defined here
# WCS_URL = os.getenv("WCS_URL")
# WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")

# --- Directory where your Markdown files are located ---
# Ensure this points to your local MemoryBank
MARKDOWN_DIRECTORY = os.getenv("MARKDOWN_DIRECTORY", os.path.expanduser("~/Dokumente/_Python/100_Days/040/FlightDealClub/FDC_MemoryBank"))
ic(f"Looking for Markdown files in: {MARKDOWN_DIRECTORY}")

# Validate MARKDOWN_DIRECTORY
if not MARKDOWN_DIRECTORY or not os.path.isdir(MARKDOWN_DIRECTORY):
    raise ValueError(f"MARKDOWN_DIRECTORY is not set or not a valid directory: {MARKDOWN_DIRECTORY}")


# Display values for debugging (comment out in production)

# --- 1. Load your documents: Read your markdown files. ---
def load_markdown_documents(directory_path: str):
    ic(f"Loading documents from: {directory_path}")
    documents = []
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.endswith((".md", ".txt")):  # Include .txt as well, if needed
                filepath = os.path.join(root, file)
                try:
                    loader = TextLoader(filepath)
                    docs_from_file = loader.load()

                    # Add metadata from the file system
                    file_stat = os.stat(filepath)
                    last_modified = datetime.fromtimestamp(file_stat.st_mtime).isoformat() + "Z"  # ISO 8601 with Z for UTC
                    file_size_kb = file_stat.st_size / 1024.0  # Convert bytes to KB

                    for doc in docs_from_file:
                        # Add extra metadata that matches your Weaviate schema
                        doc.metadata["filepath"] = filepath
                        doc.metadata["filename"] = file
                        doc.metadata["directory"] = os.path.relpath(root, directory_path)
                        doc.metadata["last_modified"] = last_modified
                        doc.metadata["file_size_kb"] = file_size_kb
                        doc.metadata["section_title"] = ""
                        doc.metadata["content_type"] = "text"  # Add content type for text documents
                        documents.append(doc)
                    ic(f"Loaded {len(docs_from_file)} document(s) from {filepath}")
                except Exception as e:
                    ic(f"Error loading {filepath}: {e}")
    ic(f"Finished loading. Total documents loaded: {len(documents)}")
    return documents

# --- 2. Chunk your documents: Break them into smaller, semantically meaningful pieces. ---
def chunk_documents(documents):
    ic(f"Chunking {len(documents)} documents...")
    markdown_splitter = MarkdownTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )

    chunks = []
    for i, doc in enumerate(documents):
        ic(f"Processing document {i+1}/{len(documents)}: {doc.metadata.get('filename', 'Unknown File')}")
        split_docs = markdown_splitter.split_documents([doc])
        for j, chunk in enumerate(split_docs):
            chunk.metadata.update(doc.metadata)
            chunk.metadata["section_title"] = chunk.metadata.get("header_titles", "No Section Title")
            chunks.append(chunk)
        ic(f"Split into {len(split_docs)} chunks.")

    ic(f"Finished chunking. Total chunks created: {len(chunks)}")
    return chunks

# Create simple random vectors for testing
def create_simple_vector(text, vector_dim=384):
    """Create a simple random vector for testing purposes."""
    # Use a seed based on the text to ensure consistency
    seed = sum(ord(c) for c in text)
    np.random.seed(seed)
    # Generate a random vector
    vector = np.random.rand(vector_dim).tolist()
    return vector

# --- 3. Embed and Ingest (store) the chunks into your Weaviate MarkdownChunk collection. ---
def ingest_chunks(client, chunks):
    ic(f"Ingesting {len(chunks)} chunks into Weaviate...")
    vector_dim = 384  # Common dimension for embeddings

    markdown_collection = client.collections.get("MarkdownChunk")

    # Instead of using batch processing, add objects one at a time
        for i, chunk in enumerate(chunks):
        try:
            data_object = {
                "content": chunk.page_content,
                "filepath": chunk.metadata.get("filepath", ""),
                "filename": chunk.metadata.get("filename", ""),
                "directory": chunk.metadata.get("directory", ""),
                "section_title": chunk.metadata.get("section_title", "Unknown Section"),
                "last_modified": chunk.metadata.get("last_modified", ""),
                "file_size_kb": chunk.metadata.get("file_size_kb", 0.0),
                "content_type": chunk.metadata.get("content_type", "text"),  # Add content type
            }
            
            # Create a random vector for the chunk
            vector = create_simple_vector(chunk.page_content, vector_dim)
            
            # Add object with an explicit vector
            markdown_collection.data.insert(
                properties=data_object,
                vector=vector
            )
            
            if (i + 1) % 10 == 0:
                ic(f"Added {i + 1} chunks individually...")
        except Exception as e:
            ic(f"Error adding chunk {i}: {e}")

    ic("Ingestion complete. All chunks sent to Weaviate.")
    try:
        objects_count = len(markdown_collection.query.fetch_objects(limit=10).objects)
        ic(f"Successfully ingested chunks. Collection now has at least {objects_count} objects.")
    except Exception as e:
        ic(f"Error checking object count: {e}")
        ic("Please check your Weaviate Cloud Console to verify ingestion status.")

# --- 4. Search function to test retrieval from Weaviate ---
def search_documents(client, search_term, limit=5, content_type=None):
    ic(f"Searching for: '{search_term}'")
    markdown_collection = client.collections.get("MarkdownChunk")

    # Add content_type filter if specified
    filters = None
    if content_type:
        filters = {
            "path": ["content_type"],
            "operator": "Equal",
            "valueText": content_type
        }

    # Execute query with optional filter
    if filters:
        results = markdown_collection.query.bm25(
            query=search_term,
            limit=limit,
            filters=filters
        )
    else:
    results = markdown_collection.query.bm25(
        query=search_term,
        limit=limit
    )

    ic(f"Found {len(results.objects)} results")
    for i, obj in enumerate(results.objects):
        ic(f"Result {i+1}:")
        ic(f"Filename: {obj.properties['filename']}")
        ic(f"Content type: {obj.properties.get('content_type', 'text')}")
        ic(f"Section title: {obj.properties['section_title']}")
        
        # Display different previews based on content type
        if obj.properties.get('content_type') == 'text':
        content_preview = obj.properties['content'][:100] + "..." if len(obj.properties['content']) > 100 else obj.properties['content']
        ic(f"Content preview: {content_preview}")
        elif obj.properties.get('content_type') == 'image':
            ic(f"Image: {obj.properties['filename']}")
        elif obj.properties.get('content_type') == 'url':
            ic(f"URL: {obj.properties.get('url')}")
            ic(f"Title: {obj.properties.get('url_title', 'N/A')}")
            ic(f"Is MCP: {obj.properties.get('is_mcp', False)}")
        elif obj.properties.get('content_type') == 'binary':
            ic(f"Binary file: {obj.properties['filename']}")
            ic(f"Binary type: {obj.properties.get('binary_type', 'unknown')}")
            ic(f"Binary size: {obj.properties.get('binary_size', 0)/1024/1024:.2f} MB")
        
        ic("---")

    return results.objects

# --- 5. RAG Query function to answer questions based on retrieved documents ---
def rag_query(client, question, num_docs=3, content_type=None):
    ic(f"RAG Query: '{question}'")
    markdown_collection = client.collections.get("MarkdownChunk")
    
    # Add content_type filter if specified
    filters = None
    if content_type:
        filters = {
            "path": ["content_type"],
            "operator": "Equal",
            "valueText": content_type
        }

    # Execute query with optional filter
    if filters:
        results = markdown_collection.query.bm25(
            query=question,
            limit=num_docs,
            filters=filters
        )
    else:
    results = markdown_collection.query.bm25(
        query=question,
        limit=num_docs
    )
    
    if not results.objects:
        return "I couldn't find any relevant information to answer your question."
    
    context = []
    for i, obj in enumerate(results.objects):
        document_info = f"Document: {obj.properties['filename']}"
        if obj.properties['section_title'] and obj.properties['section_title'] != "No Section Title":
            document_info += f", Section: {obj.properties['section_title']}"
        
        content_type = obj.properties.get('content_type', 'text')
        document_info += f", Type: {content_type}"
        
        if content_type == 'text':
        context.append(f"[Document {i+1}] {document_info}\n{obj.properties['content']}\n")
        elif content_type == 'image':
            context.append(f"[Document {i+1}] {document_info}\nImage file: {obj.properties['filename']}\n")
        elif content_type == 'url':
            context.append(f"[Document {i+1}] {document_info}\nURL: {obj.properties.get('url')}\nTitle: {obj.properties.get('url_title', 'N/A')}\nDescription: {obj.properties.get('url_description', 'N/A')}\nIs MCP: {obj.properties.get('is_mcp', False)}\n")
        elif content_type == 'binary':
            context.append(f"[Document {i+1}] {document_info}\nBinary file: {obj.properties['filename']}\nType: {obj.properties.get('binary_type', 'unknown')}\nNotes: {obj.properties.get('binary_notes', 'No notes')}\n")
    
    combined_context = "\n---\n".join(context)
    response = f"Based on the information in your Flight Deal Club project:\n\n"
    response += "Sources:\n"
    for i, obj in enumerate(results.objects):
        response += f"[{i+1}] {obj.properties['filepath']} ({obj.properties.get('content_type', 'text')})\n"
    response += "\nRelevant content from these documents:\n\n"
    response += combined_context
    return response

# --- Main execution block ---
if __name__ == "__main__":
    try:
        # --- CONNECT TO LOCAL WEAVIATE ---
        client = weaviate.connect_to_local(
            host="localhost",
            port=8080,
            # No auth_credentials needed because AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED is 'true' in docker-compose.yml
        )
        ic(client)

        meta = client.get_meta()
        ic("Successfully connected to local Weaviate!")
        ic(f"Weaviate Server Version: {meta.get('version')}")
        ic(f"Active Modules on Server: {[mod for mod in meta.get('modules', {}).keys()]}")

        # Define schema with properties for all supported content types
        properties = [
            # Core properties
            Property(name="content", data_type=DataType.TEXT, description="The textual content or description"),
            Property(name="filepath", data_type=DataType.TEXT, description="Full original file path", index_filterable=True),
            Property(name="filename", data_type=DataType.TEXT, description="Name of the file", index_filterable=True),
            Property(name="directory", data_type=DataType.TEXT, description="The directory path", index_filterable=True),
            Property(name="section_title", data_type=DataType.TEXT, description="The title of the markdown section", index_filterable=True, index_searchable=True),
            Property(name="last_modified", data_type=DataType.DATE, description="Last modification timestamp", index_filterable=True),
            Property(name="file_size_kb", data_type=DataType.NUMBER, description="Size of the file in KB", index_filterable=True),
            Property(name="content_type", data_type=DataType.TEXT, description="Type of content (text, image, url, binary)", index_filterable=True),
            
            # Image-specific properties
            Property(name="image_data", data_type=DataType.BLOB, description="Base64 encoded image data"),
            Property(name="image_format", data_type=DataType.TEXT, description="Image format (jpg, png, etc.)", index_filterable=True),
            
            # URL-specific properties
            Property(name="url", data_type=DataType.TEXT, description="The URL", index_filterable=True, index_searchable=True),
            Property(name="url_title", data_type=DataType.TEXT, description="Title of the webpage", index_searchable=True),
            Property(name="url_description", data_type=DataType.TEXT, description="Description of the webpage", index_searchable=True),
            Property(name="is_mcp", data_type=DataType.BOOLEAN, description="Whether the URL is an MCP service", index_filterable=True),
            
            # Binary file properties
            Property(name="binary_hash", data_type=DataType.TEXT, description="MD5 hash of the binary file", index_filterable=True),
            Property(name="binary_type", data_type=DataType.TEXT, description="Type of binary file", index_filterable=True),
            Property(name="binary_notes", data_type=DataType.TEXT, description="Notes about the binary file", index_searchable=True),
            Property(name="binary_size", data_type=DataType.NUMBER, description="Size of the binary file in bytes", index_filterable=True),
        ]

        if client.collections.exists("MarkdownChunk"):
            ic("MarkdownChunk collection already exists. Deleting and re-creating for a fresh start.")
            client.collections.delete("MarkdownChunk")
        else:
            ic("MarkdownChunk collection does not exist. Creating.")

        client.collections.create(
            name="MarkdownChunk",
            description="A collection for various types of content including text, images, URLs, and binary files",
            vectorizer_config=Configure.Vectorizer.none(),  # Use none vectorizer - we'll provide vectors manually
            properties=properties
        )
        ic("MarkdownChunk collection created successfully.")

        # --- NEW RAG STEPS ---
        loaded_documents = load_markdown_documents(MARKDOWN_DIRECTORY)
        if loaded_documents:
            chunked_documents = chunk_documents(loaded_documents)
            if chunked_documents:
                ingest_chunks(client, chunked_documents)
            else:
                ic("No chunks generated from documents.")
        else:
            ic("No documents loaded from the specified directory.")

    except weaviate.exceptions.WeaviateStartUpError as e:
        ic(f"Weaviate connection failed: {e}")
        ic("Please ensure your local Docker containers are running.")
    except Exception as e:
        ic(f"An unexpected error occurred: {e}")
    finally:
        try:
            if 'client' in locals() and client is not None:
                client.close()
                ic("Connection closed in finally block.")
        except Exception as close_error:
            ic(f"Error closing connection: {close_error}")