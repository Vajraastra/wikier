"""
JoinerWidget: UI del módulo Joiner.

Combina datasets curados, convierte formatos (CSV/TXT ↔ JSONL),
aplica merge por objetivo, shuffle y split train/val/test.

Layout:
  ┌───────────┬──────────────────────────────┐
  │  Sidebar  │       QStackedWidget         │
  │  ← Mód.  │  JoinerPanel                 │
  │  Joiner   │                              │
  └───────────┴──────────────────────────────┘
"""
from PySide6.QtCore    import Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout,
    QPushButton, QScrollArea, QStackedWidget, QVBoxLayout, QWidget,
)

from modules.core.i18n import t
from modules.gui.panels.joiner_panel import JoinerPanel


class JoinerWidget(QWidget):
    """
    Widget raíz del módulo Joiner.
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

        btn_back = QPushButton(t("btn.back_modules"))
        btn_back.setProperty("role", "back")
        btn_back.clicked.connect(self.back_requested)
        sb_layout.addWidget(btn_back)

        btn_joiner = QPushButton("Joiner")
        btn_joiner.setProperty("role", "nav")
        btn_joiner.setProperty("active", True)
        btn_joiner.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        sb_layout.addWidget(btn_joiner)

        sb_layout.addStretch()
        root.addWidget(sidebar)

        # ── Panel principal con scroll ─────────────────────────────────────────
        self._stack = QStackedWidget()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(JoinerPanel())

        self._stack.addWidget(scroll)
        root.addWidget(self._stack)
