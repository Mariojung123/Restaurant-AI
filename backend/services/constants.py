"""Shared backend constants for domain and vision services."""

DEFAULT_UNIT = "unit"
DEFAULT_RECIPE_TOOL_UNIT = "ea"

CHANGE_TYPE_DELIVERY = "delivery"
CHANGE_TYPE_PURCHASE = "purchase"

AUTO_INVOICE_NOTE = "Auto-created from invoice scan"

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

CONTEXT_SECTION_HEADER = "--- Current restaurant data ---"
CONTEXT_SECTION_FOOTER = "--- End of data ---"

SALES_DEFAULT_PERIOD_DAYS = 7
SALES_MAX_PERIOD_DAYS = 30
