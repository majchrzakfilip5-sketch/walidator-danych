"""Kartoteka produktów z ERP: źródło prawdy o produktach (wariantach), które sklep już ma.

Pozycja kartoteki to wariant: model w konkretnym rozmiarze i kolorze, z własnym SKU i EAN.
Wiersz z pliku jest dopasowywany do kartoteki trzema kluczami: SKU, kod EAN (tylko poprawny) i nazwa
(bez wielkości liter, polskich znaków i zbędnych spacji). Nazwa głosuje tylko wtedy, gdy wskazuje jeden
wariant: ten sam model w kilku rozmiarach ma tę samą nazwę, więc sama nazwa nie mówi, który to rozmiar.
Każdy klucz "głosuje" na produkt:
  - dwa klucze na ten sam produkt: dopasowanie, a trzeci klucz (np. SKU z literówką) poprawia kartoteka;
  - sam SKU: dopasowanie, bo SKU to klucz główny (EAN i nazwa mogą mieć literówki albo być puste);
  - sam EAN albo sama nazwa przy pustym SKU: dopasowanie i uzupełnienie SKU;
  - klucze wskazują różne produkty bez przewagi albo nieznany SKU przy cudzym EAN: konflikt.
    Tego nie da się rozstrzygnąć bez człowieka, więc wiersz idzie do weryfikacji z wyjaśnieniem.
Produkt, którego nie zna żaden klucz, jest nowy: jego kategorię zaproponuje AI.
"""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .config import RulesConfig
from .parsers import clean_text, header_key, parse_ean
from .pricelist import resolve

KEY_LABELS = {"sku": "SKU", "ean": "EAN", "name": "nazwa"}


# Ta sama wielkosc nosi w roznych branzach inna nazwe; rozmiar i kolor sa opcjonalne.
WAGA_KOLUMNY = ("Waga_g", "Gramatura_g")


class ProductMasterError(Exception):
    pass


@dataclass(frozen=True)
class MasterProduct:
    sku: str
    ean: str
    name: str
    weight_g: int
    size: str
    color: str
    category: str
    segment: str


@dataclass(frozen=True)
class Match:
    """Wynik dopasowania wiersza: produkt z kartoteki (albo None) i to, co się na niego złożyło."""

    product: MasterProduct | None
    keys: tuple[str, ...] = ()          # klucze, które wskazały ten produkt: "sku", "ean", "name"
    conflict: str = ""                  # opis sprzeczności, gdy nie da się wskazać produktu

    @property
    def is_new(self) -> bool:
        return self.product is None and not self.conflict


def name_key(name: str | None) -> str:
    return header_key(clean_text(name)) if name else ""


class ProductMaster:
    def __init__(self, products: list[MasterProduct]) -> None:
        self.products = products
        self.by_sku = {p.sku.casefold(): p for p in products}
        self.by_ean = {p.ean: p for p in products}
        by_name: dict[str, list[MasterProduct]] = {}
        for p in products:
            by_name.setdefault(name_key(p.name), []).append(p)
        # nazwa wskazuje produkt tylko wtedy, gdy ma jeden wariant
        self.by_name = {key: variants[0] for key, variants in by_name.items() if len(variants) == 1}

    def __len__(self) -> int:
        return len(self.products)

    def match(self, sku: str, ean: str | None, name: str) -> Match:
        votes: dict[str, MasterProduct] = {}
        if sku and (hit := self.by_sku.get(sku.casefold())):
            votes["sku"] = hit
        if ean and (hit := self.by_ean.get(ean)):
            votes["ean"] = hit
        if name and (hit := self.by_name.get(name_key(name))):
            votes["name"] = hit
        if not votes:
            return Match(None)

        counts = Counter(p.sku for p in votes.values())
        (best_sku, n), *rest = counts.most_common()
        best = next(p for p in votes.values() if p.sku == best_sku)
        keys = tuple(k for k, p in votes.items() if p.sku == best_sku)
        if n >= 2:
            return Match(best, keys)
        if rest:
            pointed = ", ".join(f"{KEY_LABELS[k]} wskazuje {p.sku} ({p.name})" for k, p in votes.items())
            return Match(None, conflict=f"dane wskazują różne produkty z kartoteki: {pointed}")
        if keys == ("sku",) or not sku:
            return Match(best, keys)
        return Match(None, conflict=f"SKU {sku} nie ma w kartotece, a {KEY_LABELS[keys[0]]} należy do produktu "
                                    f"{best.sku} ({best.name})")

    def examples(self, per_category: int = 3) -> list[tuple[str, str]]:
        """Kilka produktów z każdej kategorii: wzór dla AI, jak firma kategoryzuje swój asortyment."""
        seen: Counter = Counter()
        out, names = [], set()
        for p in self.products:
            if seen[p.category] < per_category and p.name not in names:   # wariant tego samego modelu raz
                seen[p.category] += 1
                names.add(p.name)
                out.append((p.name, p.category))
        return out


@lru_cache(maxsize=8)
def _read(path: str, mtime: float) -> ProductMaster:
    text = Path(path).read_text(encoding="utf-8-sig")
    rows = list(csv.DictReader(text.splitlines(), delimiter=";"))
    need = {"SKU", "EAN", "Nazwa", "Kategoria", "Segment"}
    kol_wagi = next((k for k in WAGA_KOLUMNY if rows and k in rows[0]), None)
    if not rows or not need <= set(rows[0]) or not kol_wagi:
        raise ProductMasterError(
            f"Kartoteka {Path(path).name} musi mieć kolumny: {';'.join(sorted(need))}"
            f" oraz kolumnę wagi ({' albo '.join(WAGA_KOLUMNY)})")
    products = []
    for n, row in enumerate(rows, start=2):
        ean = parse_ean(row["EAN"])
        if not ean.ok:
            raise ProductMasterError(f"Kartoteka {Path(path).name}, wiersz {n}: {ean.detail}")
        try:
            weight = int(row[kol_wagi])
        except ValueError as exc:
            raise ProductMasterError(f"Kartoteka {Path(path).name}, wiersz {n}: waga w gramach jako liczba") from exc
        products.append(MasterProduct(clean_text(row["SKU"]), ean.value, clean_text(row["Nazwa"]), weight,
                                      clean_text(row.get("Rozmiar", "")), clean_text(row.get("Kolor", "")),
                                      clean_text(row["Kategoria"]), clean_text(row["Segment"])))
    return ProductMaster(products)


def load_product_master(rules: RulesConfig) -> ProductMaster | None:
    """Kartoteka z pliku z konfiguracji albo None, gdy nie jest ustawiona."""
    if not rules.product_master:
        return None
    path = resolve(rules.product_master)
    if not path.exists():
        raise ProductMasterError(f"Nie znaleziono kartoteki produktów: {path}")
    return _read(str(path), path.stat().st_mtime)
