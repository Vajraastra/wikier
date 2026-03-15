"""
Themes: motor de temas visuales.

Aplica un QSS global a la QApplication desde /themes/<name>.qss.

Uso:
    from modules.core.themes import apply, list_themes

    apply(app, "default")     # aplica el tema oscuro
    list_themes()             # → [("default", "Oscuro"), ...]
"""
from pathlib import Path

_THEMES_DIR = Path(__file__).parent.parent.parent / "themes"
_current_theme: str = "default"


def apply(app, theme_name: str = "default") -> bool:
    """
    Carga y aplica el archivo QSS del tema indicado a la QApplication.

    Args:
        app:        Instancia de QApplication.
        theme_name: Nombre del tema (sin extensión .qss).

    Returns:
        True si el tema se aplicó, False si no se encontró el archivo.
    """
    global _current_theme

    path = _THEMES_DIR / f"{theme_name}.qss"
    if not path.exists():
        return False

    with open(path, encoding="utf-8") as f:
        stylesheet = f.read()

    app.setStyleSheet(stylesheet)
    _current_theme = theme_name
    return True


def current() -> str:
    """Retorna el nombre del tema actualmente aplicado."""
    return _current_theme


def list_themes() -> list[tuple[str, str]]:
    """
    Retorna los temas disponibles como lista de (name, display_name).
    El display_name se lee del primer comentario del QSS si tiene formato:
        /* display: Oscuro */
    Si no, usa el nombre del archivo capitalizado.
    """
    import re
    themes = []
    if _THEMES_DIR.exists():
        for path in sorted(_THEMES_DIR.glob("*.qss")):
            name = path.stem
            display = name.capitalize()
            try:
                with open(path, encoding="utf-8") as f:
                    first_line = f.readline()
                match = re.search(r'/\*\s*display:\s*(.+?)\s*\*/', first_line)
                if match:
                    display = match.group(1)
            except Exception:
                pass
            themes.append((name, display))
    return themes
