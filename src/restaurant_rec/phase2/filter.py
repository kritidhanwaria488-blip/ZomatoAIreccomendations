from __future__ import annotations

from restaurant_rec.phase1.config import AppConfig
from restaurant_rec.phase1.models import Restaurant, UserPreferences
from restaurant_rec.phase1.ports import RestaurantQuery, RestaurantStore


def retrieve_candidates(
    store: RestaurantStore, cfg: AppConfig, prefs: UserPreferences
) -> list[Restaurant]:
    """
    Phase 2 deterministic filtering:
    location(city) + budget + cuisines + min_rating.
    """
    cuisines_any = prefs.cuisine if isinstance(prefs.cuisine, list) else [prefs.cuisine]
    cost_min, cost_max = cfg.budget_to_cost_range(prefs.budget)
    return store.query(
        RestaurantQuery(
            city=prefs.city,
            cuisines_any=cuisines_any,
            min_rating=prefs.min_rating,
            budget=prefs.budget,
            cost_min=cost_min,
            cost_max=cost_max,
        )
    )


__all__ = ["retrieve_candidates"]

