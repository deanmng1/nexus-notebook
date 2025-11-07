# Quick Start Guide

Get the PDF Comparison Service up and running in 5 minutes!

## Prerequisites

- Python 3.11+ installed
- Redis installed (or Docker)
- OpenAI or Anthropic API key (for LLM features)

## Option 1: Docker (Recommended)

### 1. Set up environment

```bash
cp .env.example .env
# Edit .env and add your API keys
nano .env
```

### 2. Start all services

```bash
docker-compose up
```

That's it! The service is now running at:
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Flower (monitoring): http://localhost:5555

## Option 2: Local Development

### 1. Run setup script

```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

### 2. Configure environment

```bash
# Edit .env and add your API keys
nano .env
```

Required settings:
```env
# At minimum, set ONE of these:
OPENAI_API_KEY=sk-your-key-here
# OR
ANTHROPIC_API_KEY=sk-ant-your-key-here

# And configure the provider:
LLM_PROVIDER=openai  # or anthropic
LLM_MODEL=gpt-4-turbo-preview  # or claude-3-opus-20240229
```

### 3. Start Redis

```bash
# Using Docker
docker run -d -p 6379:6379 redis:alpine

# Or local Redis
redis-server
```

### 4. Start the services

Option A - Use the start script:
```bash
chmod +x scripts/start-dev.sh
./scripts/start-dev.sh
```

Option B - Manual start:
```bash
# Terminal 1: Start Celery worker
celery -A app.workers.celery_app worker --loglevel=info

# Terminal 2: Start API server
uvicorn app.main:app --reload
```

## Test the Service

### 1. Check health

```bash
curl http://localhost:8000/api/v1/health
```

### 2. Compare two PDFs

```bash
curl -X POST "http://localhost:8000/api/v1/compare" \
  -F "file1=@document1.pdf" \
  -F "file2=@document2.pdf" \
  -F "use_llm=true"
```

Response:
```json
{
  "job_id": "abc123...",
  "status": "pending",
  "poll_url": "/api/v1/jobs/abc123...",
  "results_url": "/api/v1/results/abc123..."
}
```

### 3. Check job status

```bash
curl "http://localhost:8000/api/v1/jobs/{job_id}"
```

### 4. Get results

```bash
curl "http://localhost:8000/api/v1/results/{job_id}"
```

## Using the Interactive Docs

Visit http://localhost:8000/docs for the interactive Swagger UI where you can:
- Test all endpoints
- See request/response schemas
- Upload files directly
- View example responses

## Example: Python Client

```python
import requests
import time

API_URL = "http://localhost:8000/api/v1"

# 1. Submit comparison job
with open("doc1.pdf", "rb") as f1, open("doc2.pdf", "rb") as f2:
    response = requests.post(
        f"{API_URL}/compare",
        files={"file1": f1, "file2": f2},
        data={"use_llm": "true"}
    )
    job_id = response.json()["job_id"]
    print(f"Job submitted: {job_id}")

# 2. Poll for completion
while True:
    status_response = requests.get(f"{API_URL}/jobs/{job_id}")
    status = status_response.json()["status"]
    print(f"Status: {status}")

    if status == "completed":
        break
    elif status == "failed":
        print("Job failed!")
        exit(1)

    time.sleep(2)

# 3. Get results
results = requests.get(f"{API_URL}/results/{job_id}").json()
print(f"Found {results['total_differences']} differences")
print(f"Similarity: {results['similarity_percentage']}%")
print(f"\nSummary: {results['llm_summary']}")
```

## Troubleshooting

### Redis Connection Error
```
Error: Cannot connect to Redis
```
**Solution**: Make sure Redis is running
```bash
docker run -d -p 6379:6379 redis:alpine
```

### Import Error: pymupdf4llm
```
ModuleNotFoundError: No module named 'pymupdf4llm'
```
**Solution**: Install dependencies
```bash
pip install -r requirements.txt
```

### LLM API Error
```
Error: LLM analysis failed
```
**Solution**: Check your API key in .env
```bash
# For OpenAI
OPENAI_API_KEY=sk-your-actual-key

# For Anthropic
ANTHROPIC_API_KEY=sk-ant-your-actual-key
```

### Worker Not Processing
```
Task stays in 'pending' state
```
**Solution**: Make sure Celery worker is running
```bash
celery -A app.workers.celery_app worker --loglevel=info
```

## Configuration Tips

### For Tax Documents
```env
# Use higher quality LLM
LLM_MODEL=gpt-4-turbo-preview

# Enable all features
EXTRACT_IMAGES=True
EXTRACT_TABLES=True

# More context for diffs
DIFF_CONTEXT_LINES=5
```

### For Performance
```env
# Increase workers
CELERY_WORKER_CONCURRENCY=8

# Larger files
MAX_FILE_SIZE_MB=100

# More aggressive caching
CACHE_TTL_SECONDS=7200
```

### For Development
```env
DEBUG=True
LOG_LEVEL=DEBUG
LOG_FORMAT=text  # Human-readable logs
```

## Next Steps

1. Read [README.md](README.md) for detailed documentation
2. Read [ARCHITECTURE.md](ARCHITECTURE.md) to understand the system
3. Check out the API docs at http://localhost:8000/docs
4. Run tests: `pytest`

## Getting Help

- Check the logs: `./logs/app.log`
- Enable debug mode: `DEBUG=True` in .env
- View worker status: http://localhost:5555 (if Flower is running)
- Check health: `curl http://localhost:8000/api/v1/health`

## Common Use Cases

### Compare Tax Documents
```bash
curl -X POST "http://localhost:8000/api/v1/compare" \
  -F "file1=@tax_return_2023.pdf" \
  -F "file2=@tax_return_2024.pdf" \
  -F "use_llm=true" \
  -F "extract_tables=true"
```

### Quick Diff Without LLM
```bash
curl -X POST "http://localhost:8000/api/v1/compare" \
  -F "file1=@old.pdf" \
  -F "file2=@new.pdf" \
  -F "use_llm=false"
```

### Compare with Custom Prompt
```bash
curl -X POST "http://localhost:8000/api/v1/compare" \
  -F "file1=@doc1.pdf" \
  -F "file2=@doc2.pdf" \
  -F "use_llm=true" \
  -F "llm_prompt=Focus on numerical changes and tax implications"
```

Enjoy using the PDF Comparison Service! 🚀
