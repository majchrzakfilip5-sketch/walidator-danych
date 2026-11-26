"""Przebieg: [1/3] reguły -> [2/3] AI -> [3/3] zapis wyników. Zbiera logi i podsumowanie."""

from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from . import fmt
from .ai import Classifier, TextItem, Usage, make_classifier, numbers_preserved
from .config import PROJECT_ROOT, AppConfig, LLMSettings
from .issues import Severity
from .master import load_product_master
from .models import Product, Status
from .outputs import (
    SqlResult,
    for_review,
    import_to_sqlite,
    ready,
    write_error_report,
    write_import_csv,
    write_manual_review,
)
from .parsers import header_key
from .reader import SourceTable, read_table
from .rules import validate_table


@dataclass(frozen=True)
class LogEntry:
    t: float        # sekundy od startu przebiegu
    kind: str       # step | info | ok | warn | error | review | done
    text: str


class RunLog:
    def __init__(self, sink: Callable[[LogEntry], None] | None = None) -> None:
        self.entries: list[LogEntry] = []
        self._start = time.perf_counter()
        self._sink = sink

    def __call__(self, text: str, kind: str = "info") -> None:
        entry = LogEntry(round(time.perf_counter() - self._start, 3), kind, text)
        self.entries.append(entry)
        if self._sink:
            self._sink(entry)

    @property
    def elapsed(self) -> float:
        return time.perf_counter() - self._start


@dataclass(frozen=True)
class Summary:
    rows_in: int
    ready: int
    review: int
    review_data: int        # wiersze w weryfikacji z powodu błędu w danych
    skipped: int            # identyczne kopie innych wierszy, pominięte w imporcie
    in_master: int          # wiersze rozpoznane w kartotece produktów
    fixed_rows: int         # wiersze z co najmniej jedną poprawką automatyczną
    critical_issues: int
    warnings: int
    fixes: int
    sent_to_ai: int


@dataclass
class RunResult:
    source: Path
    started_at: datetime
    duration_s: float
    mode: str
    model: str
    table: SourceTable
    products: list[Product]
    summary: Summary
    usage: Usage
    cost_usd: float
    cost_pln: float
    outputs: dict[str, Path]
    sql: SqlResult
    log: list[LogEntry] = field(default_factory=list)


def summarize(products: list[Product], sent_to_ai: int) -> Summary:
    statuses = Counter(p.status for p in products)
    severities = Counter(i.severity for p in products for i in p.issues)
    return Summary(
        rows_in=len(products),
        ready=statuses[Status.READY],
        review=statuses[Status.REVIEW],
        review_data=sum(p.has_critical and p.status is Status.REVIEW for p in products),
        skipped=statuses[Status.SKIPPED],
        in_master=sum(p.in_master for p in products),
        fixed_rows=sum(any(i.severity is Severity.FIXED for i in p.issues) for p in products),
        critical_issues=severities[Severity.CRITICAL],
        warnings=severities[Severity.WARNING],
        fixes=sum(i.severity is Severity.FIXED and i.code != "DUPLIKAT_WIERSZA" for p in products for i in p.issues),
        sent_to_ai=sent_to_ai,
    )


