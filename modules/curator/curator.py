"""
Curator: orquestador del pipeline de curación de datasets.

Ejecuta en orden:
    1. classify     — clasifica líneas en categorías (classifier.py)
    2. clean        — normaliza markup y encoding (cleaner.py)
    3. score        — filtra por calidad (quality_scorer.py)
    4. deduplicate  — elimina duplicados (deduplicator.py)
    5. analyze      — filtra por longitud de tokens (token_analyzer.py)  [opcional]
    6. build_prompt — inyecta system prompt (system_prompt_builder.py)   [opcional]
    7. format       — convierte al formato final (formatter.py)
    8. stats        — genera estadísticas del resultado (stats.py)

Pasos opcionales se activan según la config. El progreso se reporta via
callback para integración con la GUI (QThread) y la CLI.

Uso mínimo:
    result = curate(entries, profile, character, CuratorConfig())

Uso con callback (GUI):
    def on_progress(step, msg):
        worker.progress.emit(step, msg)
    result = curate(entries, profile, character, config, progress_cb=on_progress)
"""

from dataclasses import dataclass, field
from typing import Callable, Optional

from modules.curator import (
    classifier,
    cleaner,
    quality_scorer,
    deduplicator,
    formatter,
    stats,
    system_prompt_builder,
)


# ─────────────────────────────────────────────────────────────────────────────
# Configuración del pipeline
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CuratorConfig:
    """Parámetros de configuración del pipeline curator."""

    # — Classifier
    action_pattern: Optional[str] = None       # None → usa default
    thought_patterns: Optional[list[str]] = None

    # — Cleaner
    extra_clean_patterns: Optional[list[tuple[str, str]]] = None  # [(regex, repl), ...]

    # — Quality scorer
    min_chars: int = 10
    ttr_threshold: float = 0.3
    max_repeat_ratio: float = 0.5

    # — Deduplicator
    fuzzy_dedup: bool = False
    fuzzy_threshold: float = 0.95

    # — Token analyzer (opcional)
    token_analyzer_enabled: bool = False
    token_preset: str = "small"           # tiny|small|medium|large
    tokenizer_name: Optional[str] = None  # None → cuenta chars como proxy

    # — System prompt (opcional)
    system_prompt_enabled: bool = True
    system_prompt_template: Optional[str] = None   # None → auto-selección
    system_prompt_extra_vars: Optional[dict] = None
    # Ratio de entradas que recibirán system prompt (0.0–1.0).
    # 1.0 = todas; 0.7 = 70% con prompt, 30% sin prompt.
    # Mezclar es beneficioso: el modelo aprende a responder con y sin instrucciones.
    system_prompt_ratio: float = 1.0
    # Seed para reproducibilidad del ratio (None = no reproducible)
    system_prompt_seed: Optional[int] = 42

    # — Formatter
    output_format: str = "chatml"         # chatml|alpaca|sharegpt|jsonl_raw

    # — Categorías a incluir en el output final
    # action_only y thought_only se archivan por defecto (no van al output)
    include_categories: list[str] = field(default_factory=lambda: [
        "dialogue_clean",
        "dialogue_mixed_thought",
        "dialogue_mixed_action",
    ])


# ─────────────────────────────────────────────────────────────────────────────
# Resultado del pipeline
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CuratorResult:
    """Resultado completo del pipeline curator."""
    formatted:   dict[str, list[dict]]   # sets formateados listos para exportar
    archived:    dict[str, list[dict]]   # thought_only, action_only, overlength
    stats:       dict                    # métricas del pipeline
    stats_report: str                    # reporte legible


# ─────────────────────────────────────────────────────────────────────────────
# Orquestador
# ─────────────────────────────────────────────────────────────────────────────

