#!/usr/bin/env python3
# 040/FlightDealClub/Weaviate/weaviate-query.py

import weaviate
import os
from weaviate.auth import AuthApiKey
from icecream import ic
import argparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Enable icecream debugging ---
ic.enable()

# --- WEAVIATE CLOUD CONNECTION DETAILS ---
# WCS_URL = os.getenv("WCS_URL") # No longer needed for local
# WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY") # No longer needed for local

# Validate that required environment variables are set
# if not WCS_URL or not WEAVIATE_API_KEY: # Validation no longer needed for these vars
#     raise ValueError("Missing required environment variables. Please check your .env file.")

def query_weaviate(question, num_results=3):
    """
    Query the Weaviate database with a natural language question
    and return relevant documents from the MemoryBank.
    """
    client = None  # Initialize client to None for robust finally block
    try:
        # Connect to Local Weaviate
        client = weaviate.connect_to_local(
            host="localhost",
            port=8080,
        )
        ic("Connected to local Weaviate for querying.")
        
        # Get the MarkdownChunk collection
        markdown_collection = client.collections.get("MarkdownChunk")
        
        # Search for relevant documents using semantic (vector) search
        results = markdown_collection.query.near_text(
            query=question,
            limit=num_results
            # target_vector="content" # Usually not needed if 'content' is the only vectorizable prop or default
        )
        
        # Print the results
        print(f"\n\033[1m🔍 Query: '{question}'\033[0m\n")
        
        if not results.objects:
            print("No relevant documents found.")
            return
        
        print(f"\033[1m📄 Found {len(results.objects)} relevant documents:\033[0m\n")
        
        for i, obj in enumerate(results.objects):
            print(f"\033[1m📑 Result {i+1}:\033[0m")
            print(f"  \033[94mFile:\033[0m {obj.properties['filename']}")
            print(f"  \033[94mPath:\033[0m {obj.properties['filepath']}")
            if obj.properties['section_title'] and obj.properties['section_title'] != "No Section Title":
                print(f"  \033[94mSection:\033[0m {obj.properties['section_title']}")
            
            # Print the content
            print("\n  \033[95mContent:\033[0m")
            print(f"  {obj.properties['content'].replace(chr(10), chr(10) + '  ')}\n")
            print("-" * 80)
    
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        # Ensure connection is closed
        if 'client' in locals() and client is not None:
            client.close()

def main():
    """Main function to handle command line arguments and query Weaviate"""
    parser = argparse.ArgumentParser(description="Query the Flight Deal Club knowledge base")
    parser.add_argument(
        "question", 
        nargs="?", 
        default=None, 
        help="Your question about the Flight Deal Club project"
    )
    parser.add_argument(
        "-n", "--num-results", 
        type=int, 
        default=3, 
        help="Number of results to return (default: 3)"
    )
    
    args = parser.parse_args()
    
    # If no question was provided, enter interactive mode
    if args.question is None:
        print("\033[1m🤖 Flight Deal Club Knowledge Base Query Tool\033[0m")
        print("Type your questions about the project, or 'quit' to exit.\n")
        
        while True:
            question = input("\033[93m💬 Your question: \033[0m")
            if question.lower() in ('quit', 'exit', 'q'):
                print("Goodbye! 👋")
                break
                
            if not question.strip():
                continue
                
            query_weaviate(question, args.num_results)
    else:
        # Single question mode
        query_weaviate(args.question, args.num_results)

if __name__ == "__main__":
    main() 