def run_pipeline(path: str | Path, config: AppConfig, settings: LLMSettings, *, force_mock: bool = False,
                 output_dir: Path | None = None, sink: Callable[[LogEntry], None] | None = None,
                 classifier: Classifier | None = None) -> RunResult:
    path = Path(path)
    started_at = datetime.now()
    log = RunLog(sink)
    out_dir = output_dir or (PROJECT_ROOT / config.output.dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    log(f"Plik: {path.name}", "info")

    # [1/3] reguły -------------------------------------------------------------
    log("[1/3] Reguły walidacji...", "step")
    table = read_table(path, config.source)
    products = validate_table(table, config)
    master = load_product_master(config.rules)
    _log_reading(table, config, log)
    _log_master(products, master is not None, log)
    _log_rules(products, log)

    # [2/3] AI: każdy nowy produkt (spoza kartoteki), także z błędem w innym polu: AI ocenia tylko nazwę
    # i opis, więc np. brak terminu dostawy nie przeszkadza w kategorii, a człowiek ma potem mniej do zrobienia
    candidates = [p for p in products if not p.in_master and p.duplicate_of is None and p.name]
    classifier = classifier or make_classifier(config, settings, force_mock,
                                               examples=master.examples() if master else None)
    batches = -(-len(candidates) // config.ai.batch_size) if candidates else 0
    engine = (fmt.plural(batches, "partia", "partie", "partii") if classifier.mode == "ai"
              else "tryb mock: słownik reguł")
    if candidates:
        what = (fmt.plural(len(candidates), "nowy produkt", "nowe produkty", "nowych produktów") if master
                else fmt.rows(len(candidates)))
        log(f"[2/3] AI: kategoryzacja {what} ({engine})...", "step")
    else:
        log("[2/3] AI: brak nowych produktów, kategorie pochodzą z kartoteki", "step")
    items = [TextItem(p.row, p.name, p.description) for p in candidates]
    run = classifier.classify(items, lambda text: log(text, "info"))
    apply_classifications(candidates, run.results, run.failures, config.ai.confidence_threshold)
    if candidates:
        _log_ai(candidates, config.ai.confidence_threshold, log)

    # [3/3] zapis --------------------------------------------------------------
    log("[3/3] Zapis wyników...", "step")
    summary = summarize(products, len(candidates))
    cost_usd = run.usage.cost_usd(config.ai.pricing)
    mode_label = "AI" if classifier.mode == "ai" else "mock (bez AI)"
    meta = [
        ("Plik źródłowy", path.name),
        ("Data przebiegu", started_at.strftime("%Y-%m-%d %H:%M")),
        ("Tryb kategoryzacji", mode_label),
        ("Wierszy na wejściu", summary.rows_in),
        ("Gotowe do importu", summary.ready),
        ("Do ręcznej weryfikacji", summary.review),
        ("w tym z błędem w danych", summary.review_data),
        ("Pominięte duplikaty", summary.skipped),
        ("Rozpoznane w kartotece", summary.in_master),
    ]
    outputs = {
        "csv": out_dir / config.output.import_csv.file,
        "errors": out_dir / config.output.error_report,
        "review": out_dir / config.output.manual_review,
        "sqlite": out_dir / config.output.sqlite,
    }
    ready_rows, review_rows = ready(products), for_review(products)
    write_import_csv(ready_rows, config.output.import_csv, outputs["csv"])
    log(f"{outputs['csv'].name}: {fmt.rows(len(ready_rows))} gotowych do importu", "ok")
    issues_count = write_error_report(products, config.source, outputs["errors"], meta)
    log(f"{outputs['errors'].name}: {fmt.plural(issues_count, 'pozycja', 'pozycje', 'pozycji')}", "ok")
    write_manual_review(review_rows, config.ai.categories, outputs["review"])
    log(f"{outputs['review'].name}: {fmt.rows(len(review_rows))} do weryfikacji", "ok")
    sql = import_to_sqlite(ready_rows, outputs["sqlite"], path.name)
    log(f"{outputs['sqlite'].name}: zaimportowano "
        f"{fmt.plural(sql.rows_imported, 'produkt', 'produkty', 'produktów')} (import #{sql.import_id})", "ok")

    duration = log.elapsed
    cost_text = f", koszt AI ≈ {fmt.num(cost_usd, 4)} USD" if classifier.mode == "ai" else ", bez kosztów API"
    log(f"Gotowe w {fmt.num(duration)} s{cost_text}", "done")
    return RunResult(
        source=path, started_at=started_at, duration_s=duration, mode=classifier.mode,
        model=classifier.model_name, table=table, products=products, summary=summary, usage=run.usage,
        cost_usd=cost_usd, cost_pln=cost_usd * config.ai.usd_to_pln, outputs=outputs, sql=sql,
        log=list(log.entries),
    )


def apply_classifications(products: list[Product], results: dict, failures: dict, threshold: float) -> None:
    """Wynik AI przyjmujemy tylko wtedy, gdy przejdzie kontrole w kodzie. W innym razie: weryfikacja."""
    for p in products:
        if p.row in failures or p.row not in results:
            p.review_reasons.append(failures.get(p.row, "brak odpowiedzi AI"))
            continue
        c = results[p.row]
        p.classification = c
        if not numbers_preserved(p.name, c.normalized_name):
            p.ai_name_rejected = True
            p.review_reasons.append("AI zmieniło liczby w nazwie, propozycję nazwy odrzucono")
        if c.confidence < threshold:
            p.review_reasons.append(f"niska pewność AI ({fmt.percent(c.confidence)}, próg {fmt.percent(threshold)})")
        if p.source_category and p.source_category != c.category:
            p.review_reasons.append(f"kategoria w pliku ({p.source_category}) różni się od propozycji AI ({c.category})")


# --- logi --------------------------------------------------------------------


def _log_reading(table: SourceTable, config: AppConfig, log: RunLog) -> None:
    log(f"wczytano {fmt.rows(len(table.rows))}, "
        f"{fmt.plural(len(table.column_map), 'kolumna', 'kolumny', 'kolumn')} rozpoznanych", "info")
    renamed = [f"{header} → {config.source.label(name)}" for name, header in table.column_map.items()
               if header_key(header) != header_key(config.source.fields[name].headers[0])]
    if renamed:
        log(f"mapowanie nagłówków: {', '.join(renamed)}", "info")
    if table.ignored_columns:
        log(f"pominięto kolumny spoza mapowania: {', '.join(table.ignored_columns)}", "info")
    if table.skipped_empty_rows:
        log(f"pominięto {fmt.plural(table.skipped_empty_rows, 'pusty wiersz', 'puste wiersze', 'pustych wierszy')}", "info")


FIELD_NAMES = {"delivery": "daty", "weight": "wagi", "size": "rozmiary", "color": "kolory", "price": "ceny",
               "name": "nazwy", "sku": "SKU", "ean": "EAN", "category": "kategorie"}
FROM_MASTER = {"EAN_Z_KARTOTEKI", "SKU_Z_KARTOTEKI", "NAZWA_Z_KARTOTEKI", "WAGA_Z_KARTOTEKI",
               "ROZMIAR_Z_KARTOTEKI", "KOLOR_Z_KARTOTEKI", "KATEGORIA_Z_KARTOTEKI"}


def _log_master(products: list[Product], enabled: bool, log: RunLog) -> None:
    if not enabled:
        return
    known = sum(p.in_master for p in products)
    new = sum(not p.in_master and p.duplicate_of is None for p in products)
    log(f"kartoteka: rozpoznano {known} z {fmt.plural(len(products), 'produktu', 'produktów', 'produktów')}, "
        f"{fmt.plural(new, 'nowy', 'nowe', 'nowych')}", "info")


def _log_rules(products: list[Product], log: RunLog) -> None:
    fixes = [i for p in products for i in p.issues if i.severity is Severity.FIXED and i.code != "DUPLIKAT_WIERSZA"]
    warnings = [i for p in products for i in p.issues if i.severity is Severity.WARNING]
    critical = [i for p in products for i in p.issues if i.is_critical]
    skipped = [p for p in products if p.duplicate_of is not None]
    if fixes:
        kinds = Counter(i.field for i in fixes)
        detail = ", ".join(f"{FIELD_NAMES.get(f, f)} {n}" for f, n in kinds.most_common())
        log(f"{fmt.plural(len(fixes), 'poprawka automatyczna', 'poprawki automatyczne', 'poprawek automatycznych')}"
            f" ({detail})", "ok")
        from_master = [i for i in fixes if i.code in FROM_MASTER or i.code == "CENA_Z_CENNIKA"]
        if from_master:
            log(f"w tym {len(from_master)} z kartoteki i cennika (dane z ERP)", "info")
    if skipped:
        rows = ", ".join(f"{p.row} = {p.duplicate_of}" for p in skipped)
        log(f"pominięto {fmt.plural(len(skipped), 'zduplikowany wiersz', 'zduplikowane wiersze', 'zduplikowanych wierszy')}"
            f" (wiersz {rows})", "ok")
    if warnings:
        log(f"{fmt.plural(len(warnings), 'ostrzeżenie', 'ostrzeżenia', 'ostrzeżeń')}"
            f" ({', '.join(sorted({i.title.lower() for i in warnings}))})", "warn")
    with_errors = sum(p.has_critical for p in products)
    if critical:
        log(f"{fmt.plural(len(critical), 'błąd w danych', 'błędy w danych', 'błędów w danych')} "
            f"{fmt.in_rows(with_errors)}: te wiersze idą do ręcznej weryfikacji", "review")
    else:
        log("brak błędów w danych", "ok")


def _log_ai(products: list[Product], threshold: float, log: RunLog) -> None:
    accepted = [p for p in products if not p.review_reasons]
    review = [p for p in products if p.review_reasons]
    log(f"{fmt.rows(len(accepted))} z kategorią przypisaną z pewnością ≥ {fmt.percent(threshold)}", "ok")
    if review:
        reasons = Counter(_reason_kind(r) for p in review for r in p.review_reasons)
        detail = ", ".join(f"{k}: {n}" for k, n in reasons.most_common())
        log(f"{fmt.rows(len(review))} do ręcznej weryfikacji ({detail})", "review")


def _reason_kind(reason: str) -> str:
    for prefix, label in (("niska pewność", "niska pewność"), ("kategoria w pliku", "rozbieżna kategoria"),
                          ("brak ceny", "brak ceny"),
                          ("AI zmieniło liczby", "zmienione liczby"), ("AI niedostępne", "AI niedostępne")):
        if reason.startswith(prefix):
            return label
    return "niepoprawna odpowiedź AI"
