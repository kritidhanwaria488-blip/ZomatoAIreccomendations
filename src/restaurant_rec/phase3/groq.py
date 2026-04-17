from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests


@dataclass(frozen=True)
class GroqConfig:
    api_key: str
    model: str
    base_url: str = "https://api.groq.com/openai/v1"
    timeout_s: int = 45

    @staticmethod
    def from_env(env: dict[str, str] | None = None) -> "GroqConfig":
        env = env or dict(os.environ)
        return GroqConfig(
            api_key=env.get("GROQ_API_KEY", ""),
            model=env.get("GROQ_MODEL", "mixtral-8x7b-32768"),
        )


def load_dotenv(path: str | Path = ".env") -> dict[str, str]:
    """
    Minimal .env loader (no extra dependency).
    Sets variables into os.environ if not already present.
    """
    p = Path(path)
    if not p.exists():
        return {}

    loaded: dict[str, str] = {}
    for raw_line in p.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v
        if k:
            loaded[k] = v
    return loaded


def load_dotenv_auto(start_dir: str | Path | None = None) -> dict[str, str]:
    """
    Load `.env` from:
    - current working directory (or `start_dir`) and its parents
    - fallback: user home directory (`~/.env`)

    Returns the loaded key/value pairs (without printing secrets).
    """
    start = Path(start_dir) if start_dir is not None else Path.cwd()
    start = start.resolve()

    cur = start
    while True:
        candidate = cur / ".env"
        if candidate.exists():
            return load_dotenv(candidate)
        if cur.parent == cur:
            break
        cur = cur.parent

    home_candidate = Path.home() / ".env"
    if home_candidate.exists():
        return load_dotenv(home_candidate)

    return {}


class GroqClient:
    """
    Groq OpenAI-compatible chat completions client.
    """

    def __init__(self, cfg: GroqConfig):
        self._cfg = cfg

    def generate(self, prompt: str) -> str:
        if not self._cfg.api_key:
            raise RuntimeError("Missing GROQ_API_KEY. Put it in `.env` or your environment.")

        url = f"{self._cfg.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._cfg.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self._cfg.model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }

        resp = requests.post(
            url, headers=headers, data=json.dumps(payload), timeout=self._cfg.timeout_s
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"Groq API error {resp.status_code}: {resp.text}")

        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"Unexpected Groq response shape: {data}") from e


__all__ = ["GroqConfig", "GroqClient", "load_dotenv", "load_dotenv_auto"]

