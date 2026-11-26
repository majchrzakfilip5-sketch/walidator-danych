"""Eksport wyników dla strony statycznej (web/).

Uruchamia pełny przebieg narzędzia na dwóch plikach przykładowych (prawdziwe AI, jeśli jest
klucz w .env, w przeciwnym razie tryb mock) i zapisuje:
  web/data/index.json        lista plików i metadane eksportu
  web/data/<id>.json         podsumowanie, każdy wiersz (przed / po / źródło zmiany / problemy / AI),
                             pliki wynikowe w skrócie, wynik SQL, logi przebiegu
  web/downloads/<id>/        clean_import.csv, error_report.xlsx, manual_review.xlsx, plik wejściowy
oraz wpisuje w stronę (web/index.html) liczby i wiersze pliku 01 (hero) i liczby schematu
w sekcji "Jak działa", żeby były widoczne od pierwszej klatki, także bez JavaScriptu.

Strona czyta wyłącznie te pliki: bez backendu i bez kluczy.

  python scripts/export_web.py            # AI, jeśli jest LLM_API_KEY
  python scripts/export_web.py --mock     # wymuś tryb mock
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from walidator import fmt  # noqa: E402
from walidator.config import AppConfig, load_config, load_llm_settings  # noqa: E402
from walidator.issues import Severity  # noqa: E402
from walidator.master import KEY_LABELS  # noqa: E402
from walidator.models import Product, Status  # noqa: E402
from walidator.pipeline import RunResult, run_pipeline  # noqa: E402

WEB = ROOT / "web"
HERO_SAMPLE = "01"
# (id, plik, etykieta, krótka etykieta, opis)
SAMPLES = [
    ("01", "01_plik_brudny.xlsx", "Plik brudny", "Brudny", "Mieszane formaty, duplikaty, braki."),
    ("02", "02_plik_bardzo_brudny.xlsx", "Plik bardzo brudny", "Bardzo brudny", "Inne nagłówki, puste wiersze, chaos."),
]
SEVERITY_KEY = {Severity.CRITICAL: "critical", Severity.WARNING: "warning", Severity.FIXED: "fixed"}
STATUS_KEY = {Status.READY: "ready", Status.REVIEW: "review", Status.SKIPPED: "skipped"}
FROM_MASTER = {"ean": "EAN_Z_KARTOTEKI", "weight": "GRAMATURA_Z_KARTOTEKI", "name": "NAZWA_Z_KARTOTEKI"}
FIELDS = [("name", "Nazwa"), ("ean", "EAN"), ("weight", "Gramatura"), ("price", "Cena netto"),
          ("expiry", "Data ważności"), ("category", "Kategoria")]


# --- wiersz po wierszu: wartość w pliku, wartość po walidacji, źródło zmiany ------------------

def _fixed(p: Product, field: str) -> bool:
    return any(i.field == field and i.severity is Severity.FIXED for i in p.issues)


def _has(p: Product, code: str) -> bool:
    return any(i.code == code for i in p.issues)


def _after(p: Product, key: str) -> tuple[str, str | None]:
    """Wartość po walidacji i to, co ją zmieniło: "reguła", "kartoteka", "cennik", "AI" albo None."""
    if key in FROM_MASTER and _has(p, FROM_MASTER[key]):
        value = {"name": p.name, "ean": p.ean or "", "weight": f"{p.weight_g} g" if p.weight_g else ""}[key]
        return value, "kartoteka"
    if key == "name":
        if p.final_name != p.name:
            return p.final_name, "AI"
        return p.name, "reguła" if p.name != p.original["name"] else None
    if key == "ean":
        return p.ean or "", "reguła" if _fixed(p, "ean") else None
    if key == "weight":
        return (f"{p.weight_g} g" if p.weight_g else ""), "reguła" if _fixed(p, "weight") else None
    if key == "price":
        value = fmt.num(p.price, 2) if p.price is not None else ""
        return value, "cennik" if _has(p, "CENA_Z_CENNIKA") else "reguła" if _fixed(p, "price") else None
    if key == "expiry":
        return (p.expiry.isoformat() if p.expiry else ""), "reguła" if _fixed(p, "expiry") else None
    if key == "category":
        value = p.category or ""
        if value == p.original["category"]:
            return value, None
        if p.in_master:
            return value, "kartoteka"
        if p.classification:
            return value, "AI"
        return value, "reguła" if _fixed(p, "category") else None
    raise KeyError(key)


def row_record(p: Product, config: AppConfig) -> dict:
    cells = []
    for key, label in FIELDS:
        before = p.original[key]
        after, source = _after(p, key)
        field_issues = [i for i in p.issues if i.field == key]
        if any(i.is_critical for i in field_issues):
            state = "error"
        elif any(i.severity is Severity.WARNING for i in field_issues):
            state = "warning"
        elif source and before != after:
            state = "changed"
        else:
            state = "same"
        cells.append({"key": key, "label": label, "before": before, "after": after,
                      "source": source if source and before != after else None,
                      "state": state})
    c = p.classification
    return {
        "row": p.row,
        "sku": p.sku,
        "status": STATUS_KEY[p.status],
        "name": p.final_name or p.original["name"] or "(brak nazwy)",
        "summary": row_summary(p, cells),
        "cells": cells,
        "issues": [{"severity": SEVERITY_KEY[i.severity], "title": i.title, "field": config.source.label(i.field),
                    "detail": i.detail, "fix": i.fix or ""}
                   for i in sorted(p.issues, key=lambda i: ["critical", "warning", "fixed"].index(SEVERITY_KEY[i.severity]))],
        "ai": {"category": c.category, "confidence": c.confidence, "reasoning": c.reasoning, "segment": c.segment}
        if c else None,
        "data_error": p.has_critical and p.status is Status.REVIEW,
        "fixed": any(i.severity is Severity.FIXED for i in p.issues),
        "reasons": p.all_review_reasons if p.status is Status.REVIEW else [],
        "master": [KEY_LABELS[k] for k in p.master_keys] if p.in_master else None,
        "to_ai": p.classification is not None or (not p.in_master and p.duplicate_of is None and bool(p.name)),
        "duplicate_of": p.duplicate_of,
    }


MASTER_NOTES = [("EAN_Z_KARTOTEKI", "EAN z kartoteki"), ("SKU_Z_KARTOTEKI", "SKU z kartoteki"),
                ("GRAMATURA_Z_KARTOTEKI", "gramatura z kartoteki"), ("NAZWA_Z_KARTOTEKI", "nazwa z kartoteki"),
                ("CENA_Z_CENNIKA", "cena z cennika")]


def row_summary(p: Product, cells: list[dict]) -> str:
    """Jedna linia pod nazwą wiersza na liście: co się z nim stało."""
    if p.status is Status.SKIPPED:
        return f"identyczny z wierszem {p.duplicate_of}: pominięty"
    if p.has_critical:
        first = next(i for i in p.issues if i.is_critical)
        more = sum(i.is_critical for i in p.issues) - 1
        return first.title + (f" (+{more})" if more else "")
    if p.status is Status.REVIEW:
        if any(r.startswith("brak ceny") for r in p.review_reasons):
            return "brak ceny w pliku i w cenniku"
        if p.classification:
            return f"AI: {p.classification.category}, pewność {fmt.percent(p.classification.confidence)}"
        return "brak odpowiedzi AI"
    notes = [label for code, label in MASTER_NOTES if _has(p, code)]
    changes = [f"{c['before']} → {c['after']}" for c in cells
               if c["source"] == "reguła" and c["key"] in ("weight", "price", "expiry") and c["before"] != c["after"]]
    if notes or changes:
        return ", ".join((notes + changes)[:2])
    if any(c["source"] == "AI" and c["key"] == "name" for c in cells):
        return "nazwa poprawiona przez AI"
    return "bez zmian w formatach"


FROM_SOURCES = {"EAN_Z_KARTOTEKI", "SKU_Z_KARTOTEKI", "NAZWA_Z_KARTOTEKI", "GRAMATURA_Z_KARTOTEKI",
                "KATEGORIA_Z_KARTOTEKI", "CENA_Z_CENNIKA"}


def review_groups(products: list[Product]) -> list[dict]:
    """Wiersze do ręcznej weryfikacji pogrupowane według powodu (najliczniejsze grupy najpierw)."""
    groups: dict[str, list[int]] = {}
    for p in products:
        if p.status is not Status.REVIEW:
            continue
        if p.has_critical:
            titles = [i.title for i in p.issues if i.is_critical]
        else:
            titles = [r.split(" (")[0].split(":")[0] for r in p.review_reasons] or ["brak odpowiedzi AI"]
        for t in dict.fromkeys(titles):
            groups.setdefault(t[:1].upper() + t[1:], []).append(p.row)
    return [{"title": t, "rows": rows} for t, rows in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[1][0]))]


# --- budowa JSON ----------------------------------------------------------------------------

def sample_payload(sample_id: str, label: str, result: RunResult, config: AppConfig) -> dict:
    s = result.summary
    products = result.products
    return {
        "id": sample_id,
        "file": result.source.name,
        "label": label,
        "run": {
            "recorded_at": result.started_at.isoformat(timespec="seconds"),
            "mode": result.mode,
            "duration_s": round(result.duration_s, 2),
            "cost_usd": round(result.cost_usd, 6),
            "cost_pln": round(result.cost_pln, 6),
            "requests": result.usage.requests,
            "threshold": config.ai.confidence_threshold,
        },
        "summary": {
            "rows_in": s.rows_in, "ready": s.ready, "review": s.review, "review_data": s.review_data,
            "fixed_rows": s.fixed_rows, "critical": s.critical_issues, "warnings": s.warnings, "fixes": s.fixes,
            "sent_to_ai": s.sent_to_ai, "skipped": s.skipped, "in_master": s.in_master,
            "from_sources": sum(i.code in FROM_SOURCES for p in products for i in p.issues),
        },
        "fixes_by_field": dict(Counter(config.source.label(i.field) for p in products for i in p.issues
                                       if i.severity is Severity.FIXED and i.code != "DUPLIKAT_WIERSZA").most_common()),
        "review_groups": review_groups(products),
        "log": [{"t": e.t, "kind": e.kind, "text": e.text} for e in result.log],
        "rows": [row_record(p, config) for p in products],
        "downloads": {
            "input": f"downloads/{sample_id}/{result.source.name}",
            "csv": f"downloads/{sample_id}/{result.outputs['csv'].name}",
            "errors": f"downloads/{sample_id}/{result.outputs['errors'].name}",
            "review": f"downloads/{sample_id}/{result.outputs['review'].name}",
        },
    }


# --- hero strony: liczby i wiersze z pliku 02 wpisane w HTML ----------------------------------

CHIP = {"ready": ("st--ready", "Gotowy", 3), "review": ("st--review", "Do weryfikacji", 2),
        "skipped": ("st--skip", "Pominięty", 1)}


def pick_hero_rows(rows: list[dict], count: int = 10) -> list[dict]:
    """Mieszanka, która od razu pokazuje, co robi narzędzie: poprawione formaty, nazwa od AI,
    dwa różne błędy w danych i jeden wiersz z niepewną kategorią."""
    ready = [r for r in rows if r["status"] == "ready"]
    by_fixes = sorted(ready, key=lambda r: -sum(c["state"] == "changed" and c["key"] != "category" for c in r["cells"]))
    ai_named = [r for r in by_fixes if any(c["key"] == "name" and c["source"] == "AI" for c in r["cells"])]
    seen_titles, data_errors = set(), []
    for r in rows:
        if r["data_error"] and r["summary"] not in seen_titles:
            seen_titles.add(r["summary"])
            data_errors.append(r)
    ai_review = [r for r in rows if r["status"] == "review" and not r["data_error"]]
    chosen: list[dict] = []
    for r in by_fixes[:2] + ai_named[:1] + data_errors[:2] + ai_review[:1] + by_fixes[2:]:
        if r not in chosen:
            chosen.append(r)
        if len(chosen) == count:
            break
    return sorted(chosen, key=lambda r: r["row"])


def hero_rows_html(rows: list[dict]) -> str:
    out = []
    for r in rows:
        cls, label, tone = CHIP[r["status"]]
        out.append(
            f'<li class="ui-win__row" data-row><span class="ui-avatar" data-tone="{tone}">{r["row"]}</span>'
            f'<span class="ui-win__who">{html.escape(r["name"])}</span>'
            f'<span class="ui-win__sub">{html.escape(r["summary"])}</span>'
            f'<span class="ui-win__st {cls}" data-st>{label}</span>'
            f'<span class="ui-win__age">{html.escape(r["sku"])}</span></li>')
    return "\n                ".join(out)


# --- "Jak działa": schemat z liczbami pliku 01 ------------------------------------------------

def diagram_spec(payload: dict) -> dict:
    """Plik i kartoteka z ERP wchodzą do reguł (Python), nowe produkty idą do AI, na końcu trzy wyniki."""
    s = payload["summary"]
    rows = lambda n: fmt.plural(n, "wiersz", "wiersze", "wierszy")  # noqa: E731
    fixes = fmt.plural(s["fixes"], "poprawka", "poprawki", "poprawek")
    return {
        "layout": "free",
        "controls": False,
        "alt": (f"Plik Excel z {fmt.plural(s['rows_in'], 'wierszem', 'wierszami', 'wierszami')} i kartoteka produktów "
                f"z ERP trafiają do reguł w Pythonie; AI dostaje tylko nowe produkty. Wynik: {rows(s['ready'])} do "
                f"importu do ERP, {rows(s['review'])} do ręcznej weryfikacji, a raport opisuje {fixes}."),
        "nodes": [
            {"id": "plik", "label": "Plik Excel", "icon": "xlsx", "sub": rows(s["rows_in"]), "role": "input", "kind": "card", "kindCompact": "tile",
             "at": [0.15, 0.5], "atCompact": [0.27, 0.1]},
            {"id": "kartoteka", "label": "Kartoteka ERP", "icon": "ui:database",
             "sub": f"{s['in_master']} rozpoznanych", "role": "input", "kind": "card", "kindCompact": "tile", "at": [0.4, 0.17], "atCompact": [0.73, 0.1]},
            {"id": "reguly", "label": "Reguły", "icon": "python", "role": "core", "at": [0.4, 0.5],
             "atCompact": [0.5, 0.32]},
            {"id": "ai", "label": "AI", "icon": "ui:sparkles", "role": "core", "at": [0.62, 0.5],
             "atCompact": [0.5, 0.54]},
            {"id": "import", "label": "Import do ERP", "icon": "ui:package-check", "sub": rows(s["ready"]), "kind": "card", "kindCompact": "tile",
             "done": True, "at": [0.86, 0.25], "atCompact": [0.18, 0.84]},
            {"id": "weryfikacja", "label": "Weryfikacja", "icon": "ui:user-check", "sub": rows(s["review"]), "kind": "card", "kindCompact": "tile",
             "done": True, "at": [0.86, 0.5], "atCompact": [0.5, 0.84]},
            {"id": "raport", "label": "Raport zmian", "icon": "ui:clipboard-list", "sub": fixes, "kind": "card", "kindCompact": "tile",
             "done": True, "at": [0.86, 0.75], "atCompact": [0.82, 0.84]},
        ],
        "edges": [
            {"from": "plik", "to": "reguly"},
            {"from": "kartoteka", "to": "reguly"},
            {"from": "reguly", "to": "ai"},
            {"from": "ai", "to": "import", "curve": "elbow"},
            {"from": "ai", "to": "weryfikacja"},
            {"from": "ai", "to": "raport", "curve": "elbow"},
        ],
    }


def _verb(n: int, one: str, many: str) -> str:
    """Zgoda czasownika z liczebnikiem: 1 i 5+ "trafia", 2-4 (bez 12-14) "trafiają"."""
    return many if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else one


def page_facts(payload: dict) -> dict[str, str]:
    s = payload["summary"]
    rows = lambda n: fmt.plural(n, "wiersz", "wiersze", "wierszy")  # noqa: E731
    return {
        **{k: str(v) for k, v in s.items()},
        "file": payload["file"],
        "lead": (f"Z {s['rows_in']} wierszy przykładowego pliku {s['ready']} "
                 f"{_verb(s['ready'], 'trafia', 'trafiają')} od razu do importu, a do ręcznej weryfikacji "
                 f"tylko {s['review']}."),
        "fixes_phrase": fmt.plural(s["fixes"], "poprawka automatyczna", "poprawki automatyczne", "poprawek automatycznych"),
        "ai_rows": fmt.plural(s["sent_to_ai"], "nowego produktu", "nowych produktów", "nowych produktów"),
        "master_rows": f"{s['in_master']} z {s['rows_in']}",
        "ready_rows": f"{s['ready']} do importu",
        "review_rows": f"{s['review']} do weryfikacji",
    }


def update_page(page: Path, payload: dict) -> None:
    text = page.read_text(encoding="utf-8")
    for key, value in page_facts(payload).items():
        text = re.sub(rf'(data-fact="{key}"[^>]*>)[^<]*(<)', lambda m: f"{m.group(1)}{html.escape(value)}{m.group(2)}", text)
    rows = hero_rows_html(pick_hero_rows(payload["rows"]))
    text = re.sub(r"(<!-- hero-rows -->).*?(<!-- /hero-rows -->)",
                  lambda m: f"{m.group(1)}\n                {rows}\n                {m.group(2)}", text, flags=re.S)
    spec = json.dumps(diagram_spec(payload), ensure_ascii=False)
    text = re.sub(r'(<script type="application/json" id="how-diagram">).*?(</script>)',
                  lambda m: f"{m.group(1)}{spec}{m.group(2)}", text, flags=re.S)
    page.write_text(text, encoding="utf-8", newline="\n")


# --- pomocnicze -------------------------------------------------------------------------------

def repo_url(explicit: str | None) -> str | None:
    if explicit:
        return explicit
    try:
        url = subprocess.run(["git", "config", "--get", "remote.origin.url"], cwd=ROOT, capture_output=True,
                             text=True, check=False).stdout.strip()
    except OSError:
        return None
    if url.startswith("git@github.com:"):
        url = "https://github.com/" + url.removeprefix("git@github.com:")
    return url.removesuffix(".git") or None


def assert_no_secret(paths: list[Path], secret: str | None) -> None:
    """Klucz API nie może trafić do plików strony. Sprawdzamy bajty każdego zapisanego pliku;
    wygenerowane dane i pliki do pobrania są wtedy usuwane (strony index.html nie ruszamy)."""
    if not secret:
        return
    needle = secret.encode()
    leaked = [p for p in paths if needle in p.read_bytes()]
    if leaked:
        for p in paths:
            if p.name != "index.html" or p.parent.name == "data":
                p.unlink(missing_ok=True)
        raise SystemExit(f"Przerwano: klucz API znaleziony w {', '.join(str(p) for p in leaked)}.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Eksport wyników na stronę statyczną (web/data, web/downloads).")
    parser.add_argument("--mock", action="store_true", help="wymuś tryb mock (bez AI)")
    parser.add_argument("--repo-url", default=None, help="adres repozytorium (domyślnie z git remote origin)")
    args = parser.parse_args()
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    config = load_config()
    settings = load_llm_settings(config.ai)
    data_dir, downloads_dir = WEB / "data", WEB / "downloads"
    shutil.rmtree(downloads_dir, ignore_errors=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    index = {"generated_at": datetime.now().isoformat(timespec="seconds"), "repo_url": repo_url(args.repo_url),
             "samples": []}

    with tempfile.TemporaryDirectory() as tmp:
        for sample_id, filename, label, short, description in SAMPLES:
            source = ROOT / "data" / "samples" / filename
            result = run_pipeline(source, config, settings, force_mock=args.mock, output_dir=Path(tmp) / sample_id)
            target = downloads_dir / sample_id
            target.mkdir(parents=True, exist_ok=True)
            for path in (source, result.outputs["csv"], result.outputs["errors"], result.outputs["review"]):
                written.append(Path(shutil.copy2(path, target / path.name)))
            payload = sample_payload(sample_id, label, result, config)
            data_path = data_dir / f"{sample_id}.json"
            data_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8",
                                 newline="\n")
            written.append(data_path)
            if sample_id == HERO_SAMPLE and (WEB / "index.html").exists():
                update_page(WEB / "index.html", payload)
            index["samples"].append({"id": sample_id, "file": filename, "label": label, "short": short,
                                     "description": description, "rows": result.summary.rows_in})
            s = result.summary
            print(f"{filename:<30} wejście {s.rows_in:>2} | gotowe {s.ready:>2} | weryfikacja {s.review:>2} "
                  f"(błędy w danych {s.review_data}) | {result.mode} | {fmt.num(result.duration_s)} s | "
                  f"{fmt.num(result.cost_usd, 4)} USD")

    index_path = data_dir / "index.json"
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    written += [index_path, WEB / "index.html"]
    assert_no_secret([p for p in written if p.exists()], settings.api_key)
    print(f"Zapisano {len(written)} plików do {WEB.relative_to(ROOT)}/ (sprawdzono: brak klucza API w plikach)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
