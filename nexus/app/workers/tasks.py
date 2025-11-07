"""
Celery Tasks for PDF Comparison

This module defines the main async tasks for processing PDF comparisons.
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, any

from celery import Task

from app.core.logging import get_logger
from app.models.comparison import ComparisonResult, ComparisonStatus
from app.services.diff_service import DiffService
from app.services.llm_service import LLMService
from app.services.pdf_processor import PDFProcessor
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


class ComparisonTask(Task):
    """Base task class with shared setup."""

    _pdf_processor = None
    _diff_service = None
    _llm_service = None

    @property
    def pdf_processor(self) -> PDFProcessor:
        """Lazy-load PDF processor."""
        if self._pdf_processor is None:
            self._pdf_processor = PDFProcessor()
        return self._pdf_processor

    @property
    def diff_service(self) -> DiffService:
        """Lazy-load diff service."""
        if self._diff_service is None:
            self._diff_service = DiffService()
        return self._diff_service

    @property
    def llm_service(self) -> LLMService:
        """Lazy-load LLM service."""
        if self._llm_service is None:
            self._llm_service = LLMService()
        return self._llm_service


@celery_app.task(
    bind=True,
    base=ComparisonTask,
    name="compare_pdfs",
    max_retries=3,
    default_retry_delay=60
)
def compare_pdfs_task(
    self,
    job_id: str,
    pdf1_path: str,
    pdf2_path: str,
    use_llm: bool = False,
    llm_prompt: str = None,
    extract_images: bool = True,
    extract_tables: bool = True
) -> Dict[str, any]:
    """
    Main task for comparing two PDF documents.

    This task orchestrates the entire comparison process:
    1. Convert PDFs to Markdown
    2. Compare the Markdown texts
    3. Optionally analyze with LLM
    4. Generate comprehensive results

    Args:
        job_id: Unique job identifier
        pdf1_path: Path to first PDF
        pdf2_path: Path to second PDF
        use_llm: Whether to use LLM analysis
        llm_prompt: Custom LLM prompt
        extract_images: Whether to extract images
        extract_tables: Whether to extract tables

    Returns:
        Dictionary with comparison results
    """
    start_time = datetime.utcnow()

    logger.info(
        "comparison_task_started",
        job_id=job_id,
        pdf1=pdf1_path,
        pdf2=pdf2_path,
        use_llm=use_llm
    )

    # Update task state
    self.update_state(
        state="PROCESSING",
        meta={
            "job_id": job_id,
            "status": "processing",
            "current_step": "Converting PDFs to Markdown",
            "progress": 10
        }
    )

    try:
        # Step 1: Convert PDFs to Markdown
        logger.info("converting_pdf1", job_id=job_id, pdf=pdf1_path)

        pdf1_md, pdf1_md_path, pdf1_chunks = self.pdf_processor.pdf_to_markdown(
            Path(pdf1_path),
            extract_images=extract_images,
            extract_tables=extract_tables,
            page_chunks=True  # Get page-by-page chunks for better citation
        )

        self.update_state(
            state="PROCESSING",
            meta={
                "job_id": job_id,
                "status": "processing",
                "current_step": "Converting second PDF",
                "progress": 30
            }
        )

        logger.info("converting_pdf2", job_id=job_id, pdf=pdf2_path)

        pdf2_md, pdf2_md_path, pdf2_chunks = self.pdf_processor.pdf_to_markdown(
            Path(pdf2_path),
            extract_images=extract_images,
            extract_tables=extract_tables,
            page_chunks=True
        )

        # Extract metadata
        pdf1_metadata = self.pdf_processor.extract_metadata(Path(pdf1_path))
        pdf2_metadata = self.pdf_processor.extract_metadata(Path(pdf2_path))

        self.update_state(
            state="PROCESSING",
            meta={
                "job_id": job_id,
                "status": "processing",
                "current_step": "Comparing documents",
                "progress": 50
            }
        )

        # Step 2: Compare the Markdown documents
        logger.info("comparing_markdowns", job_id=job_id)

        diff_sections, similarity_pct = self.diff_service.compare_markdown(
            pdf1_md,
            pdf2_md,
            source_name=Path(pdf1_path).name,
            target_name=Path(pdf2_path).name,
            include_unchanged=False
        )

        # Generate diff summary
        diff_summary = self.diff_service.generate_diff_summary(diff_sections)

        self.update_state(
            state="PROCESSING",
            meta={
                "job_id": job_id,
                "status": "processing",
                "current_step": "Analyzing with LLM" if use_llm else "Finalizing results",
                "progress": 70
            }
        )

        # Step 3: Optional LLM analysis
        llm_analysis = None
        if use_llm:
            logger.info("llm_analysis_starting", job_id=job_id)

            try:
                llm_analysis = self.llm_service.analyze_differences(
                    diff_sections,
                    source_name=Path(pdf1_path).name,
                    target_name=Path(pdf2_path).name,
                    custom_prompt=llm_prompt,
                    document_context="tax document"
                )

                logger.info(
                    "llm_analysis_completed",
                    job_id=job_id,
                    key_changes=len(llm_analysis.get("key_changes", []))
                )

            except Exception as e:
                logger.error(
                    "llm_analysis_failed",
                    job_id=job_id,
                    error=str(e)
                )
                # Continue without LLM analysis
                llm_analysis = {
                    "summary": f"LLM analysis failed: {str(e)}",
                    "key_changes": [],
                    "impact_assessment": "",
                    "recommendations": []
                }

        self.update_state(
            state="PROCESSING",
            meta={
                "job_id": job_id,
                "status": "processing",
                "current_step": "Generating final results",
                "progress": 90
            }
        )

        # Step 4: Create comprehensive result
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()

        result = ComparisonResult(
            job_id=job_id,
            status=ComparisonStatus.COMPLETED,
            created_at=start_time,
            completed_at=end_time,
            processing_time_seconds=processing_time,
            source_metadata=pdf1_metadata,
            target_metadata=pdf2_metadata,
            total_differences=diff_summary["total_differences"],
            added_sections=diff_summary["added"],
            removed_sections=diff_summary["removed"],
            modified_sections=diff_summary["modified"],
            similarity_percentage=similarity_pct,
            differences=diff_sections,
            llm_summary=llm_analysis.get("summary") if llm_analysis else None,
            llm_key_changes=llm_analysis.get("key_changes") if llm_analysis else None,
            llm_recommendations=llm_analysis.get("recommendations") if llm_analysis else None,
            markdown_output_path=None,  # Could generate a combined diff markdown
            source_markdown_path=str(pdf1_md_path),
            target_markdown_path=str(pdf2_md_path)
        )

        logger.info(
            "comparison_task_completed",
            job_id=job_id,
            processing_time=processing_time,
            total_diffs=diff_summary["total_differences"],
            similarity=similarity_pct
        )

        # Return result as dict for serialization
        return result.model_dump()

    except Exception as e:
        logger.error(
            "comparison_task_failed",
            job_id=job_id,
            error=str(e),
            exc_info=True
        )

        # Create failed result
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()

        error_result = ComparisonResult(
            job_id=job_id,
            status=ComparisonStatus.FAILED,
            created_at=start_time,
            completed_at=end_time,
            processing_time_seconds=processing_time,
            error=str(e),
            error_details={"exc_type": type(e).__name__}
        )

        # Retry if we haven't exhausted retries
        if self.request.retries < self.max_retries:
            logger.warning(
                "comparison_task_retrying",
                job_id=job_id,
                retry=self.request.retries + 1,
                max_retries=self.max_retries
            )
            raise self.retry(exc=e, countdown=60)

        return error_result.model_dump()


@celery_app.task(name="health_check")
def health_check_task() -> Dict[str, str]:
    """
    Health check task for monitoring Celery workers.

    Returns:
        Dictionary with health status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }
