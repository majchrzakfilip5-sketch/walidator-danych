"""Warstwa 3: zapis wyników. CSV do importu, raporty Excel, import do SQLite."""

from __future__ import annotations

import csv
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.worksheet import Worksheet

from .config import CsvConfig, SourceConfig
from .issues import ISSUE_TYPES, Severity
from .models import Product, Status

SQL_DIR = Path(__file__).parent / "sql"
SEVERITY_ORDER = {Severity.CRITICAL: 0, Severity.WARNING: 1, Severity.FIXED: 2}

# --- CSV do importu ----------------------------------------------------------


def csv_value(value: object, cfg: CsvConfig) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return f"{value:.2f}".replace(".", cfg.decimal_separator)
    if isinstance(value, (date, datetime)):
        return value.strftime(cfg.date_format)
    return str(value)


def write_import_csv(products: list[Product], cfg: CsvConfig, path: Path) -> None:
    with path.open("w", encoding=cfg.encoding, newline="") as fh:
        writer = csv.writer(fh, delimiter=cfg.separator, quoting=csv.QUOTE_MINIMAL)
        writer.writerow([col.header for col in cfg.columns])
        for p in products:
            writer.writerow([csv_value(p.output_value(col.field), cfg) for col in cfg.columns])


# --- wspólne formatowanie arkuszy -------------------------------------------

HEADER_FILL = PatternFill("solid", fgColor="1F2937")
HEADER_FONT = Font(bold=True, color="FFFFFF")
INPUT_FILL = PatternFill("solid", fgColor="FFF8DB")
SEVERITY_FILL = {
    Severity.CRITICAL: PatternFill("solid", fgColor="FDE8E8"),
    Severity.WARNING: PatternFill("solid", fgColor="FFF4D6"),
    Severity.FIXED: PatternFill("solid", fgColor="E8F5EC"),
}
THIN = Side(style="thin", color="E5E7EB")
WRAP = Alignment(wrap_text=True, vertical="top")
TOP = Alignment(vertical="top")


def _table(ws: Worksheet, headers: list[tuple[str, int]], rows: list[list[object]], *,
           header_row: int = 1, text_columns: tuple[int, ...] = (), wrap_columns: tuple[int, ...] = (),
           freeze: bool = True) -> None:
    """Nagłówek, dane, szerokości kolumn, autofiltr i zamrożony nagłówek."""
    for col, (title, width) in enumerate(headers, start=1):
        cell = ws.cell(row=header_row, column=col, value=title)
        cell.fill, cell.font = HEADER_FILL, HEADER_FONT
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(col)].width = width
    ws.row_dimensions[header_row].height = 30
    for r, values in enumerate(rows, start=header_row + 1):
        for c, value in enumerate(values, start=1):
            cell = ws.cell(row=r, column=c, value=value)
            cell.alignment = WRAP if c in wrap_columns else TOP
            cell.border = Border(bottom=THIN)
            if c in text_columns:
                cell.number_format = "@"
    last = header_row + max(len(rows), 1)
    ws.auto_filter.ref = f"A{header_row}:{get_column_letter(len(headers))}{last}"
    if freeze:
        ws.freeze_panes = ws.cell(row=header_row + 1, column=1)


def _summary_block(ws: Worksheet, title: str, meta: list[tuple[str, object]]) -> int:
    ws["A1"] = title
    ws["A1"].font = Font(bold=True, size=14)
    for i, (label, value) in enumerate(meta, start=3):
        ws.cell(row=i, column=1, value=label).font = Font(color="6B7280")
        ws.cell(row=i, column=2, value=value).font = Font(bold=True)
    return 3 + len(meta)


# --- raport błędów -------------------------------------------------------------


def write_error_report(products: list[Product], source: SourceConfig, path: Path,
                       meta: list[tuple[str, object]]) -> int:
    wb = Workbook()
    ws = wb.active
    ws.title = "Raport błędów"
    by_row = {p.row: p for p in products}
    issues = sorted(
        (i for p in products for i in p.issues),
        key=lambda i: (i.row, SEVERITY_ORDER[i.severity], list(source.fields).index(i.field)),
    )
    rows = [[i.row, i.sku, source.label(i.field), i.title, i.severity.label,
             i.detail, i.original, i.fix or "", by_row[i.row].status.value] for i in issues]
    _table(ws, [("Wiersz", 9), ("SKU", 12), ("Pole", 15), ("Typ błędu", 38), ("Poziom", 24),
                ("Szczegóły", 58), ("Wartość oryginalna", 36), ("Proponowana poprawka", 28),
                ("Status wiersza", 24)],
           rows, text_columns=(2, 7, 8), wrap_columns=(6, 7))
    for r, issue in enumerate(issues, start=2):
        ws.cell(row=r, column=5).fill = SEVERITY_FILL[issue.severity]
        if issue.is_critical:
            ws.cell(row=r, column=4).font = Font(bold=True)
    if not issues:
        ws["A2"] = "Nie znaleziono problemów."

    summary = wb.create_sheet("Podsumowanie")
    start = _summary_block(summary, "Raport walidacji pliku", meta) + 1
    counts: dict[str, int] = {}
    for i in issues:
        counts[i.code] = counts.get(i.code, 0) + 1
    ordered = sorted(counts.items(), key=lambda kv: (SEVERITY_ORDER[ISSUE_TYPES[kv[0]][0]], -kv[1]))
    _table(summary, [("Typ problemu", 44), ("Poziom", 26), ("Liczba", 10)],
           [[ISSUE_TYPES[code][1], ISSUE_TYPES[code][0].label, n] for code, n in ordered],
           header_row=start, freeze=False)
    for r, (code, _) in enumerate(ordered, start=start + 1):
        summary.cell(row=r, column=2).fill = SEVERITY_FILL[ISSUE_TYPES[code][0]]
    wb.save(path)
    return len(issues)


