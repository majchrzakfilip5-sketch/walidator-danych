"""Cennik: ceny netto produktów według SKU, używane, gdy w pliku źródłowym brakuje ceny."""

from __future__ import annotations

import csv
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from .config import PROJECT_ROOT, RulesConfig
from .parsers import clean_text, parse_price


class PriceListError(Exception):
    pass


def resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else PROJECT_ROOT / p


@lru_cache(maxsize=8)
def _read(path: str, mtime: float) -> dict[str, Decimal]:
    text = Path(path).read_text(encoding="utf-8-sig")
    rows = list(csv.reader(text.splitlines(), delimiter=";"))
    if not rows or len(rows[0]) < 2:
        raise PriceListError(f"Cennik {Path(path).name} musi mieć dwie kolumny: SKU;Cena_netto_PLN")
    prices: dict[str, Decimal] = {}
    for n, row in enumerate(rows[1:], start=2):
        if len(row) < 2 or not clean_text(row[0]):
            continue
        result = parse_price(row[1])
        if not result.ok:
            raise PriceListError(f"Cennik {Path(path).name}, wiersz {n}: {result.detail}")
        prices[clean_text(row[0]).casefold()] = result.value
    return prices


def load_price_list(rules: RulesConfig) -> dict[str, Decimal] | None:
    """Słownik SKU (bez wielkości liter) -> cena netto, albo None, gdy cennik nie jest ustawiony."""
    if not rules.price_list:
        return None
    path = resolve(rules.price_list)
    if not path.exists():
        raise PriceListError(f"Nie znaleziono cennika: {path}")
    return _read(str(path), path.stat().st_mtime)
