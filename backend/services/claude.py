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

DEFAULT_SYSTEM_PROMPT = (
    "You are a friendly AI operations partner for a small restaurant owner. "
    "Always respond in the same language the user writes in. "
    "Speak warmly and concisely, like a trusted colleague on a messenger app. "
    "Help interpret sales, inventory, and ordering data, and proactively suggest next steps."
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


_VAGUE_UNIT_REFERENCE = """
Vague unit conversion reference (apply based on ingredient context):

KOREAN:
- 한 줌 / 한줌 (a handful): leafy greens ~30g, noodles/pasta ~80g, nuts ~20g, shrimp ~50g
- 한 웅큼 / 한웅큼 (a big handful): leafy greens ~60g, noodles ~120g, beans ~50g
- 꼬집 / 한 꼬집 (a pinch): dry spice ~0.5g, salt ~1g
- 조금 / 약간 (a little): dry spice ~1g, salt/sugar ~2g, liquid ~5ml
- 적당량 / 적당히 (as needed): dry spice ~2g, liquid ~10ml — set reasoning
- 두부 한 모 (1 block tofu): ~300g | 두부 반 모 (half block): ~150g | 두부 1/4모: ~75g
- 한 알 (1 piece): garlic clove ~5g, egg ~60g, walnut ~7g
- 두 알 / 세 알: multiply accordingly
- 한 개 (1 piece): use ea unit, estimate g by ingredient
- 반 개 (half piece): ea=0.5 or estimate g
- 한 컵 (1 cup): liquid ~240ml, flour ~120g, rice ~180g, sugar ~200g
- 반 컵 (half cup): divide accordingly
- 한 국자 (1 ladle): soup/liquid ~150ml
- 조금씩 (a little at a time): ~1g or ~5ml

ENGLISH:
- a pinch of: ~0.5-1g dry (salt ~1g, pepper ~0.5g, spice ~0.5g)
- a drizzle of: oil/sauce ~10ml, honey ~15ml
- a drop of: extract/sauce ~0.5ml (e.g. vanilla extract, soy sauce ~0.5ml)
- a squeeze of: lemon/lime juice ~15ml, tomato paste ~20g
- a handful of: same as 한 줌 — context-dependent (see above)
- a big handful of: same as 한 웅큼
- dash of: liquid ~0.6ml, dry spice ~0.5g
- sprinkle of / sprinkle some: dry topping ~1-2g
- a knob of: butter ~15g, ginger ~5g
- a splash of: liquid ~30ml
- a sliver of: thin slice ~5-10g (garlic ~3g, ginger ~5g)
- some: dry ~2g, liquid ~10ml — set reasoning
- to taste: same as 조금, set reasoning explaining the estimate

FRACTIONAL:
- 반 (half / 1/2): halve the standard unit of the ingredient
- 1/3, 1/4: divide accordingly
- 두 배 (double / 2x): multiply
"""

_RECIPE_PARSE_SYSTEM = (
    "You are a restaurant recipe analysis expert. "
    "Parse ingredient lists and return only a valid JSON array. Never include any other text."
)

_RECIPE_PARSE_PROMPT = """Parse the following ingredient list into a JSON array.

Rules:
- name: ingredient name in English
- quantity: numeric value in standard units (g or ml preferred). Use the vague unit reference below to convert expressions like "a pinch", "한 줌", "두부 반 모", "a drizzle of".
- unit: g, ml, or ea
- quantity_display: original expression exactly as written (preserve Korean/English as-is)
- reasoning: if the original was a vague or non-standard unit, write a friendly explanation in the SAME LANGUAGE as the input. If the original was already a precise measurement (e.g. "120g"), set reasoning to null.

{vague_unit_reference}

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
{{ingredient_text}}"""

_RECIPE_PARSE_PROMPT = _RECIPE_PARSE_PROMPT.format(
    vague_unit_reference=_VAGUE_UNIT_REFERENCE
).replace("{{ingredient_text}}", "{ingredient_text}")


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
    "Tablespoon/teaspoon conversions (apply based on ingredient):\n"
    "- 한 큰술 / 1 tablespoon: garlic ~9g, butter ~14g, flour ~8g, oil ~13g, sugar ~12g, salt ~17g, liquid ~15ml\n"
    "- 한 작은술 / 1 teaspoon: salt ~5g, sugar ~4g, liquid ~5ml\n\n"
    + _VAGUE_UNIT_REFERENCE
    + "\n\nReturn ONLY valid JSON, no markdown fences, no extra text:\n"
    '{"name": "<recipe name in original language>", "items": ['
    '{"name": "<English ingredient name>", "quantity": <number>, "unit": "<g|ml|ea>", '
    '"quantity_display": "<original expression exactly as written>", '
    '"reasoning": "<Korean/English explanation IF vague unit was converted, e.g. \'마늘 한 큰술은 약 9g 정도 입니다!\', else null>"}]}'
)

_RECIPE_CHAT_PARSE_PROMPT = "Extract the recipe name and ingredients from this message:\n\n{message}"


def extract_recipe_from_chat(message: str) -> dict:
    """Extract recipe name + parsed ingredients from a chat message.

    Returns {"name": str, "items": [{name, quantity, unit, quantity_display, reasoning}]}.
    """
    client = _get_client()
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        system=_RECIPE_CHAT_PARSE_SYSTEM,
        messages=[
            {"role": "user", "content": _RECIPE_CHAT_PARSE_PROMPT.format(message=message)}
        ],
    )
    raw = "".join(getattr(b, "text", "") for b in response.content).strip()
    data = json.loads(strip_fences(raw))
    if "name" not in data or "items" not in data:
        raise ValueError("Claude response missing required fields")
    return data


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
