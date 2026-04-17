from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class AppConfig:
    dataset_name: str = "ManikaSaini/zomato-restaurant-recommendation"
    data_dir: Path = Path("data")
    dataset_path: Path = Path("data/restaurants.jsonl")
    dataset_cache_dir: Path = Path("data/.hf_cache")
    restaurants_parquet_path: Path = Path("data/restaurants.parquet")

    # Phase 2 thresholds (kept for compatibility with earlier code)
    budget_low_max: int = 500
    budget_medium_max: int = 1500
    allow_unknown_cost: bool = True

    default_top_n: int = 10
    default_min_rating: float = 3.5
    candidate_cap: int = 50

    llm_provider: str = "none"
    llm_api_key_env: str = "LLM_API_KEY"

    def budget_to_cost_range(self, budget: str) -> tuple[float | None, float | None]:
        b = (budget or "").strip().lower()
        if b == "low":
            return (0.0, float(self.budget_low_max))
        if b == "medium":
            return (float(self.budget_low_max), float(self.budget_medium_max))
        if b == "high":
            return (float(self.budget_medium_max), None)
        return (None, None)

    @staticmethod
    def from_env(env: Mapping[str, str]) -> "AppConfig":
        dataset_path = Path(env.get("DATASET_PATH", "data/restaurants.jsonl"))
        return AppConfig(
            dataset_name=env.get(
                "DATASET_NAME", "ManikaSaini/zomato-restaurant-recommendation"
            ),
            data_dir=Path(env.get("DATA_DIR", "data")),
            dataset_path=dataset_path,
            dataset_cache_dir=Path(env.get("DATASET_CACHE_DIR", "data/.hf_cache")),
            restaurants_parquet_path=Path(
                env.get("RESTAURANTS_PARQUET_PATH", "data/restaurants.parquet")
            ),
            budget_low_max=int(env.get("BUDGET_LOW_MAX", "500")),
            budget_medium_max=int(env.get("BUDGET_MEDIUM_MAX", "1500")),
            allow_unknown_cost=(env.get("ALLOW_UNKNOWN_COST", "true").lower() == "true"),
            llm_provider=env.get("LLM_PROVIDER", "none"),
            llm_api_key_env=env.get("LLM_API_KEY_ENV", "LLM_API_KEY"),
        )

