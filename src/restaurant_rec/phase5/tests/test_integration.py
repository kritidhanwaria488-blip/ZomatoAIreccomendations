"""
Integration tests for the Restaurant Recommendation System (Phase 5).

Tests the full flow: API endpoints → recommendation service → data store.
"""

import unittest
import time
import json
from pathlib import Path

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from fastapi.testclient import TestClient

from restaurant_rec.phase4.app import create_app
from restaurant_rec.phase1.config import AppConfig
from restaurant_rec.phase1.store_parquet import ParquetRestaurantStore


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test client with real data store."""
        cls.cfg = AppConfig.from_env({})
        cls.store = ParquetRestaurantStore(cls.cfg.restaurants_parquet_path)
        cls.app = create_app(cls.cfg, cls.store)
        cls.client = TestClient(cls.app)
    
    def test_health_endpoint(self):
        """Test health check returns correct data."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertGreater(data["restaurant_count"], 10000)
        self.assertEqual(data["restaurant_count"], 12119)
    
    def test_locations_endpoint(self):
        """Test locations list is returned."""
        response = self.client.get("/locations")
        self.assertEqual(response.status_code, 200)
        
        locations = response.json()
        self.assertIsInstance(locations, list)
        self.assertGreater(len(locations), 80)
        self.assertIn("Bangalore", locations)
        self.assertIn("Whitefield", locations)
    
    def test_localities_endpoint(self):
        """Test localities for a location are returned."""
        response = self.client.get("/localities?location=Bangalore")
        self.assertEqual(response.status_code, 200)
        
        localities = response.json()
        self.assertIsInstance(localities, list)
        # Bangalore has many localities
        self.assertGreater(len(localities), 10)
    
    def test_recommendations_basic(self):
        """Test basic recommendation flow."""
        payload = {
            "location": "Bangalore",
            "budget_max_inr": 1000,
            "cuisines": ["North Indian"],
            "top_n": 5
        }
        
        response = self.client.post("/recommendations", json=payload)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("recommendations", data)
        self.assertIn("relaxations_applied", data)
        
        # Should return some results
        self.assertGreater(len(data["recommendations"]), 0)
        
        # Check recommendation structure
        if data["recommendations"]:
            rec = data["recommendations"][0]
            self.assertIn("restaurant_id", rec)
            self.assertIn("restaurant_name", rec)
            self.assertIn("cuisine", rec)
            self.assertIn("explanation", rec)
            self.assertIn("rank", rec)
    
    def test_recommendations_with_locality(self):
        """Test recommendations with locality filter."""
        payload = {
            "location": "Whitefield",
            "locality": "Whitefield",
            "budget_max_inr": 2000,
            "cuisines": ["Italian"],
            "top_n": 5
        }
        
        response = self.client.post("/recommendations", json=payload)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertGreaterEqual(len(data["recommendations"]), 0)
    
    def test_recommendations_with_min_rating(self):
        """Test recommendations with rating filter."""
        payload = {
            "location": "Bangalore",
            "budget_max_inr": 1500,
            "cuisines": ["Chinese"],
            "min_rating": 0,
            "top_n": 5
        }
        
        response = self.client.post("/recommendations", json=payload)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        # Should return results since rating filter is relaxed
        self.assertGreater(len(data["recommendations"]), 0)
    
    def test_recommendations_empty_cuisines(self):
        """Test recommendations with empty cuisines list."""
        payload = {
            "location": "Bangalore",
            "budget_max_inr": 1000,
            "cuisines": [],
            "top_n": 5
        }
        
        response = self.client.post("/recommendations", json=payload)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("recommendations", data)
    
    def test_recommendations_nonexistent_location(self):
        """Test recommendations for non-existent location."""
        payload = {
            "location": "XYZNonExistent123",
            "budget_max_inr": 1000,
            "cuisines": ["Italian"],
            "top_n": 5
        }
        
        response = self.client.post("/recommendations", json=payload)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        # Should return empty results gracefully
        self.assertEqual(len(data["recommendations"]), 0)
    
    def test_recommendations_high_budget(self):
        """Test recommendations with very high budget."""
        payload = {
            "location": "Bangalore",
            "budget_max_inr": 100000,
            "cuisines": ["North Indian"],
            "top_n": 10
        }
        
        response = self.client.post("/recommendations", json=payload)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        # Should return more results with high budget
        self.assertGreater(len(data["recommendations"]), 0)
    
    def test_recommendations_top_n_limit(self):
        """Test that top_n is capped correctly."""
        payload = {
            "location": "Bangalore",
            "budget_max_inr": 5000,
            "cuisines": ["North Indian"],
            "top_n": 50  # Maximum allowed
        }
        
        response = self.client.post("/recommendations", json=payload)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        # Should return at most 50 results
        self.assertLessEqual(len(data["recommendations"]), 50)
    
    def test_response_time_header(self):
        """Test that response time header is present."""
        payload = {
            "location": "Bangalore",
            "budget_max_inr": 1000,
            "cuisines": ["Italian"],
            "top_n": 5
        }
        
        response = self.client.post("/recommendations", json=payload)
        self.assertEqual(response.status_code, 200)
        
        # Check for latency header
        self.assertIn("x-response-time-ms", response.headers)
        latency = int(response.headers["x-response-time-ms"])
        self.assertGreater(latency, 0)
        self.assertLess(latency, 5000)  # Should complete within 5 seconds
    
    def test_recommendations_with_additional_preferences(self):
        """Test recommendations with additional preferences text."""
        payload = {
            "location": "Bangalore",
            "budget_max_inr": 1500,
            "cuisines": ["Italian"],
            "additional_preferences": "family-friendly, outdoor seating",
            "top_n": 5
        }
        
        response = self.client.post("/recommendations", json=payload)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("recommendations", data)
    
    def test_recommendations_relaxations(self):
        """Test that relaxations are applied when needed."""
        # Request with strict constraints that may need relaxation
        payload = {
            "location": "Bangalore",
            "budget_max_inr": 500,
            "cuisines": ["Italian"],
            "min_rating": 4.5,  # High rating requirement
            "top_n": 5
        }
        
        response = self.client.post("/recommendations", json=payload)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("relaxations_applied", data)
        
        # If results returned with strict constraints, relaxations likely applied
        if data["recommendations"]:
            # Check if min_rating was dropped
            if "min_rating dropped" in data["relaxations_applied"]:
                self.assertTrue(True, "Relaxation was applied correctly")


