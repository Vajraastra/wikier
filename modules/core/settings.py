"""
Settings: persistencia de configuración de la aplicación.

Guarda y carga ajustes del usuario (idioma, tema) en .settings.json
en la raíz del proyecto.
"""
import json
from pathlib import Path

_SETTINGS_FILE = Path(__file__).parent.parent.parent / ".settings.json"

_DEFAULTS: dict = {
    "language": "es",
    "theme":    "default",
}

_settings: dict = dict(_DEFAULTS)


def load() -> None:
    """Carga la configuración desde disco. Usa defaults si el archivo no existe."""
    global _settings
    if _SETTINGS_FILE.exists():
        try:
            with open(_SETTINGS_FILE, encoding="utf-8") as f:
                data = json.load(f)
            _settings = {**_DEFAULTS, **data}
        except Exception:
            _settings = dict(_DEFAULTS)
    else:
        _settings = dict(_DEFAULTS)


def save() -> None:
    """Guarda la configuración actual a disco."""
    with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(_settings, f, indent=2, ensure_ascii=False)


def get(key: str, default=None):
    """Obtiene un valor de configuración."""
    return _settings.get(key, default)


def set(key: str, value) -> None:
    """Actualiza un valor y persiste inmediatamente."""
    _settings[key] = value
    save()
