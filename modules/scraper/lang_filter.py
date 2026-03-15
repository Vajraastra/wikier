"""
Lang Filter: detecta y filtra páginas wikitext por idioma objetivo.

Se aplica ANTES del parser para descartar páginas en idiomas no deseados.
El idioma objetivo se configura por perfil JSON (campo "language").

Requiere: langdetect (opcional — si no está instalado, el filtro se desactiva
y todas las páginas pasan sin importar el idioma).
"""
import re

try:
    from langdetect import detect, LangDetectException
    _HAS_LANGDETECT = True
except ImportError:
    _HAS_LANGDETECT = False


# ─────────────────────────────────────────────────────────────────────────────
# Limpieza de markup
# ─────────────────────────────────────────────────────────────────────────────

def _clean_for_detection(wikitext: str) -> str:
    """
    Extrae texto legible del wikitext para mejorar la precisión de langdetect.

    Elimina templates, wikilinks, markup de formato y encabezados de sección.
    Trunca a 3000 caracteres para mantener detección rápida.
    """
    # Eliminar templates: {{...}}
    text = re.sub(r'\{\{[^}]*\}\}', '', wikitext, flags=re.DOTALL)
    # Convertir wikilinks: [[Texto|Display]] → Display, [[Display]] → Display
    text = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]*)\]\]', r'\1', text)
    # Eliminar negrita/cursiva
    text = re.sub(r"'{2,}", '', text)
    # Eliminar tags HTML
    text = re.sub(r'<[^>]+>', '', text)
    # Eliminar encabezados == ... ==
    text = re.sub(r'=+[^=]+=+', '', text)
    # Colapsar whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text[:3000]


# ─────────────────────────────────────────────────────────────────────────────
# API pública
# ─────────────────────────────────────────────────────────────────────────────

def detect_language(wikitext: str) -> str:
    """
    Detecta el idioma del wikitext crudo.

    Returns:
        Código ISO 639-1 ('en', 'es', 'fr', etc.) o 'unknown' si no se puede
        determinar (langdetect no instalado, texto muy corto, error).
    """
    if not _HAS_LANGDETECT:
        return 'unknown'

    sample = _clean_for_detection(wikitext)
    if len(sample) < 50:
        return 'unknown'

    try:
        return detect(sample)
    except LangDetectException:
        return 'unknown'


def matches_language(wikitext: str, target_lang: str) -> bool:
    """
    Verifica si el wikitext corresponde al idioma objetivo del perfil.

    Comportamiento conservador: en caso de duda, NO descarta la página.

    - Si target_lang es 'any' o vacío → True (filtro desactivado).
    - Si langdetect no está instalado → True (no puede filtrar).
    - Si la detección retorna 'unknown' → True (no descartar por error).
    - Si el idioma detectado coincide con target_lang → True.

    Args:
        wikitext:    Wikitext crudo de la página.
        target_lang: Código ISO 639-1 ('en', 'es', etc.) o 'any'.

    Returns:
        True si la página debe incluirse en el dataset.
    """
    if not target_lang or target_lang.lower() == 'any':
        return True

    detected = detect_language(wikitext)
    if detected == 'unknown':
        return True  # Conservador: en caso de duda, no filtrar

    return detected == target_lang
