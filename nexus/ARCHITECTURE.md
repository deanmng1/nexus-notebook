# Architecture Overview

## System Design

The PDF Comparison Service is built as a scalable, microservices-oriented system with the following components:

### Components

```
┌─────────────────┐
│   FastAPI App   │ ← HTTP REST API
└────────┬────────┘
         │
    ┌────▼────┐
    │  Redis  │ ← Message Broker & Cache
    └────┬────┘
         │
    ┌────▼──────────┐
    │ Celery Workers │ ← Async Task Processing
    └────┬──────────┘
         │
    ┌────▼────────────────────────────┐
    │ PDF Processor → Diff → LLM      │ ← Business Logic
    └─────────────────────────────────┘
```

## Data Flow

### 1. PDF Submission
```
User → FastAPI → Save PDFs → Queue Task → Return Job ID
```

### 2. Processing Pipeline
```
Celery Worker → PDF to Markdown → Diff Analysis → LLM Analysis → Store Results
```

### 3. Result Retrieval
```
User → FastAPI → Fetch from Celery → Return Results
```

## Core Services

### PDF Processor (`app/services/pdf_processor.py`)
- **Purpose**: Convert PDFs to Markdown using pymupdf4llm
- **Features**:
  - Multi-column layout detection
  - Table extraction
  - Image extraction
  - Header/footer handling
  - Metadata extraction

### Diff Service (`app/services/diff_service.py`)
- **Purpose**: Compare two Markdown documents
- **Features**:
  - Line-by-line diff using Python's difflib
  - Similarity scoring
  - Context extraction
  - Proof/citation generation
  - Categorization (added, removed, modified)

### LLM Service (`app/services/llm_service.py`)
- **Purpose**: AI-powered document analysis
- **Features**:
  - Multi-provider support (OpenAI, Anthropic)
  - Importance scoring
  - Key changes identification
  - Summary generation
  - Recommendations

### Queue Service (Celery)
- **Purpose**: Async task processing
- **Features**:
  - Distributed task execution
  - Retry logic
  - Progress tracking
  - Result caching

## API Endpoints

### POST `/api/v1/compare`
Submit a comparison job
- **Input**: 2 PDF files + options
- **Output**: Job ID
- **Status**: 202 Accepted

### GET `/api/v1/jobs/{job_id}`
Check job status
- **Input**: Job ID
- **Output**: Status, progress, current step
- **Status**: 200 OK

### GET `/api/v1/results/{job_id}`
Get comparison results
- **Input**: Job ID
- **Output**: Complete ComparisonResult
- **Status**: 200 OK (if complete), 202 (if processing)

### GET `/api/v1/health`
Health check
- **Output**: Service status, Redis status, worker count
- **Status**: 200 OK

## Data Models

### ComparisonResult
```python
{
    "job_id": str,
    "status": "completed" | "processing" | "failed",
    "source_metadata": PDFMetadata,
    "target_metadata": PDFMetadata,
    "total_differences": int,
    "similarity_percentage": float,
    "differences": [DiffSection],
    "llm_summary": str,
    "llm_key_changes": [str],
    "llm_recommendations": [str]
}
```

### DiffSection
```python
{
    "diff_type": "added" | "removed" | "modified",
    "source_text": str,
    "target_text": str,
    "context_before": str,
    "context_after": str,
    "line_number": int,
    "similarity_score": float,
    "importance_score": float,  # from LLM
    "llm_analysis": str,        # from LLM
    "proof": str                # citation
}
```

## Scalability Considerations

### Horizontal Scaling
- **API**: Multiple FastAPI instances behind load balancer
- **Workers**: Scale Celery workers independently
- **Redis**: Redis Cluster for high availability

### Performance Optimizations
- **Caching**: Result caching in Redis
- **Chunking**: Process large PDFs in chunks
- **Streaming**: Stream results for large outputs
- **Rate Limiting**: Prevent API abuse

### Resource Management
- **Memory**: Worker memory limits
- **CPU**: Concurrency controls
- **Storage**: Temporary file cleanup

## Security

### Input Validation
- File type verification
- File size limits
- Malicious PDF detection

### API Security
- Optional API key authentication
- CORS configuration
- Rate limiting

### Data Privacy
- Temporary file cleanup
- No persistent storage of user data
- Secure API key handling

## Monitoring & Logging

### Structured Logging
- JSON logs for production
- Human-readable logs for development
- Log levels: DEBUG, INFO, WARNING, ERROR

### Metrics
- Request count
- Processing time
- Queue depth
- Success/failure rates
- LLM API usage

### Health Checks
- API health endpoint
- Redis connection
- Worker availability
- LLM service status

## Error Handling

### Retry Logic
- Automatic retries for transient failures
- Exponential backoff
- Maximum retry limits

### Fallbacks
- LLM analysis optional (graceful degradation)
- Default to non-LLM analysis if LLM fails

### User Communication
- Clear error messages
- Status updates
- Progress tracking

## Future Enhancements

1. **Database Integration**: PostgreSQL for persistent job storage
2. **WebSocket Support**: Real-time progress updates
3. **Batch Processing**: Compare multiple PDFs at once
4. **Advanced Diffing**: Semantic diff, not just text diff
5. **More LLM Providers**: Add support for more providers
6. **Export Formats**: PDF, Word, HTML outputs
7. **User Management**: Authentication and authorization
8. **Webhooks**: Notify when jobs complete
