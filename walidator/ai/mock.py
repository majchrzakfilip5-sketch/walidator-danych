"""Tryb mock: reguły słownikowe zamiast AI, żeby całość działała offline i bez klucza API.

Zasada ta sama co dla AI: gdy słownik nie daje jednoznacznej odpowiedzi, pewność jest niska
i wiersz trafia do ręcznej weryfikacji. Nie zgadujemy.
"""

from __future__ import annotations

import re
from pathlib import Path
from collections import defaultdict

from ..config import AIConfig
from ..models import Classification
from ..parsers import fold
from .types import ClassificationRun, LogFn, TextItem

# Slowniki branzowe (kategorie, marki, literowki) sa DANYMI wdrozenia, nie kodem,
# dlatego nie ma ich w repo: wczytuje je wczytaj_slownik() z pliku wskazanego
# w konfiguracji (ai.mock_dictionary). Bez slownika mock dziala, tylko nic nie zna.
KEYWORDS: dict[str, list[tuple[str, int]]] = {}
BRANDS: list[str] = []
TYPOS: dict[str, str] = {}
SEGMENTY: list[tuple[list[str], str]] = []      # [(slowa-klucze, segment)]
SEGMENT_DOMYSLNY: str = ""
PISOWNIA: dict[str, str] = {}                   # slowo -> kanoniczna pisownia
_PATTERNS: dict[str, list[tuple[re.Pattern[str], int]]] = {}


def wczytaj_slownik(path: str | Path) -> None:
    """Wczytuje slownik mocka z YAML-a profilu i przebudowuje wzorce."""
    global KEYWORDS, BRANDS, TYPOS, _PATTERNS, SEGMENTY, SEGMENT_DOMYSLNY, PISOWNIA
    import yaml
    dane = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    KEYWORDS = {kat: [(str(rdzen), int(waga)) for rdzen, waga in slowa]
                for kat, slowa in (dane.get("keywords") or {}).items()}
    BRANDS = [str(b) for b in (dane.get("brands") or [])]
    TYPOS = {str(k): str(v) for k, v in (dane.get("typos") or {}).items()}
    _PATTERNS = {kat: [(re.compile(rf"\b{re.escape(rdzen)}"), waga) for rdzen, waga in slowa]
                 for kat, slowa in KEYWORDS.items()}
    SEGMENTY = [([str(w) for w in (r.get("gdy") or [])], str(r.get("segment", "")))
                for r in ((dane.get("segmenty") or {}).get("reguly") or [])]
    SEGMENT_DOMYSLNY = str((dane.get("segmenty") or {}).get("domyslny", ""))
    PISOWNIA = {str(k): str(v) for k, v in (dane.get("pisownia") or {}).items()}


# Słowa, po których zaczyna się dodatek, np. "Kask | do jazdy na rowerze" albo "Torba | na buty".
_HEAD_SPLIT = re.compile(r"\s(?:z|ze|w|po)\s|\s\+\s")


class MockClassifier:
    mode = "mock"
    model_name = "słownik reguł (mock)"

    def __init__(self, ai: AIConfig) -> None:
        self.ai = ai

    def classify(self, items: list[TextItem], log: LogFn) -> ClassificationRun:
        run = ClassificationRun()
        for item in items:
            run.results[item.id] = self.classify_one(item)
        log(f"tryb mock: {len(items)} wierszy sklasyfikowanych regułami słownikowymi")
        return run

    def classify_one(self, item: TextItem) -> Classification:
        name = normalize_name(item.name)
        category, confidence, reasoning = self._category(name, item.description)
        folded = fold(name + " " + item.description)
        segment = next((seg for slowa, seg in SEGMENTY if any(w in folded for w in slowa)),
                       SEGMENT_DOMYSLNY)
        if segment not in self.ai.segments:
            segment = self.ai.segments[0]
        return Classification(category, name, segment, confidence, reasoning)

    def _category(self, name: str, description: str) -> tuple[str, float, str]:
        scores = self._scores(name)
        if not scores:
            from_description = self._scores(description, head_weight=1)
            if from_description:
                best = max(from_description, key=from_description.get)
                return best, 0.55, f"Tryb mock: nazwa bez słów ze słownika, skojarzenie tylko z opisem ({best})."
            return "Inne", 0.3, "Tryb mock: brak słów kluczowych ze słownika w nazwie i opisie."
        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
        (best, top), second = ranked[0], (ranked[1][1] if len(ranked) > 1 else 0)
        if second == 0:
            return best, (0.95 if top >= 6 else 0.85), f"Tryb mock: nazwa pasuje tylko do kategorii {best}."
        if top >= 2 * second:
            return best, 0.8, f"Tryb mock: przeważają słowa z kategorii {best}, w nazwie także {ranked[1][0]}."
        rivals = ", ".join(c for c, s in ranked if s * 2 > top)
        return best, 0.45, f"Tryb mock: nazwa pasuje do kilku kategorii ({rivals})."

    def _scores(self, text: str, head_weight: int = 2) -> dict[str, int]:
        folded = fold(text)
        head, _, tail = _split_head(folded)
        scores: dict[str, int] = defaultdict(int)
        for category, words in _PATTERNS.items():
            if category not in self.ai.categories:
                continue
            for pattern, weight in words:
                if pattern.search(head):
                    scores[category] += weight * head_weight
                elif pattern.search(tail):
                    scores[category] += weight
        return dict(scores)


def _split_head(text: str) -> tuple[str, str, str]:
    match = _HEAD_SPLIT.search(text)
    if not match:
        return text, "", ""
    return text[:match.start()], match.group(), text[match.end():]


def normalize_name(name: str) -> str:
    """Słownikowa normalizacja nazwy: literówki, CAPS LOCK, zapis jednostek. Liczby bez zmian."""
    words = [_fix_typo(w) for w in name.split()]
    text = " ".join(words)
    letters = [ch for ch in text if ch.isalpha()]
    if letters and sum(ch.isupper() for ch in letters) / len(letters) > 0.7:
        text = _from_caps(text)
    text = re.sub(r"(\d)\s*(kg|g)\b", lambda m: f"{m[1]} {m[2].lower()}", text, flags=re.IGNORECASE)
    for slowo, kanon in PISOWNIA.items():
        text = re.sub(rf"\b{re.escape(slowo)}\b", kanon, text, flags=re.IGNORECASE)
    return text


def _fix_typo(word: str) -> str:
    fixed = TYPOS.get(word.lower())
    if fixed is None:
        return word
    if word.isupper():
        return fixed.upper()
    if word[0].isupper():
        return fixed[0].upper() + fixed[1:]
    return fixed


def _from_caps(text: str) -> str:
    lower = text.lower()
    for brand in BRANDS:
        if lower.startswith(brand.lower() + " "):
            rest = lower[len(brand) + 1:]
            return f"{brand} {rest[:1].upper()}{rest[1:]}"
    return lower[:1].upper() + lower[1:]
