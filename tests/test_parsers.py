from datetime import date, datetime
from decimal import Decimal

import pytest

from walidator.parsers import clean_text, header_key, parse_date, parse_price, parse_weight, weight_in_name

DATE_FORMATS = ["%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y", "%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%Y/%m/%d"]


# --- waga -------------------------------------------------------------------

@pytest.mark.parametrize("value, grams", [
    ("450g", 450),
    ("450 g", 450),
    ("450 G", 450),
    ("0,45 kg", 450),
    ("0.45kg", 450),
    ("1kg", 1000),
    ("2,5kg", 2500),
    ("2,5 KG", 2500),
    ("500 gr", 500),
    ("45 dag", 450),
    ("4 x 2,5 kg", 10000),
    ("10 x 350 g", 3500),
    (" 750 g. ", 750),
])
def test_weight_variants(value, grams):
    assert parse_weight(value).value == grams


def test_canonical_weight_is_not_reported_as_fix():
    assert not parse_weight("450 g").reformatted
    assert not parse_weight("450g").reformatted
    assert parse_weight("0,45 kg").reformatted
    assert parse_weight("450 G").reformatted


@pytest.mark.parametrize("value, fragment", [
    ("450", "brak jednostki"),
    (450, "brak jednostki"),
    ("1 l", "objętość"),
    ("750 ml", "objętość"),
    ("ok. pół kilo", "nierozpoznany"),
    ("0,4555 kg", "nie jest liczbą całkowitą"),
    ("0 g", "większa od zera"),
])
def test_weight_errors(value, fragment):
    result = parse_weight(value)
    assert result.error == "WAGA_NIEROZPOZNANA"
    assert fragment in result.detail


def test_weight_without_unit_can_be_allowed_in_config():
    assert parse_weight("450", unit_if_missing="g").value == 450
    assert parse_weight(2.5, unit_if_missing="kg").value == 2500


@pytest.mark.parametrize("name, grams", [
    ("Hi-Tec Kettlebell żeliwny 12 kg", 12000),
    ("Hi-Tec Hantle żeliwne 2 x 5 kg", 10000),
    ("HI-TEC TALERZ OBCIĄŻENIOWY 1250 G", 1250),
    ("Model 41 wersja podstawowa męskie", None),
])
def test_weight_in_name(name, grams):
    assert weight_in_name(name) == grams


# --- cena -------------------------------------------------------------------

@pytest.mark.parametrize("value, expected", [
    ("12,99", "12.99"),
    ("12.99", "12.99"),
    ("12,99 zł", "12.99"),
    ("12.99 zł", "12.99"),
    ("12,99zł", "12.99"),
    ("12,99 PLN", "12.99"),
    ("1 299,00 zł", "1299.00"),
    ("1.299,00", "1299.00"),
    ("1,299.00", "1299.00"),
    (12.99, "12.99"),
    (7, "7.00"),
    ("8,5", "8.50"),
])
def test_price_variants(value, expected):
    assert parse_price(value).value == Decimal(expected)


def test_price_reformat_flag():
    assert not parse_price(12.99).reformatted
    assert not parse_price("12.99").reformatted
    assert parse_price("12,99 zł").reformatted


@pytest.mark.parametrize("value, code", [
    ("do ustalenia", "CENA_NIEROZPOZNANA"),
    ("1,299", "CENA_NIEROZPOZNANA"),      # tysiące czy grosze? nie zgadujemy
    ("12,999", "CENA_NIEROZPOZNANA"),
    (12.999, "CENA_NIEROZPOZNANA"),
    ("-8,99", "CENA_NIEDODATNIA"),
    ("0,00 zł", "CENA_NIEDODATNIA"),
])
def test_price_errors(value, code):
    assert parse_price(value).error == code


# --- data -------------------------------------------------------------------

@pytest.mark.parametrize("value", [
    "2026-03-15",
    "15.03.2026",
    "15/03/26",
    "15/03/2026",
    "15-03-2026",
    datetime(2026, 3, 15),
    date(2026, 3, 15),
    46096,                     # numer seryjny daty w Excelu
])
def test_date_variants(value):
    assert parse_date(value, DATE_FORMATS).value == date(2026, 3, 15)


def test_iso_and_excel_dates_are_not_reported_as_fix():
    assert not parse_date("2026-03-15", DATE_FORMATS).reformatted
    assert not parse_date(datetime(2026, 3, 15), DATE_FORMATS).reformatted
    assert parse_date("15.03.2026", DATE_FORMATS).reformatted


@pytest.mark.parametrize("value, fragment", [
    ("31.02.2027", "nie istnieje"),
    ("2027-13-01", "nie istnieje"),
    ("wkrótce", "akceptowane formaty"),
    (12.5, "nie jest datą"),
])
def test_date_errors(value, fragment):
    result = parse_date(value, DATE_FORMATS)
    assert result.error == "DATA_NIEROZPOZNANA"
    assert fragment in result.detail


# --- tekst ------------------------------------------------------------------

def test_clean_text_collapses_whitespace():
    assert clean_text("  Marka  Druga  Produkt   ") == "Marka Druga Produkt"
    assert clean_text(None) == ""
    assert clean_text(1001.0) == "1001"


def test_header_key_ignores_case_diacritics_and_separators():
    assert header_key("Data dostawy") == header_key("data_dostawy") == header_key(" DATA DOSTAWY ")
    assert header_key("Rozmiar (EU)") == header_key("rozmiar_eu")
