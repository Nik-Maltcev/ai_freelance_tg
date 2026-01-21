"""SQLAlchemy models for the crypto parser bot.

Simplified models: just ParseLog for tracking parse jobs.
Messages are stored in JSON files, not in DB.
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


class ParseLog(Base):
    """Model for storing parsing job logs."""

    __tablename__ = "parse_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="running")
    chats_parsed: Mapped[int] = mapped_column(Integer, default=0)
    messages_found: Mapped[int] = mapped_column(Integer, default=0)
    json_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<ParseLog(id={self.id}, status='{self.status}')>"
