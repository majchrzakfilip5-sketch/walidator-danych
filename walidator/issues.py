"""Rekord problemu w danych i katalog typów problemów."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    CRITICAL = "krytyczny"      # blokuje import wiersza
    WARNING = "ostrzeżenie"     # import możliwy, warto sprawdzić
    FIXED = "poprawiono"        # pewna poprawka zastosowana automatycznie

    @property
    def label(self) -> str:
        return {"krytyczny": "Do poprawy (blokuje import)", "ostrzeżenie": "Ostrzeżenie",
                "poprawiono": "Poprawiono automatycznie"}[self.value]


C, W, F = Severity.CRITICAL, Severity.WARNING, Severity.FIXED

# kod -> (waga, opis dla człowieka)
ISSUE_TYPES: dict[str, tuple[Severity, str]] = {
    "BRAK_WARTOSCI": (C, "Brak wartości w polu wymaganym"),
    "EAN_FORMAT": (C, "Kod EAN nie ma 13 cyfr"),
    "EAN_SUMA_KONTROLNA": (C, "Kod EAN z literówką (nie zgadza się ostatnia cyfra)"),
    "DUPLIKAT_SKU": (C, "Ten sam SKU w innym wierszu"),
    "DUPLIKAT_EAN": (C, "Ten sam kod EAN w innym wierszu"),
    "KONFLIKT_KARTOTEKI": (C, "Dane wskazują różne produkty z kartoteki"),
    "WAGA_NIEROZPOZNANA": (C, "Nie można ustalić wagi"),
    "WAGA_NIEZGODNA_Z_NAZWA": (C, "Waga różni się od podanej w nazwie"),
    "ROZMIAR_NIEROZPOZNANY": (C, "Nie można ustalić rozmiaru"),
    "CENA_NIEROZPOZNANA": (C, "Nie można odczytać ceny"),
    "CENA_NIEDODATNIA": (C, "Cena musi być większa od zera"),
    "DATA_NIEROZPOZNANA": (C, "Nie można odczytać daty"),
    "DOSTAWA_W_PRZESZLOSCI": (C, "Termin dostawy już minął"),      # tryb delivery
    "ODLEGLA_DOSTAWA": (W, "Odległy termin dostawy"),              # tryb delivery
    "DATA_PRZETERMINOWANA": (C, "Termin ważności już minął"),      # tryb expiry
    "KROTKI_TERMIN": (W, "Krótki termin ważności"),                # tryb expiry
    "KOLOR_SPOZA_SLOWNIKA": (W, "Kolor spoza słownika"),
    "KATEGORIA_SPOZA_LISTY": (W, "Kategoria spoza listy"),
    "BRAK_CENY": (W, "Brak ceny w pliku i w cenniku"),
    "SPACJE": (F, "Usunięto zbędne spacje"),
    "FORMAT_EAN": (F, "Usunięto spacje i myślniki z EAN"),
    "FORMAT_WAGI": (F, "Waga przeliczona na gramy"),
    "FORMAT_ROZMIARU": (F, "Ujednolicono zapis rozmiaru"),
    "FORMAT_KOLORU": (F, "Ujednolicono nazwę koloru"),
    "FORMAT_CENY": (F, "Cena zapisana jako liczba"),
    "FORMAT_DATY": (F, "Data zapisana w formacie RRRR-MM-DD"),
    "FORMAT_KATEGORII": (F, "Ujednolicono zapis kategorii"),
    "CENA_Z_CENNIKA": (F, "Cena uzupełniona z cennika"),
    "EAN_Z_KARTOTEKI": (F, "Kod EAN poprawiony z kartoteki"),
    "SKU_Z_KARTOTEKI": (F, "SKU poprawiony z kartoteki"),
    "NAZWA_Z_KARTOTEKI": (F, "Nazwa z kartoteki"),
    "WAGA_Z_KARTOTEKI": (F, "Waga z kartoteki"),
    "ROZMIAR_Z_KARTOTEKI": (F, "Rozmiar z kartoteki"),
    "KOLOR_Z_KARTOTEKI": (F, "Kolor z kartoteki"),
    "KATEGORIA_Z_KARTOTEKI": (F, "Kategoria z kartoteki"),
    "DUPLIKAT_WIERSZA": (F, "Zduplikowany wiersz pominięty"),
}


@dataclass
class Issue:
    """Jeden problem w jednym polu jednego wiersza."""

    row: int                 # numer wiersza w pliku źródłowym (jak w Excelu)
    sku: str
    field: str               # pole wewnętrzne, np. "ean"
    code: str                # klucz z ISSUE_TYPES
    original: str            # wartość oryginalna, tak jak w pliku
    fix: str | None = None   # proponowana poprawka, tylko jeśli jest pewna
    detail: str = ""         # szczegóły dla człowieka

    def __post_init__(self) -> None:
        if self.code not in ISSUE_TYPES:
            raise ValueError(f"Nieznany kod problemu: {self.code}")

    @property
    def severity(self) -> Severity:
        return ISSUE_TYPES[self.code][0]

    @property
    def title(self) -> str:
        return ISSUE_TYPES[self.code][1]

    @property
    def is_critical(self) -> bool:
        return self.severity is Severity.CRITICAL
