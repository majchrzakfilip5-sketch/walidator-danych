"""Tryb CLI.

  python -m walidator run  <plik.xlsx> [--mock]   jednorazowy przebieg
  python -m walidator watch            [--mock]   obserwuje inbox/, plik po przetworzeniu trafia do processed/
"""

from __future__ import annotations

import argparse
import queue
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.status import Status
from rich.table import Table
from rich.text import Text

from . import __version__, fmt
from .config import (DEFAULT_CONFIG_PATH, PROJECT_ROOT, AppConfig, ConfigError, LLMSettings, load_config,
                     load_llm_settings)
from .pipeline import LogEntry, RunResult, run_pipeline
from .reader import SUPPORTED_EXTENSIONS, MappingError

console = Console(highlight=False)

STYLE = {
    "step": ("", "bold cyan"),
    "info": ("  ", "grey62"),
    "ok": ("✓ ", "green"),
    "warn": ("! ", "yellow"),
    "error": ("✗ ", "red"),
    "review": ("? ", "magenta"),
    "done": ("", "bold"),
}


class LogPrinter:
    """Wypisuje logi przebiegu; w trakcie zapytań do AI pokazuje spinner."""

    def __init__(self) -> None:
        self._status: Status | None = None

    def __call__(self, entry: LogEntry) -> None:
        if entry.kind == "step" and entry.text.startswith("[3/3]"):
            self.stop()
        prefix, style = STYLE.get(entry.kind, ("  ", ""))
        indent = "" if entry.kind in ("step", "done") or entry.text.startswith("Plik:") else "      "
        if entry.text.startswith("Plik:"):
            console.print(Text(entry.text, style="bold"))
        elif entry.kind == "done":
            pass  # czas i koszt są w podsumowaniu
        else:
            console.print(Text(indent + prefix + entry.text, style=style))
        if entry.kind == "step" and entry.text.startswith("[2/3]"):
            self._status = console.status("[cyan]czekam na odpowiedzi modelu...", spinner="dots")
            self._status.start()

    def stop(self) -> None:
        if self._status:
            self._status.stop()
            self._status = None


def print_summary(result: RunResult) -> None:
    s = result.summary
    table = Table(show_header=False, box=None, padding=(0, 2), pad_edge=False)
    table.add_column(style="grey70")
    table.add_column(justify="right", style="bold")
    table.add_row("Wierszy na wejściu", str(s.rows_in))
    table.add_row("Gotowe do importu", Text(str(s.ready), style="bold green"))
    table.add_row("Do ręcznej weryfikacji", Text(str(s.review), style="bold yellow"))
    table.add_row("  w tym błędy w danych", Text(str(s.review_data), style="yellow"))
    if s.skipped:
        table.add_row("Pominięte duplikaty", str(s.skipped))
    table.add_row("Wiersze poprawione automatycznie", str(s.fixed_rows))
    if s.in_master:
        table.add_row("Rozpoznane w kartotece", str(s.in_master))
    table.add_row("", "")
    table.add_row("Czas", f"{fmt.num(result.duration_s)} s")
    if result.mode == "ai":
        cost = f"{fmt.num(result.cost_usd, 4)} USD (≈ {fmt.num(result.cost_pln, 3)} zł)"
        table.add_row("Szacunkowy koszt AI", cost)
        table.add_row("Tokeny (wejście / wyjście)", f"{result.usage.prompt_tokens} / {result.usage.completion_tokens}")
    else:
        table.add_row("Szacunkowy koszt AI", "0 zł (tryb mock)")
    console.print()
    console.print(Panel(table, title=f"[bold]Podsumowanie: {result.source.name}", title_align="left",
                        subtitle=f"[grey62]wyniki w {_rel(result.outputs['csv'].parent)}/",
                        subtitle_align="left", border_style="grey50", padding=(1, 2), expand=False))


def _rel(path: Path) -> str:
    """Ścieżka względem bieżącego folderu, jeśli się da (krócej i czytelniej na nagraniu)."""
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def header(mode: str) -> None:
    console.print(Panel.fit(f"[bold]Walidator danych produktowych[/] [grey62]· import do ERP · v{__version__}[/]\n"
                            f"[grey62]tryb kategoryzacji: {mode}[/]", border_style="cyan"))


def process(path: Path, args: argparse.Namespace, config: AppConfig, settings: LLMSettings) -> RunResult:
    printer = LogPrinter()
    try:
        result = run_pipeline(path, config, settings, force_mock=args.mock, output_dir=args.out, sink=printer)
    finally:
        printer.stop()
    print_summary(result)
    return result


