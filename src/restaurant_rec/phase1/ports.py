from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Protocol

from restaurant_rec.phase1.models import Restaurant


@dataclass(frozen=True)
class RestaurantQuery:
    location: str | None = None
    locality: str | None = None
    cuisines_any: list[str] | None = None
    min_rating: float | None = None
    budget_max_inr: float | None = None


class DatasetSource(Protocol):
    def load(self) -> list[dict[str, Any]]: ...


class RestaurantStore(Protocol):
    def upsert_many(self, restaurants: Iterable[Restaurant]) -> None: ...

    def query(self, q: RestaurantQuery) -> list[Restaurant]: ...

    def count(self) -> int: ...


class LLMClient(Protocol):
    def generate(self, prompt: str) -> str: ...

