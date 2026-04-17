from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from datasets import load_dataset

from restaurant_rec.phase1.ports import DatasetSource


@dataclass(frozen=True)
class HFDatasetConfig:
    name: str
    split: str = "train"
    cache_dir: Path | None = None


class HuggingFaceDatasetSource(DatasetSource):
    def __init__(self, cfg: HFDatasetConfig):
        self._cfg = cfg

    def load(self) -> list[dict[str, Any]]:
        ds = load_dataset(
            self._cfg.name,
            split=self._cfg.split,
            cache_dir=str(self._cfg.cache_dir) if self._cfg.cache_dir else None,
        )
        return [dict(row) for row in ds]