def mode_label(args: argparse.Namespace, settings: LLMSettings) -> str:
    if args.mock:
        return "mock (wymuszony flagą --mock)"
    if not settings.has_key:
        return "mock (brak LLM_API_KEY w .env)"
    return f"AI, model {settings.model}"


# --- komendy ---------------------------------------------------------------------


def cmd_run(args: argparse.Namespace) -> int:
    path = Path(args.file)
    if not path.exists():
        console.print(f"[red]Nie znaleziono pliku: {path}")
        return 2
    config = load_config(args.config)
    settings = load_llm_settings(config.ai)
    header(mode_label(args, settings))
    process(path, args, config, settings)
    return 0


def _wait_until_stable(path: Path, timeout: float = 10.0) -> bool:
    """Czeka, aż plik przestanie rosnąć (kopiowanie/zapis z Excela trwa chwilę)."""
    deadline = time.monotonic() + timeout
    last = -1
    while time.monotonic() < deadline:
        try:
            size = path.stat().st_size
            with path.open("rb"):
                pass
        except (FileNotFoundError, PermissionError):
            time.sleep(0.3)
            continue
        if size == last and size > 0:
            return True
        last = size
        time.sleep(0.4)
    return False


def _accepts(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS and not path.name.startswith(("~$", "."))


def cmd_watch(args: argparse.Namespace) -> int:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    inbox, processed = Path(args.inbox), Path(args.processed)
    inbox.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)
    pending: queue.Queue[Path] = queue.Queue()

    class Handler(FileSystemEventHandler):
        def on_created(self, event):
            if not event.is_directory:
                pending.put(Path(event.src_path))

        def on_moved(self, event):
            if not event.is_directory:
                pending.put(Path(event.dest_path))

    config = load_config(args.config)
    settings = load_llm_settings(config.ai)
    header(mode_label(args, settings))
    for existing in sorted(p for p in inbox.iterdir() if p.is_file()):
        pending.put(existing)
    observer = Observer()
    observer.schedule(Handler(), str(inbox), recursive=False)
    observer.start()
    console.print(f"[cyan]Obserwuję folder [bold]{_rel(inbox)}/[/bold]. Wrzuć plik .xlsx lub .csv (Ctrl+C kończy).\n")
    seen: set[Path] = set()
    try:
        while True:
            try:
                path = pending.get(timeout=0.5)
            except queue.Empty:
                continue
            if path in seen or not path.exists() or not _accepts(path):
                continue
            seen.add(path)
            if not _wait_until_stable(path):
                console.print(f"[yellow]Plik {path.name} nadal jest zapisywany, pomijam.")
                seen.discard(path)
                continue
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            try:
                process(path, args, config, settings)
                target = processed / f"{stamp}_{path.name}"
            except Exception as exc:  # obserwator ma działać dalej, nawet gdy jeden plik jest uszkodzony
                message = str(exc) if isinstance(exc, (MappingError, ConfigError)) else f"{type(exc).__name__}: {exc}"
                console.print(Panel(message, title="[red]Nie można przetworzyć pliku", border_style="red"))
                target = processed / f"{stamp}_BLAD_{path.name}"
            shutil.move(str(path), target)
            seen.discard(path)
            console.print(f"[grey62]Plik przeniesiony do {_rel(target)}\n")
            console.print(f"[cyan]Czekam na kolejny plik w {_rel(inbox)}/ ...")
    except KeyboardInterrupt:
        console.print("\n[grey62]Zakończono obserwowanie folderu.")
    finally:
        observer.stop()
        observer.join()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m walidator",
                                     description="Walidacja i przygotowanie danych produktowych do importu do ERP.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--mock", action="store_true", help="bez AI: kategoryzacja regułami słownikowymi (offline)")
    common.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH, help="plik mapowania (domyślnie config/mapping.yaml)")
    common.add_argument("--out", type=Path, default=None, help="folder wyników (domyślnie output/)")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", parents=[common], help="przetwórz jeden plik")
    run.add_argument("file", help="plik .xlsx lub .csv")
    run.set_defaults(func=cmd_run)
    watch = sub.add_parser("watch", parents=[common], help="obserwuj folder inbox/ i przetwarzaj nowe pliki")
    watch.add_argument("--inbox", default=str(PROJECT_ROOT / "inbox"), help="folder wejściowy")
    watch.add_argument("--processed", default=str(PROJECT_ROOT / "processed"), help="folder na przetworzone pliki")
    watch.set_defaults(func=cmd_watch)
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ConfigError, MappingError) as exc:
        console.print(Panel(str(exc), title="[red]Błąd", border_style="red"))
        return 2
