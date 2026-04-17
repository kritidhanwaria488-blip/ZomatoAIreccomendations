#!/usr/bin/env python3
"""
Performance benchmark for the Restaurant Recommendation API (Phase 5).
"""

import time
import requests
import statistics
from datetime import datetime

API_BASE = "http://127.0.0.1:8003"


def benchmark_endpoint(name: str, method: str, endpoint: str, payload=None, iterations=10):
    """Benchmark an API endpoint."""
    times = []
    
    url = f"{API_BASE}{endpoint}"
    
    for i in range(iterations):
        start = time.time()
        try:
            if method == "GET":
                response = requests.get(url, timeout=30)
            else:
                response = requests.post(url, json=payload, timeout=30)
            
            elapsed = (time.time() - start) * 1000  # Convert to ms
            times.append(elapsed)
            
            if response.status_code != 200:
                print(f"  Warning: Request {i+1} returned status {response.status_code}")
                
        except Exception as e:
            print(f"  Error on request {i+1}: {e}")
    
    if times:
        print(f"\n{name}:")
        print(f"  Requests: {len(times)}")
        print(f"  Min: {min(times):.1f}ms")
        print(f"  Max: {max(times):.1f}ms")
        print(f"  Mean: {statistics.mean(times):.1f}ms")
        print(f"  Median: {statistics.median(times):.1f}ms")
        if len(times) > 1:
            print(f"  Std Dev: {statistics.stdev(times):.1f}ms")
    else:
        print(f"\n{name}: No successful requests")
    
    return times


def main():
    print("=" * 60)
    print("PERFORMANCE BENCHMARK - Restaurant Recommendation API")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Check if API is running
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        data = response.json()
        print(f"\nAPI Status: OK")
        print(f"Restaurant Count: {data['restaurant_count']:,}")
    except Exception as e:
        print(f"\n❌ API not accessible: {e}")
        print(f"Please start the API: python -m uvicorn restaurant_rec.phase4.app:create_app --factory")
        return 1
    
    print("\n" + "-" * 60)
    print("Starting benchmarks...")
    print("-" * 60)
    
    # Benchmark 1: Health endpoint
    benchmark_endpoint(
        "Health Check",
        "GET",
        "/health",
        iterations=20
    )
    
    # Benchmark 2: Locations endpoint
    benchmark_endpoint(
        "Get Locations",
        "GET",
        "/locations",
        iterations=10
    )
    
    # Benchmark 3: Localities endpoint
    benchmark_endpoint(
        "Get Localities (Bangalore)",
        "GET",
        "/localities?location=Bangalore",
        iterations=10
    )
    
    # Benchmark 4: Basic recommendations
    benchmark_endpoint(
        "Recommendations - Basic",
        "POST",
        "/recommendations",
        payload={
            "location": "Bangalore",
            "budget_max_inr": 1000,
            "cuisines": ["North Indian"],
            "top_n": 5
        },
        iterations=10
    )
    
    # Benchmark 5: High budget recommendations
    benchmark_endpoint(
        "Recommendations - High Budget",
        "POST",
        "/recommendations",
        payload={
            "location": "Bangalore",
            "budget_max_inr": 10000,
            "cuisines": ["Italian"],
            "top_n": 10
        },
        iterations=10
    )
    
    # Benchmark 6: Specific area
    benchmark_endpoint(
        "Recommendations - Whitefield",
        "POST",
        "/recommendations",
        payload={
            "location": "Whitefield",
            "budget_max_inr": 2000,
            "cuisines": ["North Indian", "Chinese"],
            "top_n": 5
        },
        iterations=10
    )
    
    print("\n" + "=" * 60)
    print("BENCHMARK COMPLETE")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    exit(main())
