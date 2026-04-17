from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from restaurant_rec.phase1.models import Restaurant
from restaurant_rec.phase1.ports import RestaurantQuery, RestaurantStore


def _restaurants_to_df(restaurants: Iterable[Restaurant]) -> pd.DataFrame:
    rows = []
    for r in restaurants:
        rows.append(
            {
                "id": r.id,
                "name": r.name,
                "location": r.location,
                "area": r.area,
                "cuisines": r.cuisines,
                "average_cost_for_two": r.average_cost_for_two,
                "rating": r.rating,
                "reviews_count": r.reviews_count,
                "tags": r.tags,
            }
        )
    return pd.DataFrame(rows)


def _df_to_restaurants(df: pd.DataFrame) -> list[Restaurant]:
    out: list[Restaurant] = []
    location_col = "location" if "location" in df.columns else "city"
    for row in df.to_dict(orient="records"):
        cs = row.get("cuisines")
        if cs is None or (isinstance(cs, float) and pd.isna(cs)):
            cuisines_list: list[str] = []
        elif isinstance(cs, list):
            cuisines_list = cs
        else:
            try:
                cuisines_list = list(cs)
            except TypeError:
                cuisines_list = [str(cs)]

        tg = row.get("tags")
        if tg is None or (isinstance(tg, float) and pd.isna(tg)):
            tags_list: list[str] = []
        elif isinstance(tg, list):
            tags_list = tg
        else:
            try:
                tags_list = list(tg)
            except TypeError:
                tags_list = [str(tg)]

        out.append(
            Restaurant(
                id=str(row.get("id")),
                name=str(row.get("name") or ""),
                location=str(row.get(location_col) or ""),
                area=(str(row.get("area")) if row.get("area") not in (None, "") else None),
                cuisines=cuisines_list,
                average_cost_for_two=(
                    float(row["average_cost_for_two"])
                    if row.get("average_cost_for_two") not in (None, "")
                    and not (isinstance(row.get("average_cost_for_two"), float) and pd.isna(row.get("average_cost_for_two")))
                    else None
                ),
                rating=(
                    float(row["rating"])
                    if row.get("rating") not in (None, "")
                    and not (isinstance(row.get("rating"), float) and pd.isna(row.get("rating")))
                    else None
                ),
                reviews_count=(
                    int(row["reviews_count"])
                    if row.get("reviews_count") not in (None, "")
                    and not (isinstance(row.get("reviews_count"), float) and pd.isna(row.get("reviews_count")))
                    else None
                ),
                tags=tags_list,
                raw=None,
            )
        )
    return out


class ParquetRestaurantStore(RestaurantStore):
    def __init__(self, path: Path):
        self._path = path
        self._df: pd.DataFrame | None = None

    def _load_df(self) -> pd.DataFrame:
        if self._df is not None:
            return self._df
        if self._path.exists():
            try:
                self._df = pd.read_parquet(self._path)
                print(f"[DEBUG] Loaded Parquet file {self._path} with shape {self._df.shape}")
            except Exception as e:
                print(f"[ERROR] Failed to load Parquet file {self._path}: {e}")
                self._df = pd.DataFrame(
                    columns=[
                        "id",
                        "name",
                        "location",
                        "area",
                        "cuisines",
                        "average_cost_for_two",
                        "rating",
                        "reviews_count",
                        "tags",
                    ]
                )
        else:
            print(f"[ERROR] Parquet file not found: {self._path}")
            self._df = pd.DataFrame(
                columns=[
                    "id",
                    "name",
                    "location",
                    "area",
                    "cuisines",
                    "average_cost_for_two",
                    "rating",
                    "reviews_count",
                    "tags",
                ]
            )
        return self._df

    def _persist(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._load_df().to_parquet(self._path, index=False)

    def upsert_many(self, restaurants: Iterable[Restaurant]) -> None:
        incoming = _restaurants_to_df(restaurants)
        if incoming.empty:
            return
        # Phase 1 ingestion loads the full dataset; treat this as a full refresh
        # to avoid retaining stale rows when normalization logic changes.
        self._df = incoming.drop_duplicates(subset=["id"], keep="last")
        self._persist()

    def query(self, q: RestaurantQuery) -> list[Restaurant]:
        df = self._load_df()
        if df.empty:
            return []

        filtered = df
        location_col = "location" if "location" in filtered.columns else "city"
        if q.location:
            loc = q.location.strip().lower()
            filtered = filtered[filtered[location_col].astype(str).str.lower() == loc]

        if q.locality and "area" in filtered.columns:
            area = q.locality.strip().lower()
            filtered = filtered[filtered["area"].fillna("").astype(str).str.lower() == area]

        # Only filter by rating if min_rating > 0 (most restaurants in dataset have no rating)
        if q.min_rating is not None and q.min_rating > 0 and "rating" in filtered.columns:
            filtered = filtered[(filtered["rating"].fillna(0.0).astype(float) >= q.min_rating)]

        if q.cuisines_any:
            wanted = {c.strip().lower() for c in q.cuisines_any if c.strip()}
            if wanted:
                def _as_iterable(cs):
                    if cs is None:
                        return []
                    # pandas may store lists as numpy arrays / objects; avoid truthiness checks
                    if isinstance(cs, float) and pd.isna(cs):
                        return []
                    if isinstance(cs, (list, tuple, set)):
                        return cs
                    try:
                        # numpy arrays / pandas arrays
                        return list(cs)
                    except TypeError:
                        return [cs]

                mask = filtered["cuisines"].apply(
                    lambda cs: bool(
                        {str(x).strip().lower() for x in _as_iterable(cs) if str(x).strip()}.intersection(wanted)
                    )
                )
                filtered = filtered[mask]

        if q.budget_max_inr is not None and "average_cost_for_two" in filtered.columns:
            filtered = filtered[
                filtered["average_cost_for_two"].fillna(1e18).astype(float)
                <= float(q.budget_max_inr)
            ]

        return _df_to_restaurants(filtered)

    def count(self) -> int:
        return int(len(self._load_df()))

    def list_locations(self, *, limit: int = 500) -> list[str]:
        df = self._load_df()
        if df.empty:
            return []
        col = "location" if "location" in df.columns else "city"
        vals = sorted({str(x) for x in df[col].dropna().unique() if str(x).strip()})
        return vals[:limit]

    def list_localities(self, *, location: str, limit: int = 500) -> list[str]:
        df = self._load_df()
        if df.empty or "area" not in df.columns:
            return []
        col = "location" if "location" in df.columns else "city"
        loc = str(location).strip().lower()
        sub = df[df[col].astype(str).str.lower() == loc]
        vals = sorted({str(x) for x in sub["area"].dropna().unique() if str(x).strip()})
        return vals[:limit]

    def get_by_id(self, restaurant_id: str) -> Restaurant | None:
        """Get a restaurant by its ID."""
        df = self._load_df()
        if df.empty:
            return None
        
        matching_rows = df[df["id"] == str(restaurant_id)]
        if matching_rows.empty:
            return None
        
        restaurants = _df_to_restaurants(matching_rows)
        return restaurants[0] if restaurants else None

