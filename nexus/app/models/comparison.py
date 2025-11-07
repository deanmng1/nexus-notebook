"""
Data models for PDF comparison operations.

These models define the structure of requests, responses, and intermediate data
used throughout the comparison process.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ComparisonStatus(str, Enum):
    """Status of a comparison job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PDFMetadata(BaseModel):
    """
    Metadata extracted from a PDF document.

    Contains information about the PDF structure and content.
    """

    file_name: str = Field(..., description="Original file name")
    file_size: int = Field(..., description="File size in bytes")
    page_count: int = Field(..., description="Number of pages")
    title: Optional[str] = Field(None, description="PDF title from metadata")
    author: Optional[str] = Field(None, description="PDF author from metadata")
    subject: Optional[str] = Field(None, description="PDF subject from metadata")
    creator: Optional[str] = Field(None, description="PDF creator from metadata")
    producer: Optional[str] = Field(None, description="PDF producer from metadata")
    creation_date: Optional[datetime] = Field(None, description="PDF creation date")
    modification_date: Optional[datetime] = Field(None, description="PDF modification date")
    has_images: bool = Field(default=False, description="Whether PDF contains images")
    has_tables: bool = Field(default=False, description="Whether PDF contains tables")
    word_count: int = Field(default=0, description="Approximate word count")


class DiffType(str, Enum):
    """Type of difference between documents."""

    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


class DiffSection(BaseModel):
    """
    A section of text that differs between two PDFs.

    Represents a single difference with context and metadata.
    """

    diff_type: DiffType = Field(..., description="Type of difference")
    page_number_source: Optional[int] = Field(None, description="Page number in source PDF")
    page_number_target: Optional[int] = Field(None, description="Page number in target PDF")
    source_text: Optional[str] = Field(None, description="Text from source PDF")
    target_text: Optional[str] = Field(None, description="Text from target PDF")
    context_before: Optional[str] = Field(None, description="Context before the difference")
    context_after: Optional[str] = Field(None, description="Context after the difference")
    line_number: Optional[int] = Field(None, description="Line number in document")
    similarity_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Similarity score (0-1)"
    )
    importance_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Importance score from LLM (0-1)"
    )
    llm_analysis: Optional[str] = Field(
        None,
        description="LLM analysis of this difference"
    )
    proof: Optional[str] = Field(
        None,
        description="Citation/proof for this difference"
    )


class ComparisonRequest(BaseModel):
    """
    Request to compare two PDF documents.

    This is the input model for the comparison API.
    """

    file1_path: Optional[str] = Field(None, description="Path to first PDF file")
    file2_path: Optional[str] = Field(None, description="Path to second PDF file")
    use_llm: bool = Field(default=False, description="Use LLM for analysis")
    llm_prompt: Optional[str] = Field(
        None,
        description="Custom prompt for LLM analysis"
    )
    include_unchanged: bool = Field(
        default=False,
        description="Include unchanged sections"
    )
    extract_images: bool = Field(default=True, description="Extract and compare images")
    extract_tables: bool = Field(default=True, description="Extract and compare tables")
    similarity_threshold: Optional[float] = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Similarity threshold for matching"
    )

    @field_validator("similarity_threshold")
    @classmethod
    def validate_threshold(cls, v: Optional[float]) -> Optional[float]:
        """Validate similarity threshold is in valid range."""
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError("Similarity threshold must be between 0.0 and 1.0")
        return v


class ComparisonResult(BaseModel):
    """
    Result of comparing two PDF documents.

    Contains all differences found, metadata, and analysis.
    """

    job_id: str = Field(..., description="Unique job identifier")
    status: ComparisonStatus = Field(..., description="Job status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")
    processing_time_seconds: Optional[float] = Field(
        None,
        description="Processing time in seconds"
    )

    # Source PDFs metadata
    source_metadata: Optional[PDFMetadata] = Field(None, description="Source PDF metadata")
    target_metadata: Optional[PDFMetadata] = Field(None, description="Target PDF metadata")

    # Comparison results
    total_differences: int = Field(default=0, description="Total number of differences")
    added_sections: int = Field(default=0, description="Number of added sections")
    removed_sections: int = Field(default=0, description="Number of removed sections")
    modified_sections: int = Field(default=0, description="Number of modified sections")
    similarity_percentage: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Overall similarity percentage"
    )

    # Detailed differences
    differences: List[DiffSection] = Field(
        default_factory=list,
        description="List of all differences"
    )

    # LLM analysis
    llm_summary: Optional[str] = Field(None, description="LLM summary of differences")
    llm_key_changes: Optional[List[str]] = Field(
        None,
        description="Key changes identified by LLM"
    )
    llm_recommendations: Optional[List[str]] = Field(
        None,
        description="LLM recommendations"
    )

    # Outputs
    markdown_output_path: Optional[str] = Field(
        None,
        description="Path to markdown output file"
    )
    source_markdown_path: Optional[str] = Field(
        None,
        description="Path to source PDF markdown"
    )
    target_markdown_path: Optional[str] = Field(
        None,
        description="Path to target PDF markdown"
    )

    # Error information
    error: Optional[str] = Field(None, description="Error message if failed")
    error_details: Optional[Dict[str, Any]] = Field(
        None,
        description="Detailed error information"
    )


class JobStatus(BaseModel):
    """
    Status of a comparison job.

    Used for polling job status before results are ready.
    """

    job_id: str = Field(..., description="Unique job identifier")
    status: ComparisonStatus = Field(..., description="Job status")
    progress_percentage: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Progress percentage"
    )
    current_step: Optional[str] = Field(None, description="Current processing step")
    message: Optional[str] = Field(None, description="Status message")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation time")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update time")
    estimated_completion: Optional[datetime] = Field(
        None,
        description="Estimated completion time"
    )
    error: Optional[str] = Field(None, description="Error message if failed")


class HealthCheck(BaseModel):
    """Health check response."""

    status: str = Field(default="healthy", description="Service status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check time")
    version: str = Field(..., description="API version")
    redis_connected: bool = Field(default=False, description="Redis connection status")
    celery_workers: int = Field(default=0, description="Number of active Celery workers")
    llm_configured: bool = Field(default=False, description="LLM configuration status")
