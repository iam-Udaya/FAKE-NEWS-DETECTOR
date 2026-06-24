"""
database.py - MongoDB Connection & CRUD Operations
===================================================
Handles all direct MongoDB interactions: connect, insert, find, delete.
Uses PyMongo with connection pooling.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import pymongo
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import (
    ConnectionFailure,
    OperationFailure,
    ServerSelectionTimeoutError,
)
from bson import ObjectId

from config import config

# Fix for MongoDB Atlas SRV DNS resolution on networks with strict DNS policies.
# We create a Resolver instance first (default_resolver is None until used),
# then assign Cloudflare DNS servers and set it as the global default.
try:
    import dns.resolver
    _resolver = dns.resolver.Resolver()
    _resolver.nameservers = ["1.1.1.1", "1.0.0.1"]
    dns.resolver.default_resolver = _resolver
except Exception:
    pass  # Non-fatal: PyMongo will use the system DNS if this fails

logger = logging.getLogger(__name__)


class MongoDB:
    """
    Singleton-like wrapper around PyMongo that manages connection pooling
    and exposes high-level CRUD helpers for the `analyses` collection.
    """

    _client: MongoClient | None = None
    _db: Database | None = None
    _collection: Collection | None = None

    # ──────────────────────────────────────────────────────────────────────────
    # Connection Management
    # ──────────────────────────────────────────────────────────────────────────

    @classmethod
    def connect(cls) -> bool:
        """
        Establish a connection to MongoDB Atlas.

        Returns:
            True if connected successfully, False otherwise.
        """
        if cls._client is not None:
            return True  # already connected

        if not config.MONGODB_URI:
            logger.error("MONGODB_URI is not set in .env")
            return False

        try:
            cls._client = MongoClient(
                config.MONGODB_URI,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=10000,
            )
            # Ping the server to confirm the connection
            cls._client.admin.command("ping")
            cls._db = cls._client[config.MONGODB_DB_NAME]
            cls._collection = cls._db[config.MONGODB_COLLECTION]
            # Create indexes for faster queries
            cls._ensure_indexes()
            logger.info("Connected to MongoDB Atlas: %s", config.MONGODB_DB_NAME)
            return True

        except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
            logger.error("MongoDB connection failed: %s", exc)
            cls._client = None
            return False

    @classmethod
    def disconnect(cls) -> None:
        """Close the MongoDB connection."""
        if cls._client:
            cls._client.close()
            cls._client = None
            cls._db = None
            cls._collection = None
            logger.info("MongoDB connection closed.")

    @classmethod
    def is_connected(cls) -> bool:
        """Return True if the database connection is live."""
        if cls._client is None:
            return False
        try:
            cls._client.admin.command("ping")
            return True
        except Exception:
            return False

    @classmethod
    def _get_collection(cls) -> Collection:
        """Return the analyses collection, reconnecting if needed."""
        if cls._collection is None:
            cls.connect()
        if cls._collection is None:
            raise RuntimeError("MongoDB is not connected. Check your MONGODB_URI.")
        return cls._collection

    @classmethod
    def _ensure_indexes(cls) -> None:
        """Create indexes to support the dashboard queries."""
        col = cls._collection
        if col is None:
            return
        col.create_index([("created_at", pymongo.DESCENDING)])
        col.create_index([("verdict", pymongo.ASCENDING)])
        col.create_index([("credibility_score", pymongo.DESCENDING)])
        col.create_index(
            [("article_title", pymongo.TEXT), ("article_text", pymongo.TEXT)],
            name="text_search_index",
        )

    # ──────────────────────────────────────────────────────────────────────────
    # CRUD Operations
    # ──────────────────────────────────────────────────────────────────────────

    @classmethod
    def save_analysis(cls, document: dict[str, Any]) -> str | None:
        """
        Insert an analysis document into MongoDB.

        Args:
            document: The analysis dictionary to store.

        Returns:
            The inserted document's string ID, or None on failure.
        """
        try:
            col = cls._get_collection()
            document["created_at"] = datetime.now(timezone.utc).isoformat()
            result = col.insert_one(document)
            return str(result.inserted_id)
        except OperationFailure as exc:
            logger.error("Failed to save analysis: %s", exc)
            return None

    @classmethod
    def get_all_analyses(
        cls,
        limit: int = 100,
        skip: int = 0,
        sort_field: str = "created_at",
        sort_order: int = pymongo.DESCENDING,
    ) -> list[dict]:
        """
        Fetch paginated analyses, newest first by default.

        Returns:
            List of document dictionaries with '_id' converted to string.
        """
        try:
            col = cls._get_collection()
            cursor = (
                col.find({})
                .sort(sort_field, sort_order)
                .skip(skip)
                .limit(limit)
            )
            return [cls._serialize(doc) for doc in cursor]
        except Exception as exc:
            logger.error("Failed to fetch analyses: %s", exc)
            return []

    @classmethod
    def search_analyses(
        cls,
        keyword: str = "",
        verdict_filter: str = "All",
        limit: int = 100,
    ) -> list[dict]:
        """
        Search analyses by keyword (full-text) and/or verdict.

        Args:
            keyword: Search term for title/text.
            verdict_filter: One of 'All', 'Likely Real', 'Suspicious', 'Likely Fake'.
            limit: Maximum number of results.

        Returns:
            List of matching document dictionaries.
        """
        try:
            col = cls._get_collection()
            query: dict[str, Any] = {}

            if keyword.strip():
                # Try full-text search first; fall back to regex on failure
                try:
                    query["$text"] = {"$search": keyword.strip()}
                except Exception:
                    query["article_text"] = {
                        "$regex": keyword.strip(),
                        "$options": "i",
                    }

            if verdict_filter and verdict_filter != "All":
                query["verdict"] = verdict_filter

            cursor = col.find(query).sort("created_at", pymongo.DESCENDING).limit(limit)
            return [cls._serialize(doc) for doc in cursor]
        except Exception as exc:
            logger.error("Search failed: %s", exc)
            return []

    @classmethod
    def get_analysis_by_id(cls, doc_id: str) -> dict | None:
        """Fetch a single analysis by its string ObjectId."""
        try:
            col = cls._get_collection()
            doc = col.find_one({"_id": ObjectId(doc_id)})
            return cls._serialize(doc) if doc else None
        except Exception as exc:
            logger.error("Failed to fetch analysis %s: %s", doc_id, exc)
            return None

    @classmethod
    def delete_analysis(cls, doc_id: str) -> bool:
        """
        Delete an analysis by its string ObjectId.

        Returns:
            True if deleted, False otherwise.
        """
        try:
            col = cls._get_collection()
            result = col.delete_one({"_id": ObjectId(doc_id)})
            return result.deleted_count > 0
        except Exception as exc:
            logger.error("Failed to delete analysis %s: %s", doc_id, exc)
            return False

    @classmethod
    def get_statistics(cls) -> dict[str, Any]:
        """
        Aggregate dashboard statistics from the database.

        Returns:
            Dictionary with total, average score, and verdict counts.
        """
        try:
            col = cls._get_collection()
            total = col.count_documents({})

            # Average credibility score
            pipeline_avg = [
                {"$group": {"_id": None, "avg_score": {"$avg": "$credibility_score"}}}
            ]
            avg_result = list(col.aggregate(pipeline_avg))
            avg_score = round(avg_result[0]["avg_score"], 1) if avg_result else 0.0

            # Verdict distribution
            pipeline_verdict = [
                {"$group": {"_id": "$verdict", "count": {"$sum": 1}}}
            ]
            verdict_data = {
                row["_id"]: row["count"]
                for row in col.aggregate(pipeline_verdict)
                if row["_id"]
            }

            # Recent 7 analyses for the trend chart
            recent = cls.get_all_analyses(limit=7)

            return {
                "total": total,
                "avg_credibility": avg_score,
                "verdict_distribution": verdict_data,
                "recent": recent,
            }
        except Exception as exc:
            logger.error("Failed to compute statistics: %s", exc)
            return {
                "total": 0,
                "avg_credibility": 0.0,
                "verdict_distribution": {},
                "recent": [],
            }

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _serialize(doc: dict) -> dict:
        """Convert ObjectId fields to strings for JSON compatibility."""
        if doc and "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return doc
