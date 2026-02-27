from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Disagreement:
    kind: str
    summary: str
