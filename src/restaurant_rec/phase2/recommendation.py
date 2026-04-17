from __future__ import annotations

from dataclasses import dataclass

from restaurant_rec.phase1.config import AppConfig
from restaurant_rec.phase1.models import Recommendation, Restaurant, UserPreferences
from restaurant_rec.phase1.ports import RestaurantQuery, RestaurantStore
from restaurant_rec.phase1.text_normalize import canonicalize_location


@dataclass(frozen=True)
class RecommendationDebug:
    relaxations_applied: list[str]
    candidate_count: int


class RecommendationService:
    def __init__(self, store: RestaurantStore, cfg: AppConfig):
        self._store = store
        self._cfg = cfg

    def recommend(
        self, prefs: UserPreferences, *, top_n: int | None = None
    ) -> tuple[list[Recommendation], RecommendationDebug]:
        top_n = int(top_n or self._cfg.default_top_n)
        base_query = RestaurantQuery(
            location=canonicalize_location(prefs.location),
            locality=(prefs.locality.strip() if prefs.locality else None),
            cuisines_any=prefs.cuisines,
            min_rating=prefs.min_rating,
            budget_max_inr=float(prefs.budget_max_inr),
        )

        candidates = self._store.query(base_query)
        relaxations: list[str] = []

        if not candidates:
            lowered = max(0.0, float(prefs.min_rating) - 0.5)
            if lowered != prefs.min_rating:
                candidates = self._store.query(
                    RestaurantQuery(
                        location=prefs.location,
                        locality=(prefs.locality.strip() if prefs.locality else None),
                        cuisines_any=prefs.cuisines,
                        min_rating=lowered,
                        budget_max_inr=float(prefs.budget_max_inr),
                    )
                )
                if candidates:
                    relaxations.append(f"min_rating lowered to {lowered:g}")

        if not candidates:
            # Drop min_rating entirely if lowering didn't help.
            candidates = self._store.query(
                RestaurantQuery(
                    location=prefs.location,
                    locality=(prefs.locality.strip() if prefs.locality else None),
                    cuisines_any=prefs.cuisines,
                    min_rating=None,
                    budget_max_inr=float(prefs.budget_max_inr),
                )
            )
            if candidates:
                relaxations.append("min_rating dropped")

        if not candidates:
            widened_budget = float(prefs.budget_max_inr) * 1.2
            candidates = self._store.query(
                RestaurantQuery(
                    location=prefs.location,
                    locality=(prefs.locality.strip() if prefs.locality else None),
                    cuisines_any=prefs.cuisines,
                    min_rating=prefs.min_rating,
                    budget_max_inr=widened_budget,
                )
            )
            if candidates:
                relaxations.append("budget_max_inr widened (+20%)")

        if not candidates and prefs.cuisines:
            candidates = self._store.query(
                RestaurantQuery(
                    location=prefs.location,
                    cuisines_any=None,
                    min_rating=None,
                    budget_max_inr=float(prefs.budget_max_inr),
                )
            )
            if candidates:
                relaxations.append("cuisine constraint dropped")

        scored = [_score_candidate(r, prefs, self._cfg) for r in candidates]
        scored.sort(key=lambda x: x[0], reverse=True)

        out: list[Recommendation] = []
        for idx, (_score, r, reasons) in enumerate(scored[:top_n], start=1):
            out.append(
                Recommendation(
                    restaurant_id=r.id,
                    restaurant_name=r.name,
                    cuisine=(r.cuisines[0] if r.cuisines else ""),
                    rating=r.rating,
                    estimated_cost=r.average_cost_for_two,
                    explanation=_explanation_from_reasons(reasons),
                    rank=idx,
                    match_reasons=reasons,
                )
            )
        return out, RecommendationDebug(
            relaxations_applied=relaxations, candidate_count=len(candidates)
        )


def _score_candidate(
    r: Restaurant, prefs: UserPreferences, cfg: AppConfig
) -> tuple[float, Restaurant, list[str]]:
    reasons: list[str] = []
    score = 0.0

    wanted_set = {c.strip().lower() for c in prefs.cuisines if c and c.strip()}
    cuisine_set = {c.strip().lower() for c in r.cuisines if c and c.strip()}
    if wanted_set and cuisine_set:
        inter = wanted_set.intersection(cuisine_set)
        if inter:
            score += 3.0
            reasons.append(f"cuisine match: {', '.join(sorted(inter))}")
        else:
            score -= 0.5

    if r.rating is not None:
        score += min(5.0, max(0.0, r.rating)) / 5.0 * 3.0
        reasons.append(f"rating {r.rating:g}")
    else:
        score -= 0.25

    budget_max = float(prefs.budget_max_inr)
    if r.average_cost_for_two is None:
        if cfg.allow_unknown_cost:
            reasons.append("cost unknown")
        else:
            score -= 2.0
    else:
        cost = float(r.average_cost_for_two)
        if cost <= budget_max:
            score += 1.5
            reasons.append(f"within budget (<= {budget_max:g} INR)")
        else:
            score -= 1.0
            reasons.append(f"over budget (> {budget_max:g} INR)")

    if r.reviews_count is not None:
        bump = min(1.0, r.reviews_count / 1000.0)
        score += bump
        reasons.append(f"{r.reviews_count} reviews")

    return score, r, reasons


def _explanation_from_reasons(reasons: list[str]) -> str:
    if not reasons:
        return "Recommended based on your preferences."
    return "Good match because: " + "; ".join(reasons[:3]) + "."

