"""
i18n: motor de internacionalización.

Uso:
    from modules.core.i18n import t, load

    load("es")          # cargar idioma (se llama una vez al inicio)
    t("app.name")       # → "Wikier"
    t("msg.found", n=5) # → "5 páginas encontradas"

Los archivos de traducción están en /locales/<lang>.json.
Si una clave no existe, se retorna la clave misma como fallback.
"""
import json
from pathlib import Path

_LOCALES_DIR = Path(__file__).parent.parent.parent / "locales"

_translations: dict[str, str] = {}
_current_lang: str = "es"


def load(lang: str) -> None:
    """
    Carga el archivo de traducción para el idioma dado.

    Si el archivo no existe, intenta cargar 'es' como fallback.
    Si tampoco existe, las traducciones quedan vacías (t() retorna la clave).
    """
    global _translations, _current_lang

    path = _LOCALES_DIR / f"{lang}.json"

    if not path.exists():
        # Fallback a español
        path = _LOCALES_DIR / "es.json"
        if not path.exists():
            _translations = {}
            return

    with open(path, encoding="utf-8") as f:
        _translations = json.load(f)

    _current_lang = lang


def t(key: str, **kwargs) -> str:
    """
    Retorna la traducción de la clave en el idioma activo.

    Si la clave no existe, retorna la clave misma.
    Soporta interpolación: t("msg.found", n=5) con "{n}" en el string.
    """
    text = _translations.get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text
    return text


def current_lang() -> str:
    """Retorna el código ISO del idioma actualmente cargado."""
    return _current_lang


def available_langs() -> list[tuple[str, str]]:
    """
    Retorna los idiomas disponibles como lista de (code, display_name).
    Detecta automáticamente los archivos .json en /locales/.
    """
    langs = []
    if _LOCALES_DIR.exists():
        for path in sorted(_LOCALES_DIR.glob("*.json")):
            code = path.stem
            # Intentar obtener el nombre del idioma desde sus propias traducciones
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                display = data.get(f"lang.{code}", code.upper())
            except Exception:
                display = code.upper()
            langs.append((code, display))
    return langs
