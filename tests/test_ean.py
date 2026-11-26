import pytest

from walidator.parsers import ean13_check_digit, is_valid_ean13, parse_ean


@pytest.mark.parametrize("code", ["5901234123457", "4006381333931", "9780306406157", "0012345678905"])
def test_valid_ean13(code):
    assert is_valid_ean13(code)
    assert parse_ean(code).value == code


def test_check_digit_known_value():
    # 5 9 0 1 2 3 4 1 2 3 4 5, wagi 1,3,1,3...: suma ważona 83 -> do 90 brakuje 7
    assert ean13_check_digit("590123412345") == 7


def test_check_digit_edge_cases():
    assert ean13_check_digit("001234567890") == 5
    assert ean13_check_digit("000000000000") == 0
    assert ean13_check_digit("200000000001") == 5


def test_wrong_check_digit():
    result = parse_ean("5901234123458")
    assert result.error == "EAN_SUMA_KONTROLNA"
    assert "wychodzi 7" in result.detail


@pytest.mark.parametrize("value, detail_fragment", [
    ("590123412345", "12 cyfr"),
    ("59012341234570", "14 cyfr"),
    ("59O1234123457", "znaki inne niż cyfry"),
    ("2,00597E+12", "zapis naukowy"),
])
def test_wrong_format(value, detail_fragment):
    result = parse_ean(value)
    assert result.error == "EAN_FORMAT"
    assert detail_fragment in result.detail


def test_spaces_and_dashes_are_removed():
    result = parse_ean("590 1234-123457")
    assert result.value == "5901234123457"
    assert result.reformatted


def test_numeric_cell_from_excel():
    assert parse_ean(5901234123457).value == "5901234123457"
    assert parse_ean(5901234123457.0).value == "5901234123457"
    assert not parse_ean(5901234123457).reformatted


def test_check_digit_requires_12_digits():
    with pytest.raises(ValueError):
        ean13_check_digit("12345")
