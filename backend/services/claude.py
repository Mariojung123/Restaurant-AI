"""
Claude API integration service.

Wraps the Anthropic SDK with primary helpers:
- chat_with_claude: multi-turn text chat with optional tool use
- parse_recipe_ingredients: ingredient text → structured JSON
- parse_image_with_claude: vision-enabled extraction from a base64 image
"""

import os
import json
from typing import Optional

import anthropic
from anthropic import Anthropic
from anthropic.types import Message


CLAUDE_MODEL = "claude-sonnet-4-6"
CLAUDE_HAIKU_MODEL = "claude-haiku-4-5-20251001"

DEFAULT_SYSTEM_PROMPT = (
    "You are a friendly AI operations partner for a small restaurant owner. "
    "Always respond in the same language the user writes in. "
    "Speak warmly and concisely, like a trusted colleague on a messenger app. "
    "Help interpret sales, inventory, and ordering data, and proactively suggest next steps.\n\n"
    "When a user wants to register a recipe: parse all ingredients into standard units (g, mL, ea), "
    "present a clear summary with quantities, and ask for explicit confirmation. "
    "Only call the register_recipe tool after the user clearly confirms (e.g. 'yes', '네', 'ok'). "
    "If the user cancels or says no, acknowledge and do not call the tool."
)

RECIPE_TOOL: dict = {
    "name": "register_recipe",
    "description": (
        "Register a new recipe to the database. "
        "Always parse all ingredients with standard units first, present a full summary to the user, "
        "and ask for explicit confirmation. Only call this tool after the user confirms."
    ),
    "input_schema": {
        "type": "object",
        "required": ["name", "price", "items"],
        "properties": {
            "name": {"type": "string", "description": "Recipe name"},
            "price": {"type": "number", "description": "Price in CAD dollars"},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "quantity", "unit", "quantity_display"],
                    "properties": {
                        "name": {"type": "string", "description": "Ingredient name in English"},
                        "quantity": {"type": "number"},
                        "unit": {"type": "string", "enum": ["g", "mL", "ea"]},
                        "quantity_display": {
                            "type": "string",
                            "description": "Original expression as user wrote it",
                        },
                    },
                },
            },
        },
    },
}

_client: Optional[Anthropic] = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Copy backend/.env.example to backend/.env."
            )
        _client = Anthropic(api_key=api_key)
    return _client


def strip_fences(raw: str) -> str:
    """Remove markdown code fences from a Claude response string."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return raw.strip()


def extract_text(message: Message) -> str:
    """Extract concatenated text from all TextBlock entries in a Message."""
    return "".join(
        block.text for block in message.content if block.type == "text"
    ).strip()


def extract_tool_use_block(message: Message) -> tuple[str, str, dict] | None:
    """Return (tool_use_id, tool_name, input) for the first tool_use block, or None."""
    for block in message.content:
        if block.type == "tool_use":
            return block.id, block.name, block.input
    return None


def message_content_to_dicts(content: list) -> list[dict]:
    """Convert SDK content block objects to plain dicts for follow-up API calls."""
    result = []
    for block in content:
        if block.type == "text":
            result.append({"type": "text", "text": block.text})
        elif block.type == "tool_use":
            result.append(
                {"type": "tool_use", "id": block.id, "name": block.name, "input": block.input}
            )
    return result


def chat_with_claude(
    messages: list[dict],
    system_prompt: Optional[str] = None,
    tools: Optional[list[dict]] = None,
    max_tokens: int = 1024,
) -> Message:
    """Send a multi-turn chat to Claude and return the raw Message object.

    Callers inspect stop_reason and content to handle tool_use or text responses.
    Raises RuntimeError on API failure.
    """
    client = _get_client()
    kwargs: dict = {
        "model": CLAUDE_MODEL,
        "max_tokens": max_tokens,
        "system": system_prompt or DEFAULT_SYSTEM_PROMPT,
        "messages": messages,
    }
    if tools:
        kwargs["tools"] = tools
    try:
        return client.messages.create(**kwargs)
    except anthropic.APIError as e:
        raise RuntimeError(f"Claude API error: {e}") from e


_RECIPE_PARSE_SYSTEM = (
    "You are a restaurant recipe analysis expert. "
    "Parse ingredient lists and return only a valid JSON array. Never include any other text."
)

_RECIPE_PARSE_PROMPT = """Parse the following ingredient list into a JSON array.

Rules:
- name: ingredient name in English
- quantity: numeric value converted to standard units (g or mL preferred). Use your culinary knowledge to convert any vague or non-standard expressions (e.g. "a pinch", "한 줌", "a few cloves", "두부 반 모", "a drizzle of") to the most reasonable numeric estimate in g or mL.
- unit: g, mL, or ea
- quantity_display: original expression exactly as written (preserve Korean/English as-is)
- reasoning: if the original was a vague or non-standard expression, write a brief friendly explanation in the SAME LANGUAGE as the input (e.g. "한 줌은 채소 기준 약 30g입니다"). If the original was already a precise measurement (e.g. "120g"), set reasoning to null.

Return format (JSON array only, no other text):
[
  {{
    "name": "ingredient name",
    "quantity": 15.0,
    "unit": "g",
    "quantity_display": "한 줌",
    "reasoning": "한 줌은 채소 기준 약 30g 정도 입니다!"
  }}
]

Ingredient list:
{ingredient_text}"""


def parse_recipe_ingredients(ingredient_text: str) -> list[dict]:
    """Parse a natural language ingredient list into structured data with reasoning."""
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
    raw = "".join(getattr(b, "text", "") for b in response.content).strip()
    return json.loads(strip_fences(raw))


_VISION_EXTRACTION_SYSTEM = (
    "You are a data extraction assistant. "
    "Extract structured data from images exactly as instructed. "
    "Return only valid JSON with no extra text or explanation."
)


def parse_image_with_claude(
    image_base64: str,
    prompt: str,
    media_type: str = "image/jpeg",
    max_tokens: int = 1024,
) -> str:
    """Ask Claude Vision to extract structured info from an image."""
    client = _get_client()
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=_VISION_EXTRACTION_SYSTEM,
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
    return "".join(getattr(b, "text", "") for b in response.content).strip()
