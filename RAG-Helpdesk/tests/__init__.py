#!/usr/bin/env python3
# tests/__init__.py
"""
Test package for FDC Memory Bank.

Contains test modules for:
- fdc-memory-api.py: API for interacting with Weaviate
- weaviate-client.py: Client for configuring and accessing Weaviate
- cursor-memory-client.py: CLI client for the Memory Bank API
"""

import os
import sys
from datetime import datetime

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Log test package initialization
print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Initializing FDC Memory Bank test package") 