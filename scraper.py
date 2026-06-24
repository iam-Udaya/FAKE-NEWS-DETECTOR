"""
scraper.py - Article Content Extraction
========================================
Fetches and parses news article text from a given URL.
Uses newspaper3k as primary extractor with a BeautifulSoup fallback.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from config import config

logger = logging.getLogger(__name__)

# Browser-like headers to avoid 403 blocks
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


# ─────────────────────────────────────────────────────────────────────────────
# URL Validation
# ─────────────────────────────────────────────────────────────────────────────

def is_valid_url(url: str) -> bool:
    """
    Return True if *url* is a well-formed HTTP/HTTPS URL.

    Args:
        url: The string to validate.

    Returns:
        True if valid, False otherwise.
    """
    try:
        parsed = urlparse(url.strip())
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Primary Extractor – newspaper3k
# ─────────────────────────────────────────────────────────────────────────────

def _extract_with_newspaper(url: str) -> dict | None:
    """
    Try to extract article using the `newspaper3k` library.

    Returns:
        Dict with 'title', 'text', 'authors', 'publish_date' on success.
        None on failure.
    """
    try:
        from newspaper import Article  # lazy import – may not be installed

        article = Article(url)
        article.download()
        article.parse()

        text = article.text.strip()
        if len(text) < 100:
            return None  # Too short – probably a paywall / JS-rendered page

        return {
            "title": article.title or "Unknown Title",
            "text": text,
            "authors": ", ".join(article.authors) if article.authors else "Unknown",
            "publish_date": str(article.publish_date) if article.publish_date else "",
        }
    except Exception as exc:
        logger.debug("newspaper3k extraction failed: %s", exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Fallback Extractor – BeautifulSoup
# ─────────────────────────────────────────────────────────────────────────────

def _extract_with_bs4(url: str) -> dict | None:
    """
    Fallback: fetch HTML with requests and extract text with BeautifulSoup.

    Returns:
        Dict with 'title' and 'text' on success, None on failure.
    """
    try:
        response = requests.get(
            url,
            headers=_HEADERS,
            timeout=config.REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        # Remove boilerplate tags
        for tag in soup(["script", "style", "nav", "footer", "header",
                         "aside", "advertisement", "figure"]):
            tag.decompose()

        # Title
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else "Unknown Title"

        # Article body – prefer semantic elements
        body = (
            soup.find("article")
            or soup.find("main")
            or soup.find("div", class_=re.compile(r"(article|content|story|post)", re.I))
            or soup.find("body")
        )

        if body is None:
            return None

        # Collect paragraph text
        paragraphs = body.find_all("p")
        text = " ".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 40)

        if len(text) < 100:
            # Last resort: grab all visible text
            text = body.get_text(separator=" ", strip=True)

        return {"title": title, "text": text, "authors": "Unknown", "publish_date": ""}

    except requests.exceptions.Timeout:
        logger.warning("Request timed out for URL: %s", url)
        return None
    except requests.exceptions.RequestException as exc:
        logger.warning("HTTP request failed for %s: %s", url, exc)
        return None
    except Exception as exc:
        logger.error("BeautifulSoup extraction failed: %s", exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def scrape_article(url: str) -> dict:
    """
    Extract article content from a URL.

    Tries newspaper3k first; falls back to BeautifulSoup if that fails.

    Args:
        url: A valid HTTP/HTTPS URL to scrape.

    Returns:
        Dict with keys:
            - 'success' (bool)
            - 'title'   (str)
            - 'text'    (str)
            - 'authors' (str)
            - 'publish_date' (str)
            - 'error'   (str, only when success=False)
    """
    if not is_valid_url(url):
        return {
            "success": False,
            "title": "",
            "text": "",
            "authors": "",
            "publish_date": "",
            "error": "Invalid URL. Please enter a valid HTTP/HTTPS link.",
        }

    # ── Attempt 1: newspaper3k ────────────────────────────────────────────────
    result = _extract_with_newspaper(url)

    # ── Attempt 2: BeautifulSoup fallback ────────────────────────────────────
    if result is None:
        logger.info("Falling back to BeautifulSoup for %s", url)
        result = _extract_with_bs4(url)

    if result is None:
        return {
            "success": False,
            "title": "",
            "text": "",
            "authors": "",
            "publish_date": "",
            "error": (
                "Could not extract article content. "
                "The page may be behind a paywall, require JavaScript, "
                "or block automated requests."
            ),
        }

    # Truncate to avoid Gemini token limits
    text = result["text"][: config.MAX_ARTICLE_LENGTH]

    return {
        "success": True,
        "title": result.get("title", "Unknown Title"),
        "text": text,
        "authors": result.get("authors", "Unknown"),
        "publish_date": result.get("publish_date", ""),
        "error": "",
    }
