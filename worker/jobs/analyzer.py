"""Gemini AI analyzer module for extracting freelance requests.

Provides GeminiAnalyzer class for analyzing messages using Google's
Gemini API and extracting structured freelance request data.
"""

import json
import logging
import math
from typing import Any

import google.generativeai as genai

from core.config import get_settings

logger = logging.getLogger(__name__)

# Prompt template for Gemini
ANALYSIS_PROMPT = """Analyze the following Telegram messages and extract ONLY genuine freelance job requests.
Ignore resumes, questions, spam, and non-job-related messages.

For each job request found, extract:
- title: Brief job title (max 200 chars)
- description: Job description
- budget: Budget if mentioned, otherwise "Не указан"
- skills: List of required skills
- contact: Contact information if provided
- urgency: "urgent" if urgent, otherwise "normal"
- source_message_id: The message_id from the input

Return a JSON array of extracted requests. If no valid job requests found, return empty array [].

Messages to analyze:
{messages}

Return ONLY valid JSON array, no other text."""


def split_into_batches(items: list[Any], batch_size: int) -> list[list[Any]]:
    """Split a list into batches of specified size.
    
    Args:
        items: List of items to split.
        batch_size: Maximum size of each batch.
        
    Returns:
        List of batches, each containing at most batch_size items.
    """
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    
    if not items:
        return []
    
    num_batches = math.ceil(len(items) / batch_size)
    return [
        items[i * batch_size:(i + 1) * batch_size]
        for i in range(num_batches)
    ]


def parse_gemini_response(response_text: str) -> list[dict[str, Any]]:
    """Parse JSON response from Gemini API.
    
    Extracts the JSON array from Gemini's response, handling
    potential markdown code blocks.
    
    Args:
        response_text: Raw response text from Gemini.
        
    Returns:
        List of extracted request dictionaries.
        
    Raises:
        json.JSONDecodeError: If response is not valid JSON.
    """
    text = response_text.strip()
    
    # Remove markdown code blocks if present
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    
    if text.endswith("```"):
        text = text[:-3]
    
    text = text.strip()
    
    # Parse JSON
    result = json.loads(text)
    
    if not isinstance(result, list):
        return []
    
    return result


def attach_metadata(
    requests: list[dict[str, Any]],
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Attach source metadata to extracted requests.
    
    Matches extracted requests with original messages by source_message_id
    and attaches source_chat, message_date, and category.
    
    Args:
        requests: List of extracted request dictionaries.
        messages: Original messages with metadata.
        
    Returns:
        Requests with metadata attached.
    """
    # Build lookup by message_id
    message_lookup = {
        msg["message_id"]: msg for msg in messages
    }
    
    enriched = []
    for req in requests:
        msg_id = req.get("source_message_id")
        if msg_id and msg_id in message_lookup:
            original = message_lookup[msg_id]
            req["source_chat"] = original.get("chat_id", "")
            req["message_date"] = original.get("message_date")
            req["category"] = original.get("category", "")
            req["message_text"] = original.get("text", "")
        enriched.append(req)
    
    return enriched


class GeminiAnalyzer:
    """Analyzer for extracting freelance requests using Gemini AI."""
    
    def __init__(self):
        """Initialize analyzer with Gemini API configuration."""
        settings = get_settings()
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel("gemini-1.5-flash")
        self.batch_size = settings.BATCH_SIZE

    async def analyze_batch(
        self,
        messages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Analyze a batch of messages using Gemini API.
        
        Sends messages to Gemini for analysis and extracts freelance
        requests from the response.
        
        Args:
            messages: List of message dictionaries with text and metadata.
            
        Returns:
            List of extracted request dictionaries with metadata attached.
        """
        if not messages:
            return []
        
        # Format messages for prompt
        formatted_messages = "\n\n".join(
            f"[message_id: {msg['message_id']}]\n{msg['text']}"
            for msg in messages
        )
        
        prompt = ANALYSIS_PROMPT.format(messages=formatted_messages)
        
        try:
            response = await self.model.generate_content_async(prompt)
            
            if not response.text:
                logger.warning("Empty response from Gemini")
                return []
            
            # Parse JSON response
            requests = parse_gemini_response(response.text)
            
            # Attach metadata from original messages
            enriched = attach_metadata(requests, messages)
            
            logger.info(f"Extracted {len(enriched)} requests from {len(messages)} messages")
            return enriched
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from Gemini: {e}")
            return []
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return []
    
    async def analyze_all(
        self,
        messages: list[dict[str, Any]],
        batch_size: int | None = None,
    ) -> list[dict[str, Any]]:
        """Analyze all messages in batches.
        
        Splits messages into batches and processes each batch
        through Gemini API.
        
        Args:
            messages: List of all messages to analyze.
            batch_size: Override default batch size (optional).
            
        Returns:
            Combined list of all extracted requests.
        """
        if not messages:
            return []
        
        size = batch_size or self.batch_size
        batches = split_into_batches(messages, size)
        
        logger.info(f"Analyzing {len(messages)} messages in {len(batches)} batches")
        
        all_requests = []
        for i, batch in enumerate(batches):
            logger.info(f"Processing batch {i + 1}/{len(batches)}")
            requests = await self.analyze_batch(batch)
            all_requests.extend(requests)
        
        logger.info(f"Total extracted: {len(all_requests)} requests")
        return all_requests
