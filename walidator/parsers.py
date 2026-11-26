"""Deterministyczne parsery pól: EAN-13, waga, rozmiar, kolor, cena, data, tekst.

Każdy parser zwraca Parsed: wartość albo kod błędu z opisem. Flaga `reformatted`
mówi, że wartość trzeba było przekształcić (np. "0,45 kg" -> 450), co trafia
do raportu jako poprawka automatyczna. Parsery nie zgadują: gdy zapis jest
niejednoznaczny, zwracają błąd zamiast wartości.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Parsed(Generic[T]):
    value: T | None = None
    error: str | None = None       # kod z ISSUE_TYPES
    detail: str = ""
    reformatted: bool = False

    @property
    def ok(self) -> bool:
        return self.error is None


def fail(code: str, detail: str) -> Parsed:
    return Parsed(error=code, detail=detail)


# --- tekst ----------------------------------------------------------------

_WHITESPACE = re.compile(r"\s+")


def is_blank(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def clean_text(value: object) -> str:
    """Usuwa spacje z początku i końca, zamienia wielokrotne spacje (także twarde) na jedną."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return _WHITESPACE.sub(" ", str(value).replace(" ", " ")).strip()


def display(value: object) -> str:
    """Wartość oryginalna w czytelnej postaci do raportów."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat() if value.time() == datetime.min.time() else value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else repr(value)
    return str(value)


def fold(text: str) -> str:
    """Małe litery bez polskich znaków, np. 'Długość ramy' -> 'dlugosc ramy'."""
    text = text.lower().replace("ł", "l")
    return "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))


def header_key(text: str) -> str:
    """Klucz do porównywania nagłówków: bez wielkości liter, polskich znaków, spacji i podkreśleń."""
    return re.sub(r"[^a-z0-9]", "", fold(str(text)))


# --- EAN-13 ---------------------------------------------------------------

def ean13_check_digit(first12: str) -> int:
    """Cyfra kontrolna EAN-13: wagi 1,3,1,3... od lewej, dopełnienie sumy do wielokrotności 10."""
    if len(first12) != 12 or not first12.isdigit():
        raise ValueError("oczekiwano 12 cyfr")
    total = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(first12))
    return (10 - total % 10) % 10


def is_valid_ean13(code: str) -> bool:
    return len(code) == 13 and code.isdigit() and ean13_check_digit(code[:12]) == int(code[12])


def parse_ean(value: object) -> Parsed[str]:
    if isinstance(value, bool):
        return fail("EAN_FORMAT", "wartość logiczna zamiast kodu")
    if isinstance(value, float):
        if not value.is_integer():
            return fail("EAN_FORMAT", "liczba z częścią dziesiętną zamiast kodu")
        value = int(value)
    if isinstance(value, int):
        raw = str(value)
        compact = raw
    else:
        raw = str(value).strip()
        compact = re.sub(r"[\s\- ]", "", raw)
    if re.fullmatch(r"\d+([.,]\d+)?E\+?\d+", compact, flags=re.IGNORECASE):
        return fail("EAN_FORMAT", "zapis naukowy z Excela (np. 2,01E+12), końcowe cyfry zostały utracone")
    if not compact.isdigit():
        return fail("EAN_FORMAT", "zawiera znaki inne niż cyfry")
    if len(compact) != 13:
        return fail("EAN_FORMAT", f"{len(compact)} cyfr zamiast 13")
    expected = ean13_check_digit(compact[:12])
    if expected != int(compact[12]):
        return fail("EAN_SUMA_KONTROLNA",
                    f"ostatnia cyfra to {compact[12]}, a z pierwszych 12 cyfr wychodzi {expected}: w kodzie jest literówka")
    return Parsed(compact, reformatted=compact != raw)


# --- waga ----------------------------------------------------------------

_UNIT_GRAMS = {"g": Decimal(1), "gr": Decimal(1), "dag": Decimal(10), "kg": Decimal(1000)}
_WEIGHT = re.compile(
    r"^(?:(?P<count>\d+)\s*[x×*]\s*)?(?P<num>\d+(?:[.,]\d+)?)\s*(?P<unit>kg|dag|gr|g)\.?$", re.IGNORECASE
)
_VOLUME = re.compile(r"^\d+(?:[.,]\d+)?\s*(l|ml|litr\w*)\.?$", re.IGNORECASE)
_CANONICAL_WEIGHT = re.compile(r"^\d+ ?g$")


def _grams(count: str | None, number: str, unit: str) -> Decimal:
    total = Decimal(number.replace(",", ".")) * _UNIT_GRAMS[unit.lower()]
    return total * int(count) if count else total


def parse_weight(value: object, unit_if_missing: str | None = None) -> Parsed[int]:
    """'450g', '0,45 kg', '450 G', '2,5kg', '4 x 2,5 kg' -> liczba całkowita gramów."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        text = format(Decimal(str(value)).normalize(), "f")
    else:
        text = clean_text(value)
    if _VOLUME.match(text):
        return fail("WAGA_NIEROZPOZNANA", "podano objętość (l/ml), brak przelicznika na gramy")
    if re.fullmatch(r"\d+(?:[.,]\d+)?", text):
        if unit_if_missing is None:
            return fail("WAGA_NIEROZPOZNANA", "brak jednostki (g lub kg)")
        text = f"{text} {unit_if_missing}"
    match = _WEIGHT.match(text)
    if not match:
        return fail("WAGA_NIEROZPOZNANA", "nierozpoznany zapis wagi")
    grams = _grams(match["count"], match["num"], match["unit"])
    if grams <= 0:
        return fail("WAGA_NIEROZPOZNANA", "waga musi być większa od zera")
    if grams != grams.to_integral_value():
        return fail("WAGA_NIEROZPOZNANA", f"wynik {grams.normalize()} g nie jest liczbą całkowitą")
    return Parsed(int(grams), reformatted=not _CANONICAL_WEIGHT.match(text))