def curate(
    entries: list[dict],
    profile: dict,
    character: str,
    config: CuratorConfig,
    progress_cb: Optional[Callable[[int, str], None]] = None,
) -> CuratorResult:
    """
    Ejecuta el pipeline completo de curación sobre una lista de entradas.

    Args:
        entries:      Lista de dicts {instruction, output} del exporter del scraper.
        profile:      Dict del perfil JSON del wiki (miraculousladybug.json, etc.).
        character:    Nombre del personaje objetivo.
        config:       Parámetros de configuración del pipeline.
        progress_cb:  Callback opcional (step: int, message: str).
                      step va de 0 a 100 (porcentaje aproximado).

    Returns:
        CuratorResult con los sets formateados, archivados y estadísticas.
    """

    def _report(step: int, msg: str) -> None:
        if progress_cb:
            progress_cb(step, msg)

    original_count = len(entries)

    # ── Paso 1: Clasificar ────────────────────────────────────────────────────
    _report(10, "Clasificando líneas...")
    sets = classifier.classify_dataset(
        entries,
        action_pattern=config.action_pattern,
        thought_patterns=config.thought_patterns,
    )

    # ── Paso 2: Limpiar ───────────────────────────────────────────────────────
    _report(20, "Limpiando markup residual...")
    cleaner.clean_dataset(sets, extra_patterns=config.extra_clean_patterns)

    # ── Paso 3: Quality scoring ───────────────────────────────────────────────
    _report(35, "Aplicando filtro de calidad...")
    passed, rejected = quality_scorer.score_dataset(
        sets,
        min_chars=config.min_chars,
        ttr_threshold=config.ttr_threshold,
        max_repeat_ratio=config.max_repeat_ratio,
    )
    rejected_count = sum(len(v) for v in rejected.values())

    # ── Paso 4: Deduplicar ────────────────────────────────────────────────────
    _report(50, "Eliminando duplicados...")
    unique, dupes = deduplicator.deduplicate_sets(
        passed,
        fuzzy=config.fuzzy_dedup,
        fuzzy_threshold=config.fuzzy_threshold,
    )
    dupe_count = sum(len(v) for v in dupes.values())

    # ── Paso 5: Token analyzer (opcional) ────────────────────────────────────
    if config.token_analyzer_enabled:
        _report(60, f"Analizando tokens (preset: {config.token_preset})...")
        from modules.curator import token_analyzer
        unique, overlength = token_analyzer.filter_sets(
            unique,
            preset=config.token_preset,
            tokenizer_name=config.tokenizer_name,
        )
    else:
        overlength: dict[str, list[dict]] = {}

    # ── Paso 6: System prompt (opcional) ─────────────────────────────────────
    if config.system_prompt_enabled:
        ratio_pct = int(config.system_prompt_ratio * 100)
        _report(70, f"Construyendo system prompt ({ratio_pct}% de entradas)...")
        system_prompt = system_prompt_builder.build(
            profile,
            character,
            template=config.system_prompt_template,
            extra_vars=config.system_prompt_extra_vars,
        )
        system_prompt_builder.inject_system_prompt(
            unique,
            system_prompt,
            ratio=config.system_prompt_ratio,
            seed=config.system_prompt_seed,
        )

    # ── Paso 7: Formatear ─────────────────────────────────────────────────────
    _report(80, f"Formateando ({config.output_format})...")

    # Separar sets a incluir en el output vs archivar
    active_sets = {
        cat: entries
        for cat, entries in unique.items()
        if cat in config.include_categories
    }
    archived_sets = {
        cat: entries
        for cat, entries in unique.items()
        if cat not in config.include_categories
    }
    if overlength:
        archived_sets["overlength"] = [
            e for v in overlength.values() for e in v
        ]

    formatted = formatter.format_sets(active_sets, fmt=config.output_format)

    # ── Paso 8: Estadísticas ──────────────────────────────────────────────────
    _report(95, "Calculando estadísticas...")
    pipeline_stats = stats.compute(
        active_sets,
        original_count=original_count,
        rejected_count=rejected_count,
        duplicate_count=dupe_count,
    )
    report = stats.format_report(pipeline_stats)

    _report(100, "Curación completada.")

    return CuratorResult(
        formatted=formatted,
        archived=archived_sets,
        stats=pipeline_stats,
        stats_report=report,
    )
