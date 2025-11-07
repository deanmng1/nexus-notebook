# PDF Comparison Service

A scalable Python service for comparing PDF documents, designed specifically for tax content and other document comparison needs. Features advanced PDF to Markdown conversion and comprehensive diff analysis.

## Features

- **PDF Processing**: Convert PDFs to Markdown using pymupdf4llm for optimal comparison
- **Intelligent Diff Analysis**: Find differences between two PDFs with precise citations
- **Citation Support**: Provides proof and references for all identified differences
- **Queue System**: Redis-backed Celery task queue for scalability
- **Image Handling**: Extracts and compares images from PDFs
- **Table Extraction**: Preserves tables in Markdown format for accurate comparison
- **Error Handling**: Comprehensive error handling and logging
- **Production Ready**: Docker support, health checks, and monitoring
- **LLM Ready**: Architecture supports future LLM integration (currently placeholder)

## Architecture

```
├── app/
│   ├── api/                 # FastAPI endpoints
│   ├── core/                # Configuration and settings
│   ├── services/            # Business logic
│   │   ├── pdf_processor.py       # PDF to Markdown conversion
│   │   ├── diff_service.py        # Diff comparison logic
│   │   ├── llm_service.py         # LLM integration
│   │   └── queue_service.py       # Celery task management
│   ├── models/              # Data models
│   ├── utils/               # Utility functions
│   └── workers/             # Celery workers
├── tests/                   # Test suite
├── docker/                  # Docker configuration
└── outputs/                 # Output directory for processed files
```

## Technology Stack

- **FastAPI**: High-performance async API framework
- **Celery**: Distributed task queue
- **Redis**: Message broker and caching
- **PyMuPDF (fitz)**: PDF processing
- **pymupdf4llm**: Advanced PDF to Markdown conversion
- **difflib**: Text comparison
- **Pillow**: Image processing

## Quick Start

### Prerequisites

- Python 3.11+
- Redis server
- Docker (optional)

### Installation

1. Clone the repository:
```bash
cd nexus
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration (LLM settings are optional)
```

5. Start Redis:
```bash
# Using Docker
docker run -d -p 6379:6379 redis:alpine

# Or using local Redis
redis-server
```

6. Start Celery worker:
```bash
celery -A app.workers.celery_worker worker --loglevel=info
```

7. Start the API server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker Deployment

```bash
docker-compose up -d
```

## API Usage

### Compare Two PDFs

```bash
curl -X POST "http://localhost:8000/api/v1/compare" \
  -F "file1=@document1.pdf" \
  -F "file2=@document2.pdf"
```

### Check Job Status

```bash
curl "http://localhost:8000/api/v1/jobs/{job_id}"
```

### Get Comparison Results

```bash
curl "http://localhost:8000/api/v1/results/{job_id}"
```

## API Endpoints

- `POST /api/v1/compare` - Submit PDF comparison job
- `GET /api/v1/jobs/{job_id}` - Get job status
- `GET /api/v1/results/{job_id}` - Get comparison results
- `GET /health` - Health check endpoint
- `GET /metrics` - Service metrics

## Configuration

Key environment variables:

```env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# LLM Configuration (OPTIONAL - not currently implemented)
# Future feature: LLM-powered analysis
# LLM_PROVIDER=openai  # or anthropic
# OPENAI_API_KEY=your_key_here

# Processing Configuration
MAX_FILE_SIZE_MB=50
SUPPORTED_FORMATS=pdf
CELERY_TASK_TIMEOUT=600

# Logging
LOG_LEVEL=INFO
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test
pytest tests/test_pdf_processor.py -v
```

## Performance Considerations

- PDFs are processed asynchronously using Celery
- Redis caching for repeated comparisons
- Chunked processing for large PDFs
- Connection pooling for LLM API calls
- Rate limiting to prevent overload

## Error Handling

The service includes comprehensive error handling:
- Invalid PDF format detection
- Corrupted file handling
- LLM API failure fallbacks
- Queue overflow protection
- Graceful degradation

## Security

- File type validation
- Size limits
- Secure temporary file handling
- API key encryption
- Rate limiting

## Monitoring

Built-in metrics for:
- Request count and latency
- Queue depth
- Processing success/failure rates
- LLM API usage
- Cache hit rates

## Contributing

Contributions are welcome! Please follow the coding standards and include tests.

## License

MIT License