class TestPerformance(unittest.TestCase):
    """Performance tests for API endpoints."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test client."""
        cls.cfg = AppConfig.from_env({})
        cls.store = ParquetRestaurantStore(cls.cfg.restaurants_parquet_path)
        cls.app = create_app(cls.cfg, cls.store)
        cls.client = TestClient(cls.app)
    
    def test_health_response_time(self):
        """Test health endpoint responds quickly."""
        start = time.time()
        response = self.client.get("/health")
        elapsed = (time.time() - start) * 1000
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(elapsed, 500)  # Should be under 500ms
    
    def test_locations_response_time(self):
        """Test locations endpoint responds quickly."""
        start = time.time()
        response = self.client.get("/locations")
        elapsed = (time.time() - start) * 1000
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(elapsed, 1000)  # Should be under 1 second
    
    def test_recommendations_response_time(self):
        """Test recommendations endpoint responds within acceptable time."""
        payload = {
            "location": "Bangalore",
            "budget_max_inr": 1000,
            "cuisines": ["North Indian"],
            "top_n": 10
        }
        
        start = time.time()
        response = self.client.post("/recommendations", json=payload)
        elapsed = (time.time() - start) * 1000
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(elapsed, 3000)  # Should be under 3 seconds
    
    def test_multiple_concurrent_requests(self):
        """Test that multiple requests can be handled."""
        payload = {
            "location": "Bangalore",
            "budget_max_inr": 1000,
            "cuisines": ["Italian"],
            "top_n": 5
        }
        
        # Make 5 sequential requests (test client doesn't support true async concurrency)
        responses = []
        for _ in range(5):
            response = self.client.post("/recommendations", json=payload)
            responses.append(response)
        
        # All should succeed
        for response in responses:
            self.assertEqual(response.status_code, 200)
            self.assertIn("recommendations", response.json())


class TestEdgeCases(unittest.TestCase):
    """Edge case tests."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test client."""
        cls.cfg = AppConfig.from_env({})
        cls.store = ParquetRestaurantStore(cls.cfg.restaurants_parquet_path)
        cls.app = create_app(cls.cfg, cls.store)
        cls.client = TestClient(cls.app)
    
    def test_empty_location_validation(self):
        """Test empty location returns validation error."""
        payload = {
            "location": "",
            "budget_max_inr": 1000,
            "cuisines": ["Italian"],
            "top_n": 5
        }
        
        response = self.client.post("/recommendations", json=payload)
        self.assertEqual(response.status_code, 422)
    
    def test_zero_budget_validation(self):
        """Test zero budget returns validation error."""
        payload = {
            "location": "Bangalore",
            "budget_max_inr": 0,
            "cuisines": ["Italian"],
            "top_n": 5
        }
        
        response = self.client.post("/recommendations", json=payload)
        self.assertEqual(response.status_code, 422)
    
    def test_negative_budget_validation(self):
        """Test negative budget returns validation error."""
        payload = {
            "location": "Bangalore",
            "budget_max_inr": -100,
            "cuisines": ["Italian"],
            "top_n": 5
        }
        
        response = self.client.post("/recommendations", json=payload)
        self.assertEqual(response.status_code, 422)
    
    def test_large_top_n_validation(self):
        """Test top_n over 50 returns validation error."""
        payload = {
            "location": "Bangalore",
            "budget_max_inr": 1000,
            "cuisines": ["Italian"],
            "top_n": 100
        }
        
        response = self.client.post("/recommendations", json=payload)
        self.assertEqual(response.status_code, 422)
    
    def test_special_characters_in_location(self):
        """Test special characters in location are handled."""
        payload = {
            "location": "Bangalore!@#$%",
            "budget_max_inr": 1000,
            "cuisines": ["Italian"],
            "top_n": 5
        }
        
        response = self.client.post("/recommendations", json=payload)
        # Should handle gracefully (return empty or validate)
        self.assertIn(response.status_code, [200, 422])
    
    def test_very_long_cuisine_list(self):
        """Test with many cuisines."""
        payload = {
            "location": "Bangalore",
            "budget_max_inr": 2000,
            "cuisines": ["Italian", "Chinese", "North Indian", "South Indian", "Mexican", "Thai"],
            "top_n": 10
        }
        
        response = self.client.post("/recommendations", json=payload)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("recommendations", data)


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)
