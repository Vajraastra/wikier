"""
EditorWidget: UI del módulo Editor de Dataset.

Permite revisar y editar manualmente las entradas de un dataset curado
antes de entrenarlo. Mismo patrón arquitectónico que CuratorWidget.

Layout:
  ┌───────────┬──────────────────────────────┐
  │  Sidebar  │       EditorPanel            │
  │  ← Mód.  │                              │
  │  Editor   │                              │
  └───────────┴──────────────────────────────┘
"""
from PySide6.QtCore    import Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout,
    QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from modules.core.i18n               import t
from modules.gui.panels.editor_panel import EditorPanel


class EditorWidget(QWidget):
    """
    Widget raíz del módulo Editor de Dataset.
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

        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(0, 0, 0, 0)
        sb.setSpacing(0)

        btn_back = QPushButton(t("btn.back_modules"))
        btn_back.setProperty("role", "back")
        btn_back.clicked.connect(self.back_requested)
        sb.addWidget(btn_back)

        btn_editor = QPushButton("Editor")
        btn_editor.setProperty("role", "nav")
        btn_editor.setProperty("active", True)
        btn_editor.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        sb.addWidget(btn_editor)

        sb.addStretch()
        root.addWidget(sidebar)

        # ── Panel principal ───────────────────────────────────────────────────
        self._stack = QStackedWidget()
        self._stack.addWidget(EditorPanel())
        root.addWidget(self._stack)
