from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Restaurant:
    id: str
    name: str
    location: str
    area: str | None = None
    cuisines: list[str] = field(default_factory=list)
    average_cost_for_two: float | None = None
    rating: float | None = None
    reviews_count: int | None = None
    tags: list[str] = field(default_factory=list)
    raw: dict[str, Any] | None = None

    @property
    def city(self) -> str:
        # Backward-compatible alias for older code.
        return self.location


@dataclass(frozen=True)
class UserPreferences:
    location: str
    budget_max_inr: float
    cuisines: list[str]
    min_rating: float = 3.5
    additional_preferences: str | None = None
    locality: str | None = None


@dataclass(frozen=True)
class Recommendation:
    restaurant_id: str
    restaurant_name: str
    cuisine: str
    rating: float | None
    estimated_cost: float | None
    explanation: str
    rank: int
    match_reasons: list[str] = field(default_factory=list)

