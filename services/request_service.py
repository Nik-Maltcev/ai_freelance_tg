"""Request service for managing freelance requests and parse logs.

Provides methods for CRUD operations on FreelanceRequest and ParseLog models.
"""

import hashlib
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import FreelanceRequest, ParseLog


def compute_hash(text: str) -> str:
    """Compute SHA256 hash of message text for deduplication.
    
    Args:
        text: Message text to hash.
        
    Returns:
        Hexadecimal SHA256 hash string (64 characters).
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class RequestService:
    """Service for managing freelance requests."""

    def __init__(self, session: AsyncSession):
        """Initialize with database session.
        
        Args:
            session: Async SQLAlchemy session.
        """
        self.session = session

    async def get_requests(
        self,
        category: str | None = None,
        days: int = 7,
        offset: int = 0,
        limit: int = 5,
    ) -> tuple[list[FreelanceRequest], int]:
        """Get paginated freelance requests.
        
        Args:
            category: Filter by category slug (None for all categories).
            days: Number of days to look back.
            offset: Pagination offset.
            limit: Maximum number of results.
            
        Returns:
            Tuple of (list of requests, total count).
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Base query conditions
        conditions = [
            FreelanceRequest.is_active == True,
            FreelanceRequest.message_date >= cutoff_date,
        ]
        if category:
            conditions.append(FreelanceRequest.category == category)

        # Count query
        count_query = select(func.count(FreelanceRequest.id)).where(*conditions)
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Data query with pagination
        query = (
            select(FreelanceRequest)
            .where(*conditions)
            .order_by(FreelanceRequest.message_date.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(query)
        requests = list(result.scalars().all())

        return requests, total

    async def save_requests(self, requests: list[dict[str, Any]]) -> int:
        """Save requests with deduplication by hash.
        
        Args:
            requests: List of request dictionaries with fields:
                - category, title, description, budget, skills, contact,
                - urgency, source_chat, source_message_id, message_date,
                - message_text (used for hash computation)
                
        Returns:
            Number of new requests saved (excluding duplicates).
        """
        if not requests:
            return 0

        saved_count = 0
        for req_data in requests:
            # Compute hash from message text
            message_text = req_data.pop("message_text", "")
            text_hash = compute_hash(message_text)

            # Check if hash already exists
            existing = await self.session.execute(
                select(FreelanceRequest.id).where(
                    FreelanceRequest.message_text_hash == text_hash
                )
            )
            if existing.scalar() is not None:
                continue  # Skip duplicate

            # Create new request
            request = FreelanceRequest(
                category=req_data.get("category", ""),
                title=req_data.get("title", ""),
                description=req_data.get("description", ""),
                budget=req_data.get("budget", "Не указан"),
                skills=req_data.get("skills", []),
                contact=req_data.get("contact"),
                urgency=req_data.get("urgency", "normal"),
                source_chat=req_data.get("source_chat", ""),
                source_message_id=req_data.get("source_message_id", 0),
                message_date=req_data.get("message_date", datetime.utcnow()),
                message_text_hash=text_hash,
                is_active=True,
            )
            self.session.add(request)
            saved_count += 1

        if saved_count > 0:
            await self.session.commit()

        return saved_count

    async def cleanup_old_requests(self, days: int = 30) -> int:
        """Delete requests older than TTL.
        
        Args:
            days: TTL in days. Requests older than this will be deleted.
            
        Returns:
            Number of deleted requests.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        stmt = delete(FreelanceRequest).where(
            FreelanceRequest.message_date < cutoff_date
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        
        return result.rowcount or 0

    async def create_parse_log(self) -> int:
        """Create a new parse log entry with 'running' status.
        
        Returns:
            ID of the created parse log.
        """
        log = ParseLog(status="running")
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        return log.id

    async def finish_parse_log(
        self,
        log_id: int,
        status: str,
        chats_parsed: int = 0,
        messages_found: int = 0,
        requests_extracted: int = 0,
        error_message: str | None = None,
    ) -> None:
        """Update parse log with final status and metrics.
        
        Args:
            log_id: ID of the parse log to update.
            status: Final status ('success' or 'failed').
            chats_parsed: Number of chats parsed.
            messages_found: Number of messages found.
            requests_extracted: Number of requests extracted.
            error_message: Error message if status is 'failed'.
        """
        result = await self.session.execute(
            select(ParseLog).where(ParseLog.id == log_id)
        )
        log = result.scalar_one_or_none()
        
        if log:
            log.finished_at = datetime.utcnow()
            log.status = status
            log.chats_parsed = chats_parsed
            log.messages_found = messages_found
            log.requests_extracted = requests_extracted
            log.error_message = error_message
            await self.session.commit()

    async def get_last_parse_log(self) -> ParseLog | None:
        """Get the most recent parse log.
        
        Returns:
            Most recent ParseLog or None if no logs exist.
        """
        result = await self.session.execute(
            select(ParseLog).order_by(ParseLog.started_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_stats_by_category(self) -> dict[str, int]:
        """Get request counts grouped by category.
        
        Returns:
            Dictionary mapping category slug to request count.
        """
        query = (
            select(
                FreelanceRequest.category,
                func.count(FreelanceRequest.id).label("count"),
            )
            .where(FreelanceRequest.is_active == True)
            .group_by(FreelanceRequest.category)
        )
        result = await self.session.execute(query)
        
        return {row.category: row.count for row in result.all()}
