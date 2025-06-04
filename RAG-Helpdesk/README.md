# FDC Memory Bank

A versatile memory storage and retrieval system using Weaviate for embedding, storing, and querying various types of content including text, images, URLs, and binary files.

## Features

- Store and retrieve different types of content:
  - **Text**: Plain text and markdown documents
  - **Images**: Store and retrieve images in various formats (jpg, png, gif, webp, svg, etc.)
  - **URLs**: Store URLs with automatic metadata extraction (title, description) and MCP service detection
  - **Binary files**: Store references to binary files with custom notes and metadata

- Flexible querying by content type or across all content
- Simple API for integration with various clients
- Command-line interface for common operations
- Runs as a system service for persistent availability

## Setup

### Prerequisites

- Python 3.9+
- Docker and Docker Compose
- Internet connection for the initial setup

### Installation

1. Clone this repository:
```bash
git clone https://github.com/your-username/fdc-memory-bank.git
cd fdc-memory-bank
```

2. Create and activate a virtual environment:
```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install the required packages:
```bash
   pip install -r requirements.txt
```

4. Start the Weaviate service using Docker Compose:
```bash
docker-compose up -d
```

5. Initialize the Weaviate schema:
```bash
python weaviate-client.py
```

6. Set up your API keys and configuration in a `.env` file:
```
FDC_API_KEY=your-secure-api-key
FDC_API_PORT=5000
MARKDOWN_DIRECTORY=/home/oem/Dokumente/_Python/100_Days/040/FlightDealClub/v_3/FDC_MemoryBank
```

7. Install the service to run at system startup:
```bash
./install_service.sh
```

## Usage

### API Endpoints

The Memory Bank API provides the following endpoints:

- `GET /health` - Check the API health
- `POST /query` - Query the memory bank
- `POST /add` - Add content to the memory bank
- `PUT /update` - Update existing content
- `DELETE /delete` - Delete content

All endpoints except `/health` require API key authentication via the `X-API-Key` header.

### Command Line Client

The `cursor-memory-client.py` script provides a convenient way to interact with the Memory Bank:

```bash
# Query the memory bank
python cursor-memory-client.py query "What is the status of the flight deal project?" --limit=5 --type=text

# Add text content
python cursor-memory-client.py add-text "This is important information to remember" --title="Important Note"

# Add an image
python cursor-memory-client.py add-image /path/to/image.jpg --title="Project Diagram"

# Add a URL
python cursor-memory-client.py add-url https://example.com/article --title="Reference Article"

# Add a binary file
python cursor-memory-client.py add-binary /path/to/program.exe --notes="Useful utility" --title="CLI Tool"

# Update existing content
python cursor-memory-client.py update 12345-uuid-67890 "Updated content" --title="New Title" --type=text

# Delete content
python cursor-memory-client.py delete 12345-uuid-67890
```

### Python API

You can also use the Memory Bank directly from your Python code:

```python
from cursor_memory_client import query_memory_bank, add_to_memory_bank, add_image_to_memory_bank, add_url_to_memory_bank, add_binary_to_memory_bank

# Query the memory bank
results = query_memory_bank("project status", limit=5, content_type="text")

# Add text content
add_to_memory_bank("Important information", filename="note.md", section_title="Project Notes")

# Add an image
add_image_to_memory_bank("/path/to/image.jpg", section_title="Project Diagram")

# Add a URL
add_url_to_memory_bank("https://example.com", section_title="Reference")

# Add a binary file
add_binary_to_memory_bank("/path/to/file.exe", notes="Useful utility", section_title="Tools")
```

## Content Types

### Text

Text content is stored as plain text or markdown. Longer content is automatically chunked for better retrieval.

### Images

Supported image formats:
- JPEG/JPG
- PNG
- GIF
- BMP
- WebP
- SVG

Images are stored as base64-encoded data with metadata.

### URLs

URLs are stored with automatically extracted metadata:
- Page title
- Description
- Domain information
- MCP service detection (Management Control Panel services are automatically flagged)

### Binary Files

Binary files are stored with:
- File path reference
- MD5 hash for integrity verification
- File type detection
- Custom notes
- Size information

## Testing

The Memory Bank includes a comprehensive test suite to verify all functionality:

```bash
# Run all tests
python tests/run_tests.py

# Run tests for a specific module
python tests/run_tests.py -m api     # Test the API only
python tests/run_tests.py -m client  # Test the client only
python tests/run_tests.py -m weaviate # Test the Weaviate client only

# Run tests with increased verbosity
python tests/run_tests.py -v -s

