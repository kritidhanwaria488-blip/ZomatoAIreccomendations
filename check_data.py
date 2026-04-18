#!/usr/bin/env python3
"""Check if data file exists and its status."""
from pathlib import Path

data_path = Path("data/restaurants.parquet")

if data_path.exists():
    size = data_path.stat().st_size / (1024 * 1024)
    print(f"✅ Data file exists: {data_path}")
    print(f"   Size: {size:.2f} MB")
else:
    print(f"❌ Data file NOT found: {data_path}")
    print("   Need to run: python -m restaurant_rec ingest")
