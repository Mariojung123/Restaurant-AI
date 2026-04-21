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


CLAUDE_MODEL = "claude-sonnet-4-6"
CLAUDE_HAIKU_MODEL = "claude-haiku-4-5-20251001"

DEFAULT_SYSTEM_PROMPT = (
    "You are a friendly AI operations partner for a small restaurant owner. "
    "Always respond in the same language the user writes in. "
    "Speak warmly and concisely, like a trusted colleague on a messenger app. "
    "Help interpret sales, inventory, and ordering data, and proactively suggest next steps. "
    "When the user asks to add or register a recipe, the system will automatically handle it — "
    "just acknowledge naturally and let the system do the work."
)

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


def chat_with_claude(
    messages: list[dict],
    system_prompt: Optional[str] = None,
    max_tokens: int = 1024,
) -> str:
    """Send a multi-turn chat to Claude and return the assistant text reply."""
    client = _get_client()
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system_prompt or DEFAULT_SYSTEM_PROMPT,
        messages=messages,
    )
    return "".join(getattr(b, "text", "") for b in response.content).strip()



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


_RECIPE_CHAT_PARSE_SYSTEM = (
    "You are a restaurant recipe extraction assistant. "
    "Extract recipe name and ingredient info from a natural language chat message.\n\n"
    "Always convert quantities to standard units (g, mL, or ea). "
    "Use your culinary knowledge to estimate vague expressions "
    "(e.g. 'a handful', '한 줌', 'a few cloves of garlic', 'a drizzle of oil', '한 큰술'). "
    "Every ingredient must have a numeric quantity — never leave it as a vague string.\n\n"
    "Return ONLY valid JSON, no markdown fences, no extra text:\n"
    '{"name": "<recipe name in original language>", "price": <number or null>, "items": ['
    '{"name": "<English ingredient name>", "quantity": <number>, "unit": "<g|mL|ea>", '
    '"quantity_display": "<original expression exactly as written>", '
    '"reasoning": "<English explanation IF vague unit was converted, e.g. \'a few cloves of garlic is about 15g\', else null>"}]}'
)

_RECIPE_CHAT_PARSE_PROMPT = "Extract the recipe name and ingredients from this message:\n\n{message}"


def extract_recipe_from_chat(message: str, history: list[dict] | None = None) -> dict:
    """Extract recipe name + parsed ingredients from a chat message.

    history: recent chat turns passed as context so Claude can resolve references
    like "register it" that point to a recipe discussed earlier in the conversation.
    Returns {"name": str, "items": [{name, quantity, unit, quantity_display, reasoning}]}.
    """
    client = _get_client()
    context_messages = list(history or [])[-10:]
    context_messages.append(
        {"role": "user", "content": _RECIPE_CHAT_PARSE_PROMPT.format(message=message)}
    )
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        system=_RECIPE_CHAT_PARSE_SYSTEM,
        messages=context_messages,
    )
    raw = "".join(getattr(b, "text", "") for b in response.content).strip()
    data = json.loads(strip_fences(raw))
    if "name" not in data or "items" not in data:
        raise ValueError("Claude response missing required fields")
    return data


_RECIPE_UPDATE_SYSTEM = (
    "You are a recipe modification assistant. "
    "The user has a pending recipe awaiting confirmation and wants to change something before confirming.\n\n"
    "Analyze the user message and return ONLY valid JSON, no markdown fences:\n"
    '{"modified": false} — if the message is NOT a recipe modification, OR\n'
    '{"modified": true, "price": <number or null>, "name": "<string or null>", "items": [<updated items array or null>]}'
    " — if it IS a modification. "
    "Use null for fields that did NOT change. "
    "For items, use the same structure: "
    '{"name": "<English ingredient name>", "quantity": <number>, "unit": "<g|ml|ea>", '
    '"quantity_display": "<expression as written>", "reasoning": "<English explanation if vague, else null>"}. '
    "Only include items array if at least one ingredient changed; otherwise use null."
)

_RECIPE_UPDATE_PROMPT = (
    "Current pending recipe:\n{pending}\n\nUser message: {message}\n\n"
    "Does this message modify the recipe? Return JSON as instructed."
)


def detect_recipe_update(pending: dict, user_message: str) -> Optional[dict]:
    client = _get_client()
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=_RECIPE_UPDATE_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": _RECIPE_UPDATE_PROMPT.format(
                    pending=json.dumps(pending, ensure_ascii=False),
                    message=user_message,
                ),
            }
        ],
    )
    raw = "".join(getattr(b, "text", "") for b in response.content).strip()
    data = json.loads(strip_fences(raw))
    return data if data.get("modified") else None


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
