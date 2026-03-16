"""
CuratorWidget: UI completa del módulo Curator.

QWidget embebible en AppWindow. Mismo patrón que ScraperWidget:
sidebar lateral + QStackedWidget con paneles internos.

Layout:
  ┌───────────┬──────────────────────────────┐
  │  Sidebar  │       QStackedWidget         │
  │  ← Mód.  │  (CuratorPanel / futuro)     │
  │  Curación │                              │
  └───────────┴──────────────────────────────┘
"""
from PySide6.QtCore    import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel,
    QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from modules.gui.panels.curator_panel import CuratorPanel
from modules.gui.panels.languages_panel import LanguagesPanel


_NAV_ITEMS = [
    ("Curación", 0),
    ("Idiomas",  1),
]


class CuratorWidget(QWidget):
    """
    Widget raíz del módulo Curator.
    Emite back_requested cuando el usuario pulsa "← Módulos".
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

        btn_back = QPushButton("← Módulos")
        btn_back.setProperty("role", "back")
        btn_back.clicked.connect(self.back_requested)
        sb_layout.addWidget(btn_back)

        sep_top = QFrame()
        sep_top.setFrameShape(QFrame.HLine)
        sb_layout.addWidget(sep_top)

        app_title = QLabel("Curator")
        app_title.setObjectName("app-title")
        sb_layout.addWidget(app_title)

        app_sub = QLabel("Dataset Curator")
        app_sub.setObjectName("app-sub")
        sb_layout.addWidget(app_sub)

        sep_nav = QFrame()
        sep_nav.setFrameShape(QFrame.HLine)
        sb_layout.addWidget(sep_nav)

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
        self._curator_panel = CuratorPanel()
        self._stack.addWidget(self._curator_panel)   # 0

        self._languages_panel = LanguagesPanel()
        self._languages_panel.models_changed.connect(
            self._curator_panel.refresh_language_status
        )
        self._stack.addWidget(self._languages_panel)  # 1

        root.addWidget(self._stack)

    def _switch_panel(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == index)
