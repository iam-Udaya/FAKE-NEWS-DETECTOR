"""
services/gemini_service.py - Google Gemini AI Integration
==========================================================
Uses the new google-genai SDK (google.genai) which replaces the
deprecated google-generativeai package.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from config import config

logger = logging.getLogger(__name__)


class GeminiService:
    """
    Manages interaction with Google Gemini API via the google-genai SDK.

    Usage:
        service = GeminiService()
        result  = service.analyze_article(title, text)
    """

    def __init__(self) -> None:
        if not config.GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY is missing. Add it to your .env file."
            )
        try:
            from google import genai
            from google.genai import types as genai_types
            self._client = genai.Client(api_key=config.GEMINI_API_KEY)
            self._genai_types = genai_types
        except ImportError:
            # Fallback to old SDK if new one not installed
            import google.generativeai as genai_old
            genai_old.configure(api_key=config.GEMINI_API_KEY)
            self._client = None
            self._old_model = genai_old.GenerativeModel(model_name=config.GEMINI_MODEL)
            self._genai_types = None

        logger.info("GeminiService initialized with model: %s", config.GEMINI_MODEL)

    # ─────────────────────────────────────────────────────────────────────────
    # Prompt Builder
    # ─────────────────────────────────────────────────────────────────────────

    def _build_prompt(self, title: str, text: str) -> str:
        """Construct the analysis prompt. Model must return ONLY valid JSON."""
        return f"""
You are an expert fact-checker and media literacy educator.
Analyze the following news article and respond with ONLY a valid JSON object.
Do NOT include any markdown fences, explanation, or text outside the JSON.

Article Title: {title}

Article Text:
{text}

Return this EXACT JSON structure (fill in all fields):

{{
  "credibility_score": <integer 0-100>,
  "confidence_score": <integer 0-100>,
  "verdict": "<Likely Real | Suspicious | Likely Fake>",
  "summary": "<2-3 sentence student-friendly summary of the article>",
  "detailed_explanation": "<3-5 paragraph expert explanation of the credibility assessment>",
  "key_claims": [
    "<claim 1>",
    "<claim 2>",
    "<claim 3>"
  ],
  "red_flags": [
    "<red flag 1 if any, else empty list>"
  ],
  "trust_indicators": [
    "<positive trust signal 1 if any, else empty list>"
  ],
  "fact_checking_suggestions": [
    "<actionable step 1 for students to verify this article>",
    "<actionable step 2>"
  ],
  "bias_indicators": "<description of any detected bias or 'None detected'>",
  "emotional_language_score": <integer 0-10 where 10 is highly emotional>,
  "source_credibility_notes": "<notes about the source/publisher if identifiable>",
  "missing_context": "<important context missing from the article or 'None identified'>"
}}

Scoring guide:
- credibility_score 70-100 → Likely Real
- credibility_score 40-69  → Suspicious
- credibility_score 0-39   → Likely Fake

Be accurate, educational, and suitable for high-school and university students.
""".strip()

    # ─────────────────────────────────────────────────────────────────────────
    # Response Parser
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_response(raw_text: str) -> dict[str, Any]:
        """Extract and parse JSON from Gemini's response."""
        cleaned = re.sub(r"```(?:json)?", "", raw_text, flags=re.IGNORECASE).strip()
        cleaned = cleaned.strip("`").strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON object found in Gemini response.")
        return json.loads(cleaned[start:end])

    # ─────────────────────────────────────────────────────────────────────────
    # Main Analysis Method
    # ─────────────────────────────────────────────────────────────────────────

    def analyze_article(self, title: str, text: str, max_retries: int = 2) -> dict[str, Any]:
        """Send the article to Gemini and return a structured analysis."""
        prompt = self._build_prompt(title, text[: config.MAX_ARTICLE_LENGTH])

        for attempt in range(max_retries + 1):
            try:
                logger.info("Sending article to Gemini (attempt %d)…", attempt + 1)

                if self._client is not None:
                    # New google-genai SDK
                    response = self._client.models.generate_content(
                        model=config.GEMINI_MODEL,
                        contents=prompt,
                    )
                    raw_text = response.text
                else:
                    # Old google-generativeai SDK fallback
                    response = self._old_model.generate_content(prompt)
                    raw_text = response.text

                if not raw_text:
                    raise ValueError("Gemini returned an empty response.")

                parsed = self._parse_response(raw_text)
                parsed = self._normalize_fields(parsed)
                logger.info("Gemini analysis complete. Verdict: %s", parsed.get("verdict"))
                return {"success": True, **parsed}

            except json.JSONDecodeError as exc:
                logger.warning("JSON parse error (attempt %d): %s", attempt + 1, exc)
                if attempt == max_retries:
                    return self._error_result(f"Could not parse Gemini response: {exc}")
                time.sleep(1)

            except Exception as exc:
                logger.error("Gemini API error (attempt %d): %s", attempt + 1, exc)
                if attempt == max_retries:
                    return self._error_result(str(exc))
                time.sleep(2 ** attempt)

        return self._error_result("Max retries exceeded.")

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _normalize_fields(data: dict) -> dict:
        """Ensure all expected fields exist with correct types."""
        defaults: dict[str, Any] = {
            "credibility_score": 50,
            "confidence_score": 50,
            "verdict": "Suspicious",
            "summary": "No summary available.",
            "detailed_explanation": "No detailed explanation available.",
            "key_claims": [],
            "red_flags": [],
            "trust_indicators": [],
            "fact_checking_suggestions": [],
            "bias_indicators": "None detected",
            "emotional_language_score": 5,
            "source_credibility_notes": "Unknown source",
            "missing_context": "None identified",
        }
        for key, default in defaults.items():
            if key not in data or data[key] is None:
                data[key] = default

        data["credibility_score"] = max(0, min(100, int(data["credibility_score"])))
        data["confidence_score"] = max(0, min(100, int(data["confidence_score"])))
        data["emotional_language_score"] = max(0, min(10, int(data["emotional_language_score"])))

        for list_field in ["key_claims", "red_flags", "trust_indicators", "fact_checking_suggestions"]:
            if not isinstance(data[list_field], list):
                data[list_field] = [str(data[list_field])]

        return data

    @staticmethod
    def _error_result(message: str) -> dict[str, Any]:
        """Return a standardized error result dictionary."""
        return {
            "success": False,
            "error": message,
            "credibility_score": 0,
            "confidence_score": 0,
            "verdict": "Error",
            "summary": "",
            "detailed_explanation": "",
            "key_claims": [],
            "red_flags": [],
            "trust_indicators": [],
            "fact_checking_suggestions": [],
            "bias_indicators": "",
            "emotional_language_score": 0,
            "source_credibility_notes": "",
            "missing_context": "",
        }
