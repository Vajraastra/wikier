"""
ScraperWidget: UI completa del módulo Fandom Scraper.

Ahora es un QWidget embebible dentro del AppWindow.
Emite back_requested cuando el usuario pulsa "← Módulos".

Layout:
  ┌───────────┬──────────────────────────────┐
  │  Sidebar  │       QStackedWidget         │
  │  ← Mód.  │  (ScrapePanel / Profiles /   │
  │  Scraping │   CachePanel)                │
  │  Perfiles │                              │
  │  Caché    │                              │
  └───────────┴──────────────────────────────┘
"""
from PySide6.QtCore    import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel,
    QPushButton, QStackedWidget, QVBoxLayout, QWidget,
    QTextEdit,
)

from modules.gui.panels.profiles_panel import ProfilesPanel
from modules.gui.panels.scrape_panel   import ScrapePanel
from modules.scraper.config            import INDEX_DIR


# ─────────────────────────────────────────────────────────────────────────────
# Panel de caché (simple, no merece módulo propio)
# ─────────────────────────────────────────────────────────────────────────────

class CachePanel(QWidget):
    """Panel para limpiar caché HTTP e índices de speakers."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Gestión de caché")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        desc = QLabel(
            "La caché HTTP evita re-descargar páginas ya visitadas (TTL: 24 h).\n"
            "Los índices guardan el conteo de speakers por wiki."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        btn_http = QPushButton("Limpiar caché HTTP")
        btn_http.clicked.connect(self._clear_http)
        layout.addWidget(btn_http)

        btn_idx = QPushButton("Limpiar índices de speakers")
        btn_idx.clicked.connect(self._clear_indexes)
        layout.addWidget(btn_idx)

        btn_all = QPushButton("Limpiar todo")
        btn_all.clicked.connect(self._clear_all)
        layout.addWidget(btn_all)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFixedHeight(120)
        self.log.setStyleSheet("font-family: monospace; font-size: 11px;")
        layout.addWidget(self.log)

        layout.addStretch()

    def _clear_http(self) -> None:
        try:
            import requests_cache
            requests_cache.clear()
            self.log.append("✓ Caché HTTP limpiada.")
        except Exception as e:
            self.log.append(f"✗ Error: {e}")

    def _clear_indexes(self) -> None:
        count = 0
        if INDEX_DIR.exists():
            for f in INDEX_DIR.glob("*.json"):
                f.unlink()
                count += 1
        self.log.append(f"✓ {count} índice(s) eliminado(s).")

    def _clear_all(self) -> None:
        self._clear_http()
        self._clear_indexes()


# ─────────────────────────────────────────────────────────────────────────────
# ScraperWidget — módulo completo como QWidget embebible
# ─────────────────────────────────────────────────────────────────────────────

_NAV_ITEMS = [
    ("Scraping", 0),
    ("Perfiles", 1),
    ("Caché",    2),
]


class ScraperWidget(QWidget):
    """
    Widget raíz del módulo Fandom Scraper.
    Puede embebirse en cualquier QStackedWidget (AppWindow lo hace).

    Señales:
        back_requested — el usuario pulsó "← Módulos".
    """

    back_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ───────────────────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(160)

        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(0, 0, 0, 0)
        sb_layout.setSpacing(0)

        # Botón volver al dashboard
        btn_back = QPushButton("← Módulos")
        btn_back.setProperty("role", "back")
        btn_back.clicked.connect(self.back_requested)
        sb_layout.addWidget(btn_back)

        # Separador
        sep_top = QFrame()
        sep_top.setFrameShape(QFrame.HLine)
        sb_layout.addWidget(sep_top)

        # Título del módulo
        app_title = QLabel("Fandom Scraper")
        app_title.setObjectName("app-title")
        sb_layout.addWidget(app_title)

        app_sub = QLabel("Dialogue Scraper")
        app_sub.setObjectName("app-sub")
        sb_layout.addWidget(app_sub)

        sep_nav = QFrame()
        sep_nav.setFrameShape(QFrame.HLine)
        sb_layout.addWidget(sep_nav)

        # Botones de navegación interna
        self._nav_buttons: list[QPushButton] = []
        for label, idx in _NAV_ITEMS:
            btn = QPushButton(label)
            btn.setProperty("role", "nav")
            btn.setCheckable(True)
            btn.setChecked(idx == 0)
            btn.clicked.connect(lambda checked, i=idx: self._switch_panel(i))
            sb_layout.addWidget(btn)
            self._nav_buttons.append(btn)

        sb_layout.addStretch()

        version = QLabel("v0.2-dev")
        version.setObjectName("version-label")
        version.setAlignment(Qt.AlignCenter)
        sb_layout.addWidget(version)

        root.addWidget(sidebar)

        # ── Paneles de contenido ──────────────────────────────────────────────
        self._stack = QStackedWidget()

        self._scrape_panel   = ScrapePanel()
        self._profiles_panel = ProfilesPanel()
        self._cache_panel    = CachePanel()

        self._stack.addWidget(self._scrape_panel)    # 0
        self._stack.addWidget(self._profiles_panel)  # 1
        self._stack.addWidget(self._cache_panel)     # 2

        # Sincronizar cambios de perfiles con el combo del scrape panel
        self._profiles_panel.profiles_changed.connect(
            self._scrape_panel.refresh_profiles
        )

        root.addWidget(self._stack)

    def _switch_panel(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == index)
