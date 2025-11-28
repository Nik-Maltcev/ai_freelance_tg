"""Property-based tests for request display formatting.

Tests that request display contains all required fields.
"""

from datetime import datetime

import pytest
from hypothesis import given, settings, strategies as st

from bot.handlers.requests import format_request
from core.models import FreelanceRequest


# Strategy for generating valid request data
title_strategy = st.text(min_size=5, max_size=100).filter(lambda x: x.strip())
description_strategy = st.text(min_size=10, max_size=500).filter(lambda x: x.strip())
budget_strategy = st.one_of(
    st.just("Не указан"),
    st.integers(min_value=100, max_value=100000).map(lambda x: f"{x} руб"),
)
skills_strategy = st.lists(
    st.text(min_size=2, max_size=30).filter(lambda x: x.strip()),
    min_size=0,
    max_size=5,
)
contact_strategy = st.one_of(
    st.none(),
    st.text(min_size=3, max_size=100).filter(lambda x: x.strip()),
)
urgency_strategy = st.sampled_from(["normal", "urgent"])
category_strategy = st.sampled_from(["web_dev", "mobile", "design", "copywriting", "marketing"])


# Strategy for generating FreelanceRequest objects
freelance_request_strategy = st.builds(
    FreelanceRequest,
    id=st.integers(min_value=1, max_value=1000),
    category=category_strategy,
    title=title_strategy,
    description=description_strategy,
    budget=budget_strategy,
    skills=skills_strategy,
    contact=contact_strategy,
    urgency=urgency_strategy,
    source_chat=st.just("@test_chat"),
    source_message_id=st.integers(min_value=1, max_value=10000),
    message_date=st.datetimes(
        min_value=datetime(2024, 1, 1),
        max_value=datetime(2024, 12, 31),
    ),
    message_text_hash=st.text(min_size=64, max_size=64, alphabet="0123456789abcdef"),
    is_active=st.just(True),
)


# **Feature: freelance-parser-bot, Property 2: Pagination displays correct fields**
@given(request=freelance_request_strategy)
@settings(max_examples=100, deadline=None)
def test_request_display_contains_all_fields(request: FreelanceRequest):
    """
    Property 2: Pagination displays correct fields

    *For any* FreelanceRequest object, the formatted display string SHALL contain
    the title, description, budget, and urgency indicator.

    **Validates: Requirements 1.4**
    """
    formatted = format_request(request)
    
    # Check that title is present
    assert request.title in formatted, (
        f"Title '{request.title}' not found in formatted request"
    )
    
    # Check that description is present
    assert request.description in formatted, (
        f"Description '{request.description}' not found in formatted request"
    )
    
    # Check that budget is present
    assert request.budget in formatted, (
        f"Budget '{request.budget}' not found in formatted request"
    )
    
    # Check that urgency indicator is present
    if request.urgency == "urgent":
        assert "🔴" in formatted, "Urgent indicator (🔴) not found in formatted request"
    else:
        assert "🟢" in formatted, "Normal urgency indicator (🟢) not found in formatted request"
    
    # Check that all skills are present
    for skill in request.skills:
        assert str(skill) in formatted, (
            f"Skill '{skill}' not found in formatted request"
        )
    
    # Check that contact is present if provided
    if request.contact:
        assert request.contact in formatted, (
            f"Contact '{request.contact}' not found in formatted request"
        )
    
    # Check that date is present
    date_str = request.message_date.strftime('%d.%m.%Y %H:%M')
    assert date_str in formatted, (
        f"Date '{date_str}' not found in formatted request"
    )
