"""
Phase 5: Simplified unit tests for core functionality.
"""

import unittest
import tempfile
import shutil
from pathlib import Path


class TestCache(unittest.TestCase):
    """Test caching functionality."""

    def test_cache_set_and_get(self):
        """Test basic cache operations."""
        from restaurant_rec.phase5.cache import RecommendationsCache, CacheConfig

        temp_dir = Path(tempfile.mkdtemp())
        try:
            config = CacheConfig(cache_dir=temp_dir)
            cache = RecommendationsCache(config)

            prefs = {"location": "Bangalore", "budget": 1000}
            recommendations = [
                {"name": "Restaurant A", "rating": 4.5},
                {"name": "Restaurant B", "rating": 4.0},
            ]

            # Set cache
            cache.set(prefs, recommendations)

            # Get cache
            cached = cache.get(prefs)
            self.assertIsNotNone(cached)
            self.assertEqual(len(cached), 2)
            self.assertEqual(cached[0]["name"], "Restaurant A")

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_cache_miss(self):
        """Test cache miss for unknown preferences."""
        from restaurant_rec.phase5.cache import RecommendationsCache, CacheConfig

        temp_dir = Path(tempfile.mkdtemp())
        try:
            config = CacheConfig(cache_dir=temp_dir)
            cache = RecommendationsCache(config)

            prefs = {"location": "Delhi", "budget": 500}
            cached = cache.get(prefs)
            self.assertIsNone(cached)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_cache_clear(self):
        """Test cache clearing."""
        from restaurant_rec.phase5.cache import RecommendationsCache, CacheConfig

        temp_dir = Path(tempfile.mkdtemp())
        try:
            config = CacheConfig(cache_dir=temp_dir)
            cache = RecommendationsCache(config)

            # Add some entries
            cache.set({"loc": "A"}, [{"name": "R1"}])
            cache.set({"loc": "B"}, [{"name": "R2"}])

            # Clear all
            cleared = cache.clear()
            self.assertEqual(cleared, 2)

            # Verify cleared
            self.assertIsNone(cache.get({"loc": "A"}))
            self.assertIsNone(cache.get({"loc": "B"}))

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestLogging(unittest.TestCase):
    """Test logging functionality."""

    def test_log_entry(self):
        """Test logging a recommendation request."""
        from restaurant_rec.phase5.logging import RecommendationLogger

        temp_dir = Path(tempfile.mkdtemp())
        try:
            logger = RecommendationLogger(log_dir=temp_dir)

            logger.log(
                preferences={"location": "Bangalore", "cuisines": ["Italian"]},
                result_count=5,
                relaxations_applied=["min_rating dropped"],
                latency_ms=150.5,
                llm_used=True,
                llm_fallback=False,
            )

            # Verify log file was created
            log_file = temp_dir / "recommendations.jsonl"
            self.assertTrue(log_file.exists())

            # Read and verify content
            with open(log_file) as f:
                line = f.readline()
                import json

                data = json.loads(line)
                self.assertEqual(data["result_count"], 5)
                self.assertTrue(data["llm_used"])
                self.assertEqual(data["latency_ms"], 150.5)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_log_stats(self):
        """Test getting statistics from logs."""
        from restaurant_rec.phase5.logging import RecommendationLogger

        temp_dir = Path(tempfile.mkdtemp())
        try:
            logger = RecommendationLogger(log_dir=temp_dir)

            # Add multiple entries
            logger.log(
                preferences={"loc": "A"},
                result_count=3,
                relaxations_applied=[],
                latency_ms=100.0,
                llm_used=False,
            )
            logger.log(
                preferences={"loc": "B"},
                result_count=5,
                relaxations_applied=["min_rating dropped"],
                latency_ms=200.0,
                llm_used=True,
                llm_fallback=True,
            )

            stats = logger.get_stats()
            self.assertEqual(stats["total_requests"], 2)
            self.assertEqual(stats["llm_requests"], 1)
            self.assertEqual(stats["llm_fallbacks"], 1)
            self.assertEqual(stats["avg_latency_ms"], 150.0)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestModels(unittest.TestCase):
    """Test data models."""

    def test_restaurant_creation(self):
        """Test Restaurant model creation."""
        from restaurant_rec.phase1.models import Restaurant

        r = Restaurant(
            id="r1",
            name="Test Restaurant",
            location="Bangalore",
            cuisines=["Italian", "Chinese"],
            average_cost_for_two=800.0,
            rating=4.5,
        )

        self.assertEqual(r.id, "r1")
        self.assertEqual(r.name, "Test Restaurant")
        self.assertEqual(r.location, "Bangalore")
        self.assertEqual(r.cuisines, ["Italian", "Chinese"])
        self.assertEqual(r.average_cost_for_two, 800.0)
        self.assertEqual(r.rating, 4.5)

    def test_user_preferences(self):
        """Test UserPreferences model."""
        from restaurant_rec.phase1.models import UserPreferences

        prefs = UserPreferences(
            location="Delhi",
            budget_max_inr=1000,
            cuisines=["North Indian"],
            min_rating=4.0,
            additional_preferences="Spicy food",
        )

        self.assertEqual(prefs.location, "Delhi")
        self.assertEqual(prefs.budget_max_inr, 1000)
        self.assertEqual(prefs.min_rating, 4.0)

    def test_recommendation(self):
        """Test Recommendation model."""
        from restaurant_rec.phase1.models import Recommendation

        rec = Recommendation(
            restaurant_id="r1",
            restaurant_name="Test Restaurant",
            cuisine="Italian",
            rating=4.5,
            estimated_cost=800.0,
            rank=1,
            explanation="Great match!",
            match_reasons=["cuisine match", "good rating"],
        )

        self.assertEqual(rec.rank, 1)
        self.assertEqual(rec.restaurant_name, "Test Restaurant")


class TestLLMIntegration(unittest.TestCase):
    """Test LLM service integration."""

    def test_llm_service_fallback_on_empty(self):
        """Test LLM service fallback when no candidates."""
        from restaurant_rec.phase3.llm_recommendation import LLMRecommendationService
        from restaurant_rec.phase3.groq import GroqConfig
        from restaurant_rec.phase1.models import UserPreferences

        # Create service with test config
        config = GroqConfig(api_key="test_key", model="test_model")
        service = LLMRecommendationService(groq_config=config)

        prefs = UserPreferences(
            location="Bangalore",
            budget_max_inr=1000,
            cuisines=["Italian"],
            min_rating=3.5,
        )

        # Test with empty candidates
        result = service.rank_candidates(prefs, [], top_n=5)

        self.assertEqual(len(result.recommendations), 0)
        self.assertTrue(result.used_fallback)
        self.assertIsNotNone(result.error)


if __name__ == "__main__":
    unittest.main()
