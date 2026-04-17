from __future__ import annotations

import json
from dataclasses import dataclass

from restaurant_rec.phase3.groq import GroqClient, GroqConfig, load_dotenv_auto


@dataclass(frozen=True)
class SmokeResult:
    name: str
    ok: bool
    detail: str = ""


def _parse_json_loose(text: str) -> tuple[dict | list | None, str | None]:
    """
    Best-effort JSON parser:
    - try full string
    - else extract first {...} or [...] block
    """
    s = text.strip()
    try:
        return json.loads(s), None
    except Exception:
        pass

    first_obj = s.find("{")
    last_obj = s.rfind("}")
    if 0 <= first_obj < last_obj:
        snippet = s[first_obj : last_obj + 1]
        try:
            return json.loads(snippet), None
        except Exception as e:  # noqa: BLE001
            return None, f"json parse error (object snippet): {e}"

    first_arr = s.find("[")
    last_arr = s.rfind("]")
    if 0 <= first_arr < last_arr:
        snippet = s[first_arr : last_arr + 1]
        try:
            return json.loads(snippet), None
        except Exception as e:  # noqa: BLE001
            return None, f"json parse error (array snippet): {e}"

    return None, "no JSON object/array found"


def _test_connectivity(client: GroqClient) -> SmokeResult:
    text = client.generate("Reply with exactly: OK")
    ok = "OK" in text.strip().upper()
    return SmokeResult("connectivity", ok, detail=text.strip()[:200])


def _test_json_only(client: GroqClient) -> SmokeResult:
    prompt = "\n".join(
        [
            "Return ONLY valid JSON. No markdown, no code fences, no extra text.",
            "Your response must start with '{' and end with '}'.",
            'Return: {"ok": true, "source": "smoke_test"}',
        ]
    )
    text = client.generate(prompt).strip()
    obj, err = _parse_json_loose(text)
    if obj is None:
        return SmokeResult("json_only", False, detail=f"{err}; text={text[:200]!r}")

    ok = isinstance(obj, dict) and obj.get("ok") is True
    return SmokeResult("json_only", ok, detail=str(obj)[:200])


def _test_choose_from_candidates(client: GroqClient) -> SmokeResult:
    candidates = [{"id": "r1", "name": "A"}, {"id": "r2", "name": "B"}, {"id": "r3", "name": "C"}]
    prompt = "\n".join(
        [
            "Choose ONLY from these candidates. Output ONLY valid JSON.",
            "No markdown, no code fences, no extra text.",
            "Your response must start with '{' and end with '}'.",
            json.dumps({"candidates": candidates}),
            'Return: {"restaurant_id": "...", "reason": "..."}',
        ]
    )
    text = client.generate(prompt).strip()
    obj, err = _parse_json_loose(text)
    if obj is None or not isinstance(obj, dict):
        return SmokeResult("choose_from_candidates", False, detail=f"{err}; text={text[:200]!r}")

    rid = str(obj.get("restaurant_id", ""))
    ok = rid in {c["id"] for c in candidates}
    return SmokeResult("choose_from_candidates", ok, detail=f"restaurant_id={rid!r}")


def main() -> int:
    # Load .env from CWD/parents or ~/.env
    load_dotenv_auto()
    cfg = GroqConfig.from_env()
    client = GroqClient(cfg)

    tests = [
        _test_connectivity,
        _test_json_only,
        _test_choose_from_candidates,
    ]

    results: list[SmokeResult] = []
    for t in tests:
        try:
            results.append(t(client))
        except Exception as e:  # noqa: BLE001
            results.append(SmokeResult(t.__name__, False, detail=str(e)))

    failed = [r for r in results if not r.ok]
    for r in results:
        status = "PASS" if r.ok else "FAIL"
        print(f"{status} - {r.name}: {r.detail}")

    if failed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

