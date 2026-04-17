from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from restaurant_rec.phase1.models import Restaurant
from restaurant_rec.phase1.text_normalize import canonicalize_location


@dataclass(frozen=True)
class NormalizationResult:
    restaurants: list[Restaurant]
    skipped_by_reason: dict[str, int]


def _get_first(raw: dict[str, Any], keys: list[str]) -> Any:
    for k in keys:
        if k in raw and raw[k] not in (None, ""):
            return raw[k]
    return None


def _stable_id(raw: dict[str, Any]) -> str:
    if raw.get("id"):
        return str(raw["id"])
    basis = "|".join(
        [
            str(raw.get("name", "")).strip().lower(),
            str(raw.get("city", "")).strip().lower(),
            str(raw.get("area", "")).strip().lower(),
        ]
    )
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s:
        return None
    cleaned = "".join(ch for ch in s if ch.isdigit() or ch == ".")
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def _to_cuisines(v: Any) -> list[str]:
    if v is None:
        return []
    if isinstance(v, list):
        items = v
    else:
        s = str(v)
        if "|" in s and "," in s:
            s = s.replace("|", ",")
        sep = "," if "," in s else "|"
        items = [x.strip() for x in s.split(sep)]
    cleaned = [x for x in (i.strip() for i in items) if x]
    # Canonicalize: strip + title-case tokens while preserving acronyms reasonably
    out: list[str] = []
    for c in cleaned:
        cc = " ".join(part for part in c.split() if part)
        out.append(cc)
    return out


def normalize_record(raw: dict[str, Any]) -> tuple[Restaurant | None, str | None]:
    name = str(_get_first(raw, ["name", "restaurant_name", "Restaurant Name"]) or "").strip()
    location = str(_get_first(raw, ["city", "location", "City", "Location"]) or "").strip()
    if not name:
        return None, "missing_name"
    if not location:
        return None, "missing_location"
    location = canonicalize_location(location)

    area = _get_first(raw, ["area", "locality", "Area", "Locality"])
    cuisines = _get_first(raw, ["cuisines", "Cuisines", "cuisine"])
    cost = _get_first(
        raw,
        [
            "average_cost_for_two",
            "Average Cost for two",
            "approx_cost(for two people)",
            "cost_for_two",
            "cost",
        ],
    )
    rating = _get_first(raw, ["rating", "Aggregate rating", "Rate", "Rating"])
    votes = _get_first(raw, ["votes", "reviews_count", "Votes", "Review Count"])

    return (
        Restaurant(
        id=_stable_id({"id": raw.get("id"), "name": name, "city": location, "area": area}),
        name=name,
        location=location,
        area=(str(area).strip() if area is not None else None),
        cuisines=_to_cuisines(cuisines),
        average_cost_for_two=_to_float(cost),
        rating=_to_float(rating),
        reviews_count=(int(votes) if str(votes or "").strip().isdigit() else None),
        tags=_to_cuisines(_get_first(raw, ["tags", "Tags"])),
        raw=raw,
        ),
        None,
    )


def normalize_many(raw_records: list[dict[str, Any]]) -> NormalizationResult:
    out: list[Restaurant] = []
    skipped: dict[str, int] = {}
    seen_keys: set[str] = set()
    for r in raw_records:
        rr, reason = normalize_record(r)
        if rr is None:
            skipped[reason or "unknown"] = skipped.get(reason or "unknown", 0) + 1
            continue
        key = "|".join([rr.name.strip().lower(), (rr.area or "").strip().lower(), rr.location.strip().lower()])
        if key in seen_keys:
            skipped["duplicate_name_area_location"] = skipped.get("duplicate_name_area_location", 0) + 1
            continue
        seen_keys.add(key)
        out.append(rr)
    return NormalizationResult(restaurants=out, skipped_by_reason=skipped)

