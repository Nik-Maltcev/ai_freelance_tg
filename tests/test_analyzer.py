"""Property-based tests for analyzer module.

Tests batch splitting, JSON response parsing, and metadata preservation using hypothesis.
"""

import json
import math
from datetime import datetime

import pytest
from hypothesis import given, settings, assume, strategies as st

from worker.jobs.analyzer import (
    split_into_batches,
    parse_gemini_response,
    attach_metadata,
)


# ============================================================================
# Strategies
# ============================================================================

def message_strategy():
    """Generate a message dictionary with all required fields."""
    return st.fixed_dictionaries({
        "text": st.text(min_size=50, max_size=500),
        "message_id": st.integers(min_value=1, max_value=1000000),
        "message_date": st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime(2030, 1, 1),
        ),
        "chat_id": st.text(min_size=1, max_size=50),
        "is_bot": st.just(False),
        "category": st.sampled_from(["web_dev", "mobile", "design", "marketing"]),
    })


def request_strategy():
    """Generate a valid request dictionary as Gemini would return."""
    return st.fixed_dictionaries({
        "title": st.text(min_size=1, max_size=200),
        "description": st.text(min_size=1, max_size=1000),
        "budget": st.one_of(
            st.just("Не указан"),
            st.text(min_size=1, max_size=50).map(lambda x: f"{x} руб"),
        ),
        "skills": st.lists(st.text(min_size=1, max_size=30), min_size=0, max_size=5),
        "contact": st.text(min_size=0, max_size=100),
        "urgency": st.sampled_from(["urgent", "normal"]),
        "source_message_id": st.integers(min_value=1, max_value=1000000),
    })



# ============================================================================
# Property 5: Batch splitting correctness
# ============================================================================

# **Feature: freelance-parser-bot, Property 5: Batch splitting correctness**
@given(
    messages=st.lists(message_strategy(), min_size=0, max_size=200),
    batch_size=st.integers(min_value=1, max_value=100),
)
@settings(max_examples=100, deadline=None)
def test_batch_splitting_correctness(messages: list[dict], batch_size: int):
    """
    Property 5: Batch splitting correctness

    *For any* list of N messages and batch_size B, the analyzer SHALL split
    into ceil(N/B) batches, each with at most B messages.

    **Validates: Requirements 3.1**
    """
    batches = split_into_batches(messages, batch_size)
    
    # Empty input should return empty list
    if not messages:
        assert batches == [], "Empty messages should return empty batches"
        return
    
    # Verify number of batches
    expected_num_batches = math.ceil(len(messages) / batch_size)
    assert len(batches) == expected_num_batches, (
        f"Expected {expected_num_batches} batches, got {len(batches)}"
    )
    
    # Verify each batch has at most batch_size messages
    for i, batch in enumerate(batches):
        assert len(batch) <= batch_size, (
            f"Batch {i} has {len(batch)} messages, exceeds batch_size {batch_size}"
        )
    
    # Verify all messages are preserved (no loss)
    total_messages = sum(len(batch) for batch in batches)
    assert total_messages == len(messages), (
        f"Total messages in batches ({total_messages}) != input ({len(messages)})"
    )
    
    # Verify order is preserved
    flattened = [msg for batch in batches for msg in batch]
    assert flattened == messages, "Batch splitting should preserve message order"


# ============================================================================
# Property 6: Gemini JSON response parsing
# ============================================================================

# **Feature: freelance-parser-bot, Property 6: Gemini JSON response parsing**
@given(requests=st.lists(request_strategy(), min_size=0, max_size=20))
@settings(max_examples=100, deadline=None)
def test_gemini_json_response_parsing(requests: list[dict]):
    """
    Property 6: Gemini JSON response parsing

    *For any* valid JSON response from Gemini containing request objects,
    the parser SHALL extract all fields (title, description, budget, skills,
    contact, urgency, source_message_id).

    **Validates: Requirements 3.3**
    """
    # Create JSON response as Gemini would return
    json_response = json.dumps(requests)
    
    parsed = parse_gemini_response(json_response)
    
    # All valid requests should be parsed
    assert len(parsed) == len(requests), (
        f"Expected {len(requests)} requests, got {len(parsed)}"
    )
    
    # Verify all required fields are present in each parsed request
    required_fields = {"title", "description", "budget", "skills", "contact", "urgency", "source_message_id"}
    
    for i, parsed_req in enumerate(parsed):
        for field in required_fields:
            assert field in parsed_req, (
                f"Request {i} missing field '{field}'"
            )
        
        # Verify source_message_id matches original
        assert parsed_req["source_message_id"] == requests[i]["source_message_id"], (
            f"source_message_id mismatch for request {i}"
        )
        
        # Verify skills is a list
        assert isinstance(parsed_req["skills"], list), (
            f"skills should be a list for request {i}"
        )
        
        # Verify urgency is valid
        assert parsed_req["urgency"] in ("urgent", "normal"), (
            f"Invalid urgency '{parsed_req['urgency']}' for request {i}"
        )


