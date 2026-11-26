"""Warstwa 1: reguły walidacji w kodzie, bez AI.

Wszystkie liczby i identyfikatory (EAN, SKU, waga, rozmiar, cena, data) sprawdza
wyłącznie ten moduł. Każdy problem staje się rekordem Issue z numerem wiersza,
polem, typem, wartością oryginalną i proponowaną poprawką (tylko jeśli jest pewna).

Źródła prawdy (opcjonalne, z konfiguracji):
  - kartoteka produktów z ERP: produkt rozpoznany po SKU, EAN albo nazwie dostaje stamtąd
    poprawny EAN, SKU, wagę, rozmiar, kolor, nazwę i kategorię, więc literówka w kodzie czy brak rozmiaru
    przestaje być powodem do ręcznej weryfikacji;
  - cennik: uzupełnia brakującą albo nieczytelną cenę.
Do człowieka trafia tylko to, czego nie zna żadne źródło (np. brak terminu dostawy).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from .config import INPUT_FIELDS, AppConfig
from .issues import Issue
from .master import KEY_LABELS, ProductMaster, load_product_master
from .models import Product
from .parsers import (
    clean_text,
    display,
    header_key,
    is_blank,
    parse_date,
    parse_color,
    parse_ean,
    parse_price,
    parse_size,
    parse_weight,
    weight_in_name,
)
from .pricelist import load_price_list
from .reader import SourceRow, SourceTable

# pola, które kartoteka może poprawić albo uzupełnić
MASTER_FIELDS = ("sku", "ean", "weight", "size", "color", "name")


def validate_table(table: SourceTable, config: AppConfig) -> list[Product]:
    prices = load_price_list(config.rules)
    master = load_product_master(config.rules)
    products = [validate_row(row, config, prices, master) for row in table.rows]
    flag_duplicates(products, {name: spec.label for name, spec in config.source.fields.items()})
    return products


def validate_row(src: SourceRow, config: AppConfig, prices: dict | None = None,
                 master: ProductMaster | None = None) -> Product:
    rules, source = config.rules, config.source
    raw = src.values
    original = {name: display(raw.get(name)) for name in INPUT_FIELDS}
    sku = clean_text(raw.get("sku"))
    issues: list[Issue] = []
    review: list[str] = []
    pending: dict[str, list[Issue]] = defaultdict(list)   # problemy, które może rozwiązać kartoteka

    def add(field: str, code: str, fix: str | None = None, detail: str = "") -> None:
        issues.append(Issue(src.row_number, sku, field, code, original[field], fix, detail))

    def problem(field: str, code: str, detail: str = "") -> None:
        target = pending[field] if field in MASTER_FIELDS else issues
        target.append(Issue(src.row_number, sku, field, code, original[field], None, detail))

    missing = {name for name in source.required_fields if is_blank(raw.get(name))}
    price_blank = is_blank(raw.get("price"))
    if price_blank and prices is not None:
        missing.discard("price")   # brak ceny to nie błąd: uzupełni ją cennik albo człowiek
    for name in INPUT_FIELDS:
        if name in missing:
            problem(name, "BRAK_WARTOSCI", detail=f"kolumna '{source.label(name)}' jest wymagana")

    if sku and sku != original["sku"]:
        add("sku", "SPACJE", fix=sku)

    ean = None
    if not is_blank(raw.get("ean")):
        result = parse_ean(raw["ean"])
        if result.ok:
            ean = result.value
            if result.reformatted:
                add("ean", "FORMAT_EAN", fix=ean)
        else:
            problem("ean", result.error, detail=result.detail)

    name = clean_text(raw.get("name"))

    weight = None
    if not is_blank(raw.get("weight")):
        result = parse_weight(raw["weight"], rules.weight_unit_if_missing)
        if result.ok:
            weight = result.value
            if result.reformatted:
                add("weight", "FORMAT_WAGI", fix=str(weight))
        else:
            problem("weight", result.error, detail=result.detail)

    size = None
    if not is_blank(raw.get("size")):
        result = parse_size(raw["size"])
        if result.ok:
            size = result.value
            if result.reformatted:
                add("size", "FORMAT_ROZMIARU", fix=size)
        else:
            problem("size", result.error, detail=result.detail)

    color = None
    if not is_blank(raw.get("color")):
        result = parse_color(raw["color"])
        color = result.value
        if result.ok and result.reformatted:
            add("color", "FORMAT_KOLORU", fix=color)
        elif not result.ok:
            problem("color", result.error, detail=result.detail)   # kolor spoza słownika: ostrzeżenie

    price, price_problem = None, None
    if not price_blank:
        result = parse_price(raw["price"])
        if result.ok:
            price = result.value
            if result.reformatted:
                add("price", "FORMAT_CENY", fix=str(price))
        else:
            price_problem = (result.error, result.detail)

    delivery = None
    if not is_blank(raw.get("delivery")):
        result = parse_date(raw["delivery"], rules.date_formats)
        if result.ok:
            delivery = result.value
            if result.reformatted:
                add("delivery", "FORMAT_DATY", fix=delivery.isoformat())
            if rules.date_mode == "expiry":
                _check_expiry(delivery, rules.today(), rules.short_expiry_days, add)
            else:
                _check_delivery(delivery, rules.today(), rules.max_delivery_days, add)
        else:
            add("delivery", result.error, detail=result.detail)

    raw_category = clean_text(raw.get("category"))
    source_category = master_category = master_segment = None
    keys: tuple[str, ...] = ()

    # --- kartoteka: znany produkt dostaje poprawne dane, nieznany idzie dalej do AI ------------------
    match = master.match(sku, ean, name) if master else None
    if match and match.product:
        mp = match.product
        keys = match.keys
        found_by = ", ".join(KEY_LABELS[k] for k in keys)
        if sku != mp.sku:
            add("sku", "SKU_Z_KARTOTEKI", fix=mp.sku,
                detail=f"w pliku {sku or 'pusto'}; produkt rozpoznany po: {found_by}")
            sku = mp.sku
        if ean != mp.ean:
            add("ean", "EAN_Z_KARTOTEKI", fix=mp.ean,
                detail=_why(pending["ean"], ean and f"w pliku {ean}, a kartoteka ma dla tego produktu inny kod"))
            issues[:] = [i for i in issues if not (i.field == "ean" and i.code == "FORMAT_EAN")]
            ean = mp.ean
        if weight != mp.weight_g:
            add("weight", "WAGA_Z_KARTOTEKI", fix=str(mp.weight_g),
                detail=_why(pending["weight"], weight and f"w pliku {weight} g, w kartotece {mp.weight_g} g"))
            issues[:] = [i for i in issues if not (i.field == "weight" and i.code == "FORMAT_WAGI")]
            weight = mp.weight_g
        if mp.size and size != mp.size:          # kartoteka bez rozmiarow: nie ma czego poprawiac
            add("size", "ROZMIAR_Z_KARTOTEKI", fix=mp.size,
                detail=_why(pending["size"], size and f"w pliku {size}, a ten SKU to rozmiar {mp.size}"))
            issues[:] = [i for i in issues if not (i.field == "size" and i.code == "FORMAT_ROZMIARU")]
            size = mp.size
        if mp.color and color != mp.color:       # jw. dla koloru
            add("color", "KOLOR_Z_KARTOTEKI", fix=mp.color,
                detail=_why(pending["color"], color and f"w pliku {color}, a ten SKU to kolor {mp.color}"))
            issues[:] = [i for i in issues if not (i.field == "color" and i.code == "FORMAT_KOLORU")]
            color = mp.color
        if name != mp.name:
            add("name", "NAZWA_Z_KARTOTEKI", fix=mp.name,
                detail=_why(pending["name"], name and "w pliku inna pisownia (literówka, wielkość liter)"))
            name = mp.name
        elif name != original["name"]:
            add("name", "SPACJE", fix=name)
        if raw_category and raw_category != mp.category:
            add("category", "KATEGORIA_Z_KARTOTEKI", fix=mp.category,
                detail=f"w pliku '{raw_category}', w kartotece '{mp.category}'")
        master_category, master_segment = mp.category, mp.segment
        pending.clear()
    else:
        if match and match.conflict:
            add("sku", "KONFLIKT_KARTOTEKI", detail=match.conflict)
        for field in MASTER_FIELDS:
            issues.extend(pending[field])
        if name and name != original["name"]:
            add("name", "SPACJE", fix=name)
        named = weight_in_name(name) if rules.check_weight_in_name and name and weight else None
        if named is not None and named != weight:
            add("weight", "WAGA_NIEZGODNA_Z_NAZWA",
                detail=f"w nazwie {named} g, w kolumnie {weight} g; nie wiadomo, która wartość jest prawdziwa")
        if raw_category:
            allowed = {header_key(c): c for c in config.ai.categories}
            listed = allowed.get(header_key(raw_category))
            if listed:
                source_category = listed
                if listed != raw_category:
                    add("category", "FORMAT_KATEGORII", fix=listed)
            else:
                add("category", "KATEGORIA_SPOZA_LISTY", detail="kategorię zaproponuje AI z zamkniętej listy")

    # --- cena: z pliku, a gdy jej brak albo nie da się jej odczytać, z cennika (po poprawionym SKU) ---------
    listed_price = prices.get(sku.casefold()) if prices is not None and sku else None
    if price_problem:
        code, detail = price_problem
        if listed_price is not None:
            price = listed_price
            add("price", "CENA_Z_CENNIKA", fix=str(price), detail=f"w pliku błędna cena ({detail}); cena z cennika")
        else:
            add("price", code, detail=detail)
    elif price_blank and prices is not None:
        if listed_price is not None:
            price = listed_price
            add("price", "CENA_Z_CENNIKA", fix=str(price), detail="w pliku nie ma ceny, cena pochodzi z cennika")
        else:
            add("price", "BRAK_CENY", detail="w pliku nie ma ceny, a cennik nie zna tego SKU")
            review.append("brak ceny w pliku i w cenniku: uzupełnij cenę")

    for issue in issues:
        issue.sku = sku
    return Product(
        row=src.row_number,
        sku=sku,
        ean=ean,
        name=name,
        weight_g=weight,
        size=size,
        color=color,
        price=price,
        delivery=delivery,
        source_category=source_category,
        description=clean_text(raw.get("description")),
        original=original,
        issues=issues,
        review_reasons=review,
        master_category=master_category,
        master_segment=master_segment,
        master_keys=keys,
    )


def _why(problems: list[Issue], fallback: str | None) -> str:
    """Co było nie tak w pliku, zanim kartoteka podała poprawną wartość."""
    if problems:
        first = problems[0]
        what = first.title[:1].lower() + first.title[1:]
        return f"w pliku: {what}" + (f" ({first.detail})" if first.detail else "")
    return fallback or "w pliku brak wartości"


def _check_expiry(expiry: date, today: date, short_days: int, add) -> None:
    """Tryb expiry: towar przeterminowany to blad, krotki termin to ostrzezenie."""
    days_left = (expiry - today).days
    if days_left < 0:
        add("delivery", "DATA_PRZETERMINOWANA", detail=f"termin minął {-days_left} dni temu")
    elif days_left <= short_days:
        add("delivery", "KROTKI_TERMIN", detail=f"zostało {days_left} dni (próg: {short_days} dni)")


def _check_delivery(delivery: date, today: date, max_days: int, add) -> None:
    days_ahead = (delivery - today).days
    if days_ahead < 0:
        add("delivery", "DOSTAWA_W_PRZESZLOSCI", detail=f"termin minął {-days_ahead} dni temu")
    elif days_ahead > max_days:
        add("delivery", "ODLEGLA_DOSTAWA", detail=f"dostawa za {days_ahead} dni (próg: {max_days} dni)")


_COMPARED = {"sku": "sku", "ean": "ean", "name": "name", "weight": "weight_g", "size": "size", "color": "color",
             "price": "price", "delivery": "delivery", "category": "source_category", "description": "description"}


def _differences(a: Product, b: Product, skip: str, labels: dict[str, str]) -> str:
    diff = [labels.get(f, f) for f, attr in _COMPARED.items()
            if f != skip and getattr(a, attr) != getattr(b, attr)]
    return ", ".join(diff) if diff else "inne pola"


def flag_duplicates(products: list[Product], labels: dict[str, str] | None = None) -> None:
    """Identyczny wiersz (po normalizacji i poprawkach z kartoteki): pomijany, w imporcie zostaje pierwszy.
    Ten sam SKU lub EAN przy różnych danych (np. dwie ceny jednego produktu): oznaczamy wszystkie
    wystąpienia, bo nie wiadomo, który wiersz jest prawdziwy."""
    labels = labels or {}
    first_seen: dict[tuple, Product] = {}
    distinct: list[Product] = []
    for p in products:
        if not p.sku:
            distinct.append(p)
            continue
        key = p.identity()
        if key in first_seen:
            first = first_seen[key]
            p.duplicate_of = first.row
            p.issues.append(Issue(p.row, p.sku, "sku", "DUPLIKAT_WIERSZA", p.original["sku"],
                                  fix="pominięto w imporcie", detail=f"identyczny z wierszem {first.row}"))
        else:
            first_seen[key] = p
            distinct.append(p)

    _flag_groups(distinct, lambda p: p.sku.casefold() or None, "sku", "DUPLIKAT_SKU", labels)
    _flag_groups(distinct, lambda p: p.ean, "ean", "DUPLIKAT_EAN", labels)


def _flag_groups(products: list[Product], key_fn, field: str, code: str, labels: dict[str, str]) -> None:
    groups: dict[str, list[Product]] = defaultdict(list)
    for p in products:
        key = key_fn(p)
        if key:
            groups[key].append(p)
    for group in groups.values():
        if len(group) < 2:
            continue
        for p in group:
            others = [o for o in group if o is not p]
            if len(others) == 1:
                detail = f"ta sama wartość w wierszu {others[0].row}; różnice: {_differences(p, others[0], field, labels)}"
            else:
                detail = f"ta sama wartość w wierszach {', '.join(str(o.row) for o in others)}"
            p.issues.append(Issue(p.row, p.sku, field, code, p.original[field], detail=detail))
