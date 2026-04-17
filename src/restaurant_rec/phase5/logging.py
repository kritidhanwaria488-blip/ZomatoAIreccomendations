from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RecommendationLogEntry:
    timestamp: float
    preferences: dict[str, Any]
    result_count: int
    relaxations_applied: list[str]
    latency_ms: float
    llm_used: bool
    llm_fallback: bool = False
    error: str | None = None


class RecommendationLogger:
    """
    Structured logging for recommendation requests.
    """

    def __init__(self, log_dir: Path | None = None):
        self._log_dir = log_dir or Path("logs")
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._log_file = self._log_dir / "recommendations.jsonl"

    def log(
        self,
        preferences: dict[str, Any],
        result_count: int,
        relaxations_applied: list[str],
        latency_ms: float,
        llm_used: bool = False,
        llm_fallback: bool = False,
        error: str | None = None,
    ) -> None:
        """Log a recommendation request."""
        entry = RecommendationLogEntry(
            timestamp=time.time(),
            preferences=preferences,
            result_count=result_count,
            relaxations_applied=relaxations_applied,
            latency_ms=latency_ms,
            llm_used=llm_used,
            llm_fallback=llm_fallback,
            error=error,
        )

        # Convert to dict for JSON logging
        entry_dict = {
            "timestamp": entry.timestamp,
            "preferences": entry.preferences,
            "result_count": entry.result_count,
            "relaxations_applied": entry.relaxations_applied,
            "latency_ms": entry.latency_ms,
            "llm_used": entry.llm_used,
            "llm_fallback": entry.llm_fallback,
            "error": entry.error,
        }

        with open(self._log_file, "a") as f:
            f.write(json.dumps(entry_dict) + "\n")

    def get_stats(self) -> dict[str, Any]:
        """Get basic statistics from logs."""
        if not self._log_file.exists():
            return {"total_requests": 0}

        total = 0
        llm_count = 0
        fallback_count = 0
        errors = 0
        total_latency = 0.0

        with open(self._log_file, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    total += 1
                    if entry.get("llm_used"):
                        llm_count += 1
                    if entry.get("llm_fallback"):
                        fallback_count += 1
                    if entry.get("error"):
                        errors += 1
                    total_latency += entry.get("latency_ms", 0)
                except json.JSONDecodeError:
                    continue

        return {
            "total_requests": total,
            "llm_requests": llm_count,
            "llm_fallbacks": fallback_count,
            "errors": errors,
            "avg_latency_ms": total_latency / total if total > 0 else 0,
        }


__all__ = ["RecommendationLogger", "RecommendationLogEntry"]