_WEIGHT_IN_TEXT = re.compile(
    r"(?:(?P<count>\d+)\s*[x×]\s*)?(?P<num>\d+(?:[.,]\d+)?)\s*(?P<unit>kg|dag|gr|g)\b", re.IGNORECASE
)


def weight_in_name(name: str) -> int | None:
    """Waga zapisana w nazwie produktu (ostatnie wystąpienie), np. '... Hantle 2 x 5 kg' -> 10000."""
    matches = list(_WEIGHT_IN_TEXT.finditer(name))
    if not matches:
        return None
    m = matches[-1]
    grams = _grams(m["count"], m["num"], m["unit"])
    return int(grams) if grams == grams.to_integral_value() else None


# --- cena -----------------------------------------------------------------

_CURRENCY = re.compile(r"(zł|zl|pln)\.?", re.IGNORECASE)


def parse_price(value: object) -> Parsed[Decimal]:
    """'12,99', '12.99 zł', '12,99zł', 12.99 -> Decimal('12.99'). Niejednoznaczne zapisy to błąd."""
    if isinstance(value, bool):
        return fail("CENA_NIEROZPOZNANA", "wartość logiczna zamiast ceny")
    if isinstance(value, (int, float)):
        amount = Decimal(str(value))
        reformatted = False
    else:
        raw = clean_text(value)
        text = _CURRENCY.sub("", raw).replace(" ", "")
        if "," in text and "." in text:
            decimal_sep = "," if text.rfind(",") > text.rfind(".") else "."
            thousands = "." if decimal_sep == "," else ","
            text = text.replace(thousands, "").replace(decimal_sep, ".")
        elif text.count(",") == 1:
            if re.search(r",\d{3}$", text):
                return fail("CENA_NIEROZPOZNANA", "niejednoznaczny zapis: przecinek może oddzielać tysiące")
            text = text.replace(",", ".")
        elif re.search(r"^\-?\d+\.\d{3}$", text):
            return fail("CENA_NIEROZPOZNANA", "niejednoznaczny zapis: kropka może oddzielać tysiące")
        if not re.fullmatch(r"-?\d+(\.\d+)?", text):
            return fail("CENA_NIEROZPOZNANA", "to nie jest kwota")
        amount = Decimal(text)
        reformatted = raw != text
    try:
        if amount != amount.quantize(Decimal("0.01")):
            return fail("CENA_NIEROZPOZNANA", "więcej niż 2 miejsca po przecinku")
    except InvalidOperation:
        return fail("CENA_NIEROZPOZNANA", "to nie jest kwota")
    if amount <= 0:
        return fail("CENA_NIEDODATNIA", f"podano {str(amount).replace('.', ',')} zł")
    return Parsed(amount.quantize(Decimal("0.01")), reformatted=reformatted)


# --- data -----------------------------------------------------------------

_EXCEL_EPOCH = date(1899, 12, 30)
_ISO = "%Y-%m-%d"
_FORMAT_LABELS = {"%Y": "RRRR", "%y": "RR", "%m": "MM", "%d": "DD"}


def format_label(fmt: str) -> str:
    for code, label in _FORMAT_LABELS.items():
        fmt = fmt.replace(code, label)
    return fmt


