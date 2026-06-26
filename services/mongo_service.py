"""
services/mongo_service.py - High-Level MongoDB Service
=======================================================
Thin facade over database.py that formats documents before
storage and provides convenience helpers for the Streamlit UI.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from database import MongoDB


class MongoService:
    """
    Application-level service for MongoDB operations.
    Handles document construction/formatting so analyzer.py stays clean.
    """

    @staticmethod
    def save_analysis(
        *,
        article_title: str,
        article_text: str,
        source_url: str,
        analysis_result: dict[str, Any],
    ) -> str | None:
        """
        Persist an analysis result to MongoDB.

        Args:
            article_title:   Headline of the article.
            article_text:    Full body text (truncated).
            source_url:      URL the article was scraped from (empty if manual).
            analysis_result: The dict returned by GeminiService.analyze_article().

        Returns:
            Inserted document ID string, or None on failure.
        """
        document = {
            "article_title": article_title,
            "article_text": article_text[:5000],  # Store first 5k chars
            "source_url": source_url,
            "credibility_score": analysis_result.get("credibility_score", 0),
            "confidence_score": analysis_result.get("confidence_score", 0),
            "verdict": analysis_result.get("verdict", "Unknown"),
            "summary": analysis_result.get("summary", ""),
            "analysis": {
                "detailed_explanation": analysis_result.get("detailed_explanation", ""),
                "key_claims": analysis_result.get("key_claims", []),
                "red_flags": analysis_result.get("red_flags", []),
                "trust_indicators": analysis_result.get("trust_indicators", []),
                "fact_checking_suggestions": analysis_result.get("fact_checking_suggestions", []),
                "bias_indicators": analysis_result.get("bias_indicators", ""),
                "emotional_language_score": analysis_result.get("emotional_language_score", 0),
                "source_credibility_notes": analysis_result.get("source_credibility_notes", ""),
                "missing_context": analysis_result.get("missing_context", ""),
            },
        }
        return MongoDB.save_analysis(document)

    @staticmethod
    def get_dashboard_stats() -> dict[str, Any]:
        """Return aggregated statistics for the dashboard."""
        return MongoDB.get_statistics()

    @staticmethod
    def list_analyses(limit: int = 100) -> list[dict]:
        """Return recent analyses for the history page."""
        return MongoDB.get_all_analyses(limit=limit)

    @staticmethod
    def search_analyses(keyword: str, verdict_filter: str) -> list[dict]:
        """Delegate search to the database layer."""
        return MongoDB.search_analyses(keyword=keyword, verdict_filter=verdict_filter)

    @staticmethod
    def delete_analysis(doc_id: str) -> bool:
        """Delete a single analysis record."""
        return MongoDB.delete_analysis(doc_id)

    @staticmethod
    def get_analysis(doc_id: str) -> dict | None:
        """Fetch a single analysis by ID."""
        return MongoDB.get_analysis_by_id(doc_id)
