"""
Cleaner: normaliza markup residual y encoding en texto de diálogo.

Operaciones (en orden de aplicación):
    1. Strip HTML — elimina tags HTML manteniendo el texto interior
    2. Normalización Unicode — NFC para consistencia de caracteres
    3. Normalización de puntuación — unifica variantes de guiones y ellipsis
    4. Espacios redundantes — colapsa múltiples espacios/tabs en uno
    5. Strip final — elimina espacios al inicio y final

Diseño no destructivo: solo normaliza, nunca descarta contenido real.
"""

import re
import unicodedata


# ─────────────────────────────────────────────────────────────────────────────
# Sustituciones de puntuación (orden importa)
# ─────────────────────────────────────────────────────────────────────────────

# Variantes de ellipsis → "..."
_ELLIPSIS_VARIANTS = [
    ("\u2026", "..."),   # carácter ellipsis U+2026
]

# Variantes de guión largo → "—"  (em dash, sin cambiar hyphens de palabras)
_DASH_VARIANTS = [
    ("\u2013", "—"),     # en dash U+2013
    ("\u2014", "—"),     # em dash U+2014 (ya es —, re-escritura por consistencia)
]

# Comillas tipográficas → ASCII
_QUOTE_VARIANTS = [
    ("\u2018", "'"),     # left single quotation
    ("\u2019", "'"),     # right single quotation / apostrophe tipográfico
    ("\u201C", '"'),     # left double quotation
    ("\u201D", '"'),     # right double quotation
]

# Espacio sin ruptura → espacio normal
_SPACE_VARIANTS = [
    ("\u00A0", " "),     # non-breaking space
    ("\u202F", " "),     # narrow no-break space
]


# ─────────────────────────────────────────────────────────────────────────────
# Pasos de limpieza
# ─────────────────────────────────────────────────────────────────────────────

def _strip_html(text: str) -> str:
    """
    Elimina tags HTML conservando el texto interior.
    Maneja correctamente tags anidados.
    Ejemplo: '<span title="nota">texto visible</span>' → 'texto visible'
    """
    return re.sub(r"<[^>]+>", "", text)


def _normalize_unicode(text: str) -> str:
    """Normaliza a forma NFC para consistencia de caracteres compuestos."""
    return unicodedata.normalize("NFC", text)


def _normalize_punctuation(text: str) -> str:
    """Unifica variantes tipográficas de puntuación a ASCII estándar."""
    for variant, replacement in (
        _ELLIPSIS_VARIANTS
        + _DASH_VARIANTS
        + _QUOTE_VARIANTS
        + _SPACE_VARIANTS
    ):
        text = text.replace(variant, replacement)
    return text


def _collapse_spaces(text: str) -> str:
    """Colapsa múltiples espacios/tabs en un único espacio."""
    return re.sub(r"[ \t]{2,}", " ", text).strip()


# ─────────────────────────────────────────────────────────────────────────────
# API pública
# ─────────────────────────────────────────────────────────────────────────────

def clean(text: str, extra_patterns: list[tuple[str, str]] | None = None) -> str:
    """
    Aplica el pipeline completo de limpieza a un string de texto.

    Args:
        text:             Texto a limpiar (campo 'clean' del classifier).
        extra_patterns:   Pares (regex, reemplazo) adicionales configurables
                          por perfil. Se aplican DESPUÉS de los pasos estándar.

    Returns:
        Texto normalizado.
    """
    text = _strip_html(text)
    text = _normalize_unicode(text)
    text = _normalize_punctuation(text)
    text = _collapse_spaces(text)

    if extra_patterns:
        for pattern, replacement in extra_patterns:
            text = re.sub(pattern, replacement, text)
        text = _collapse_spaces(text)

    return text


def clean_dataset(
    sets: dict[str, list[dict]],
    extra_patterns: list[tuple[str, str]] | None = None,
) -> dict[str, list[dict]]:
    """
    Aplica clean() al campo 'clean' de todas las entradas de los sets.

    Opera in-place sobre las entradas (muta el dict).
    Retorna el mismo dict para compatibilidad con el pipeline.

    Args:
        sets:            Dict {categoría: [entradas]} del classify_dataset().
        extra_patterns:  Patrones adicionales por perfil.
    """
    for entries in sets.values():
        for entry in entries:
            if entry.get("clean"):
                entry["clean"] = clean(entry["clean"], extra_patterns)
    return sets
