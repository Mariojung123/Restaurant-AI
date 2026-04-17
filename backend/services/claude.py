"""
Claude API integration service.

Wraps the Anthropic SDK with two primary helpers:
- chat_with_claude: multi-turn text chat with a system prompt
- parse_image_with_claude: vision-enabled single-turn extraction from a base64 image
"""

import os
import json
from typing import Optional

from anthropic import Anthropic


# Model id used across the service. Update here to roll forward to a new Claude version.
CLAUDE_MODEL = "claude-sonnet-4-6"

# Default system prompt reflecting the product persona: friendly multilingual AI partner
DEFAULT_SYSTEM_PROMPT = (
    "You are a friendly AI operations partner for a small restaurant owner. "
    "Always respond in the same language the user writes in. "
    "Speak warmly and concisely, like a trusted colleague on a messenger app. "
    "Help interpret sales, inventory, and ordering data, and proactively suggest next steps."
)


def _get_client() -> Anthropic:
    """Build an Anthropic client from the ANTHROPIC_API_KEY environment variable."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Copy backend/.env.example to backend/.env."
        )
    return Anthropic(api_key=api_key)


def chat_with_claude(
    messages: list[dict],
    system_prompt: Optional[str] = None,
    max_tokens: int = 1024,
) -> str:
    """
    Send a multi-turn chat to Claude and return the assistant text reply.

    Args:
        messages: list of {"role": "user"|"assistant", "content": str} dicts
        system_prompt: optional override for the default system prompt
        max_tokens: generation cap for the reply

    Returns:
        Plain-text content of the assistant reply.
    """
    client = _get_client()
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system_prompt or DEFAULT_SYSTEM_PROMPT,
        messages=messages,
    )

    # Concatenate any text blocks returned by the API
    parts: list[str] = []
    for block in response.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "".join(parts).strip()


_RECIPE_PARSE_SYSTEM = (
    "You are a restaurant recipe analysis expert. "
    "Parse ingredient lists and return only a valid JSON array. Never include any other text."
)

_RECIPE_PARSE_PROMPT = """Parse the following ingredient list into a JSON array.

Rules:
- name: ingredient name
- quantity: estimated numeric value (float). For vague amounts like "a little", "some", "a handful" — estimate a reasonable quantity
- unit: standard unit (g, ml, ea, tsp, tbsp, etc.)
- quantity_display: original expression exactly as written
- reasoning: friendly 1-2 sentence explanation for the estimate, written in the SAME LANGUAGE as the input

Return format (JSON array only, no other text):
[
  {{
    "name": "ingredient name",
    "quantity": 15.0,
    "unit": "g",
    "quantity_display": "a handful",
    "reasoning": "A loose handful of chives is typically around 15g!"
  }}
]

Ingredient list:
{ingredient_text}"""


def parse_recipe_ingredients(ingredient_text: str) -> list[dict]:
    """
    Parse a natural language ingredient list into structured data with reasoning.

    Returns a list of dicts with keys: name, quantity, unit, quantity_display, reasoning.
    """
    client = _get_client()
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        system=_RECIPE_PARSE_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": _RECIPE_PARSE_PROMPT.format(ingredient_text=ingredient_text),
            }
        ],
    )

    raw = "".join(
        getattr(block, "text", "") for block in response.content
    ).strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)


def parse_image_with_claude(
    image_base64: str,
    prompt: str,
    media_type: str = "image/jpeg",
    max_tokens: int = 1024,
) -> str:
    """
    Ask Claude Vision to extract structured info from an image.

    Args:
        image_base64: the image encoded as a base64 string (no data: prefix)
        prompt: instruction describing what to extract (e.g. invoice fields)
        media_type: MIME type of the supplied image
        max_tokens: generation cap for the reply

    Returns:
        Plain-text content of the assistant reply.
    """
    client = _get_client()
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=DEFAULT_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_base64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )

    parts: list[str] = []
    for block in response.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "".join(parts).strip()
