"""Wczytanie konfiguracji z config/mapping.yaml i ustawień LLM ze zmiennych środowiskowych."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "mapping.yaml"

# Pola, na których opiera się logika walidacji. Mapowanie nagłówków jest w YAML.
# Rdzen jest wspolny dla kazdego wdrozenia. Rozmiar i kolor sa opcjonalne
# (ma je odziez i obuwie, nie ma zywnosc). Pole daty wystepuje pod jedna
# z dwoch nazw, zaleznie od tego, co data oznacza w danej branzy:
#   delivery - termin dostawy (data w przyszlosci),
#   expiry   - data waznosci (towar nie moze byc przeterminowany).
# Wewnetrznie uzywamy nazwy "delivery", a tryb zapamietuje rules.date_mode.
CORE_INPUT_FIELDS = ("sku", "ean", "name", "weight", "price", "category", "description")
OPTIONAL_INPUT_FIELDS = ("size", "color")
DATE_FIELDS = ("delivery", "expiry")
INPUT_FIELDS = CORE_INPUT_FIELDS + OPTIONAL_INPUT_FIELDS + DATE_FIELDS
OUTPUT_FIELDS = ("sku", "ean", "name", "weight_g", "size", "color", "price", "delivery", "expiry",
                 "category", "segment")


class ConfigError(Exception):
    """Błąd w pliku konfiguracyjnym, z czytelnym komunikatem dla użytkownika."""


class FieldSpec(BaseModel):
    label: str
    headers: list[str] = Field(min_length=1)
    required: bool = False


class SourceConfig(BaseModel):
    sheet: str | int | None = None
    fields: dict[str, FieldSpec]

    @field_validator("fields")
    @classmethod
    def _all_fields_defined(cls, fields: dict[str, FieldSpec]) -> dict[str, FieldSpec]:
        missing = [name for name in CORE_INPUT_FIELDS if name not in fields]
        unknown = [name for name in fields if name not in INPUT_FIELDS]
        if missing:
            raise ValueError(f"brak definicji pól: {', '.join(missing)}")
        if unknown:
            raise ValueError(f"nieznane pola: {', '.join(unknown)} (dozwolone: {', '.join(INPUT_FIELDS)})")
        daty = [name for name in DATE_FIELDS if name in fields]
        if len(daty) != 1:
            raise ValueError(f"trzeba zdefiniowac dokladnie jedno pole daty: {' albo '.join(DATE_FIELDS)}")
        return fields

    @property
    def required_fields(self) -> list[str]:
        return [name for name, spec in self.fields.items() if spec.required]

    def label(self, field: str) -> str:
        return self.fields[field].label if field in self.fields else field


class RulesConfig(BaseModel):
    date_formats: list[str] = Field(min_length=1)
    reference_date: date | None = None
    max_delivery_days: int = Field(default=120, ge=0)
    short_expiry_days: int = Field(default=90, ge=0)
    date_mode: Literal["delivery", "expiry"] = "delivery"
    weight_unit_if_missing: Literal["g", "kg"] | None = None
    check_weight_in_name: bool = True
    price_list: str | None = None
    product_master: str | None = None

    def today(self) -> date:
        return self.reference_date or date.today()


class PricingConfig(BaseModel):
    input_per_1m: float = Field(ge=0)
    input_cached_per_1m: float = Field(ge=0)
    output_per_1m: float = Field(ge=0)


class AIConfig(BaseModel):
    base_url: str
    model: str
    temperature: float = Field(default=0, ge=0, le=2)
    max_tokens: int = Field(default=4000, gt=0)
    batch_size: int = Field(default=10, gt=0)
    max_parallel: int = Field(default=4, gt=0)
    api_retries: int = Field(default=3, ge=0)
    timeout_seconds: float = Field(default=45, gt=0)
    confidence_threshold: float = Field(default=0.75, ge=0, le=1)
    extra_body: dict[str, Any] = Field(default_factory=dict)
    # Slownik mocka AI (kategorie, marki, literowki) to dane branzy: plik z profilu wdrozenia.
    mock_dictionary: str | None = None
    categories: list[str] = Field(min_length=2)
    segments: list[str] = Field(min_length=1)
    pricing: PricingConfig
    usd_to_pln: float = Field(default=4.0, gt=0)

    @field_validator("categories")
    @classmethod
    def _has_fallback(cls, categories: list[str]) -> list[str]:
        if "Inne" not in categories:
            raise ValueError("lista kategorii musi zawierać kategorię 'Inne'")
        return categories


class OutputColumn(BaseModel):
    header: str
    field: str

    @field_validator("field")
    @classmethod
    def _known_field(cls, field: str) -> str:
        if field not in OUTPUT_FIELDS:
            raise ValueError(f"nieznane pole wyjściowe '{field}' (dozwolone: {', '.join(OUTPUT_FIELDS)})")
        return field


class CsvConfig(BaseModel):
    file: str
    separator: str = Field(min_length=1, max_length=1)
    encoding: str = "utf-8"
    decimal_separator: Literal[".", ","] = "."
    date_format: str = "%Y-%m-%d"
    columns: list[OutputColumn] = Field(min_length=1)

    @model_validator(mode="after")
    def _separators_differ(self) -> CsvConfig:
        if self.separator == self.decimal_separator:
            raise ValueError("separator kolumn i separator dziesiętny muszą być różne")
        return self


class OutputConfig(BaseModel):
    dir: str = "output"
    import_csv: CsvConfig
    error_report: str = "error_report.xlsx"
    manual_review: str = "manual_review.xlsx"
    sqlite: str = "products.db"


class AppConfig(BaseModel):
    source: SourceConfig
    rules: RulesConfig
    ai: AIConfig
    output: OutputConfig


def _normalize_date_field(raw: dict) -> None:
    """Pole daty moze nazywac sie expiry albo delivery. Dalej w kodzie jest
    zawsze "delivery", a znaczenie niesie rules.date_mode."""
    fields = (raw.get("source") or {}).get("fields") or {}
    if "expiry" not in fields:
        return
    fields["delivery"] = fields.pop("expiry")
    raw.setdefault("rules", {})["date_mode"] = "expiry"
    for csv_cfg in (raw.get("output") or {}).values():
        if not isinstance(csv_cfg, dict):
            continue
        for col in csv_cfg.get("columns") or []:
            if isinstance(col, dict) and col.get("field") == "expiry":
                col["field"] = "delivery"


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> AppConfig:
    """Wczytuje i waliduje plik YAML. Błędy zgłasza z nazwą klucza, którego dotyczą."""
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"Nie znaleziono pliku konfiguracji: {path}")
    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    _normalize_date_field(raw)
    try:
        cfg = AppConfig.model_validate(raw)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()
        )
        raise ConfigError(f"Niepoprawna konfiguracja w {path.name}: {problems}") from exc
    if cfg.ai.mock_dictionary:
        from .ai import mock as _mock
        sciezka = Path(cfg.ai.mock_dictionary)
        if not sciezka.is_absolute():
            sciezka = path.parent / sciezka          # slownik lezy obok mapping.yaml
        if sciezka.exists():
            _mock.wczytaj_slownik(sciezka)
    return cfg


@dataclass(frozen=True)
class LLMSettings:
    """Ustawienia połączenia z modelem. Klucz nigdy nie trafia do logów ani plików wynikowych."""

    base_url: str
    model: str
    api_key: str | None

    @property
    def has_key(self) -> bool:
        return bool(self.api_key)

    def __repr__(self) -> str:  # klucz zamaskowany także przy przypadkowym wypisaniu obiektu
        return f"LLMSettings(base_url={self.base_url!r}, model={self.model!r}, api_key={'***' if self.api_key else None})"


def load_llm_settings(ai: AIConfig, env_file: Path | None = PROJECT_ROOT / ".env") -> LLMSettings:
    """Zmienne środowiskowe mają pierwszeństwo, wartości z YAML są domyślne."""
    if env_file is not None and env_file.exists():
        load_dotenv(env_file, override=False)
    return LLMSettings(
        base_url=os.getenv("LLM_BASE_URL") or ai.base_url,
        model=os.getenv("LLM_MODEL") or ai.model,
        api_key=os.getenv("LLM_API_KEY") or None,
    )
