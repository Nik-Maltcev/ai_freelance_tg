"""Property-based tests for request service module.

Tests hash computation, deduplication, TTL cleanup, skills JSON round-trip,
and stats aggregation using hypothesis.
"""

import json
from datetime import datetime, timedelta

import pytest
from hypothesis import given, settings, strategies as st

from services.request_service import compute_hash


# **Feature: freelance-parser-bot, Property 8: Hash computation determinism**
@given(text=st.text(min_size=1))
@settings(max_examples=100, deadline=None)
def test_hash_computation_determinism(text: str):
    """
    Property 8: Hash computation determinism

    *For any* message text, computing SHA256 hash twice SHALL produce
    identical results.

    **Validates: Requirements 4.1**
    """
    hash1 = compute_hash(text)
    hash2 = compute_hash(text)
    
    assert hash1 == hash2, "Hash computation must be deterministic"
    assert len(hash1) == 64, "SHA256 hash must be 64 hex characters"
    assert all(c in "0123456789abcdef" for c in hash1), "Hash must be hexadecimal"



# Async test fixtures and database tests
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from core.models import Base, FreelanceRequest


# Strategy for generating valid request data
request_text_strategy = st.text(min_size=50, max_size=500)
category_strategy = st.sampled_from(["web_dev", "mobile", "design", "copywriting", "marketing"])
title_strategy = st.text(min_size=5, max_size=100).filter(lambda x: x.strip())
budget_strategy = st.one_of(
    st.just("Не указан"),
    st.integers(min_value=100, max_value=100000).map(lambda x: f"{x} руб"),
)
skills_strategy = st.lists(
    st.text(min_size=2, max_size=30).filter(lambda x: x.strip()),
    min_size=0,
    max_size=5,
)


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_session():
    """Create async session with in-memory SQLite database."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_maker() as session:
        yield session
    
    await engine.dispose()


# **Feature: freelance-parser-bot, Property 9: Deduplication by hash**
@given(message_text=request_text_strategy)
@settings(max_examples=100, deadline=None)
def test_deduplication_by_hash(message_text: str):
    """
    Property 9: Deduplication by hash

    *For any* two requests with identical message_text_hash, saving both
    SHALL result in only one record in database.

    **Validates: Requirements 4.2**
    """
    async def run_test():
        from services.request_service import RequestService
        
        # Create fresh database for each test
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        async_session_maker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async with async_session_maker() as session:
            service = RequestService(session)
            
            # Create two requests with the same message text
            request1 = {
                "category": "web_dev",
                "title": "Test Request 1",
                "description": "Description 1",
                "budget": "1000 руб",
                "skills": ["Python"],
                "contact": "@test",
                "urgency": "normal",
                "source_chat": "@test_chat",
                "source_message_id": 1,
                "message_date": datetime.utcnow(),
                "message_text": message_text,
            }
            
            request2 = {
                "category": "web_dev",
                "title": "Test Request 2",  # Different title
                "description": "Description 2",  # Different description
                "budget": "2000 руб",
                "skills": ["JavaScript"],
                "contact": "@test2",
                "urgency": "urgent",
                "source_chat": "@test_chat2",
                "source_message_id": 2,
                "message_date": datetime.utcnow(),
                "message_text": message_text,  # Same message text = same hash
            }
            
            # Save first request
            saved1 = await service.save_requests([request1])
            assert saved1 == 1, "First request should be saved"
            
            # Try to save second request with same hash
            saved2 = await service.save_requests([request2])
            assert saved2 == 0, "Duplicate request should not be saved"
            
            # Verify only one record exists
            from sqlalchemy import select, func
            count_result = await session.execute(
                select(func.count(FreelanceRequest.id))
            )
            total_count = count_result.scalar()
            assert total_count == 1, f"Expected 1 record, got {total_count}"
        
        await engine.dispose()
    
    asyncio.run(run_test())



# **Feature: freelance-parser-bot, Property 10: TTL cleanup correctness**
@given(
    ttl_days=st.integers(min_value=1, max_value=365),
    old_days_offset=st.integers(min_value=1, max_value=100),
    new_days_offset=st.integers(min_value=0, max_value=100),
)
@settings(max_examples=100, deadline=None)
def test_ttl_cleanup_correctness(ttl_days: int, old_days_offset: int, new_days_offset: int):
    """
    Property 10: TTL cleanup correctness

    *For any* set of requests, cleanup with TTL of N days SHALL delete only
    requests where message_date < now - N days.

    **Validates: Requirements 4.3**
    """
    async def run_test():
        from services.request_service import RequestService, compute_hash
        from datetime import timezone
        
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        async_session_maker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async with async_session_maker() as session:
            service = RequestService(session)
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            
            # Create an old request (should be deleted)
            old_date = now - timedelta(days=ttl_days + old_days_offset)
            old_request = FreelanceRequest(
                category="web_dev",
                title="Old Request",
                description="Old description",
                budget="1000 руб",
                skills=["Python"],
                contact="@old",
                urgency="normal",
                source_chat="@chat",
                source_message_id=1,
                message_date=old_date,
                message_text_hash=compute_hash(f"old_message_{old_days_offset}"),
                is_active=True,
            )
            session.add(old_request)
            
            # Create a new request (should NOT be deleted)
            # Ensure new_date is within TTL (at least 1 day before cutoff)
            new_date = now - timedelta(days=max(0, ttl_days - new_days_offset - 1))
            new_request = FreelanceRequest(
                category="web_dev",
                title="New Request",
                description="New description",
                budget="2000 руб",
                skills=["JavaScript"],
                contact="@new",
                urgency="urgent",
                source_chat="@chat",
                source_message_id=2,
                message_date=new_date,
                message_text_hash=compute_hash(f"new_message_{new_days_offset}"),
                is_active=True,
            )
            session.add(new_request)
            await session.commit()
            
            # Verify both requests exist
            from sqlalchemy import select, func
            count_before = await session.execute(
                select(func.count(FreelanceRequest.id))
            )
            assert count_before.scalar() == 2, "Should have 2 requests before cleanup"
            
            # Run cleanup
            deleted = await service.cleanup_old_requests(days=ttl_days)
            
            # Verify old request was deleted
            assert deleted == 1, f"Expected 1 deleted, got {deleted}"
            
            # Verify new request still exists
            count_after = await session.execute(
                select(func.count(FreelanceRequest.id))
            )
            assert count_after.scalar() == 1, "Should have 1 request after cleanup"
            
            # Verify the remaining request is the new one
            remaining = await session.execute(
                select(FreelanceRequest)
            )
            remaining_request = remaining.scalar_one()
            assert remaining_request.title == "New Request", "New request should remain"
        
        await engine.dispose()
    
    asyncio.run(run_test())



# **Feature: freelance-parser-bot, Property 11: Skills JSON round-trip**
@given(
    skills=st.lists(
        st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        min_size=0,
        max_size=20,
    )
)
@settings(max_examples=100, deadline=None)
def test_skills_json_round_trip(skills: list[str]):
    """
    Property 11: Skills JSON round-trip

    *For any* list of skill strings, serializing to JSON and deserializing
    back SHALL produce an equivalent list.

    **Validates: Requirements 4.4, 4.5**
    """
    async def run_test():
        from services.request_service import RequestService, compute_hash
        from datetime import timezone
        
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        async_session_maker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async with async_session_maker() as session:
            service = RequestService(session)
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            
            # Create unique hash for this test
            unique_text = f"skills_test_{json.dumps(skills)}"
            
            # Save request with skills
            request_data = {
                "category": "web_dev",
                "title": "Skills Test",
                "description": "Testing skills round-trip",
                "budget": "1000 руб",
                "skills": skills,
                "contact": "@test",
                "urgency": "normal",
                "source_chat": "@chat",
                "source_message_id": 1,
                "message_date": now,
                "message_text": unique_text,
            }
            
            saved = await service.save_requests([request_data])
            assert saved == 1, "Request should be saved"
            
            # Retrieve the request
            from sqlalchemy import select
            result = await session.execute(
                select(FreelanceRequest).where(
                    FreelanceRequest.message_text_hash == compute_hash(unique_text)
                )
            )
            retrieved = result.scalar_one()
            
            # Verify skills round-trip
            assert retrieved.skills == skills, (
                f"Skills mismatch: expected {skills}, got {retrieved.skills}"
            )
        
        await engine.dispose()
    
    asyncio.run(run_test())



# **Feature: freelance-parser-bot, Property 12: Stats aggregation correctness**
@given(
    category_counts=st.dictionaries(
        keys=st.sampled_from(["web_dev", "mobile", "design", "copywriting", "marketing"]),
        values=st.integers(min_value=0, max_value=10),
        min_size=1,
        max_size=5,
    )
)
@settings(max_examples=100, deadline=None)
def test_stats_aggregation_correctness(category_counts: dict[str, int]):
    """
    Property 12: Stats aggregation correctness

    *For any* set of requests, stats by category SHALL return counts matching
    the actual number of requests per category.

    **Validates: Requirements 5.3**
    """
    async def run_test():
        from services.request_service import RequestService, compute_hash
        from datetime import timezone
        
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        async_session_maker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async with async_session_maker() as session:
            service = RequestService(session)
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            
            # Create requests for each category
            request_id = 0
            for category, count in category_counts.items():
                for i in range(count):
                    request = FreelanceRequest(
                        category=category,
                        title=f"Request {request_id}",
                        description=f"Description for {category}",
                        budget="1000 руб",
                        skills=["Python"],
                        contact="@test",
                        urgency="normal",
                        source_chat="@chat",
                        source_message_id=request_id,
                        message_date=now,
                        message_text_hash=compute_hash(f"stats_test_{category}_{i}_{request_id}"),
                        is_active=True,
                    )
                    session.add(request)
                    request_id += 1
            
            await session.commit()
            
            # Get stats
            stats = await service.get_stats_by_category()
            
            # Verify counts match
            for category, expected_count in category_counts.items():
                if expected_count > 0:
                    actual_count = stats.get(category, 0)
                    assert actual_count == expected_count, (
                        f"Category '{category}': expected {expected_count}, got {actual_count}"
                    )
            
            # Verify no extra categories
            for category in stats:
                assert category in category_counts, f"Unexpected category: {category}"
        
        await engine.dispose()
    
    asyncio.run(run_test())
