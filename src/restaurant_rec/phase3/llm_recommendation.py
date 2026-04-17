from __future__ import annotations

import json
from dataclasses import dataclass

from restaurant_rec.phase1.models import Recommendation, Restaurant, UserPreferences
from restaurant_rec.phase3.groq import GroqClient, GroqConfig, load_dotenv_auto
from restaurant_rec.phase3.prompting import LLMRecommendationRequest, build_prompt


@dataclass(frozen=True)
class LLMRecommendationResult:
    recommendations: list[Recommendation]
    used_fallback: bool
    error: str | None = None


class LLMRecommendationService:
    """
    Phase 3 LLM-powered recommendation service with fallback to deterministic baseline.
    """

    def __init__(self, groq_config: GroqConfig | None = None):
        if groq_config is None:
            load_dotenv_auto()
            groq_config = GroqConfig.from_env()
        self._client = GroqClient(groq_config)

    def rank_candidates(
        self, prefs: UserPreferences, candidates: list[Restaurant], top_n: int = 10
    ) -> LLMRecommendationResult:
        """
        Rank candidates using LLM with deterministic fallback.
        """
        if not candidates:
            return LLMRecommendationResult(
                recommendations=[], used_fallback=False, error="No candidates provided"
            )

        # Cap candidates to control cost
        max_candidates = min(len(candidates), 50)
        capped_candidates = candidates[:max_candidates]

        try:
            prompt = build_prompt(LLMRecommendationRequest(prefs=prefs, candidates=capped_candidates))
            response = self._client.generate(prompt)
            
            # Parse LLM response
            parsed = self._parse_llm_response(response, capped_candidates)
            if parsed is None:
                # Fallback to baseline ranking
                return self._fallback_rank(prefs, candidates, top_n, "LLM response parsing failed")
            
            recommendations = self._convert_to_recommendations(parsed, capped_candidates)
            return LLMRecommendationResult(
                recommendations=recommendations[:top_n], used_fallback=False
            )
            
        except Exception as e:
            # Fallback to baseline ranking on any error
            return self._fallback_rank(prefs, candidates, top_n, str(e))

    def _parse_llm_response(self, response: str, candidates: list[Restaurant]) -> dict | None:
        """
        Parse LLM JSON response with validation.
        """
        try:
            # Try to parse as JSON directly
            data = json.loads(response.strip())
        except json.JSONDecodeError:
            # Try to extract JSON from response
            start = response.find("{")
            end = response.rfind("}")
            if start >= 0 and end > start:
                try:
                    data = json.loads(response[start : end + 1])
                except json.JSONDecodeError:
                    return None
            else:
                return None

        # Validate structure
        if not isinstance(data, dict) or "recommendations" not in data:
            return None

        recs = data["recommendations"]
        if not isinstance(recs, list):
            return None

        # Validate each recommendation
        valid_ids = {r.id for r in candidates}
        for rec in recs:
            if not isinstance(rec, dict):
                return None
            if "restaurant_id" not in rec or rec["restaurant_id"] not in valid_ids:
                return None
            if "rank" not in rec or not isinstance(rec["rank"], int):
                return None

        return data

    def _convert_to_recommendations(self, parsed: dict, candidates: list[Restaurant]) -> list[Recommendation]:
        """
        Convert parsed LLM response to Recommendation objects.
        """
        id_to_restaurant = {r.id: r for r in candidates}
        recommendations = []
        
        for rec in parsed["recommendations"]:
            restaurant = id_to_restaurant[rec["restaurant_id"]]
            recommendations.append(
                Recommendation(
                    restaurant_id=restaurant.id,
                    restaurant_name=restaurant.name,
                    cuisine=", ".join(restaurant.cuisines) if restaurant.cuisines else "Unknown",
                    rating=restaurant.rating,
                    estimated_cost=restaurant.average_cost_for_two,
                    rank=rec["rank"],
                    explanation=rec.get("explanation", "LLM-ranked recommendation"),
                    match_reasons=[f"LLM rank {rec['rank']}"],
                )
            )
        
        # Sort by rank
        recommendations.sort(key=lambda r: r.rank)
        return recommendations

    def _fallback_rank(
        self, prefs: UserPreferences, candidates: list[Restaurant], top_n: int, error: str
    ) -> LLMRecommendationResult:
        """
        Fallback to deterministic baseline ranking.
        """
        # Simple deterministic ranking based on multiple factors
        scored_candidates = []
        for i, restaurant in enumerate(candidates):
            score = 0
            reasons = []
            
            # Cuisine match strength
            if restaurant.cuisines and prefs.cuisines:
                matches = len(set(restaurant.cuisines) & set(prefs.cuisines))
                if matches > 0:
                    score += matches * 10
                    reasons.append(f"{matches} cuisine match(es)")
            
            # Rating signal
            if restaurant.rating is not None and restaurant.rating >= prefs.min_rating:
                score += restaurant.rating * 5
                reasons.append(f"rating {restaurant.rating}")
            
            # Budget fit
            if (
                restaurant.average_cost_for_two is not None
                and restaurant.average_cost_for_two <= prefs.budget_max_inr
            ):
                score += 5
                reasons.append("within budget")
            
            # Popularity (reviews)
            if restaurant.reviews_count is not None and restaurant.reviews_count > 0:
                score += min(restaurant.reviews_count / 100, 10)  # Cap at 10 points
                reasons.append(f"{restaurant.reviews_count} reviews")
            
            scored_candidates.append((score, i, restaurant, reasons))
        
        # Sort by score (descending), then by original index for stability
        scored_candidates.sort(key=lambda x: (-x[0], x[1]))
        
        recommendations = []
        for rank, (_, _, restaurant, reasons) in enumerate(scored_candidates[:top_n], 1):
            recommendations.append(
                Recommendation(
                    restaurant_id=restaurant.id,
                    restaurant_name=restaurant.name,
                    cuisine=", ".join(restaurant.cuisines) if restaurant.cuisines else "Unknown",
                    rating=restaurant.rating,
                    estimated_cost=restaurant.average_cost_for_two,
                    rank=rank,
                    explanation=f"Good match because: {'; '.join(reasons)}.",
                    match_reasons=reasons,
                )
            )
        
        return LLMRecommendationResult(
            recommendations=recommendations, used_fallback=True, error=error
        )


__all__ = ["LLMRecommendationService", "LLMRecommendationResult"]
