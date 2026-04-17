import pandas as pd

parquet_path = 'data/restaurants.parquet'

try:
    df = pd.read_parquet(parquet_path)
    print(f"Loaded {len(df)} rows.")
    print(df.head())
except Exception as e:
    print(f"[ERROR] Failed to load Parquet file: {e}")
