"""
analyzer.py - Core Analysis Orchestrator
=========================================
Ties together scraping, Gemini AI, and MongoDB persistence.
This is the single entry-point called by the Streamlit UI.
"""

from __future__ import annotations

import logging
from typing import Any

from scraper import scrape_article, is_valid_url
from services.gemini_service import GeminiService
from services.mongo_service import MongoService
from database import MongoDB

logger = logging.getLogger(__name__)

# Lazily-initialized Gemini service (avoids startup cost when not needed)
_gemini: GeminiService | None = None


def _get_gemini() -> GeminiService:
    """Return a cached GeminiService instance."""
    global _gemini
    if _gemini is None:
        _gemini = GeminiService()
    return _gemini


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def analyze_from_text(title: str, text: str) -> dict[str, Any]:
    """
    Analyze a news article provided as raw text.

    Args:
        title: Article headline (may be empty, will use placeholder).
        text:  Article body text.

    Returns:
        Combined result dict with 'success', 'doc_id', and all analysis fields.
    """
    if not text or len(text.strip()) < 50:
        return {
            "success": False,
            "error": "Article text is too short. Please provide at least 50 characters.",
        }

    title = title.strip() or "Untitled Article"
    return _run_analysis(title=title, text=text, source_url="")


def analyze_from_url(url: str) -> dict[str, Any]:
    """
    Scrape and analyze an article from a URL.

    Args:
        url: A valid HTTP/HTTPS URL.

    Returns:
        Combined result dict with scraping info + analysis fields.
    """
    if not is_valid_url(url):
        return {
            "success": False,
            "error": "Invalid URL. Please enter a valid http:// or https:// link.",
        }

    # Step 1: Scrape article content
    scrape_result = scrape_article(url)
    if not scrape_result["success"]:
        return {
            "success": False,
            "error": scrape_result.get("error", "Failed to extract article content."),
        }

    title = scrape_result["title"]
    text = scrape_result["text"]
    authors = scrape_result.get("authors", "")
    publish_date = scrape_result.get("publish_date", "")

    # Step 2: Analyze
    result = _run_analysis(title=title, text=text, source_url=url)
    result["authors"] = authors
    result["publish_date"] = publish_date
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Internal Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _run_analysis(title: str, text: str, source_url: str) -> dict[str, Any]:
    """
    Core pipeline: Gemini analysis → MongoDB storage.

    Returns:
        The analysis result with 'doc_id' if stored successfully.
    """
    try:
        gemini = _get_gemini()
    except ValueError as exc:
        return {"success": False, "error": str(exc)}

    # ── Gemini Analysis ───────────────────────────────────────────────────────
    analysis = gemini.analyze_article(title=title, text=text)

    if not analysis.get("success"):
        return {
            "success": False,
            "error": analysis.get("error", "Gemini analysis failed."),
        }

    # ── MongoDB Storage ───────────────────────────────────────────────────────
    doc_id = None
    if MongoDB.is_connected():
        try:
            doc_id = MongoService.save_analysis(
                article_title=title,
                article_text=text,
                source_url=source_url,
                analysis_result=analysis,
            )
        except Exception as exc:
            logger.warning("Could not save analysis to MongoDB: %s", exc)
    else:
        logger.warning("MongoDB not connected – analysis will not be persisted.")

    return {
        **analysis,
        "article_title": title,
        "article_text": text,
        "source_url": source_url,
        "doc_id": doc_id,
    }
