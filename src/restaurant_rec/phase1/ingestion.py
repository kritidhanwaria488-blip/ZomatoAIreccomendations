from __future__ import annotations

from dataclasses import dataclass

from restaurant_rec.phase1.models import Restaurant
from restaurant_rec.phase1.normalize import NormalizationResult, normalize_many
from restaurant_rec.phase1.ports import DatasetSource, RestaurantStore


@dataclass(frozen=True)
class IngestionReport:
    total_rows: int
    cleaned_rows: int
    skipped_rows: int
    unique_cities: int
    top_cuisines: list[tuple[str, int]]
    skipped_by_reason: dict[str, int]


class IngestionService:
    def __init__(self, source: DatasetSource, store: RestaurantStore):
        self._source = source
        self._store = store

    def ingest(self) -> IngestionReport:
        raw = self._source.load()
        total = len(raw)

        norm: NormalizationResult = normalize_many(raw)
        restaurants = norm.restaurants
        cleaned = len(restaurants)
        skipped = sum(norm.skipped_by_reason.values())

        self._store.upsert_many(restaurants)
        return _build_report(
            restaurants=restaurants,
            total_rows=total,
            skipped_rows=skipped,
            skipped_by_reason=norm.skipped_by_reason,
        )


def _build_report(
    *,
    restaurants: list[Restaurant],
    total_rows: int,
    skipped_rows: int,
    skipped_by_reason: dict[str, int],
) -> IngestionReport:
    city_set = {r.location.strip().lower() for r in restaurants if r.location.strip()}
    cuisine_counts: dict[str, int] = {}
    for r in restaurants:
        for c in r.cuisines:
            cc = c.strip()
            if not cc:
                continue
            cuisine_counts[cc] = cuisine_counts.get(cc, 0) + 1

    top_cuisines = sorted(cuisine_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]

    return IngestionReport(
        total_rows=total_rows,
        cleaned_rows=len(restaurants),
        skipped_rows=skipped_rows,
        unique_cities=len(city_set),
        top_cuisines=top_cuisines,
        skipped_by_reason=skipped_by_reason,
    )

