from __future__ import annotations

import argparse
import os
from pathlib import Path

from restaurant_rec.phase1.config import AppConfig
from restaurant_rec.phase1.hf_dataset_source import HFDatasetConfig, HuggingFaceDatasetSource
from restaurant_rec.phase1.ingestion import IngestionService
from restaurant_rec.phase1.models import UserPreferences
from restaurant_rec.phase1.store_parquet import ParquetRestaurantStore
from restaurant_rec.phase2.recommendation import RecommendationService
from restaurant_rec.phase3.llm_recommendation import LLMRecommendationService


def _build_source(cfg: AppConfig):
    return HuggingFaceDatasetSource(
        HFDatasetConfig(name=cfg.dataset_name, cache_dir=cfg.dataset_cache_dir)
    )


def _build_store(cfg: AppConfig):
    return ParquetRestaurantStore(cfg.restaurants_parquet_path)


def cmd_ingest(cfg: AppConfig) -> int:
    store = _build_store(cfg)
    source = _build_source(cfg)
    report = IngestionService(source=source, store=store).ingest()

    print("Ingestion summary")
    print(f"- total rows: {report.total_rows}")
    print(f"- cleaned rows: {report.cleaned_rows}")
    print(f"- skipped rows: {report.skipped_rows}")
    print(f"- unique cities: {report.unique_cities}")
    if report.skipped_by_reason:
        print("- skipped by reason:")
        for reason, n in sorted(report.skipped_by_reason.items(), key=lambda kv: kv[1], reverse=True):
            print(f"  - {reason}: {n}")
    if report.top_cuisines:
        print("- top cuisines:")
        for c, n in report.top_cuisines:
            print(f"  - {c}: {n}")
    return 0


def cmd_recommend(cfg: AppConfig, args: argparse.Namespace) -> int:
    store = _build_store(cfg)
    if store.count() == 0:
        IngestionService(source=_build_source(cfg), store=store).ingest()

    cuisines = [c.strip() for c in (args.cuisines or "").split(",") if c.strip()]
    prefs = UserPreferences(
        location=args.location,
        budget_max_inr=float(args.budget_max_inr),
        cuisines=cuisines,
        min_rating=float(args.min_rating),
        additional_preferences=(args.additional if args.additional else None),
    )

    if args.use_llm:
        # Phase 3: LLM-powered recommendations
        llm_service = LLMRecommendationService()
        
        # Get baseline candidates first
        baseline_recs, debug = RecommendationService(store=store, cfg=cfg).recommend(
            prefs, top_n=50  # Get more candidates for LLM to choose from
        )
        
        if debug.relaxations_applied:
            print("No exact matches; relaxations applied:")
            for r in debug.relaxations_applied:
                print(f"- {r}")
        
        if not baseline_recs:
            print("No matches found.")
            return 0
        
        # Convert baseline recommendations back to restaurants for LLM
        candidate_restaurants = []
        for rec in baseline_recs:
            restaurant = store.get_by_id(rec.restaurant_id)
            if restaurant:
                candidate_restaurants.append(restaurant)
        
        # Use LLM to rank candidates
        llm_result = llm_service.rank_candidates(prefs, candidate_restaurants, top_n=int(args.top_n))
        
        if llm_result.used_fallback:
            print(f"LLM ranking failed, using deterministic baseline: {llm_result.error}")
        
        recs = llm_result.recommendations
    else:
        # Phase 2: Deterministic recommendations
        recs, debug = RecommendationService(store=store, cfg=cfg).recommend(
            prefs, top_n=int(args.top_n)
        )

        if debug.relaxations_applied:
            print("No exact matches; relaxations applied:")
            for r in debug.relaxations_applied:
                print(f"- {r}")

    if not recs:
        print("No matches found.")
        return 0

    for rec in recs:
        cost = f"{rec.estimated_cost:g}" if rec.estimated_cost is not None else "N/A"
        rating = f"{rec.rating:g}" if rec.rating is not None else "N/A"
        print(
            f"{rec.rank}. {rec.restaurant_name} | {rec.cuisine} | rating {rating} | cost {cost}"
        )
        print(f"   {rec.explanation}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="restaurant-rec")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("ingest", help="Phase 1 ingestion + summary report")
    r = sub.add_parser("recommend", help="Phase 2 deterministic recommendations (no LLM)")
    r.add_argument("--location", required=True, help="Location/city, e.g. Bangalore")
    r.add_argument("--budget-max-inr", required=True, dest="budget_max_inr")
    r.add_argument(
        "--cuisines",
        required=True,
        help="Comma-separated cuisines, e.g. Italian,Chinese",
    )
    r.add_argument("--min-rating", default="3.5")
    r.add_argument("--top-n", default="10")
    r.add_argument("--additional", default="")
    r.add_argument("--use-llm", action="store_true", help="Use Phase 3 LLM-powered ranking")

    args = parser.parse_args(argv)

    cfg = AppConfig.from_env(os.environ)
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    Path(cfg.dataset_cache_dir).mkdir(parents=True, exist_ok=True)

    if args.cmd == "ingest":
        return cmd_ingest(cfg)
    if args.cmd == "recommend":
        return cmd_recommend(cfg, args)

    raise RuntimeError(f"Unknown command: {args.cmd}")

