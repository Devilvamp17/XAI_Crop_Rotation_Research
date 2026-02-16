from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np


DEFAULT_TOKEN_PATTERN = r"(?u)[A-Za-z0-9_:]+"


@dataclass(frozen=True)
class TfidfConfig:
    ngram_range: tuple[int, int] = (1, 2)
    sublinear_tf: bool = True
    smooth_idf: bool = True
    min_df: int | float = 2
    max_df: int | float = 0.9
    token_pattern: str = DEFAULT_TOKEN_PATTERN


class SparseRetriever(Protocol):
    def score(self, query: str, query_fields: dict[str, str] | None = None) -> np.ndarray: ...

