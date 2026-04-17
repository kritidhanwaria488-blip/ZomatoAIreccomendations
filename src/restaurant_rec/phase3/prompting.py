from __future__ import annotations

import json
from dataclasses import dataclass

from restaurant_rec.phase1.models import Restaurant, UserPreferences


@dataclass(frozen=True)
class LLMRecommendationRequest:
    prefs: UserPreferences
    candidates: list[Restaurant]


def build_prompt(req: LLMRecommendationRequest) -> str:
    """
    Phase 3 prompt skeleton: strict 'choose only from candidates' + JSON-only output.
    """
    candidates = [
        {
            "id": r.id,
            "name": r.name,
            "location": r.location,
            "area": r.area,
            "cuisines": r.cuisines,
            "rating": r.rating,
            "average_cost_for_two": r.average_cost_for_two,
        }
        for r in req.candidates
    ]

    prefs = {
        "location": req.prefs.location,
        "budget_max_inr": req.prefs.budget_max_inr,
        "cuisines": req.prefs.cuisines,
        "min_rating": req.prefs.min_rating,
        "additional_preferences": req.prefs.additional_preferences,
    }

    return "\n".join(
        [
            "You are a restaurant recommendation engine.",
            "Rules:",
            "- Use ONLY the provided candidate restaurants (by id). Do not invent any new restaurants.",
            "- Output valid JSON only. No extra text.",
            "",
            "User preferences (JSON):",
            json.dumps(prefs, ensure_ascii=False),
            "",
            "Candidate restaurants (JSON):",
            json.dumps(candidates, ensure_ascii=False),
            "",
            "Return JSON with shape:",
            '{"recommendations":[{"restaurant_id":"...","rank":1,"explanation":"..."}]}',
        ]
    )


__all__ = ["LLMRecommendationRequest", "build_prompt"]

