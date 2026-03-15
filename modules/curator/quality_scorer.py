"""
Quality Scorer: evalúa y filtra entradas del dataset por calidad.

Criterios:
    1. Longitud mínima — descarta líneas demasiado cortas
    2. TTR (type-token ratio) — diversidad de vocabulario
    3. Penalización por markup residual — markup no limpiado reduce el score
    4. Penalización por repetición — misma palabra repetida muchas veces

El scorer NO descarta silenciosamente. Retorna el resultado con score y razón,
y una lista separada de rechazados para inspección.
"""

import re
from dataclasses import dataclass
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Defaults
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_MIN_CHARS = 10          # longitud mínima del texto clean (caracteres)
DEFAULT_TTR_THRESHOLD = 0.3     # ratio tipo/token mínimo (0–1)
DEFAULT_MAX_REPEAT_RATIO = 0.5  # máximo ratio de repetición de una sola palabra


# ─────────────────────────────────────────────────────────────────────────────
# Tipos de datos
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ScoreResult:
    """Resultado del scoring de una entrada."""
    passed: bool
    score: float          # 0.0 – 1.0
    reasons: list[str]    # por qué pasó o fue rechazada


# ─────────────────────────────────────────────────────────────────────────────
# Cálculo de métricas
# ─────────────────────────────────────────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    """Tokenización simple por palabras (lowercase, sin puntuación)."""
    return re.findall(r"[a-záéíóúüñA-ZÁÉÍÓÚÜÑ']+", text.lower())


def _ttr(tokens: list[str]) -> float:
    """Type-Token Ratio: tipos únicos / total tokens. Retorna 1.0 si < 3 tokens."""
    if len(tokens) < 3:
        return 1.0  # frases muy cortas no se penalizan por TTR
    return len(set(tokens)) / len(tokens)


def _max_word_repeat_ratio(tokens: list[str]) -> float:
    """Ratio del token más repetido respecto al total."""
    if not tokens:
        return 0.0
    counts: dict[str, int] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1
    return max(counts.values()) / len(tokens)


def _has_residual_markup(text: str) -> bool:
    """Detecta markup HTML o wiki que no fue limpiado."""
    return bool(re.search(r"<[a-z]+|{{|\[\[", text, re.IGNORECASE))


# ─────────────────────────────────────────────────────────────────────────────
# API pública
# ─────────────────────────────────────────────────────────────────────────────

def score(
    text: str,
    min_chars: int = DEFAULT_MIN_CHARS,
    ttr_threshold: float = DEFAULT_TTR_THRESHOLD,
    max_repeat_ratio: float = DEFAULT_MAX_REPEAT_RATIO,
) -> ScoreResult:
    """
    Evalúa la calidad de un texto de diálogo limpio.

    Args:
        text:              Campo 'clean' después de aplicar cleaner.py.
        min_chars:         Longitud mínima aceptable en caracteres.
        ttr_threshold:     TTR mínimo aceptable (diversidad de vocabulario).
        max_repeat_ratio:  Ratio máximo de repetición de una palabra.

    Returns:
        ScoreResult con passed=True/False, score 0–1, y lista de razones.
    """
    reasons: list[str] = []
    penalties: list[float] = []

    # — 1. Longitud mínima
    if len(text) < min_chars:
        return ScoreResult(
            passed=False,
            score=0.0,
            reasons=[f"muy corta ({len(text)} chars < {min_chars})"],
        )

    # — 2. Markup residual
    if _has_residual_markup(text):
        penalties.append(0.4)
        reasons.append("markup residual detectado")

    # — 3. TTR
    tokens = _tokenize(text)
    ttr_val = _ttr(tokens)
    if ttr_val < ttr_threshold:
        penalties.append(0.3)
        reasons.append(f"TTR bajo ({ttr_val:.2f} < {ttr_threshold})")

    # — 4. Repetición de palabra dominante
    repeat = _max_word_repeat_ratio(tokens)
    if repeat > max_repeat_ratio:
        penalties.append(0.2)
        reasons.append(f"palabra repetida ({repeat:.0%} del texto)")

    # — Score final
    score_val = max(0.0, 1.0 - sum(penalties))
    passed = score_val > 0.0 and not reasons or all(
        "markup" not in r for r in reasons
    )
    # Falla hard solo si hay markup residual (indica pipeline incompleta)
    if _has_residual_markup(text):
        passed = False

    if passed and not reasons:
        reasons.append("ok")

    return ScoreResult(passed=passed, score=round(score_val, 3), reasons=reasons)


def score_dataset(
    sets: dict[str, list[dict]],
    min_chars: int = DEFAULT_MIN_CHARS,
    ttr_threshold: float = DEFAULT_TTR_THRESHOLD,
    max_repeat_ratio: float = DEFAULT_MAX_REPEAT_RATIO,
) -> tuple[dict[str, list[dict]], dict[str, list[dict]]]:
    """
    Aplica scoring a todos los sets y separa aprobados de rechazados.

    Retorna:
        (passed_sets, rejected_sets) — misma estructura de dict por categoría.
        Cada entrada rechazada incluye 'score_reasons' y 'score' para inspección.
    """
    passed: dict[str, list[dict]] = {cat: [] for cat in sets}
    rejected: dict[str, list[dict]] = {cat: [] for cat in sets}

    for cat, entries in sets.items():
        for entry in entries:
            result = score(
                entry.get("clean", ""),
                min_chars=min_chars,
                ttr_threshold=ttr_threshold,
                max_repeat_ratio=max_repeat_ratio,
            )
            entry["score"] = result.score
            entry["score_reasons"] = result.reasons
            if result.passed:
                passed[cat].append(entry)
            else:
                rejected[cat].append(entry)

    return passed, rejected


def score_summary(
    passed: dict[str, list[dict]],
    rejected: dict[str, list[dict]],
) -> dict:
    """
    Genera un resumen legible del scoring para mostrar en la GUI o CLI.
    """
    summary = {}
    for cat in passed:
        total = len(passed[cat]) + len(rejected[cat])
        summary[cat] = {
            "passed": len(passed[cat]),
            "rejected": len(rejected[cat]),
            "total": total,
            "pass_rate": round(len(passed[cat]) / total, 3) if total else 0.0,
        }
    return summary
