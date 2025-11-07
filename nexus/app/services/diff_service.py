"""
Diff Comparison Service

This service compares two markdown documents and identifies differences with:
- Line-by-line diff analysis
- Similarity scoring
- Context extraction for each difference
- Proof/citation generation
- Categorization of changes (added, removed, modified)
"""

import difflib
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.comparison import DiffSection, DiffType

logger = get_logger(__name__)


class DiffComparisonError(Exception):
    """Raised when diff comparison fails."""

    pass


class DiffService:
    """
    Service for comparing markdown documents and generating detailed diffs.

    This service uses Python's difflib for comprehensive text comparison
    and provides rich metadata about each difference.

    Attributes:
        settings: Application settings
    """

    def __init__(self):
        """Initialize the diff service with configuration."""
        self.settings = get_settings()

        logger.info(
            "diff_service_initialized",
            context_lines=self.settings.diff_context_lines,
            similarity_threshold=self.settings.similarity_threshold
        )

    def compare_markdown(
        self,
        source_text: str,
        target_text: str,
        source_name: str = "source",
        target_name: str = "target",
        include_unchanged: bool = False
    ) -> Tuple[List[DiffSection], float]:
        """
        Compare two markdown texts and generate detailed diff information.

        Args:
            source_text: Source markdown text
            target_text: Target markdown text
            source_name: Name of source document (for references)
            target_name: Name of target document (for references)
            include_unchanged: Whether to include unchanged sections

        Returns:
            Tuple of (list of DiffSection objects, overall_similarity_percentage)

        Raises:
            DiffComparisonError: If comparison fails
        """
        logger.info(
            "markdown_comparison_started",
            source_name=source_name,
            target_name=target_name,
            source_length=len(source_text),
            target_length=len(target_text)
        )

        try:
            # Split texts into lines for comparison
            source_lines = source_text.splitlines(keepends=True)
            target_lines = target_text.splitlines(keepends=True)

            # Calculate overall similarity
            similarity = self._calculate_similarity(source_text, target_text)

            # Generate unified diff for detailed analysis
            diff_sections = []
            differ = difflib.unified_diff(
                source_lines,
                target_lines,
                fromfile=source_name,
                tofile=target_name,
                lineterm='',
                n=self.settings.diff_context_lines
            )

            # Parse the unified diff
            diff_sections = self._parse_unified_diff(
                list(differ),
                source_lines,
                target_lines,
                include_unchanged
            )

            # Generate detailed diffs using SequenceMatcher for finer granularity
            detailed_sections = self._generate_detailed_diffs(
                source_lines,
                target_lines,
                include_unchanged
            )

            logger.info(
                "markdown_comparison_completed",
                source_name=source_name,
                target_name=target_name,
                differences_found=len(detailed_sections),
                similarity_percentage=similarity * 100
            )

            return detailed_sections, similarity * 100

        except Exception as e:
            logger.error(
                "markdown_comparison_failed",
                source_name=source_name,
                target_name=target_name,
                error=str(e),
                exc_info=True
            )
            raise DiffComparisonError(f"Failed to compare markdown documents: {e}")

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity ratio between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity ratio between 0.0 and 1.0
        """
        matcher = difflib.SequenceMatcher(None, text1, text2)
        return matcher.ratio()

    def _parse_unified_diff(
        self,
        diff_lines: List[str],
        source_lines: List[str],
        target_lines: List[str],
        include_unchanged: bool
    ) -> List[DiffSection]:
        """
        Parse unified diff output into structured DiffSection objects.

        Args:
            diff_lines: Lines from unified_diff output
            source_lines: Source document lines
            target_lines: Target document lines
            include_unchanged: Whether to include unchanged sections

        Returns:
            List of DiffSection objects
        """
        sections = []
        current_source_line = 0
        current_target_line = 0

        for line in diff_lines:
            if line.startswith('@@'):
                # Parse hunk header to get line numbers
                # Format: @@ -start,count +start,count @@
                parts = line.split()
                if len(parts) >= 3:
                    source_info = parts[1].lstrip('-').split(',')
                    target_info = parts[2].lstrip('+').split(',')
                    current_source_line = int(source_info[0])
                    current_target_line = int(target_info[0])

        return sections

    def _generate_detailed_diffs(
        self,
        source_lines: List[str],
        target_lines: List[str],
        include_unchanged: bool
    ) -> List[DiffSection]:
        """
        Generate detailed diffs using SequenceMatcher.

        This provides more granular control over difference detection
        and allows for similarity scoring of individual changes.

        Args:
            source_lines: Source document lines
            target_lines: Target document lines
            include_unchanged: Whether to include unchanged sections

        Returns:
            List of DiffSection objects
        """
        sections = []
        matcher = difflib.SequenceMatcher(None, source_lines, target_lines)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            # Determine diff type
            if tag == 'equal':
                if include_unchanged:
                    diff_type = DiffType.UNCHANGED
                else:
                    continue  # Skip unchanged sections
            elif tag == 'delete':
                diff_type = DiffType.REMOVED
            elif tag == 'insert':
                diff_type = DiffType.ADDED
            elif tag == 'replace':
                diff_type = DiffType.MODIFIED
            else:
                continue

            # Extract text for this section
            source_text = ''.join(source_lines[i1:i2]).strip() if i1 < i2 else None
            target_text = ''.join(target_lines[j1:j2]).strip() if j1 < j2 else None

            # Calculate similarity for this section
            if source_text and target_text:
                similarity = self._calculate_similarity(source_text, target_text)
            else:
                similarity = 0.0 if (source_text or target_text) else 1.0

            # Extract context
            context_before = self._get_context(source_lines, max(0, i1 - 2), i1)
            context_after = self._get_context(source_lines, i2, min(len(source_lines), i2 + 2))

            # Generate proof/citation
            proof = self._generate_proof(
                diff_type,
                i1 + 1,  # Convert to 1-based line numbers
                j1 + 1,
                source_text,
                target_text
            )

            section = DiffSection(
                diff_type=diff_type,
                page_number_source=None,  # Will be populated if we have page chunk data
                page_number_target=None,
                source_text=source_text,
                target_text=target_text,
                context_before=context_before,
                context_after=context_after,
                line_number=i1 + 1 if source_text else j1 + 1,
                similarity_score=similarity,
                importance_score=None,  # Will be set by LLM service
                llm_analysis=None,  # Will be set by LLM service
                proof=proof
            )

            sections.append(section)

        logger.debug(
            "detailed_diffs_generated",
            total_sections=len(sections),
            added=sum(1 for s in sections if s.diff_type == DiffType.ADDED),
            removed=sum(1 for s in sections if s.diff_type == DiffType.REMOVED),
            modified=sum(1 for s in sections if s.diff_type == DiffType.MODIFIED)
        )

        return sections

    def _get_context(self, lines: List[str], start: int, end: int) -> Optional[str]:
        """
        Extract context lines from document.

        Args:
            lines: Document lines
            start: Start index
            end: End index

        Returns:
            Context text or None if no context
        """
        if start < 0 or end > len(lines) or start >= end:
            return None

        context = ''.join(lines[start:end]).strip()
        return context if context else None

    def _generate_proof(
        self,
        diff_type: DiffType,
        source_line: int,
        target_line: int,
        source_text: Optional[str],
        target_text: Optional[str]
    ) -> str:
        """
        Generate citation/proof for a difference.

        Args:
            diff_type: Type of difference
            source_line: Source line number
            target_line: Target line number
            source_text: Source text snippet
            target_text: Target text snippet

        Returns:
            Proof/citation string
        """
        if diff_type == DiffType.ADDED:
            return f"Added at line {target_line}: '{self._truncate_text(target_text, 50)}'"
        elif diff_type == DiffType.REMOVED:
            return f"Removed from line {source_line}: '{self._truncate_text(source_text, 50)}'"
        elif diff_type == DiffType.MODIFIED:
            return (
                f"Modified at line {source_line} → {target_line}: "
                f"'{self._truncate_text(source_text, 30)}' → "
                f"'{self._truncate_text(target_text, 30)}'"
            )
        else:
            return f"Unchanged at line {source_line}"

    def _truncate_text(self, text: Optional[str], max_length: int) -> str:
        """
        Truncate text to maximum length.

        Args:
            text: Text to truncate
            max_length: Maximum length

        Returns:
            Truncated text with ellipsis if needed
        """
        if not text:
            return ""

        if len(text) <= max_length:
            return text

        return text[:max_length] + "..."

    def generate_diff_summary(self, sections: List[DiffSection]) -> Dict[str, any]:
        """
        Generate a summary of differences.

        Args:
            sections: List of diff sections

        Returns:
            Summary dictionary with statistics
        """
        summary = {
            "total_differences": len(sections),
            "added": sum(1 for s in sections if s.diff_type == DiffType.ADDED),
            "removed": sum(1 for s in sections if s.diff_type == DiffType.REMOVED),
            "modified": sum(1 for s in sections if s.diff_type == DiffType.MODIFIED),
            "unchanged": sum(1 for s in sections if s.diff_type == DiffType.UNCHANGED),
            "average_similarity": sum(
                s.similarity_score for s in sections if s.similarity_score
            ) / len(sections) if sections else 0.0,
            "low_similarity_sections": [
                s for s in sections
                if s.similarity_score and s.similarity_score < self.settings.similarity_threshold
            ]
        }

        logger.info("diff_summary_generated", **summary)

        return summary

    def export_diff_html(
        self,
        source_text: str,
        target_text: str,
        output_path: Path
    ) -> Path:
        """
        Export diff as an HTML file.

        Args:
            source_text: Source text
            target_text: Target text
            output_path: Path to save HTML file

        Returns:
            Path to saved HTML file
        """
        try:
            differ = difflib.HtmlDiff()
            html = differ.make_file(
                source_text.splitlines(),
                target_text.splitlines(),
                fromdesc="Source",
                todesc="Target",
                context=True,
                numlines=self.settings.diff_context_lines
            )

            output_path.write_text(html, encoding='utf-8')

            logger.info(
                "html_diff_exported",
                output_path=str(output_path),
                size_bytes=len(html)
            )

            return output_path

        except Exception as e:
            logger.error(
                "html_diff_export_failed",
                output_path=str(output_path),
                error=str(e)
            )
            raise DiffComparisonError(f"Failed to export HTML diff: {e}")
