"""
GUI entry point — inicializa la aplicación PySide6.

Orden de arranque:
  1. Cargar configuración guardada (.settings.json)
  2. Cargar traducciones del idioma configurado
  3. Aplicar tema QSS
  4. Activar caché HTTP del scraper
  5. Mostrar AppWindow (dashboard)
"""
import sys

from PySide6.QtWidgets import QApplication

from modules.core        import settings, i18n, themes
from modules.gui.app_window import AppWindow
from modules.scraper.fetcher import setup_cache


def launch() -> int:
    """
    Lanza la aplicación GUI.

    Returns:
        Código de salida del proceso (0 = OK).
    """
    # 1. Cargar configuración persistida
    settings.load()

    # 2. Cargar traducciones
    lang = settings.get("language", "es")
    i18n.load(lang)

    # 3. Crear la QApplication antes de aplicar el tema
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Wikier")
    app.setApplicationVersion("0.2-dev")

    # 4. Aplicar tema QSS
    theme = settings.get("theme", "default")
    themes.apply(app, theme)

    # 5. Activar caché HTTP
    setup_cache()

    # 6. Ventana principal
    window = AppWindow()
    window.show()

    return app.exec()
