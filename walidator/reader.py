"""Odczyt pliku źródłowego (xlsx/csv) i mapowanie kolumn na pola wewnętrzne wg mapping.yaml."""

from __future__ import annotations

import csv
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from .config import SourceConfig
from .parsers import header_key, is_blank

SUPPORTED_EXTENSIONS = (".xlsx", ".xlsm", ".csv")


class MappingError(Exception):
    """Pliku nie da się zmapować: brakuje kolumn wymaganych albo są niejednoznaczne."""


@dataclass
class SourceRow:
    row_number: int                  # numer wiersza w pliku (jak w Excelu, nagłówek = 1)
    values: dict[str, object]        # pole wewnętrzne -> surowa wartość z komórki


@dataclass
class SourceTable:
    path: Path
    rows: list[SourceRow]
    column_map: dict[str, str]       # pole wewnętrzne -> nagłówek w pliku
    ignored_columns: list[str] = field(default_factory=list)
    skipped_empty_rows: int = 0


def map_columns(headers: list[object], source: SourceConfig) -> tuple[dict[str, int], list[str]]:
    """Zwraca {pole: indeks kolumny} oraz listę kolumn pominiętych (nieznanych)."""
    alias_to_field: dict[str, str] = {}
    for name, spec in source.fields.items():
        for alias in spec.headers:
            alias_to_field[header_key(alias)] = name

    mapping: dict[str, int] = {}
    ignored: list[str] = []
    for idx, header in enumerate(headers):
        if is_blank(header):
            continue
        target = alias_to_field.get(header_key(str(header)))
        if target is None:
            ignored.append(str(header).strip())
        elif target in mapping:
            first = str(headers[mapping[target]]).strip()
            raise MappingError(
                f"Kolumny '{first}' i '{str(header).strip()}' wskazują na to samo pole "
                f"'{source.label(target)}'. Zostaw jedną z nich albo popraw mapping.yaml."
            )
        else:
            mapping[target] = idx

    missing = [name for name in source.required_fields if name not in mapping]
    if missing:
        details = "; ".join(
            f"{source.label(name)} (szukano: {', '.join(source.fields[name].headers)})" for name in missing
        )
        raise MappingError(f"Brak wymaganych kolumn: {details}. Dodaj nagłówek do mapping.yaml.")
    return mapping, ignored


def _read_xlsx(path: Path, sheet: str | int | None) -> list[tuple]:
    try:
        wb = load_workbook(path, read_only=True, data_only=True)
    except (zipfile.BadZipFile, InvalidFileException, KeyError) as exc:
        raise MappingError(f"Plik {path.name} nie jest poprawnym arkuszem Excel (.xlsx). "
                           "Otwórz go w Excelu i zapisz ponownie jako .xlsx.") from exc
    try:
        if sheet is None:
            ws = wb.worksheets[0]
        elif isinstance(sheet, int):
            ws = wb.worksheets[sheet]
        else:
            ws = wb[sheet]
        return [tuple(row) for row in ws.iter_rows(values_only=True)]
    finally:
        wb.close()


class _SemicolonDialect(csv.excel):
    delimiter = ";"


def _read_csv(path: Path) -> list[tuple]:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "cp1250"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise MappingError("Nie udało się odczytać kodowania pliku CSV (obsługiwane: UTF-8, Windows-1250).")
    try:
        dialect: type[csv.Dialect] | csv.Dialect = csv.Sniffer().sniff(text[:4096], delimiters=";,\t")
    except csv.Error:
        dialect = _SemicolonDialect
    return [tuple(cell if cell != "" else None for cell in row) for row in csv.reader(text.splitlines(), dialect)]


def read_table(path: str | Path, source: SourceConfig) -> SourceTable:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise MappingError(f"Nieobsługiwany typ pliku '{suffix}'. Obsługiwane: {', '.join(SUPPORTED_EXTENSIONS)}.")
    raw_rows = _read_csv(path) if suffix == ".csv" else _read_xlsx(path, source.sheet)

    header_idx = next((i for i, row in enumerate(raw_rows) if any(not is_blank(c) for c in row)), None)
    if header_idx is None:
        raise MappingError("Plik jest pusty.")
    headers = list(raw_rows[header_idx])
    mapping, ignored = map_columns(headers, source)

    rows: list[SourceRow] = []
    skipped = 0
    for offset, raw in enumerate(raw_rows[header_idx + 1:], start=header_idx + 2):
        if all(is_blank(c) for c in raw):
            skipped += 1
            continue
        values = {name: (raw[idx] if idx < len(raw) else None) for name, idx in mapping.items()}
        for name in source.fields:
            values.setdefault(name, None)
        rows.append(SourceRow(row_number=offset, values=values))

    # puste wiersze na samym końcu arkusza to nie błąd w danych, tylko formatowanie Excela
    trailing = 0
    for raw in reversed(raw_rows[header_idx + 1:]):
        if all(is_blank(c) for c in raw):
            trailing += 1
        else:
            break
    column_map = {name: str(headers[idx]).strip() for name, idx in mapping.items()}
    return SourceTable(path, rows, column_map, ignored, skipped_empty_rows=skipped - trailing)
