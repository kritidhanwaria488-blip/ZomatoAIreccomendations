#!/usr/bin/env python3
"""Test edge cases for the restaurant recommendation API."""

import requests
import sys

API_BASE = "http://127.0.0.1:8003"

def test_case(name: str, payload: dict, expected_status: int = 200):
    """Run a test case and print results."""
    try:
        r = requests.post(f"{API_BASE}/recommendations", json=payload, timeout=10)
        data = r.json()
        rec_count = len(data.get("recommendations", []))
        relaxations = data.get("relaxations_applied", [])
        
        status_ok = "✅" if r.status_code == expected_status else "❌"
        print(f"{status_ok} {name}")
        print(f"   Status: {r.status_code}")
        print(f"   Results: {rec_count} restaurants")
        if relaxations:
            print(f"   Relaxations: {relaxations}")
        return r.status_code == expected_status
    except Exception as e:
        print(f"❌ {name}")
        print(f"   Error: {e}")
        return False

def main():
    print("=" * 60)
    print("EDGE CASE TESTING - Restaurant Recommendation API")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    # Test 1: Valid request
    if test_case("Valid request (Bangalore, budget 1000)", 
                 {"location": "Bangalore", "budget_max_inr": 1000, "cuisines": ["Italian"], "top_n": 3}):
        passed += 1
    else:
        failed += 1
    
    # Test 2: Empty location
    if test_case("Empty location (should still return results)", 
                 {"location": "", "budget_max_inr": 1000, "cuisines": ["Italian"]}):
        passed += 1
    else:
        failed += 1
    
    # Test 3: Zero budget
    if test_case("Zero budget (edge case)", 
                 {"location": "Bangalore", "budget_max_inr": 0, "cuisines": ["Italian"]}):
        passed += 1
    else:
        failed += 1
    
    # Test 4: Non-existent location
    if test_case("Non-existent location (XYZ123)", 
                 {"location": "XYZ123", "budget_max_inr": 1000, "cuisines": ["Italian"]}):
        passed += 1
    else:
        failed += 1
    
    # Test 5: Very high budget
    if test_case("Very high budget (100000)", 
                 {"location": "Bangalore", "budget_max_inr": 100000, "cuisines": ["Italian"], "top_n": 3}):
        passed += 1
    else:
        failed += 1
    
    # Test 6: Empty cuisines
    if test_case("Empty cuisines list", 
                 {"location": "Bangalore", "budget_max_inr": 1000, "cuisines": []}):
        passed += 1
    else:
        failed += 1
    
    # Test 7: Large top_n
    if test_case("Large top_n (100, should cap at 50)", 
                 {"location": "Bangalore", "budget_max_inr": 5000, "cuisines": ["North Indian"], "top_n": 100}):
        passed += 1
    else:
        failed += 1
    
    # Test 8: Missing cuisines field
    if test_case("Missing cuisines field", 
                 {"location": "Bangalore", "budget_max_inr": 1000}):
        passed += 1
    else:
        failed += 1
    
    # Test 9: Min rating 0
    if test_case("Min rating 0 (should include all)", 
                 {"location": "Bangalore", "budget_max_inr": 1000, "cuisines": ["Chinese"], "min_rating": 0, "top_n": 3}):
        passed += 1
    else:
        failed += 1
    
    # Test 10: Min rating 5
    if test_case("Min rating 5 (no restaurants have ratings)", 
                 {"location": "Bangalore", "budget_max_inr": 1000, "cuisines": ["Chinese"], "min_rating": 5, "top_n": 3}):
        passed += 1
    else:
        failed += 1
    
    # Test 11: Special characters in location
    if test_case("Special characters in location", 
                 {"location": "Bangalore!@#$%", "budget_max_inr": 1000, "cuisines": ["Italian"]}):
        passed += 1
    else:
        failed += 1
    
    # Test 12: Negative budget
    if test_case("Negative budget (edge case)", 
                 {"location": "Bangalore", "budget_max_inr": -100, "cuisines": ["Italian"]}):
        passed += 1
    else:
        failed += 1
    
    # Test 13: Whitefield (popular area)
    if test_case("Specific area - Whitefield", 
                 {"location": "Whitefield", "budget_max_inr": 1500, "cuisines": ["North Indian"], "top_n": 5}):
        passed += 1
    else:
        failed += 1
    
    # Test 14: Health endpoint
    try:
        r = requests.get(f"{API_BASE}/health", timeout=5)
        if r.status_code == 200:
            print("✅ Health endpoint")
            print(f"   Response: {r.json()}")
            passed += 1
        else:
            print(f"❌ Health endpoint (status: {r.status_code})")
            failed += 1
    except Exception as e:
        print(f"❌ Health endpoint: {e}")
        failed += 1
    
    # Test 15: Locations endpoint
    try:
        r = requests.get(f"{API_BASE}/locations", timeout=5)
        if r.status_code == 200:
            locations = r.json()
            print("✅ Locations endpoint")
            print(f"   Total locations: {len(locations)}")
            passed += 1
        else:
            print(f"❌ Locations endpoint (status: {r.status_code})")
            failed += 1
    except Exception as e:
        print(f"❌ Locations endpoint: {e}")
        failed += 1
    
    print()
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
