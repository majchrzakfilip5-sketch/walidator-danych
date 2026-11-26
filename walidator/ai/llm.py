"""Warstwa 2: klasyfikacja tekstu przez model językowy (API zgodne z OpenAI, domyślnie DeepSeek)."""

from __future__ import annotations

import random
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import openai
from openai import OpenAI

from .. import fmt
from ..config import AIConfig, LLMSettings
from ..models import Classification
from .prompt import system_prompt, user_message
from .schema import parse_response
from .types import ClassificationRun, LogFn, TextItem, Usage

# Błędy przejściowe: warto ponowić. Błędy klucza i zapytania ponawiać nie ma sensu.
RETRYABLE = (openai.APIConnectionError, openai.APITimeoutError, openai.RateLimitError, openai.InternalServerError)


class LLMUnavailable(Exception):
    pass


@dataclass
class _BatchResult:
    index: int
    results: dict[int, Classification]
    failures: dict[int, str]
    usage: Usage
    retried: int
    seconds: float


class LLMClassifier:
    mode = "ai"

    def __init__(self, settings: LLMSettings, ai: AIConfig, sleep=time.sleep,
                 examples: list[tuple[str, str]] | None = None) -> None:
        if not settings.has_key:
            raise ValueError("Brak LLM_API_KEY: uruchom z flagą --mock albo uzupełnij plik .env")
        self.ai = ai
        self.model_name = settings.model
        self._sleep = sleep
        self._system = system_prompt(ai.categories, ai.segments, examples)
        self._client = OpenAI(api_key=settings.api_key, base_url=settings.base_url,
                              timeout=ai.timeout_seconds, max_retries=0)

    # --- publiczne API ------------------------------------------------------

    def classify(self, items: list[TextItem], log: LogFn) -> ClassificationRun:
        run = ClassificationRun()
        if not items:
            return run
        batches = split_evenly(items, self.ai.batch_size)
        with ThreadPoolExecutor(max_workers=min(self.ai.max_parallel, len(batches))) as pool:
            futures = [pool.submit(self._run_batch, idx, batch) for idx, batch in enumerate(batches, start=1)]
            for future in futures:
                result = future.result()
                run.results.update(result.results)
                run.failures.update(result.failures)
                run.usage.add(result.usage)
                run.retried += result.retried
                log(self._batch_summary(result, len(batches), len(batches[result.index - 1])))
        return run

    # --- partia -------------------------------------------------------------

    def _run_batch(self, index: int, batch: list[TextItem]) -> _BatchResult:
        started = time.perf_counter()
        usage = Usage()
        ids = [item.id for item in batch]
        try:
            content = self._request(batch, usage)
            valid, errors = parse_response(content, ids, self.ai.categories, self.ai.segments)
            retried = 0
            if errors:
                # Jedna ponowna próba tylko dla pozycji z niepoprawną odpowiedzią.
                retried = len(errors)
                again = [item for item in batch if item.id in errors]
                content = self._request(again, usage)
                valid2, errors2 = parse_response(content, list(errors), self.ai.categories, self.ai.segments)
                valid.update(valid2)
                errors = {i: f"niepoprawna odpowiedź AI po ponownej próbie ({reason})" for i, reason in errors2.items()}
        except LLMUnavailable as exc:
            valid, errors, retried = {}, {i: f"AI niedostępne: {exc}" for i in ids}, 0
        return _BatchResult(index, valid, errors, usage, retried, time.perf_counter() - started)

    def _request(self, batch: list[TextItem], usage: Usage) -> str | None:
        """Jedno zapytanie z ponowieniami i wykładniczym backoffem (1 s, 2 s, 4 s ... + losowy rozrzut)."""
        attempts = self.ai.api_retries + 1
        for attempt in range(1, attempts + 1):
            try:
                response = self._client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": self._system},
                        {"role": "user", "content": user_message(batch)},
                    ],
                    response_format={"type": "json_object"},
                    temperature=self.ai.temperature,
                    max_tokens=self.ai.max_tokens,
                    extra_body=self.ai.extra_body or None,
                )
            except RETRYABLE as exc:
                if attempt == attempts:
                    raise LLMUnavailable(f"{type(exc).__name__} po {attempts} próbach") from exc
                self._sleep(2 ** (attempt - 1) + random.uniform(0, 0.5))
                continue
            except openai.AuthenticationError as exc:
                raise LLMUnavailable("odrzucony klucz API (sprawdź LLM_API_KEY)") from exc
            except openai.APIStatusError as exc:
                raise LLMUnavailable(f"błąd API {exc.status_code}") from exc
            usage.add(_usage_of(response))
            return response.choices[0].message.content if response.choices else None
        return None

    @staticmethod
    def _batch_summary(result: _BatchResult, total: int, size: int) -> str:
        ok = len(result.results)
        line = f"partia {result.index}/{total}: {ok}/{size} poprawnych odpowiedzi ({fmt.num(result.seconds)} s)"
        if result.retried:
            line += f", ponowiono {result.retried}"
        if result.failures:
            line += f", bez wyniku: {len(result.failures)}"
        return line


def split_evenly(items: list[TextItem], max_size: int) -> list[list[TextItem]]:
    """31 wierszy przy limicie 10 -> partie 8, 8, 8, 7 zamiast 10, 10, 10, 1."""
    count = -(-len(items) // max_size)
    base, extra = divmod(len(items), count)
    batches, start = [], 0
    for i in range(count):
        end = start + base + (1 if i < extra else 0)
        batches.append(items[start:end])
        start = end
    return batches


def _usage_of(response) -> Usage:
    u = getattr(response, "usage", None)
    if u is None:
        return Usage(requests=1)
    cached = getattr(u, "prompt_cache_hit_tokens", None)
    if cached is None:
        details = getattr(u, "prompt_tokens_details", None)
        cached = getattr(details, "cached_tokens", 0) if details else 0
    return Usage(requests=1, prompt_tokens=u.prompt_tokens or 0, cached_tokens=cached or 0,
                 completion_tokens=u.completion_tokens or 0)
