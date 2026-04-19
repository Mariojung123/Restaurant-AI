import difflib
from typing import TypeVar

FUZZY_MATCH_THRESHOLD = 0.7

T = TypeVar("T")


def fuzzy_match(items: list[T], name: str) -> tuple[T | None, float]:
    if not items:
        return (None, 0.0)

    best_score = 0.0
    best_match = None
    normalized = name.lower().strip()

    for item in items:
        score = difflib.SequenceMatcher(None, normalized, item.name.lower().strip()).ratio()
        if score > best_score:
            best_score = score
            best_match = item

    if best_score >= FUZZY_MATCH_THRESHOLD:
        return (best_match, best_score)
    return (None, 0.0)
