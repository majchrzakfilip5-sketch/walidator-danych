"""Walidacja odpowiedzi modelu w kodzie (pydantic). Model może się mylić, kod nie wpuszcza błędów dalej."""

from __future__ import annotations

import json

from pydantic import BaseModel, ConfigDict, Field, ValidationError, ValidationInfo, field_validator

from ..models import Classification


class AIItem(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    id: int
    category: str
    normalized_name: str = Field(min_length=2, max_length=200)
    segment: str
    confidence: float = Field(ge=0, le=1)
    reasoning: str = Field(min_length=3, max_length=400)

    @field_validator("category")
    @classmethod
    def _category_from_closed_list(cls, value: str, info: ValidationInfo) -> str:
        allowed = info.context["categories"]
        if value not in allowed:
            raise ValueError(f"kategoria spoza listy: {value!r}")
        return value

    @field_validator("segment")
    @classmethod
    def _segment_from_closed_list(cls, value: str, info: ValidationInfo) -> str:
        allowed = info.context["segments"]
        match = next((s for s in allowed if s.casefold() == value.casefold()), None)
        if match is None:
            raise ValueError(f"segment spoza listy: {value!r}")
        return match

    def to_classification(self) -> Classification:
        return Classification(
            category=self.category,
            normalized_name=" ".join(self.normalized_name.split()),
            segment=self.segment,
            confidence=round(self.confidence, 3),
            reasoning=self.reasoning,
        )


def parse_response(content: str | None, expected_ids: list[int], categories: list[str],
                   segments: list[str]) -> tuple[dict[int, Classification], dict[int, str]]:
    """Zwraca poprawne wyniki oraz {id: powód} dla pozycji, których nie da się przyjąć.

    Każda pozycja jest walidowana osobno, więc jeden błędny wynik nie odrzuca całej partii.
    """
    if not content or not content.strip():
        return {}, {i: "pusta odpowiedź modelu" for i in expected_ids}
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return {}, {i: "odpowiedź nie jest poprawnym JSON" for i in expected_ids}
    items = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return {}, {i: "brak listy 'results' w odpowiedzi" for i in expected_ids}

    valid: dict[int, Classification] = {}
    errors: dict[int, str] = {}
    context = {"categories": categories, "segments": segments}
    for raw in items:
        try:
            item = AIItem.model_validate(raw, context=context)
        except ValidationError as exc:
            raw_id = raw.get("id") if isinstance(raw, dict) else None
            if isinstance(raw_id, int) and raw_id in expected_ids:
                errors[raw_id] = "; ".join(e["msg"].removeprefix("Value error, ") for e in exc.errors())
            continue
        if item.id in expected_ids and item.id not in valid:
            valid[item.id] = item.to_classification()
    for i in expected_ids:
        if i not in valid and i not in errors:
            errors[i] = "brak wyniku dla tego wiersza"
    return valid, errors