# Test parsing with markdown code blocks
@given(requests=st.lists(request_strategy(), min_size=1, max_size=10))
@settings(max_examples=100, deadline=None)
def test_json_parsing_with_markdown_blocks(requests: list[dict]):
    """
    Verify parser handles JSON wrapped in markdown code blocks.
    """
    json_content = json.dumps(requests)
    
    # Test with ```json wrapper
    wrapped_json = f"```json\n{json_content}\n```"
    parsed = parse_gemini_response(wrapped_json)
    assert len(parsed) == len(requests)
    
    # Test with ``` wrapper
    wrapped_plain = f"```\n{json_content}\n```"
    parsed = parse_gemini_response(wrapped_plain)
    assert len(parsed) == len(requests)



# ============================================================================
# Property 7: Metadata preservation
# ============================================================================

# **Feature: freelance-parser-bot, Property 7: Metadata preservation**
@given(
    messages=st.lists(message_strategy(), min_size=1, max_size=20),
)
@settings(max_examples=100, deadline=None)
def test_metadata_preservation(messages: list[dict]):
    """
    Property 7: Metadata preservation

    *For any* extracted request, the system SHALL attach source_chat,
    message_date, and category from the original message.

    **Validates: Requirements 3.5**
    """
    # Create requests that reference the messages
    requests = [
        {
            "title": f"Job {i}",
            "description": "Test description",
            "budget": "Не указан",
            "skills": [],
            "contact": "@test",
            "urgency": "normal",
            "source_message_id": msg["message_id"],
        }
        for i, msg in enumerate(messages)
    ]
    
    enriched = attach_metadata(requests, messages)
    
    # All requests should be enriched
    assert len(enriched) == len(requests)
    
    # Build lookup for verification
    message_lookup = {msg["message_id"]: msg for msg in messages}
    
    for req in enriched:
        source_id = req["source_message_id"]
        original_msg = message_lookup.get(source_id)
        
        if original_msg:
            # Verify metadata is attached
            assert "source_chat" in req, "source_chat should be attached"
            assert "message_date" in req, "message_date should be attached"
            assert "category" in req, "category should be attached"
            
            # Verify metadata matches original message
            assert req["source_chat"] == original_msg["chat_id"], (
                f"source_chat mismatch: {req['source_chat']} != {original_msg['chat_id']}"
            )
            assert req["message_date"] == original_msg["message_date"], (
                "message_date mismatch"
            )
            assert req["category"] == original_msg["category"], (
                f"category mismatch: {req['category']} != {original_msg['category']}"
            )


# Test metadata preservation with unmatched requests
@given(
    messages=st.lists(message_strategy(), min_size=1, max_size=10),
)
@settings(max_examples=100, deadline=None)
def test_metadata_preservation_unmatched_requests(messages: list[dict]):
    """
    Verify that requests without matching messages are still included in output
    but without metadata fields added (since there's no source to copy from).
    """
    # Create requests with non-existent message IDs
    requests = [
        {
            "title": "Unmatched job",
            "description": "Test",
            "budget": "Не указан",
            "skills": [],
            "contact": "",
            "urgency": "normal",
            "source_message_id": 999999999,  # Non-existent ID
        }
    ]
    
    enriched = attach_metadata(requests, messages)
    
    # Request should still be in output (not dropped)
    assert len(enriched) == 1
    # Original fields should be preserved
    assert enriched[0]["title"] == "Unmatched job"
    assert enriched[0]["source_message_id"] == 999999999
