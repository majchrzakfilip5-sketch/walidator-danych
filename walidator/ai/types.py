"""Typy wspólne dla klasyfikatora AI i trybu mock."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Protocol

from ..config import PricingConfig
from ..models import Classification

LogFn = Callable[[str], None]


@dataclass(frozen=True)
class TextItem:
    """Jedyne, co trafia do AI: identyfikator wiersza, nazwa i opis. Bez EAN, cen, wag i rozmiarów."""

    id: int
    name: str
    description: str


@dataclass
class Usage:
    requests: int = 0
    prompt_tokens: int = 0
    cached_tokens: int = 0
    completion_tokens: int = 0

    def add(self, other: Usage) -> None:
        self.requests += other.requests
        self.prompt_tokens += other.prompt_tokens
        self.cached_tokens += other.cached_tokens
        self.completion_tokens += other.completion_tokens

    def cost_usd(self, pricing: PricingConfig) -> float:
        uncached = max(self.prompt_tokens - self.cached_tokens, 0)
        return (uncached * pricing.input_per_1m
                + self.cached_tokens * pricing.input_cached_per_1m
                + self.completion_tokens * pricing.output_per_1m) / 1_000_000


@dataclass
class ClassificationRun:
    results: dict[int, Classification] = field(default_factory=dict)
    failures: dict[int, str] = field(default_factory=dict)   # id -> powód, dla którego brak wyniku
    usage: Usage = field(default_factory=Usage)
    retried: int = 0                                         # wierszy wysłanych ponownie po złej odpowiedzi


class Classifier(Protocol):
    mode: str            # "ai" albo "mock"
    model_name: str

    def classify(self, items: list[TextItem], log: LogFn) -> ClassificationRun: ...


_NUMBER = re.compile(r"\d+")


def numbers_preserved(original: str, normalized: str) -> bool:
    """Strażnik: znormalizowana nazwa musi zawierać dokładnie te same liczby, w tej samej kolejności."""
    return _NUMBER.findall(original) == _NUMBER.findall(normalized)
