"""Property-based tests for configuration module.

Tests YAML config parsing correctness using hypothesis.
"""

import tempfile
from pathlib import Path

import pytest
import yaml
from hypothesis import given, settings, strategies as st

from core.config import load_chats_config


# Strategy for generating valid category names (non-empty strings)
category_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "S")),
    min_size=1,
    max_size=50,
).filter(lambda x: x.strip())

# Strategy for generating valid chat identifiers
chat_id_strategy = st.one_of(
    st.integers(min_value=-1000000000000, max_value=-1),  # Telegram group IDs
    st.text(min_size=1, max_size=32).filter(lambda x: x.strip()),  # Usernames
)

# Strategy for generating a single category
category_strategy = st.fixed_dictionaries({
    "name": category_name_strategy,
    "chats": st.lists(chat_id_strategy, min_size=1, max_size=10),
})

# Strategy for generating valid categories dict
categories_dict_strategy = st.dictionaries(
    keys=st.text(
        alphabet=st.characters(whitelist_categories=("L", "N")),
        min_size=1,
        max_size=20,
    ).filter(lambda x: x.strip() and x.isidentifier()),
    values=category_strategy,
    min_size=1,
    max_size=5,
)


# **Feature: freelance-parser-bot, Property 14: YAML config parsing**
@given(categories=categories_dict_strategy)
@settings(max_examples=100, deadline=None)
def test_yaml_config_parsing_produces_categories_with_required_fields(categories: dict):
    """
    Property 14: YAML config parsing

    *For any* valid chats.yaml content, parsing SHALL produce a dict with
    "categories" key containing category objects with "name", "chats" fields.

    **Validates: Requirements 6.2**
    """
    # Create a valid YAML config
    config_content = {"categories": categories}

    # Write to temporary file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        yaml.safe_dump(config_content, f, allow_unicode=True)
        temp_path = f.name

    try:
        # Parse the config
        result = load_chats_config(temp_path)

        # Verify the result has "categories" key
        assert "categories" in result, "Result must contain 'categories' key"

        # Verify each category has required fields
        for slug, category in result["categories"].items():
            assert "name" in category, f"Category '{slug}' must have 'name' field"
            assert "chats" in category, f"Category '{slug}' must have 'chats' field"

        # Verify the number of categories matches
        assert len(result["categories"]) == len(categories), (
            "Number of categories must match input"
        )

    finally:
        # Cleanup
        Path(temp_path).unlink(missing_ok=True)


def test_yaml_config_missing_file_raises_error():
    """Test that missing config file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_chats_config("nonexistent/path/config.yaml")


def test_yaml_config_missing_categories_key_raises_error():
    """Test that config without 'categories' key raises ValueError."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        yaml.safe_dump({"other_key": "value"}, f)
        temp_path = f.name

    try:
        with pytest.raises(ValueError, match="must contain 'categories' key"):
            load_chats_config(temp_path)
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_yaml_config_category_missing_name_raises_error():
    """Test that category without 'name' field raises ValueError."""
    config = {
        "categories": {
            "test_cat": {"chats": ["@test_chat"]}
        }
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        yaml.safe_dump(config, f)
        temp_path = f.name

    try:
        with pytest.raises(ValueError, match="must have 'name' field"):
            load_chats_config(temp_path)
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_yaml_config_category_missing_chats_raises_error():
    """Test that category without 'chats' field raises ValueError."""
    config = {
        "categories": {
            "test_cat": {"name": "Test Category"}
        }
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        yaml.safe_dump(config, f)
        temp_path = f.name

    try:
        with pytest.raises(ValueError, match="must have 'chats' field"):
            load_chats_config(temp_path)
    finally:
        Path(temp_path).unlink(missing_ok=True)
