"""Model wiersza produktu przechodzącego przez trzy warstwy: reguły -> AI -> wyjście."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum

from .issues import Issue


class Status(str, Enum):
    """Wiersz idzie do importu albo do człowieka; błąd w danych to powód weryfikacji, nie ślepa uliczka.
    Identyczna kopia innego wiersza jest pomijana: w imporcie byłaby tym samym produktem drugi raz."""

    READY = "gotowy do importu"
    REVIEW = "do ręcznej weryfikacji"
    SKIPPED = "pominięty duplikat"


@dataclass(frozen=True)
class Classification:
    """Wynik warstwy AI (albo trybu mock) dla jednego wiersza. Dotyczy tylko pól tekstowych."""

    category: str
    normalized_name: str
    segment: str
    confidence: float
    reasoning: str


@dataclass
class Product:
    row: int
    sku: str
    ean: str | None
    name: str                              # nazwa po usunięciu zbędnych spacji (warstwa reguł)
    weight_g: int | None
    size: str | None                       # rozmiar w zapisie kanonicznym, np. "42.5", "M", "uniwersalny"
    color: str | None                      # kolor w zapisie kanonicznym, np. "czarny/biały"
    price: Decimal | None
    delivery: date | None                  # planowana data dostawy towaru
    source_category: str | None            # kategoria z pliku, jeśli jest na liście
    description: str
    original: dict[str, str]               # pole -> wartość oryginalna z pliku
    issues: list[Issue] = field(default_factory=list)
    classification: Classification | None = None
    review_reasons: list[str] = field(default_factory=list)
    ai_name_rejected: bool = False         # AI zmieniło liczby w nazwie: nazwa z AI odrzucona
    master_category: str | None = None     # produkt rozpoznany w kartotece: kategoria i segment stamtąd
    master_segment: str | None = None
    master_keys: tuple[str, ...] = ()      # klucze, po których rozpoznano produkt: "sku", "ean", "name"
    duplicate_of: int | None = None        # numer wiersza, którego ten wiersz jest identyczną kopią

    @property
    def in_master(self) -> bool:
        return self.master_category is not None

    @property
    def has_critical(self) -> bool:
        return any(i.is_critical for i in self.issues)

    @property
    def status(self) -> Status:
        if self.duplicate_of is not None:
            return Status.SKIPPED
        if self.has_critical or self.review_reasons or (self.classification is None and not self.in_master):
            return Status.REVIEW
        return Status.READY

    @property
    def all_review_reasons(self) -> list[str]:
        """Co człowiek ma zrobić z wierszem: najpierw błędy w danych (z poprawką do wpisania), potem uwagi AI."""
        data = [f"{i.title}: {i.detail}" if i.detail else i.title for i in self.issues if i.is_critical]
        return data + list(self.review_reasons)

    @property
    def final_name(self) -> str:
        if self.classification and not self.ai_name_rejected:
            return self.classification.normalized_name
        return self.name

    @property
    def category(self) -> str | None:
        if self.classification:
            return self.classification.category
        return self.master_category or self.source_category

    @property
    def segment(self) -> str | None:
        return self.classification.segment if self.classification else self.master_segment

    def identity(self) -> tuple:
        """Klucz do wykrywania wierszy identycznych po normalizacji."""
        return (self.sku.casefold(), self.ean, self.name, self.weight_g, self.size, self.color, self.price,
                self.delivery, self.source_category, self.description)

    def output_value(self, field_name: str) -> object:
        return {
            "sku": self.sku,
            "ean": self.ean,
            "name": self.final_name,
            "weight_g": self.weight_g,
            "size": self.size,
            "color": self.color,
            "price": self.price,
            "delivery": self.delivery,
            "category": self.category,
            "segment": self.segment,
        }[field_name]
