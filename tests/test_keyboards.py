"""Property-based tests for bot keyboards.

Tests keyboard generation correctness using hypothesis.
"""

from datetime import datetime

import pytest
from hypothesis import given, settings, strategies as st

from bot.keyboards import (
    get_back_keyboard,
    get_categories_keyboard,
    get_pagination_keyboard,
    get_period_keyboard,
)
from core.models import Category


# Strategy for generating valid category slugs
category_slug_strategy = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789_",
    min_size=1,
    max_size=20,
)

# Strategy for generating valid category names
category_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "S")),
    min_size=1,
    max_size=50,
).filter(lambda x: x.strip())

# Strategy for generating Category objects
category_strategy = st.builds(
    Category,
    slug=category_slug_strategy,
    name=category_name_strategy,
    description=st.none() | st.text(max_size=100),
    is_active=st.just(True),
    chats_count=st.integers(min_value=1, max_value=100),
    last_parsed_at=st.none() | st.datetimes(),
)


# **Feature: freelance-parser-bot, Property 1: Categories keyboard contains all config categories**
@given(categories=st.lists(category_strategy, min_size=1, max_size=10))
@settings(max_examples=100, deadline=None)
def test_categories_keyboard_contains_all_categories_plus_all_button(
    categories: list[Category],
):
    """
    Property 1: Categories keyboard contains all config categories

    *For any* chat configuration with N categories, the generated categories
    keyboard SHALL contain exactly N+1 buttons (N categories + "All categories" button).

    **Validates: Requirements 1.1**
    """
    keyboard = get_categories_keyboard(categories)

    # Flatten all buttons from the keyboard
    all_buttons = []
    for row in keyboard.inline_keyboard:
        all_buttons.extend(row)

    # Count total buttons
    total_buttons = len(all_buttons)

    # Should have N categories + 1 "All categories" button
    expected_button_count = len(categories) + 1
    assert total_buttons == expected_button_count, (
        f"Expected {expected_button_count} buttons, got {total_buttons}"
    )

    # Verify all category slugs are present in callback data
    callback_data_list = [btn.callback_data for btn in all_buttons]
    for category in categories:
        expected_callback = f"cat_{category.slug}"
        assert expected_callback in callback_data_list, (
            f"Category '{category.slug}' not found in keyboard buttons"
        )

    # Verify "All categories" button is present
    assert "cat_all" in callback_data_list, (
        "All categories button not found in keyboard"
    )


def test_categories_keyboard_empty_list():
    """Test that empty category list still produces "All categories" button."""
    keyboard = get_categories_keyboard([])

    all_buttons = []
    for row in keyboard.inline_keyboard:
        all_buttons.extend(row)

    # Should have only the "All categories" button
    assert len(all_buttons) == 1
    assert all_buttons[0].callback_data == "cat_all"


def test_period_keyboard_structure():
    """Test that period keyboard has correct structure."""
    keyboard = get_period_keyboard("web_dev")

    # Should have 2 rows: period buttons and back button
    assert len(keyboard.inline_keyboard) == 2

    # First row should have 2 period buttons
    period_buttons = keyboard.inline_keyboard[0]
    assert len(period_buttons) == 2
    assert period_buttons[0].callback_data == "period_7_web_dev"
    assert period_buttons[1].callback_data == "period_30_web_dev"

    # Second row should have back button
    back_buttons = keyboard.inline_keyboard[1]
    assert len(back_buttons) == 1
    assert back_buttons[0].callback_data == "back_to_categories"


def test_back_keyboard_structure():
    """Test that back keyboard has correct structure."""
    keyboard = get_back_keyboard()

    # Should have 1 row with 1 button
    assert len(keyboard.inline_keyboard) == 1
    assert len(keyboard.inline_keyboard[0]) == 1
    assert keyboard.inline_keyboard[0][0].callback_data == "back_to_categories"


# **Feature: freelance-parser-bot, Property 3: Pagination controls correctness**
@given(
    category_slug=category_slug_strategy,
    period_days=st.sampled_from([7, 30]),
    page=st.integers(min_value=0, max_value=10),
    total_count=st.integers(min_value=0, max_value=100),
    page_size=st.integers(min_value=1, max_value=20),
)
@settings(max_examples=100, deadline=None)
def test_pagination_keyboard_controls_correctness(
    category_slug: str,
    period_days: int,
    page: int,
    total_count: int,
    page_size: int,
):
    """
    Property 3: Pagination controls correctness

    *For any* total count > page_size, the pagination keyboard SHALL include
    navigation buttons; for page > 0 include "previous", for (page+1)*page_size < total
    include "next".

    **Validates: Requirements 1.5**
    """
    keyboard = get_pagination_keyboard(
        category_slug=category_slug,
        period_days=period_days,
        page=page,
        total_count=total_count,
        page_size=page_size,
    )

    # Flatten all buttons
    all_buttons = []
    for row in keyboard.inline_keyboard:
        all_buttons.extend(row)

    callback_data_list = [btn.callback_data for btn in all_buttons]

    # Check for "Previous" button
    has_previous = page > 0
    has_previous_button = any(
        "page_" in cb and cb.startswith(f"page_{page - 1}_")
        for cb in callback_data_list
    )
    assert has_previous == has_previous_button, (
        f"Previous button presence mismatch: expected {has_previous}, got {has_previous_button}"
    )

    # Check for "Next" button
    has_next = (page + 1) * page_size < total_count
    has_next_button = any(
        "page_" in cb and cb.startswith(f"page_{page + 1}_")
        for cb in callback_data_list
    )
    assert has_next == has_next_button, (
        f"Next button presence mismatch: expected {has_next}, got {has_next_button}"
    )

    # Back button should always be present
    assert "back_to_categories" in callback_data_list, (
        "Back button should always be present"
    )
