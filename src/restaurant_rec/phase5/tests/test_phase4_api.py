import unittest

from fastapi.testclient import TestClient

from restaurant_rec.phase1.config import AppConfig
from restaurant_rec.phase1.models import Restaurant
from restaurant_rec.phase1.ports import RestaurantQuery, RestaurantStore
from restaurant_rec.phase4.app import create_app


class _InMemoryStore(RestaurantStore):
    def __init__(self, restaurants):
        self._restaurants = list(restaurants)

    def upsert_many(self, restaurants):
        self._restaurants = list(restaurants)

    def query(self, q: RestaurantQuery):
        out = list(self._restaurants)
        if q.location:
            out = [r for r in out if r.location.lower() == q.location.lower()]
        if q.min_rating is not None:
            out = [r for r in out if (r.rating or 0) >= q.min_rating]
        if q.cuisines_any:
            wanted = {c.lower() for c in q.cuisines_any}
            out = [r for r in out if wanted.intersection({c.lower() for c in r.cuisines})]
        if q.budget_max_inr is not None:
            out = [
                r
                for r in out
                if (r.average_cost_for_two is None) or (r.average_cost_for_two <= q.budget_max_inr)
            ]
        return out

    def count(self):
        return len(self._restaurants)

    def list_locations(self, *, limit: int = 500):
        vals = sorted({r.location for r in self._restaurants if r.location})
        return vals[:limit]

    def list_localities(self, *, location: str, limit: int = 500):
        loc = location.lower()
        vals = sorted(
            {r.area for r in self._restaurants if r.location.lower() == loc and r.area}
        )
        return vals[:limit]


class Phase4ApiTests(unittest.TestCase):
    def _client(self):
        cfg = AppConfig()
        store = _InMemoryStore(
            [
                Restaurant(
                    id="r1",
                    name="Pasta Place",
                    location="Bangalore",
                    area="Indiranagar",
                    cuisines=["Italian"],
                    average_cost_for_two=1200,
                    rating=4.2,
                ),
                Restaurant(
                    id="r2",
                    name="Dragon Wok",
                    location="Bangalore",
                    area="Koramangala",
                    cuisines=["Chinese"],
                    average_cost_for_two=800,
                    rating=4.0,
                ),
                Restaurant(
                    id="r3",
                    name="Budget Bites",
                    location="Delhi",
                    cuisines=["Chinese"],
                    average_cost_for_two=300,
                    rating=3.6,
                ),
            ]
        )
        app = create_app(cfg=cfg, store=store)  # type: ignore[arg-type]
        return TestClient(app)

    def test_health(self):
        c = self._client()
        r0 = c.get("/")
        self.assertEqual(r0.status_code, 200)
        self.assertIn("RestaurantRec", r0.text)
        rloc = c.get("/locations")
        self.assertEqual(rloc.status_code, 200)
        self.assertIn("Bangalore", rloc.json())
        r = c.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])
        self.assertEqual(r.json()["restaurant_count"], 3)

    def test_recommendations_basic(self):
        c = self._client()
        r = c.post(
            "/recommendations",
            json={
                "location": "Bangalore",
                "budget_max_inr": 1500,
                "cuisines": ["Italian", "Chinese"],
                "min_rating": 3.5,
                "top_n": 3,
            },
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("recommendations", data)
        self.assertGreaterEqual(len(data["recommendations"]), 1)

    def test_recommendations_budget_filter(self):
        c = self._client()
        r = c.post(
            "/recommendations",
            json={
                "location": "Bangalore",
                "budget_max_inr": 900,
                "cuisines": ["Italian", "Chinese"],
                "min_rating": 3.5,
                "top_n": 10,
            },
        )
        self.assertEqual(r.status_code, 200)
        recs = r.json()["recommendations"]
        # Pasta Place should be filtered out due to cost 1200 > 900
        names = {x["restaurant_name"] for x in recs}
        self.assertNotIn("Pasta Place", names)


if __name__ == "__main__":
    unittest.main()