# Generate HTML test report
python tests/run_tests.py --html
```

The test suite uses pytest and includes:
- Unit tests for all core functions
- Integration tests for API endpoints
- Tests for different content types (text, images, URLs, binary files)
- Logging with timestamps to track test execution

Test logs are written to `fdc_test_log.txt` and detailed HTML reports can be generated with the `--html` flag.

## Troubleshooting

### Weaviate Connection Issues

If you encounter connection issues to Weaviate:

1. Check if the Docker containers are running:
```bash
docker ps
```

2. Restart the Weaviate container:
```bash
docker-compose restart weaviate
```

3. Check the Weaviate logs:
```bash
docker-compose logs weaviate
```

### API Service Issues

To check the status of the Memory Bank API service:

```bash
sudo systemctl status fdc-memory-service
```

To restart the service:

```bash
sudo systemctl restart fdc-memory-service
```

To view service logs:

```bash
sudo journalctl -u fdc-memory-service
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

# Weaviate Web Interface

This project provides a simple, lean web interface for interacting with your local Weaviate database. It is designed for:

- Viewing statistics about your Weaviate collections (e.g., number of entries/vectors)
- Adding new entries (documents, images, binaries, code, JSON, etc.)
- Deleting entries by UUID

## Structure

- `webapp/app.py`: Main Flask web server. Handles routes for stats, adding, and deleting entries.
- `webapp/templates/index.html`: The main HTML interface. Includes forms for adding and deleting entries, and displays database stats.
- `requirements.txt`: Python dependencies for the web server (Flask, weaviate-client, python-dotenv).
- (Planned) `webapp/weaviate_service.py`: Will encapsulate all Weaviate client logic for stats, add, delete, and search operations.

## Features

- **Statistics**: See the total number of objects in the `MarkdownChunk` collection (more stats coming soon).
- **Add Entry**: Upload text or files (images, binaries, code, JSON, etc.) with metadata. Content type and tags supported. (Currently, only prints to console; ingestion logic to be implemented next.)
- **Delete Entry**: Remove entries by Weaviate UUID. (Currently, only prints to console; deletion logic to be implemented next.)

## Setup & Usage

1. **Start Weaviate**
   - Make sure your Weaviate instance is running (see `docker-compose.yml`).
   - Example: `docker-compose up -d`

2. **Set up Python environment**
   - (Recommended) Create a virtual environment:
     ```bash
     python3 -m venv .venv-webapp
     source .venv-webapp/bin/activate
     ```
   - Install dependencies:
     ```bash
     pip install -r requirements.txt
     ```

3. **Run the web server**
   - From the project root:
     ```bash
     python webapp/app.py
     ```
   - Open your browser to [http://localhost:5001](http://localhost:5001)
   

**Summ of the metrics to call and get from Weaviate database**

---

| Endpoint / Feature                   | Description                                                                 | Example Call / Path              | Data Returned / Monitored             |
|--------------------------------------|-----------------------------------------------------------------------------|----------------------------------|---------------------------------------|
| `/v1/graphql`                        | GraphQL API for flexible data queries and manipulation                      | `POST /v1/graphql`               | Query/Mutation results                |
| `/v1/objects`                        | CRUD operations on objects (Create, Read, Update, Delete)                   | `GET /v1/objects`                | Object lists, single objects          |
| `/v1/batch/objects`                  | Batch import and update of objects                                          | `POST /v1/batch/objects`         | Batch status, errors                  |
| `/v1/schema`                         | Schema definition and querying                                              | `GET /v1/schema`                 | Current schema                        |
| `/v1/classifications`                | Start and monitor classification jobs                                       | `POST /v1/classifications`       | Job status, results                   |
| `/v1/backup`                         | Backup and restore operations                                               | `POST /v1/backup`                | Backup status, restore status         |
| `/v1/nodes`                          | Cluster and node information                                                | `GET /v1/nodes`                  | Node status, cluster info             |
| `/v1/.well-known/ready`              | Readiness probe for health checks                                           | `GET /v1/.well-known/ready`      | HTTP status (200 = ready)             |
| `/v1/.well-known/live`               | Liveness probe for health checks                                            | `GET /v1/.well-known/live`       | HTTP status (200 = alive)             |
| `/v1/modules`                        | Information about loaded modules                                            | `GET /v1/modules`                | Module status, configuration          |
| `/v1/meta`                           | Metadata about the Weaviate instance                                        | `GET /v1/meta`                   | Version, configuration, uptime        |
| `/metrics` (e.g., port 2112)         | Prometheus-compatible metrics (performance, memory, latency, etc.)          | `GET /metrics`                   | Metric data in Prometheus format      |

**Note:**  
- Actual paths may vary slightly depending on Weaviate version and configuration.
- All endpoints are accessible via `localhost`, e.g., `http://localhost:8080/v1/objects` (default port 8080).
- For Prometheus metrics, a separate port (e.g., 2112) may be used and the feature must be enabled.

This table provides a quick overview of the main API endpoints and metrics you can directly query from a Weaviate instance.

---

## Next Steps

- Move Weaviate logic into `webapp/weaviate_service.py` for better modularity.
- Implement actual add/delete/search operations.
- Enhance UI to list/search entries and show more detailed stats.
- Improve error handling and user feedback.

---

*This README was generated by the AI assistant based on the current project structure and development plan.* 