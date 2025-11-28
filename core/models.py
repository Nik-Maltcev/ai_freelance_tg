"""SQLAlchemy models for the freelance parser bot.

Defines database models for FreelanceRequest, ParseLog, and Category.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class FreelanceRequest(Base):
    """Model for storing parsed freelance requests."""

    __tablename__ = "freelance_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    budget: Mapped[str] = mapped_column(String(100), default="Не указан")
    skills: Mapped[list[Any]] = mapped_column(JSON, default=list)
    contact: Mapped[str] = mapped_column(String(500), nullable=True)
    urgency: Mapped[str] = mapped_column(String(20), default="normal")
    source_chat: Mapped[str] = mapped_column(String(100), nullable=False)
    source_message_id: Mapped[int] = mapped_column(Integer, nullable=False)
    message_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    message_text_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )
    parsed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Composite index for category + date queries
    __table_args__ = (
        Index("ix_requests_category_date", "category", "message_date"),
    )

    def __repr__(self) -> str:
        return f"<FreelanceRequest(id={self.id}, title='{self.title[:30]}...')>"


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
    requests_extracted: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<ParseLog(id={self.id}, status='{self.status}')>"


class Category(Base):
    """Model for storing category configuration."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    chats_count: Mapped[int] = mapped_column(Integer, default=0)
    last_parsed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<Category(slug='{self.slug}', name='{self.name}')>"
