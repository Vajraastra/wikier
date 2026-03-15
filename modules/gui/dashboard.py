"""
Dashboard: pantalla de inicio con selector de módulos.

Muestra una tarjeta por módulo disponible. Los módulos no implementados
aparecen con badge "Próximamente" y no son clickeables.

Señales:
    module_selected(module_id) — emitida cuando el usuario abre un módulo.
"""
from PySide6.QtCore    import Qt, Signal
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFrame, QHBoxLayout,
    QLabel, QPushButton, QVBoxLayout, QWidget,
)

from modules.core        import i18n, settings, themes
from modules.core.i18n   import t


# ─────────────────────────────────────────────────────────────────────────────
# Definición de módulos disponibles
# ─────────────────────────────────────────────────────────────────────────────

# Cada entrada: (module_id, i18n_name_key, i18n_desc_key, available)
_MODULES = [
    ("scraper", "module.scraper.name", "module.scraper.desc", True),
    ("curator", "module.curator.name", "module.curator.desc", False),
]


# ─────────────────────────────────────────────────────────────────────────────
# Tarjeta de módulo
# ─────────────────────────────────────────────────────────────────────────────

class ModuleCard(QFrame):
    """
    Tarjeta visual que representa un módulo de la aplicación.
    Si el módulo está disponible, muestra un botón "Abrir".
    Si no, muestra un badge "Próximamente" con estilo apagado.
    """

    activated = Signal(str)   # module_id

    def __init__(
        self,
        module_id: str,
        name:      str,
        desc:      str,
        available: bool = True,
        parent:    QWidget | None = None,
    ):
        super().__init__(parent)
        self._module_id = module_id
        self._available = available

        self.setObjectName("module-card")
        self.setFixedSize(270, 185)

        if available:
            self.setCursor(Qt.PointingHandCursor)

        self._build_ui(name, desc, available)

    def _build_ui(self, name: str, desc: str, available: bool) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)

        name_lbl = QLabel(name)
        name_lbl.setObjectName("card-title")
        layout.addWidget(name_lbl)

        desc_lbl = QLabel(desc)
        desc_lbl.setObjectName("card-desc")
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)

        layout.addStretch()

        if available:
            btn = QPushButton(t("btn.open"))
            btn.setProperty("role", "primary")
            btn.setFixedHeight(32)
            btn.clicked.connect(lambda: self.activated.emit(self._module_id))
            layout.addWidget(btn)
        else:
            soon_lbl = QLabel(f"● {t('label.coming_soon')}")
            soon_lbl.setObjectName("card-soon")
            layout.addWidget(soon_lbl)

    def mousePressEvent(self, event) -> None:
        if self._available:
            self.activated.emit(self._module_id)


# ─────────────────────────────────────────────────────────────────────────────
# Panel del Dashboard
# ─────────────────────────────────────────────────────────────────────────────

class DashboardPanel(QWidget):
    """
    Panel raíz de la aplicación. Muestra el selector de módulos y los
    controles de idioma y tema en el footer.

    Señales:
        module_selected(module_id) — el usuario eligió un módulo.
    """

    module_selected = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(56, 48, 56, 24)
        root.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────────
        title = QLabel(t("app.name"))
        title.setObjectName("dashboard-title")
        root.addWidget(title)

        subtitle = QLabel(t("dashboard.welcome"))
        subtitle.setObjectName("dashboard-subtitle")
        root.addWidget(subtitle)

        root.addSpacing(36)

        # ── Grid de tarjetas ──────────────────────────────────────────────────
        cards_row = QHBoxLayout()
        cards_row.setSpacing(20)
        cards_row.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        for module_id, name_key, desc_key, available in _MODULES:
            card = ModuleCard(
                module_id = module_id,
                name      = t(name_key),
                desc      = t(desc_key),
                available = available,
            )
            card.activated.connect(self.module_selected)
            cards_row.addWidget(card)

        cards_row.addStretch()
        root.addLayout(cards_row)
        root.addStretch()

        # ── Footer ────────────────────────────────────────────────────────────
        footer = QHBoxLayout()
        footer.setSpacing(8)

        version_lbl = QLabel(t("app.version"))
        version_lbl.setObjectName("footer-label")
        footer.addWidget(version_lbl)

        footer.addStretch()

        # Selector de idioma
        lang_lbl = QLabel(t("label.language") + ":")
        lang_lbl.setObjectName("footer-label")
        footer.addWidget(lang_lbl)

        self._lang_combo = QComboBox()
        self._lang_combo.setFixedWidth(120)
        for code, display in i18n.available_langs():
            self._lang_combo.addItem(display, code)
        # Seleccionar idioma activo
        current = settings.get("language", "es")
        idx = self._lang_combo.findData(current)
        if idx >= 0:
            self._lang_combo.setCurrentIndex(idx)
        self._lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        footer.addWidget(self._lang_combo)

        footer.addSpacing(16)

        # Selector de tema
        theme_lbl = QLabel(t("label.theme") + ":")
        theme_lbl.setObjectName("footer-label")
        footer.addWidget(theme_lbl)

        self._theme_combo = QComboBox()
        self._theme_combo.setFixedWidth(110)
        for name, display in themes.list_themes():
            self._theme_combo.addItem(display, name)
        current_theme = settings.get("theme", "default")
        tidx = self._theme_combo.findData(current_theme)
        if tidx >= 0:
            self._theme_combo.setCurrentIndex(tidx)
        self._theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        footer.addWidget(self._theme_combo)

        root.addLayout(footer)

    # ── Handlers ──────────────────────────────────────────────────────────────

    def _on_lang_changed(self, _index: int) -> None:
        lang = self._lang_combo.currentData()
        settings.set("language", lang)
        # El idioma se aplica al reiniciar; mostrar aviso al usuario
        from PySide6.QtWidgets import QToolTip
        QToolTip.showText(
            self._lang_combo.mapToGlobal(self._lang_combo.rect().bottomLeft()),
            t("label.restart_required"),
            self._lang_combo,
        )

    def _on_theme_changed(self, _index: int) -> None:
        theme_name = self._theme_combo.currentData()
        settings.set("theme", theme_name)
        app = QApplication.instance()
        if app:
            themes.apply(app, theme_name)
