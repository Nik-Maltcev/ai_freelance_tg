"""Property-based tests for parser module.

Tests message filtering using hypothesis.
"""

from datetime import datetime, timezone

import pytest
from hypothesis import given, settings, strategies as st

from worker.jobs.parser import filter_messages


# Strategy for generating message text
message_text_strategy = st.text(min_size=0, max_size=200)


# Strategy for generating a single message
def message_strategy():
    """Generate a message dictionary with text and is_bot fields."""
    return st.fixed_dictionaries({
        "text": message_text_strategy,
        "message_id": st.integers(min_value=1, max_value=1000000),
        "message_date": st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime(2030, 1, 1),
        ),
        "chat_id": st.text(min_size=1, max_size=50),
        "is_bot": st.booleans(),
    })


# **Feature: freelance-parser-bot, Property 4: Message filtering by length and sender**
@given(messages=st.lists(message_strategy(), min_size=0, max_size=50))
@settings(max_examples=100, deadline=None)
def test_message_filtering_by_length_and_sender(messages: list[dict]):
    """
    Property 4: Message filtering by length and sender

    *For any* list of messages, the parser SHALL return only messages where
    text length >= 50 AND sender is not a bot.

    **Validates: Requirements 2.3, 2.5**
    """
    filtered = filter_messages(messages)
    
    # All filtered messages must have text length >= 50
    for msg in filtered:
        assert len(msg.get("text", "")) >= 50, (
            f"Message with text length {len(msg.get('text', ''))} should not pass filter"
        )
    
    # All filtered messages must not be from bots
    for msg in filtered:
        assert not msg.get("is_bot", False), (
            "Message from bot should not pass filter"
        )
    
    # All messages meeting criteria must be in filtered list
    expected_count = sum(
        1 for msg in messages
        if len(msg.get("text", "")) >= 50 and not msg.get("is_bot", False)
    )
    assert len(filtered) == expected_count, (
        f"Expected {expected_count} messages, got {len(filtered)}"
    )


# Additional test to verify filter preserves message data
@given(messages=st.lists(message_strategy(), min_size=1, max_size=20))
@settings(max_examples=100, deadline=None)
def test_filter_preserves_message_data(messages: list[dict]):
    """
    Verify that filtering preserves all original message fields.
    """
    filtered = filter_messages(messages)
    
    # Each filtered message should be the exact same object from input
    for filtered_msg in filtered:
        assert filtered_msg in messages, (
            "Filtered message should be from original list"
        )
        # Verify all fields are preserved
        assert "text" in filtered_msg
        assert "message_id" in filtered_msg
        assert "message_date" in filtered_msg
        assert "chat_id" in filtered_msg
        assert "is_bot" in filtered_msg
