"""
Deduplicator: elimina duplicados exactos y casi-duplicados del dataset.

Dos pasadas:
    1. Exact match  — hash del texto clean normalizado (lowercase + strip)
    2. Fuzzy match  — difflib SequenceMatcher para similitud configurable

Diseño no destructivo: retorna (únicos, duplicados) para inspección.
La deduplicación cruzada entre categorías se realiza en joiner.py (paso final).
"""

import hashlib
from difflib import SequenceMatcher
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Defaults
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_FUZZY_THRESHOLD = 0.95   # ratio mínimo para considerar casi-duplicado
DEFAULT_FUZZY_MIN_CHARS = 20     # no comparar fuzzy textos más cortos que esto

# Fuzzy deshabilitado por default: O(n²) es prohibitivo en datasets grandes.
# Activar solo para datasets pequeños (<500 entradas) o con --fuzzy explícito.
DEFAULT_FUZZY_ENABLED = False


# ─────────────────────────────────────────────────────────────────────────────
# Funciones internas
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_key(text: str) -> str:
    """Normaliza texto para comparación exacta."""
    return text.lower().strip()


def _hash(text: str) -> str:
    return hashlib.md5(_normalize_key(text).encode()).hexdigest()


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


# ─────────────────────────────────────────────────────────────────────────────
# API pública
# ─────────────────────────────────────────────────────────────────────────────

def deduplicate(
    entries: list[dict],
    fuzzy: bool = DEFAULT_FUZZY_ENABLED,
    fuzzy_threshold: float = DEFAULT_FUZZY_THRESHOLD,
    fuzzy_min_chars: int = DEFAULT_FUZZY_MIN_CHARS,
    seen_hashes: Optional[set] = None,
) -> tuple[list[dict], list[dict]]:
    """
    Deduplica una lista de entradas por el campo 'clean'.

    El paso 1 (exact match por hash) siempre se ejecuta y es O(n).
    El paso 2 (fuzzy) es O(n²) — solo activar en datasets pequeños (<500 entradas).

    Args:
        entries:          Lista de entradas ya clasificadas y limpias.
        fuzzy:            Activar comparación fuzzy (default: False).
        fuzzy_threshold:  Ratio de similitud a partir del cual se considera duplicado.
        fuzzy_min_chars:  Longitud mínima para activar comparación fuzzy.
        seen_hashes:      Set externo de hashes ya vistos (para dedup entre categorías).
                          Se muta in-place: los nuevos hashes se añaden al set.

    Returns:
        (únicos, duplicados)
    """
    if seen_hashes is None:
        seen_hashes = set()

    unique: list[dict] = []
    dupes: list[dict] = []
    unique_texts: list[str] = []  # solo usado en modo fuzzy

    for entry in entries:
        text = entry.get("clean", "")
        h = _hash(text)

        # — Paso 1: exact match (siempre, O(1) por hash)
        if h in seen_hashes:
            dupes.append(entry)
            continue

        # — Paso 2: fuzzy match (opt-in, O(n) por entrada)
        if fuzzy and len(text) >= fuzzy_min_chars:
            is_fuzzy_dupe = False
            for existing in unique_texts:
                # Early-exit: si las longitudes difieren >30%, imposible llegar al threshold
                if abs(len(text) - len(existing)) / max(len(text), len(existing)) > 0.3:
                    continue
                if _similarity(text, existing) >= fuzzy_threshold:
                    is_fuzzy_dupe = True
                    break
            if is_fuzzy_dupe:
                dupes.append(entry)
                continue

        seen_hashes.add(h)
        unique.append(entry)
        if fuzzy and len(text) >= fuzzy_min_chars:
            unique_texts.append(text)

    return unique, dupes


def deduplicate_sets(
    sets: dict[str, list[dict]],
    fuzzy: bool = DEFAULT_FUZZY_ENABLED,
    fuzzy_threshold: float = DEFAULT_FUZZY_THRESHOLD,
    fuzzy_min_chars: int = DEFAULT_FUZZY_MIN_CHARS,
    cross_category: bool = False,
) -> tuple[dict[str, list[dict]], dict[str, list[dict]]]:
    """
    Deduplica todos los sets del curator.

    Args:
        sets:             Dict {categoría: [entradas]}.
        fuzzy_threshold:  Threshold fuzzy.
        fuzzy_min_chars:  Mínimo de chars para fuzzy.
        cross_category:   Si True, comparte el set de hashes entre categorías
                          (deduplicación cruzada). Para uso interno del joiner.

    Returns:
        (passed_sets, duplicate_sets) — misma estructura de dict.
    """
    passed: dict[str, list[dict]] = {}
    dupes_out: dict[str, list[dict]] = {}

    shared_hashes: set = set() if cross_category else None  # type: ignore[assignment]

    for cat, entries in sets.items():
        hashes = shared_hashes if cross_category else set()
        unique, dupes = deduplicate(
            entries,
            fuzzy=fuzzy,
            fuzzy_threshold=fuzzy_threshold,
            fuzzy_min_chars=fuzzy_min_chars,
            seen_hashes=hashes,
        )
        passed[cat] = unique
        dupes_out[cat] = dupes

    return passed, dupes_out
