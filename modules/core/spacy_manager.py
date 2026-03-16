"""
SpacyManager: gestión de modelos spaCy multilingüe.

Permite verificar, descargar y cargar modelos para distintos idiomas.
Solo usa modelos 'sm' (~12-30 MB) — suficientes para dependency parsing.
"""
from __future__ import annotations

import subprocess
import sys
from typing import Callable

# ─────────────────────────────────────────────────────────────────────────────
# Mapa ISO 639-1 → (model_name, display_name, size_mb)
# ─────────────────────────────────────────────────────────────────────────────

_MODELS: dict[str, tuple[str, str, int]] = {
    "en": ("en_core_web_sm",  "English",     12),
    "es": ("es_core_news_sm", "Español",     12),
    "fr": ("fr_core_news_sm", "Français",    15),
    "de": ("de_core_news_sm", "Deutsch",     13),
    "it": ("it_core_news_sm", "Italiano",    14),
    "pt": ("pt_core_news_sm", "Português",   15),
    "nl": ("nl_core_news_sm", "Nederlands",  13),
    "el": ("el_core_news_sm", "Ελληνικά",    14),
    "nb": ("nb_core_news_sm", "Norsk",       14),
    "da": ("da_core_news_sm", "Dansk",       15),
    "pl": ("pl_core_news_sm", "Polski",      14),
    "ro": ("ro_core_news_sm", "Română",      14),
    "ru": ("ru_core_news_sm", "Русский",     15),
    "uk": ("uk_core_news_sm", "Українська",  14),
    "ja": ("ja_core_news_sm", "日本語",       13),
    "zh": ("zh_core_web_sm",  "中文",         30),
    "ca": ("ca_core_news_sm", "Català",      12),
    "lt": ("lt_core_news_sm", "Lietuvių",    12),
    "hr": ("hr_core_news_sm", "Hrvatski",    12),
    "sl": ("sl_core_news_sm", "Slovenščina", 12),
    "sk": ("sk_core_news_sm", "Slovenčina",  12),
    "mk": ("mk_core_news_sm", "Македонски",  12),
}

ProgressCb = Callable[[int, str], None]   # (percent 0-100, message)


# ─────────────────────────────────────────────────────────────────────────────
# API pública
# ─────────────────────────────────────────────────────────────────────────────

def list_available() -> list[dict]:
    """
    Lista todos los idiomas soportados con su estado de instalación.

    Retorna:
        Lista de dicts con claves: lang, name, model, size_mb, installed.
    """
    return [
        {
            "lang":      lang,
            "name":      name,
            "model":     model,
            "size_mb":   size,
            "installed": is_installed(lang),
        }
        for lang, (model, name, size) in _MODELS.items()
    ]


def is_installed(lang: str) -> bool:
    """
    Verifica si el modelo spaCy para el idioma está instalado.

    Usa spacy.util.is_package() en lugar de importlib para evitar
    falsos negativos cuando el GUI corre con un Python diferente al venv.
    """
    model = _model_name(lang)
    if not model:
        return False
    try:
        import spacy.util
        return spacy.util.is_package(model)
    except Exception:
        return False


def load(lang: str):
    """
    Carga y retorna el modelo spaCy para el idioma dado.

    Raises:
        ValueError:   Si el idioma no está en el mapa de modelos soportados.
        RuntimeError: Si el modelo no está instalado o spaCy falla al cargar.
    """
    model = _model_name(lang)
    if not model:
        supported = ", ".join(sorted(_MODELS))
        raise ValueError(
            f"Idioma '{lang}' no soportado. "
            f"Idiomas disponibles: {supported}"
        )
    if not is_installed(lang):
        raise RuntimeError(
            f"El modelo '{model}' no está instalado.\n"
            f"Descárgalo desde el panel Idiomas en la GUI."
        )
    try:
        import spacy
        return spacy.load(model)
    except Exception as exc:
        raise RuntimeError(
            f"Error al cargar el modelo '{model}':\n{exc}"
        ) from exc


def download(lang: str, progress_cb: ProgressCb | None = None) -> None:
    """
    Descarga el modelo spaCy para el idioma dado.

    Usa subprocess con sys.executable para correr en el mismo venv que la GUI,
    evitando conflictos de estado de pydantic dentro del proceso principal.

    Args:
        lang:        Código ISO 639-1 del idioma.
        progress_cb: Callback (percent 0-100, message). None → salida a stdout.

    Raises:
        ValueError:   Si el idioma no está soportado.
        RuntimeError: Si la descarga falla.
    """
    model = _model_name(lang)
    if not model:
        raise ValueError(f"Idioma '{lang}' no soportado.")

    if progress_cb:
        progress_cb(0, f"Descargando {model}...")

    result = subprocess.run(
        [sys.executable, "-m", "spacy", "download", model],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Error al descargar {model}:\n{result.stderr or result.stdout}"
        )

    if progress_cb:
        progress_cb(100, f"{model} instalado correctamente.")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers internos
# ─────────────────────────────────────────────────────────────────────────────

def _model_name(lang: str) -> str | None:
    """Retorna el nombre del modelo spaCy para el código ISO dado, o None."""
    entry = _MODELS.get(lang)
    return entry[0] if entry else None
