from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CacheConfig:
    cache_dir: Path
    ttl_seconds: int | None = None  # None means no expiration


class RecommendationsCache:
    """
    Simple file-based cache for recommendations keyed by normalized preferences.
    """

    def __init__(self, config: CacheConfig | None = None):
        if config is None:
            config = CacheConfig(cache_dir=Path(".cache"))
        self._config = config
        self._config.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key(self, prefs_dict: dict[str, Any]) -> str:
        """Generate cache key from preferences dictionary."""
        # Normalize and hash preferences
        normalized = json.dumps(prefs_dict, sort_keys=True)
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def _cache_path(self, key: str) -> Path:
        return self._config.cache_dir / f"rec_{key}.json"

    def get(self, prefs_dict: dict[str, Any]) -> list[dict] | None:
        """Get cached recommendations if they exist and are not expired."""
        key = self._key(prefs_dict)
        cache_path = self._cache_path(key)

        if not cache_path.exists():
            return None

        # Check TTL if configured
        if self._config.ttl_seconds is not None:
            import time

            mtime = cache_path.stat().st_mtime
            if time.time() - mtime > self._config.ttl_seconds:
                cache_path.unlink()
                return None

        try:
            with open(cache_path, "r") as f:
                data = json.load(f)
                return data.get("recommendations")
        except Exception:
            return None

    def set(self, prefs_dict: dict[str, Any], recommendations: list[dict]) -> None:
        """Cache recommendations."""
        key = self._key(prefs_dict)
        cache_path = self._cache_path(key)

        data = {
            "preferences": prefs_dict,
            "recommendations": recommendations,
            "cached_at": json.dumps(None),  # Would add timestamp in production
        }

        with open(cache_path, "w") as f:
            json.dump(data, f, indent=2)

    def clear(self) -> int:
        """Clear all cached recommendations. Returns number of files deleted."""
        count = 0
        for f in self._config.cache_dir.glob("rec_*.json"):
            f.unlink()
            count += 1
        return count


__all__ = ["RecommendationsCache", "CacheConfig"]