# --- ręczna weryfikacja ---------------------------------------------------------

DECISIONS = ["Zatwierdź i importuj", "Popraw dane i importuj", "Zmień kategorię", "Nie importuj"]


def write_manual_review(products: list[Product], categories: list[str], path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Do weryfikacji"
    rows = []
    for p in products:
        c = p.classification
        rows.append([
            p.row, p.sku, p.ean, p.name, p.description,
            c.category if c else "", p.final_name if c else "", c.segment if c else "",
            c.confidence if c else None, c.reasoning if c else "",
            "; ".join(p.all_review_reasons), "", "", "",
        ])
    _table(ws, [("Wiersz", 9), ("SKU", 12), ("EAN", 16), ("Nazwa w pliku", 42), ("Opis", 44),
                ("Propozycja AI: kategoria", 28), ("Propozycja AI: nazwa", 42), ("Segment", 11),
                ("Pewność AI", 11), ("Uzasadnienie AI", 46), ("Powód weryfikacji", 40),
                ("Decyzja", 22), ("Kategoria po weryfikacji", 28), ("Uwagi", 30)],
           rows, text_columns=(2, 3), wrap_columns=(4, 5, 7, 10, 11))
    for r in range(2, len(rows) + 2):
        ws.cell(row=r, column=9).number_format = "0%"
        for col in (12, 13, 14):
            ws.cell(row=r, column=col).fill = INPUT_FILL
    for col in (12, 13, 14):
        ws.cell(row=1, column=col).fill = PatternFill("solid", fgColor="92400E")
    if rows:
        last = len(rows) + 1
        decision = DataValidation(type="list", formula1='"' + ",".join(DECISIONS) + '"', allow_blank=True)
        decision.add(f"L2:L{last}")
        # lista kategorii w ukrytym arkuszu: odporna na przecinki i długość formuły
        lists = wb.create_sheet("Listy")
        for i, cat in enumerate(categories, start=1):
            lists.cell(row=i, column=1, value=cat)
        lists.sheet_state = "hidden"
        category = DataValidation(type="list", formula1=f"=Listy!$A$1:$A${len(categories)}", allow_blank=True)
        category.add(f"M2:M{last}")
        ws.add_data_validation(decision)
        ws.add_data_validation(category)
    else:
        ws["A2"] = "Brak wierszy do ręcznej weryfikacji."
    wb.save(path)


# --- SQLite -----------------------------------------------------------------------


@dataclass
class SqlResult:
    query: str
    columns: list[str]
    rows: list[tuple]
    import_id: int
    rows_imported: int


def import_to_sqlite(products: list[Product], db_path: Path, source_name: str) -> SqlResult:
    query = (SQL_DIR / "produkty_per_kategoria.sql").read_text(encoding="utf-8").strip()
    with sqlite3.connect(db_path) as conn:
        conn.executescript((SQL_DIR / "schema.sql").read_text(encoding="utf-8"))
        cur = conn.execute(
            "INSERT INTO importy (plik_zrodlowy, data_importu, liczba_wierszy) VALUES (?, ?, ?)",
            (source_name, datetime.now().isoformat(timespec="seconds"), len(products)),
        )
        import_id = cur.lastrowid
        conn.executemany(
            """
            INSERT INTO produkty (sku, ean, nazwa, rozmiar, kolor, waga_g, cena_netto_pln, data_dostawy,
                                  kategoria, segment, import_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(sku) DO UPDATE SET
                ean = excluded.ean, nazwa = excluded.nazwa, rozmiar = excluded.rozmiar, kolor = excluded.kolor,
                waga_g = excluded.waga_g, cena_netto_pln = excluded.cena_netto_pln,
                data_dostawy = excluded.data_dostawy, kategoria = excluded.kategoria,
                segment = excluded.segment, import_id = excluded.import_id
            """,
            [(p.sku, p.ean, p.final_name, p.size, p.color, p.weight_g, str(p.price), p.delivery.isoformat(),
              p.category, p.segment, import_id) for p in products],
        )
        cur = conn.execute(query, {"import_id": import_id})
        columns = [d[0] for d in cur.description]
        rows = cur.fetchall()
    conn.close()
    return SqlResult(query, columns, rows, import_id, len(products))


def ready(products: list[Product]) -> list[Product]:
    return [p for p in products if p.status is Status.READY]


def for_review(products: list[Product]) -> list[Product]:
    return [p for p in products if p.status is Status.REVIEW]
