"""
LLM Integration Service - Placeholder

This is a placeholder for future LLM integration.
Currently, the service works without LLM analysis.
"""

from typing import Dict, List, Optional

from app.core.logging import get_logger
from app.models.comparison import DiffSection

logger = get_logger(__name__)


class LLMServiceError(Exception):
    """Raised when LLM service fails."""

    pass


class LLMService:
    """
    Placeholder service for future LLM integration.

    This service is currently disabled. The PDF comparison works
    entirely on diff analysis without LLM enhancement.
    """

    def __init__(self):
        """Initialize the LLM service placeholder."""
        logger.info("llm_service_disabled", message="LLM integration is disabled")

    def analyze_differences(
        self,
        diff_sections: List[DiffSection],  # noqa: ARG002
        source_name: str = "source",  # noqa: ARG002
        target_name: str = "target",  # noqa: ARG002
        custom_prompt: Optional[str] = None,  # noqa: ARG002
        document_context: str = "document"  # noqa: ARG002
    ) -> Dict[str, any]:
        """
        Placeholder for LLM analysis.

        Currently returns empty analysis. This can be implemented
        in the future to add AI-powered insights.

        Args:
            diff_sections: List of differences to analyze (unused - placeholder)
            source_name: Name of source document (unused - placeholder)
            target_name: Name of target document (unused - placeholder)
            custom_prompt: Custom prompt for analysis (unused - placeholder)
            document_context: Context about the document type (unused - placeholder)

        Returns:
            Empty analysis dictionary
        """
        logger.debug("llm_analysis_skipped", message="LLM is disabled")

        return {
            "summary": None,
            "key_changes": None,
            "impact_assessment": None,
            "recommendations": None,
            "raw_response": None
        }

    def score_difference_importance(
        self,
        diff_section: DiffSection,  # noqa: ARG002
        document_context: str = "document"  # noqa: ARG002
    ) -> Optional[float]:
        """
        Placeholder for importance scoring.

        Args:
            diff_section: Difference to score (unused - placeholder)
            document_context: Document context (unused - placeholder)

        Returns:
            None (LLM disabled)
        """
        return None
