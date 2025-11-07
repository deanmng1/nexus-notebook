"""
PDF Processing Service

This service handles converting PDFs to Markdown format with full support for:
- Text extraction with layout preservation
- Image extraction and embedding
- Table detection and extraction
- Metadata extraction
- Multi-page processing
- Multi-column layout handling
- Header/footer detection

The service uses pymupdf4llm for high-quality PDF to Markdown conversion,
which provides superior layout analysis and text extraction compared to basic methods.
"""

import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import fitz  # PyMuPDF
import pymupdf4llm

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.comparison import PDFMetadata

logger = get_logger(__name__)


class PDFProcessingError(Exception):
    """Raised when PDF processing fails."""

    pass


class PDFProcessor:
    """
    Service for processing PDF documents and converting them to Markdown.

    This class provides comprehensive PDF processing capabilities using pymupdf4llm,
    which handles complex layouts, tables, images, and preserves document structure.

    Attributes:
        settings: Application settings
        temp_dir: Temporary directory for intermediate files
        output_dir: Output directory for final files
    """

    def __init__(self):
        """Initialize the PDF processor with configuration."""
        self.settings = get_settings()
        self.temp_dir = Path(self.settings.temp_dir)
        self.output_dir = Path(self.settings.output_dir)

        # Ensure directories exist
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "pdf_processor_initialized",
            temp_dir=str(self.temp_dir),
            output_dir=str(self.output_dir),
            using_library="pymupdf4llm"
        )

    def validate_pdf(self, file_path: Path) -> None:
        """
        Validate that a file is a valid PDF.

        Args:
            file_path: Path to the PDF file

        Raises:
            PDFProcessingError: If file is invalid or not a PDF
        """
        if not file_path.exists():
            raise PDFProcessingError(f"File not found: {file_path}")

        if file_path.stat().st_size < self.settings.min_file_size_bytes:
            raise PDFProcessingError(
                f"File too small: {file_path.stat().st_size} bytes"
            )

        if file_path.stat().st_size > self.settings.max_file_size_bytes:
            raise PDFProcessingError(
                f"File too large: {file_path.stat().st_size} bytes "
                f"(max: {self.settings.max_file_size_bytes})"
            )

        # Try to open with PyMuPDF to validate it's a real PDF
        try:
            doc = fitz.open(file_path)
            if doc.page_count == 0:
                raise PDFProcessingError("PDF has no pages")
            if doc.page_count > self.settings.pdf_max_pages:
                raise PDFProcessingError(
                    f"PDF has too many pages: {doc.page_count} "
                    f"(max: {self.settings.pdf_max_pages})"
                )
            doc.close()
        except fitz.FileDataError as e:
            raise PDFProcessingError(f"Invalid PDF file: {e}")
        except Exception as e:
            raise PDFProcessingError(f"Error validating PDF: {e}")

        logger.info("pdf_validated", file_path=str(file_path))

    def extract_metadata(self, file_path: Path) -> PDFMetadata:
        """
        Extract metadata from a PDF document.

        Args:
            file_path: Path to the PDF file

        Returns:
            PDFMetadata: Extracted metadata

        Raises:
            PDFProcessingError: If metadata extraction fails
        """
        try:
            doc = fitz.open(file_path)
            metadata = doc.metadata or {}

            # Count images and tables
            has_images = False
            has_tables = False
            word_count = 0

            for page in doc:
                # Check for images
                if page.get_images():
                    has_images = True

                # Approximate word count
                text = page.get_text()
                word_count += len(text.split())

            # Check for tables using PyMuPDF's table detection
            for page_num in range(min(5, doc.page_count)):  # Check first 5 pages
                page = doc[page_num]
                tables = page.find_tables()
                if tables and len(tables.tables) > 0:
                    has_tables = True
                    break

            pdf_metadata = PDFMetadata(
                file_name=file_path.name,
                file_size=file_path.stat().st_size,
                page_count=doc.page_count,
                title=metadata.get("title"),
                author=metadata.get("author"),
                subject=metadata.get("subject"),
                creator=metadata.get("creator"),
                producer=metadata.get("producer"),
                creation_date=None,  # Can be parsed from metadata if needed
                modification_date=None,
                has_images=has_images,
                has_tables=has_tables,
                word_count=word_count
            )

            doc.close()
            logger.info(
                "metadata_extracted",
                file_path=str(file_path),
                pages=pdf_metadata.page_count,
                words=word_count,
                has_images=has_images,
                has_tables=has_tables
            )
            return pdf_metadata

        except Exception as e:
            logger.error("metadata_extraction_failed", file_path=str(file_path), error=str(e))
            raise PDFProcessingError(f"Failed to extract metadata: {e}")

    def pdf_to_markdown(
        self,
        pdf_path: Path,
        output_path: Optional[Path] = None,
        extract_images: bool = True,
        extract_tables: bool = True,
        page_chunks: bool = False
    ) -> Tuple[str, Path, Optional[List[Dict]]]:
        """
        Convert a PDF to Markdown format using pymupdf4llm.

        This is the main conversion method that uses the pymupdf4llm library for:
        1. Superior layout analysis (handles multi-column layouts)
        2. Proper reading order
        3. Table extraction and conversion to markdown tables
        4. Image extraction and embedding
        5. Header detection (font-size based)
        6. Text formatting (bold, italic, code blocks, lists)

        Args:
            pdf_path: Path to the PDF file
            output_path: Optional output path for markdown file
            extract_images: Whether to extract images
            extract_tables: Whether to extract tables
            page_chunks: Whether to return page-by-page chunks with metadata

        Returns:
            Tuple of (markdown_content, output_file_path, page_chunks_data)
            - markdown_content: Full markdown text
            - output_file_path: Path where markdown was saved
            - page_chunks_data: List of dicts with per-page data (if page_chunks=True)

        Raises:
            PDFProcessingError: If conversion fails
        """
        logger.info(
            "pdf_conversion_started",
            pdf_path=str(pdf_path),
            extract_images=extract_images,
            extract_tables=extract_tables,
            page_chunks=page_chunks
        )

        # Validate PDF
        self.validate_pdf(pdf_path)

        # Create output path if not provided
        if output_path is None:
            job_id = uuid.uuid4().hex[:8]
            output_filename = f"{pdf_path.stem}_{job_id}.md"
            output_path = self.output_dir / output_filename

        # Create image directory
        image_dir = None
        if extract_images and self.settings.extract_images:
            image_dir = output_path.parent / f"{output_path.stem}_images"
            image_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Open PDF with PyMuPDF
            doc = fitz.open(pdf_path)

            # Configure pymupdf4llm parameters
            conversion_params = {
                "pages": None,  # Process all pages
                "write_images": extract_images and self.settings.extract_images,
                "image_path": str(image_dir) if image_dir else "",
                "image_format": "png",
                "dpi": self.settings.pdf_dpi,
                "page_chunks": page_chunks,
                "force_text": True,  # Extract text even when overlaid on images
                "table_strategy": "lines_strict" if extract_tables and self.settings.extract_tables else None,
                "ignore_code": False,  # Preserve code block formatting
                "show_progress": False,  # Don't show progress bar
            }

            logger.debug(
                "pymupdf4llm_conversion_params",
                params=conversion_params
            )

            # Convert PDF to Markdown using pymupdf4llm
            result = pymupdf4llm.to_markdown(
                doc,
                **conversion_params
            )

            # Handle result based on page_chunks setting
            page_chunks_data = None
            if page_chunks:
                # Result is a list of dictionaries (one per page)
                page_chunks_data = result
                # Combine all page text into single markdown
                markdown_content = "\n\n".join([
                    f"<!-- Page {chunk['metadata']['page']} -->\n{chunk['text']}"
                    for chunk in result
                ])
            else:
                # Result is a single markdown string
                markdown_content = result

            doc.close()

            # Add document header
            header_parts = []
            header_parts.append(f"# {pdf_path.stem}\n")
            header_parts.append(f"**Source:** {pdf_path.name}\n")
            header_parts.append("---\n\n")

            full_markdown = "".join(header_parts) + markdown_content

            # Write to file
            output_path.write_text(full_markdown, encoding="utf-8")

            logger.info(
                "pdf_conversion_completed",
                pdf_path=str(pdf_path),
                output_path=str(output_path),
                size_bytes=len(full_markdown),
                chunks=len(page_chunks_data) if page_chunks_data else 0
            )

            return full_markdown, output_path, page_chunks_data

        except Exception as e:
            logger.error(
                "pdf_conversion_failed",
                pdf_path=str(pdf_path),
                error=str(e),
                exc_info=True
            )
            raise PDFProcessingError(f"Failed to convert PDF to Markdown: {e}")

    def compare_pdfs_structure(
        self,
        pdf1_path: Path,
        pdf2_path: Path
    ) -> Dict[str, any]:
        """
        Compare the structure of two PDFs.

        This is a quick comparison that checks:
        - Page counts
        - Image counts
        - Table counts
        - Word counts

        Args:
            pdf1_path: Path to first PDF
            pdf2_path: Path to second PDF

        Returns:
            Dictionary with structural comparison data
        """
        try:
            metadata1 = self.extract_metadata(pdf1_path)
            metadata2 = self.extract_metadata(pdf2_path)

            comparison = {
                "pdf1": {
                    "name": metadata1.file_name,
                    "pages": metadata1.page_count,
                    "words": metadata1.word_count,
                    "has_images": metadata1.has_images,
                    "has_tables": metadata1.has_tables,
                },
                "pdf2": {
                    "name": metadata2.file_name,
                    "pages": metadata2.page_count,
                    "words": metadata2.word_count,
                    "has_images": metadata2.has_images,
                    "has_tables": metadata2.has_tables,
                },
                "differences": {
                    "page_count_diff": metadata2.page_count - metadata1.page_count,
                    "word_count_diff": metadata2.word_count - metadata1.word_count,
                    "images_changed": metadata1.has_images != metadata2.has_images,
                    "tables_changed": metadata1.has_tables != metadata2.has_tables,
                }
            }

            logger.info(
                "pdf_structure_comparison",
                pdf1=pdf1_path.name,
                pdf2=pdf2_path.name,
                page_diff=comparison["differences"]["page_count_diff"],
                word_diff=comparison["differences"]["word_count_diff"]
            )

            return comparison

        except Exception as e:
            logger.error(
                "structure_comparison_failed",
                pdf1=str(pdf1_path),
                pdf2=str(pdf2_path),
                error=str(e)
            )
            raise PDFProcessingError(f"Failed to compare PDF structures: {e}")

    def cleanup_temp_files(self, file_paths: List[Path]) -> None:
        """
        Clean up temporary files.

        Args:
            file_paths: List of file paths to delete
        """
        if not self.settings.cleanup_temp_files:
            logger.debug("cleanup_disabled", message="Temp file cleanup is disabled")
            return

        for file_path in file_paths:
            try:
                if file_path.exists():
                    if file_path.is_file():
                        file_path.unlink()
                        logger.debug("temp_file_deleted", path=str(file_path))
                    elif file_path.is_dir():
                        import shutil
                        shutil.rmtree(file_path)
                        logger.debug("temp_dir_deleted", path=str(file_path))
            except Exception as e:
                logger.warning(
                    "temp_file_cleanup_failed",
                    path=str(file_path),
                    error=str(e)
                )
