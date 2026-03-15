"""
Workers de QThread para indexación y extracción de diálogos.

IndexWorker  — construye el índice de speakers (puede tardar minutos).
ExtractWorker — extrae los pares de diálogo para un personaje específico.

Ambos emiten señales de progreso que la GUI conecta sin bloquear el UI thread.
"""
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from modules.scraper.fetcher import get_wikitext, setup_cache
from modules.scraper.parser import parse_dialogue
from modules.scraper.filter import filter_character
from modules.scraper.discovery import build_index, load_index, delete_index
from modules.scraper.exporter import export
from modules.scraper.config import OUTPUT_DIR


# ─────────────────────────────────────────────────────────────────────────────
# Index Worker
# ─────────────────────────────────────────────────────────────────────────────

class IndexWorker(QThread):
    """
    Construye (o carga desde cache) el índice de speakers de un wiki.

    Señales:
        progress(current, total, message) — actualización de progreso.
        finished(index)                   — índice completo al terminar.
        error(message)                    — mensaje de error si falla.
    """

    progress = Signal(int, int, str)
    finished = Signal(dict)
    error    = Signal(str)

    def __init__(
        self,
        base_url:    str,
        categories:  list[str],
        rate_limit:  float,
        format_hint: str  = "auto",
        rebuild:     bool = False,
        sample:      int  = 0,
    ):
        super().__init__()
        self.base_url    = base_url
        self.categories  = categories
        self.rate_limit  = rate_limit
        self.format_hint = format_hint
        self.rebuild     = rebuild
        self.sample      = sample

    def run(self) -> None:
        try:
            setup_cache()

            # Borrar índice si se pidió rebuild
            if self.rebuild:
                delete_index(self.base_url, self.categories)

            # Si no hay rebuild y existe el índice, cargarlo directamente
            if not self.rebuild:
                index = load_index(self.base_url, self.categories)
                if index:
                    n_pages    = len(index["pages"])
                    n_speakers = len(index["speakers"])
                    self.progress.emit(
                        n_pages, n_pages,
                        f"Índice cargado desde cache ({n_pages} páginas, {n_speakers} personajes)"
                    )
                    self.finished.emit(index)
                    return

            # Construir índice desde cero (modo sample o completo)
            if self.sample > 0:
                index = self._build_sample_index()
            else:
                index = build_index(
                    self.base_url,
                    self.categories,
                    self.rate_limit,
                    self.format_hint,
                    on_progress=self._on_progress,
                )

            self.finished.emit(index)

        except Exception as exc:
            self.error.emit(str(exc))

    # ── helpers ───────────────────────────────────────────────────────────────

    def _on_progress(self, current: int, total: int, message: str) -> None:
        """Bridge entre el callback de build_index y la señal Qt."""
        self.progress.emit(current, total, message)

    def _build_sample_index(self) -> dict:
        """Construye un índice parcial con N páginas. No se guarda en disco."""
        from collections import Counter
        from scraper.walker import walk_category

        all_titles: list[str] = []
        for cat in self.categories:
            for title in walk_category(self.base_url, cat, self.rate_limit):
                all_titles.append(title)
                if len(all_titles) >= self.sample:
                    break
            if len(all_titles) >= self.sample:
                break

        speaker_counts: Counter = Counter()
        pages_ok: list[str] = []
        total = len(all_titles)

        for i, title in enumerate(all_titles, 1):
            self.progress.emit(i, total, title)
            wikitext = get_wikitext(self.base_url, title, self.rate_limit)
            if not wikitext:
                continue
            lines, fmt = parse_dialogue(wikitext, self.format_hint)
            if fmt != "unknown":
                for line in lines:
                    if line.speaker and not line.is_action:
                        speaker_counts[line.speaker] += 1
                pages_ok.append(title)

        return {
            "base_url":      self.base_url,
            "categories":    self.categories,
            "pages":         pages_ok,
            "speakers":      dict(speaker_counts.most_common()),
            "unrecognized":  [],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Extract Worker
# ─────────────────────────────────────────────────────────────────────────────

class ExtractWorker(QThread):
    """
    Extrae los pares de diálogo de un personaje específico.

    Señales:
        progress(current, total, page_title) — actualización de progreso.
        finished(pairs, output_path)          — pares extraídos y ruta del JSONL.
        error(message)                        — mensaje de error si falla.
    """

    progress = Signal(int, int, str)
    finished = Signal(list, str)
    error    = Signal(str)

    def __init__(
        self,
        index:           dict,
        character:       str,
        aliases:         list[str],
        context_window:  int,
        include_actions: bool,
        rate_limit:      float,
        format_hint:     str       = "auto",
        formats:         list[str] | None = None,
    ):
        super().__init__()
        self.index           = index
        self.character       = character
        self.aliases         = aliases
        self.context_window  = context_window
        self.include_actions = include_actions
        self.rate_limit      = rate_limit
        self.format_hint     = format_hint
        self.formats         = formats or ["jsonl"]

    def run(self) -> None:
        try:
            pages   = self.index["pages"]
            total   = len(pages)
            all_pairs: list[dict] = []

            for i, title in enumerate(pages, 1):
                self.progress.emit(i, total, title)
                wikitext = get_wikitext(
                    self.index["base_url"], title, self.rate_limit
                )
                if not wikitext:
                    continue

                lines, fmt = parse_dialogue(wikitext, self.format_hint)
                if fmt == "unknown":
                    continue

                pairs = filter_character(
                    lines,
                    target=self.character,
                    aliases=self.aliases,
                    context_window=self.context_window,
                    include_actions=self.include_actions,
                )
                for pair in pairs:
                    pair["source_page"] = title
                all_pairs.extend(pairs)

            # Exportar a output/<personaje>/<personaje>_dataset.<ext>
            char_slug  = self.character.replace(" ", "_")
            out_dir    = OUTPUT_DIR / char_slug
            out_path   = str(out_dir / f"{char_slug}_dataset")

            if all_pairs:
                export(all_pairs, out_path, self.formats)

            self.finished.emit(all_pairs, str(out_dir))

        except Exception as exc:
            self.error.emit(str(exc))
