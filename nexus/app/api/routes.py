"""
API Routes for PDF Comparison Service

This module defines all HTTP endpoints for the service.
"""

import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.comparison import ComparisonResult, HealthCheck, JobStatus
from app.workers.celery_app import celery_app
from app.workers.tasks import compare_pdfs_task

logger = get_logger(__name__)
router = APIRouter()
settings = get_settings()


@router.post("/compare", status_code=status.HTTP_202_ACCEPTED)
async def compare_pdfs(
    file1: UploadFile = File(..., description="First PDF file"),
    file2: UploadFile = File(..., description="Second PDF file"),
    use_llm: bool = Form(default=False, description="Use LLM for analysis"),
    llm_prompt: Optional[str] = Form(default=None, description="Custom LLM prompt"),
    extract_images: bool = Form(default=True, description="Extract images"),
    extract_tables: bool = Form(default=True, description="Extract tables")
):
    """
    Submit a PDF comparison job.

    This endpoint accepts two PDF files and creates an async job to compare them.
    The job ID is returned immediately, and the client can poll for results.

    Args:
        file1: First PDF file
        file2: Second PDF file
        use_llm: Whether to use LLM for analysis
        llm_prompt: Custom prompt for LLM
        extract_images: Whether to extract images
        extract_tables: Whether to extract tables

    Returns:
        Job information with job_id for tracking
    """
    logger.info(
        "compare_request_received",
        file1=file1.filename,
        file2=file2.filename,
        use_llm=use_llm
    )

    # Validate file types
    for file in [file1, file2]:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {file.filename} is not a PDF"
            )

    # Validate file sizes
    for file in [file1, file2]:
        content = await file.read()
        if len(content) > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File {file.filename} exceeds maximum size of {settings.max_file_size_mb}MB"
            )
        await file.seek(0)  # Reset file pointer

    try:
        # Generate job ID
        job_id = uuid.uuid4().hex

        # Save uploaded files temporarily
        temp_dir = Path(settings.temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)

        pdf1_path = temp_dir / f"{job_id}_1.pdf"
        pdf2_path = temp_dir / f"{job_id}_2.pdf"

        # Write files
        with open(pdf1_path, "wb") as f:
            f.write(await file1.read())

        with open(pdf2_path, "wb") as f:
            f.write(await file2.read())

        logger.info(
            "files_saved",
            job_id=job_id,
            pdf1=str(pdf1_path),
            pdf2=str(pdf2_path)
        )

        # Submit Celery task
        task = compare_pdfs_task.apply_async(
            kwargs={
                "job_id": job_id,
                "pdf1_path": str(pdf1_path),
                "pdf2_path": str(pdf2_path),
                "use_llm": use_llm,
                "llm_prompt": llm_prompt,
                "extract_images": extract_images,
                "extract_tables": extract_tables
            },
            task_id=job_id
        )

        logger.info(
            "task_submitted",
            job_id=job_id,
            task_id=task.id
        )

        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "job_id": job_id,
                "status": "pending",
                "message": "Comparison job submitted successfully",
                "poll_url": f"/api/v1/jobs/{job_id}",
                "results_url": f"/api/v1/results/{job_id}"
            }
        )

    except Exception as e:
        logger.error(
            "compare_request_failed",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit comparison job: {str(e)}"
        )


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """
    Get the status of a comparison job.

    Args:
        job_id: Job identifier

    Returns:
        Job status information
    """
    logger.debug("job_status_requested", job_id=job_id)

    try:
        # Get task result
        task_result = celery_app.AsyncResult(job_id)

        # Map Celery state to our status
        if task_result.state == "PENDING":
            status_enum = "pending"
            message = "Job is pending"
            progress = 0
        elif task_result.state == "PROCESSING":
            status_enum = "processing"
            meta = task_result.info or {}
            message = meta.get("current_step", "Processing")
            progress = meta.get("progress", 50)
        elif task_result.state == "SUCCESS":
            status_enum = "completed"
            message = "Job completed successfully"
            progress = 100
        elif task_result.state == "FAILURE":
            status_enum = "failed"
            message = f"Job failed: {str(task_result.info)}"
            progress = 0
        else:
            status_enum = task_result.state.lower()
            message = f"Job status: {task_result.state}"
            progress = 50

        return JobStatus(
            job_id=job_id,
            status=status_enum,
            progress_percentage=progress,
            message=message,
            current_step=task_result.info.get("current_step") if isinstance(task_result.info, dict) else None
        )

    except Exception as e:
        logger.error(
            "job_status_failed",
            job_id=job_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}"
        )


@router.get("/results/{job_id}", response_model=ComparisonResult)
async def get_comparison_results(job_id: str):
    """
    Get the results of a completed comparison job.

    Args:
        job_id: Job identifier

    Returns:
        Complete comparison results

    Raises:
        HTTPException: If job not found, still processing, or failed
    """
    logger.info("results_requested", job_id=job_id)

    try:
        task_result = celery_app.AsyncResult(job_id)

        if task_result.state == "PENDING":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found or not yet started"
            )

        if task_result.state in ["PROCESSING", "STARTED"]:
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail="Job is still processing. Check job status first."
            )

        if task_result.state == "FAILURE":
            error_msg = str(task_result.info)
            logger.error("job_failed", job_id=job_id, error=error_msg)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Job failed: {error_msg}"
            )

        if task_result.state == "SUCCESS":
            result_data = task_result.result
            logger.info(
                "results_retrieved",
                job_id=job_id,
                status=result_data.get("status")
            )
            return ComparisonResult(**result_data)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected job state: {task_result.state}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "results_retrieval_failed",
            job_id=job_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve results: {str(e)}"
        )


@router.get("/health", response_model=HealthCheck)
async def health_check():
    """
    Health check endpoint.

    Returns:
        Service health status
    """
    try:
        # Check Redis connection
        redis_connected = False
        try:
            celery_app.connection().ensure_connection(max_retries=1)
            redis_connected = True
        except Exception as e:
            logger.warning("redis_health_check_failed", error=str(e))

        # Check Celery workers
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        worker_count = len(stats) if stats else 0

        # Check LLM configuration
        llm_configured = settings.validate_llm_config()

        return HealthCheck(
            status="healthy" if redis_connected else "degraded",
            version=settings.api_version,
            redis_connected=redis_connected,
            celery_workers=worker_count,
            llm_configured=llm_configured
        )

    except Exception as e:
        logger.error("health_check_failed", error=str(e))
        return HealthCheck(
            status="unhealthy",
            version=settings.api_version,
            redis_connected=False,
            celery_workers=0,
            llm_configured=False
        )


@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    """
    Cancel a running job.

    Args:
        job_id: Job identifier

    Returns:
        Cancellation confirmation
    """
    logger.info("job_cancellation_requested", job_id=job_id)

    try:
        celery_app.control.revoke(job_id, terminate=True)

        return {
            "job_id": job_id,
            "status": "cancelled",
            "message": "Job cancellation requested"
        }

    except Exception as e:
        logger.error("job_cancellation_failed", job_id=job_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel job: {str(e)}"
        )
