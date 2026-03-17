"""
SettingsPanel: panel de configuración de la aplicación.

Agrupa los ajustes de apariencia (idioma, tema) en un único lugar.
Mismo patrón de widget embebible que los demás módulos.
"""
from PySide6.QtCore    import Signal
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFrame,
    QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, QWidget,
)

from modules.core        import i18n, settings, themes
from modules.core.i18n   import t


class SettingsPanel(QWidget):
    """
    Panel de ajustes de la aplicación.
    Emite back_requested cuando el usuario pulsa "← Módulos".
    """

    back_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Barra superior ────────────────────────────────────────────────────
        topbar = QFrame()
        topbar.setObjectName("settings-topbar")
        topbar_lay = QHBoxLayout(topbar)
        topbar_lay.setContentsMargins(12, 8, 20, 8)
        topbar_lay.setSpacing(12)

        btn_back = QPushButton(t("btn.back_modules"))
        btn_back.setProperty("role", "back")
        btn_back.clicked.connect(self.back_requested)
        topbar_lay.addWidget(btn_back)

        title = QLabel(t("settings.title"))
        title.setObjectName("settings-title")
        topbar_lay.addWidget(title)

        topbar_lay.addStretch()
        root.addWidget(topbar)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        root.addWidget(sep)

        # ── Contenido ─────────────────────────────────────────────────────────
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(48, 40, 48, 40)
        lay.setSpacing(32)

        lay.addWidget(self._build_appearance_group())
        lay.addStretch()
        root.addWidget(content, stretch=1)

    def _build_appearance_group(self) -> QFrame:
        group = QFrame()
        group.setObjectName("settings-group")
        lay = QVBoxLayout(group)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(20)

        group_title = QLabel(t("settings.appearance"))
        group_title.setObjectName("settings-group-title")
        lay.addWidget(group_title)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        lay.addWidget(sep)

        # — Selector de idioma
        lang_row = QHBoxLayout()
        lang_row.setSpacing(16)

        lang_lbl = QLabel(t("label.language"))
        lang_lbl.setFixedWidth(120)
        lang_row.addWidget(lang_lbl)

        self._lang_combo = QComboBox()
        self._lang_combo.setFixedWidth(180)
        for code, display in i18n.available_langs():
            self._lang_combo.addItem(display, code)
        current = settings.get("language", "es")
        idx = self._lang_combo.findData(current)
        if idx >= 0:
            self._lang_combo.setCurrentIndex(idx)
        self._lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        lang_row.addWidget(self._lang_combo)

        self._lang_note = QLabel(t("label.restart_required"))
        self._lang_note.setObjectName("help-text")
        self._lang_note.setVisible(False)
        lang_row.addWidget(self._lang_note)

        lang_row.addStretch()
        lay.addLayout(lang_row)

        # — Selector de tema
        theme_row = QHBoxLayout()
        theme_row.setSpacing(16)

        theme_lbl = QLabel(t("label.theme"))
        theme_lbl.setFixedWidth(120)
        theme_row.addWidget(theme_lbl)

        self._theme_combo = QComboBox()
        self._theme_combo.setFixedWidth(180)
        for name, display in themes.list_themes():
            self._theme_combo.addItem(display, name)
        current_theme = settings.get("theme", "default")
        tidx = self._theme_combo.findData(current_theme)
        if tidx >= 0:
            self._theme_combo.setCurrentIndex(tidx)
        self._theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        theme_row.addWidget(self._theme_combo)

        theme_note = QLabel(t("settings.theme_live"))
        theme_note.setObjectName("help-text")
        theme_row.addWidget(theme_note)

        theme_row.addStretch()
        lay.addLayout(theme_row)

        return group

    # ── Handlers ──────────────────────────────────────────────────────────────

    def _on_lang_changed(self, _index: int) -> None:
        lang = self._lang_combo.currentData()
        settings.set("language", lang)
        self._lang_note.setVisible(True)

    def _on_theme_changed(self, _index: int) -> None:
        theme_name = self._theme_combo.currentData()
        settings.set("theme", theme_name)
        app = QApplication.instance()
        if app:
            themes.apply(app, theme_name)
