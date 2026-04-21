"""Pydantic schemas for recipe router payloads and responses."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RecipeIngredientIn(BaseModel):
    ingredient_id: int
    quantity: Optional[float] = None
    unit: str = "unit"
    quantity_display: Optional[str] = None


class ParseRequest(BaseModel):
    ingredient_text: str


class ParsedIngredient(BaseModel):
    name: str
    quantity: Optional[float]
    unit: str
    quantity_display: str
    reasoning: str


class RecipeIn(BaseModel):
    name: str
    description: Optional[str] = None
    price: float = 0.0
    ingredients: list[RecipeIngredientIn] = Field(default_factory=list)


class RecipeOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price: float

    model_config = ConfigDict(from_attributes=True)


class SalesLogIn(BaseModel):
    recipe_id: int
    quantity: int = 1
    total_price: Optional[float] = None


class RecipePreviewIn(BaseModel):
    name: str
    description: Optional[str] = None
    price: float = 0.0
    ingredient_text: str


class SuggestedMatch(BaseModel):
    id: int
    name: str
    unit: str


class PreviewItem(BaseModel):
    name: str
    quantity: Optional[float]
    unit: str
    quantity_display: str
    reasoning: str
    suggested_match: Optional[SuggestedMatch]
    match_score: float


class RecipePreviewOut(BaseModel):
    name: str
    description: Optional[str]
    price: float
    items: list[PreviewItem]


class ConfirmItem(BaseModel):
    name: str
    quantity: Optional[float] = None
    unit: str = "unit"
    quantity_display: str = ""
    ingredient_id: Optional[int] = None
    include: bool = True


class RecipeConfirmIn(BaseModel):
    name: str
    description: Optional[str] = None
    price: float = 0.0
    items: list[ConfirmItem] = Field(default_factory=list)


class RecipeConfirmOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price: float
    ingredients_linked: int
    ingredients_created: int


class IngredientDetail(BaseModel):
    link_id: int
    ingredient_id: int
    name: str
    quantity: Optional[float]
    unit: str
    quantity_display: Optional[str]


class RecipeDetailOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price: float
    ingredients: list[IngredientDetail]

    model_config = ConfigDict(from_attributes=True)


class RecipeUpdateIn(BaseModel):
    name: str
    description: Optional[str] = None
    price: float = 0.0
    items: Optional[list[ConfirmItem]] = None