def parse_date(value: object, formats: list[str]) -> Parsed[date]:
    """Data z komórki Excela, numeru seryjnego Excela albo tekstu w jednym z podanych formatów."""
    if isinstance(value, datetime):
        return Parsed(value.date())
    if isinstance(value, date):
        return Parsed(value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if 20000 <= value <= 80000 and float(value).is_integer():
            return Parsed(_EXCEL_EPOCH + timedelta(days=int(value)), reformatted=True)
        return fail("DATA_NIEROZPOZNANA", "liczba, która nie jest datą")
    text = clean_text(value)
    for fmt in formats:
        try:
            parsed = datetime.strptime(text, fmt).date()
        except ValueError:
            continue
        return Parsed(parsed, reformatted=fmt != _ISO or text != parsed.isoformat())
    if re.fullmatch(r"\d{1,4}[./-]\d{1,2}[./-]\d{1,4}", text):
        return fail("DATA_NIEROZPOZNANA", "taka data nie istnieje w kalendarzu albo ma nieobsługiwany układ")
    accepted = ", ".join(format_label(f) for f in formats)
    return fail("DATA_NIEROZPOZNANA", f"akceptowane formaty: {accepted}")


# --- rozmiar --------------------------------------------------------------
# Kanoniczny zapis: litery (XS-3XL), rozmiar liczbowy z kropką (42, 42.5, 42 2/3) albo "uniwersalny".

_LETTER_SIZES = {"XXS": "XXS", "XS": "XS", "S": "S", "M": "M", "L": "L", "XL": "XL", "XXL": "XXL", "2XL": "XXL",
                 "XXXL": "3XL", "3XL": "3XL", "4XL": "4XL"}
_ONE_SIZE = {"ONESIZE", "OS", "UNI", "UNIWERSALNY", "UNIWERSALNA", "U"}
_NUMERIC_SIZE = re.compile(r"^(\d{1,3})(?:[.,](\d))?(?:\s+([12])/3)?$")


def parse_size(value: object) -> Parsed[str]:
    """"EU 42" -> "42", "42,5" -> "42.5", "m" -> "M", "XXXL" -> "3XL", "one size" -> "uniwersalny".
    Zapis, który może oznaczać dwa rozmiary ("XL/XXL", "43-44"), to błąd, a nie zgadywanie."""
    raw = clean_text(value)
    if not raw:
        return fail("BRAK_WARTOSCI", "pusty rozmiar")
    text = re.sub(r"^(?:EU|EUR|ROZM\.?|ROZMIAR)\s*", "", raw.upper()).strip()
    if re.search(r"[/\-]|\bLUB\b", text.replace(" 1/3", "").replace(" 2/3", "")):
        return fail("ROZMIAR_NIEROZPOZNANY", f"'{raw}' może oznaczać dwa rozmiary")
    if text.replace(" ", "") in _ONE_SIZE:
        size = "uniwersalny"
    elif text in _LETTER_SIZES:
        size = _LETTER_SIZES[text]
    elif match := _NUMERIC_SIZE.match(text):
        whole, decimal, third = match.groups()
        if not 1 <= int(whole) <= 60:
            return fail("ROZMIAR_NIEROZPOZNANY", f"rozmiar {raw} poza zakresem")
        size = whole + (f".{decimal}" if decimal and decimal != "0" else "") + (f" {third}/3" if third else "")
    else:
        return fail("ROZMIAR_NIEROZPOZNANY", f"nieznany zapis rozmiaru: '{raw}'")
    return Parsed(size, reformatted=size != display(value))


# --- kolor ----------------------------------------------------------------
# Kanoniczny zapis: polska nazwa w rodzaju męskim; dwa kolory rozdzielone ukośnikiem ("czarny/biały").

COLORS = {
    "czarny": ["czarny", "czarna", "czarne", "black", "blk", "bk"],
    "biały": ["bialy", "biala", "biale", "white", "wht", "wh"],
    "szary": ["szary", "szara", "szare", "grey", "gray", "gry"],
    "granatowy": ["granatowy", "granatowa", "granatowe", "navy", "nvy"],
    "niebieski": ["niebieski", "niebieska", "niebieskie", "blue", "blu"],
    "czerwony": ["czerwony", "czerwona", "czerwone", "red"],
    "zielony": ["zielony", "zielona", "zielone", "green", "grn"],
    "żółty": ["zolty", "zolta", "zolte", "yellow", "ylw"],
    "pomarańczowy": ["pomaranczowy", "pomaranczowa", "pomaranczowe", "orange", "org"],
    "różowy": ["rozowy", "rozowa", "rozowe", "pink"],
    "fioletowy": ["fioletowy", "fioletowa", "fioletowe", "purple", "violet"],
    "beżowy": ["bezowy", "bezowa", "bezowe", "beige"],
    "srebrny": ["srebrny", "srebrna", "srebrne", "silver"],
    "wielokolorowy": ["wielokolorowy", "wielokolorowa", "wielokolorowe", "multicolor", "multi"],
}
_COLOR_WORDS = {word: name for name, words in COLORS.items() for word in words}


def parse_color(value: object) -> Parsed[str]:
    """"Black" / "blk" / "czarne" -> "czarny", "black/white" -> "czarny/biały".
    Kolor spoza słownika zostaje jak w pliku (po usunięciu spacji) z kodem ostrzeżenia."""
    raw = clean_text(value)
    if not raw:
        return fail("BRAK_WARTOSCI", "pusty kolor")
    parts = [p for p in re.split(r"\s*[/,+&]\s*|\s+i\s+", fold(raw)) if p]
    names = [_COLOR_WORDS.get(p) for p in parts]
    if not parts or None in names:
        return Parsed(raw, error="KOLOR_SPOZA_SLOWNIKA", detail=f"'{raw}' nie ma w słowniku kolorów")
    color = "/".join(dict.fromkeys(names))
    return Parsed(color, reformatted=color != display(value))
