"""Formatowanie liczb i odmiana rzeczowników po polsku (logi, raporty, strona)."""

from __future__ import annotations

from decimal import Decimal


def num(value: float | Decimal, digits: int = 1) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def percent(value: float) -> str:
    return f"{round(value * 100)}%"


def plural(n: int, one: str, few: str, many: str) -> str:
    """plural(1, 'wiersz', 'wiersze', 'wierszy') -> '1 wiersz'; 3 -> '3 wiersze'; 5 -> '5 wierszy'."""
    if n == 1:
        word = one
    elif n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        word = few
    else:
        word = many
    return f"{n} {word}"


def rows(n: int) -> str:
    return plural(n, "wiersz", "wiersze", "wierszy")


def in_rows(n: int) -> str:
    """Miejscownik: 'w 1 wierszu', 'w 3 wierszach'."""
    return f"w {n} wierszu" if n == 1 else f"w {n} wierszach"
