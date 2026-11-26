"""Warstwa 2: AI dotyka wyłącznie tekstu nieustrukturyzowanego (nazwa, opis)."""

from __future__ import annotations

from ..config import AppConfig, LLMSettings
from .mock import MockClassifier
from .types import Classifier, ClassificationRun, TextItem, Usage, numbers_preserved


def make_classifier(config: AppConfig, settings: LLMSettings, force_mock: bool = False,
                    examples: list[tuple[str, str]] | None = None) -> Classifier:
    """Prawdziwe AI, jeśli jest klucz i nie wymuszono trybu mock; w przeciwnym razie reguły słownikowe.
    examples: produkty z kartoteki z ich kategoriami, dopisywane do promptu jako wzór."""
    if force_mock or not settings.has_key:
        return MockClassifier(config.ai)
    from .llm import LLMClassifier  # import tylko, gdy potrzebny klient API

    return LLMClassifier(settings, config.ai, examples=examples)


__all__ = ["Classifier", "ClassificationRun", "TextItem", "Usage", "make_classifier", "numbers_preserved"]
