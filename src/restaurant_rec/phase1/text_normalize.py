from __future__ import annotations


def canonicalize_location(location: str) -> str:
    s = " ".join(str(location or "").strip().split())
    low = s.lower()
    if not low:
        return ""

    # Common India city variants / regional dataset labels
    if "bangalore" in low or "bengaluru" in low:
        return "Bangalore"
    if "delhi" in low or "ncr" in low:
        return "Delhi"
    if "mumbai" in low or "bombay" in low:
        return "Mumbai"

    return s


__all__ = ["canonicalize_location"]

