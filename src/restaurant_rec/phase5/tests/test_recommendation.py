"""
Phase 5: Unit tests for recommendation system.
"""

import unittest
from pathlib import Path
from restaurant_rec.phase1.models import Restaurant, UserPreferences, Recommendation
from restaurant_rec.phase2.recommendation import RecommendationDebug
from restaurant_rec.phase1.config import AppConfig
from restaurant_rec.phase3.llm_recommendation import LLMRecommendationService


class MockStore:
    """Mock restaurant store for testing."""
    
    def __init__(self, restaurants):
        self._restaurants = {r.id: r for r in restaurants}
    
    def query(self, q):
        results = list(self._restaurants.values())
        if q.location:
            results = [r for r in results if q.location.lower() in r.location.lower()]
        if q.cuisines_any:
            wanted = {c.lower() for c in q.cuisines_any}
            results = [r for r in results if any(c.lower() in wanted for c in r.cuisines)]
        return results
    
    def count(self):
        return len(self._restaurants)
    
    def get_by_id(self, restaurant_id):
        return self._restaurants.get(restaurant_id)


class TestRecommendationService(unittest.TestCase):
    
    def setUp(self):
        self.restaurants = [
            Restaurant(
                id="r1",
                name="Italian Place",
                location="Bangalore",
                cuisines=["Italian"],
                average_cost_for_two=800.0,
                rating=4.5,
                reviews_count=100,
            ),
            Restaurant(
                id="r2", 
                name="Chinese Express",
                location="Bangalore",
                cuisines=["Chinese"],
                average_cost_for_two=600.0,
                rating=4.0,
                reviews_count=80,
            ),
            Restaurant(
                id="r3",
                name="Mixed Cuisine",
                location="Bangalore",
                cuisines=["Italian", "Chinese"],
                average_cost_for_two=1000.0,
                rating=4.2,
                reviews_count=50,
            ),
            Restaurant(
                id="r4",
                name="Expensive Italian",
                location="Bangalore",
                cuisines=["Italian"],
                average_cost_for_two=2000.0,
                rating=4.8,
                reviews_count=200,
            ),
        ]
        self.store = MockStore(self.restaurants)
    
    def test_basic_filtering(self):
        """Test basic filtering by location and cuisine."""
        from restaurant_rec.phase2.recommendation import RecommendationService
        
        prefs = UserPreferences(
            location="Bangalore",
            budget_max_inr=1500,
            cuisines=["Italian"],
            min_rating=3.5,
        )
        
        cfg = AppConfig.from_env({})
        service = RecommendationService(store=self.store, cfg=cfg)
        recs, debug = service.recommend(prefs, top_n=5)
        
        self.assertGreater(len(recs), 0)
        # Should only include restaurants with Italian cuisine under 1500
        for rec in recs:
            self.assertIn(rec.restaurant_id, ["r1", "r3"])  # Not r4 (too expensive)
    
    def test_budget_constraint(self):
        """Test budget constraint enforcement."""
        from restaurant_rec.phase2.recommendation import RecommendationService
        
        prefs = UserPreferences(
            location="Bangalore",
            budget_max_inr=900,
            cuisines=["Italian"],
            min_rating=3.5,
        )
        
        cfg = AppConfig.from_env({})
        service = RecommendationService(store=self.store, cfg=cfg)
        recs, debug = service.recommend(prefs, top_n=5)
        
        # Should only include r1 (800 INR), not r3 (1000 INR)
        for rec in recs:
            self.assertIn(rec.restaurant_id, ["r1"])
    
    def test_relaxation_when_no_matches(self):
        """Test that constraints are relaxed when no exact matches."""
        from restaurant_rec.phase2.recommendation import RecommendationService
        
        prefs = UserPreferences(
            location="Bangalore",
            budget_max_inr=500,
            cuisines=["Italian"],
            min_rating=4.9,  # Very high rating, no matches
        )
        
        cfg = AppConfig.from_env({})
        service = RecommendationService(store=self.store, cfg=cfg)
        recs, debug = service.recommend(prefs, top_n=5)
        
        # Should have applied relaxations
        self.assertTrue(len(debug.relaxations_applied) > 0)
        self.assertGreater(len(recs), 0)


class TestLLMRecommendation(unittest.TestCase):
    
    def test_fallback_when_no_candidates(self):
        """Test fallback when no candidates are provided."""
        from restaurant_rec.phase3.groq import GroqConfig
        
        # Mock config to avoid needing real API key
        config = GroqConfig(api_key="test_key", model="test_model")
        service = LLMRecommendationService(groq_config=config)
        
        prefs = UserPreferences(
            location="Bangalore",
            budget_max_inr=1000,
            cuisines=["Italian"],
            min_rating=3.5,
        )
        
        result = service.rank_candidates(prefs, [], top_n=5)
        
        self.assertEqual(len(result.recommendations), 0)
        self.assertTrue(result.used_fallback)


class TestCache(unittest.TestCase):
    
    def test_cache_operations(self):
        """Test basic cache operations."""
        from restaurant_rec.phase5.cache import RecommendationsCache, CacheConfig
        
        import tempfile
        import shutil
        
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
            
            # Clear cache
            cleared = cache.clear()
            self.assertEqual(cleared, 1)
            
            cached = cache.get(prefs)
            self.assertIsNone(cached)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
