"""
Stats: estadísticas del dataset curado para mostrar en GUI y CLI.

Métricas calculadas:
    - Total de entradas por categoría
    - Distribución de longitudes (chars): min, max, media, p50, p90, p95
    - Vocabulario único del personaje (tokens únicos en campo 'clean')
    - Detección de desbalances entre categorías
    - Resumen general del pipeline (entrada → salida)
"""

import re
from statistics import mean, median, quantiles


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    """Tokenización simple por palabras (lowercase)."""
    return re.findall(r"[a-záéíóúüñA-ZÁÉÍÓÚÜÑ']+", text.lower())


def _percentile(data: list[float], p: float) -> float:
    """Percentil p (0–100) de una lista ordenada."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = (p / 100) * (len(sorted_data) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(sorted_data) - 1)
    return sorted_data[lo] + (sorted_data[hi] - sorted_data[lo]) * (idx - lo)


def _length_stats(texts: list[str]) -> dict:
    """Estadísticas de longitud para una lista de textos."""
    if not texts:
        return {"count": 0, "min": 0, "max": 0, "mean": 0, "p50": 0, "p90": 0, "p95": 0}
    lengths = [len(t) for t in texts]
    return {
        "count": len(lengths),
        "min":   min(lengths),
        "max":   max(lengths),
        "mean":  round(mean(lengths), 1),
        "p50":   round(_percentile(lengths, 50), 1),
        "p90":   round(_percentile(lengths, 90), 1),
        "p95":   round(_percentile(lengths, 95), 1),
    }


# ─────────────────────────────────────────────────────────────────────────────
# API pública
# ─────────────────────────────────────────────────────────────────────────────

def compute(
    sets: dict[str, list[dict]],
    original_count: int = 0,
    rejected_count: int = 0,
    duplicate_count: int = 0,
) -> dict:
    """
    Calcula estadísticas completas del dataset curado.

    Args:
        sets:             Dict {categoría: [entradas]} del pipeline curator.
        original_count:   Total de entradas antes de curar (para % retención).
        rejected_count:   Entradas eliminadas por quality_scorer.
        duplicate_count:  Entradas eliminadas por deduplicator.

    Returns:
        Dict con todas las métricas estructuradas.
    """
    all_texts: list[str] = []
    all_vocab: set[str] = set()
    per_category: dict[str, dict] = {}

    for cat, entries in sets.items():
        texts = [e.get("clean", "") for e in entries if e.get("clean")]
        all_texts.extend(texts)

        vocab: set[str] = set()
        for t in texts:
            vocab.update(_tokenize(t))
        all_vocab.update(vocab)

        per_category[cat] = {
            "count":         len(entries),
            "length_stats":  _length_stats(texts),
            "unique_tokens": len(vocab),
        }

    total_kept = sum(len(v) for v in sets.values())

    stats: dict = {
        "pipeline": {
            "original":   original_count,
            "rejected":   rejected_count,
            "duplicates": duplicate_count,
            "kept":       total_kept,
            "retention":  round(total_kept / original_count, 3) if original_count else 0.0,
        },
        "total": {
            "entries":       total_kept,
            "unique_tokens": len(all_vocab),
            "length_stats":  _length_stats(all_texts),
        },
        "per_category": per_category,
        "balance":       _balance_report(per_category, total_kept),
    }

    return stats


def _balance_report(per_category: dict, total: int) -> dict:
    """
    Detecta desbalances entre categorías.
    Retorna proporciones y una advertencia si alguna categoría
    representa menos del 5% del total (posible subrepresentación).
    """
    if total == 0:
        return {}

    proportions: dict[str, float] = {}
    warnings: list[str] = []

    for cat, data in per_category.items():
        count = data["count"]
        prop = round(count / total, 3)
        proportions[cat] = prop
        if 0 < count < total * 0.05:
            warnings.append(f"{cat} representa solo {prop:.0%} del dataset")

    return {"proportions": proportions, "warnings": warnings}


def format_report(stats: dict) -> str:
    """
    Genera un reporte de texto legible para mostrar en CLI o GUI.
    """
    lines = []

    # — Pipeline
    p = stats["pipeline"]
    if p["original"]:
        lines.append("=== Pipeline ===")
        lines.append(f"  Original:    {p['original']:>6}")
        lines.append(f"  Rechazadas:  {p['rejected']:>6}")
        lines.append(f"  Duplicadas:  {p['duplicates']:>6}")
        lines.append(f"  Retenidas:   {p['kept']:>6}  ({p['retention']:.0%})")

    # — Total
    t = stats["total"]
    lines.append("\n=== Total ===")
    lines.append(f"  Entradas:        {t['entries']}")
    lines.append(f"  Tokens únicos:   {t['unique_tokens']}")
    ls = t["length_stats"]
    lines.append(f"  Longitud media:  {ls['mean']} chars")
    lines.append(f"  p50={ls['p50']}  p90={ls['p90']}  p95={ls['p95']}  max={ls['max']}")

    # — Por categoría
    lines.append("\n=== Por categoría ===")
    for cat, data in stats["per_category"].items():
        if data["count"] > 0:
            ls = data["length_stats"]
            lines.append(f"  {cat:<30} {data['count']:>5} entradas  "
                         f"vocab={data['unique_tokens']}  "
                         f"media={ls['mean']} chars")

    # — Balance
    b = stats["balance"]
    if b.get("warnings"):
        lines.append("\n⚠ Desbalances detectados:")
        for w in b["warnings"]:
            lines.append(f"  - {w}")

    return "\n".join(lines)
